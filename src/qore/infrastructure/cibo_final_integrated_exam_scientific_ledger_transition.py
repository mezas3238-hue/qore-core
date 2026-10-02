"""Canonical Architect-A scientific ledger transition for CIBO certification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
    ArchitectAPhase22V2ScientificClosureBatch,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
ARCHITECT_A_PHASE22_WORKSTREAM_IDS = tuple(
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM
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
            "Architect-A ledger transition schema drift"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "Architect-A ledger transition workstreams invalid"
        )
    return [row for row in rows if row.get("mandatory") is True]


def _external_ids(ledger: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(row.get("id"))
        for row in _mandatory_rows(ledger)
        if row.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
    )


@dataclass(frozen=True, slots=True)
class ArchitectAScientificLedgerTransitionReceipt:
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
        for name in (
            "phase22_manifest_sha256",
            "pre_ledger_sha256",
            "post_ledger_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("sha256:"):
                raise CiboCapitalManagementError(
                    f"Architect-A ledger transition {name} invalid"
                )
        if set(self.resolved_ids) != set(ARCHITECT_A_PHASE22_WORKSTREAM_IDS):
            raise CiboCapitalManagementError(
                "Architect-A ledger transition coverage drift"
            )
        if self.applied_count != len(ARCHITECT_A_PHASE22_WORKSTREAM_IDS):
            raise CiboCapitalManagementError(
                "Architect-A ledger transition count drift"
            )
        if (
            not self.ledger_update_authority
            or self.certification_claimed
            or self.production_authority
            or self.merge_authority
        ):
            raise CiboCapitalManagementError(
                "Architect-A ledger transition authority drift"
            )

    def fingerprint(self) -> str:
        return _canonical_sha(asdict(self))


def apply_architect_a_scientific_dispositions_to_ledger(
    *,
    ledger: dict[str, Any],
    batch: ArchitectAPhase22V2ScientificClosureBatch,
    receipts: tuple[ArchitectAPhase22V2ScientificDispositionReceipt, ...],
) -> tuple[dict[str, Any], ArchitectAScientificLedgerTransitionReceipt]:
    """Apply exactly the 35 source-bound Architect-A terminal dispositions."""

    if not isinstance(batch, ArchitectAPhase22V2ScientificClosureBatch):
        raise CiboCapitalManagementError(
            "Architect-A ledger transition requires canonical closure batch"
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
            "Architect-A ledger transition receipts invalid"
        )

    expected_ids = ARCHITECT_A_PHASE22_WORKSTREAM_IDS
    receipt_ids = tuple(item.workstream_id for item in receipts)
    if (
        len(receipts) != len(expected_ids)
        or len(receipt_ids) != len(set(receipt_ids))
        or set(receipt_ids) != set(expected_ids)
    ):
        raise CiboCapitalManagementError(
            "Architect-A ledger transition requires exact 35-receipt surface"
        )
    if (
        batch.phase22_manifest_sha256
        not in {item.phase22_manifest_sha256 for item in receipts}
        or len({item.phase22_manifest_sha256 for item in receipts}) != 1
    ):
        raise CiboCapitalManagementError(
            "Architect-A ledger transition Phase22 manifest drift"
        )
    if (
        batch.receipt_count != len(expected_ids)
        or batch.resolved_count != len(expected_ids)
        or batch.external_ids
        or batch.missing_ids
        or not batch.all_scientific_workstreams_resolved
    ):
        raise CiboCapitalManagementError(
            "Architect-A ledger transition requires fully resolved batch"
        )

    pre_external = set(_external_ids(ledger))
    if not set(expected_ids).issubset(pre_external):
        raise CiboCapitalManagementError(
            "Architect-A ledger transition cannot reopen non-external rows"
        )

    updated = json.loads(json.dumps(ledger))
    mandatory = _mandatory_rows(updated)
    by_id = {str(row.get("id")): row for row in mandatory}
    resolved: list[str] = []
    for receipt in receipts:
        row = by_id[receipt.workstream_id]
        if row.get("terminal_disposition") != "EXTERNAL_DEPENDENCY_BLOCKED":
            raise CiboCapitalManagementError(
                "Architect-A ledger transition preimage disposition drift"
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
            "Terminal Phase22 scientific intake disposition. "
            "No operational or certification authority is granted."
        )
        resolved.append(receipt.workstream_id)

    residual = _external_ids(updated)
    transition = ArchitectAScientificLedgerTransitionReceipt(
        phase22_manifest_sha256=batch.phase22_manifest_sha256,
        pre_ledger_sha256=_canonical_sha(ledger),
        post_ledger_sha256=_canonical_sha(updated),
        resolved_ids=tuple(resolved),
        residual_external_ids=residual,
        applied_count=len(resolved),
    )
    return updated, transition
