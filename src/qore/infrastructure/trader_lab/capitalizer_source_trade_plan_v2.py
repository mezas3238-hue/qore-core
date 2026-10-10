"""Source-faithful trade-plan boundary for QORE Capitalizer V2.

A strategy candidate may be source-eligible, but replay needs an explicit planned expression:
side, structural invalidation/protected swing, stop at that anchor, and a structural/HTF target.
The plan is still pre-Risk and cannot execute or size.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    CapitalizerSourceEntryRoute,
    CapitalizerSourceStrategyAssessment,
    CapitalizerSourceStrategyDecision,
)


class CapitalizerSourceTargetKind(StrEnum):
    RECENT_DAILY_HIGH_LOW = "RECENT_DAILY_HIGH_LOW"
    HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE = "HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE"


@dataclass(frozen=True, slots=True)
class CapitalizerSourceTradePlanFacts:
    symbol: str
    side: CapitalizerSide
    route: CapitalizerSourceEntryRoute
    entry_price: Decimal
    protected_swing_price: Decimal
    structural_target_price: Decimal
    target_kind: CapitalizerSourceTargetKind
    strategy_assessment: CapitalizerSourceStrategyAssessment

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("trade-plan symbol must be uppercase")
        for value in (
            self.entry_price,
            self.protected_swing_price,
            self.structural_target_price,
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError("trade-plan prices must be finite Decimal values")
        if self.route is not self.strategy_assessment.route:
            raise ValueError("trade-plan route must match strategy assessment")
        if self.symbol != self.strategy_assessment.symbol:
            raise ValueError("trade-plan symbol must match strategy assessment")


@dataclass(frozen=True, slots=True)
class CapitalizerSourceTradePlan:
    symbol: str
    side: CapitalizerSide
    route: CapitalizerSourceEntryRoute
    entry_price: Decimal
    initial_stop_price: Decimal
    target_price: Decimal
    target_kind: CapitalizerSourceTargetKind
    stop_anchor: str = "LOGICAL_PROTECTED_SWING"
    target_anchor: str = "STRUCTURAL_OR_HIGHER_TIMEFRAME_OBJECTIVE"
    initial_stop_can_widen: bool = False
    fixed_r_target_invented: bool = False
    executes_trade: bool = False
    sizes_position: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.initial_stop_can_widen:
            raise ValueError("source trade plan cannot allow stop widening")
        if self.fixed_r_target_invented:
            raise ValueError("source trade plan cannot invent arbitrary fixed-R target")
        if self.executes_trade or self.sizes_position or self.grants_capital_authority:
            raise ValueError("source trade plan stops before QORE Risk/execution")
        if self.side is CapitalizerSide.LONG:
            if not self.initial_stop_price < self.entry_price < self.target_price:
                raise ValueError("LONG source plan requires stop < entry < target")
        else:
            if not self.target_price < self.entry_price < self.initial_stop_price:
                raise ValueError("SHORT source plan requires target < entry < stop")


def build_source_trade_plan(
    facts: CapitalizerSourceTradePlanFacts,
) -> CapitalizerSourceTradePlan:
    """Build a plan only after the complete source grammar says it is eligible."""

    if (
        facts.strategy_assessment.decision
        is not CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK
    ):
        raise ValueError("source trade plan requires ELIGIBLE_FOR_QORE_RISK assessment")

    return CapitalizerSourceTradePlan(
        symbol=facts.symbol,
        side=facts.side,
        route=facts.route,
        entry_price=facts.entry_price,
        initial_stop_price=facts.protected_swing_price,
        target_price=facts.structural_target_price,
        target_kind=facts.target_kind,
    )
