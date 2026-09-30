from __future__ import annotations

from dataclasses import replace

from qore.infrastructure.cibo_ce2i_final_certification import (
    CiboEconomicCertificationDecision,
    CiboEconomicCertificationStatus,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedAssertionEvidence,
    FinalIntegratedAssertionId,
    FinalIntegratedExamEvidence,
    FinalIntegratedExamStatus,
    assess_final_integrated_exam,
)


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _economic(
    status: CiboEconomicCertificationStatus = (
        CiboEconomicCertificationStatus.CERTIFIED
    ),
) -> CiboEconomicCertificationDecision:
    return CiboEconomicCertificationDecision(
        status=status,
        candidate_id="candidate",
        candidate_parameter_sha256=_sha("1"),
        phase21_manifest_sha256=_sha("2"),
        phase22_plan_sha256=_sha("3"),
        blockers=() if status is CiboEconomicCertificationStatus.CERTIFIED else ("BLOCKED",),
    )


def _evidence() -> FinalIntegratedExamEvidence:
    assertions = tuple(
        FinalIntegratedAssertionEvidence(
            assertion_id=item,
            passed=True,
            evidence_sha256=_sha(format(index + 1, "x")[-1]),
        )
        for index, item in enumerate(FinalIntegratedAssertionId)
    )
    return FinalIntegratedExamEvidence(
        integrated_head_sha="a" * 40,
        source_truth_sha256=_sha("1"),
        pre_exam_zero_open_sha256=_sha("2"),
        ci_manifest_sha256=_sha("3"),
        provider_risk_cma_forward_sha256=_sha("4"),
        phase20d_qualification_sha256=_sha("5"),
        policy_calibration_freeze_sha256=_sha("6"),
        scientific_closure_sha256=_sha("7"),
        compound_closure_sha256=_sha("8"),
        economic_certification=_economic(),
        assertions=assertions,
        source_truth_reconciled=True,
        pre_exam_zero_open_passed=True,
        certification_ci_clear=True,
        provider_risk_cma_forward_valid=True,
        phase20d_passed=True,
        policy_calibration_frozen=True,
        scientific_closure_terminal=True,
        compound_closure_terminal=True,
    )


def test_final_integrated_exam_passes_only_all_and_gate() -> None:
    report = assess_final_integrated_exam(_evidence())

    assert report.status is FinalIntegratedExamStatus.PASS
    assert report.blockers == ()
    assert report.demo_execution_authorized is False
    assert report.live_authorized is False
    assert report.real_capital_authorized is False
    assert report.merge_authorized is False


def test_final_integrated_exam_blocks_missing_prerequisite() -> None:
    evidence = replace(_evidence(), compound_closure_terminal=False)

    report = assess_final_integrated_exam(evidence)

    assert report.status is FinalIntegratedExamStatus.BLOCKED
    assert "P8_COMPOUND_CLOSURE" in report.blockers


def test_final_integrated_exam_blocks_failed_assertion() -> None:
    evidence = _evidence()
    assertions = list(evidence.assertions)
    assertions[6] = replace(assertions[6], passed=False)

    report = assess_final_integrated_exam(
        replace(evidence, assertions=tuple(assertions))
    )

    assert report.status is FinalIntegratedExamStatus.BLOCKED
    assert "E7_ECONOMIC_NONCOMPENSATION_FAILED" in report.blockers


def test_final_integrated_exam_blocks_missing_assertion() -> None:
    evidence = _evidence()

    report = assess_final_integrated_exam(
        replace(evidence, assertions=evidence.assertions[:-1])
    )

    assert report.status is FinalIntegratedExamStatus.BLOCKED
    assert "E10_DETERMINISTIC_REPLAY_EVIDENCE_REQUIRED" in report.blockers


def test_final_integrated_exam_requires_phase22_economic_certification() -> None:
    evidence = replace(
        _evidence(),
        economic_certification=_economic(CiboEconomicCertificationStatus.PENDING),
    )

    report = assess_final_integrated_exam(evidence)

    assert report.status is FinalIntegratedExamStatus.BLOCKED
    assert "PHASE22_ECONOMIC_CERTIFICATION_REQUIRED" in report.blockers


def test_final_integrated_exam_rejects_compensatory_external_blocker() -> None:
    evidence = replace(
        _evidence(),
        certification_critical_external_blockers=("PROVIDER_UNKNOWN",),
    )

    report = assess_final_integrated_exam(evidence)

    assert report.status is FinalIntegratedExamStatus.BLOCKED
    assert "CERTIFICATION_CRITICAL_EXTERNAL_BLOCKER" in report.blockers
