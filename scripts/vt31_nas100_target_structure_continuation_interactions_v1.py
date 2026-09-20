"""Target/structure continuation interaction forensics for VT31_NAS100.

Consumes V1 target-expansion observations from the current causal stack.
Diagnostic only.

Question:
Which interactions visible at the close of the M1 bar that touched DOL1
reliably distinguish genuine continuation from structural exhaustion?

No target, runner, stop, entry, admission, risk, Silver Bullet or lifecycle
policy is changed. Future extension remains a research-only label.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import vt31_nas100_target_structure_expansion_falsification_v1 as base

SCHEMA = (
    "qore.vt31.nas100.target_structure_continuation_interactions.v1"
)
MIN_SAMPLE = 5

INTERACTIONS = (
    (
        "target_bar_close_beyond_target",
        "last5_path_efficiency_bucket",
    ),
    (
        "target_bar_close_beyond_target",
        "last5_overlap_bucket",
    ),
    (
        "target_bar_close_beyond_target",
        "last5_favorable_close_bucket",
    ),
    (
        "target_bar_close_beyond_target",
        "close_giveback_bucket",
    ),
    (
        "target_bar_favorable_body",
        "target_bar_body_bucket",
    ),
    (
        "last5_path_efficiency_bucket",
        "last5_overlap_bucket",
    ),
    (
        "last5_path_efficiency_bucket",
        "last5_favorable_close_bucket",
    ),
    (
        "target_clock_bucket",
        "target_bar_close_beyond_target",
    ),
    (
        "entry_family",
        "target_bar_close_beyond_target",
    ),
    (
        "tier",
        "target_bar_close_beyond_target",
    ),
    (
        "current_path_bucket",
        "target_bar_close_beyond_target",
    ),
    (
        "reference_volatility_state",
        "target_bar_close_beyond_target",
    ),
)

TRIPLES = (
    (
        "target_bar_close_beyond_target",
        "last5_path_efficiency_bucket",
        "last5_favorable_close_bucket",
    ),
    (
        "target_bar_close_beyond_target",
        "last5_overlap_bucket",
        "close_giveback_bucket",
    ),
)


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    n = len(rows)

    def rate(field: str) -> str:
        if n == 0:
            return "0"
        return format(
            Decimal(sum(bool(row[field]) for row in rows))
            / Decimal(n),
            "f",
        )

    return {
        "sample": n,
        "extension_0_25_rate": rate("post_target_reached_0_25"),
        "extension_0_50_rate": rate("post_target_reached_0_50"),
        "extension_1_00_rate": rate("post_target_reached_1_00"),
        "extension_1_50_rate": rate("post_target_reached_1_50"),
        "extension_2_00_rate": rate("post_target_reached_2_00"),
    }


def _group(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(
            f"{field}={row.get(field)}"
            for field in fields
        )
        grouped[key].append(row)
    return {
        key: _stats(items)
        for key, items in sorted(grouped.items())
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    payload = base.replay(path, partition=partition)
    rows = list(payload["observations"])

    interactions = {
        " x ".join(fields): _group(rows, fields)
        for fields in INTERACTIONS
    }
    triples = {
        " x ".join(fields): _group(rows, fields)
        for fields in TRIPLES
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "overall": payload["overall"],
        "target_winner_count": payload["target_winner_count"],
        "interactions": interactions,
        "triples": triples,
        "governance": {
            "diagnostic_only": True,
            "features_known_by_next_m1": True,
            "future_extension_runtime_input": False,
            "current_structural_target_changed": False,
            "runner_policy_changed": False,
            "stop_changed": False,
            "silver_bullet_changed": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "target_winner_count": payload["target_winner_count"],
                "overall": payload["overall"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
