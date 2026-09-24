from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

NEW_YORK_TZ = ZoneInfo("America/New_York")
LEGACY_SERVER_TZ = ZoneInfo("Europe/Helsinki")


def normalise_legacy_server_epoch(value: int) -> datetime:
    """Decode the legacy broker-wall-clock epoch used by frozen trader logic."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("legacy provider timestamp must be int")
    pseudo_utc = datetime.fromtimestamp(value, tz=UTC).replace(tzinfo=None)
    return pseudo_utc.replace(tzinfo=LEGACY_SERVER_TZ).astimezone(UTC)


def causal_daily_candidate_allowed(
    *,
    candidate_anchor_hours: tuple[int, ...],
    current_anchor_hour: int,
    admitted_anchor_hours: tuple[int, ...],
) -> bool:
    normalized = tuple(sorted(candidate_anchor_hours))
    admitted = tuple(sorted(admitted_anchor_hours))
    return current_anchor_hour in admitted and current_anchor_hour in normalized


def h4_containment_exit_at(signal_at: datetime) -> datetime:
    if signal_at.tzinfo is None or signal_at.utcoffset() is None:
        raise ValueError("signal_at must be timezone-aware")
    local = signal_at.astimezone(NEW_YORK_TZ)
    if local.minute != 0 or local.second != 0 or local.microsecond != 0:
        raise ValueError("signal_at must be exact H4 anchor")
    return (local + timedelta(hours=4)).astimezone(UTC)


@dataclass(frozen=True, slots=True)
class CTraderDemoAccountState:
    balance: Decimal
    equity: Decimal
    margin: Decimal
    free_margin: Decimal
    observed_at: datetime

    def __post_init__(self) -> None:
        for value in (self.balance, self.equity, self.margin, self.free_margin):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ValueError("account monetary values must be non-negative finite Decimal")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CTraderDemoSymbolSpecification:
    provider_symbol: str
    bid: Decimal
    ask: Decimal
    spread_points: Decimal
    digits: int
    point: Decimal
    contract_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    minimum_stop_distance_points: Decimal
    freeze_level_points: Decimal
    margin_per_volume: Decimal
    trade_enabled: bool
    session_open: bool
    observed_at: datetime
    open_commission_per_lot_usd: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.provider_symbol:
            raise ValueError("provider_symbol is required")
        for value in (
            self.bid, self.ask, self.point, self.contract_size, self.tick_size,
            self.tick_value, self.minimum_volume, self.maximum_volume,
            self.volume_step, self.margin_per_volume,
        ):
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise ValueError("positive finite Decimal required")
        for value in (
            self.spread_points,
            self.minimum_stop_distance_points,
            self.freeze_level_points,
            self.open_commission_per_lot_usd,
        ):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ValueError("non-negative finite Decimal required")
        if self.ask < self.bid:
            raise ValueError("ask cannot be below bid")
        if type(self.digits) is not int or self.digits < 0:
            raise ValueError("digits must be non-negative int")
        if self.maximum_volume < self.minimum_volume:
            raise ValueError("maximum volume cannot be below minimum")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
