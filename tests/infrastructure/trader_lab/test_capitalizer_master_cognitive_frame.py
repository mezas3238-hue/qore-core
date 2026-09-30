from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

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
