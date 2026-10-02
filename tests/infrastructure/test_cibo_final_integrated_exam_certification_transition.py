from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FINAL_INTEGRATED_EXAM_ID,
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_final_integrated_exam_certification_transition import (
    build_cibo_certification_seal,
    promote_final_certification_candidate,
    transition_final_integrated_exam_pass,
    transition_world_cup_exam_pass,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam import (
    WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_ID,
    WorldCupMaximumCapabilityReport,
    WorldCupMaximumCapabilityStatus,
    world_cup_policy_identity_sha256,
)

HEAD = "a" * 40
T0 = datetime(2026, 10, 1, 21, 0, tzinfo=UTC)


def _row(row_id: str, *, disposition: str | None) -> dict:
    return {
        "id": row_id,
        "kind": "CERTIFICATION" if row_id in {
            "FINAL_INTEGRATED_CIBO_EXAM",
            "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
        } else "SYSTEM",
        "mandatory": True,
        "certification_blocking": True,
        "current_maturity": (
            "OPEN_EXAM" if disposition is None else "COMPLETED_AND_PROVEN"
        ),
        "terminal_disposition": disposition,
        "evidence_refs": [] if disposition is None else [f"evidence:{row_id}"],
        "blockers": (
            ["EXAM_REQUIRED"] if disposition is None else []
        ),
        "next_gate": "next",
    }


def _ledger() -> dict:
    rows = [
        _row(f"WORK_{index:02d}", disposition="COMPLETED_AND_PROVEN")
        for index in range(62)
    ]
    rows.extend(
        (
            _row("FINAL_INTEGRATED_CIBO_EXAM", disposition=None),
            _row("WORLD_CUP_MAXIMUM_CAPABILITY_EXAM", disposition=None),
        )
    )
    return {
        "schema": "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1",
        "workstreams": rows,
        "current_summary": {
            "mandatory_count": 64,
            "terminal_count": 62,
            "open_count": 2,
            "zero_open_work_pass": False,
            "final_certification_candidate": False,
        },
    }


def _final() -> FinalIntegratedExamReport:
    return FinalIntegratedExamReport(
        exam_id=FINAL_INTEGRATED_EXAM_ID,
        status=FinalIntegratedExamStatus.PASS,
        integrated_head_sha=HEAD,
        blockers=(),
    )


def _world() -> WorldCupMaximumCapabilityReport:
    return WorldCupMaximumCapabilityReport(
        exam_id=WORLD_CUP_MAXIMUM_CAPABILITY_EXAM_ID,
        status=WorldCupMaximumCapabilityStatus.PASS,
        integrated_head_sha=HEAD,
        world_cup_policy_identity_sha256=world_cup_policy_identity_sha256(),
        final_integrated_exam_report_sha256="sha256:" + "b" * 64,
        evidence_sha256s=("sha256:" + "c" * 64,),
        blockers=(),
    )


def _strict_artifact() -> str:
    payload = {
        "schema": "QORE_CIBO_ZERO_OPEN_WORK_GATE_V1",
        "scope": "STRICT",
        "pass": True,
        "mandatory_workstream_count": 64,
        "terminal_workstream_count": 64,
        "open_workstream_ids": [],
        "certification_blocking_external_dependency_ids": [],
        "missing_required_artifacts": [],
        "high_signal_marker_hits": [],
        "inventory_paths": [],
        "inventory_assignments": [],
        "orphan_candidate_paths": [],
        "reasons": [],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def test_transition_sequence_62_to_64_to_seal() -> None:
    ledger63 = transition_final_integrated_exam_pass(
        ledger=_ledger(),
        report=_final(),
        integrated_git_sha=HEAD,
    )
    assert ledger63["current_summary"]["terminal_count"] == 63
    assert ledger63["current_summary"]["open_count"] == 1

    ledger64 = transition_world_cup_exam_pass(
        ledger=ledger63,
        report=_world(),
        integrated_git_sha=HEAD,
    )
    assert ledger64["current_summary"]["terminal_count"] == 64
    assert ledger64["current_summary"]["zero_open_work_pass"] is True

    seal = build_cibo_certification_seal(
        ledger=ledger64,
        strict_zero_open_artifact_json=_strict_artifact(),
        strict_evidence_git_sha=HEAD,
        final_integrated_exam=_final(),
        world_cup_exam=_world(),
        integrated_git_sha=HEAD,
        certified_at=T0,
    )
    assert seal.scientifically_certified is True
    assert seal.live_authorized is False
    assert seal.real_capital_authorized is False

    promoted = promote_final_certification_candidate(
        ledger=ledger64,
        seal=seal,
    )
    assert promoted["current_summary"]["final_certification_candidate"] is True


def test_final_transition_rejects_external_blocker() -> None:
    ledger = _ledger()
    ledger["workstreams"][0]["terminal_disposition"] = "EXTERNAL_DEPENDENCY_BLOCKED"
    ledger["workstreams"][0]["blockers"] = ["REAL_EXTERNAL_DEPENDENCY"]
    with pytest.raises(
        CiboCapitalManagementError,
        match="external blockers remain",
    ):
        transition_final_integrated_exam_pass(
            ledger=ledger,
            report=_final(),
            integrated_git_sha=HEAD,
        )


def test_seal_rejects_non_strict_artifact() -> None:
    ledger63 = transition_final_integrated_exam_pass(
        ledger=_ledger(),
        report=_final(),
        integrated_git_sha=HEAD,
    )
    ledger64 = transition_world_cup_exam_pass(
        ledger=ledger63,
        report=_world(),
        integrated_git_sha=HEAD,
    )
    payload = json.loads(_strict_artifact())
    payload["pass"] = False
    artifact = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with pytest.raises(
        CiboCapitalManagementError,
        match="strict zero-open artifact field mismatch: pass",
    ):
        build_cibo_certification_seal(
            ledger=ledger64,
            strict_zero_open_artifact_json=artifact,
            strict_evidence_git_sha=HEAD,
            final_integrated_exam=_final(),
            world_cup_exam=_world(),
            integrated_git_sha=HEAD,
            certified_at=T0,
        )
