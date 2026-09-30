"""Integrator support audit for Architect-B provenance coverage.

This audit does not change B workstream status. It expands combined provenance
scopes into B-01..B-24 and reports exactly which mandatory workstreams still
lack an immutable provenance pointer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_b_open_work_ledger import (
    SharedBWorkStatus,
    build_shared_b_open_work_ledger,
)

EXPECTED_B_IDS = tuple(f"B-{i:02d}" for i in range(1, 25))


@dataclass(frozen=True, slots=True)
class BProvenanceCoverage:
    covered_ids: tuple[str, ...]
    missing_ids: tuple[str, ...]
    missing_terminal_ids: tuple[str, ...]
    missing_external_blocked_ids: tuple[str, ...]
    missing_nonterminal_ids: tuple[str, ...]
    coverage_complete: bool


def _expand_scope(scope: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in scope.split("/") if part.strip())
    if not parts:
        raise ValueError("empty capability scope")
    expanded: list[str] = []
    prefix: str | None = None
    for part in parts:
        if part.startswith("B-"):
            prefix = "B-"
            ident = part
        elif prefix == "B-" and part.isdigit():
            ident = f"B-{int(part):02d}"
        else:
            raise ValueError(f"unsupported B capability scope: {scope}")
        if ident not in EXPECTED_B_IDS:
            raise ValueError(f"unknown B workstream in provenance scope: {ident}")
        expanded.append(ident)
    return tuple(sorted(set(expanded)))


def assess_b_provenance_coverage(
    capability_scopes: Iterable[str],
) -> BProvenanceCoverage:
    covered = tuple(
        sorted(
            {
                ident
                for scope in capability_scopes
                for ident in _expand_scope(scope)
            }
        )
    )
    missing = tuple(x for x in EXPECTED_B_IDS if x not in covered)

    ledger = build_shared_b_open_work_ledger()
    rows = {item["work_id"]: item for item in ledger["items"]}
    missing_terminal = tuple(
        ident
        for ident in missing
        if rows[ident]["status"] == SharedBWorkStatus.COMPLETE_AND_PROVEN.value
    )
    missing_external = tuple(
        ident
        for ident in missing
        if rows[ident]["status"] == SharedBWorkStatus.EXTERNALLY_BLOCKED.value
    )
    missing_nonterminal = tuple(
        ident
        for ident in missing
        if ident not in set(missing_terminal) | set(missing_external)
    )
    return BProvenanceCoverage(
        covered_ids=covered,
        missing_ids=missing,
        missing_terminal_ids=missing_terminal,
        missing_external_blocked_ids=missing_external,
        missing_nonterminal_ids=missing_nonterminal,
        coverage_complete=not missing,
    )
