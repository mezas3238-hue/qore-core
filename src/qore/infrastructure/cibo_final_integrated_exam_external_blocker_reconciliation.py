"""Exact 45-row external-blocker reconciliation for CIBO certification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2ScientificClosureBatch,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_arch_b_ledger_transition import (
    ArchitectBPhase22DispositionReceipt,
    apply_architect_b_dispositions_to_ledger,
)
from qore.infrastructure.cibo_final_integrated_exam_scientific_ledger_transition import (
    apply_architect_a_scientific_dispositions_to_ledger,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_EXPECTED_OPEN = (
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
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
            "external reconciliation ledger schema drift"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "external reconciliation workstreams invalid"
        )
    return [row for row in rows if row.get("mandatory") is True]


def _external_ids(ledger: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(row.get("id"))
        for row in _mandatory_rows(ledger)
        if row.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
    )


def _open_ids(ledger: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(row.get("id"))
        for row in _mandatory_rows(ledger)
        if row.get("terminal_disposition") is None
    )


@dataclass(frozen=True, slots=True)
class ExternalBlockerReconciliationReceipt:
    phase22_manifest_sha256: str
    pre_ledger_sha256: str
    post_ledger_sha256: str
    architect_a_transition_sha256: str
    architect_b_transition_sha256: str
    external_before_count: int
    external_after_count: int
    resolved_external_count: int
    open_ids: tuple[str, ...]
    exact_45_external_blockers_resolved: bool
    certification_claimed: bool = False
    production_authority: bool = False
    merge_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "phase22_manifest_sha256",
            "pre_ledger_sha256",
            "post_ledger_sha256",
            "architect_a_transition_sha256",
            "architect_b_transition_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.startswith("sha256:"):
                raise CiboCapitalManagementError(
                    f"external reconciliation {name} invalid"
                )
        if (
            self.external_before_count != 45
            or self.external_after_count != 0
            or self.resolved_external_count != 45
        ):
            raise CiboCapitalManagementError(
                "external reconciliation exact 45-row count drift"
            )
        if self.open_ids != _EXPECTED_OPEN:
            raise CiboCapitalManagementError(
                "external reconciliation open-exam topology drift"
            )
        if (
            type(self.exact_45_external_blockers_resolved) is not bool
            or not self.exact_45_external_blockers_resolved
        ):
            raise CiboCapitalManagementError(
                "external reconciliation must resolve exact 45-row surface"
            )
        if (
            self.certification_claimed
            or self.production_authority
            or self.merge_authority
        ):
            raise CiboCapitalManagementError(
                "external reconciliation grants no authority"
            )

    def fingerprint(self) -> str:
        return _canonical_sha(asdict(self))


def reconcile_all_external_blockers(
    *,
    ledger: dict[str, Any],
    architect_a_batch: ArchitectAPhase22V2ScientificClosureBatch,
    architect_a_receipts: tuple[
        ArchitectAPhase22V2ScientificDispositionReceipt, ...
    ],
    architect_b_receipts: tuple[ArchitectBPhase22DispositionReceipt, ...],
) -> tuple[dict[str, Any], ExternalBlockerReconciliationReceipt]:
    """Resolve all 45 external blockers from source-bound A+B receipts."""

    external_before = _external_ids(ledger)
    if len(external_before) != 45:
        raise CiboCapitalManagementError(
            "external reconciliation requires canonical 45-blocker starting state"
        )

    after_a, a_transition = apply_architect_a_scientific_dispositions_to_ledger(
        ledger=ledger,
        batch=architect_a_batch,
        receipts=architect_a_receipts,
    )
    if len(a_transition.residual_external_ids) != 10:
        raise CiboCapitalManagementError(
            "external reconciliation expected ten residual B blockers after A"
        )

    after_b, b_transition = apply_architect_b_dispositions_to_ledger(
        ledger=after_a,
        receipts=architect_b_receipts,
    )
    if (
        a_transition.phase22_manifest_sha256
        != b_transition.phase22_manifest_sha256
    ):
        raise CiboCapitalManagementError(
            "external reconciliation A/B Phase22 manifest drift"
        )

    external_after = _external_ids(after_b)
    if external_after:
        raise CiboCapitalManagementError(
            "external reconciliation left certification blockers: "
            + ",".join(external_after)
        )
    mandatory = _mandatory_rows(after_b)
    terminal_count = sum(
        row.get("terminal_disposition") is not None for row in mandatory
    )
    open_ids = _open_ids(after_b)
    if len(mandatory) != 64 or terminal_count != 62 or open_ids != _EXPECTED_OPEN:
        raise CiboCapitalManagementError(
            "external reconciliation final 64/62/2 topology drift"
        )
    summary = after_b.get("current_summary")
    expected_summary = {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    if summary != expected_summary:
        raise CiboCapitalManagementError(
            "external reconciliation summary drift"
        )

    receipt = ExternalBlockerReconciliationReceipt(
        phase22_manifest_sha256=a_transition.phase22_manifest_sha256,
        pre_ledger_sha256=_canonical_sha(ledger),
        post_ledger_sha256=_canonical_sha(after_b),
        architect_a_transition_sha256=a_transition.fingerprint(),
        architect_b_transition_sha256=b_transition.fingerprint(),
        external_before_count=45,
        external_after_count=0,
        resolved_external_count=45,
        open_ids=open_ids,
        exact_45_external_blockers_resolved=True,
    )
    return after_b, receipt
