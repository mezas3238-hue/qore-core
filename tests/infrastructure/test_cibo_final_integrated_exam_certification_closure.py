from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_assembly import (
    assemble_final_integrated_control_package,
    assess_assembled_final_integrated_exam,
)
from qore.infrastructure.cibo_final_integrated_exam_certification_closure import (
    CiboCertificationSealStatus,
    build_certification_closure_ledger,
    build_cibo_certification_seal,
    promote_certification_candidate_after_seal,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    CANONICAL_PROVIDER_IDENTITY,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam_assembly import (
    assemble_world_cup_control_package,
    assess_assembled_world_cup_exam,
)

_FINAL_FIXTURE_PATH = Path(__file__).with_name(
    "test_cibo_final_integrated_exam_assembly.py"
)
_FINAL_SPEC = importlib.util.spec_from_file_location(
    "_cert_closure_final_fixture",
    _FINAL_FIXTURE_PATH,
)
assert _FINAL_SPEC is not None and _FINAL_SPEC.loader is not None
_FINAL_FIXTURE = importlib.util.module_from_spec(_FINAL_SPEC)
_FINAL_SPEC.loader.exec_module(_FINAL_FIXTURE)

_WORLD_FIXTURE_PATH = Path(__file__).with_name(
    "test_cibo_world_cup_maximum_capability_exam_assembly.py"
)
_WORLD_SPEC = importlib.util.spec_from_file_location(
    "_cert_closure_world_fixture",
    _WORLD_FIXTURE_PATH,
)
assert _WORLD_SPEC is not None and _WORLD_SPEC.loader is not None
_WORLD_FIXTURE = importlib.util.module_from_spec(_WORLD_SPEC)
_WORLD_SPEC.loader.exec_module(_WORLD_FIXTURE)

SUCCESSOR_HOLDOUT_ID = "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"


def _exam_chain():
    phase21, phase22, final_receipts = _FINAL_FIXTURE._chain()
    final_package = assemble_final_integrated_control_package(
        integrated_git_sha=_FINAL_FIXTURE.HEAD,
        receipts=final_receipts,
    )
    final_report = assess_assembled_final_integrated_exam(
        package=final_package,
        phase21_manifest=phase21,
        phase22_receipt=phase22,
    )
    world_package = assemble_world_cup_control_package(
        integrated_git_sha=_FINAL_FIXTURE.HEAD,
        final_integrated_exam=final_report,
        receipts=_WORLD_FIXTURE._receipts(final_report),
    )
    world_report = assess_assembled_world_cup_exam(
        package=world_package,
        final_integrated_exam=final_report,
    )
    return phase22, final_package, final_report, world_package, world_report


def _ledger() -> dict:
    rows = []
    for index in range(62):
        rows.append(
            {
                "id": f"W{index:02d}",
                "kind": "SCIENCE",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "TERMINAL_PROVEN",
                "terminal_disposition": "COMPLETED_AND_PROVEN",
                "evidence_refs": [f"evidence:{index}"],
                "blockers": [],
                "next_gate": "Terminal.",
            }
        )
    rows.extend(
        [
            {
                "id": "FINAL_INTEGRATED_CIBO_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": ["protocol:final"],
                "blockers": ["ACTUAL_EXAM_NOT_RUN"],
                "next_gate": "Run Final.",
            },
            {
                "id": "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": ["protocol:world"],
                "blockers": ["ACTUAL_EXAM_NOT_RUN"],
                "next_gate": "Run World Cup.",
            },
        ]
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


def test_closure_changes_only_two_exam_rows_and_reaches_64_64() -> None:
    phase22, final_package, final_report, world_package, world_report = _exam_chain()
    before = _ledger()
    closed, transition = build_certification_closure_ledger(
        pre_ledger=before,
        holdout_candidate_id=SUCCESSOR_HOLDOUT_ID,
        final_package=final_package,
        final_report=final_report,
        world_cup_package=world_package,
        world_cup_report=world_report,
    )
    assert transition.changed_workstream_ids == (
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    )
    assert closed["current_summary"] == {
        "mandatory_count": 64,
        "terminal_count": 64,
        "open_count": 0,
        "zero_open_work_pass": True,
        "final_certification_candidate": False,
    }
    assert closed["workstreams"][:62] == before["workstreams"][:62]
    assert all(
        row["terminal_disposition"] == "COMPLETED_AND_PROVEN"
        for row in closed["workstreams"][-2:]
    )
    assert transition.phase22_qualification_artifact_sha256 == (
        phase22.qualification_artifact_sha256
    )


def test_closure_refuses_external_blocker_before_exam_terminalization() -> None:
    _phase22, final_package, final_report, world_package, world_report = _exam_chain()
    before = _ledger()
    before["workstreams"][0]["terminal_disposition"] = "EXTERNAL_DEPENDENCY_BLOCKED"
    before["workstreams"][0]["blockers"] = ["REAL_EVIDENCE_REQUIRED"]
    with pytest.raises(
        CiboCapitalManagementError,
        match="clean 64/62/2 pre-close ledger",
    ):
        build_certification_closure_ledger(
            pre_ledger=before,
            holdout_candidate_id=SUCCESSOR_HOLDOUT_ID,
            final_package=final_package,
            final_report=final_report,
            world_cup_package=world_package,
            world_cup_report=world_report,
        )


def test_certification_seal_requires_strict_zero_open_pass() -> None:
    phase22, final_package, final_report, world_package, world_report = _exam_chain()
    closed, transition = build_certification_closure_ledger(
        pre_ledger=_ledger(),
        holdout_candidate_id=SUCCESSOR_HOLDOUT_ID,
        final_package=final_package,
        final_report=final_report,
        world_cup_package=world_package,
        world_cup_report=world_report,
    )
    strict = json.loads(_strict_artifact())
    strict["pass"] = False
    bad = json.dumps(strict, indent=2, sort_keys=True) + "\n"
    with pytest.raises(
        CiboCapitalManagementError,
        match="STRICT field mismatch: pass",
    ):
        build_cibo_certification_seal(
            transition=transition,
            closed_ledger=closed,
            strict_zero_open_artifact_json=bad,
            closure_head_sha="c" * 40,
            phase22_receipt=phase22,
            certified_at=phase22.qualified_at + timedelta(days=1),
        )


def test_certification_seal_certifies_science_but_grants_no_operations() -> None:
    phase22, final_package, final_report, world_package, world_report = _exam_chain()
    closed, transition = build_certification_closure_ledger(
        pre_ledger=_ledger(),
        holdout_candidate_id=SUCCESSOR_HOLDOUT_ID,
        final_package=final_package,
        final_report=final_report,
        world_cup_package=world_package,
        world_cup_report=world_report,
    )
    seal = build_cibo_certification_seal(
        transition=transition,
        closed_ledger=closed,
        strict_zero_open_artifact_json=_strict_artifact(),
        closure_head_sha="c" * 40,
        phase22_receipt=phase22,
        certified_at=phase22.qualified_at + timedelta(days=1),
    )
    assert seal.status is CiboCertificationSealStatus.CERTIFIED
    assert seal.holdout_candidate_id == SUCCESSOR_HOLDOUT_ID
    assert seal.provider_identity == CANONICAL_PROVIDER_IDENTITY
    assert seal.mandatory_count == 64
    assert seal.terminal_count == 64
    assert seal.open_count == 0
    assert seal.source_truth_receipt_sha256.startswith("sha256:")
    assert seal.provider_risk_cma_receipt_sha256.startswith("sha256:")
    assert seal.scientific_closure_receipt_sha256.startswith("sha256:")
    assert seal.final_integrated_package_sha256.startswith("sha256:")
    assert seal.world_cup_package_sha256.startswith("sha256:")
    assert seal.policy_identity_sha256.startswith("sha256:")
    assert seal.live_authorized is False
    assert seal.real_capital_authorized is False
    assert seal.production_authorized is False
    assert seal.merge_authorized is False
    assert seal.production_authority is False
    assert seal.fingerprint().startswith("sha256:")

    promoted = promote_certification_candidate_after_seal(
        closed_ledger=closed,
        transition=transition,
        seal=seal,
    )
    assert promoted["current_summary"] == {
        "mandatory_count": 64,
        "terminal_count": 64,
        "open_count": 0,
        "zero_open_work_pass": True,
        "final_certification_candidate": True,
    }



def test_candidate_cannot_promote_before_certification_seal() -> None:
    _phase22, final_package, final_report, world_package, world_report = _exam_chain()
    closed, transition = build_certification_closure_ledger(
        pre_ledger=_ledger(),
        holdout_candidate_id=SUCCESSOR_HOLDOUT_ID,
        final_package=final_package,
        final_report=final_report,
        world_cup_package=world_package,
        world_cup_report=world_report,
    )
    tampered = dict(closed)
    tampered["current_summary"] = dict(closed["current_summary"])
    tampered["current_summary"]["final_certification_candidate"] = True

    phase22 = _phase22
    seal = build_cibo_certification_seal(
        transition=transition,
        closed_ledger=closed,
        strict_zero_open_artifact_json=_strict_artifact(),
        closure_head_sha="c" * 40,
        phase22_receipt=phase22,
        certified_at=phase22.qualified_at + timedelta(days=1),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="closed-ledger digest drift",
    ):
        promote_certification_candidate_after_seal(
            closed_ledger=tampered,
            transition=transition,
            seal=seal,
        )


def test_certification_seal_rejects_invalid_holdout_identity_shape() -> None:
    phase22, final_package, final_report, world_package, world_report = _exam_chain()
    closed, transition = build_certification_closure_ledger(
        pre_ledger=_ledger(),
        holdout_candidate_id=SUCCESSOR_HOLDOUT_ID,
        final_package=final_package,
        final_report=final_report,
        world_cup_package=world_package,
        world_cup_report=world_report,
    )
    seal = build_cibo_certification_seal(
        transition=transition,
        closed_ledger=closed,
        strict_zero_open_artifact_json=_strict_artifact(),
        closure_head_sha="c" * 40,
        phase22_receipt=phase22,
        certified_at=phase22.qualified_at + timedelta(days=1),
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="holdout identity invalid",
    ):
        replace(
            seal,
            holdout_candidate_id="CIBO_USD60_6M_HOLDOUT_2017H1_BURNED",
        )
