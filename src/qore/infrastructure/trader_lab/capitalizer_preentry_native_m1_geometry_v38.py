"""Causal pre-entry native-M1 geometry contract for Capitalizer V38.

This module is a contingency representation source. It does not score, filter,
admit, size, protect, or execute trades.

Every emitted feature must be fully knowable at or before the frozen entry
decision timestamp. Future M1 bars, terminal outcome, MAE/MFE, exit reason and
post-entry path are structurally absent from this contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)

IDENTITY = "QORE_CAPITALIZER_PREENTRY_NATIVE_M1_GEOMETRY_V38"
FEATURE_NAMES = (
    "m3_body_ratio",
    "m3_displacement_range_r",
    "m3_atr14_r",
    "distance_ob_proximal_to_mss_r",
    "m1_ob_width_r",
    "m1_fvg_width_r",
    "m1_ob_fvg_overlap_width_r",
    "m5_closeback_to_m3_mss_minutes",
    "m1_fvg_confirmation_lead_to_m3_mss_minutes",
    "fvg_confirmation_to_entry_minutes",
    "m5_closeback_to_entry_minutes",
    "stop_buffer_fraction_of_risk",
)


@dataclass(frozen=True, slots=True)
class PreentryNativeM1Geometry:
    symbol: str
    side: str
    entry_at: str
    m5_closeback_at: str
    m3_mss_confirmed_at: str
    m1_fvg_confirmed_at: str
    m1_ob_opened_at: str
    risk_price: str
    feature_names: tuple[str, ...]
    vector: tuple[str, ...]
    feature_count: int
    feature_timestamp_max: str
    feature_timestamp_le_entry: bool = True
    future_bar_used: bool = False
    outcome_used: bool = False
    mae_mfe_used: bool = False
    exit_reason_used: bool = False
    symbol_identity_in_vector: bool = False
    date_identity_in_vector: bool = False

    def __post_init__(self) -> None:
        if self.feature_names != FEATURE_NAMES:
            raise ValueError("V38 feature-name contract drift")
        if len(self.vector) != len(FEATURE_NAMES):
            raise ValueError("V38 geometry vector dimension drift")
        if self.feature_count != len(FEATURE_NAMES):
            raise ValueError("V38 feature_count mismatch")
        if not self.feature_timestamp_le_entry:
            raise ValueError("V38 feature timestamp exceeds entry decision")
        if (
            self.future_bar_used
            or self.outcome_used
            or self.mae_mfe_used
            or self.exit_reason_used
            or self.symbol_identity_in_vector
            or self.date_identity_in_vector
        ):
            raise ValueError("V38 causal/governance invariant violated")


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("V38 requires timezone-aware timestamps")
    return parsed


def _minutes(later: datetime, earlier: datetime) -> Decimal:
    if later < earlier:
        raise ValueError("V38 causal timestamp order violated")
    return Decimal(str((later - earlier).total_seconds())) / Decimal("60")


def _positive(value: Decimal, *, name: str) -> Decimal:
    if value <= 0:
        raise ValueError(f"V38 {name} must be positive")
    return value


def build_geometry(
    *,
    symbol: str,
    side: str,
    entry_at: datetime,
    entry_price: Decimal,
    stop_price: Decimal,
    stop_buffer_price: Decimal,
    m5_closeback_at: datetime,
    mss: v3.M3MssEvent,
    zone: v3.M1EntryZone,
) -> PreentryNativeM1Geometry:
    """Build one outcome-free geometry vector from causal setup objects."""

    risk = _positive(abs(entry_price - stop_price), name="risk")
    if stop_buffer_price < 0:
        raise ValueError("V38 stop buffer cannot be negative")

    timestamps = (
        m5_closeback_at,
        mss.confirmed_at,
        mss.displacement_closed_at,
        zone.ob_opened_at,
        zone.fvg_confirmed_at,
    )
    if any(
        stamp.tzinfo is None or stamp.utcoffset() is None
        for stamp in (*timestamps, entry_at)
    ):
        raise ValueError("V38 causal timestamps must be timezone-aware")
    if any(stamp > entry_at for stamp in timestamps):
        raise ValueError("V38 attempted to use post-entry setup evidence")
    if mss.displacement_closed_at > mss.confirmed_at:
        raise ValueError("V38 MSS confirmation precedes displacement close")
    if zone.fvg_confirmed_at < mss.displacement_opened_at:
        raise ValueError("V38 FVG confirmation precedes causal displacement")
    if zone.fvg_confirmed_at > mss.confirmed_at:
        raise ValueError("V38 causal-zone FVG cannot follow MSS confirmation")
    if zone.ob_opened_at >= entry_at:
        raise ValueError("V38 order block must predate entry")

    ob_width = _positive(zone.ob_high - zone.ob_low, name="OB width")
    fvg_width = _positive(zone.fvg_high - zone.fvg_low, name="FVG width")

    if side == "LONG":
        ob_proximal = zone.ob_high
    elif side == "SHORT":
        ob_proximal = zone.ob_low
    else:
        raise ValueError("V38 side must be LONG or SHORT")

    overlap_width = Decimal("0")
    if zone.overlap_low is not None or zone.overlap_high is not None:
        if zone.overlap_low is None or zone.overlap_high is None:
            raise ValueError("V38 incomplete OB/FVG overlap")
        if zone.overlap_high < zone.overlap_low:
            raise ValueError("V38 invalid OB/FVG overlap")
        overlap_width = zone.overlap_high - zone.overlap_low

    values = (
        mss.body_ratio,
        mss.displacement_range / risk,
        mss.atr14 / risk,
        abs(ob_proximal - mss.broken_swing_price) / risk,
        ob_width / risk,
        fvg_width / risk,
        overlap_width / risk,
        _minutes(mss.confirmed_at, m5_closeback_at),
        _minutes(mss.confirmed_at, zone.fvg_confirmed_at),
        _minutes(entry_at, zone.fvg_confirmed_at),
        _minutes(entry_at, m5_closeback_at),
        stop_buffer_price / risk,
    )
    if any(not value.is_finite() for value in values):
        raise ValueError("V38 geometry contains non-finite value")

    feature_timestamp_max = max(timestamps)
    return PreentryNativeM1Geometry(
        symbol=symbol,
        side=side,
        entry_at=entry_at.isoformat(),
        m5_closeback_at=m5_closeback_at.isoformat(),
        m3_mss_confirmed_at=mss.confirmed_at.isoformat(),
        m1_fvg_confirmed_at=zone.fvg_confirmed_at.isoformat(),
        m1_ob_opened_at=zone.ob_opened_at.isoformat(),
        risk_price=str(risk),
        feature_names=FEATURE_NAMES,
        vector=tuple(str(value) for value in values),
        feature_count=len(FEATURE_NAMES),
        feature_timestamp_max=feature_timestamp_max.isoformat(),
    )


def from_v3_trade(trade: v3.V3Trade) -> PreentryNativeM1Geometry:
    """Rehydrate the frozen geometry already retained by a V3 trade row."""

    entry_at = _aware(trade.entry_at)
    m5_closeback_at = _aware(trade.m5_closeback_at)
    m3_mss_at = _aware(trade.m3_mss_at)
    fvg_at = _aware(trade.m1_fvg_confirmed_at)
    ob_at = _aware(trade.m1_ob_opened_at)

    # V3Trade retains only aggregate MSS fields, enough for the geometry vector.
    mss = v3.M3MssEvent(
        side=CapitalizerSide(trade.side),
        confirmed_at=m3_mss_at,
        displacement_opened_at=m3_mss_at,
        displacement_closed_at=m3_mss_at,
        broken_swing_price=Decimal(trade.m3_broken_swing_price),
        cisd_boundary=Decimal(trade.m3_cisd_boundary),
        body_ratio=Decimal(trade.m3_body_ratio),
        atr14=Decimal(trade.m3_atr14),
        displacement_range=Decimal(trade.m3_displacement_range),
    )
    zone = v3.M1EntryZone(
        ob_opened_at=ob_at,
        ob_low=Decimal(trade.m1_ob_low),
        ob_high=Decimal(trade.m1_ob_high),
        fvg_confirmed_at=fvg_at,
        fvg_low=Decimal(trade.m1_fvg_low),
        fvg_high=Decimal(trade.m1_fvg_high),
        overlap_low=(
            max(Decimal(trade.m1_ob_low), Decimal(trade.m1_fvg_low))
            if trade.m1_ob_fvg_overlap
            else None
        ),
        overlap_high=(
            min(Decimal(trade.m1_ob_high), Decimal(trade.m1_fvg_high))
            if trade.m1_ob_fvg_overlap
            else None
        ),
    )
    return build_geometry(
        symbol=trade.symbol,
        side=trade.side,
        entry_at=entry_at,
        entry_price=Decimal(trade.entry_price),
        stop_price=Decimal(trade.stop_price),
        stop_buffer_price=Decimal(trade.stop_buffer_price),
        m5_closeback_at=m5_closeback_at,
        mss=mss,
        zone=zone,
    )


def as_json_dict(row: PreentryNativeM1Geometry) -> dict[str, Any]:
    return asdict(row)
