from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    CapitalizerSourceEntryRoute,
    CapitalizerSourceStrategyDecision,
    CapitalizerSourceStrategyFacts,
    assess_source_strategy,
)


def _base(route: CapitalizerSourceEntryRoute) -> dict[str, object]:
    return {
        "symbol": "EURUSD",
        "route": route,
        "cognitive_gate_decision": CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
        "source_session_context_eligible": True,
        "higher_timeframe_bias_aligned": True,
        "structural_liquidity_objective_available": True,
        "target_is_higher_timeframe_or_structural": True,
        "protected_swing_available": True,
    }


def test_fractal_scalp_requires_h1_m15_m1_sequence() -> None:
    facts = CapitalizerSourceStrategyFacts(
        **_base(CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION),
        hourly_expansion_bias_confirmed=True,
        m15_swing_structure_confirmed=True,
        m1_continuation_confirmed=True,
    )

    result = assess_source_strategy(facts)

    assert result.decision is CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK
    assert result.executes_trade is False
    assert result.sizes_position is False
    assert result.grants_capital_authority is False
    assert result.outcome_aware is False
    assert result.numeric_score_used is False


def test_fractal_scalp_waits_for_missing_lower_timeframe_confirmation() -> None:
    facts = CapitalizerSourceStrategyFacts(
        **_base(CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION),
        hourly_expansion_bias_confirmed=True,
        m15_swing_structure_confirmed=True,
        m1_continuation_confirmed=False,
    )

    result = assess_source_strategy(facts)

    assert result.decision is CapitalizerSourceStrategyDecision.WAIT
    assert result.reasons == ("M1_CONTINUATION_NOT_CONFIRMED",)


def test_failure_to_manipulate_requires_actual_failed_reversal_and_continuation() -> None:
    incomplete = CapitalizerSourceStrategyFacts(
        **_base(CapitalizerSourceEntryRoute.FAILURE_TO_MANIPULATE_CONTINUATION),
        liquidity_level_taken=True,
        candle_closure_confirmation_complete=True,
        expected_reversal_failed_to_confirm=False,
        continuation_structure_confirmed=False,
    )
    complete = CapitalizerSourceStrategyFacts(
        **_base(CapitalizerSourceEntryRoute.FAILURE_TO_MANIPULATE_CONTINUATION),
        liquidity_level_taken=True,
        candle_closure_confirmation_complete=True,
        expected_reversal_failed_to_confirm=True,
        continuation_structure_confirmed=True,
    )

    waiting = assess_source_strategy(incomplete)
    eligible = assess_source_strategy(complete)

    assert waiting.decision is CapitalizerSourceStrategyDecision.WAIT
    assert "EXPECTED_REVERSAL_HAS_NOT_FAILED" in waiting.reasons
    assert "CONTINUATION_STRUCTURE_NOT_CONFIRMED" in waiting.reasons
    assert eligible.decision is CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK


def test_source_strategy_rejects_unsourced_context_even_when_entry_sequence_exists() -> None:
    base = _base(CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION)
    base["source_session_context_eligible"] = False
    facts = CapitalizerSourceStrategyFacts(
        **base,
        hourly_expansion_bias_confirmed=True,
        m15_swing_structure_confirmed=True,
        m1_continuation_confirmed=True,
    )

    result = assess_source_strategy(facts)

    assert result.decision is CapitalizerSourceStrategyDecision.REJECT
    assert "OUTSIDE_SOURCE_SESSION_CONTEXT" in result.reasons


def test_cognitive_abstain_cannot_be_resurrected_by_strategy() -> None:
    base = _base(CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION)
    base["cognitive_gate_decision"] = CapitalizerCognitiveGateDecision.ABSTAIN
    facts = CapitalizerSourceStrategyFacts(
        **base,
        hourly_expansion_bias_confirmed=True,
        m15_swing_structure_confirmed=True,
        m1_continuation_confirmed=True,
    )

    result = assess_source_strategy(facts)

    assert result.decision is CapitalizerSourceStrategyDecision.REJECT
    assert result.reasons == ("COGNITIVE_GATE_ABSTAIN",)
