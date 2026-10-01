"""Governed application of the ten residual Architect-B dispositions.

The transition consumes only source-bound Phase22 receipts from Architect B.
It never fabricates provider execution, settlement, release or fresh-OOS facts.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_SCHEMA = "qore.cibo.arch-b.phase22-disposition.v1"
_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_SOURCE_DISPOSITION = "EXTERNAL_DEPENDENCY_BLOCKED"
_TARGET_DISPOSITIONS = {
    "COMPLETED_AND_PROVEN",
    "FALSIFIED_AND_CLOSED",
}
_ARCH_B_IDS = (
    "T02",
    "T03",
    "T11",
    "T16",
    "T20",
    "PROVIDER_ECONOMICS",
    "FORWARD_QUALIFICATION",
    "FRESH_OOS",
    "USD60_CAPABILITY_PROGRAM",
    "INTEGRATED_CAPITAL_TRUTH",
)
_EXAM_IDS = {
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
}


def _sha(value: str, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"Architect-B ledger transition {name} must be canonical sha256"
        )
    return value


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
            "Architect-B ledger transition ledger schema drift"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "Architect-B ledger transition rows invalid"
        )
    return rows


def _row_map(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in _rows(ledger):
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id:
            raise CiboCapitalManagementError(
                "Architect-B ledger transition row id invalid"
            )
        if row_id in result:
            raise CiboCapitalManagementError(
                "Architect-B ledger transition duplicate row id"
            )
        result[row_id] = row
    return result


@dataclass(frozen=True, slots=True)
class ArchitectBPhase22DispositionReceipt:
    schema: str
    workstream_id: str
    phase22_manifest_sha256: str
    source_gate_id: str
    source_gate_evidence_sha256: str
    source_gate_status: str
    passed: bool
    recommended_disposition: str
    blockers: tuple[str, ...]
    failed_dimensions: tuple[str, ...]
    synthetic_evidence_used: bool = False
    provider_evidence_fabricated: bool = False
    holdout_mining_used: bool = False
    ledger_update_authority: bool = False
    certification_claimed: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != _SCHEMA:
            raise CiboCapitalManagementError(
                "Architect-B disposition schema drift"
            )
        if self.workstream_id not in _ARCH_B_IDS:
            raise CiboCapitalManagementError(
                "Architect-B disposition workstream drift"
            )
        _sha(self.phase22_manifest_sha256, "phase22_manifest_sha256")
        _sha(self.source_gate_evidence_sha256, "source_gate_evidence_sha256")
        if not self.source_gate_id or not self.source_gate_status:
            raise CiboCapitalManagementError(
                "Architect-B disposition source gate identity required"
            )
        for name in (
            "passed",
            "synthetic_evidence_used",
            "provider_evidence_fabricated",
            "holdout_mining_used",
            "ledger_update_authority",
            "certification_claimed",
            "production_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Architect-B disposition {name} must be bool"
                )
        if (
            self.synthetic_evidence_used
            or self.provider_evidence_fabricated
            or self.holdout_mining_used
        ):
            raise CiboCapitalManagementError(
                "Architect-B disposition governance contamination"
            )
        if (
            self.ledger_update_authority
            or self.certification_claimed
            or self.production_authority
        ):
            raise CiboCapitalManagementError(
                "Architect-B disposition grants no authority"
            )
        expected = (
            "COMPLETED_AND_PROVEN"
            if self.passed
            else "FALSIFIED_AND_CLOSED"
        )
        if self.recommended_disposition != expected:
            raise CiboCapitalManagementError(
                "Architect-B disposition/result drift"
            )
        if self.recommended_disposition not in _TARGET_DISPOSITIONS:
            raise CiboCapitalManagementError(
                "Architect-B disposition target invalid"
            )
        if self.passed and (self.blockers or self.failed_dimensions):
            raise CiboCapitalManagementError(
                "Architect-B PASS cannot retain failed dimensions"
            )
        if not self.passed and not (self.blockers or self.failed_dimensions):
            raise CiboCapitalManagementError(
                "Architect-B falsification requires failure evidence"
            )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        return _canonical_sha(self.as_dict())


@dataclass(frozen=True, slots=True)
class ArchitectBLedgerTransitionReceipt:
    phase22_manifest_sha256: str
    pre_ledger_sha256: str
    post_ledger_sha256: str
    completed_ids: tuple[str, ...]
    falsified_ids: tuple[str, ...]
    residual_external_ids: tuple[str, ...]
    exact_b_surface_resolved: bool
    certification_claimed: bool = False
    production_authority: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        _sha(self.phase22_manifest_sha256, "phase22_manifest_sha256")
        _sha(self.pre_ledger_sha256, "pre_ledger_sha256")
        _sha(self.post_ledger_sha256, "post_ledger_sha256")
        if set(self.completed_ids) & set(self.falsified_ids):
            raise CiboCapitalManagementError(
                "Architect-B transition disposition overlap"
            )
        if set(self.completed_ids) | set(self.falsified_ids) != set(_ARCH_B_IDS):
            raise CiboCapitalManagementError(
                "Architect-B transition exact ten-row coverage drift"
            )
        if (
            type(self.exact_b_surface_resolved) is not bool
            or not self.exact_b_surface_resolved
        ):
            raise CiboCapitalManagementError(
                "Architect-B transition exact surface must be resolved"
            )
        if (
            self.certification_claimed
            or self.production_authority
            or self.merge_authority
        ):
            raise CiboCapitalManagementError(
                "Architect-B transition grants no authority"
            )

    def fingerprint(self) -> str:
        return _canonical_sha(asdict(self))


def apply_architect_b_dispositions_to_ledger(
    *,
    ledger: dict[str, Any],
    receipts: tuple[ArchitectBPhase22DispositionReceipt, ...],
) -> tuple[dict[str, Any], ArchitectBLedgerTransitionReceipt]:
    """Resolve exactly the ten residual B rows and nothing else."""

    if (
        not isinstance(receipts, tuple)
        or any(
            not isinstance(item, ArchitectBPhase22DispositionReceipt)
            for item in receipts
        )
    ):
        raise CiboCapitalManagementError(
            "Architect-B transition receipts must be canonical tuple"
        )
    by_id: dict[str, ArchitectBPhase22DispositionReceipt] = {}
    for receipt in receipts:
        if receipt.workstream_id in by_id:
            raise CiboCapitalManagementError(
                "Architect-B transition duplicate receipt"
            )
        by_id[receipt.workstream_id] = receipt
    if set(by_id) != set(_ARCH_B_IDS):
        raise CiboCapitalManagementError(
            "Architect-B transition requires exact ten receipt identities"
        )

    manifests = {item.phase22_manifest_sha256 for item in receipts}
    if len(manifests) != 1:
        raise CiboCapitalManagementError(
            "Architect-B transition Phase22 manifest drift"
        )
    phase22_manifest_sha256 = next(iter(manifests))

    before = copy.deepcopy(ledger)
    before_rows = _row_map(before)
    for workstream_id in _ARCH_B_IDS:
        row = before_rows.get(workstream_id)
        if row is None:
            raise CiboCapitalManagementError(
                "Architect-B transition missing row: " + workstream_id
            )
        if row.get("terminal_disposition") != _SOURCE_DISPOSITION:
            raise CiboCapitalManagementError(
                "Architect-B transition source disposition drift: "
                + workstream_id
            )
    if _EXAM_IDS & set(_ARCH_B_IDS):
        raise CiboCapitalManagementError(
            "Architect-B transition surface contains certification exam"
        )

    result = copy.deepcopy(ledger)
    result_rows = _row_map(result)
    for workstream_id in _ARCH_B_IDS:
        receipt = by_id[workstream_id]
        row = result_rows[workstream_id]
        row["terminal_disposition"] = receipt.recommended_disposition
        row["current_maturity"] = (
            "PHASE22_V2_COMPLETED_AND_PROVEN_RECEIPT_BOUND"
            if receipt.passed
            else "PHASE22_V2_FALSIFIED_AND_CLOSED_RECEIPT_BOUND"
        )
        row["blockers"] = []
        row["next_gate"] = (
            "Architect-B Phase22 V2 scientific disposition is terminal; "
            "preserve exact provider/execution/fresh evidence lineage."
        )
        evidence_refs = list(row.get("evidence_refs", []))
        evidence_refs.extend(
            (
                "phase22-manifest:" + receipt.phase22_manifest_sha256,
                "architect-b-gate:" + receipt.source_gate_id,
                "architect-b-evidence:" + receipt.source_gate_evidence_sha256,
                "architect-b-disposition-receipt:" + receipt.fingerprint(),
            )
        )
        row["evidence_refs"] = list(dict.fromkeys(evidence_refs))

    after_rows = _row_map(result)
    b_set = set(_ARCH_B_IDS)
    for row_id, before_row in before_rows.items():
        if row_id not in b_set and after_rows[row_id] != before_row:
            raise CiboCapitalManagementError(
                "Architect-B transition mutated non-B row: " + row_id
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
    if b_set & set(residual_external):
        raise CiboCapitalManagementError(
            "Architect-B transition left B external blocker"
        )

    completed_ids = tuple(
        item for item in _ARCH_B_IDS if by_id[item].passed
    )
    falsified_ids = tuple(
        item for item in _ARCH_B_IDS if not by_id[item].passed
    )
    transition = ArchitectBLedgerTransitionReceipt(
        phase22_manifest_sha256=phase22_manifest_sha256,
        pre_ledger_sha256=_canonical_sha(before),
        post_ledger_sha256=_canonical_sha(result),
        completed_ids=completed_ids,
        falsified_ids=falsified_ids,
        residual_external_ids=residual_external,
        exact_b_surface_resolved=True,
    )
    return result, transition
