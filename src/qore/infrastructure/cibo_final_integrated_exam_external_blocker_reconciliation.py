"""Exact current 41-row external-blocker reconciliation for CIBO certification."""

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
    ARCHITECT_B_PHASE22_WORKSTREAM_IDS,
    ArchitectBPhase22DispositionReceipt,
    apply_architect_b_dispositions_to_ledger,
)
from qore.infrastructure.cibo_final_integrated_exam_scientific_ledger_transition import (
    ARCHITECT_A_PHASE22_WORKSTREAM_IDS,
    apply_architect_a_scientific_dispositions_to_ledger,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_EXPECTED_OPEN = (
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
)
_EXPECTED_NON_REOPEN_DISPOSITIONS = {
    "T03": "FALSIFIED_AND_CLOSED",
    "T16": "FALSIFIED_AND_CLOSED",
    "PROVIDER_ECONOMICS": "SUPERSEDED_WITH_PROVEN_LINEAGE",
    "FORWARD_QUALIFICATION": "SUPERSEDED_WITH_PROVEN_LINEAGE",
}
_EXPECTED_EXTERNAL_IDS = frozenset(
    ARCHITECT_A_PHASE22_WORKSTREAM_IDS
    + ARCHITECT_B_PHASE22_WORKSTREAM_IDS
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


def _assert_non_reopen_preimage(ledger: dict[str, Any]) -> None:
    by_id = {
        str(row.get("id")): row for row in _mandatory_rows(ledger)
    }
    for workstream_id, disposition in _EXPECTED_NON_REOPEN_DISPOSITIONS.items():
        row = by_id.get(workstream_id)
        if row is None or row.get("terminal_disposition") != disposition:
            raise CiboCapitalManagementError(
                "external reconciliation non-reopen disposition drift: "
                + workstream_id
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
    exact_41_external_blockers_resolved: bool
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
            self.external_before_count != 41
            or self.external_after_count != 0
            or self.resolved_external_count != 41
        ):
            raise CiboCapitalManagementError(
                "external reconciliation exact 41-row count drift"
            )
        if self.open_ids != _EXPECTED_OPEN:
            raise CiboCapitalManagementError(
                "external reconciliation open-exam topology drift"
            )
        if (
            type(self.exact_41_external_blockers_resolved) is not bool
            or not self.exact_41_external_blockers_resolved
        ):
            raise CiboCapitalManagementError(
                "external reconciliation must resolve exact 41-row surface"
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
    """Resolve the canonical 41 blockers from source-bound A+B/cross receipts."""

    _assert_non_reopen_preimage(ledger)
    external_before = _external_ids(ledger)
    if (
        len(external_before) != 41
        or set(external_before) != _EXPECTED_EXTERNAL_IDS
    ):
        raise CiboCapitalManagementError(
            "external reconciliation requires canonical 41-blocker starting state"
        )

    after_a, a_transition = apply_architect_a_scientific_dispositions_to_ledger(
        ledger=ledger,
        batch=architect_a_batch,
        receipts=architect_a_receipts,
    )
    if set(a_transition.residual_external_ids) != set(
        ARCHITECT_B_PHASE22_WORKSTREAM_IDS
    ):
        raise CiboCapitalManagementError(
            "external reconciliation expected six residual B/cross blockers after A"
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
    _assert_non_reopen_preimage(after_b)

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
        external_before_count=41,
        external_after_count=0,
        resolved_external_count=41,
        open_ids=open_ids,
        exact_41_external_blockers_resolved=True,
    )
    return after_b, receipt
