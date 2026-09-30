"""Pre-registered Phase22 sealed-holdout qualification protocol for CIBO.

Phase22 is an untouched confirmation stage after the Phase21 policy freeze.
It does not introduce a weaker economic standard: the holdout reuses the exact
frozen Phase20D V2 economic protocol without refit, while adding stricter
post-freeze/disjoint lineage requirements.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)

_PHASE22_PLAN_ID = "CIBO_PHASE22_SEALED_HOLDOUT_QUALIFICATION_PLAN_V1"


@dataclass(frozen=True, slots=True)
class Phase22HoldoutQualificationPlan:
    plan_id: str
    candidate_id: str
    candidate_parameter_sha256: str
    economic_protocol_plan_id: str
    economic_protocol_plan_sha256: str
    require_post_phase21_freeze: bool
    require_disjoint_from_phase20_qualification: bool
    require_exact_frozen_policy_identity: bool
    require_causal_decision_seals: bool
    require_complete_single_collector_git_lineage: bool
    require_exact_policy_decision_set: bool
    require_outcomes_bound_to_prior_decisions: bool
    reuse_phase20d_economic_thresholds_without_refit: bool
    allow_synthetic_evidence: bool
    allow_holdout_mining: bool

    def __post_init__(self) -> None:
        candidate = FROZEN_PHASE20_POLICY_CANDIDATE
        phase20_plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
        if self.plan_id != _PHASE22_PLAN_ID:
            raise CiboCapitalManagementError("Phase22 qualification plan id drift")
        if self.candidate_id != candidate.candidate_id:
            raise CiboCapitalManagementError(
                "Phase22 qualification candidate identity drift"
            )
        if self.candidate_parameter_sha256 != candidate.parameter_sha256():
            raise CiboCapitalManagementError(
                "Phase22 qualification parameter digest drift"
            )
        if self.economic_protocol_plan_id != phase20_plan.plan_id:
            raise CiboCapitalManagementError(
                "Phase22 economic protocol plan identity drift"
            )
        if (
            self.economic_protocol_plan_sha256
            != phase20d_qualification_plan_sha256()
        ):
            raise CiboCapitalManagementError(
                "Phase22 economic protocol digest drift"
            )
        required_true = (
            self.require_post_phase21_freeze,
            self.require_disjoint_from_phase20_qualification,
            self.require_exact_frozen_policy_identity,
            self.require_causal_decision_seals,
            self.require_complete_single_collector_git_lineage,
            self.require_exact_policy_decision_set,
            self.require_outcomes_bound_to_prior_decisions,
            self.reuse_phase20d_economic_thresholds_without_refit,
        )
        if not all(required_true):
            raise CiboCapitalManagementError(
                "Phase22 qualification cannot weaken lineage/economic gates"
            )
        if self.allow_synthetic_evidence or self.allow_holdout_mining:
            raise CiboCapitalManagementError(
                "Phase22 qualification forbids synthetic evidence and holdout mining"
            )


FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN = Phase22HoldoutQualificationPlan(
    plan_id=_PHASE22_PLAN_ID,
    candidate_id=FROZEN_PHASE20_POLICY_CANDIDATE.candidate_id,
    candidate_parameter_sha256=(
        FROZEN_PHASE20_POLICY_CANDIDATE.parameter_sha256()
    ),
    economic_protocol_plan_id=FROZEN_PHASE20D_QUALIFICATION_PLAN.plan_id,
    economic_protocol_plan_sha256=phase20d_qualification_plan_sha256(),
    require_post_phase21_freeze=True,
    require_disjoint_from_phase20_qualification=True,
    require_exact_frozen_policy_identity=True,
    require_causal_decision_seals=True,
    require_complete_single_collector_git_lineage=True,
    require_exact_policy_decision_set=True,
    require_outcomes_bound_to_prior_decisions=True,
    reuse_phase20d_economic_thresholds_without_refit=True,
    allow_synthetic_evidence=False,
    allow_holdout_mining=False,
)


def phase22_holdout_qualification_plan_sha256() -> str:
    plan = FROZEN_PHASE22_HOLDOUT_QUALIFICATION_PLAN
    payload = {
        "plan_id": plan.plan_id,
        "candidate_id": plan.candidate_id,
        "candidate_parameter_sha256": plan.candidate_parameter_sha256,
        "economic_protocol_plan_id": plan.economic_protocol_plan_id,
        "economic_protocol_plan_sha256": plan.economic_protocol_plan_sha256,
        "require_post_phase21_freeze": plan.require_post_phase21_freeze,
        "require_disjoint_from_phase20_qualification": (
            plan.require_disjoint_from_phase20_qualification
        ),
        "require_exact_frozen_policy_identity": (
            plan.require_exact_frozen_policy_identity
        ),
        "require_causal_decision_seals": plan.require_causal_decision_seals,
        "require_complete_single_collector_git_lineage": (
            plan.require_complete_single_collector_git_lineage
        ),
        "require_exact_policy_decision_set": (
            plan.require_exact_policy_decision_set
        ),
        "require_outcomes_bound_to_prior_decisions": (
            plan.require_outcomes_bound_to_prior_decisions
        ),
        "reuse_phase20d_economic_thresholds_without_refit": (
            plan.reuse_phase20d_economic_thresholds_without_refit
        ),
        "allow_synthetic_evidence": plan.allow_synthetic_evidence,
        "allow_holdout_mining": plan.allow_holdout_mining,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"
