"""Admit Architect-B post-Phase22 dispositions into the canonical ledger.

Architect A owns this consumer only. It cannot manufacture B outcomes. The
package must contain the exact ten B-owned certification-blocking rows, all
bound to one Phase22 V2 manifest and one Architect-B HEAD, with no blockers.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_PACKAGE_SCHEMA = "QORE_CIBO_ARCH_B_PHASE22_FINAL_DISPOSITION_PACKAGE_V1"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUIRED_IDS = (
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
_ALLOWED_FINAL_DISPOSITIONS = {
    "COMPLETED_AND_PROVEN",
    "FALSIFIED_AND_CLOSED",
    "SUPERSEDED_WITH_PROVEN_LINEAGE",
}


@dataclass(frozen=True, slots=True)
class ArchitectBPhase22FinalDisposition:
    workstream_id: str
    recommendation: str
    evidence_sha256: str
    evidence_ref: str
    blockers: tuple[str, ...] = ()
    certification_blocking: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id not in _REQUIRED_IDS:
            raise CiboCapitalManagementError(
                "B final disposition workstream identity drift"
            )
        if self.recommendation not in _ALLOWED_FINAL_DISPOSITIONS:
            raise CiboCapitalManagementError(
                "B final disposition must be terminal and non-external"
            )
        if _SHA256_RE.fullmatch(self.evidence_sha256) is None:
            raise CiboCapitalManagementError(
                "B final disposition evidence SHA invalid"
            )
        if not self.evidence_ref:
            raise CiboCapitalManagementError(
                "B final disposition evidence ref required"
            )
        if self.blockers:
            raise CiboCapitalManagementError(
                "B final disposition cannot retain blockers"
            )
        if self.certification_blocking:
            raise CiboCapitalManagementError(
                "B final disposition cannot remain certification-blocking"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "B final disposition grants no productive authority"
            )


@dataclass(frozen=True, slots=True)
class ArchitectBPhase22FinalDispositionPackage:
    schema: str
    architect_b_head_sha: str
    phase22_manifest_sha256: str
    dispositions: tuple[ArchitectBPhase22FinalDisposition, ...]
    fresh_execution_complete: bool
    economic_qualification_executed: bool
    ledger_update_authority: bool = False
    certification_claimed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != _PACKAGE_SCHEMA:
            raise CiboCapitalManagementError(
                "B final disposition package schema drift"
            )
        if _SHA1_RE.fullmatch(self.architect_b_head_sha) is None:
            raise CiboCapitalManagementError(
                "B final disposition package HEAD invalid"
            )
        if _SHA256_RE.fullmatch(self.phase22_manifest_sha256) is None:
            raise CiboCapitalManagementError(
                "B final disposition package manifest SHA invalid"
            )
        if (
            not isinstance(self.dispositions, tuple)
            or any(
                not isinstance(item, ArchitectBPhase22FinalDisposition)
                for item in self.dispositions
            )
        ):
            raise CiboCapitalManagementError(
                "B final disposition package rows invalid"
            )
        ids = tuple(item.workstream_id for item in self.dispositions)
        if ids != _REQUIRED_IDS:
            raise CiboCapitalManagementError(
                "B final disposition package requires exact ten-row order"
            )
        if not self.fresh_execution_complete:
            raise CiboCapitalManagementError(
                "B final disposition package requires complete fresh execution"
            )
        if not self.economic_qualification_executed:
            raise CiboCapitalManagementError(
                "B final disposition package requires executed qualification"
            )
        if (
            self.ledger_update_authority
            or self.certification_claimed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "B final disposition package grants no authority"
            )


def required_arch_b_final_workstream_ids() -> tuple[str, ...]:
    return _REQUIRED_IDS


def apply_architect_b_phase22_final_dispositions(
    *,
    ledger: dict[str, Any],
    package: ArchitectBPhase22FinalDispositionPackage,
) -> dict[str, Any]:
    """Apply exact B dispositions only to currently external-blocked B rows."""

    if not isinstance(package, ArchitectBPhase22FinalDispositionPackage):
        raise CiboCapitalManagementError(
            "B ledger reconciliation requires canonical package"
        )
    if not isinstance(ledger, dict) or ledger.get("schema") != _LEDGER_SCHEMA:
        raise CiboCapitalManagementError(
            "B ledger reconciliation schema drift"
        )
    rows = ledger.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "B ledger reconciliation rows invalid"
        )

    result = copy.deepcopy(ledger)
    result_rows = result["workstreams"]
    by_id: dict[str, dict[str, Any]] = {}
    for row in result_rows:
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id:
            raise CiboCapitalManagementError(
                "B ledger reconciliation row identity invalid"
            )
        if row_id in by_id:
            raise CiboCapitalManagementError(
                "B ledger reconciliation duplicate row"
            )
        by_id[row_id] = row

    for disposition in package.dispositions:
        row = by_id.get(disposition.workstream_id)
        if row is None:
            raise CiboCapitalManagementError(
                "B ledger reconciliation target missing: "
                + disposition.workstream_id
            )
        if row.get("mandatory") is not True:
            raise CiboCapitalManagementError(
                "B ledger reconciliation target must be mandatory"
            )
        if row.get("terminal_disposition") != "EXTERNAL_DEPENDENCY_BLOCKED":
            raise CiboCapitalManagementError(
                "B ledger reconciliation target is not external-blocked: "
                + disposition.workstream_id
            )

        evidence_refs = row.get("evidence_refs")
        if not isinstance(evidence_refs, list):
            raise CiboCapitalManagementError(
                "B ledger reconciliation evidence refs invalid"
            )
        for ref in (
            disposition.evidence_ref,
            "phase22-v2-manifest:" + package.phase22_manifest_sha256,
            "architect-b-head:" + package.architect_b_head_sha,
        ):
            if ref not in evidence_refs:
                evidence_refs.append(ref)

        row["terminal_disposition"] = disposition.recommendation
        row["certification_blocking"] = True
        row["blockers"] = []
        row["current_maturity"] = (
            "PHASE22_V2_B_EMPIRICAL_" + disposition.recommendation
        )
        row["next_gate"] = (
            "Terminal Architect-B Phase22 disposition integrated; "
            "global certification still requires A science and both final exams."
        )

    mandatory = [
        item for item in result_rows if item.get("mandatory") is True
    ]
    if len(mandatory) != 64:
        raise CiboCapitalManagementError(
            "B ledger reconciliation requires 64 mandatory rows"
        )
    terminal = [
        item for item in mandatory if item.get("terminal_disposition") is not None
    ]
    open_rows = [
        item for item in mandatory if item.get("terminal_disposition") is None
    ]
    remaining_external = [
        item
        for item in mandatory
        if (
            item.get("certification_blocking") is True
            and item.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
        )
    ]

    result["current_summary"] = {
        "mandatory_count": 64,
        "terminal_count": len(terminal),
        "open_count": len(open_rows),
        "zero_open_work_pass": len(open_rows) == 0,
        "final_certification_candidate": False,
    }
    result["phase22_b_reconciliation"] = {
        "architect_b_head_sha": package.architect_b_head_sha,
        "phase22_manifest_sha256": package.phase22_manifest_sha256,
        "integrated_workstream_ids": list(_REQUIRED_IDS),
        "remaining_certification_blocking_external_ids": [
            str(item.get("id")) for item in remaining_external
        ],
        "certification_claimed": False,
        "productive_authority": False,
    }
    return result
