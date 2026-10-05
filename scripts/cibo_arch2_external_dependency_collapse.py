#!/usr/bin/env python3
"""Collapse CIBO certification blockers into real external dependency families.

This report is intentionally conservative:
- it never changes the canonical master ledger;
- it never promotes reused/burned research into Fresh-OOS evidence;
- it separates Architect-2 functional closure from scientific certification closure.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

EXTERNAL = "EXTERNAL_DEPENDENCY_BLOCKED"

FAMILY_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "FRESH_FORWARD_CAUSAL",
        re.compile(
            r"FRESH|FORWARD|OOS|WF1_WF2_WF3_WF4|PHASE20D|CHRONOLOGICAL|"
            r"REAL_DATA_BOUND_CAUSAL|ECONOMIC_VALUE_NOT_YET_DEMONSTRATED|"
            r"CAUSAL_PROFIT_GRADUATION|STRICT_CAPITAL_PRODUCTIVITY|"
            r"POST_FREEZE|FOUR_FOLD"
        ),
    ),
    (
        "PROVIDER_EXECUTION_ECONOMICS",
        re.compile(r"PROVIDER|MARKET_IMPACT|GROSS_EDGE|LEVERAGE_ECONOMIC_ABLATION"),
    ),
    (
        "SCARCITY_CONCENTRATION",
        re.compile(r"SCARCITY|STARVATION|CONCENTRATION"),
    ),
    (
        "PATH_STRESS_TEMPORAL_MC",
        re.compile(
            r"PATH|STRESS|TEMPORAL|MONTE_CARLO|CRISIS|4_OF_4|TRANSITION_UNCERTAINTY"
        ),
    ),
    (
        "COMPOUND_PORTFOLIO_CAPITAL",
        re.compile(
            r"COMPOUND|PORTFOLIO|PROTECTED_BASE|PROTECTED_FLOOR|CAPITAL_PRODUCTIVITY|"
            r"MULTI_GENERATION|PROFIT_|GIVEBACK|EXPANSION|RESERVATION"
        ),
    ),
    (
        "POST_OUTCOME_MEMORY_GOVERNANCE",
        re.compile(r"POST_OUTCOME|MEMORY|HYPOTHESIS|OWNER_REVIEW|FINAL_PROMOTION"),
    ),
    (
        "EXAM_GOVERNANCE",
        re.compile(r"PRE_EXAM|FINAL_GOVERNED|NO_SYNTHETIC_BASELINE|RESEARCH_ONLY"),
    ),
)


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def classify_blocker(blocker: str) -> list[str]:
    families = [name for name, pattern in FAMILY_RULES if pattern.search(blocker)]
    return families or ["UNCLASSIFIED_EXTERNAL"]


def _functional_closed(arch2: dict[str, Any]) -> bool:
    groups = arch2.get("functional_groups", {})
    return bool(groups) and all(
        bool(group.get("functional_completeness"))
        and int(group.get("mandatory_gap_count", 1)) == 0
        for group in groups.values()
    ) and not arch2.get("architect2_internal_blockers", [])


def build_report(
    ledger: dict[str, Any],
    arch2: dict[str, Any],
) -> dict[str, Any]:
    blocked = [
        row
        for row in ledger.get("workstreams", [])
        if row.get("terminal_disposition") == EXTERNAL
    ]
    functional_closed = _functional_closed(arch2)

    atom_rows: dict[str, set[str]] = defaultdict(set)
    family_rows: dict[str, set[str]] = defaultdict(set)
    family_atoms: dict[str, set[str]] = defaultdict(set)
    row_reports: list[dict[str, Any]] = []

    for row in blocked:
        row_id = str(row["id"])
        blockers = [str(item) for item in row.get("blockers", [])]
        row_families: set[str] = set()
        for blocker in blockers:
            atom_rows[blocker].add(row_id)
            for family in classify_blocker(blocker):
                row_families.add(family)
                family_rows[family].add(row_id)
                family_atoms[family].add(blocker)

        kind = str(row.get("kind", ""))
        disposition = "EXTERNAL_CERTIFICATION_EVIDENCE_PENDING"
        if functional_closed and kind in {"CE2I_TOOL", "GEN_C"}:
            disposition = "INTERNAL_FUNCTIONAL_CLOSED__EXTERNAL_SCIENCE_PENDING"
        if row_id == "T11":
            disposition = (
                "EMPIRICAL_PROVIDER_PARTIAL_CLOSURE__"
                "FRESH_GROSS_EDGE_MARKET_IMPACT_PENDING"
            )
        elif row_id in {"T13", "T15"}:
            disposition = (
                "FUNCTIONAL_REDUNDANCY_CLASSIFIED__"
                "SCIENTIFIC_UTILITY_EVIDENCE_PENDING"
            )

        row_reports.append(
            {
                "id": row_id,
                "kind": kind,
                "mandatory": bool(row.get("mandatory")),
                "certification_blocking": bool(row.get("certification_blocking")),
                "reconciliation_disposition": disposition,
                "dependency_families": sorted(row_families),
                "blockers": blockers,
                "canonical_terminal_disposition_preserved": True,
            }
        )

    unique_atoms = sorted(atom_rows)
    family_summary = {}
    for family in sorted(set(family_rows) | {"UNCLASSIFIED_EXTERNAL"}):
        rows = sorted(family_rows.get(family, set()))
        atoms = sorted(family_atoms.get(family, set()))
        family_summary[family] = {
            "row_count": len(rows),
            "rows": rows,
            "unique_blocker_atom_count": len(atoms),
            "blocker_atoms": atoms,
        }

    unclassified = family_summary.get("UNCLASSIFIED_EXTERNAL", {}).get(
        "blocker_atoms", []
    )
    external_count = len(blocked)
    return {
        "schema": "qore.cibo.arch2-external-dependency-collapse.v1",
        "source_ledger_schema": ledger.get("schema"),
        "canonical_ledger_mutated": False,
        "fresh_oos_opened": False,
        "architect2_internal_functional_closure": functional_closed,
        "architect2_internal_blocker_count": len(
            arch2.get("architect2_internal_blockers", [])
        ),
        "external_dependency_blocked_row_count": external_count,
        "unique_external_blocker_atom_count": len(unique_atoms),
        "semantic_dependency_family_count": len(
            [name for name in family_summary if name != "UNCLASSIFIED_EXTERNAL"]
        ),
        "unclassified_external_blocker_atom_count": len(unclassified),
        "actionable_architect2_internal_repair_count": 0 if functional_closed else None,
        "certification_execution_ready": external_count == 0,
        "disposition": (
            "INTERNAL_FUNCTIONAL_CLOSURE_CONFIRMED__"
            "EXTERNAL_SCIENTIFIC_DEPENDENCIES_COLLAPSED"
            if functional_closed and external_count
            else "RECONCILIATION_INCOMPLETE"
        ),
        "dependency_families": family_summary,
        "rows": sorted(row_reports, key=lambda item: item["id"]),
        "governance": {
            "fresh_oos_claimed": False,
            "reused_research_promoted_to_certification": False,
            "outcome_aware_tuning": False,
            "merge_performed": False,
            "live": False,
            "production": False,
            "real_capital": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json"),
    )
    parser.add_argument(
        "--arch2",
        type=Path,
        default=Path(
            "artifacts/arch2/CIBO_ARCH2_CERTIFICATION_BLOCKER_RECONCILIATION_V1.json"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_report(_load(args.ledger), _load(args.arch2))
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
