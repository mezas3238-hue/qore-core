from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
    PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
    ArchitectAPhase22V2ScientificClosureBatch,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_final_integrated_exam_arch_b_ledger_reconciliation import (
    ArchitectBPhase22FinalDisposition,
    ArchitectBPhase22FinalDispositionPackage,
    required_arch_b_final_workstream_ids,
)
from qore.infrastructure.cibo_final_integrated_exam_pre_exam_ledger import (
    reconcile_pre_exam_ledger,
    reconcile_pre_exam_ledger_from_scientific_closure_41,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    CANONICAL_POLICY_IDENTITY,
    CANONICAL_PROVIDER_IDENTITY,
    EXTERNAL,
    FRESH_OOS_ID,
    OPEN_PREIMAGE,
    SCIENTIFIC_CLOSURE_41_IDS,
    ScientificClosure41Evidence,
    build_scientific_closure_41_package,
)

A_MANIFEST = "sha256:" + "a" * 64
B_MANIFEST = "sha256:" + "b" * 64
EVIDENCE = "sha256:" + "c" * 64
HEAD = "d" * 40
CLOSURE_MANIFEST = "sha256:" + "e" * 64
CLOSURE_EVIDENCE = "sha256:" + "f" * 64
CLOSURE_LINEAGE = "sha256:" + "1" * 64
SUCCESSOR_HOLDOUT_ID = "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"


def _row(row_id: str, disposition: str) -> dict:
    return {
        "id": row_id,
        "kind": "SYSTEM",
        "mandatory": True,
        "certification_blocking": True,
        "current_maturity": "STATE",
        "terminal_disposition": disposition,
        "evidence_refs": [],
        "blockers": (
            ["WAIT"] if disposition == "EXTERNAL_DEPENDENCY_BLOCKED" else []
        ),
        "next_gate": "next",
    }


def _ledger() -> dict:
    a_ids = tuple(_PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM)
    b_ids = required_arch_b_final_workstream_ids()
    rows = [
        _row(row_id, "EXTERNAL_DEPENDENCY_BLOCKED")
        for row_id in (*a_ids, *b_ids)
    ]
    rows.extend(
        _row(f"WORK_{index:02d}", "COMPLETED_AND_PROVEN")
        for index in range(17)
    )
    rows.extend(
        (
            {
                "id": "FINAL_INTEGRATED_CIBO_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": [],
                "blockers": ["EXAM_REQUIRED"],
                "next_gate": "run",
            },
            {
                "id": "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": [],
                "blockers": ["EXAM_REQUIRED"],
                "next_gate": "run",
            },
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




def _closure41_ledger() -> dict:
    rows = []
    for row_id in SCIENTIFIC_CLOSURE_41_IDS:
        if row_id == FRESH_OOS_ID:
            rows.append(
                {
                    "id": row_id,
                    "kind": "CERTIFICATION",
                    "mandatory": True,
                    "certification_blocking": True,
                    "current_maturity": "OPEN",
                    "terminal_disposition": None,
                    "evidence_refs": [],
                    "blockers": ["FRESH_OOS_REQUIRED"],
                    "next_gate": "run",
                }
            )
        else:
            rows.append(_row(row_id, EXTERNAL))
    rows.extend(
        _row(f"OTHER_{index:02d}", "COMPLETED_AND_PROVEN")
        for index in range(21)
    )
    rows.extend(
        (
            {
                "id": "FINAL_INTEGRATED_CIBO_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": [],
                "blockers": ["EXAM_REQUIRED"],
                "next_gate": "run",
            },
            {
                "id": "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": [],
                "blockers": ["EXAM_REQUIRED"],
                "next_gate": "run",
            },
        )
    )
    return {
        "schema": "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1",
        "workstreams": rows,
        "current_summary": {
            "mandatory_count": 64,
            "terminal_count": 61,
            "open_count": 3,
            "zero_open_work_pass": False,
            "final_certification_candidate": False,
        },
    }


def _closure41_package():
    evidence = tuple(
        ScientificClosure41Evidence(
            workstream_id=workstream_id,
            previous_disposition=(
                OPEN_PREIMAGE if workstream_id == FRESH_OOS_ID else EXTERNAL
            ),
            scientific_hypothesis=f"Frozen {workstream_id} hypothesis",
            evidence_refs=(f"artifact://{workstream_id}",),
            evidence_sha256s=(CLOSURE_EVIDENCE,),
            population_identity="phase22-v6:canonical",
            policy_identity=CANONICAL_POLICY_IDENTITY,
            provider_identity=CANONICAL_PROVIDER_IDENTITY,
            causal_lineage=CLOSURE_LINEAGE,
            economic_result="PASS",
            stress_result="PASS",
            temporal_replication_result="PASS",
            integrity_result="PASS",
            source_gate_status="PASS",
            terminal_reason=f"Terminal {workstream_id}",
            evaluated_at=datetime(2026, 10, 2, 12, 0, tzinfo=UTC),
            phase22_manifest_sha256=CLOSURE_MANIFEST,
            holdout_id=SUCCESSOR_HOLDOUT_ID,
        )
        for workstream_id in SCIENTIFIC_CLOSURE_41_IDS
    )
    return build_scientific_closure_41_package(
        phase22_manifest_sha256=CLOSURE_MANIFEST,
        evidence=evidence,
    )


def _a_receipts():
    return tuple(
        ArchitectAPhase22V2ScientificDispositionReceipt(
            schema=PHASE22_V2_SCIENTIFIC_DISPOSITION_SCHEMA,
            workstream_id=workstream_id,
            phase22_manifest_sha256=A_MANIFEST,
            source_gate_id="gate:" + workstream_id,
            source_gate_evidence_sha256=EVIDENCE,
            source_gate_status="PASS",
            passed=True,
            recommended_disposition="COMPLETED_AND_PROVEN",
            blockers=(),
            failed_dimensions=(),
            owner_review_approved=(workstream_id == "GEN-C14"),
        )
        for workstream_id in _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM
    )


def _a_batch() -> ArchitectAPhase22V2ScientificClosureBatch:
    ids = tuple(_PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM)
    return ArchitectAPhase22V2ScientificClosureBatch(
        phase22_manifest_sha256=A_MANIFEST,
        receipt_count=len(ids),
        resolved_count=len(ids),
        completed_ids=ids,
        falsified_ids=(),
        external_ids=(),
        missing_ids=(),
        all_scientific_workstreams_resolved=True,
    )


def _b_package() -> ArchitectBPhase22FinalDispositionPackage:
    dispositions = tuple(
        ArchitectBPhase22FinalDisposition(
            workstream_id=workstream_id,
            recommendation=(
                "SUPERSEDED_WITH_PROVEN_LINEAGE"
                if workstream_id == "FORWARD_QUALIFICATION"
                else "COMPLETED_AND_PROVEN"
            ),
            evidence_sha256=EVIDENCE,
            evidence_ref="artifact:" + workstream_id,
        )
        for workstream_id in required_arch_b_final_workstream_ids()
    )
    return ArchitectBPhase22FinalDispositionPackage(
        schema="QORE_CIBO_ARCH_B_PHASE22_FINAL_DISPOSITION_PACKAGE_V1",
        architect_b_head_sha=HEAD,
        phase22_manifest_sha256=B_MANIFEST,
        dispositions=dispositions,
        fresh_execution_complete=True,
        economic_qualification_executed=True,
    )


def test_reconciles_a_and_b_to_exact_pre_exam_topology() -> None:
    result = reconcile_pre_exam_ledger(
        ledger=_ledger(),
        architect_a_batch=_a_batch(),
        architect_a_receipts=_a_receipts(),
        architect_b_package=_b_package(),
    )
    assert result["current_summary"] == {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    assert not [
        row
        for row in result["workstreams"]
        if row.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
    ]


def test_closure41_reconciles_directly_to_exact_pre_exam_topology() -> None:
    result = reconcile_pre_exam_ledger_from_scientific_closure_41(
        ledger=_closure41_ledger(),
        closure_package=_closure41_package(),
    )
    assert result["current_summary"] == {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    open_ids = tuple(
        row["id"]
        for row in result["workstreams"]
        if row["terminal_disposition"] is None
    )
    assert open_ids == (
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    )
    assert not [
        row
        for row in result["workstreams"]
        if row.get("terminal_disposition") == EXTERNAL
    ]
