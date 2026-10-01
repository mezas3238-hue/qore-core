"""Governed application of Architect-A Phase22 scientific dispositions.

This transition resolves only the 35 Architect-A workstreams whose external
blockers are explicitly covered by the Phase22 V2 scientific evidence matrix.
It cannot close B-side external dependencies or either certification exam.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2ScientificClosureBatch,
    ArchitectAPhase22V2ScientificDispositionReceipt,
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_ALLOWED_SOURCE_DISPOSITION = "EXTERNAL_DEPENDENCY_BLOCKED"
_ALLOWED_TARGET_DISPOSITIONS = {
    "COMPLETED_AND_PROVEN",
    "FALSIFIED_AND_CLOSED",
}
_EXAM_IDS = {
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
}
_A_IDS = tuple(_PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM)


def _canonical_sha(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _rows(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(ledger, dict) or ledger.get("schema") != _LEDGER_SCHEMA:
        raise CiboCapitalManagementError(
            "scientific ledger transition schema drift"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "scientific ledger transition workstreams invalid"
        )
    return rows


def _row_map(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in _rows(ledger):
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id:
            raise CiboCapitalManagementError(
                "scientific ledger transition row id invalid"
            )
        if row_id in by_id:
            raise CiboCapitalManagementError(
                "scientific ledger transition duplicate row id"
            )
        by_id[row_id] = row
    return by_id


def _receipt_sha(
    receipt: ArchitectAPhase22V2ScientificDispositionReceipt,
) -> str:
    return _canonical_sha(receipt.as_dict())


@dataclass(frozen=True, slots=True)
class ArchitectAScientificLedgerTransitionReceipt:
    phase22_manifest_sha256: str
    pre_ledger_sha256: str
    post_ledger_sha256: str
    completed_ids: tuple[str, ...]
    falsified_ids: tuple[str, ...]
    residual_external_ids: tuple[str, ...]
    exact_a_surface_resolved: bool
    certification_claimed: bool = False
    production_authority: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        if not self.phase22_manifest_sha256.startswith("sha256:"):
            raise CiboCapitalManagementError(
                "scientific ledger transition manifest digest invalid"
            )
        for name in ("pre_ledger_sha256", "post_ledger_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("sha256:"):
                raise CiboCapitalManagementError(
                    f"scientific ledger transition {name} invalid"
                )
        if set(self.completed_ids) & set(self.falsified_ids):
            raise CiboCapitalManagementError(
                "scientific ledger transition disposition overlap"
            )
        if set(self.completed_ids) | set(self.falsified_ids) != set(_A_IDS):
            raise CiboCapitalManagementError(
                "scientific ledger transition A-surface coverage drift"
            )
        if type(self.exact_a_surface_resolved) is not bool or not self.exact_a_surface_resolved:
            raise CiboCapitalManagementError(
                "scientific ledger transition requires exact A closure"
            )
        if (
            self.certification_claimed
            or self.production_authority
            or self.merge_authority
        ):
            raise CiboCapitalManagementError(
                "scientific ledger transition grants no authority"
            )

    def fingerprint(self) -> str:
        return _canonical_sha(asdict(self))


def apply_architect_a_scientific_dispositions_to_ledger(
    *,
    ledger: dict[str, Any],
    batch: ArchitectAPhase22V2ScientificClosureBatch,
    receipts: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
) -> tuple[dict[str, Any], ArchitectAScientificLedgerTransitionReceipt]:
    """Apply exactly 35 resolved A dispositions; never close B/exam rows."""

    if not isinstance(batch, ArchitectAPhase22V2ScientificClosureBatch):
        raise CiboCapitalManagementError(
            "scientific ledger transition requires canonical closure batch"
        )
    if (
        not batch.all_scientific_workstreams_resolved
        or batch.external_ids
        or batch.missing_ids
        or batch.resolved_count != len(_A_IDS)
        or batch.receipt_count != len(_A_IDS)
    ):
        raise CiboCapitalManagementError(
            "scientific ledger transition requires terminal 35-of-35 A closure"
        )
    if (
        not isinstance(receipts, tuple)
        or any(
            not isinstance(
                item,
                ArchitectAPhase22V2ScientificDispositionReceipt,
            )
            for item in receipts
        )
    ):
        raise CiboCapitalManagementError(
            "scientific ledger transition receipts must be canonical tuple"
        )

    by_receipt: dict[str, ArchitectAPhase22V2ScientificDispositionReceipt] = {}
    for receipt in receipts:
        if receipt.workstream_id in by_receipt:
            raise CiboCapitalManagementError(
                "scientific ledger transition duplicate receipt"
            )
        if receipt.phase22_manifest_sha256 != batch.phase22_manifest_sha256:
            raise CiboCapitalManagementError(
                "scientific ledger transition manifest lineage drift"
            )
        if receipt.recommended_disposition not in _ALLOWED_TARGET_DISPOSITIONS:
            raise CiboCapitalManagementError(
                "scientific ledger transition unresolved disposition remains"
            )
        by_receipt[receipt.workstream_id] = receipt

    if set(by_receipt) != set(_A_IDS):
        raise CiboCapitalManagementError(
            "scientific ledger transition requires exact 35 receipt identities"
        )
    if tuple(batch.completed_ids) != tuple(
        item for item in _A_IDS
        if by_receipt[item].recommended_disposition == "COMPLETED_AND_PROVEN"
    ):
        raise CiboCapitalManagementError(
            "scientific ledger transition completed partition drift"
        )
    if tuple(batch.falsified_ids) != tuple(
        item for item in _A_IDS
        if by_receipt[item].recommended_disposition == "FALSIFIED_AND_CLOSED"
    ):
        raise CiboCapitalManagementError(
            "scientific ledger transition falsified partition drift"
        )

    before = copy.deepcopy(ledger)
    before_rows = _row_map(before)
    if _EXAM_IDS & set(_A_IDS):
        raise CiboCapitalManagementError(
            "scientific ledger transition A surface contains certification exam"
        )
    for workstream_id in _A_IDS:
        row = before_rows.get(workstream_id)
        if row is None:
            raise CiboCapitalManagementError(
                "scientific ledger transition missing A workstream: "
                + workstream_id
            )
        if row.get("terminal_disposition") != _ALLOWED_SOURCE_DISPOSITION:
            raise CiboCapitalManagementError(
                "scientific ledger transition source disposition drift: "
                + workstream_id
            )

    result = copy.deepcopy(ledger)
    result_rows = _row_map(result)
    for workstream_id in _A_IDS:
        receipt = by_receipt[workstream_id]
        row = result_rows[workstream_id]
        row["terminal_disposition"] = receipt.recommended_disposition
        row["current_maturity"] = (
            "PHASE22_V2_COMPLETED_AND_PROVEN_RECEIPT_BOUND"
            if receipt.recommended_disposition == "COMPLETED_AND_PROVEN"
            else "PHASE22_V2_FALSIFIED_AND_CLOSED_RECEIPT_BOUND"
        )
        row["blockers"] = []
        row["next_gate"] = (
            "Architect-A Phase22 V2 scientific disposition is terminal; "
            "preserve receipt lineage for Final Integrated Exam."
        )
        evidence_refs = list(row.get("evidence_refs", []))
        evidence_refs.extend(
            (
                "phase22-manifest:" + receipt.phase22_manifest_sha256,
                "scientific-gate:" + receipt.source_gate_id,
                "scientific-evidence:" + receipt.source_gate_evidence_sha256,
                "scientific-disposition-receipt:" + _receipt_sha(receipt),
            )
        )
        row["evidence_refs"] = list(dict.fromkeys(evidence_refs))

    # Prove no row outside the 35-row A surface changed.
    before_map = _row_map(before)
    after_map = _row_map(result)
    for row_id, before_row in before_map.items():
        if row_id not in set(_A_IDS) and after_map[row_id] != before_row:
            raise CiboCapitalManagementError(
                "scientific ledger transition mutated non-A row: " + row_id
            )

    mandatory = [
        row for row in _rows(result) if row.get("mandatory") is True
    ]
    terminal = [
        row for row in mandatory if row.get("terminal_disposition") is not None
    ]
    open_rows = [
        row for row in mandatory if row.get("terminal_disposition") is None
    ]
    summary = result.get("current_summary")
    if not isinstance(summary, dict):
        raise CiboCapitalManagementError(
            "scientific ledger transition summary missing"
        )
    result["current_summary"] = {
        "mandatory_count": len(mandatory),
        "terminal_count": len(terminal),
        "open_count": len(open_rows),
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }

    residual_external = tuple(
        str(row.get("id"))
        for row in mandatory
        if row.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
    )
    if any(item in set(_A_IDS) for item in residual_external):
        raise CiboCapitalManagementError(
            "scientific ledger transition left A external blocker"
        )

    transition = ArchitectAScientificLedgerTransitionReceipt(
        phase22_manifest_sha256=batch.phase22_manifest_sha256,
        pre_ledger_sha256=_canonical_sha(before),
        post_ledger_sha256=_canonical_sha(result),
        completed_ids=batch.completed_ids,
        falsified_ids=batch.falsified_ids,
        residual_external_ids=residual_external,
        exact_a_surface_resolved=True,
    )
    return result, transition
