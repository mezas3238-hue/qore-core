"""Composed source-faithful trader engine for QORE Capitalizer V2.

This is the pre-Risk methodology engine. It combines:
- Cognitive gate decision;
- source session context;
- higher-timeframe direction;
- either H1/M15/M1 fractal alignment or Failure-to-Manipulate continuation;
- protected swing invalidation;
- structural/HTF target;
- source strategy grammar;
- structural trade plan.

It never executes or sizes a position and never uses terminal outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_dual_source_entry_acceptance_v1 import (
    CapitalizerDualSourceEntryAcceptance,
    CapitalizerEntryAcceptanceState,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerFailureToManipulateObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasObservation,
    CapitalizerDailyBiasResolution,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    CapitalizerFractalAlignmentObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerSourceDirection,
    CapitalizerStructuralTargetObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionAssessment,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    SOURCE_STRATEGY_GRAMMAR_ID,
    CapitalizerSourceEntryRoute,
    CapitalizerSourceStrategyAssessment,
    CapitalizerSourceStrategyDecision,
    CapitalizerSourceStrategyFacts,
    assess_source_strategy,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
    CapitalizerSourceTradePlan,
    CapitalizerSourceTradePlanFacts,
    build_source_trade_plan,
)


def _direction_for_side(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


@dataclass(frozen=True, slots=True)
class CapitalizerSourceTraderEngineFacts:
    symbol: str
    side: CapitalizerSide
    route: CapitalizerSourceEntryRoute
    cognitive_gate_decision: CapitalizerCognitiveGateDecision
    source_session: CapitalizerSourceSessionAssessment
    daily_bias: CapitalizerDailyBiasObservation
    entry_price: Decimal
    protected_swing: CapitalizerProtectedSwingObservation
    structural_target: CapitalizerStructuralTargetObservation
    target_kind: CapitalizerSourceTargetKind
    fractal_alignment: CapitalizerFractalAlignmentObservation | None = None
    failure_to_manipulate: CapitalizerFailureToManipulateObservation | None = None
    dual_source_entry_acceptance: CapitalizerDualSourceEntryAcceptance | None = None
    contradictions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("source trader engine symbol must be uppercase")
        if not isinstance(self.entry_price, Decimal) or not self.entry_price.is_finite():
            raise ValueError("source trader engine entry price must be finite Decimal")
        if self.route is CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION:
            if self.fractal_alignment is None:
                raise ValueError("fractal route requires fractal alignment observation")
            if self.failure_to_manipulate is not None:
                raise ValueError("fractal route cannot carry FTM observation")
        else:
            if self.failure_to_manipulate is None:
                raise ValueError("FTM route requires Failure-to-Manipulate observation")
            if self.fractal_alignment is not None:
                raise ValueError("FTM route cannot carry fractal alignment observation")


@dataclass(frozen=True, slots=True)
class CapitalizerSourceTraderEngineAssessment:
    symbol: str
    route: CapitalizerSourceEntryRoute
    strategy_assessment: CapitalizerSourceStrategyAssessment
    trade_plan: CapitalizerSourceTradePlan | None
    passes_to_qore_risk: bool
    reasons: tuple[str, ...]
    outcome_aware: bool = False
    executes_trade: bool = False
    sizes_position: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.outcome_aware:
            raise ValueError("source trader engine cannot use terminal outcomes")
        if self.executes_trade or self.sizes_position or self.grants_capital_authority:
            raise ValueError("source trader engine stops before QORE Risk/execution")
        eligible = (
            self.strategy_assessment.decision
            is CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK
        )
        if self.passes_to_qore_risk != eligible:
            raise ValueError("QORE Risk handoff must match source strategy eligibility")
        if eligible != (self.trade_plan is not None):
            raise ValueError("eligible source strategy requires exactly one trade plan")


def _reject(
    *,
    facts: CapitalizerSourceTraderEngineFacts,
    reason: str,
) -> CapitalizerSourceTraderEngineAssessment:
    assessment = CapitalizerSourceStrategyAssessment(
        grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
        symbol=facts.symbol,
        route=facts.route,
        decision=CapitalizerSourceStrategyDecision.REJECT,
        reasons=(reason,),
    )
    return CapitalizerSourceTraderEngineAssessment(
        symbol=facts.symbol,
        route=facts.route,
        strategy_assessment=assessment,
        trade_plan=None,
        passes_to_qore_risk=False,
        reasons=assessment.reasons,
    )


def assess_source_trader_engine(
    facts: CapitalizerSourceTraderEngineFacts,
) -> CapitalizerSourceTraderEngineAssessment:
    """Compose reviewed source observations into one pre-Risk trader decision."""

    intended_direction = _direction_for_side(facts.side)
    htf_aligned = (
        facts.daily_bias.resolution is CapitalizerDailyBiasResolution.CONFIRMED
        and facts.daily_bias.direction is intended_direction
    )
    protected_available = (
        facts.protected_swing.confirmed
        and facts.protected_swing.direction is intended_direction
    )
    target_available = (
        facts.structural_target.valid
        and facts.structural_target.direction is intended_direction
    )

    if facts.side is CapitalizerSide.LONG:
        stop_geometry_valid = facts.protected_swing.swing_price < facts.entry_price
    else:
        stop_geometry_valid = facts.protected_swing.swing_price > facts.entry_price

    if not stop_geometry_valid:
        return _reject(facts=facts, reason="PROTECTED_SWING_GEOMETRY_INVALID")
    if not target_available:
        return _reject(facts=facts, reason="STRUCTURAL_TARGET_INVALID_OR_CONSUMED")

    if facts.route is CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION:
        alignment = facts.fractal_alignment
        if alignment is None:
            raise AssertionError("validated fractal alignment unexpectedly missing")
        strategy_facts = CapitalizerSourceStrategyFacts(
            symbol=facts.symbol,
            route=facts.route,
            cognitive_gate_decision=facts.cognitive_gate_decision,
            source_session_context_resolved=facts.source_session.resolved,
            source_session_context_eligible=facts.source_session.eligible,
            higher_timeframe_bias_aligned=htf_aligned,
            structural_liquidity_objective_available=target_available,
            target_is_higher_timeframe_or_structural=target_available,
            protected_swing_available=protected_available,
            hourly_expansion_bias_confirmed=alignment.h1_closure_confirmed,
            m15_swing_structure_confirmed=alignment.m15_cisd_confirmed,
            m1_continuation_confirmed=alignment.m1_protected_swing_confirmed,
            contradictions=facts.contradictions,
        )
    else:
        ftm = facts.failure_to_manipulate
        if ftm is None:
            raise AssertionError("validated FTM observation unexpectedly missing")
        strategy_facts = CapitalizerSourceStrategyFacts(
            symbol=facts.symbol,
            route=facts.route,
            cognitive_gate_decision=facts.cognitive_gate_decision,
            source_session_context_resolved=facts.source_session.resolved,
            source_session_context_eligible=facts.source_session.eligible,
            higher_timeframe_bias_aligned=htf_aligned and ftm.higher_timeframe_bias_aligned,
            structural_liquidity_objective_available=target_available,
            target_is_higher_timeframe_or_structural=target_available,
            protected_swing_available=protected_available,
            liquidity_level_taken=ftm.level_taken,
            expected_reversal_failed_to_confirm=(
                ftm.post_sweep_closure_observed
                and not ftm.expected_reversal_cisd_confirmed
            ),
            continuation_structure_confirmed=ftm.continuation_protected_swing_confirmed,
            candle_closure_confirmation_complete=ftm.post_sweep_closure_observed,
            contradictions=facts.contradictions,
        )

    strategy = assess_source_strategy(strategy_facts)
    if strategy.decision is not CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK:
        return CapitalizerSourceTraderEngineAssessment(
            symbol=facts.symbol,
            route=facts.route,
            strategy_assessment=strategy,
            trade_plan=None,
            passes_to_qore_risk=False,
            reasons=strategy.reasons,
        )

    entry_gate = facts.dual_source_entry_acceptance
    if entry_gate is None:
        gate_strategy = CapitalizerSourceStrategyAssessment(
            grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
            symbol=facts.symbol,
            route=facts.route,
            decision=CapitalizerSourceStrategyDecision.WAIT,
            reasons=("DUAL_SOURCE_ENTRY_ACCEPTANCE_REQUIRED",),
        )
        return CapitalizerSourceTraderEngineAssessment(
            symbol=facts.symbol,
            route=facts.route,
            strategy_assessment=gate_strategy,
            trade_plan=None,
            passes_to_qore_risk=False,
            reasons=gate_strategy.reasons,
        )

    if not entry_gate.passes_to_qore_risk:
        gate_decision = (
            CapitalizerSourceStrategyDecision.REJECT
            if entry_gate.state is CapitalizerEntryAcceptanceState.REJECT
            else CapitalizerSourceStrategyDecision.WAIT
        )
        gate_strategy = CapitalizerSourceStrategyAssessment(
            grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
            symbol=facts.symbol,
            route=facts.route,
            decision=gate_decision,
            reasons=tuple(
                f"ENTRY_GATE:{reason}" for reason in entry_gate.reasons
            ),
        )
        return CapitalizerSourceTraderEngineAssessment(
            symbol=facts.symbol,
            route=facts.route,
            strategy_assessment=gate_strategy,
            trade_plan=None,
            passes_to_qore_risk=False,
            reasons=gate_strategy.reasons,
        )

    plan = build_source_trade_plan(
        CapitalizerSourceTradePlanFacts(
            symbol=facts.symbol,
            side=facts.side,
            route=facts.route,
            entry_price=facts.entry_price,
            protected_swing_price=facts.protected_swing.swing_price,
            structural_target_price=facts.structural_target.target_price,
            target_kind=facts.target_kind,
            strategy_assessment=strategy,
        )
    )
    return CapitalizerSourceTraderEngineAssessment(
        symbol=facts.symbol,
        route=facts.route,
        strategy_assessment=strategy,
        trade_plan=plan,
        passes_to_qore_risk=True,
        reasons=strategy.reasons,
    )
