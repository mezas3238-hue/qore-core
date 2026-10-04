#!/usr/bin/env python3
"""WP-11 monotonic governed self-improvement blocker audit.

The audit accepts one or more sealed evidence payloads for MC23/MC24/MC25.
It never requires the original eight blockers to remain open: blockers may
only disappear as stronger sealed evidence is added.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

IDENTITY = "QORE_SHARED_WP11_EXACT_BLOCKER_AUDIT_002"

KNOWN_BLOCKERS = frozenset(
    {
        "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION",
        "MC24_BIND_REAL_MC23_ADAPTATION",
        "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE",
        "MC25_SAME_LINEAGE_PERFORMANCE_STRESS",
        "MC25_FORMAL_STRESS_STAGE",
        "MC25_SAME_LINEAGE_SHADOW",
        "MC25_CERTIFICATION",
        "MC25_GOVERNED_PROMOTION",
    }
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _any_true(rows: Iterable[dict[str, Any]], key: str) -> bool:
    return any(row.get(key) is True for row in rows)


def _status_in(rows: Iterable[dict[str, Any]], *statuses: str) -> bool:
    allowed = set(statuses)
    return any(row.get("status") in allowed for row in rows)


def _identities(rows: Iterable[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(row["identity"])
                for row in rows
                if isinstance(row.get("identity"), str) and row["identity"]
            }
        )
    )


def audit_blockers(
    *,
    mc23_rows: tuple[dict[str, Any], ...],
    mc24_rows: tuple[dict[str, Any], ...],
    mc25_rows: tuple[dict[str, Any], ...],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not mc23_rows or not mc24_rows or not mc25_rows:
        raise ValueError("MC23, MC24 and MC25 evidence groups must be non-empty")

    novelty_bound = _any_true(mc23_rows, "real_novelty_detection_bound") or _status_in(
        mc23_rows,
        "MC23_REAL_NOVELTY_DETECTION_BOUND_PASS",
    )
    regression_bound = _any_true(
        mc24_rows, "real_adaptation_regression_suite_bound"
    ) or _status_in(
        mc24_rows,
        "MC24_REAL_REGRESSION_SUITE_BOUND_PASS",
    )
    lineage_bound = _any_true(mc25_rows, "lineage_integrity_stress_pass") or _status_in(
        mc25_rows,
        "MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_PASS",
    )

    if not novelty_bound:
        raise AssertionError("MC23 real novelty evidence missing")
    if not regression_bound:
        raise AssertionError("MC24 real regression evidence missing")
    if not lineage_bound:
        raise AssertionError("MC25 lineage-integrity stress evidence missing")

    blockers: list[str] = []
    if not _any_true(mc23_rows, "real_novel_regime_validated_adaptation"):
        blockers.append("MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION")
    if not _any_true(mc24_rows, "mc23_real_regime_adaptation_bound"):
        blockers.append("MC24_BIND_REAL_MC23_ADAPTATION")
    if not _any_true(mc24_rows, "empirical_half_life_validated"):
        blockers.append("MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE")
    if not (
        _any_true(mc25_rows, "performance_stress_bound")
        and _any_true(mc25_rows, "performance_stress_pass")
    ):
        blockers.append("MC25_SAME_LINEAGE_PERFORMANCE_STRESS")
    if not _any_true(mc25_rows, "formal_stress_stage_completed"):
        blockers.append("MC25_FORMAL_STRESS_STAGE")
    if not _any_true(mc25_rows, "shadow_stage_bound"):
        blockers.append("MC25_SAME_LINEAGE_SHADOW")
    if not _any_true(mc25_rows, "certification_stage_bound"):
        blockers.append("MC25_CERTIFICATION")
    if not _any_true(mc25_rows, "promotion_allowed"):
        blockers.append("MC25_GOVERNED_PROMOTION")

    blockers_tuple = tuple(sorted(blockers))
    if not set(blockers_tuple).issubset(KNOWN_BLOCKERS):
        raise AssertionError("WP11 produced an unknown blocker")

    previous_blockers: tuple[str, ...] = ()
    if previous is not None:
        raw_previous = previous.get("blockers", ())
        if not isinstance(raw_previous, (list, tuple)):
            raise ValueError("previous blockers must be a list/tuple")
        previous_blockers = tuple(sorted(str(x) for x in raw_previous))
        unknown_previous = set(previous_blockers) - KNOWN_BLOCKERS
        if unknown_previous:
            raise ValueError(
                f"previous WP11 evidence contains unknown blockers: {sorted(unknown_previous)}"
            )
        reopened = set(blockers_tuple) - set(previous_blockers)
        if reopened:
            raise AssertionError(
                f"WP11 blocker monotonicity violated; reopened={sorted(reopened)}"
            )

    complete = not blockers_tuple
    return {
        "identity": IDENTITY,
        "status": (
            "WP11_GOVERNED_SELF_IMPROVEMENT_COMPLETED_AND_PROVEN"
            if complete
            else "WP11_GOVERNED_SELF_IMPROVEMENT_OPEN_EXACT_BLOCKERS"
        ),
        "real_novelty_detection_bound": novelty_bound,
        "real_regression_suite_bound": regression_bound,
        "lineage_integrity_stress_pass": lineage_bound,
        "blocker_count": len(blockers_tuple),
        "blockers": blockers_tuple,
        "previous_blockers": previous_blockers,
        "monotonic_reduction_verified": previous is not None,
        "mc23_evidence_identities": _identities(mc23_rows),
        "mc24_evidence_identities": _identities(mc24_rows),
        "mc25_evidence_identities": _identities(mc25_rows),
        "zero_open_work": complete,
        "wp11_completed_and_proven": complete,
        "productive_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mc23", type=Path, action="append", required=True)
    parser.add_argument("--mc24", type=Path, action="append", required=True)
    parser.add_argument("--mc25", type=Path, action="append", required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = audit_blockers(
        mc23_rows=tuple(_load(path) for path in args.mc23),
        mc24_rows=tuple(_load(path) for path in args.mc24),
        mc25_rows=tuple(_load(path) for path in args.mc25),
        previous=None if args.previous is None else _load(args.previous),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
