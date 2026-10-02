from __future__ import annotations

from pathlib import Path

from qore.infrastructure.cibo_arch_a1_internal_readiness import (
    A1_REQUIRED_ARTIFACTS,
    A1_REQUIRED_WORKFLOWS,
    EXPECTED_EXTERNAL_DEPENDENCIES,
    evaluate_architect_a1_internal_readiness,
)


def test_a1_internal_readiness_is_green_on_complete_branch() -> None:
    report = evaluate_architect_a1_internal_readiness(Path("."))

    assert report.engineering_ready is True
    assert report.owned_workstream_count == 18
    assert report.missing_artifacts == ()
    assert report.missing_workflows == ()
    assert report.expected_external_dependencies == EXPECTED_EXTERNAL_DEPENDENCIES
    assert report.scientific_closure_claimed is False
    assert report.integration_authority is False
    assert report.certification_ready is False


def test_a1_internal_readiness_fail_closes_on_missing_files(tmp_path: Path) -> None:
    report = evaluate_architect_a1_internal_readiness(tmp_path)

    assert report.engineering_ready is False
    assert report.missing_artifacts == A1_REQUIRED_ARTIFACTS
    assert report.missing_workflows == A1_REQUIRED_WORKFLOWS
    assert report.expected_external_dependencies == EXPECTED_EXTERNAL_DEPENDENCIES


def test_a1_external_dependencies_do_not_turn_into_engineering_failures() -> None:
    report = evaluate_architect_a1_internal_readiness(Path("."))

    assert report.engineering_ready is True
    assert "CANONICAL_PHASE22_V2_TERMINAL_SCIENTIFIC_INTAKE" in (
        report.expected_external_dependencies
    )
    assert "A2_COMPOUND_ENGINE_COMPLETED_AND_PROVEN" in (
        report.expected_external_dependencies
    )
    assert "INTEGRATOR_MASTER_LEDGER_RECONCILIATION" in (
        report.expected_external_dependencies
    )
