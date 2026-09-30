from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


MODULE_PATH = (\n    Path(__file__).resolve().parents[2]\n    / "scripts/cibo_ab_integration_gate.py"\n)
SPEC = importlib.util.spec_from_file_location("cibo_ab_integration_gate", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def _state():
    matrix = {
        "schema": "CIBO_AB_INTEGRATION_ACCEPTANCE_V1",
        "common_split_base_sha": "a" * 40,
        "architect_a": {
            "pr": 660,
            "accepted_head_sha": "b" * 40,
            "latest_observed_head_sha": "c" * 40,
            "support_blockers": ["A-BLOCKER"],
        },
        "architect_b": {
            "pr": 661,
            "accepted_head_sha": "d" * 40,
            "latest_observed_head_sha": "e" * 40,
            "support_blockers": [],
        },
        "integrated_terminal_ids": ["T01"],
        "integration_ready": False,
        "certification_ready": False,
        "productive_authority": False,
    }
    ledger = {
        "workstreams": [
            {
                "id": "T01",
                "mandatory": True,
                "terminal_disposition": "COMPLETED_AND_PROVEN",
            },
            {"id": "T02", "mandatory": True, "terminal_disposition": None},
            {
                "id": "FINAL_INTEGRATED_CIBO_EXAM",
                "mandatory": True,
                "certification_blocking": True,
                "terminal_disposition": None,
            },
            {
                "id": "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
                "mandatory": True,
                "certification_blocking": True,
                "terminal_disposition": None,
            },
        ],
        "current_summary": {
            "mandatory_count": 4,
            "terminal_count": 1,
            "open_count": 3,
            "zero_open_work_pass": False,
            "final_certification_candidate": False,
        },
    }
    return matrix, ledger


def test_consistent_partial_integration_is_valid_but_not_certified() -> None:
    matrix, ledger = _state()
    assert gate.validate_state(matrix, ledger) == []
    errors = gate.validate_state(matrix, ledger, enforce_certification=True)
    assert "CIBO A+B integration is not certification-ready" in errors


def test_terminal_union_must_match_ledger() -> None:
    matrix, ledger = _state()
    matrix["integrated_terminal_ids"] = []
    assert "integrated terminal set does not match canonical ledger" in gate.validate_state(
        matrix, ledger
    )


def test_support_blockers_prevent_integration_ready() -> None:
    matrix, ledger = _state()
    matrix["integration_ready"] = True
    assert "integration_ready cannot coexist with support blockers" in gate.validate_state(
        matrix, ledger
    )


def test_open_work_cannot_be_relabelled_final_candidate() -> None:
    matrix, ledger = _state()
    ledger = copy.deepcopy(ledger)
    ledger["current_summary"]["zero_open_work_pass"] = True
    ledger["current_summary"]["final_certification_candidate"] = True
    errors = gate.validate_state(matrix, ledger)
    assert "zero-open cannot pass while mandatory work remains open" in errors
    assert "final certification candidate cannot be true with open work" in errors


def test_integrator_can_never_grant_productive_authority() -> None:
    matrix, ledger = _state()
    matrix["productive_authority"] = True
    assert "integrator acceptance cannot grant productive authority" in gate.validate_state(
        matrix, ledger
    )


def test_world_cup_exam_cannot_be_removed_from_mandatory_closure() -> None:
    matrix, ledger = _state()
    world_cup = next(
        row
        for row in ledger["workstreams"]
        if row["id"] == "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"
    )
    world_cup["mandatory"] = False
    world_cup["certification_blocking"] = False
    ledger["current_summary"]["mandatory_count"] = 3
    ledger["current_summary"]["open_count"] = 2

    errors = gate.validate_state(matrix, ledger)

    assert (
        "required certification workstream is not mandatory: "
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"
    ) in errors
    assert (
        "required certification workstream is not blocking: "
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"
    ) in errors
