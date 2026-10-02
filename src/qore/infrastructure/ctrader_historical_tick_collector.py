"""Read-only cTrader historical BID/ASK acquisition for Shared WP-05 V12.

The collector resolves exact provider symbol identity, requests historical BID
and ASK independently, paginates newest-first provider chunks, preserves
provider-event versus retrieval time, and emits deterministic coverage/digest
evidence. It has no order, sizing, Risk, capital or Execution authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import sleep
from typing import Protocol

from qore.infrastructure.ctrader_historical_tick_data import (
    CTraderHistoricalTickError,
    CTraderHistoricalTickPage,
    CTraderHistoricalTickReader,
    CTraderHistoricalTickRequest,
    CTraderQuoteType,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiClientError,
    CTraderOpenApiMessageClientBoundary,
)
from qore.infrastructure.historical_quote_side_evidence import (
    HistoricalQuoteSideEvidenceError,
    HistoricalQuoteSideObservation,
    retain_ctrader_historical_quote_side_page,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.ports import ExternalPortError, ExternalSourceDescriptor
from qore.kernel.result import Failure, Result, Success

_MAX_WINDOW = timedelta(days=7)
_ONE_MILLISECOND = timedelta(milliseconds=1)
_DEFAULT_HISTORICAL_REQUEST_INTERVAL_SECONDS = 0.2
_HISTORICAL_READ_ONLY_MESSAGES = frozenset(
    {
        "ProtoOASymbolsListReq",
        "ProtoOASymbolByIdReq",
        "ProtoOAGetTickDataReq",
    }
)


class CTraderHistoricalTickCollectorError(ExternalPortError):
    """Historical acquisition violates provider or provenance contracts."""


class CTraderHistoricalReadOnlyClientError(CTraderOpenApiClientError):
    """The V12 provider firewall rejected a non-observation operation."""


@dataclass(frozen=True, slots=True)
class CTraderHistoricalSensorIdentity:
    account_id: int
    symbol_id: int
    provider_symbol: str
    digits: int

    def __post_init__(self) -> None:
        if type(self.account_id) is not int or self.account_id <= 0:
            raise CTraderHistoricalTickCollectorError(
                "account_id must be a positive int"
            )
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderHistoricalTickCollectorError(
                "symbol_id must be a positive int"
            )
        if (
            not isinstance(self.provider_symbol, str)
            or not self.provider_symbol
            or self.provider_symbol != self.provider_symbol.strip()
        ):
            raise CTraderHistoricalTickCollectorError(
                "provider_symbol must be a non-empty trimmed string"
            )
        if type(self.digits) is not int or not 0 <= self.digits <= 12:
            raise CTraderHistoricalTickCollectorError(
                "digits must be int within 0..12"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id,
            self.symbol_id,
            self.provider_symbol,
            self.digits,
        )


@dataclass(frozen=True, slots=True)
class HistoricalRequestWindow:
    from_at: datetime
    to_at: datetime

    def __post_init__(self) -> None:
        for name, value in (("from_at", self.from_at), ("to_at", self.to_at)):
            if (
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise CTraderHistoricalTickCollectorError(
                    f"{name} must be a timezone-aware datetime"
                )
        if self.to_at <= self.from_at:
            raise CTraderHistoricalTickCollectorError(
                "historical request window must be positive"
            )
        if self.to_at - self.from_at > _MAX_WINDOW:
            raise CTraderHistoricalTickCollectorError(
                "historical request window cannot exceed seven days"
            )


def split_historical_request_windows(
    *,
    from_at: datetime,
    to_at: datetime,
) -> tuple[HistoricalRequestWindow, ...]:
    """Split one range into non-overlapping provider windows of at most 7 days."""

    if (
        not isinstance(from_at, datetime)
        or from_at.tzinfo is None
        or from_at.utcoffset() is None
        or not isinstance(to_at, datetime)
        or to_at.tzinfo is None
        or to_at.utcoffset() is None
    ):
        raise CTraderHistoricalTickCollectorError(
            "historical range timestamps must be timezone-aware"
        )
    start = from_at.astimezone(UTC)
    finish = to_at.astimezone(UTC)
    if finish <= start:
        raise CTraderHistoricalTickCollectorError(
            "historical acquisition range must be positive"
        )

    windows: list[HistoricalRequestWindow] = []
    cursor = start
    while cursor < finish:
        window_end = min(cursor + _MAX_WINDOW, finish)
        windows.append(HistoricalRequestWindow(cursor, window_end))
        if window_end == finish:
            break
        cursor = window_end + _ONE_MILLISECOND
    return tuple(windows)


def resolve_ctrader_historical_sensor_identity(
    *,
    client: CTraderOpenApiMessageClientBoundary,
    provider_symbol: str,
    timeout_seconds: float,
) -> Result[
    CTraderHistoricalSensorIdentity,
    CTraderHistoricalTickCollectorError,
]:
    """Resolve exact enabled symbol ID and digits from an authenticated DEMO account."""

    if (
        not isinstance(provider_symbol, str)
        or not provider_symbol
        or provider_symbol != provider_symbol.strip()
    ):
        return Failure(
            CTraderHistoricalTickCollectorError(
                "provider_symbol must be a non-empty trimmed string"
            )
        )
    if not isinstance(timeout_seconds, float) or timeout_seconds <= 0.0:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "timeout_seconds must be a positive float"
            )
        )
    if not client.is_ready:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            return Failure(
                CTraderHistoricalTickCollectorError(
                    "cTrader historical sensor session unavailable"
                )
            )

    listed = client.request(
        "ProtoOASymbolsListReq",
        {
            "ctidTraderAccountId": client.account_id,
            "includeArchivedSymbols": False,
        },
        client_msg_id="wp05-v12-symbol-list",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(listed, Failure):
        return Failure(
            CTraderHistoricalTickCollectorError(
                "cTrader historical symbol list request failed"
            )
        )
    if getattr(listed.value, "ctidTraderAccountId", None) != client.account_id:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "cTrader historical symbol-list account mismatch"
            )
        )
    native_symbols = getattr(listed.value, "symbol", None)
    if native_symbols is None:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "cTrader historical symbol list is missing"
            )
        )
    matches = tuple(
        item
        for item in native_symbols
        if getattr(item, "symbolName", None) == provider_symbol
        and getattr(item, "enabled", None) is True
    )
    if len(matches) != 1:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "provider symbol must resolve to exactly one enabled identity"
            )
        )
    symbol_id = getattr(matches[0], "symbolId", None)
    if type(symbol_id) is not int or symbol_id <= 0:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "resolved provider symbol id is invalid"
            )
        )

    details = client.request(
        "ProtoOASymbolByIdReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": [symbol_id],
        },
        client_msg_id="wp05-v12-symbol-details",
        timeout_seconds=timeout_seconds,
    )
    if isinstance(details, Failure):
        return Failure(
            CTraderHistoricalTickCollectorError(
                "cTrader historical symbol details request failed"
            )
        )
    if getattr(details.value, "ctidTraderAccountId", None) != client.account_id:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "cTrader historical symbol-details account mismatch"
            )
        )
    native_details = getattr(details.value, "symbol", None)
    if native_details is None or len(native_details) != 1:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "cTrader historical symbol details are incomplete"
            )
        )
    detail = native_details[0]
    if getattr(detail, "symbolId", None) != symbol_id:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "cTrader historical symbol detail identity mismatch"
            )
        )
    digits = getattr(detail, "digits", None)
    if type(digits) is not int or not 0 <= digits <= 12:
        return Failure(
            CTraderHistoricalTickCollectorError(
                "cTrader historical symbol digits are invalid"
            )
        )
    try:
        identity = CTraderHistoricalSensorIdentity(
            account_id=client.account_id,
            symbol_id=symbol_id,
            provider_symbol=provider_symbol,
            digits=digits,
        )
    except CTraderHistoricalTickCollectorError as error:
        return Failure(error)
    return Success(identity)


class CTraderHistoricalReadOnlyMessageClient:
    """Fail-closed message firewall for V12 historical acquisition.

    The underlying authenticated client may hold either a view-only or a
    trading-capable token. This wrapper admits only the three read-only provider
    requests required by V12 and never exposes subscription or order-shaped
    operations to the collector.
    """

    __slots__ = ("_client",)

    def __init__(self, client: CTraderOpenApiMessageClientBoundary) -> None:
        self._client = client

    @property
    def is_ready(self) -> bool:
        return self._client.is_ready

    @property
    def account_id(self) -> int:
        return self._client.account_id

    def connect_and_authenticate(self) -> Result[None, CTraderOpenApiClientError]:
        return self._client.connect_and_authenticate()

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]:
        if message_name not in _HISTORICAL_READ_ONLY_MESSAGES:
            return Failure(
                CTraderHistoricalReadOnlyClientError(
                    "V12 historical client rejected non-read-only provider message"
                )
            )
        result = self._client.request(
            message_name,
            fields,
            client_msg_id=client_msg_id,
            timeout_seconds=timeout_seconds,
        )
        if isinstance(result, Failure):
            # The underlying Open API boundary already sanitizes provider errors.
            # Preserve that category/code so research runs can distinguish a
            # protocol rejection from timeout/transport failure without exposing
            # credentials or raw provider payloads.
            return Failure(result.error)
        return Success(result.value)

    def wait_for_event(
        self,
        message_name: str,
        *,
        timeout_seconds: float,
        predicate: Callable[[object], bool] | None = None,
    ) -> Result[object, CTraderOpenApiClientError]:
        del message_name, timeout_seconds, predicate
        return Failure(
            CTraderHistoricalReadOnlyClientError(
                "V12 historical client does not admit provider subscriptions"
            )
        )

    def close(self) -> None:
        self._client.close()


class HistoricalTickPageReaderBoundary(Protocol):
    def read_page(
        self,
        *,
        request: CTraderHistoricalTickRequest,
        digits: int,
        client_msg_id: str,
    ) -> Result[CTraderHistoricalTickPage, CTraderHistoricalTickError]: ...


@dataclass(frozen=True, slots=True)
class CTraderHistoricalTickCoverage:
    requested_from_at: datetime
    requested_to_at: datetime
    bid_count: int
    ask_count: int
    bid_page_count: int
    ask_page_count: int
    bid_first_at: datetime | None
    bid_last_at: datetime | None
    ask_first_at: datetime | None
    ask_last_at: datetime | None
    digest_sha256: str

    def __post_init__(self) -> None:
        if self.bid_count < 0 or self.ask_count < 0:
            raise CTraderHistoricalTickCollectorError(
                "historical tick counts must be non-negative"
            )
        if self.bid_page_count < 0 or self.ask_page_count < 0:
            raise CTraderHistoricalTickCollectorError(
                "historical page counts must be non-negative"
            )
        if (
            not isinstance(self.digest_sha256, str)
            or len(self.digest_sha256) != 64
        ):
            raise CTraderHistoricalTickCollectorError(
                "historical dataset digest must be sha256 hex"
            )


@dataclass(frozen=True, slots=True)
class CTraderHistoricalTickCollection:
    identity: CTraderHistoricalSensorIdentity
    bid: tuple[HistoricalQuoteSideObservation, ...]
    ask: tuple[HistoricalQuoteSideObservation, ...]
    coverage: CTraderHistoricalTickCoverage

    def __post_init__(self) -> None:
        if any(item.provider_symbol_id != self.identity.symbol_id for item in self.bid):
            raise CTraderHistoricalTickCollectorError(
                "BID collection symbol identity mismatch"
            )
        if any(item.provider_symbol_id != self.identity.symbol_id for item in self.ask):
            raise CTraderHistoricalTickCollectorError(
                "ASK collection symbol identity mismatch"
            )


def _canonical_dataset_digest(
    *,
    identity: CTraderHistoricalSensorIdentity,
    bid: tuple[HistoricalQuoteSideObservation, ...],
    ask: tuple[HistoricalQuoteSideObservation, ...],
) -> str:
    payload: Mapping[str, object] = {
        "identity": identity.logical_values(),
        "bid": tuple(item.logical_values() for item in bid),
        "ask": tuple(item.logical_values() for item in ask),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _ordered(
    observations: list[HistoricalQuoteSideObservation],
) -> tuple[HistoricalQuoteSideObservation, ...]:
    return tuple(
        sorted(
            observations,
            key=lambda item: (
                item.provider_event_at,
                item.relative_price,
                item.retrieved_at,
            ),
        )
    )


class CTraderHistoricalTickCollector:
    """Deterministic two-side collector over a read-only historical page reader."""

    __slots__ = (
        "_clock",
        "_instrument",
        "_interval_seconds",
        "_provider_symbol",
        "_reader",
        "_sleeper",
        "_source",
    )

    def __init__(
        self,
        *,
        reader: HistoricalTickPageReaderBoundary,
        instrument: Instrument,
        source: ExternalSourceDescriptor,
        provider_symbol: str,
        clock: Callable[[], datetime],
        sleeper: Callable[[float], None] = sleep,
        request_interval_seconds: float = (
            _DEFAULT_HISTORICAL_REQUEST_INTERVAL_SECONDS
        ),
    ) -> None:
        if not isinstance(instrument, Instrument):
            raise CTraderHistoricalTickCollectorError(
                "collector instrument must be Instrument"
            )
        if not isinstance(source, ExternalSourceDescriptor):
            raise CTraderHistoricalTickCollectorError(
                "collector source must be ExternalSourceDescriptor"
            )
        if (
            not isinstance(provider_symbol, str)
            or not provider_symbol
            or provider_symbol != provider_symbol.strip()
        ):
            raise CTraderHistoricalTickCollectorError(
                "collector provider_symbol must be non-empty"
            )
        if not callable(clock) or not callable(sleeper):
            raise CTraderHistoricalTickCollectorError(
                "collector clock and sleeper must be callable"
            )
        if (
            not isinstance(request_interval_seconds, float)
            or request_interval_seconds < 0.2
        ):
            raise CTraderHistoricalTickCollectorError(
                "historical request interval must be at least 0.2 seconds"
            )
        self._reader = reader
        self._instrument = instrument
        self._source = source
        self._provider_symbol = provider_symbol
        self._clock = clock
        self._sleeper = sleeper
        self._interval_seconds = request_interval_seconds

    def _collect_side(
        self,
        *,
        identity: CTraderHistoricalSensorIdentity,
        quote_type: CTraderQuoteType,
        windows: tuple[HistoricalRequestWindow, ...],
    ) -> Result[
        tuple[tuple[HistoricalQuoteSideObservation, ...], int],
        CTraderHistoricalTickCollectorError,
    ]:
        observations: list[HistoricalQuoteSideObservation] = []
        page_count = 0
        request_count = 0
        for window_index, window in enumerate(windows):
            page_to_at = window.to_at
            page_index = 0
            while True:
                if request_count:
                    self._sleeper(self._interval_seconds)
                request = CTraderHistoricalTickRequest(
                    account_id=identity.account_id,
                    symbol_id=identity.symbol_id,
                    quote_type=quote_type,
                    from_at=window.from_at,
                    to_at=page_to_at,
                )
                result = self._reader.read_page(
                    request=request,
                    digits=identity.digits,
                    client_msg_id=(
                        f"wp05-v12-{quote_type.name.lower()}-"
                        f"{window_index}-{page_index}"
                    ),
                )
                request_count += 1
                if isinstance(result, Failure):
                    return Failure(
                        CTraderHistoricalTickCollectorError(
                            "historical tick page request failed: "
                            f"{result.error}"
                        )
                    )
                page = result.value
                retrieved_at = self._clock()
                try:
                    retained = retain_ctrader_historical_quote_side_page(
                        page=page,
                        instrument=self._instrument,
                        source=self._source,
                        provider_symbol=self._provider_symbol,
                        retrieved_at=retrieved_at,
                    )
                except HistoricalQuoteSideEvidenceError as error:
                    return Failure(
                        CTraderHistoricalTickCollectorError(str(error))
                    )
                observations.extend(retained)
                page_count += 1
                next_to_at = page.next_older_to_at
                if next_to_at is None:
                    break
                if next_to_at <= window.from_at or next_to_at >= page_to_at:
                    return Failure(
                        CTraderHistoricalTickCollectorError(
                            "historical tick pagination made no legal progress"
                        )
                    )
                page_to_at = next_to_at
                page_index += 1
        return Success((_ordered(observations), page_count))

    def collect(
        self,
        *,
        identity: CTraderHistoricalSensorIdentity,
        from_at: datetime,
        to_at: datetime,
    ) -> Result[CTraderHistoricalTickCollection, CTraderHistoricalTickCollectorError]:
        if not isinstance(identity, CTraderHistoricalSensorIdentity):
            return Failure(
                CTraderHistoricalTickCollectorError(
                    "collector requires CTraderHistoricalSensorIdentity"
                )
            )
        if identity.provider_symbol != self._provider_symbol:
            return Failure(
                CTraderHistoricalTickCollectorError(
                    "collector provider symbol does not match sensor identity"
                )
            )
        try:
            windows = split_historical_request_windows(
                from_at=from_at,
                to_at=to_at,
            )
        except CTraderHistoricalTickCollectorError as error:
            return Failure(error)

        bid_result = self._collect_side(
            identity=identity,
            quote_type=CTraderQuoteType.BID,
            windows=windows,
        )
        if isinstance(bid_result, Failure):
            return bid_result
        ask_result = self._collect_side(
            identity=identity,
            quote_type=CTraderQuoteType.ASK,
            windows=windows,
        )
        if isinstance(ask_result, Failure):
            return ask_result

        bid, bid_page_count = bid_result.value
        ask, ask_page_count = ask_result.value
        digest = _canonical_dataset_digest(
            identity=identity,
            bid=bid,
            ask=ask,
        )
        coverage = CTraderHistoricalTickCoverage(
            requested_from_at=from_at.astimezone(UTC),
            requested_to_at=to_at.astimezone(UTC),
            bid_count=len(bid),
            ask_count=len(ask),
            bid_page_count=bid_page_count,
            ask_page_count=ask_page_count,
            bid_first_at=bid[0].provider_event_at if bid else None,
            bid_last_at=bid[-1].provider_event_at if bid else None,
            ask_first_at=ask[0].provider_event_at if ask else None,
            ask_last_at=ask[-1].provider_event_at if ask else None,
            digest_sha256=digest,
        )
        return Success(
            CTraderHistoricalTickCollection(
                identity=identity,
                bid=bid,
                ask=ask,
                coverage=coverage,
            )
        )


def build_ctrader_historical_tick_reader(
    *,
    client: CTraderOpenApiMessageClientBoundary,
    timeout_seconds: float,
) -> CTraderHistoricalTickReader:
    """Explicit constructor retained here for acquisition composition."""

    return CTraderHistoricalTickReader(
        client=client,
        timeout_seconds=timeout_seconds,
    )
