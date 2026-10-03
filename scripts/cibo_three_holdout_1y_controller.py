#!/usr/bin/env python3
"""Finite adaptive-search controller for the CIBO Trader Lab 3x1Y harness.

The controller never manufactures candidates. It consumes a preregistered,
ordered candidate catalog and cumulative results for all three fixed research
holdouts. It either stops on three cross-holdout full passes, emits the next
unevaluated batch, or declares the frozen search space exhausted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    REQUIRED_CROSS_HOLDOUT_PASS_COUNT,
    evaluate_three_groups,
)

BATCH_SIZE = 250


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def next_batch(
    *,
    catalog: dict[str, Any],
    group_payloads: tuple[dict[str, Any], ...],
    batch_size: int = BATCH_SIZE,
) -> dict[str, Any]:
    if catalog.get("schema") != "qore.cibo.trader-lab.3x1y-candidate-catalog.v1":
        raise ValueError("unexpected candidate catalog schema")
    raw_candidates = catalog.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("candidate catalog must be non-empty")

    fingerprints: list[str] = []
    by_fp: dict[str, dict[str, Any]] = {}
    for candidate in raw_candidates:
        if not isinstance(candidate, dict):
            raise ValueError("catalog candidate must be object")
        fp = candidate.get("configuration_fingerprint")
        if not isinstance(fp, str) or not fp:
            raise ValueError("catalog candidate fingerprint missing")
        if fp in by_fp:
            raise ValueError("catalog fingerprints must be unique")
        fingerprints.append(fp)
        by_fp[fp] = candidate

    sensor = evaluate_three_groups(group_payloads)
    if sensor["cross_holdout_full_pass_count"] >= REQUIRED_CROSS_HOLDOUT_PASS_COUNT:
        return {
            "schema": "qore.cibo.trader-lab.3x1y-controller.v1",
            "status": "STOP_THREE_CROSS_HOLDOUT_FULL_PASS",
            "sensor": sensor,
            "next_candidates": [],
            "search_space_size": len(fingerprints),
            "search_exhausted": False,
        }

    evaluated_by_group = []
    for payload in group_payloads:
        rows = payload.get("candidates")
        if not isinstance(rows, list):
            raise ValueError("group candidates missing")
        evaluated_by_group.append(
            {
                str(row["configuration_fingerprint"])
                for row in rows
                if isinstance(row, dict)
                and isinstance(row.get("configuration_fingerprint"), str)
            }
        )

    fully_evaluated = set.intersection(*evaluated_by_group)
    pending = [fp for fp in fingerprints if fp not in fully_evaluated]
    selected = pending[:batch_size]
    exhausted = not selected

    return {
        "schema": "qore.cibo.trader-lab.3x1y-controller.v1",
        "status": (
            "SEARCH_SPACE_EXHAUSTED_NO_THREE_PASS"
            if exhausted
            else "CONTINUE_SEARCH"
        ),
        "sensor": sensor,
        "next_candidates": [by_fp[fp] for fp in selected],
        "next_candidate_fingerprints": selected,
        "evaluated_configuration_count": len(fully_evaluated),
        "remaining_configuration_count": len(pending),
        "search_space_size": len(fingerprints),
        "batch_size": batch_size,
        "search_exhausted": exhausted,
        "adaptive_outcome_aware_research": True,
        "fresh_oos_claimed": False,
        "certification_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--group1", type=Path, required=True)
    parser.add_argument("--group2", type=Path, required=True)
    parser.add_argument("--group3", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()
    if args.batch_size <= 0 or args.batch_size > 1000:
        raise ValueError("batch-size must be in [1,1000]")

    result = next_batch(
        catalog=_json(args.catalog),
        group_payloads=tuple(
            _json(path) for path in (args.group1, args.group2, args.group3)
        ),
        batch_size=args.batch_size,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
