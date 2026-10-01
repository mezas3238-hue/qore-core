"""Receipt-bound V2 wrapper for the CIBO Final Integrated Exam."""

from __future__ import annotations

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationStatus,
    Phase22QualificationReceipt,
    assess_cibo_final_economic_certification,
)
from qore.infrastructure.cibo_ce2i_phase21_policy_freeze import (
    Phase21PolicyFreezeManifest,
)
from qore.infrastructure.cibo_final_exam_control_receipt import (
    CiboFinalExamControlReceipt,
    require_final_exam_control_receipts,
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
_REQUIRED_IDS = _P_IDS + _E_IDS

_EXPECTED_PRODUCER_GATE_BY_ID = {
    "P1_SOURCE_OF_TRUTH_RECONCILED": "CIBO_FINAL_SOURCE_OF_TRUTH_CONTROL_V2",
    "P2_PRE_EXAM_ZERO_OPEN_PASS": "CIBO_PRE_EXAM_ZERO_OPEN_CONTROL_V1",
    "P3_CERTIFICATION_CI_CLEAR": "CIBO_FINAL_CERTIFICATION_CI_CLEAR_V1",
    "P4_PROVIDER_RISK_CMA_FORWARD_TRUTH": (
        "CIBO_P4_PROVIDER_RISK_CMA_FORWARD_TRUTH_V1"
    ),
    "P5_PHASE20D_PASS": "CIBO_P5_PHASE20D_PASS_V1",
    "P6_POLICY_CALIBRATION_FREEZE": "CIBO_P6_POLICY_CALIBRATION_FREEZE_V1",
    "P7_SCIENTIFIC_CLOSURE": "CIBO_ARCH_A_PHASE22_V2_SCIENTIFIC_CLOSURE",
    "P8_COMPOUND_CLOSURE": "CIBO_ARCH_A_PHASE22_V2_COMPOUND_CLOSURE",
    "E1_AUTHORITY": "CIBO_ARCH_A_E1_AUTHORITY_V1",
    "E2_CAPITAL_CONSERVATION": "CIBO_ARCH_A_E2_CAPITAL_CONSERVATION_V1",
    "E3_REALIZED_CAPITAL_LAW": "CIBO_ARCH_A_E3_REALIZED_CAPITAL_LAW_V1",
    "E4_PROVIDER_TRUTH": "CIBO_ARCH_A_E4_PROVIDER_TRUTH_V2",
    "E5_RISK_PRECEDENCE": "CIBO_ARCH_A_E5_RISK_PRECEDENCE_V1",
    "E6_CHRONOLOGY_NO_LEAKAGE": "CIBO_ARCH_A_E6_CHRONOLOGY_NO_LEAKAGE_V1",
    "E7_ECONOMIC_NONCOMPENSATION": (
        "CIBO_ARCH_A_E7_ECONOMIC_NONCOMPENSATION_V1"
    ),
    "E8_STRESS_INTEGRITY": "CIBO_ARCH_A_E8_STRESS_INTEGRITY_V1",
    "E9_TEMPORAL_REPLICATION": "CIBO_ARCH_A_E9_TEMPORAL_REPLICATION_V1",
    "E10_DETERMINISTIC_REPLAY": "CIBO_ARCH_A_E10_DETERMINISTIC_REPLAY_V1",
}


def required_final_exam_control_ids() -> tuple[str, ...]:
    return _REQUIRED_IDS


def expected_final_exam_control_producer_gate_id(receipt_id: str) -> str:
    try:
        return _EXPECTED_PRODUCER_GATE_BY_ID[receipt_id]
    except KeyError as error:
        raise CiboCapitalManagementError(
            "unknown final-exam control receipt identity"
        ) from error


def assess_receipt_bound_final_integrated_exam_v2(
    *,
    integrated_head_sha: str,
    phase21_manifest: Phase21PolicyFreezeManifest,
    phase22_receipt: Phase22QualificationReceipt,
    receipts: tuple[CiboFinalExamControlReceipt, ...],
    certification_critical_external_blockers: tuple[str, ...] = (),
) -> FinalIntegratedExamReport:
    if not isinstance(phase21_manifest, Phase21PolicyFreezeManifest):
        raise CiboCapitalManagementError(
            "receipt-bound final exam requires canonical Phase21 manifest"
        )
    if not isinstance(phase22_receipt, Phase22QualificationReceipt):
        raise CiboCapitalManagementError(
            "receipt-bound final exam requires canonical Phase22 receipt"
        )
    economic = assess_cibo_final_economic_certification(
        phase21_manifest=phase21_manifest,
        phase22_receipt=phase22_receipt,
    )
    if (
        economic.status is not CiboEconomicCertificationStatus.CERTIFIED
        or economic.blockers
    ):
        raise CiboCapitalManagementError(
            "receipt-bound final exam requires exact Phase21/Phase22 certification"
        )
    by_id = require_final_exam_control_receipts(
        receipts=receipts,
        required_receipt_ids=_REQUIRED_IDS,
        integrated_git_sha=integrated_head_sha,
        policy_identity_sha256=economic.candidate_parameter_sha256,
        phase22_qualification_artifact_sha256=(
            phase22_receipt.qualification_artifact_sha256
        ),
    )
    for receipt_id, receipt in by_id.items():
        expected_producer = expected_final_exam_control_producer_gate_id(receipt_id)
        if receipt.producer_gate_id != expected_producer:
            raise CiboCapitalManagementError(
                "final-exam control producer-gate drift: " + receipt_id
            )

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
        economic_certification=economic,
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
