"""Architect-B empirical relational population gate.

B-10..B-13 may have validated descriptive architecture, but empirical
population remains forbidden until B-08 temporal governance is READY. This
gate makes that dependency executable and fail-closed.
"""

from __future__ import annotations

import hashlib
import json

IDENTITY = "SHARED_B_RELATIONAL_POPULATION_GATE_001"
EXPECTED_B08 = "SHARED_B_TEMPORAL_GOVERNANCE_READINESS_001"


class SharedBRelationalPopulationGateError(ValueError):
    """Relational population gate evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_relational_population_gate(
    *,
    temporal_readiness: dict[str, object],
    b10_b12_architecture_verified: bool,
    b13_architecture_verified: bool,
) -> dict[str, object]:
    if temporal_readiness.get("identity") != EXPECTED_B08:
        raise SharedBRelationalPopulationGateError(
            "unexpected B-08 readiness identity"
        )
    if b10_b12_architecture_verified is not True:
        raise SharedBRelationalPopulationGateError(
            "B-10/B-11/B-12 architecture evidence missing"
        )
    if b13_architecture_verified is not True:
        raise SharedBRelationalPopulationGateError(
            "B-13 architecture evidence missing"
        )

    governance_status = temporal_readiness.get("temporal_governance_status")
    blockers = temporal_readiness.get("temporal_governance_blockers")
    if not isinstance(blockers, list):
        raise SharedBRelationalPopulationGateError(
            "B-08 blocker list missing"
        )
    if temporal_readiness.get("relational_comparability_authorized") is not False:
        raise SharedBRelationalPopulationGateError(
            "B-08 unexpectedly authorizes relational comparability"
        )
    if governance_status != "NOT_READY":
        raise SharedBRelationalPopulationGateError(
            "expected current B-08 NOT_READY evidence"
        )
    if not blockers:
        raise SharedBRelationalPopulationGateError(
            "NOT_READY B-08 must expose blockers"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "RELATIONAL_EMPIRICAL_POPULATION_CLOSED_BY_B08",
        "b10_global_graph_architecture_verified": True,
        "b11_relationship_lifecycle_architecture_verified": True,
        "b12_lead_lag_architecture_verified": True,
        "b13_structural_divergence_architecture_verified": True,
        "b08_temporal_governance_status": governance_status,
        "b08_blockers": sorted(set(str(item) for item in blockers)),
        "global_graph_population_authorized": False,
        "relationship_lifecycle_population_authorized": False,
        "lead_lag_population_authorized": False,
        "structural_divergence_population_authorized": False,
        "causal_relation_claim_authorized": False,
        "stale_relation_empirical_isolation_authorized": False,
        "not_comparable_is_valid_terminal_state": True,
        "architecture_green_does_not_equal_empirical_population_green": True,
        "automatic_threshold_invention": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b10_complete": False,
        "b11_complete": False,
        "b12_complete": False,
        "b13_complete": False,
    }
    payload["gate_fingerprint_sha256"] = _fingerprint(payload)
    return payload
