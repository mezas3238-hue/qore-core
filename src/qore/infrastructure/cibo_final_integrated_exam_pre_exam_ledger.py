"""Compose evidence-bound scientific closure into the legal PRE_EXAM ledger."""

from __future__ import annotations

from typing import Any

from qore.infrastructure.cibo_arch_a_internal_readiness import (
    ArchitectAPhase22V2ScientificClosureBatch,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam_arch_b_ledger_reconciliation import (
    ArchitectBPhase22FinalDispositionPackage,
    apply_architect_b_phase22_final_dispositions,
)
from qore.infrastructure.cibo_final_integrated_exam_scientific_ledger_reconciliation import (
    apply_architect_a_phase22_scientific_dispositions,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    ScientificClosure41Package,
    apply_scientific_closure_41_to_ledger_copy,
)

_REQUIRED_OPEN_IDS = (
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
)


def validate_pre_exam_reconciled_ledger(
    ledger: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(ledger, dict):
        raise CiboCapitalManagementError(
            "PRE_EXAM reconciled ledger must be object"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "PRE_EXAM reconciled ledger rows invalid"
        )
    mandatory = [item for item in rows if item.get("mandatory") is True]
    if len(mandatory) != 64:
        raise CiboCapitalManagementError(
            "PRE_EXAM reconciled ledger requires 64 mandatory rows"
        )
    terminal = [
        item for item in mandatory if item.get("terminal_disposition") is not None
    ]
    open_ids = tuple(
        str(item.get("id"))
        for item in mandatory
        if item.get("terminal_disposition") is None
    )
    external = tuple(
        str(item.get("id"))
        for item in mandatory
        if (
            item.get("certification_blocking") is True
            and item.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
        )
    )
    if len(terminal) != 62 or open_ids != _REQUIRED_OPEN_IDS:
        raise CiboCapitalManagementError(
            "PRE_EXAM reconciled ledger topology drift"
        )
    if external:
        raise CiboCapitalManagementError(
            "PRE_EXAM reconciled ledger external blockers remain: "
            + ",".join(external)
        )
    expected_summary = {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    if ledger.get("current_summary") != expected_summary:
        raise CiboCapitalManagementError(
            "PRE_EXAM reconciled ledger summary drift"
        )
    return ledger


def reconcile_pre_exam_ledger_from_scientific_closure_41(
    *,
    ledger: dict[str, Any],
    closure_package: ScientificClosure41Package,
) -> dict[str, Any]:
    """Apply canonical Closure41, then require exact 64/62/2/0 PRE_EXAM."""

    if not isinstance(closure_package, ScientificClosure41Package):
        raise CiboCapitalManagementError(
            "PRE_EXAM requires canonical Scientific Closure 41 package"
        )
    reconciled, transition = apply_scientific_closure_41_to_ledger_copy(
        ledger=ledger,
        package=closure_package,
    )
    if transition.open_exam_ids != (
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    ):
        raise CiboCapitalManagementError(
            "PRE_EXAM Closure41 transition exam topology drift"
        )
    if transition.residual_external_ids:
        raise CiboCapitalManagementError(
            "PRE_EXAM Closure41 transition retains external blockers"
        )
    return validate_pre_exam_reconciled_ledger(reconciled)


def reconcile_pre_exam_ledger(
    *,
    ledger: dict[str, Any],
    architect_a_batch: ArchitectAPhase22V2ScientificClosureBatch,
    architect_a_receipts: tuple[
        ArchitectAPhase22V2ScientificDispositionReceipt, ...
    ],
    architect_b_package: ArchitectBPhase22FinalDispositionPackage,
) -> dict[str, Any]:
    """Legacy A+B compatibility path; current certification uses Closure41."""

    after_a = apply_architect_a_phase22_scientific_dispositions(
        ledger=ledger,
        batch=architect_a_batch,
        receipts=architect_a_receipts,
    )
    after_b = apply_architect_b_phase22_final_dispositions(
        ledger=after_a,
        package=architect_b_package,
    )
    return validate_pre_exam_reconciled_ledger(after_b)
