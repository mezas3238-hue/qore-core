"""Apply Architect-A Phase22 scientific dispositions to the canonical ledger.

This adapter grants no scientific result by itself. It only applies already
validated disposition receipts to rows that are currently
EXTERNAL_DEPENDENCY_BLOCKED. Missing or still-external science remains blocked.
"""

from __future__ import annotations

import copy
from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2ScientificClosureBatch,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_ALLOWED_TERMINAL = {
    "COMPLETED_AND_PROVEN",
    "FALSIFIED_AND_CLOSED",
    "SUPERSEDED_WITH_PROVEN_LINEAGE",
    "EXTERNAL_DEPENDENCY_BLOCKED",
}


def _rows(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(ledger, dict) or ledger.get("schema") != _LEDGER_SCHEMA:
        raise CiboCapitalManagementError(
            "scientific ledger reconciliation schema drift"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "scientific ledger reconciliation rows invalid"
        )
    return rows


def _row_map(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _rows(ledger):
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id:
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation row id invalid"
            )
        if row_id in result:
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation duplicate row id"
            )
        result[row_id] = row
    return result


def _validate_batch_receipts(
    *,
    batch: ArchitectAPhase22V2ScientificClosureBatch,
    receipts: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
) -> dict[str, ArchitectAPhase22V2ScientificDispositionReceipt]:
    if not isinstance(batch, ArchitectAPhase22V2ScientificClosureBatch):
        raise CiboCapitalManagementError(
            "scientific ledger reconciliation requires canonical closure batch"
        )
    if (
        not isinstance(receipts, tuple)
        or any(
            not isinstance(item, ArchitectAPhase22V2ScientificDispositionReceipt)
            for item in receipts
        )
    ):
        raise CiboCapitalManagementError(
            "scientific ledger reconciliation requires canonical receipts"
        )

    by_id: dict[str, ArchitectAPhase22V2ScientificDispositionReceipt] = {}
    for receipt in receipts:
        if receipt.phase22_manifest_sha256 != batch.phase22_manifest_sha256:
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation manifest drift"
            )
        if receipt.workstream_id in by_id:
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation duplicate receipt"
            )
        by_id[receipt.workstream_id] = receipt

    expected_receipt_ids = (
        set(batch.completed_ids)
        | set(batch.falsified_ids)
        | set(batch.external_ids)
    )
    if set(by_id) != expected_receipt_ids:
        raise CiboCapitalManagementError(
            "scientific ledger reconciliation receipt/batch partition drift"
        )

    for workstream_id in batch.completed_ids:
        if by_id[workstream_id].recommended_disposition != "COMPLETED_AND_PROVEN":
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation completed partition drift"
            )
    for workstream_id in batch.falsified_ids:
        if by_id[workstream_id].recommended_disposition != "FALSIFIED_AND_CLOSED":
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation falsified partition drift"
            )
    for workstream_id in batch.external_ids:
        if by_id[workstream_id].recommended_disposition != "EXTERNAL_DEPENDENCY_BLOCKED":
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation external partition drift"
            )
    return by_id


def _evidence_ref(
    receipt: ArchitectAPhase22V2ScientificDispositionReceipt,
) -> str:
    return (
        "phase22-v2-science:"
        + receipt.source_gate_id
        + ":"
        + receipt.source_gate_evidence_sha256
    )


def apply_architect_a_phase22_scientific_dispositions(
    *,
    ledger: dict[str, Any],
    batch: ArchitectAPhase22V2ScientificClosureBatch,
    receipts: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
) -> dict[str, Any]:
    """Apply evidence-bound A dispositions without claiming global certification."""

    result = copy.deepcopy(ledger)
    rows = _row_map(result)
    by_id = _validate_batch_receipts(batch=batch, receipts=receipts)

    for workstream_id, receipt in by_id.items():
        row = rows.get(workstream_id)
        if row is None:
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation missing target row: "
                + workstream_id
            )
        if row.get("mandatory") is not True:
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation target must be mandatory"
            )
        if row.get("certification_blocking") is not True:
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation target must be certification-blocking"
            )
        if row.get("terminal_disposition") != "EXTERNAL_DEPENDENCY_BLOCKED":
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation target is not external-blocked: "
                + workstream_id
            )

        evidence = row.get("evidence_refs")
        if not isinstance(evidence, list):
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation evidence_refs invalid"
            )
        ref = _evidence_ref(receipt)
        if ref not in evidence:
            evidence.append(ref)
        manifest_ref = "phase22-v2-manifest:" + receipt.phase22_manifest_sha256
        if manifest_ref not in evidence:
            evidence.append(manifest_ref)

        if receipt.recommended_disposition == "COMPLETED_AND_PROVEN":
            row["current_maturity"] = (
                "PHASE22_V2_EMPIRICAL_COMPLETED_AND_PROVEN"
            )
            row["terminal_disposition"] = "COMPLETED_AND_PROVEN"
            row["blockers"] = []
            row["next_gate"] = (
                "Terminal scientific proof; reopen only on contradiction or regression."
            )
        elif receipt.recommended_disposition == "FALSIFIED_AND_CLOSED":
            row["current_maturity"] = "PHASE22_V2_EMPIRICAL_FALSIFIED_AND_CLOSED"
            row["terminal_disposition"] = "FALSIFIED_AND_CLOSED"
            row["blockers"] = []
            row["next_gate"] = (
                "Terminal falsification; any successor hypothesis requires new evidence."
            )
        elif receipt.recommended_disposition == "EXTERNAL_DEPENDENCY_BLOCKED":
            row["current_maturity"] = (
                "PHASE22_V2_EMPIRICAL_EXTERNAL_DEPENDENCY_RETAINED"
            )
            row["terminal_disposition"] = "EXTERNAL_DEPENDENCY_BLOCKED"
            row["blockers"] = list(receipt.blockers) or [
                "PHASE22_V2_EXTERNAL_DEPENDENCY_REMAINS"
            ]
            row["next_gate"] = (
                "Remain fail-closed until the explicit external dependency is satisfied."
            )
        else:
            raise CiboCapitalManagementError(
                "scientific ledger reconciliation unknown disposition"
            )

    mandatory = [
        item for item in _rows(result) if item.get("mandatory") is True
    ]
    if len(mandatory) != 64:
        raise CiboCapitalManagementError(
            "scientific ledger reconciliation requires 64 mandatory rows"
        )
    terminal = [
        item
        for item in mandatory
        if item.get("terminal_disposition") in _ALLOWED_TERMINAL
    ]
    open_rows = [
        item for item in mandatory if item.get("terminal_disposition") is None
    ]
    if len(terminal) + len(open_rows) != len(mandatory):
        raise CiboCapitalManagementError(
            "scientific ledger reconciliation encountered invalid disposition"
        )

    summary = result.get("current_summary")
    if not isinstance(summary, dict):
        raise CiboCapitalManagementError(
            "scientific ledger reconciliation summary missing"
        )
    result["current_summary"] = {
        "mandatory_count": 64,
        "terminal_count": len(terminal),
        "open_count": len(open_rows),
        "zero_open_work_pass": len(open_rows) == 0,
        "final_certification_candidate": False,
    }
    return result
