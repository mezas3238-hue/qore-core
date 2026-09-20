"""Two-stage DEEP -> DOL1 continuation forensics for VT31_NAS100.

Diagnostic only.

Stage 1 comes from Target Decision Engine V2:
- DEEP permission is granted at entry only when compressed reference volatility
  is present and no stable 4/4 shallow interaction is active.

Stage 2 asks whether information visible at the CLOSE of the M1 bar that
touched DOL1 can confirm continued structural delivery.

Only DEEP trades that actually touched DOL1 are studied.
Future DOL2/DOL3 reach is a research-only label.
No target/runner policy is changed here.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import vt31_nas100_target_decision_engine_frontier_v2 as decision
import vt31_nas100_target_structure_expansion_falsification_v1 as target

SCHEMA = "qore.vt31.nas100.deep_dol1_continuation_forensics.v1"

FEATURES = (
    "target_clock_bucket",
    "fill_to_target_bucket",
    "last5_overlap_bucket",
    "last5_path_efficiency_bucket",
    "last5_favorable_close_bucket",
    "close_giveback_bucket",
    "target_bar_body_bucket",
    "target_bar_favorable_body",
    "target_bar_close_beyond_target",
    "consecutive_favorable_closes",
    "entry_family",
    "tier",
    "side",
)

PAIRS = (
    ("target_bar_close_beyond_target", "last5_path_efficiency_bucket"),
    ("target_bar_close_beyond_target", "last5_overlap_bucket"),
    ("target_bar_close_beyond_target", "last5_favorable_close_bucket"),
    ("target_bar_favorable_body", "target_bar_body_bucket"),
    ("last5_path_efficiency_bucket", "last5_overlap_bucket"),
    ("last5_path_efficiency_bucket", "close_giveback_bucket"),
    ("target_clock_bucket", "target_bar_close_beyond_target"),
)


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    n = len(rows)

    def rate(field: str) -> str:
        if not n:
            return "0"
        return format(
            Decimal(sum(bool(row[field]) for row in rows)) / Decimal(n),
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
    payload = target.replay(path, partition=partition)
    observations = list(payload["observations"])

    deep: list[dict[str, object]] = []
    shallow_target_winners = 0
    neutral_target_winners = 0
    for row in observations:
        state, reasons = decision._destination_state(row)
        updated = dict(row)
        updated["entry_destination_state_v2"] = state
        updated["entry_destination_reasons_v2"] = list(reasons)
        if state == "DEEP":
            deep.append(updated)
        elif state == "SHALLOW":
            shallow_target_winners += 1
        else:
            neutral_target_winners += 1

    dimensions = {
        field: _group(deep, (field,))
        for field in FEATURES
    }
    pairs = {
        " x ".join(fields): _group(deep, fields)
        for fields in PAIRS
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "all_target_winners": len(observations),
        "deep_target_winners": len(deep),
        "shallow_target_winners": shallow_target_winners,
        "neutral_target_winners": neutral_target_winners,
        "deep_overall": _stats(deep),
        "dimensions": dimensions,
        "pairs": pairs,
        "governance": {
            "diagnostic_only": True,
            "stage1_uses_entry_known_features_only": True,
            "stage2_features_known_at_dol1_close": True,
            "stage2_effective_next_m1_only": True,
            "future_extension_runtime_input": False,
            "target_changed": False,
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
                "all_target_winners": payload["all_target_winners"],
                "deep_target_winners": payload["deep_target_winners"],
                "deep_overall": payload["deep_overall"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
