"""Frozen provider-native pre-entry M1 path-state representation for V40.

V40 is an information-frontier experiment only. It uses exactly the 30 M1 bars
that close at or before the frozen entry timestamp. The entry bar, future path,
outcome, exit reason and MAE/MFE are structurally forbidden.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)

IDENTITY = "QORE_CAPITALIZER_PREENTRY_CAUSAL_M1_PATH_STATE_V40"
HORIZONS = (5, 15, 30)
LOOKBACK_MINUTES = 30

FEATURE_NAMES = (
    "m5_directional_net_displacement_r",
    "m5_close_path_length_r",
    "m5_path_efficiency",
    "m5_summed_range_r",
    "m5_close_increment_reversal_rate",
    "m15_directional_net_displacement_r",
    "m15_close_path_length_r",
    "m15_path_efficiency",
    "m15_summed_range_r",
    "m15_close_increment_reversal_rate",
    "m30_directional_net_displacement_r",
    "m30_close_path_length_r",
    "m30_path_efficiency",
    "m30_summed_range_r",
    "m30_close_increment_reversal_rate",
    "m30_directional_range_location",
    "m5_to_m30_mean_range_ratio",
    "m15_directional_wick_pressure",
)


@dataclass(frozen=True, slots=True)
class PreentryCausalM1PathState:
    symbol: str
    side: str
    entry_at: str
    risk_price: str
    feature_names: tuple[str, ...]
    vector: tuple[str, ...]
    feature_count: int
    feature_timestamp_max: str
    bars_used: int
    feature_timestamp_le_entry: bool = True
    entry_bar_used: bool = False
    future_bar_used: bool = False
    outcome_used: bool = False
    exit_used: bool = False
    mae_mfe_used: bool = False
    symbol_identity_in_vector: bool = False
    date_identity_in_vector: bool = False

    def __post_init__(self) -> None:
        if self.feature_names != FEATURE_NAMES:
            raise ValueError("V40 feature-name contract drift")
        if len(self.vector) != len(FEATURE_NAMES):
            raise ValueError("V40 path vector dimension drift")
        if self.feature_count != len(FEATURE_NAMES):
            raise ValueError("V40 feature_count mismatch")
        if self.bars_used != LOOKBACK_MINUTES:
            raise ValueError("V40 must use exactly 30 pre-entry M1 bars")
        if not self.feature_timestamp_le_entry:
            raise ValueError("V40 feature timestamp exceeds entry")
        if (
            self.entry_bar_used
            or self.future_bar_used
            or self.outcome_used
            or self.exit_used
            or self.mae_mfe_used
            or self.symbol_identity_in_vector
            or self.date_identity_in_vector
        ):
            raise ValueError("V40 causal/governance invariant violated")


def _positive(value: Decimal, *, name: str) -> Decimal:
    if value <= 0:
        raise ValueError(f"V40 {name} must be positive")
    return value


def _sign(value: Decimal) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _reversal_rate(increments: tuple[Decimal, ...]) -> Decimal:
    directions = tuple(_sign(value) for value in increments if value != 0)
    if len(directions) < 2:
        return Decimal("0")
    reversals = sum(
        left != right
        for left, right in zip(directions[:-1], directions[1:], strict=True)
    )
    return Decimal(reversals) / Decimal(len(directions) - 1)


def _horizon_features(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    directional_sign: Decimal,
    risk: Decimal,
) -> tuple[Decimal, ...]:
    if not bars:
        raise ValueError("V40 horizon cannot be empty")
    points = (bars[0].open, *(bar.close for bar in bars))
    increments = tuple(
        right - left
        for left, right in zip(points[:-1], points[1:], strict=True)
    )
    net = points[-1] - points[0]
    path_length = sum((abs(value) for value in increments), Decimal("0"))
    range_sum = sum((bar.range for bar in bars), Decimal("0"))
    efficiency = (
        Decimal("0")
        if path_length == 0
        else abs(net) / path_length
    )
    return (
        directional_sign * net / risk,
        path_length / risk,
        efficiency,
        range_sum / risk,
        _reversal_rate(increments),
    )


def build_path_state(
    *,
    symbol: str,
    side: str,
    entry_at: datetime,
    risk_price: Decimal,
    bars: tuple[CapitalizerM1Bar, ...],
) -> PreentryCausalM1PathState:
    """Build the frozen 18D path state from exactly 30 completed M1 bars."""

    if entry_at.tzinfo is None or entry_at.utcoffset() is None:
        raise ValueError("V40 entry timestamp must be timezone-aware")
    risk = _positive(risk_price, name="structural risk")
    if len(bars) != LOOKBACK_MINUTES:
        raise ValueError("V40 requires exactly 30 M1 bars")
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("V40 M1 symbol mismatch")

    expected_start = entry_at - timedelta(minutes=LOOKBACK_MINUTES)
    if bars[0].opened_at != expected_start:
        raise ValueError("V40 path does not start exactly T-30m")
    if bars[-1].closed_at != entry_at:
        raise ValueError("V40 path does not end exactly at entry")
    for previous, current in zip(bars[:-1], bars[1:], strict=True):
        if previous.closed_at != current.opened_at:
            raise ValueError("V40 pre-entry M1 path contains a gap")
    if any(bar.opened_at >= entry_at for bar in bars):
        raise ValueError("V40 attempted to use entry/future bar")
    if any(bar.closed_at > entry_at for bar in bars):
        raise ValueError("V40 attempted to use future M1 close")

    if side == "LONG":
        directional_sign = Decimal("1")
    elif side == "SHORT":
        directional_sign = Decimal("-1")
    else:
        raise ValueError("V40 side must be LONG or SHORT")

    values: list[Decimal] = []
    for horizon in HORIZONS:
        values.extend(
            _horizon_features(
                bars[-horizon:],
                directional_sign=directional_sign,
                risk=risk,
            )
        )

    high_30 = max(bar.high for bar in bars)
    low_30 = min(bar.low for bar in bars)
    span_30 = _positive(high_30 - low_30, name="30m range")
    last_close = bars[-1].close
    range_location = (
        (last_close - low_30) / span_30
        if side == "LONG"
        else (high_30 - last_close) / span_30
    )

    mean_range_5 = (
        sum((bar.range for bar in bars[-5:]), Decimal("0"))
        / Decimal("5")
    )
    mean_range_30 = (
        sum((bar.range for bar in bars), Decimal("0"))
        / Decimal("30")
    )
    range_ratio = mean_range_5 / _positive(
        mean_range_30,
        name="30m mean range",
    )

    wick_bars = bars[-15:]
    favorable_minus_adverse = Decimal("0")
    wick_denominator = Decimal("0")
    for bar in wick_bars:
        lower = min(bar.open, bar.close) - bar.low
        upper = bar.high - max(bar.open, bar.close)
        favorable_minus_adverse += (
            lower - upper
            if side == "LONG"
            else upper - lower
        )
        wick_denominator += bar.range
    wick_pressure = favorable_minus_adverse / _positive(
        wick_denominator,
        name="15m wick denominator",
    )

    values.extend((range_location, range_ratio, wick_pressure))
    if len(values) != len(FEATURE_NAMES):
        raise ValueError("V40 internal feature dimension drift")
    if any(not value.is_finite() for value in values):
        raise ValueError("V40 path state contains non-finite value")

    return PreentryCausalM1PathState(
        symbol=symbol,
        side=side,
        entry_at=entry_at.isoformat(),
        risk_price=str(risk),
        feature_names=FEATURE_NAMES,
        vector=tuple(str(value) for value in values),
        feature_count=len(FEATURE_NAMES),
        feature_timestamp_max=max(bar.closed_at for bar in bars).isoformat(),
        bars_used=len(bars),
    )


def from_json_dict(payload: dict[str, Any]) -> PreentryCausalM1PathState:
    normalized = dict(payload)
    for field in ("feature_names", "vector"):
        value = normalized.get(field)
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"V40 {field} JSON field must be a sequence")
        if any(not isinstance(item, str) for item in value):
            raise ValueError(f"V40 {field} JSON items must be strings")
        normalized[field] = tuple(value)
    return PreentryCausalM1PathState(**normalized)


def as_json_dict(row: PreentryCausalM1PathState) -> dict[str, Any]:
    return asdict(row)
