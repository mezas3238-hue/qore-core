"""VT08 B R17 — V3 source-family separation & three-level stop firewall.

Only original TTrades M30→M3 intraday-reversal example is represented.
Never promote generic protected-swing or dealing-range EQ to the specific
example's EQ+breaker stop. No trade permission; no alpha strategy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.vt08_b_r16_owner_scope_no_alpha_v1 import (
    audit_frozen_source_program_scope,
    no_excluded_alpha_lineage,
)

EQ_C2_SOURCE = "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/"
EQ_DEALING_SOURCE = (
    "https://ttrades.com/understanding-dealing-ranges-in-trading-get-better-risk-reward/"
)
SPECIFIC_STOP_SOURCE = (
    "https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-"
    "time-frames-for-precision-entries/"
)
POS_STOP_SOURCE = "https://ttrades.com/positional-entries-enter-before-the-expansion/"
PS_STOP_SOURCE = (
    "https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/"
)
PROGRAM = "VT08_TTRADES_CURRENT"


class EqNamespace(StrEnum):
    FRACTAL_C2_CANDLE = "FRACTAL_C2_CANDLE_EQ"
    DEALING_RANGE = "DEALING_RANGE_EQ"


class StopFamily(StrEnum):
    M30_M3_REVERSAL_EXAMPLE = "SPECIFIC_M30_M3_REVERSAL_EXAMPLE"
    GENERIC_POSITIONAL = "GENERIC_TTRADES_POSITIONAL_OTHER_EXAMPLE"


@dataclass(frozen=True, slots=True)
class SourceLevel:
    """Research evidence only; flag never confers authority by itself."""

    price: Decimal
    available_at: datetime
    bar_id: str
    source_adjudicated: bool = False

    def __post_init__(self) -> None:
        if (
            self.price <= 0
            or not self.price.is_finite()
            or self.available_at.tzinfo is None
            or not self.bar_id
        ):
            raise ValueError("R17 level requires positive price, UTC clock and bar ID")
        no_excluded_alpha_lineage(self.bar_id)


def c2_candle_eq(
    *, candle_open: Decimal, candle_high: Decimal,
    candle_low: Decimal, candle_close: Decimal,
    reference_swing_direction: str | None,
) -> dict[str, object]:
    """Article 2026-10-10 C2 candle branch; not the dealing-range midpoint."""
    if not (
        0 < candle_low <= min(candle_open, candle_close)
        <= max(candle_open, candle_close) <= candle_high
        and candle_low < candle_high
    ):
        raise ValueError("R17 invalid C2 OHLC")
    branch = None
    if reference_swing_direction not in (None, "BULLISH", "BEARISH"):
        raise ValueError("R17 unknown reference swing direction")
    if candle_open == candle_close or reference_swing_direction is None:
        return {
            "namespace": EqNamespace.FRACTAL_C2_CANDLE.value,
            "conditional_eq": None,
            "source_branch": "D_UNRESOLVED_SWING_OR_DOJI",
            "actionable_trade_eq": None,
        }
    with_swing = (
        candle_close > candle_open
        if reference_swing_direction == "BULLISH"
        else candle_close < candle_open
    )
    if with_swing:
        lower, upper = candle_low, candle_high
        branch = "C2_WITH_SWING_FULL_RANGE"
    elif reference_swing_direction == "BULLISH":
        lower, upper = candle_low, candle_close
        branch = "C2_AGAINST_BULLISH_SWING_CLOSE_TO_LOW"
    else:
        lower, upper = candle_close, candle_high
        branch = "C2_AGAINST_BEARISH_SWING_CLOSE_TO_HIGH"
    return {
        "namespace": EqNamespace.FRACTAL_C2_CANDLE.value,
        "conditional_eq": str((lower + upper) / 2),
        "source_branch": branch,
        "actionable_trade_eq": None,
    }


def dealing_range_eq(*, swing_low: SourceLevel, swing_high: SourceLevel,
                     decision_at: datetime) -> dict[str, object]:
    """Geometric dealing-range midpoint; never aliased to the C2 stop EQ."""
    if decision_at.tzinfo is None:
        raise ValueError("R17 naive decision cutoff")
    now = decision_at.astimezone(UTC)
    if any(level.available_at.astimezone(UTC) > now
           for level in (swing_low, swing_high)):
        raise ValueError("R17 dealing-range witness from future")
    if swing_high.price <= swing_low.price:
        raise ValueError("R17 dealing-range bounds invalid")
    return {
        "namespace": EqNamespace.DEALING_RANGE.value,
        "conditional_eq": str((swing_high.price + swing_low.price) / 2),
        "actionable_trade_eq": None,
        "source_level_identity_approved": False,
    }


def inspect_stop_reference(
    *, stop: Decimal, decision_at: datetime,
    family: StopFamily, protected_swing_low: SourceLevel | None,
    c2_candle_eq_level: SourceLevel | None = None,
    breaker_low: SourceLevel | None = None,
    eq_namespace: EqNamespace = EqNamespace.FRACTAL_C2_CANDLE,
) -> dict[str, object]:
    """Numerical stop contract; STRICT witness provenance, zero trade authority.

    Generic positional: author-protected PS stop. Specific reversal example:
    requires the positional PS AND the specific example's EQ+breaker.
    These are *separate author passages*, not one invented 'universal 3' rule.
    """
    if decision_at.tzinfo is None:
        raise ValueError("R17 source cutoff must be timezone aware")
    if not isinstance(family, StopFamily):
        raise ValueError("R17 stop family must be explicit")
    if not stop.is_finite() or stop <= 0:
        raise ValueError("R17 stop must be positive and finite")
    now = decision_at.astimezone(UTC)
    necessary: dict[str, SourceLevel | None] = {
        "PROTECTED_SWING": protected_swing_low,
    }
    if family is StopFamily.M30_M3_REVERSAL_EXAMPLE:
        if eq_namespace is not EqNamespace.FRACTAL_C2_CANDLE:
            raise ValueError("R17 dealing-range EQ cannot masquerade as C2 EQ")
        necessary["M30_C2_EQ"] = c2_candle_eq_level
        necessary["BREAKER_LOW"] = breaker_low
    missing = [k for k, v in necessary.items() if v is None]
    if missing:
        status = "D_MISSING_SOURCE_IDENTITY"
    elif any(v.available_at.astimezone(UTC) > now
             for v in necessary.values() if v is not None):
        status = "REJECT_FUTURE_SOURCE_LEVEL"
    elif any(not v.source_adjudicated
             for v in necessary.values() if v is not None):
        status = "D_UNADJUDICATED_SOURCE_LEVELS"
    elif any(stop >= v.price for v in necessary.values() if v is not None):
        status = "REJECT_AUTHOR_SOURCE_STOP_RELATION"
    else:
        status = "NUMERIC_RELATION_COMPATIBLE_ONLY"
    return {
        "program": PROGRAM,
        "family": family.value,
        "status": status,
        "missing_levels": missing,
        "stop_relation": (
            "STOP_BELOW_AUTHENTIC_PS_AND_M30_EQ_AND_BREAKER"
            if family is StopFamily.M30_M3_REVERSAL_EXAMPLE
            else "STOP_BELOW_AUTHENTIC_PS"
        ),
        "source_only": True,
        "author_complete": False,
        "cognitive_admitted": False,
        "authorized_orders": 0,
    }


def audit_original_owner_restriction(
    report: dict[str, object], *, market: str,
) -> dict[str, object]:
    """Carry approved R16 five-market frozen-source gate into V3 audit."""
    base = audit_frozen_source_program_scope(report, expected_market=market)
    return {
        "market": market,
        "frozen_vt08_cases": base["frozen_vt08_cases_verified"],
        "program": PROGRAM,
        "source_contract": "V3_AUTHOR_EQ_DISTINCT_FROM_DEALING_EQ_STOP_FAMILY",
        "model_family_stop_known": True,
        "source_selected_eq_proven": False,
        "source_protected_swing_proven": False,
        "source_breaker_low_proven": False,
        "source_poi_proven": False,
        "source_target_selected": False,
        "author_complete": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "qore_alpha_admitted": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
    }
