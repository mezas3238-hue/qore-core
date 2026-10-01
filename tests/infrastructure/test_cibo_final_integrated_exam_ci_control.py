from __future__ import annotations

import importlib.util
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.cibo_arch_a_final_source_truth_control import (
    FinalSourceTruthManifest,
    build_final_source_truth_control,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_ci_control import (
    FinalCiCheckResult,
    FinalCiScope,
    FinalCiWorkflowRequirement,
    build_p3_ci_clear_control,
)

_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_final_ci_fixture", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _chain():
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    manifest = FinalSourceTruthManifest(
        schema="qore.cibo.final-source-truth-manifest.v2",
        integrated_git_sha="a" * 40,
        architect_a_head_sha="b" * 40,
        architect_b_head_sha="c" * 40,
        phase22_handoff_manifest_sha256=_sha("phase22-handoff"),
        mandatory_count=64,
        terminal_count=62,
        open_ids=(
            "FINAL_INTEGRATED_CIBO_EXAM",
            "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
        ),
        file_sha256s=(
            ("master_ledger", _sha("master")),
            ("source_truth_reconciliation", _sha("truth")),
            ("final_integrated_exam_protocol", _sha("final")),
            ("world_cup_exam_protocol", _sha("world")),
            ("certification_sequence", _sha("sequence")),
            ("architect_a_science", _sha("a-science")),
            ("architect_b_phase22", _sha("b-phase22")),
        ),
        unaccounted_files=(),
        certification_critical_external_blockers=(),
        stale_current_state_claims=(),
    )
    p1 = build_final_source_truth_control(
        manifest=manifest,
        phase22_receipt=phase22,
        observed_at=phase22.qualified_at + timedelta(minutes=1),
    )
    scope = FinalCiScope(
        scope_id="CIBO_FINAL_CERTIFICATION_CI_SCOPE_V1",
        integrated_git_sha=manifest.integrated_git_sha,
        source_truth_control_sha256=p1.fingerprint(),
        requirements=(
            FinalCiWorkflowRequirement(
                workflow_name="QORE CIBO Zero Open Work Gate",
                workflow_path=".github/workflows/cibo-zero-open-work-gate.yml",
                workflow_file_sha256=_sha("zero-open"),
            ),
            FinalCiWorkflowRequirement(
                workflow_name="QORE CIBO Final Exam Control Receipt V2",
                workflow_path=".github/workflows/cibo-final-exam-control-receipt-v2.yml",
                workflow_file_sha256=_sha("final-control"),
            ),
        ),
        frozen_at=phase22.qualified_at + timedelta(minutes=2),
        frozen=True,
    )
    results = tuple(
        FinalCiCheckResult(
            workflow_name=item.workflow_name,
            workflow_path=item.workflow_path,
            head_sha=manifest.integrated_git_sha,
            run_id=index + 100,
            status="completed",
            conclusion="success",
            observed_at=scope.frozen_at + timedelta(minutes=1),
        )
        for index, item in enumerate(scope.requirements)
    )
    return phase22, p1, scope, results


def test_p3_requires_all_frozen_checks_green_on_same_head() -> None:
    phase22, p1, scope, results = _chain()
    receipt = build_p3_ci_clear_control(
        scope=scope,
        results=results,
        source_truth_control=p1,
        phase22_receipt=phase22,
        observed_at=scope.frozen_at + timedelta(minutes=2),
    )
    assert receipt.receipt_id == "P3_CERTIFICATION_CI_CLEAR"
    assert receipt.integrated_git_sha == "a" * 40


def test_p3_rejects_missing_required_check() -> None:
    phase22, p1, scope, results = _chain()
    with pytest.raises(
        CiboCapitalManagementError,
        match="required workflow results missing",
    ):
        build_p3_ci_clear_control(
            scope=scope,
            results=results[:-1],
            source_truth_control=p1,
            phase22_receipt=phase22,
            observed_at=scope.frozen_at + timedelta(minutes=2),
        )


def test_p3_rejects_cross_head_check() -> None:
    phase22, p1, scope, results = _chain()
    bad = FinalCiCheckResult(
        workflow_name=results[0].workflow_name,
        workflow_path=results[0].workflow_path,
        head_sha="d" * 40,
        run_id=results[0].run_id,
        status="completed",
        conclusion="success",
        observed_at=results[0].observed_at,
    )
    with pytest.raises(CiboCapitalManagementError, match="workflow HEAD drift"):
        build_p3_ci_clear_control(
            scope=scope,
            results=(bad, results[1]),
            source_truth_control=p1,
            phase22_receipt=phase22,
            observed_at=scope.frozen_at + timedelta(minutes=2),
        )
