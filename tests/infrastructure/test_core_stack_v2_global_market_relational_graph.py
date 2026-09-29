from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.global_market_relational_graph import (
    GlobalMarketNode,
    GlobalMarketRelationEdge,
    GlobalRelationHorizon,
    GlobalRelationKind,
    GlobalRelationState,
    QoreGlobalMarketRelationalGraph,
    RelationDirection,
    RelationEpistemicGrade,
)
from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    ComparabilityConfidence,
    RelationalComparabilityState,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def _node(key: str, family: str) -> GlobalMarketNode:
    return GlobalMarketNode(
        instrument_key=key,
        family=family,
        observation_status="OBSERVE_ONLY",
        data_quality_bps=9500,
        uncertainty_bps=1200,
        freshness_ms=250,
        provenance_refs=(f"source:{key}",),
    )


def _edge(**overrides: object) -> GlobalMarketRelationEdge:
    values: dict[str, object] = {
        "relation_id": "edge-001",
        "source_instrument_key": "CTRADER:US2000:10012",
        "target_instrument_key": "CTRADER:USTEC:10014",
        "relation_kind": GlobalRelationKind.LEAD_LAG,
        "relation_state": GlobalRelationState.STABLE,
        "horizon": GlobalRelationHorizon.M5,
        "direction": RelationDirection.SOURCE_TO_TARGET,
        "epistemic_grade": RelationEpistemicGrade.TEMPORAL_DEPENDENCY,
        "as_of": NOW,
        "evidence_cutoff_at": NOW,
        "last_transition_at": NOW - timedelta(minutes=5),
        "strength_bps": 6200,
        "confidence_bps": 7100,
        "uncertainty_bps": 2900,
        "stability_bps": 6800,
        "persistence_bps": 6400,
        "historical_validity_bps": 7000,
        "current_validity_bps": 6600,
        "timestamp_alignment_bps": 9800,
        "market_hours_comparable": True,
        "comparability_state": RelationalComparabilityState.COMPARABLE,
        "comparability_confidence": ComparabilityConfidence.HIGH,
        "relational_observation_fingerprint": "a" * 64,
        "comparability_policy_fingerprint": "b" * 64,
        "lag_ms": 720_000,
        "regime_context": ("US_RISK_SESSION",),
        "multiple_testing_control": "BH_FDR_FAMILY_001",
        "sample_count": 500,
        "provenance_refs": ("experiment:001",),
    }
    values.update(overrides)
    return GlobalMarketRelationEdge(**values)  # type: ignore[arg-type]


def test_global_market_graph_supports_instrument_level_relation() -> None:
    graph = QoreGlobalMarketRelationalGraph(
        as_of=NOW,
        nodes=tuple(
            sorted(
                (
                    _node("CTRADER:US2000:10012", "indices-benchmarks"),
                    _node("CTRADER:USTEC:10014", "indices-benchmarks"),
                ),
                key=lambda item: item.instrument_key,
            )
        ),
        edges=(_edge(),),
    )

    assert graph.node_count == 2
    assert graph.edge_count == 1
    assert len(graph.fingerprint()) == 64
    assert graph.current_trader_universe_defines_graph_ceiling is False
    assert graph.execution_authority is False


def test_divergence_requires_market_hours_comparability() -> None:
    with pytest.raises(ValueError, match="comparable market hours"):
        _edge(
            relation_kind=GlobalRelationKind.CROSS_MARKET_STRUCTURAL_DIVERGENCE,
            relation_state=GlobalRelationState.DIVERGING,
            market_hours_comparable=False,
        )


def test_global_relation_rejects_future_evidence() -> None:
    with pytest.raises(ValueError, match="future relation evidence"):
        _edge(evidence_cutoff_at=NOW + timedelta(milliseconds=1))


def test_global_graph_rejects_missing_endpoint() -> None:
    with pytest.raises(ValueError, match="target is not"):
        QoreGlobalMarketRelationalGraph(
            as_of=NOW,
            nodes=(_node("CTRADER:US2000:10012", "indices-benchmarks"),),
            edges=(_edge(),),
        )


def test_generalized_relation_taxonomy_includes_owner_requirements() -> None:
    required = {
        "CORRELATION",
        "CONDITIONAL_CORRELATION",
        "ROLLING_CORRELATION",
        "NONLINEAR_DEPENDENCE",
        "LEAD_LAG",
        "INFORMATION_FLOW",
        "CONVERGENCE",
        "DIVERGENCE",
        "CROSS_MARKET_STRUCTURAL_DIVERGENCE",
        "RELATIVE_STRENGTH",
        "VOLATILITY_COUPLING",
        "LIQUIDITY_COUPLING",
        "MOMENTUM_COUPLING",
        "REGIME_DEPENDENCE",
        "CAUSAL_INFLUENCE",
        "TEMPORAL_PRECEDENCE",
        "STRUCTURAL_BREAK",
        "RELATIONSHIP_STABILITY",
        "RELATIONSHIP_DECAY",
        "RELATIONSHIP_RECOVERY",
        "CROSS_ASSET_CONTAGION",
        "SYSTEMIC_STRESS",
    }
    assert required <= {item.value for item in GlobalRelationKind}


def test_no_relational_edge_without_comparability() -> None:
    with pytest.raises(
        ValueError,
        match="NO RELATIONAL CLAIM WITHOUT RELATIONAL COMPARABILITY",
    ):
        _edge(
            comparability_state=RelationalComparabilityState.STALE_PEER,
        )


def test_relational_edge_requires_high_comparability_confidence() -> None:
    with pytest.raises(ValueError, match="HIGH comparability confidence"):
        _edge(
            comparability_confidence=ComparabilityConfidence.LOW,
        )
