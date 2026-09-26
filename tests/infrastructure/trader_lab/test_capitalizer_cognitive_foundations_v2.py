from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.capitalizer_attention import (
    derive_attention_state,
)
from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketCausalGraph,
    CapitalizerCrossMarketEdge,
    CapitalizerCrossMarketRelation,
)
from qore.infrastructure.trader_lab.capitalizer_hypothesis_lifecycle import (
    CapitalizerHypothesisState,
    transition_hypothesis,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerAttentionState,
    CapitalizerHypothesisStage,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerPerceptionFacts,
    CapitalizerPerceptionStatus,
    assess_perception_integrity,
)


def test_perception_integrity_fails_closed_without_numeric_tuning() -> None:
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
    degraded = assess_perception_integrity(
        CapitalizerPerceptionFacts(
            quote_fresh=False,
            bars_complete=True,
            timestamps_ordered=True,
            session_clock_valid=True,
            provenance_valid=True,
            microstructure_complete=True,
        )
    )
    bad = assess_perception_integrity(
        CapitalizerPerceptionFacts(
            quote_fresh=True,
            bars_complete=False,
            timestamps_ordered=True,
            session_clock_valid=True,
            provenance_valid=True,
            microstructure_complete=True,
        )
    )

    assert good.status is CapitalizerPerceptionStatus.GOOD
    assert degraded.status is CapitalizerPerceptionStatus.DEGRADED
    assert "QUOTE_NOT_FRESH" in degraded.reasons
    assert bad.status is CapitalizerPerceptionStatus.BAD
    assert "BARS_INCOMPLETE" in bad.reasons


def test_hypothesis_lifecycle_cannot_jump_or_resurrect_killed_thesis() -> None:
    at = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    state = CapitalizerHypothesisState(
        hypothesis_id="H-1",
        source_event_id="SRC-1",
        event_generation=1,
        stage=CapitalizerHypothesisStage.OBSERVED_EVENT,
        observed_at=at,
    )

    with pytest.raises(ValueError, match="invalid hypothesis transition"):
        transition_hypothesis(
            state,
            to_stage=CapitalizerHypothesisStage.EXECUTABLE,
            observed_at=at,
        )

    forming = transition_hypothesis(
        state,
        to_stage=CapitalizerHypothesisStage.HYPOTHESIS_FORMING,
        observed_at=at + timedelta(seconds=1),
    )
    killed = transition_hypothesis(
        forming,
        to_stage=CapitalizerHypothesisStage.THESIS_KILLED,
        observed_at=at + timedelta(seconds=2),
    )

    assert killed.terminal is True
    with pytest.raises(ValueError, match="invalid hypothesis transition"):
        transition_hypothesis(
            killed,
            to_stage=CapitalizerHypothesisStage.HYPOTHESIS_FORMING,
            observed_at=at + timedelta(seconds=3),
        )


def test_attention_requires_known_evidence_before_decision_state() -> None:
    known = derive_attention_state(
        has_relevant_event=True,
        hypothesis_stage=CapitalizerHypothesisStage.CONFIRMED,
        knowledge=CapitalizerKnowledgeState.KNOWN,
        position_open=False,
    )
    partial = derive_attention_state(
        has_relevant_event=True,
        hypothesis_stage=CapitalizerHypothesisStage.CONFIRMED,
        knowledge=CapitalizerKnowledgeState.PARTIAL,
        position_open=False,
    )

    assert known is CapitalizerAttentionState.DECISION
    assert partial is CapitalizerAttentionState.FOCUSED


def test_open_position_forces_position_attention_with_active_thesis() -> None:
    attention = derive_attention_state(
        has_relevant_event=True,
        hypothesis_stage=CapitalizerHypothesisStage.THESIS_STABLE,
        knowledge=CapitalizerKnowledgeState.CONFLICTED,
        position_open=True,
    )
    assert attention is CapitalizerAttentionState.POSITION

    with pytest.raises(ValueError, match="active position-stage"):
        derive_attention_state(
            has_relevant_event=True,
            hypothesis_stage=CapitalizerHypothesisStage.EXECUTABLE,
            knowledge=CapitalizerKnowledgeState.KNOWN,
            position_open=True,
        )


def test_cross_market_graph_requires_causal_evidence_and_no_future_edges() -> None:
    at = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    edge = CapitalizerCrossMarketEdge(
        left_symbol="NAS100",
        right_symbol="XAUUSD",
        relation=CapitalizerCrossMarketRelation.SHARED_CAUSE,
        observed_at=at,
        causal_tokens=("USD_FACTOR_ACTIVE", "SAME_DECISION_WINDOW"),
    )
    graph = CapitalizerCrossMarketCausalGraph(
        observed_at=at,
        edges=(edge,),
    )

    assert graph.relation_for("xauusd", "nas100") == edge
    assert graph.correlation_only_allowed is False

    with pytest.raises(ValueError, match="causal evidence tokens"):
        CapitalizerCrossMarketEdge(
            left_symbol="EURUSD",
            right_symbol="GBPUSD",
            relation=CapitalizerCrossMarketRelation.REINFORCING,
            observed_at=at,
            causal_tokens=(),
        )

    future_edge = CapitalizerCrossMarketEdge(
        left_symbol="EURUSD",
        right_symbol="GBPUSD",
        relation=CapitalizerCrossMarketRelation.UNKNOWN,
        observed_at=at + timedelta(seconds=1),
        causal_tokens=(),
    )
    with pytest.raises(ValueError, match="future causal edge"):
        CapitalizerCrossMarketCausalGraph(
            observed_at=at,
            edges=(future_edge,),
        )
