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
    "symbol", "side", "anchor", "closure_family", "bias_family",
    "source_day_relationship", "previous_source_day_body_alignment",
    "current_source_day_body_alignment", "previous_day_sweep_type",
    "current_day_sweep_type", "recent_causal_h4_range_state",
    "recent_causal_daily_range_state", "cross_index_directional_state",
    "protected_swing_count", "selected_protected_swing_rank",
)
CONTINUOUS = (
    "opposing_series_length", "cisd_latency_m15",
    "protected_swing_confirmation_latency_m15",
    "cisd_to_extreme_normalized_distance", "sweep_depth", "reclaim_depth",
    "closure_reference_range_ratio", "closure_body_fraction",
    "closure_close_position", "protected_risk_fraction",
    "recent_causal_h4_range_ratio", "recent_causal_daily_range_ratio",
    "cross_index_simultaneous_signal_count",
)


def _r(row: dict[str, str]) -> Decimal:
    for key in ("r_multiple", "label_r", "outcome_r", "r"):
        value = row.get(key)
        if value not in (None, ""):
            return Decimal(value)
    raise ValueError("missing R outcome column")


def _summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    vals = [_r(x) - FRICTION for x in rows]
    return {"n": len(vals), "stressed_total_r": str(sum(vals, Decimal(0))),
            "stressed_mean_r": str(sum(vals, Decimal(0)) / Decimal(len(vals))) if vals else None}


def _categorical(rows: list[dict[str, str]], feature: str) -> dict[str, Any]:
    groups: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
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
    idx = [0, (len(vals)-1)//4, (len(vals)-1)//2, 3*(len(vals)-1)//4, len(vals)-1]
    return [vals[i] for i in idx]


def _continuous(rows: list[dict[str, str]], feature: str) -> dict[str, Any]:
    usable = [(row, Decimal(row[feature])) for row in rows if row.get(feature) not in (None, "")]
    edges = _quantile_edges([v for _, v in usable])
    if not edges:
        return {"edges": [], "bins": {}}
    bins: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row, value in usable:
        if value <= edges[1]: b = "q1"
        elif value <= edges[2]: b = "q2"
        elif value <= edges[3]: b = "q3"
        else: b = "q4"
        bins[b][row["window_id"]].append(row)
    return {"edges": [str(x) for x in edges],
            "bins": {b: {w: _summary(bins[b].get(w, [])) for w in WINDOWS} for b in ("q1","q2","q3","q4")}}


def run(census_csv: Path, output_json: Path) -> dict[str, Any]:
    with census_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 183 or set(r["window_id"] for r in rows) != set(WINDOWS):
        raise ValueError("Phase C requires exactly the frozen 183-row three-window census")
    report = {
        "phase": "V5_PHASE_C_REGIME_FORENSICS",
        "contract": "consumed-evidence-only; diagnostic; no candidate freeze; holdout sealed",
        "sample": len(rows), "friction_r_per_trade": str(FRICTION),
        "baseline_by_window": {w: _summary([r for r in rows if r["window_id"] == w]) for w in WINDOWS},
        "categorical": {f: _categorical(rows, f) for f in CATEGORICAL if f in rows[0]},
        "continuous": {f: _continuous(rows, f) for f in CONTINUOUS if f in rows[0]},
        "candidate_freeze_permitted": False, "holdout_open_permitted": False,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--census-csv", type=Path, required=True)
    p.add_argument("--output-json", type=Path, required=True)
    a = p.parse_args(); run(a.census_csv, a.output_json)

if __name__ == "__main__":
    main()
