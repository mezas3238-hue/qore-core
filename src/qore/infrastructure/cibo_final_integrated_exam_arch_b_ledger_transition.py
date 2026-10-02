"""Canonical B/cross scientific ledger transition for CIBO certification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
ARCHITECT_B_PHASE22_DISPOSITION_SCHEMA = (
    "qore.cibo.arch-b.phase22-disposition.v1"
)
ARCHITECT_B_PHASE22_WORKSTREAM_IDS = (
    "T02",
    "T11",
    "T20",
    "FRESH_OOS",
    "USD60_CAPABILITY_PROGRAM",
    "INTEGRATED_CAPITAL_TRUTH",
)


def _canonical_sha(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _mandatory_rows(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(ledger, dict) or ledger.get("schema") != _LEDGER_SCHEMA:
        raise CiboCapitalManagementError(
            "Architect-B ledger transition schema drift"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "Architect-B ledger transition workstreams invalid"
        )
    return [row for row in rows if row.get("mandatory") is True]


def _external_ids(ledger: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(row.get("id"))
        for row in _mandatory_rows(ledger)
        if row.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
    )


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
    ledger_update_authority: bool = False
    certification_claimed: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != ARCHITECT_B_PHASE22_DISPOSITION_SCHEMA:
            raise CiboCapitalManagementError(
                "Architect-B Phase22 disposition schema drift"
            )
        if self.workstream_id not in ARCHITECT_B_PHASE22_WORKSTREAM_IDS:
            raise CiboCapitalManagementError(
                "Architect-B Phase22 disposition workstream drift"
            )
        for name in (
            "phase22_manifest_sha256",
            "source_gate_evidence_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("sha256:"):
                raise CiboCapitalManagementError(
                    f"Architect-B Phase22 disposition {name} invalid"
                )
        if not self.source_gate_id or not self.source_gate_status:
            raise CiboCapitalManagementError(
                "Architect-B Phase22 disposition source gate identity required"
            )
        expected = (
            "COMPLETED_AND_PROVEN"
            if self.passed
            else "FALSIFIED_AND_CLOSED"
        )
        if self.recommended_disposition != expected:
            raise CiboCapitalManagementError(
                "Architect-B Phase22 disposition/result drift"
            )
        if self.passed and (self.blockers or self.failed_dimensions):
            raise CiboCapitalManagementError(
                "Architect-B passing disposition cannot retain failures"
            )
        if not self.passed and not self.failed_dimensions:
            raise CiboCapitalManagementError(
                "Architect-B falsified disposition needs failed dimension"
            )
        if (
            self.ledger_update_authority
            or self.certification_claimed
            or self.production_authority
        ):
            raise CiboCapitalManagementError(
                "Architect-B Phase22 disposition cannot grant authority"
            )


@dataclass(frozen=True, slots=True)
class ArchitectBLedgerTransitionReceipt:
    phase22_manifest_sha256: str
    pre_ledger_sha256: str
    post_ledger_sha256: str
    resolved_ids: tuple[str, ...]
    residual_external_ids: tuple[str, ...]
    applied_count: int
    ledger_update_authority: bool = True
    certification_claimed: bool = False
    production_authority: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        if set(self.resolved_ids) != set(ARCHITECT_B_PHASE22_WORKSTREAM_IDS):
            raise CiboCapitalManagementError(
                "Architect-B ledger transition coverage drift"
            )
        if self.applied_count != len(ARCHITECT_B_PHASE22_WORKSTREAM_IDS):
            raise CiboCapitalManagementError(
                "Architect-B ledger transition count drift"
            )
        if self.residual_external_ids:
            raise CiboCapitalManagementError(
                "Architect-B ledger transition left external blockers"
            )
        if (
            not self.ledger_update_authority
            or self.certification_claimed
            or self.production_authority
            or self.merge_authority
        ):
            raise CiboCapitalManagementError(
                "Architect-B ledger transition authority drift"
            )

    def fingerprint(self) -> str:
        return _canonical_sha(asdict(self))


def apply_architect_b_dispositions_to_ledger(
    *,
    ledger: dict[str, Any],
    receipts: tuple[ArchitectBPhase22DispositionReceipt, ...],
) -> tuple[dict[str, Any], ArchitectBLedgerTransitionReceipt]:
    """Apply exactly the six current B/cross terminal dispositions."""

    if (
        not isinstance(receipts, tuple)
        or any(
            not isinstance(item, ArchitectBPhase22DispositionReceipt)
            for item in receipts
        )
    ):
        raise CiboCapitalManagementError(
            "Architect-B ledger transition receipts invalid"
        )
    receipt_ids = tuple(item.workstream_id for item in receipts)
    if (
        len(receipts) != len(ARCHITECT_B_PHASE22_WORKSTREAM_IDS)
        or len(receipt_ids) != len(set(receipt_ids))
        or set(receipt_ids) != set(ARCHITECT_B_PHASE22_WORKSTREAM_IDS)
    ):
        raise CiboCapitalManagementError(
            "Architect-B ledger transition requires exact six-receipt surface"
        )
    manifests = {item.phase22_manifest_sha256 for item in receipts}
    if len(manifests) != 1:
        raise CiboCapitalManagementError(
            "Architect-B ledger transition Phase22 manifest drift"
        )
    if set(_external_ids(ledger)) != set(ARCHITECT_B_PHASE22_WORKSTREAM_IDS):
        raise CiboCapitalManagementError(
            "Architect-B ledger transition requires canonical six-blocker preimage"
        )

    updated = json.loads(json.dumps(ledger))
    by_id = {
        str(row.get("id")): row for row in _mandatory_rows(updated)
    }
    resolved: list[str] = []
    for receipt in receipts:
        row = by_id[receipt.workstream_id]
        if row.get("terminal_disposition") != "EXTERNAL_DEPENDENCY_BLOCKED":
            raise CiboCapitalManagementError(
                "Architect-B ledger transition preimage disposition drift"
            )
        row["terminal_disposition"] = receipt.recommended_disposition
        row["current_maturity"] = (
            "PHASE22_SCIENTIFIC_INTAKE_"
            + receipt.recommended_disposition
        )
        refs = list(row.get("evidence_refs") or [])
        refs.extend(
            [
                receipt.source_gate_id,
                receipt.source_gate_evidence_sha256,
            ]
        )
        row["evidence_refs"] = list(dict.fromkeys(refs))
        row["blockers"] = list(receipt.blockers)
        row["next_gate"] = (
            "Terminal Phase22 B/cross scientific intake disposition. "
            "No operational or certification authority is granted."
        )
        resolved.append(receipt.workstream_id)

    residual = _external_ids(updated)
    manifest_sha = next(iter(manifests))
    transition = ArchitectBLedgerTransitionReceipt(
        phase22_manifest_sha256=manifest_sha,
        pre_ledger_sha256=_canonical_sha(ledger),
        post_ledger_sha256=_canonical_sha(updated),
        resolved_ids=tuple(resolved),
        residual_external_ids=residual,
        applied_count=len(resolved),
    )
    return updated, transition
