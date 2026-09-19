"""Cross-period causal factor forensics for VT31_NAS100_R5.

Replays the frozen R5 development identity on consumed R5/R6/R8 and the
permanently consumed 2022-2024 holdout, then attributes economics to fields
known at or before trade authorization. Diagnostic only.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import cast

import vt31_nas100_r5_certification_candidate as candidate

SCHEMA = "qore.vt31.nas100.r5.cross_period_factor_forensics.v1"


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return candidate.engine._capital_metrics(rows)


def _interactions(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(f"{field}={row.get(field)}" for field in fields)
        groups[key].append(row)
    return {
        key: _metrics(items)
        for key, items in sorted(groups.items())
    }


def analyze(evidence: Path, *, partition: str) -> dict[str, object]:
    replay = candidate.replay(evidence)
    result = cast(dict[str, object], replay["result"])
    rows = cast(list[dict[str, object]], result["trade_rows"])
    specs = {
        "tier_x_family": ("tier", "entry_family"),
        "tier_x_side": ("tier", "side"),
        "family_x_side": ("entry_family", "side"),
        "tier_x_authorization": ("tier", "authorization_reason"),
        "rearm_score_x_side": ("rearm_quality_score", "side"),
        "rearm_first_tier_x_side": ("first_tier", "side"),
    }
    return {
        "schema": SCHEMA,
        "partition": partition,
        "trade_count": len(rows),
        "overall": _metrics(rows),
        "interactions": {
            name: _interactions(rows, fields)
            for name, fields in specs.items()
        },
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "uses_terminal_outcome_at_runtime": False,
            "policy_promoted": False,
            "opens_new_holdout": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = analyze(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
