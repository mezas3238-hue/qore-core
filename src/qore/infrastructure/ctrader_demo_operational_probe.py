from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.ctrader_demo_market_data import (
    CTraderDemoMarketDataFlow,
    CTraderDemoMarketDataPayloadAdapter,
    CTraderTrendbar,
    CTraderTrendbarPeriod,
    CTraderTrendbarReadResult,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcRequest,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Result, Success

_ALLOWED_INSTRUMENTS = ("EURUSD", "GBPUSD")
_DEMO_ENDPOINT_HOST = "demo.ctraderapi.com"
_EVIDENCE_SCHEMA = "qore.ctrader-demo.closed-m5-evidence.v1"
_M5_SECONDS = 300


class CTraderDemoOperationalProbeError(ExternalPortError):
    """Base error for one explicitly invoked cTrader Demo market-data probe."""

    __slots__ = ()


class CTraderDemoOperationalProbeValidationError(CTraderDemoOperationalProbeError):
    """Operational observation violates the read-only cTrader Demo contract."""

    __slots__ = ()


class CTraderClientPermissionScope(IntEnum):
    """cTrader access-token permission admitted by the operational probe."""

    VIEW = 0
    TRADE = 1


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CTraderDemoOperationalProbeValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoOperationalProbeValidationError(
            f"{field_name} must be timezone-aware"
        )


def _stable_uuid(run_key: str, purpose: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"qore:ctrader-demo:{run_key}:{purpose}")


def _account_fingerprint(account_id: int) -> str:
    digest = hashlib.sha256(str(account_id).encode("ascii")).hexdigest()
    return f"sha256:{digest[:24]}"


def normalize_ctrader_symbol_name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CTraderDemoOperationalProbeValidationError(
            "cTrader symbol name must be a non-empty string"
        )
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def closed_m5_interval(started_at: datetime) -> tuple[datetime, datetime]:
    """Return the latest fully closed native M5 interval at an explicit timestamp."""
    _validate_explicit_datetime(started_at, field_name="started_at")
    boundary = started_at.replace(second=0, microsecond=0) - timedelta(
        minutes=started_at.minute % 5
    )
    return boundary - timedelta(seconds=_M5_SECONDS), boundary


def unix_milliseconds(value: datetime) -> int:
    """Convert an explicit timezone-aware datetime to Unix milliseconds without floats."""
    _validate_explicit_datetime(value, field_name="timestamp")
    utc_value = value.astimezone(UTC)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    delta = utc_value - epoch
    milliseconds = (
        delta.days * 86_400_000
        + delta.seconds * 1_000
        + delta.microseconds // 1_000
    )
    if milliseconds < 0:
        raise CTraderDemoOperationalProbeValidationError(
            "timestamp must not predate the Unix epoch"
        )
    return milliseconds


@dataclass(frozen=True, slots=True)
class CTraderDemoOperationalProbeInputs:
    """Non-secret explicit inputs for one deterministic cTrader Demo probe."""

    run_key: str
    instrument: str
    started_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.run_key, str) or re.fullmatch(
            r"[0-9]+-[0-9]+", self.run_key
        ) is None:
            raise CTraderDemoOperationalProbeValidationError(
                "run_key must use '<run-id>-<attempt>' numeric syntax"
            )
        if self.instrument not in _ALLOWED_INSTRUMENTS:
            raise CTraderDemoOperationalProbeValidationError(
                "instrument must be an allowlisted cTrader Demo symbol"
            )
        _validate_explicit_datetime(self.started_at, field_name="started_at")


@dataclass(frozen=True, slots=True, repr=False)
class CTraderGrantedAccount:
    """Sanitized-in-repr account identity returned by the access-token account list."""

    account_id: int
    is_live: bool
    is_live_explicit: bool

    def __post_init__(self) -> None:
        if type(self.account_id) is not int or self.account_id <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader granted account_id must be a positive int"
            )
        if type(self.is_live) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader granted account is_live must be a strict bool"
            )
        if type(self.is_live_explicit) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader granted account is_live_explicit must be a strict bool"
            )

    def __repr__(self) -> str:
        return (
            "CTraderGrantedAccount("
            f"account_fingerprint={_account_fingerprint(self.account_id)!r}, "
            f"is_live={self.is_live!r}, is_live_explicit={self.is_live_explicit!r})"
        )


@dataclass(frozen=True, slots=True)
class CTraderLightSymbolObservation:
    """Provider symbol-list fields needed for exact deterministic symbol selection."""

    symbol_id: int
    symbol_name: str
    enabled: bool
    symbol_name_explicit: bool
    enabled_explicit: bool

    def __post_init__(self) -> None:
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader light symbol_id must be a positive int"
            )
        if type(self.symbol_name_explicit) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader symbol_name_explicit must be a strict bool"
            )
        if type(self.enabled_explicit) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader enabled_explicit must be a strict bool"
            )
        if not isinstance(self.symbol_name, str):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader light symbol name must be a string"
            )
        if self.symbol_name_explicit:
            normalize_ctrader_symbol_name(self.symbol_name)
        if type(self.enabled) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader light symbol enabled must be a strict bool"
            )


@dataclass(frozen=True, slots=True)
class CTraderFullSymbolObservation:
    """Full provider symbol fields required to decode relative trendbar prices."""

    symbol_id: int
    digits: int

    def __post_init__(self) -> None:
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader full symbol_id must be a positive int"
            )
        if type(self.digits) is not int or self.digits < 0:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader full symbol digits must be a non-negative int"
            )


@dataclass(frozen=True, slots=True, repr=False)
class CTraderTrendbarsResponseObservation:
    """Sanitized-in-repr fields from one real ProtoOAGetTrendbarsRes response."""

    account_id: int
    symbol_id: int
    symbol_id_explicit: bool
    period_code: int
    trendbars: tuple[CTraderTrendbar, ...]
    trendbar_fields_explicit: bool
    has_more: bool

    def __post_init__(self) -> None:
        if type(self.account_id) is not int or self.account_id <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader trendbars account_id must be a positive int"
            )
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader trendbars symbol_id must be a positive int"
            )
        if type(self.symbol_id_explicit) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader trendbars symbol_id_explicit must be a strict bool"
            )
        if type(self.period_code) is not int or self.period_code <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader trendbars period_code must be a positive int"
            )
        if not isinstance(self.trendbars, tuple) or any(
            not isinstance(item, CTraderTrendbar) for item in self.trendbars
        ):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader trendbars must be an immutable CTraderTrendbar tuple"
            )
        if type(self.trendbar_fields_explicit) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader trendbar_fields_explicit must be a strict bool"
            )
        if type(self.has_more) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader trendbars has_more must be a strict bool"
            )

    def __repr__(self) -> str:
        return (
            "CTraderTrendbarsResponseObservation("
            f"account_fingerprint={_account_fingerprint(self.account_id)!r}, "
            f"symbol_id={self.symbol_id!r}, symbol_id_explicit={self.symbol_id_explicit!r}, "
            f"period_code={self.period_code!r}, trendbar_count={len(self.trendbars)!r}, "
            f"trendbar_fields_explicit={self.trendbar_fields_explicit!r}, "
            f"has_more={self.has_more!r})"
        )


@dataclass(frozen=True, slots=True, repr=False)
class CTraderDemoOperationalObservation:
    """Credential-free snapshot of one completed real cTrader Demo wire exchange."""

    permission_scope: CTraderClientPermissionScope
    permission_scope_explicit: bool
    granted_accounts: tuple[CTraderGrantedAccount, ...]
    authorized_account_id: int
    light_symbols: tuple[CTraderLightSymbolObservation, ...]
    full_symbol: CTraderFullSymbolObservation
    trendbars_response: CTraderTrendbarsResponseObservation

    def __post_init__(self) -> None:
        if not isinstance(self.permission_scope, CTraderClientPermissionScope):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader permission_scope must be CTraderClientPermissionScope"
            )
        if type(self.permission_scope_explicit) is not bool:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader permission_scope_explicit must be a strict bool"
            )
        if not isinstance(self.granted_accounts, tuple) or any(
            not isinstance(item, CTraderGrantedAccount)
            for item in self.granted_accounts
        ):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader granted_accounts must be an immutable account tuple"
            )
        if type(self.authorized_account_id) is not int or self.authorized_account_id <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader authorized_account_id must be a positive int"
            )
        if not isinstance(self.light_symbols, tuple) or any(
            not isinstance(item, CTraderLightSymbolObservation)
            for item in self.light_symbols
        ):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader light_symbols must be an immutable symbol tuple"
            )
        if not isinstance(self.full_symbol, CTraderFullSymbolObservation):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader full_symbol must be CTraderFullSymbolObservation"
            )
        if not isinstance(
            self.trendbars_response, CTraderTrendbarsResponseObservation
        ):
            raise CTraderDemoOperationalProbeValidationError(
                "cTrader trendbars_response must be CTraderTrendbarsResponseObservation"
            )

    def __repr__(self) -> str:
        return (
            "CTraderDemoOperationalObservation("
            f"permission_scope={self.permission_scope.name!r}, "
            f"permission_scope_explicit={self.permission_scope_explicit!r}, "
            f"granted_accounts={self.granted_accounts!r}, "
            f"authorized_account_fingerprint="
            f"{_account_fingerprint(self.authorized_account_id)!r}, "
            f"light_symbol_count={len(self.light_symbols)!r}, "
            f"full_symbol={self.full_symbol!r}, "
            f"trendbars_response={self.trendbars_response!r})"
        )


@dataclass(frozen=True, slots=True)
class CTraderDemoOperationalEvidence:
    """Sanitized proof that one real Demo trendbar formed a canonical QORE snapshot."""

    run_key: str
    provider_key: str
    environment: str
    endpoint_host: str
    account_fingerprint: str
    instrument: str
    symbol_id: int
    digits: int
    timeframe_seconds: int
    snapshot_id: UUID
    opened_at: datetime
    closed_at: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if self.provider_key != "ctrader-open-api":
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence provider must be ctrader-open-api"
            )
        if self.environment != "demo":
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence environment must be demo"
            )
        if self.endpoint_host != _DEMO_ENDPOINT_HOST:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence endpoint must be cTrader Demo"
            )
        if self.instrument not in _ALLOWED_INSTRUMENTS:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence instrument must be allowlisted"
            )
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence symbol_id must be a positive int"
            )
        if type(self.digits) is not int or self.digits < 0:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence digits must be a non-negative int"
            )
        if self.timeframe_seconds != _M5_SECONDS:
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence timeframe must be native M5"
            )
        if not isinstance(self.snapshot_id, UUID):
            raise CTraderDemoOperationalProbeValidationError(
                "operational evidence snapshot_id must be UUID"
            )
        _validate_explicit_datetime(self.opened_at, field_name="evidence opened_at")
        _validate_explicit_datetime(self.closed_at, field_name="evidence closed_at")
        for field_name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if type(value) is not float or value <= 0.0:
                raise CTraderDemoOperationalProbeValidationError(
                    f"operational evidence {field_name} must be a positive float"
                )

    def public_payload(self) -> dict[str, object]:
        """Return stable evidence safe for logs and artifacts."""
        return {
            "account_fingerprint": self.account_fingerprint,
            "close": self.close,
            "closed_at": self.closed_at.isoformat(),
            "digits": self.digits,
            "endpoint_host": self.endpoint_host,
            "environment": self.environment,
            "high": self.high,
            "instrument": self.instrument,
            "low": self.low,
            "open": self.open,
            "opened_at": self.opened_at.isoformat(),
            "provider_key": self.provider_key,
            "run_key": self.run_key,
            "schema": _EVIDENCE_SCHEMA,
            "snapshot_id": str(self.snapshot_id),
            "status": "success",
            "symbol_id": self.symbol_id,
            "timeframe_seconds": self.timeframe_seconds,
        }

    def to_json(self) -> str:
        return json.dumps(self.public_payload(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class _ObservedTrendbarClient:
    descriptor: ExternalSourceDescriptor
    result: CTraderTrendbarReadResult

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return Success(
            ExternalHealth(
                descriptor=self.descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        )

    def read_trendbars(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderTrendbarReadResult, ExternalPortError]:
        del request, metadata
        return Success(self.result)


def _source(run_key: str) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_stable_uuid(run_key, "adapter")),
        source_id=SourceId(_stable_uuid(run_key, "source")),
        port_name=PortName("market-data.ctrader-demo"),
    )


def _metadata(run_key: str) -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=CorrelationId(_stable_uuid(run_key, "correlation")),
        causation_id=CausationId(_stable_uuid(run_key, "causation")),
        attributes={
            "run-key": run_key,
            "workflow": "ctrader-demo-closed-m5-operational-probe",
        },
    )


def _selected_account(
    observation: CTraderDemoOperationalObservation,
) -> Result[CTraderGrantedAccount, ExternalPortError]:
    if not observation.permission_scope_explicit:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader permission scope must be explicitly present on the wire"
            )
        )
    if observation.permission_scope is not CTraderClientPermissionScope.VIEW:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader operational probe requires VIEW-only permission scope"
            )
        )
    if len(observation.granted_accounts) != 1:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader operational probe requires exactly one granted account"
            )
        )
    account = observation.granted_accounts[0]
    if not account.is_live_explicit:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader account isLive must be explicitly present on the wire"
            )
        )
    if account.is_live:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader operational probe refuses Live accounts"
            )
        )
    if observation.authorized_account_id != account.account_id:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader authorized account must match the granted Demo account"
            )
        )
    return Success(account)


def _selected_symbol(
    instrument: str,
    observation: CTraderDemoOperationalObservation,
) -> Result[CTraderLightSymbolObservation, ExternalPortError]:
    matching = tuple(
        item
        for item in observation.light_symbols
        if item.symbol_name_explicit
        and normalize_ctrader_symbol_name(item.symbol_name) == instrument
    )
    if len(matching) != 1:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader symbol list must contain exactly one requested instrument"
            )
        )
    selected = matching[0]
    if not selected.enabled_explicit:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader selected symbol enabled field must be explicit"
            )
        )
    if not selected.enabled:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader requested symbol must be explicitly enabled"
            )
        )
    if observation.full_symbol.symbol_id != selected.symbol_id:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader full symbol metadata must bind to selected symbol_id"
            )
        )
    return Success(selected)


def run_ctrader_demo_closed_m5_probe(
    inputs: CTraderDemoOperationalProbeInputs,
    observation: CTraderDemoOperationalObservation,
) -> Result[CTraderDemoOperationalEvidence, ExternalPortError]:
    """Validate one real wire observation and project it through canonical ingestion."""
    if not isinstance(inputs, CTraderDemoOperationalProbeInputs):
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader operational probe requires explicit inputs"
            )
        )
    if not isinstance(observation, CTraderDemoOperationalObservation):
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader operational probe requires an operational observation"
            )
        )

    account_result = _selected_account(observation)
    if isinstance(account_result, Failure):
        return account_result
    account = account_result.value

    symbol_result = _selected_symbol(inputs.instrument, observation)
    if isinstance(symbol_result, Failure):
        return symbol_result
    symbol = symbol_result.value

    response = observation.trendbars_response
    if response.account_id != account.account_id:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader trendbar response account must match authorized Demo account"
            )
        )
    if not response.symbol_id_explicit:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader trendbar response symbol_id must be explicitly present"
            )
        )
    if response.symbol_id != symbol.symbol_id:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader trendbar response symbol_id must match selected symbol"
            )
        )
    if response.period_code != 5:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader trendbar response period code must be M5"
            )
        )
    if not response.trendbar_fields_explicit:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader trendbar required price/time fields must be explicit"
            )
        )
    if len(response.trendbars) == 1 and response.trendbars[0].delta_high == 0:
        return Failure(
            CTraderDemoOperationalProbeValidationError(
                "cTrader zero-deltaHigh historical bar is ambiguous and not certifiable"
            )
        )

    opened_at, closed_at = closed_m5_interval(inputs.started_at)
    request = OhlcRequest(
        instrument=Instrument(inputs.instrument),
        timeframe=Timeframe(_M5_SECONDS),
        opened_at=opened_at,
        closed_at=closed_at,
    )

    read_result = CTraderTrendbarReadResult(
        instrument=inputs.instrument,
        symbol_id=symbol.symbol_id,
        digits=observation.full_symbol.digits,
        period=CTraderTrendbarPeriod.M5,
        trendbars=response.trendbars,
        has_more=response.has_more,
    )
    client = _ObservedTrendbarClient(
        descriptor=_source(inputs.run_key),
        result=read_result,
    )
    flow = CTraderDemoMarketDataFlow(
        CTraderDemoMarketDataPayloadAdapter(client=client)
    )
    snapshot_id = MarketDataSnapshotId(_stable_uuid(inputs.run_key, "ohlc-snapshot"))
    snapshot_result = flow.read_ohlc(
        request,
        snapshot_id=snapshot_id,
        metadata=_metadata(inputs.run_key),
    )
    if isinstance(snapshot_result, Failure):
        return Failure(snapshot_result.error)
    snapshot = snapshot_result.value
    try:
        evidence = CTraderDemoOperationalEvidence(
            run_key=inputs.run_key,
            provider_key="ctrader-open-api",
            environment="demo",
            endpoint_host=_DEMO_ENDPOINT_HOST,
            account_fingerprint=_account_fingerprint(account.account_id),
            instrument=snapshot.instrument.symbol,
            symbol_id=symbol.symbol_id,
            digits=observation.full_symbol.digits,
            timeframe_seconds=snapshot.timeframe.seconds,
            snapshot_id=snapshot.snapshot_id.value,
            opened_at=snapshot.opened_at,
            closed_at=snapshot.closed_at,
            open=snapshot.open,
            high=snapshot.high,
            low=snapshot.low,
            close=snapshot.close,
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(evidence)
