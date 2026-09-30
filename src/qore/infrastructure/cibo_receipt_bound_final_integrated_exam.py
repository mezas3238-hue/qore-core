"""Receipt-bound wrapper for the CIBO Final Integrated Certification Exam.

The Architect-A exam engine is retained as the non-compensatory decision
engine, but callers cannot directly self-attest P1-P8 or E1-E10 booleans.
All eighteen controls are derived from canonical cross-boundary PASS artifacts
bound to the same integrated HEAD and frozen policy identity.
"""

from __future__ import annotations

import json

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationDecision,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
    require_cross_boundary_receipts,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedAssertionEvidence,
    FinalIntegratedAssertionId,
    FinalIntegratedExamEvidence,
    FinalIntegratedExamReport,
    assess_final_integrated_exam,
)

_P_IDS = (
    "P1_SOURCE_OF_TRUTH_RECONCILED",
    "P2_PRE_EXAM_ZERO_OPEN_PASS",
    "P3_CERTIFICATION_CI_CLEAR",
    "P4_PROVIDER_RISK_CMA_FORWARD_TRUTH",
    "P5_PHASE20D_PASS",
    "P6_POLICY_CALIBRATION_FREEZE",
    "P7_SCIENTIFIC_CLOSURE",
    "P8_COMPOUND_CLOSURE",
)
_E_IDS = tuple(item.value for item in FinalIntegratedAssertionId)
_REQUIRED_RECEIPT_IDS = _P_IDS + _E_IDS


def required_final_exam_receipt_ids() -> tuple[str, ...]:
    return _REQUIRED_RECEIPT_IDS


def _assert_clean_governance(
    receipt: CiboCrossBoundaryEvidenceReceipt,
) -> None:
    payload = json.loads(receipt.source_artifact_json)
    required_false = (
        "synthetic_evidence_used",
        "holdout_mining_used",
        "outcome_aware_refit",
        "operational_authority_claimed",
    )
    missing = tuple(key for key in required_false if key not in payload)
    if missing:
        raise CiboCapitalManagementError(
            "bound final exam source artifact missing governance flags: "
            + ",".join(missing)
        )
    contaminated = tuple(key for key in required_false if payload[key] is not False)
    if contaminated:
        raise CiboCapitalManagementError(
            "bound final exam source artifact governance contamination: "
            + ",".join(contaminated)
        )


def assess_receipt_bound_final_integrated_exam(
    *,
    integrated_head_sha: str,
    economic_certification: CiboEconomicCertificationDecision,
    receipts: tuple[CiboCrossBoundaryEvidenceReceipt, ...],
    certification_critical_external_blockers: tuple[str, ...] = (),
) -> FinalIntegratedExamReport:
    if not isinstance(
        economic_certification,
        CiboEconomicCertificationDecision,
    ):
        raise CiboCapitalManagementError(
            "bound final exam requires canonical economic certification"
        )
    policy_identity_sha256 = economic_certification.candidate_parameter_sha256
    by_id = require_cross_boundary_receipts(
        receipts=receipts,
        required_receipt_ids=_REQUIRED_RECEIPT_IDS,
        integrated_git_sha=integrated_head_sha,
        policy_identity_sha256=policy_identity_sha256,
    )
    for receipt in by_id.values():
        _assert_clean_governance(receipt)

    assertions = tuple(
        FinalIntegratedAssertionEvidence(
            assertion_id=assertion_id,
            passed=True,
            evidence_sha256=by_id[assertion_id.value].source_artifact_sha256,
        )
        for assertion_id in FinalIntegratedAssertionId
    )
    evidence = FinalIntegratedExamEvidence(
        integrated_head_sha=integrated_head_sha,
        source_truth_sha256=by_id[_P_IDS[0]].source_artifact_sha256,
        pre_exam_zero_open_sha256=by_id[_P_IDS[1]].source_artifact_sha256,
        ci_manifest_sha256=by_id[_P_IDS[2]].source_artifact_sha256,
        provider_risk_cma_forward_sha256=by_id[_P_IDS[3]].source_artifact_sha256,
        phase20d_qualification_sha256=by_id[_P_IDS[4]].source_artifact_sha256,
        policy_calibration_freeze_sha256=by_id[_P_IDS[5]].source_artifact_sha256,
        scientific_closure_sha256=by_id[_P_IDS[6]].source_artifact_sha256,
        compound_closure_sha256=by_id[_P_IDS[7]].source_artifact_sha256,
        economic_certification=economic_certification,
        assertions=assertions,
        source_truth_reconciled=True,
        pre_exam_zero_open_passed=True,
        certification_ci_clear=True,
        provider_risk_cma_forward_valid=True,
        phase20d_passed=True,
        policy_calibration_frozen=True,
        scientific_closure_terminal=True,
        compound_closure_terminal=True,
        certification_critical_external_blockers=(
            certification_critical_external_blockers
        ),
        synthetic_evidence_used=False,
        holdout_mining_used=False,
        outcome_aware_refit=False,
        operational_authority_claimed=False,
    )
    return assess_final_integrated_exam(evidence)
