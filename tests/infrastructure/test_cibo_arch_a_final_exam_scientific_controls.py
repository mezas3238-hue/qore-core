from __future__ import annotations

import importlib.util
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.cibo_arch_a_final_exam_scientific_controls import (
    build_architect_a_final_exam_scientific_controls,
    build_closure41_final_exam_scientific_controls,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    PHASE22_V2_INTAKE_SCHEMA,
    PHASE22_V2_REQUIRED_FOLDS,
    PHASE22_V2_REQUIRED_RECEIPTS,
    PHASE22_V2_REQUIRED_TRADERS,
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificDispositionReceipt,
    ArchitectAPhase22V2ScientificIntakeReport,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_final_science_fixture", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)

_CLOSURE_FIXTURE_PATH = Path(__file__).with_name(
    "test_cibo_scientific_closure_41.py"
)
_CLOSURE_SPEC = importlib.util.spec_from_file_location(
    "_closure41_science_fixture",
    _CLOSURE_FIXTURE_PATH,
)
assert _CLOSURE_SPEC is not None and _CLOSURE_SPEC.loader is not None
_CLOSURE_FIXTURE = importlib.util.module_from_spec(_CLOSURE_SPEC)
_CLOSURE_SPEC.loader.exec_module(_CLOSURE_FIXTURE)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _intake(qualification_sha: str) -> ArchitectAPhase22V2ScientificIntakeReport:
    refs = tuple(
        (
            name,
            qualification_sha if name == "qualification_report_sha256"
            else _sha(name),
        )
        for name in PHASE22_V2_REQUIRED_RECEIPTS
    )
    return ArchitectAPhase22V2ScientificIntakeReport(
        schema=PHASE22_V2_INTAKE_SCHEMA,
        manifest_sha256=_sha("phase22-handoff"),
        candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        qualification_status="PASS",
        trader_ids=PHASE22_V2_REQUIRED_TRADERS,
        fold_ids=PHASE22_V2_REQUIRED_FOLDS,
        decision_epochs=80,
        candidate_outcomes=200,
        selected_outcomes=60,
        calendar_span_days=28,
        distinct_trading_days=20,
        minimum_fold_candidate_outcomes=40,
        minimum_fold_lineages=4,
        minimum_outcomes_any_lineage=8,
        candidate_outcome_coverage="0.95",
        selected_outcome_coverage="1.00",
        baseline_selected_outcome_coverage="1.00",
        receipt_refs=refs,
        ready_for_scientific_reentry=True,
        blockers=(),
    )


def _disposition(
    intake: ArchitectAPhase22V2ScientificIntakeReport,
    workstream_id: str,
) -> ArchitectAPhase22V2ScientificDispositionReceipt:
    return ArchitectAPhase22V2ScientificDispositionReceipt(
        schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
        workstream_id=workstream_id,
        phase22_manifest_sha256=intake.manifest_sha256,
        source_gate_id=f"gate:{workstream_id}",
        source_gate_evidence_sha256=_sha(workstream_id),
        source_gate_status="PASS",
        passed=True,
        recommended_disposition="COMPLETED_AND_PROVEN",
        blockers=(),
        failed_dimensions=(),
        owner_review_approved=False,
    )


def _chain():
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    intake = _intake(phase22.qualification_artifact_sha256)
    ids = (
        "GEN-C9",
        "PROTECTED_BASE_CAPITAL",
        "CAPITAL_AMPLIFICATION",
        "ADVERSARIAL_STRESS",
        "TEMPORAL_REPLICATION",
    )
    dispositions = tuple(_disposition(intake, item) for item in ids)
    return phase22, intake, dispositions


def test_arch_a_derives_e7_e8_e9_from_positive_frozen_gates() -> None:
    phase22, intake, dispositions = _chain()
    receipts = build_architect_a_final_exam_scientific_controls(
        integrated_git_sha="a" * 40,
        phase22_receipt=phase22,
        intake=intake,
        dispositions=dispositions,
        observed_at=phase22.qualified_at + timedelta(minutes=1),
    )
    assert tuple(item.receipt_id for item in receipts) == (
        "E7_ECONOMIC_NONCOMPENSATION",
        "E8_STRESS_INTEGRITY",
        "E9_TEMPORAL_REPLICATION",
    )
    assert all(
        item.phase22_qualification_artifact_sha256
        == phase22.qualification_artifact_sha256
        for item in receipts
    )


def test_arch_a_final_science_rejects_falsified_required_gate() -> None:
    phase22, intake, dispositions = _chain()
    altered = list(dispositions)
    altered[0] = replace(
        altered[0],
        passed=False,
        recommended_disposition="FALSIFIED_AND_CLOSED",
        blockers=("RUIN_GATE_FAILED",),
        failed_dimensions=("RUIN",),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="require positive frozen gates",
    ):
        build_architect_a_final_exam_scientific_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            dispositions=tuple(altered),
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_arch_a_final_science_rejects_qualification_artifact_drift() -> None:
    phase22, intake, dispositions = _chain()
    bad_intake = replace(
        intake,
        receipt_refs=tuple(
            (
                name,
                _sha("wrong-qualification")
                if name == "qualification_report_sha256"
                else digest,
            )
            for name, digest in intake.receipt_refs
        ),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="qualification artifact drift",
    ):
        build_architect_a_final_exam_scientific_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=bad_intake,
            dispositions=dispositions,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_closure41_derives_e7_e8_e9_only_from_positive_dimensions() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    package = _CLOSURE_FIXTURE._package()

    receipts = build_closure41_final_exam_scientific_controls(
        integrated_git_sha="a" * 40,
        phase22_receipt=phase22,
        closure_package=package,
        observed_at=phase22.qualified_at + timedelta(minutes=1),
    )

    assert tuple(item.receipt_id for item in receipts) == (
        "E7_ECONOMIC_NONCOMPENSATION",
        "E8_STRESS_INTEGRITY",
        "E9_TEMPORAL_REPLICATION",
    )
    assert tuple(item.producer_gate_id for item in receipts) == (
        "CIBO_CLOSURE41_E7_ECONOMIC_NONCOMPENSATION_V1",
        "CIBO_CLOSURE41_E8_STRESS_INTEGRITY_V1",
        "CIBO_CLOSURE41_E9_TEMPORAL_REPLICATION_V1",
    )


def test_closure41_e8_rejects_terminal_falsification_as_positive_pass() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    package = _CLOSURE_FIXTURE._package(fail_id="ADVERSARIAL_STRESS")

    with pytest.raises(
        CiboCapitalManagementError,
        match="requires positive terminal gate: ADVERSARIAL_STRESS",
    ):
        build_closure41_final_exam_scientific_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            closure_package=package,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )
