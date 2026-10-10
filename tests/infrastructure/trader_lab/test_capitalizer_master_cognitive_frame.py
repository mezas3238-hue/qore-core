from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_a1_full_frame_research_adapter import (
    A1CausalSettledMemory,
    A1FullFrameResearchDecision,
    A1SettledChosenTrade,
    A1SourceBinding,
    evaluate_full_frame_research_batch,
)
from qore.infrastructure.trader_lab.capitalizer_cognitive_explanation import (
    explain_all_candidates,
)
from qore.infrastructure.trader_lab.capitalizer_cognitive_pressure import (
    CapitalizerCognitivePressureFacts,
    assess_cognitive_pressure,
)
from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_context_brains import (
    CapitalizerMarketBrainState,
    CapitalizerSessionBrainState,
    CapitalizerSessionPhase,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketCausalGraph,
)
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_global_world_model import (
    CapitalizerGlobalWorldModel,
    CapitalizerMarketWorldState,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerAttentionState,
    CapitalizerCognitivePressure,
    CapitalizerHypothesisStage,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame import (
    CapitalizerCandidateCognitiveContext,
    build_master_cognitive_frame,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerDailyJourney,
    CapitalizerLossCause,
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_microstructure import (
    CapitalizerMicrostructureTrace,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerMarketPerceptionSnapshot,
    CapitalizerPerceptionFacts,
    assess_perception_integrity,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeHypothesis,
)


def _world(at: datetime) -> CapitalizerGlobalWorldModel:
    markets: list[CapitalizerMarketWorldState] = []
    for session in CapitalizerSession:
        for symbol in sorted(allowed_markets(session)):
            decision = symbol in {"AUDJPY", "USDJPY"}
            markets.append(
                CapitalizerMarketWorldState(
                    brain=CapitalizerMarketBrainState(
                        symbol=symbol,
                        session=session,
                        state_family_id="PRE_STRATEGY_STATE",
                        microstructure=CapitalizerMicrostructureTrace(
                            decision_at=at,
                            events=(),
                        ),
                    ),
                    attention=(
                        CapitalizerAttentionState.DECISION
                        if decision
                        else CapitalizerAttentionState.BACKGROUND
                    ),
                    knowledge=CapitalizerKnowledgeState.KNOWN,
                    hypothesis_stage=(
                        CapitalizerHypothesisStage.EXECUTABLE if decision else None
                    ),
                    hypothesis_id=f"H-{symbol}" if decision else None,
                    source_event_id=f"SRC-{symbol}" if decision else None,
                )
            )
    return CapitalizerGlobalWorldModel(
        observed_at=at,
        current_session=CapitalizerSession.ASIA,
        session_brain=CapitalizerSessionBrainState(
            session=CapitalizerSession.ASIA,
            phase=CapitalizerSessionPhase.ACTIVE,
        ),
        markets=tuple(markets),
        session_ledgers=(
            CapitalizerSessionLedger(CapitalizerSession.ASIA, executions=2),
            CapitalizerSessionLedger(CapitalizerSession.LONDON),
            CapitalizerSessionLedger(CapitalizerSession.NEW_YORK),
        ),
        journey=CapitalizerDailyJourney(),
        loss_memory=CapitalizerLossMemory(),
    )


def _perceptions(at: datetime) -> tuple[CapitalizerMarketPerceptionSnapshot, ...]:
    good = assess_perception_integrity(
        CapitalizerPerceptionFacts(
            quote_fresh=True,
            bars_complete=True,
            timestamps_ordered=True,
            session_clock_valid=True,
            provenance_valid=True,
            microstructure_complete=True,
        )
    )
    return tuple(
        CapitalizerMarketPerceptionSnapshot(
            symbol=symbol,
            observed_at=at,
            assessment=good,
        )
        for session in CapitalizerSession
        for symbol in sorted(allowed_markets(session))
    )


def _regimes(at: datetime) -> tuple[CapitalizerRegimeHypothesis, ...]:
    rows: list[CapitalizerRegimeHypothesis] = []
    for session in CapitalizerSession:
        for symbol in sorted(allowed_markets(session)):
            decision = symbol in {"AUDJPY", "USDJPY"}
            rows.append(
                CapitalizerRegimeHypothesis(
                    symbol=symbol,
                    observed_at=at,
                    family_id="RESEARCH_SUPPORTED_STATE" if decision else None,
                    causal_evidence=("CAUSAL_REGIME_EVIDENCE",) if decision else (),
                    contradictions=(),
                    knowledge=(
                        CapitalizerKnowledgeState.KNOWN
                        if decision
                        else CapitalizerKnowledgeState.UNKNOWN
                    ),
                )
            )
    return tuple(rows)


def _candidate_contexts(
    at: datetime,
) -> tuple[CapitalizerCandidateCognitiveContext, ...]:
    return tuple(
        CapitalizerCandidateCognitiveContext(
            symbol=symbol,
            observed_at=at,
            failure_state_fingerprint=None,
            evidence_provenance_complete=True,
            destination_context_known=True,
            destination_available=True,
            event_is_fresh=True,
            genuinely_new_causal_event=True,
            observation_tokens=(f"OBSERVED:{symbol}",),
        )
        for symbol in ("AUDJPY", "USDJPY")
    )


def test_master_frame_integrates_complete_pre_strategy_cognition() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    frame = build_master_cognitive_frame(
        world=_world(at),
        perceptions=_perceptions(at),
        regime_hypotheses=_regimes(at),
        cross_market_graph=CapitalizerCrossMarketCausalGraph(
            observed_at=at,
            edges=(),
        ),
        pressure_facts=CapitalizerCognitivePressureFacts(),
        candidate_contexts=_candidate_contexts(at),
    )

    assert len(frame.market_registry.symbols) == 9
    assert len(frame.perceptions) == 9
    assert len(frame.regimes) == 9
    assert frame.competition.available_slots == 1
    assert frame.competition.arbitration_required is True
    assert tuple(item.symbol for item in frame.candidate_evaluations) == (
        "AUDJPY",
        "USDJPY",
    )
    assert all(
        item.gate.decision is CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY
        for item in frame.candidate_evaluations
    )
    explanations = explain_all_candidates(frame)
    assert len(explanations) == 2
    assert all(item.free_form_reasoning_used is False for item in explanations)
    assert all(item.audit_record.decision is None for item in explanations)
    assert all(
        item.audit_record.cognitive_gate_decision
        is CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY
        for item in explanations
    )
    assert all(
        any(token.startswith("COGNITIVE_GATE:") for token in item.why_tokens)
        for item in explanations
    )
    assert all(
        any(
            token.startswith("OBSERVED:")
            for token in item.audit_record.observations
        )
        for item in explanations
    )
    assert frame.strategy_decision_allowed is False
    assert frame.outcome_visibility is False
    assert frame.grants_capital_authority is False


def test_master_frame_rejects_future_perception() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    perceptions = list(_perceptions(at))
    perceptions[0] = CapitalizerMarketPerceptionSnapshot(
        symbol=perceptions[0].symbol,
        observed_at=at + timedelta(seconds=1),
        assessment=perceptions[0].assessment,
    )

    with pytest.raises(ValueError, match="future perception"):
        build_master_cognitive_frame(
            world=_world(at),
            perceptions=tuple(perceptions),
            regime_hypotheses=_regimes(at),
            cross_market_graph=CapitalizerCrossMarketCausalGraph(
                observed_at=at,
                edges=(),
            ),
            pressure_facts=CapitalizerCognitivePressureFacts(),
            candidate_contexts=_candidate_contexts(at),
        )


def test_same_failure_pressure_observes_instead_of_recovery_aggression() -> None:
    assessment = assess_cognitive_pressure(
        CapitalizerCognitivePressureFacts(
            same_failure_repeat_active=True,
            genuinely_new_causal_event_present=False,
        )
    )

    assert assessment.pressure is CapitalizerCognitivePressure.RECOVERY_OBSERVATION
    assert assessment.increases_risk_to_recover is False
    assert assessment.grants_capital_authority is False


def _a1_research_run(
    at: datetime,
    *,
    perceptions: tuple[CapitalizerMarketPerceptionSnapshot, ...] | None = None,
    contexts: tuple[CapitalizerCandidateCognitiveContext, ...] | None = None,
    bindings: tuple[A1SourceBinding, ...] | None = None,
    memory: A1CausalSettledMemory | None = None,
) -> tuple[A1FullFrameResearchDecision, ...]:
    return evaluate_full_frame_research_batch(
        world=_world(at),
        perceptions=_perceptions(at) if perceptions is None else perceptions,
        regime_hypotheses=_regimes(at),
        cross_market_graph=CapitalizerCrossMarketCausalGraph(observed_at=at, edges=()),
        pressure_facts=CapitalizerCognitivePressureFacts(),
        contexts=_candidate_contexts(at) if contexts is None else contexts,
        source_bindings=(
            (
                A1SourceBinding("SRC:AUDJPY", "AUDJPY", at),
                A1SourceBinding("SRC:USDJPY", "USDJPY", at),
            )
            if bindings is None
            else bindings
        ),
        settled_memory=A1CausalSettledMemory() if memory is None else memory,
    )


def test_a1_research_adapter_invokes_real_nine_market_frame_with_why() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    decisions = _a1_research_run(at)
    assert len(decisions) == 2
    assert {item.source_opportunity_id for item in decisions} == {
        "SRC:AUDJPY", "SRC:USDJPY"
    }
    assert all(item.nine_market_frame_invoked for item in decisions)
    assert all(item.cognitive_gate == "PASS_TO_STRATEGY" for item in decisions)
    assert all(any(t.startswith("COGNITIVE_GATE:") for t in item.why_tokens)
               for item in decisions)
    assert all(not item.economic_admission_changed and not item.outcome_visible
               and not item.winner_selected and not item.grants_capital_authority
               for item in decisions)


def test_a1_research_adapter_fails_closed_on_missing_market_or_future_data() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    perceptions = _perceptions(at)
    with pytest.raises(ValueError, match="nine markets|perception snapshot"):
        _a1_research_run(at, perceptions=perceptions[:-1])
    with pytest.raises(ValueError, match="future perception"):
        _a1_research_run(
            at,
            perceptions=(
                replace(perceptions[0], observed_at=at + timedelta(seconds=1)),
                *perceptions[1:],
            ),
        )


def test_a1_research_adapter_rejects_source_collisions_and_missing_provenance() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="duplicate source ID"):
        _a1_research_run(
            at,
            bindings=(
                A1SourceBinding("DUPLICATE", "AUDJPY", at),
                A1SourceBinding("DUPLICATE", "USDJPY", at),
            ),
        )
    with pytest.raises(ValueError, match="time barrier"):
        _a1_research_run(
            at,
            bindings=(
                A1SourceBinding("SRC:AUDJPY", "AUDJPY", at - timedelta(minutes=1)),
                A1SourceBinding("SRC:USDJPY", "USDJPY", at),
            ),
        )
    contexts = _candidate_contexts(at)
    with pytest.raises(ValueError, match="provenance"):
        _a1_research_run(
            at,
            contexts=(replace(contexts[0], evidence_provenance_complete=False), contexts[1]),
        )


def test_a1_research_memory_reads_only_strictly_prior_settlements() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    memory = A1CausalSettledMemory(
        (
            A1SettledChosenTrade(
                "PRIOR", at - timedelta(hours=2), at - timedelta(seconds=1)
            ),
            A1SettledChosenTrade(
                "TIE", at - timedelta(hours=1), at
            ),
            A1SettledChosenTrade(
                "FUTURE", at - timedelta(minutes=1), at + timedelta(seconds=1)
            ),
        )
    )
    assert tuple(row.execution_id for row in memory.as_of(at)) == ("PRIOR",)
    decisions = _a1_research_run(at, memory=memory)
    assert all(item.closed_chosen_history_count == 1 for item in decisions)
    assert all(not hasattr(item, "realized_gross_r") for item in decisions)
    with pytest.raises(ValueError, match="duplicate settled execution"):
        A1CausalSettledMemory(
            (memory.chosen_settlements[0], memory.chosen_settlements[0])
        )


def test_a1_settled_loss_changes_real_adversarial_gate_only_after_settlement() -> None:
    """Ablation: identical context, only causally visible chosen loss changes gate."""
    entered = datetime(2026, 1, 5, 0, 30, tzinfo=UTC)
    exit_at = entered + timedelta(minutes=31)
    loss = CapitalizerLossCause(
        loss_id="EXEC-1",
        symbol="AUDJPY",
        session=CapitalizerSession.ASIA,
        hypothesis_id="H-AUDJPY",
        failure_state_fingerprint="FAMILY-AUDJPY",
        realized_r=Decimal("-1"),
        causes=("INVALIDATED_PRIOR_THESIS",),
    )
    memory = A1CausalSettledMemory(
        (A1SettledChosenTrade("EXEC-1", entered, exit_at, loss),)
    )

    def evaluate(at: datetime, chosen: A1CausalSettledMemory):
        contexts = _candidate_contexts(at)
        contexts = (
            replace(
                contexts[0],
                failure_state_fingerprint="FAMILY-AUDJPY",
                genuinely_new_causal_event=False,
            ),
            contexts[1],
        )
        decisions = _a1_research_run(at, contexts=contexts, memory=chosen)
        return {item.symbol: item for item in decisions}

    prior = evaluate(exit_at - timedelta(seconds=1), memory)
    tie = evaluate(exit_at, memory)
    after = evaluate(exit_at + timedelta(seconds=1), memory)
    ablated = evaluate(exit_at + timedelta(seconds=1), A1CausalSettledMemory())

    assert prior["AUDJPY"].cognitive_gate == "PASS_TO_STRATEGY"
    assert tie["AUDJPY"].cognitive_gate == "PASS_TO_STRATEGY"
    assert after["AUDJPY"].cognitive_gate == "ABSTAIN"
    assert ablated["AUDJPY"].cognitive_gate == "PASS_TO_STRATEGY"
    assert "UNRESOLVED_FAILURE_REPEAT_WITHOUT_NEW_CAUSE" in after["AUDJPY"].why_tokens
    assert after["AUDJPY"].closed_chosen_history_count == 1
    assert after["AUDJPY"].closed_chosen_failure_count == 1
    assert prior["AUDJPY"].closed_chosen_failure_count == 0
    assert tie["AUDJPY"].closed_chosen_failure_count == 0
    assert after["USDJPY"].cognitive_gate == "PASS_TO_STRATEGY"

    # A genuinely new independent event may be assessed without a blanket ban.
    fresh_contexts = _candidate_contexts(exit_at + timedelta(seconds=1))
    fresh = evaluate_full_frame_research_batch(
        world=_world(exit_at + timedelta(seconds=1)),
        perceptions=_perceptions(exit_at + timedelta(seconds=1)),
        regime_hypotheses=_regimes(exit_at + timedelta(seconds=1)),
        cross_market_graph=CapitalizerCrossMarketCausalGraph(
            observed_at=exit_at + timedelta(seconds=1), edges=()
        ),
        pressure_facts=CapitalizerCognitivePressureFacts(),
        contexts=(
            replace(
                fresh_contexts[0],
                failure_state_fingerprint="FAMILY-AUDJPY",
                genuinely_new_causal_event=True,
            ),
            fresh_contexts[1],
        ),
        source_bindings=(
            A1SourceBinding("SRC:AUDJPY", "AUDJPY", exit_at + timedelta(seconds=1)),
            A1SourceBinding("SRC:USDJPY", "USDJPY", exit_at + timedelta(seconds=1)),
        ),
        settled_memory=memory,
    )
    assert next(item for item in fresh if item.symbol == "AUDJPY").cognitive_gate == (
        "PASS_TO_STRATEGY"
    )


def test_a1_rejects_unproven_world_loss_history_and_mismatched_chosen_loss() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    loss = CapitalizerLossCause(
        loss_id="LOSS-1",
        symbol="AUDJPY",
        session=CapitalizerSession.ASIA,
        hypothesis_id="H-AUDJPY",
        failure_state_fingerprint="FAMILY-AUDJPY",
        realized_r=Decimal("-1"),
        causes=("SOURCE_INVALIDATION",),
    )
    with pytest.raises(ValueError, match="settled loss must match"):
        A1SettledChosenTrade("DIFFERENT-ID", at - timedelta(minutes=2), at, loss)
    with pytest.raises(ValueError, match="unproven or future world loss memory"):
        evaluate_full_frame_research_batch(
            world=replace(_world(at), loss_memory=CapitalizerLossMemory((loss,))),
            perceptions=_perceptions(at),
            regime_hypotheses=_regimes(at),
            cross_market_graph=CapitalizerCrossMarketCausalGraph(observed_at=at, edges=()),
            pressure_facts=CapitalizerCognitivePressureFacts(),
            contexts=_candidate_contexts(at),
            source_bindings=(
                A1SourceBinding("SRC:AUDJPY", "AUDJPY", at),
                A1SourceBinding("SRC:USDJPY", "USDJPY", at),
            ),
            settled_memory=A1CausalSettledMemory(),
        )
