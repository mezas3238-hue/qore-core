"""Architect A internal-readiness contract for CIBO.

This module proves only that Architect A has exhausted the engineering,
preregistration and test surface that A itself owns. It is not scientific
closure, integration, certification or production authority.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

LEDGER_PATH = Path("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
SCHEMA = "QORE_CIBO_ARCH_A_INTERNAL_READINESS_V1"

A_WORKSTREAM_IDS = (
    "T04", "T05", "T06", "T07", "T08", "T09", "T10", "T12", "T13",
    "T14", "T15", "T18", "T19", "GEN-C1", "GEN-C2", "GEN-C3", "GEN-C4",
    "GEN-C5", "GEN-C6", "GEN-C7", "GEN-C8", "GEN-C9", "GEN-C10",
    "GEN-C11", "GEN-C12", "GEN-C13", "GEN-C14", "COMPOUND_ENGINE",
    "COMPOUND_PORTFOLIO", "INTERNAL_CAPITAL_MARKET", "CAPITAL_GENERATIONS",
    "PROTECTED_BASE_CAPITAL", "PROFIT_PROTECTION", "PATH_DEPENDENT_MONTE_CARLO",
    "ADVERSARIAL_STRESS", "TEMPORAL_REPLICATION", "CAPITAL_AMPLIFICATION",
    "AS_IS_ECONOMIC_BASELINE",
)

_INTERNAL_DEBT_MARKERS = (
    "REGISTRY_RECONCILIATION_REQUIRED", "CI_PENDING", "NOT_IMPLEMENTED",
    "ARCHITECTURE_ONLY", "PREREGISTRATION_REQUIRED", "PROTOCOL_REQUIRED",
    "TEST_REQUIRED", "ENGINE_REQUIRED", "CHILD_CI_REQUIRED",
    "REVALIDATION_REQUIRED", "MISSING_IMPLEMENTATION",
)


class ArchitectAReadinessError(RuntimeError):
    """Raised when the canonical ledger cannot be audited safely."""


@dataclass(frozen=True, slots=True)
class ArchitectAInternalReadinessReport:
    schema: str
    passed: bool
    workstream_count: int
    terminal_count: int
    empirical_open_count: int
    terminal_ids: tuple[str, ...]
    empirical_open_ids: tuple[str, ...]
    internal_debt_ids: tuple[str, ...]
    missing_workstream_ids: tuple[str, ...]
    evidence_missing_ids: tuple[str, ...]
    scientific_closure_claimed: bool = False
    integration_authority: bool = False
    production_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_architect_a_internal_readiness(
    ledger_path: Path = LEDGER_PATH,
) -> ArchitectAInternalReadinessReport:
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    rows = payload.get("workstreams")
    if not isinstance(rows, list):
        raise ArchitectAReadinessError("canonical workstreams array is required")

    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ArchitectAReadinessError("canonical workstream row is invalid")
        row_id = str(row["id"])
        if row_id in by_id:
            raise ArchitectAReadinessError(f"duplicate workstream id: {row_id}")
        by_id[row_id] = row

    missing = tuple(item for item in A_WORKSTREAM_IDS if item not in by_id)
    internal_debt: list[str] = []
    evidence_missing: list[str] = []
    terminal: list[str] = []
    empirical_open: list[str] = []

    for row_id in A_WORKSTREAM_IDS:
        row = by_id.get(row_id)
        if row is None:
            continue
        if row.get("mandatory") is not True:
            raise ArchitectAReadinessError(
                f"Architect A workstream must remain mandatory: {row_id}"
            )

        blockers_raw = row.get("blockers", [])
        blockers = (
            tuple(str(item) for item in blockers_raw)
            if isinstance(blockers_raw, list)
            else ()
        )
        searchable = " ".join(
            (
                str(row.get("current_maturity", "")),
                *blockers,
                str(row.get("next_gate", "")),
            )
        ).upper()
        if any(marker in searchable for marker in _INTERNAL_DEBT_MARKERS):
            internal_debt.append(row_id)

        evidence = row.get("evidence_refs")
        if not isinstance(evidence, list) or not evidence:
            evidence_missing.append(row_id)

        if row.get("terminal_disposition") is None:
            empirical_open.append(row_id)
            if not blockers:
                internal_debt.append(row_id)
        else:
            terminal.append(row_id)
            if blockers:
                internal_debt.append(row_id)

    internal_debt = list(dict.fromkeys(internal_debt))
    passed = not missing and not internal_debt and not evidence_missing
    return ArchitectAInternalReadinessReport(
        schema=SCHEMA,
        passed=passed,
        workstream_count=len(A_WORKSTREAM_IDS),
        terminal_count=len(terminal),
        empirical_open_count=len(empirical_open),
        terminal_ids=tuple(terminal),
        empirical_open_ids=tuple(empirical_open),
        internal_debt_ids=tuple(internal_debt),
        missing_workstream_ids=missing,
        evidence_missing_ids=tuple(evidence_missing),
    )
