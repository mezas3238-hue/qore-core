from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_adversarial_reasoning_v2 import (
    CapitalizerAdversarialCandidateFacts,
    CapitalizerAdversarialVerdict,
    assess_adversarial_candidate,
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
    CapitalizerCognitiveGateFacts,
    assess_cognitive_gate,
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
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerDailyJourney,
    CapitalizerLossCause,
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
    CapitalizerMetacognitiveFacts,
    assess_metacognition,
)
from qore.infrastructure.trader_lab.capitalizer_microstructure import (
    CapitalizerMicrostructureTrace,
)
from qore.infrastructure.trader_lab.capitalizer_opportunity_competition import (
    build_opportunity_competition_state,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerPerceptionStatus,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeResolution,
)

def _world(
    at: datetime,
    *,
    loss_memory: CapitalizerLossMemory | None = None,
) -> CapitalizerGlobalWorldModel:
    markets: list[CapitalizerMarketWorldState] = []
    for session in CapitalizerSession:
        for symbol in sorted(allowed_markets(session)):
            decision = symbol == "USDJPY"
            markets.append(
                CapitalizerMarketWorldState(
                    brain=CapitalizerMarketBrainState(
                        symbol=symbol,
                        session=session,
                        state_family_id="STATE",
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
                    hypothesis_id="H-USDJPY" if decision else None,
                    source_event_id="SRC-USDJPY" if decision else None,
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
            CapitalizerSessionLedger(CapitalizerSession.ASIA),
            CapitalizerSessionLedger(CapitalizerSession.LONDON),
            CapitalizerSessionLedger(CapitalizerSession.NEW_YORK),
        ),
        journey=CapitalizerDailyJourney(),
        loss_memory=loss_memory or CapitalizerLossMemory(),
    )


def _well_supported_metacognition():
    return assess_metacognition(
        CapitalizerMetacognitiveFacts(
            knowledge=CapitalizerKnowledgeState.KNOWN,
            perception_status=CapitalizerPerceptionStatus.GOOD,
            regime_resolution=CapitalizerRegimeResolution.SUPPORTED,
            contradictions=(),
            evidence_provenance_complete=True,
            destination_context_known=True,
        )
    )


def test_metacognition_distinguishes_supported_unresolved_and_conflicted() -> None:
    supported = _well_supported_metacognition()
    unresolved = assess_metacognition(
        CapitalizerMetacognitiveFacts(
            knowledge=CapitalizerKnowledgeState.UNKNOWN,
            perception_status=CapitalizerPerceptionStatus.GOOD,
            regime_resolution=CapitalizerRegimeResolution.UNRESOLVED,
            contradictions=(),
            evidence_provenance_complete=False,
            destination_context_known=False,
        )
    )
    conflicted = assess_metacognition(
        CapitalizerMetacognitiveFacts(
            knowledge=CapitalizerKnowledgeState.KNOWN,
            perception_status=CapitalizerPerceptionStatus.GOOD,
            regime_resolution=CapitalizerRegimeResolution.SUPPORTED,
            contradictions=("OPPOSITE_ACCEPTANCE",),
            evidence_provenance_complete=True,
            destination_context_known=True,
        )
    )

    assert supported.readiness is CapitalizerEpistemicReadiness.WELL_SUPPORTED
    assert unresolved.readiness is CapitalizerEpistemicReadiness.UNRESOLVED
    assert conflicted.readiness is CapitalizerEpistemicReadiness.CONFLICTED
    assert supported.numeric_confidence_used is False


def test_adversarial_brain_falsifies_repeated_failure_without_new_cause() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    loss = CapitalizerLossCause(
        loss_id="L-1",
        symbol="USDJPY",
        session=CapitalizerSession.ASIA,
        hypothesis_id="H-OLD",
        failure_state_fingerprint="FP-REPEAT",
        realized_r=Decimal("-1"),
        causes=("FAILED_EXPANSION",),
    )
    world = _world(at, loss_memory=CapitalizerLossMemory(unresolved=(loss,)))
    metacognition = _well_supported_metacognition()

    assessment = assess_adversarial_candidate(
        facts=CapitalizerAdversarialCandidateFacts(
            symbol="USDJPY",
            hypothesis_id="H-USDJPY",
            source_event_id="SRC-USDJPY",
            failure_state_fingerprint="FP-REPEAT",
            metacognition=metacognition,
            perception_status=CapitalizerPerceptionStatus.GOOD,
            regime_resolution=CapitalizerRegimeResolution.SUPPORTED,
            destination_context_known=True,
            destination_available=True,
            event_is_fresh=True,
            genuinely_new_causal_event=False,
            contradictions=(),
        ),
        world=world,
        cross_market_graph=CapitalizerCrossMarketCausalGraph(
            observed_at=at,
            edges=(),
        ),
    )

    assert assessment.verdict is CapitalizerAdversarialVerdict.FALSIFIED
    assert "UNRESOLVED_FAILURE_REPEAT_WITHOUT_NEW_CAUSE" in assessment.hard_findings
    assert assessment.grants_entry_authority is False


def test_cognitive_gate_waits_when_evidence_is_conditional() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    world = _world(at)
    competition = build_opportunity_competition_state(world)
    metacognition = assess_metacognition(
        CapitalizerMetacognitiveFacts(
            knowledge=CapitalizerKnowledgeState.PARTIAL,
            perception_status=CapitalizerPerceptionStatus.GOOD,
            regime_resolution=CapitalizerRegimeResolution.SUPPORTED,
            contradictions=(),
            evidence_provenance_complete=True,
            destination_context_known=True,
        )
    )
    adversarial = assess_adversarial_candidate(
        facts=CapitalizerAdversarialCandidateFacts(
            symbol="USDJPY",
            hypothesis_id="H-USDJPY",
            source_event_id="SRC-USDJPY",
            failure_state_fingerprint=None,
            metacognition=metacognition,
            perception_status=CapitalizerPerceptionStatus.GOOD,
            regime_resolution=CapitalizerRegimeResolution.SUPPORTED,
            destination_context_known=True,
            destination_available=True,
            event_is_fresh=True,
            genuinely_new_causal_event=True,
            contradictions=(),
        ),
        world=world,
        cross_market_graph=CapitalizerCrossMarketCausalGraph(
            observed_at=at,
            edges=(),
        ),
    )
    gate = assess_cognitive_gate(
        facts=CapitalizerCognitiveGateFacts(
            symbol="USDJPY",
            attention=CapitalizerAttentionState.DECISION,
            hypothesis_stage=CapitalizerHypothesisStage.EXECUTABLE,
            metacognition=metacognition,
            adversarial=adversarial,
            cognitive_pressure=CapitalizerCognitivePressure.NORMAL,
        ),
        competition=competition,
    )

    assert gate.decision is CapitalizerCognitiveGateDecision.WAIT
    assert gate.strategy_may_evaluate is False
    assert gate.executes_trade is False


def test_cognitive_gate_can_only_pass_clean_candidate_to_strategy() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    world = _world(at)
    competition = build_opportunity_competition_state(world)
    metacognition = _well_supported_metacognition()
    adversarial = assess_adversarial_candidate(
        facts=CapitalizerAdversarialCandidateFacts(
            symbol="USDJPY",
            hypothesis_id="H-USDJPY",
            source_event_id="SRC-USDJPY",
            failure_state_fingerprint=None,
            metacognition=metacognition,
            perception_status=CapitalizerPerceptionStatus.GOOD,
            regime_resolution=CapitalizerRegimeResolution.SUPPORTED,
            destination_context_known=True,
            destination_available=True,
            event_is_fresh=True,
            genuinely_new_causal_event=True,
            contradictions=(),
        ),
        world=world,
        cross_market_graph=CapitalizerCrossMarketCausalGraph(
            observed_at=at,
            edges=(),
        ),
    )
    gate = assess_cognitive_gate(
        facts=CapitalizerCognitiveGateFacts(
            symbol="USDJPY",
            attention=CapitalizerAttentionState.DECISION,
            hypothesis_stage=CapitalizerHypothesisStage.EXECUTABLE,
            metacognition=metacognition,
            adversarial=adversarial,
            cognitive_pressure=CapitalizerCognitivePressure.NORMAL,
        ),
        competition=competition,
    )

    assert adversarial.verdict is CapitalizerAdversarialVerdict.PASSED
    assert gate.decision is CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY
    assert gate.strategy_may_evaluate is True
    assert gate.executes_trade is False
    assert gate.grants_capital_authority is False
