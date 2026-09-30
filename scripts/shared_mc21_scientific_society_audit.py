#!/usr/bin/env python3
"""Audit MC-21 Scientific Society role coverage and real-engine bindings."""

from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.core_stack_v2.scientific_society import (
    ScientificClaim,
    ScientificContribution,
    ScientificRole,
    ScientificSocietyVerdict,
    arbitrate_scientific_society,
)

IDENTITY = "QORE_SHARED_MC21_SCIENTIFIC_SOCIETY_AUDIT_001"

REAL_BINDINGS = {
    ScientificRole.OBSERVER: ("source-observation", "run:36737948664"),
    ScientificRole.HYPOTHESIS_GENERATOR: (
        "symbolic-hypothesis-ensemble",
        "module:hypothesis_ensemble",
    ),
    ScientificRole.CAUSAL_SCIENTIST: (
        "causal-discovery",
        "run:36236760353",
    ),
    ScientificRole.COUNTERFACTUAL_ANALYST: (
        "counterfactual-world",
        "run:36764204066",
    ),
    ScientificRole.TRAJECTORY_SPECIALIST: (
        "trajectory-model",
        "run:36764215198",
    ),
    ScientificRole.RISK_OF_ERROR_ANALYST: (
        "calibrated-belief",
        "run:36754966932",
    ),
    ScientificRole.REPLICATION_SCIENTIST: (
        "replication-science",
        "run:36248025384",
    ),
}

MODEL_FAMILIES = {
    ScientificRole.OBSERVER: "SOURCE_OBSERVATION",
    ScientificRole.HYPOTHESIS_GENERATOR: "SYMBOLIC",
    ScientificRole.CAUSAL_SCIENTIST: "CAUSAL",
    ScientificRole.STATISTICIAN: "STATISTICAL",
    ScientificRole.ADVERSARIAL_CRITIC: "ADVERSARIAL",
    ScientificRole.DEFENDER: "SYMBOLIC",
    ScientificRole.SKEPTIC: "EPISTEMIC",
    ScientificRole.COUNTERFACTUAL_ANALYST: "COUNTERFACTUAL",
    ScientificRole.REGIME_SPECIALIST: "REGIME_STATE",
    ScientificRole.TRAJECTORY_SPECIALIST: "TRAJECTORY",
    ScientificRole.RISK_OF_ERROR_ANALYST: "BAYESIAN_CALIBRATION",
    ScientificRole.REPLICATION_SCIENTIST: "REPLICATION",
}


def _contribution(
    role: ScientificRole,
    *,
    claim: ScientificClaim,
    confidence_bps: int,
) -> ScientificContribution:
    binding = REAL_BINDINGS.get(role)
    evidence = (
        (binding[1],)
        if binding is not None
        else (f"mc21:role-contract:{role.value}",)
    )
    return ScientificContribution(
        role=role,
        claim=claim,
        confidence_bps=confidence_bps,
        model_family=MODEL_FAMILIES[role],
        evidence_refs=tuple(sorted(evidence)),
        real_engine_bound=binding is not None,
    )


def main() -> None:
    minority_case = tuple(
        _contribution(
            role,
            claim=(
                ScientificClaim.FALSIFY
                if role is ScientificRole.ADVERSARIAL_CRITIC
                else ScientificClaim.SUPPORT
            ),
            confidence_bps=7_000,
        )
        for role in ScientificRole
    )
    minority_decision = arbitrate_scientific_society(
        proposition_id="MC21_MINORITY_FALSIFICATION_CANARY",
        contributions=minority_case,
    )
    if (
        minority_decision.verdict
        is not ScientificSocietyVerdict.REJECTED_BY_FALSIFICATION
    ):
        raise AssertionError("MC21 minority falsification was suppressed")

    support_case = tuple(
        _contribution(
            role,
            claim=ScientificClaim.SUPPORT,
            confidence_bps=6_000,
        )
        for role in ScientificRole
    )
    support_decision = arbitrate_scientific_society(
        proposition_id="MC21_RESEARCH_ONLY_CANARY",
        contributions=support_case,
    )
    if support_decision.verdict is not ScientificSocietyVerdict.RESEARCH_ONLY:
        raise AssertionError("MC21 support case self-promoted beyond research")

    bound_roles = sorted(role.value for role in REAL_BINDINGS)
    unbound_roles = sorted(
        role.value for role in ScientificRole if role not in REAL_BINDINGS
    )
    families = sorted(set(MODEL_FAMILIES.values()))
    payload = {
        "identity": IDENTITY,
        "status": "MC21_SCIENTIFIC_SOCIETY_FOUNDATION_PASS",
        "required_role_count": len(ScientificRole),
        "all_required_roles_present": True,
        "real_engine_bound_role_count": len(bound_roles),
        "real_engine_bound_roles": bound_roles,
        "contract_only_roles": unbound_roles,
        "heterogeneous_model_family_count": len(families),
        "model_families": families,
        "minority_falsification_preserved": True,
        "simple_majority_voting_used": False,
        "support_only_self_promotes_to_validated": False,
        "all_roles_real_engine_bound": len(bound_roles) == len(ScientificRole),
        "mc21_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
        "productive_authority": False,
    }
    Path("result").mkdir(exist_ok=True)
    Path("result/mc21-scientific-society-audit.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
