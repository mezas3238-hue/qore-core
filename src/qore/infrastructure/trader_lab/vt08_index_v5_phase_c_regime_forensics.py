"""VT-08 Index V5 Phase C regime forensics on consumed evidence only."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

FRICTION = Decimal("0.05")
WINDOWS = ("2022_23", "2023_24", "2024_26")
CATEGORICAL = (
    "symbol",
    "side",
    "anchor",
    "closure_family",
    "bias_family",
    "source_day_relationship",
    "previous_source_day_body_alignment",
    "current_source_day_body_alignment",
    "previous_day_sweep_type",
    "current_day_sweep_type",
    "recent_causal_h4_range_state",
    "recent_causal_daily_range_state",
    "cross_index_directional_state",
    "protected_swing_count",
    "selected_protected_swing_rank",
)
CONTINUOUS = (
    "opposing_series_length",
    "cisd_latency_m15",
    "protected_swing_confirmation_latency_m15",
    "cisd_to_extreme_normalized_distance",
    "sweep_depth",
    "reclaim_depth",
    "closure_reference_range_ratio",
    "closure_body_fraction",
    "closure_close_position",
    "protected_risk_fraction",
    "recent_causal_h4_range_ratio",
    "recent_causal_daily_range_ratio",
    "cross_index_simultaneous_same_side_signals",
    "cross_index_simultaneous_opposite_side_signals",
)
PHASE_B_DECOMPOSITION_FEATURES = (
    "symbol",
    "side",
    "anchor",
    "closure_family",
    "bias_family",
    "source_day_relationship",
    "recent_causal_h4_range_state",
    "recent_causal_daily_range_state",
    "cross_index_directional_state",
)


def _r(row: dict[str, str]) -> Decimal:
    for key in ("r_multiple", "label_r", "outcome_r", "r"):
        value = row.get(key)
        if value is not None and value != "":
            return Decimal(value)
    raise ValueError("missing R outcome column")


def _summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    vals = [_r(x) - FRICTION for x in rows]
    total = sum(vals, Decimal(0))
    return {
        "n": len(vals),
        "stressed_total_r": str(total),
        "stressed_mean_r": str(total / Decimal(len(vals))) if vals else None,
    }


def _categorical(rows: list[dict[str, str]], feature: str) -> dict[str, Any]:
    groups: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        groups[row[feature]][row["window_id"]].append(row)
    out: dict[str, Any] = {}
    for value in sorted(groups):
        out[value] = {w: _summary(groups[value].get(w, [])) for w in WINDOWS}
    return out


def _quantile_edges(values: list[Decimal]) -> list[Decimal]:
    vals = sorted(values)
    if not vals:
        return []
    last = len(vals) - 1
    idx = [0, last // 4, last // 2, 3 * last // 4, last]
    return [vals[i] for i in idx]


def _continuous(rows: list[dict[str, str]], feature: str) -> dict[str, Any]:
    usable = [
        (row, Decimal(row[feature]))
        for row in rows
        if row.get(feature) not in (None, "")
    ]
    edges = _quantile_edges([value for _, value in usable])
    if not edges:
        return {"edges": [], "bins": {}}
    bins: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row, value in usable:
        if value <= edges[1]:
            bucket = "q1"
        elif value <= edges[2]:
            bucket = "q2"
        elif value <= edges[3]:
            bucket = "q3"
        else:
            bucket = "q4"
        bins[bucket][row["window_id"]].append(row)
    return {
        "edges": [str(x) for x in edges],
        "bins": {
            bucket: {
                window: _summary(bins[bucket].get(window, [])) for window in WINDOWS
            }
            for bucket in ("q1", "q2", "q3", "q4")
        },
    }


def _phase_b_ideal(row: dict[str, str]) -> bool:
    latency = int(row["cisd_latency_m15"])
    return 0 <= latency <= 15 and int(row["protected_swing_count"]) >= 1


def _phase_b_context_direction(row: dict[str, str]) -> str | None:
    return {
        "high_breakout": "long",
        "low_breakout": "short",
        "high_reclaim": "short",
        "low_reclaim": "long",
    }.get(row["current_day_sweep_type"])


def _phase_b_retained_sets(
    rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    ideal = [row for row in rows if _phase_b_ideal(row)]
    return {
        "H1_ideal_formation": ideal,
        "H2_c2_ideal_formation": [
            row for row in ideal if row["closure_family"] == "c2"
        ],
        "H3_c3_ideal_formation": [
            row for row in ideal if row["closure_family"] == "c3"
        ],
        "H4_ideal_with_source_direction": [
            row
            for row in ideal
            if _phase_b_context_direction(row) == row["side"]
        ],
    }


def _phase_b_failure_decomposition(
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for hypothesis, retained in _phase_b_retained_sets(rows).items():
        report[hypothesis] = {
            "summary": _summary(retained),
            "by_window": {
                window: _summary(
                    [row for row in retained if row["window_id"] == window]
                )
                for window in WINDOWS
            },
            "by_feature": {
                feature: _categorical(retained, feature)
                for feature in PHASE_B_DECOMPOSITION_FEATURES
            },
        }
    return report


def run(census_csv: Path, output_json: Path) -> dict[str, Any]:
    with census_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 183 or set(row["window_id"] for row in rows) != set(WINDOWS):
        raise ValueError("Phase C requires exactly the frozen 183-row three-window census")
    report = {
        "phase": "V5_PHASE_C_REGIME_FORENSICS",
        "contract": "consumed-evidence-only; diagnostic; no candidate freeze; holdout sealed",
        "sample": len(rows),
        "friction_r_per_trade": str(FRICTION),
        "baseline_by_window": {
            window: _summary([row for row in rows if row["window_id"] == window])
            for window in WINDOWS
        },
        "categorical": {
            feature: _categorical(rows, feature)
            for feature in CATEGORICAL
            if feature in rows[0]
        },
        "continuous": {
            feature: _continuous(rows, feature)
            for feature in CONTINUOUS
            if feature in rows[0]
        },
        "phase_b_failure_decomposition": _phase_b_failure_decomposition(rows),
        "candidate_freeze_permitted": False,
        "holdout_open_permitted": False,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    run(args.census_csv, args.output_json)


if __name__ == "__main__":
    main()
