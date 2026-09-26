"""Deterministic source-faithful strategy grammar for QORE Capitalizer V2.

ICT supplies time/context, higher-timeframe directional framing and liquidity objectives.
TTrades supplies the H1 -> M15 -> M1 scalp execution sequence plus a separately identified
Failure-to-Manipulate continuation route.

This grammar cannot place trades, size risk, mutate targets/stops online, or claim edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)

SOURCE_STRATEGY_GRAMMAR_ID = "QORE_CAPITALIZER_SOURCE_STRATEGY_GRAMMAR_V2"


class CapitalizerSourceEntryRoute(StrEnum):
    FRACTAL_SCALP_CONTINUATION = "FRACTAL_SCALP_CONTINUATION"
    FAILURE_TO_MANIPULATE_CONTINUATION = "FAILURE_TO_MANIPULATE_CONTINUATION"


class CapitalizerSourceStrategyDecision(StrEnum):
    ELIGIBLE_FOR_QORE_RISK = "ELIGIBLE_FOR_QORE_RISK"
    WAIT = "WAIT"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class CapitalizerSourceStrategyFacts:
    symbol: str
    route: CapitalizerSourceEntryRoute
    cognitive_gate_decision: CapitalizerCognitiveGateDecision

    source_session_context_resolved: bool
    source_session_context_eligible: bool
    higher_timeframe_bias_aligned: bool
    structural_liquidity_objective_available: bool
    target_is_higher_timeframe_or_structural: bool
    protected_swing_available: bool

    hourly_expansion_bias_confirmed: bool = False
    m15_swing_structure_confirmed: bool = False
    m1_continuation_confirmed: bool = False

    liquidity_level_taken: bool = False
    expected_reversal_failed_to_confirm: bool = False
    continuation_structure_confirmed: bool = False
    candle_closure_confirmation_complete: bool = False

    contradictions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("strategy symbol must be non-empty uppercase")


@dataclass(frozen=True, slots=True)
class CapitalizerSourceStrategyAssessment:
    grammar_id: str
    symbol: str
    route: CapitalizerSourceEntryRoute
    decision: CapitalizerSourceStrategyDecision
    reasons: tuple[str, ...]
    source_faithful_path_only: bool = True
    outcome_aware: bool = False
    numeric_score_used: bool = False
    executes_trade: bool = False
    sizes_position: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grammar_id != SOURCE_STRATEGY_GRAMMAR_ID:
            raise ValueError("source strategy grammar identity is frozen")
        if not self.reasons:
            raise ValueError("strategy assessment requires explicit reasons")
        if not self.source_faithful_path_only:
            raise ValueError("Capitalizer V2 cannot add unsourced entry paths")
        if self.outcome_aware:
            raise ValueError("source strategy grammar cannot use future outcomes")
        if self.numeric_score_used:
            raise ValueError("source strategy grammar cannot replace source logic with score")
        if self.executes_trade or self.sizes_position or self.grants_capital_authority:
            raise ValueError("source strategy grammar stops before QORE Risk/execution")


def assess_source_strategy(
    facts: CapitalizerSourceStrategyFacts,
) -> CapitalizerSourceStrategyAssessment:
    """Apply the reviewed source sequence without economic optimization."""

    if facts.cognitive_gate_decision is CapitalizerCognitiveGateDecision.ABSTAIN:
        return CapitalizerSourceStrategyAssessment(
            grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
            symbol=facts.symbol,
            route=facts.route,
            decision=CapitalizerSourceStrategyDecision.REJECT,
            reasons=("COGNITIVE_GATE_ABSTAIN",),
        )
    if facts.cognitive_gate_decision is CapitalizerCognitiveGateDecision.WAIT:
        return CapitalizerSourceStrategyAssessment(
            grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
            symbol=facts.symbol,
            route=facts.route,
            decision=CapitalizerSourceStrategyDecision.WAIT,
            reasons=("COGNITIVE_GATE_WAIT",),
        )

    hard_reasons: list[str] = []
    if facts.contradictions:
        hard_reasons.extend(f"CONTRADICTION:{item}" for item in facts.contradictions)
    if facts.source_session_context_resolved and not facts.source_session_context_eligible:
        hard_reasons.append("OUTSIDE_SOURCE_SESSION_CONTEXT")
    if not facts.higher_timeframe_bias_aligned:
        hard_reasons.append("HIGHER_TIMEFRAME_BIAS_NOT_ALIGNED")
    if not facts.structural_liquidity_objective_available:
        hard_reasons.append("STRUCTURAL_LIQUIDITY_OBJECTIVE_UNAVAILABLE")
    if not facts.target_is_higher_timeframe_or_structural:
        hard_reasons.append("TARGET_NOT_SOURCE_STRUCTURAL")
    if not facts.protected_swing_available:
        hard_reasons.append("PROTECTED_SWING_UNAVAILABLE")

    if hard_reasons:
        return CapitalizerSourceStrategyAssessment(
            grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
            symbol=facts.symbol,
            route=facts.route,
            decision=CapitalizerSourceStrategyDecision.REJECT,
            reasons=tuple(dict.fromkeys(hard_reasons)),
        )

    wait_reasons: list[str] = []
    if not facts.source_session_context_resolved:
        wait_reasons.append("SOURCE_SESSION_CONTEXT_UNRESOLVED")
    if facts.route is CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION:
        if not facts.hourly_expansion_bias_confirmed:
            wait_reasons.append("H1_EXPANSION_BIAS_NOT_CONFIRMED")
        if not facts.m15_swing_structure_confirmed:
            wait_reasons.append("M15_SWING_STRUCTURE_NOT_CONFIRMED")
        if not facts.m1_continuation_confirmed:
            wait_reasons.append("M1_CONTINUATION_NOT_CONFIRMED")
    else:
        if not facts.liquidity_level_taken:
            wait_reasons.append("LIQUIDITY_LEVEL_NOT_TAKEN")
        if not facts.candle_closure_confirmation_complete:
            wait_reasons.append("CANDLE_CLOSURE_CONFIRMATION_INCOMPLETE")
        if not facts.expected_reversal_failed_to_confirm:
            wait_reasons.append("EXPECTED_REVERSAL_HAS_NOT_FAILED")
        if not facts.continuation_structure_confirmed:
            wait_reasons.append("CONTINUATION_STRUCTURE_NOT_CONFIRMED")

    if wait_reasons:
        return CapitalizerSourceStrategyAssessment(
            grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
            symbol=facts.symbol,
            route=facts.route,
            decision=CapitalizerSourceStrategyDecision.WAIT,
            reasons=tuple(wait_reasons),
        )

    return CapitalizerSourceStrategyAssessment(
        grammar_id=SOURCE_STRATEGY_GRAMMAR_ID,
        symbol=facts.symbol,
        route=facts.route,
        decision=CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK,
        reasons=(
            "COGNITIVE_GATE_PASSED",
            "SOURCE_SESSION_CONTEXT_PASSED",
            "HIGHER_TIMEFRAME_BIAS_ALIGNED",
            "STRUCTURAL_LIQUIDITY_OBJECTIVE_AVAILABLE",
            "SOURCE_ENTRY_SEQUENCE_CONFIRMED",
            "PROTECTED_SWING_AVAILABLE",
            "STRUCTURAL_TARGET_AVAILABLE",
        ),
    )
