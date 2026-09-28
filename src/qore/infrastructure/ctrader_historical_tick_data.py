"""Read-only cTrader historical tick contracts for Active Perception.

The cTrader Open API returns historical BID/ASK ticks newest-first. The first
tick contains absolute timestamp/relative-price values; later ticks use signed
deltas from the previous newer tick for both time and relative price.

This module converts that provider representation into explicit point-in-time
observations and request pages. It has no storage, trading, sizing, Risk or
execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import IntEnum
from typing import Protocol

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiMessageClientBoundary,
)
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_RELATIVE_PRICE_SCALE = Decimal(100_000)
_MAX_WINDOW = timedelta(days=7)


class CTraderHistoricalTickError(ExternalPortError):
    """Historical tick request or provider response violates causal semantics."""


class CTraderQuoteType(IntEnum):
    BID = 1
    ASK = 2


class NativeTickLike(Protocol):
    timestamp: int
    tick: int


@dataclass(frozen=True, slots=True)
class CTraderHistoricalTickRequest:
    account_id: int
    symbol_id: int
    quote_type: CTraderQuoteType
    from_at: datetime
    to_at: datetime

    def __post_init__(self) -> None:
        if type(self.account_id) is not int or self.account_id <= 0:
            raise CTraderHistoricalTickError("account_id must be a positive int")
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderHistoricalTickError("symbol_id must be a positive int")
        if not isinstance(self.quote_type, CTraderQuoteType):
            raise CTraderHistoricalTickError(
                "quote_type must be CTraderQuoteType"
            )
        for name, value in (("from_at", self.from_at), ("to_at", self.to_at)):
            if (
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise CTraderHistoricalTickError(
                    f"{name} must be a timezone-aware datetime"
                )
        if self.to_at <= self.from_at:
            raise CTraderHistoricalTickError("tick window must be positive")
        if self.to_at - self.from_at > _MAX_WINDOW:
            raise CTraderHistoricalTickError(
                "cTrader historical tick window cannot exceed seven days"
            )

    @property
    def from_timestamp_ms(self) -> int:
        return int(self.from_at.astimezone(UTC).timestamp() * 1_000)

    @property
    def to_timestamp_ms(self) -> int:
        return int(self.to_at.astimezone(UTC).timestamp() * 1_000)

    def fields(self) -> Mapping[str, object]:
        return {
            "ctidTraderAccountId": self.account_id,
            "symbolId": self.symbol_id,
            "type": int(self.quote_type),
            "fromTimestamp": self.from_timestamp_ms,
            "toTimestamp": self.to_timestamp_ms,
        }


@dataclass(frozen=True, slots=True)
class CTraderHistoricalTick:
    observed_at: datetime
    relative_price: int
    price: Decimal
    quote_type: CTraderQuoteType
    wire_timestamp_value: int
    wire_price_value: int

    def __post_init__(self) -> None:
        if (
            self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise CTraderHistoricalTickError(
                "historical tick timestamp must be timezone-aware"
            )
        if type(self.relative_price) is not int or self.relative_price <= 0:
            raise CTraderHistoricalTickError(
                "historical tick relative price must be positive int"
            )
        if not isinstance(self.price, Decimal) or self.price <= 0:
            raise CTraderHistoricalTickError(
                "historical tick price must be positive Decimal"
            )
        if type(self.wire_timestamp_value) is not int:
            raise CTraderHistoricalTickError(
                "historical tick wire timestamp value must be int"
            )
        if type(self.wire_price_value) is not int:
            raise CTraderHistoricalTickError(
                "historical tick wire price value must be int"
            )


@dataclass(frozen=True, slots=True)
class CTraderHistoricalTickPage:
    request: CTraderHistoricalTickRequest
    ticks: tuple[CTraderHistoricalTick, ...]
    has_more: bool

    def __post_init__(self) -> None:
        if not isinstance(self.request, CTraderHistoricalTickRequest):
            raise CTraderHistoricalTickError(
                "historical tick page requires request"
            )
        if not isinstance(self.ticks, tuple):
            raise CTraderHistoricalTickError("ticks must be immutable tuple")
        if any(not isinstance(item, CTraderHistoricalTick) for item in self.ticks):
            raise CTraderHistoricalTickError(
                "tick page contains invalid observations"
            )
        if tuple(sorted(self.ticks, key=lambda item: item.observed_at)) != self.ticks:
            raise CTraderHistoricalTickError(
                "normalized historical ticks must be oldest-first"
            )
        lower = self.request.from_at.astimezone(UTC)
        upper = self.request.to_at.astimezone(UTC)
        if any(
            item.observed_at < lower or item.observed_at > upper
            for item in self.ticks
        ):
            raise CTraderHistoricalTickError(
                "historical tick escaped requested window"
            )
        if type(self.has_more) is not bool:
            raise CTraderHistoricalTickError("has_more must be bool")

    @property
    def next_older_to_at(self) -> datetime | None:
        if not self.has_more or not self.ticks:
            return None
        return self.ticks[0].observed_at - timedelta(milliseconds=1)


def decode_historical_tick_page(
    *,
    request: CTraderHistoricalTickRequest,
    native_ticks: Sequence[NativeTickLike],
    has_more: bool,
    digits: int,
) -> CTraderHistoricalTickPage:
    """Decode cTrader newest-first absolute+delta timestamps deterministically."""

    if type(digits) is not int or not 0 <= digits <= 12:
        raise CTraderHistoricalTickError("digits must be int within 0..12")
    if type(has_more) is not bool:
        raise CTraderHistoricalTickError("has_more must be bool")
    if not native_ticks:
        if has_more:
            raise CTraderHistoricalTickError(
                "empty tick page cannot advertise has_more"
            )
        return CTraderHistoricalTickPage(
            request=request,
            ticks=(),
            has_more=False,
        )

    newest_first: list[CTraderHistoricalTick] = []
    previous_ms: int | None = None
    previous_relative_price: int | None = None
    quantum = Decimal(1).scaleb(-digits)

    for index, raw in enumerate(native_ticks):
        timestamp_value = getattr(raw, "timestamp", None)
        relative_price = getattr(raw, "tick", None)
        if type(timestamp_value) is not int:
            raise CTraderHistoricalTickError(
                "provider tick timestamp must be int"
            )
        if type(relative_price) is not int:
            raise CTraderHistoricalTickError(
                "provider tick price must be int "
                f"(index={index}, type={type(relative_price).__name__})"
            )

        if index == 0:
            if timestamp_value <= 0:
                raise CTraderHistoricalTickError(
                    "first provider tick requires absolute Unix milliseconds"
                )
            if relative_price <= 0:
                raise CTraderHistoricalTickError(
                    "first provider tick requires positive absolute price"
                )
            absolute_ms = timestamp_value
            absolute_relative_price = relative_price
        else:
            if previous_ms is None or previous_relative_price is None:
                raise CTraderHistoricalTickError(
                    "historical tick decoder lost previous state"
                )
            if timestamp_value > 0:
                raise CTraderHistoricalTickError(
                    "newest-first provider tick delta must be non-positive"
                )
            absolute_ms = previous_ms + timestamp_value
            if absolute_ms < 0:
                raise CTraderHistoricalTickError(
                    "provider tick delta moved before Unix epoch"
                )
            absolute_relative_price = previous_relative_price + relative_price
            if absolute_relative_price <= 0:
                raise CTraderHistoricalTickError(
                    "provider price delta reconstructed non-positive price"
                )

        observed_at = datetime.fromtimestamp(
            absolute_ms / 1_000,
            tz=UTC,
        )
        price = (
            Decimal(absolute_relative_price) / _RELATIVE_PRICE_SCALE
        ).quantize(quantum)
        newest_first.append(
            CTraderHistoricalTick(
                observed_at=observed_at,
                relative_price=absolute_relative_price,
                price=price,
                quote_type=request.quote_type,
                wire_timestamp_value=timestamp_value,
                wire_price_value=relative_price,
            )
        )
        previous_ms = absolute_ms
        previous_relative_price = absolute_relative_price

    for newer, older in zip(newest_first, newest_first[1:], strict=False):
        if older.observed_at > newer.observed_at:
            raise CTraderHistoricalTickError(
                "provider tick chronology is not newest-first"
            )

    # Sort to chronological replay order while preserving provider order for
    # multiple quote updates that share the same millisecond timestamp.
    ticks = tuple(sorted(newest_first, key=lambda item: item.observed_at))
    return CTraderHistoricalTickPage(
        request=request,
        ticks=ticks,
        has_more=has_more,
    )


class CTraderHistoricalTickReader:
    """One authenticated, read-only historical tick page reader."""

    __slots__ = ("_client", "_timeout_seconds")

    def __init__(
        self,
        *,
        client: CTraderOpenApiMessageClientBoundary,
        timeout_seconds: float,
    ) -> None:
        if not isinstance(timeout_seconds, float) or timeout_seconds <= 0.0:
            raise CTraderHistoricalTickError(
                "timeout_seconds must be positive float"
            )
        self._client = client
        self._timeout_seconds = timeout_seconds

    def read_page(
        self,
        *,
        request: CTraderHistoricalTickRequest,
        digits: int,
        client_msg_id: str,
    ) -> Result[CTraderHistoricalTickPage, CTraderHistoricalTickError]:
        if not isinstance(client_msg_id, str) or not client_msg_id:
            return Failure(
                CTraderHistoricalTickError(
                    "client_msg_id must be non-empty"
                )
            )
        if not self._client.is_ready:
            ready = self._client.connect_and_authenticate()
            if isinstance(ready, Failure):
                return Failure(
                    CTraderHistoricalTickError(
                        "cTrader historical tick session unavailable"
                    )
                )
        if self._client.account_id != request.account_id:
            return Failure(
                CTraderHistoricalTickError(
                    "historical tick account mismatch"
                )
            )

        response = self._client.request(
            "ProtoOAGetTickDataReq",
            request.fields(),
            client_msg_id=client_msg_id,
            timeout_seconds=self._timeout_seconds,
        )
        if isinstance(response, Failure):
            return Failure(
                CTraderHistoricalTickError(
                    "cTrader historical tick request failed: "
                    f"{response.error}"
                )
            )

        account_id = getattr(
            response.value,
            "ctidTraderAccountId",
            None,
        )
        native_ticks = getattr(response.value, "tickData", None)
        has_more = getattr(response.value, "hasMore", None)
        if account_id != request.account_id:
            return Failure(
                CTraderHistoricalTickError(
                    "historical tick response account mismatch"
                )
            )
        if native_ticks is None or type(has_more) is not bool:
            return Failure(
                CTraderHistoricalTickError(
                    "historical tick response missing evidence"
                )
            )
        try:
            page = decode_historical_tick_page(
                request=request,
                native_ticks=tuple(native_ticks),
                has_more=has_more,
                digits=digits,
            )
        except (CTraderHistoricalTickError, OverflowError, OSError, ValueError) as error:
            return Failure(
                CTraderHistoricalTickError(
                    "invalid cTrader historical tick response: "
                    f"{type(error).__name__}: {error}"
                )
            )
        return Success(page)
