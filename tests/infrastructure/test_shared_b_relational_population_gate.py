from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_relational_population_gate import (
    SharedBRelationalPopulationGateError,
    build_relational_population_gate,
)


def _b08() -> dict[str, object]:
    return {
        "identity": "SHARED_B_TEMPORAL_GOVERNANCE_READINESS_001",
        "temporal_governance_status": "NOT_READY",
        "temporal_governance_blockers": [
            "CANONICAL_CALENDAR_REGISTRY_EMPTY",
            "COMPARABILITY_POLICY_REGISTRY_NOT_FROZEN",
        ],
        "relational_comparability_authorized": False,
    }


def test_architecture_green_cannot_bypass_b08() -> None:
    payload = build_relational_population_gate(
        temporal_readiness=_b08(),
        b10_b12_architecture_verified=True,
        b13_architecture_verified=True,
    )
    assert payload["status"] == "RELATIONAL_EMPIRICAL_POPULATION_CLOSED_BY_B08"
    assert payload["global_graph_population_authorized"] is False
    assert payload["relationship_lifecycle_population_authorized"] is False
    assert payload["lead_lag_population_authorized"] is False
    assert payload["structural_divergence_population_authorized"] is False
    assert payload["causal_relation_claim_authorized"] is False
    assert payload["stale_relation_empirical_isolation_authorized"] is False
    assert payload["not_comparable_is_valid_terminal_state"] is True
    assert payload[
        "architecture_green_does_not_equal_empirical_population_green"
    ] is True
    assert payload["b10_complete"] is False
    assert payload["b11_complete"] is False
    assert payload["b12_complete"] is False
    assert payload["b13_complete"] is False


def test_missing_architecture_evidence_fails_closed() -> None:
    with pytest.raises(
        SharedBRelationalPopulationGateError,
        match="B-10/B-11/B-12",
    ):
        build_relational_population_gate(
            temporal_readiness=_b08(),
            b10_b12_architecture_verified=False,
            b13_architecture_verified=True,
        )


def test_unexpected_b08_authority_fails_closed() -> None:
    b08 = deepcopy(_b08())
    b08["relational_comparability_authorized"] = True
    with pytest.raises(
        SharedBRelationalPopulationGateError,
        match="unexpectedly authorizes",
    ):
        build_relational_population_gate(
            temporal_readiness=b08,
            b10_b12_architecture_verified=True,
            b13_architecture_verified=True,
        )
