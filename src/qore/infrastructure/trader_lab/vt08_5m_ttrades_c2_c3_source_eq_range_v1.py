"""Research-only author-source EQ range selection for C2 and C3 closures.

TTrades 2026-10-10 clarification:
C2 closes WITH swing -> full candle; C2 closes AGAINST swing ->
close-to-extreme wick; C3 closure -> full candle. No order or bias
grant; closure/swing point/POI evidence must be independently validated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SOURCE_URL = "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/"


class EqRangeBasis(StrEnum):
    FULL_CANDLE_C2_WITH_SWING = "C2_FULL_WICK_TO_WICK_WITH_SWING"
    CLOSE_TO_EXTREME_C2_AGAINST_SWING = "C2_CLOSE_TO_EXTREME_AGAINST_SWING"
    FULL_CANDLE_C3 = "C3_FULL_WICK_TO_WICK_AFTER_CLOSURE"


@dataclass(frozen=True, slots=True)
class SourceEqObservation:
    source_candle: str
    intended_side: DemoTradingSetupSide
    evidence_closed_at: datetime
    lower_bound: Decimal
    upper_bound: Decimal
    eq: Decimal
    basis: EqRangeBasis
    research_only: bool = True
    source_complete_entry: bool = False

    def __post_init__(self) -> None:
        if self.evidence_closed_at.utcoffset() is None:
            raise ValueError("EQ source closure must be time aware")
        if not (self.lower_bound < self.upper_bound):
            raise ValueError("EQ source range must be positive")
        if self.eq != (self.lower_bound + self.upper_bound) / 2:
            raise ValueError("EQ midpoint not geometrically exact")
        if not self.research_only or self.source_complete_entry:
            raise ValueError("EQ does not authorize source setup or orders")

    def payload(self) -> dict[str, str | bool]:
        return {
            "source_candle": self.source_candle,
            "side": self.intended_side.value,
            "evidence_closed_at": self.evidence_closed_at.astimezone(UTC).isoformat(),
            "eq": str(self.eq),
            "lower_bound": str(self.lower_bound),
            "upper_bound": str(self.upper_bound),
            "range_basis": self.basis.value,
            "source_ref": SOURCE_URL,
            "research_only": True,
            "source_complete_entry": False,
        }


def source_eq_after_closure(
    candle: Vt08B01Bar,
    *,
    candle_label: str,
    intended_side: DemoTradingSetupSide,
    closure_adjudicated: bool,
    decision_at: datetime,
) -> SourceEqObservation | None:
    """Produce correct range only AFTER closure and verified context.

    No fallback to blanket (H+L)/2 if C2 is against confirmed swing;
    doji C2 remains UNKNOWN (author requires directional close).
    """
    if candle_label not in {"C2", "C3"}:
        raise ValueError("EQ requires closed C2 or C3 source label")
    if decision_at.utcoffset() is None or candle.closed_at.utcoffset() is None:
        raise ValueError("EQ requires timezone-aware source/decision")
    if candle.closed_at.astimezone(UTC) > decision_at.astimezone(UTC):
        raise ValueError("EQ cannot read unclosed higher timeframe candle")
    if candle.closed_at.astimezone(UTC) != (
        candle.opened_at.astimezone(UTC) + timedelta(hours=4)
    ):
        raise ValueError("C2/C3 H4 source must be complete")
    if not closure_adjudicated:
        return None
    if candle_label == "C3":
        lower, upper = candle.low, candle.high
        basis = EqRangeBasis.FULL_CANDLE_C3
    elif candle.close == candle.open:
        return None
    else:
        bullish = intended_side is DemoTradingSetupSide.LONG
        with_swing = (
            candle.close > candle.open if bullish
            else candle.close < candle.open
        )
        if with_swing:
            lower, upper = candle.low, candle.high
            basis = EqRangeBasis.FULL_CANDLE_C2_WITH_SWING
        else:
            lower, upper = (
                (candle.low, candle.close)
                if bullish
                else (candle.close, candle.high)
            )
            basis = EqRangeBasis.CLOSE_TO_EXTREME_C2_AGAINST_SWING
    if lower == upper:
        return None
    return SourceEqObservation(
        source_candle=candle_label,
        intended_side=intended_side,
        evidence_closed_at=candle.closed_at,
        lower_bound=lower,
        upper_bound=upper,
        eq=(lower + upper) / 2,
        basis=basis,
    )
