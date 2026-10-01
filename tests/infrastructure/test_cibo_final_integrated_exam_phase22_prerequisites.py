from __future__ import annotations

import importlib.util
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from qore.infrastructure.cibo_arch_a_final_exam_system_controls import (
    build_architect_a_final_exam_system_controls,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_phase22_prerequisites import (
    build_phase22_prerequisite_controls,
)

_SYSTEM_FIXTURE_PATH = Path(__file__).with_name(
    "test_cibo_arch_a_final_exam_system_controls.py"
)
_SYSTEM_SPEC = importlib.util.spec_from_file_location(
    "_phase22_prereq_system_fixture",
    _SYSTEM_FIXTURE_PATH,
)
assert _SYSTEM_SPEC is not None and _SYSTEM_SPEC.loader is not None
_SYSTEM_FIXTURE = importlib.util.module_from_spec(_SYSTEM_SPEC)
_SYSTEM_SPEC.loader.exec_module(_SYSTEM_FIXTURE)


def _chain():
    phase22, intake, mechanism, compound, capital_truth = _SYSTEM_FIXTURE._chain()
    observed_at = phase22.qualified_at + timedelta(minutes=1)
    system = build_architect_a_final_exam_system_controls(
        integrated_git_sha="a" * 40,
        phase22_receipt=phase22,
        intake=intake,
        mechanism=mechanism,
        compound_closure=compound,
        capital_truth=capital_truth,
        observed_at=observed_at,
    )
    return phase22, intake, system, observed_at


def test_builds_p4_p5_p6_from_phase22_chain() -> None:
    phase22, intake, system, observed_at = _chain()
    receipts = build_phase22_prerequisite_controls(
        integrated_git_sha="a" * 40,
        phase22_receipt=phase22,
        intake=intake,
        system_controls=system,
        observed_at=observed_at,
    )
    assert tuple(item.receipt_id for item in receipts) == (
        "P4_PROVIDER_RISK_CMA_FORWARD_TRUTH",
        "P5_PHASE20D_PASS",
        "P6_POLICY_CALIBRATION_FREEZE",
    )


def test_rejects_missing_system_control() -> None:
    phase22, intake, system, observed_at = _chain()
    with pytest.raises(CiboCapitalManagementError, match="missing system controls"):
        build_phase22_prerequisite_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            system_controls=system[:-1],
            observed_at=observed_at,
        )


def test_rejects_phase22_fail_intake() -> None:
    phase22, intake, system, observed_at = _chain()
    intake = replace(intake, qualification_status="FAIL")
    with pytest.raises(
        CiboCapitalManagementError,
        match="admissible Phase22 PASS intake",
    ):
        build_phase22_prerequisite_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            intake=intake,
            system_controls=system,
            observed_at=observed_at,
        )
