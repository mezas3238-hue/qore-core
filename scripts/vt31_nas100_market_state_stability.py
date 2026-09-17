"""Cross-fold temporal stability analysis for VT31_NAS100 Market State Lab V2.

Consumes only already-generated research outputs from consumed R8/R6/R5 folds.
It does not select or authorize a trading rule.  Hypotheses are mechanism
diagnostics, and half-year instability is surfaced explicitly.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

SCHEMA = "qore.vt31.nas100.market_state_stability.v1"
FRICTION = Decimal("0.05")
MIN_HALFYEAR_SAMPLE = 5

Row = dict[str, Any]
Predicate = Callable[[Row], bool]

HYPOTHESES: dict[str, tuple[str, Predicate]] = {
    "moderate-raid-depth": (
        "raid depth is 0.25-0.50 of the frozen 09 reference width",
        lambda row: row.get("raid_depth_ref_bin") == "0.25-0.50",
    ),
    "active-recent-range": (
        "last-15m range is 0.50-0.75 of the frozen 09 reference width",
        lambda row: row.get("recent_range_ref_bin") == "0.50-0.75",
    ),
    "stale-reclaim-8-14m": (
        "reference reclaim occurred 8-14 minutes before the decision",
        lambda row: row.get("reclaim_latency_bin") == "8-14",
    ),
    "moderate-raid-plus-active-range": (
        "moderate raid depth and active recent range coexist",
        lambda row: (
            row.get("raid_depth_ref_bin") == "0.25-0.50"
            and row.get("recent_range_ref_bin") == "0.50-0.75"
        ),
    ),
    "moderate-raid-active-range-no-stale-reclaim": (
        "moderate raid + active recent range without an 8-14m stale reclaim",
        lambda row: (
            row.get("raid_depth_ref_bin") == "0.25-0.50"
            and row.get("recent_range_ref_bin") == "0.50-0.75"
            and row.get("reclaim_latency_bin") != "8-14"
        ),
    ),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _halfyear(local_date: str) -> str:
    parsed = date.fromisoformat(local_date)
    return f"{parsed.year}-H{1 if parsed.month <= 6 else 2}"


def _metrics(rows: list[Row]) -> dict[str, object]:
    terminal = sorted(
        (row for row in rows if row.get("status") == "terminal"),
        key=lambda row: cast(str, row["signal_at"]),
    )
    values = [_d(row["r_multiple"]) - FRICTION for row in terminal]
    equity = Decimal(0)
    peak = Decimal(0)
    max_drawdown = Decimal(0)
    max_losing_streak = 0
    losing_streak = 0
    gross_profit = Decimal(0)
    gross_loss = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value > 0:
            gross_profit += value
            losing_streak = 0
        elif value < 0:
            gross_loss += -value
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0
    sample = len(values)
    return {
        "sample": sample,
        "total_r": format(sum(values, Decimal(0)), "f"),
        "mean_r": (
            format(sum(values, Decimal(0)) / Decimal(sample), "f")
            if sample else None
        ),
        "profit_factor": (
            format(gross_profit / gross_loss, "f")
            if gross_loss > 0 else None
        ),
        "max_drawdown_r": format(max_drawdown, "f"),
        "max_losing_streak": max_losing_streak,
    }


def _halfyear_metrics(rows: list[Row]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        grouped[_halfyear(cast(str, row["local_date"]))].append(row)
    return {key: _metrics(group) for key, group in sorted(grouped.items())}


def _diagnose_hypothesis(
    folds: dict[str, list[Row]],
    description: str,
    predicate: Predicate,
) -> dict[str, object]:
    fold_results: dict[str, object] = {}
    eligible_halfyears = 0
    positive_halfyears = 0
    negative_halfyears = 0
    halfyear_means: list[Decimal] = []
    for fold, rows in sorted(folds.items()):
        selected = [row for row in rows if predicate(row)]
        aggregate = _metrics(selected)
        halfyears = _halfyear_metrics(selected)
        for metrics in halfyears.values():
            if cast(int, metrics["sample"]) < MIN_HALFYEAR_SAMPLE:
                continue
            mean = _d(metrics["mean_r"])
            eligible_halfyears += 1
            halfyear_means.append(mean)
            if mean > 0:
                positive_halfyears += 1
            elif mean < 0:
                negative_halfyears += 1
        fold_results[fold] = {
            "aggregate": aggregate,
            "halfyears": halfyears,
        }

    fold_means = [
        _d(cast(dict[str, object], value["aggregate"])["mean_r"])
        for value in cast(dict[str, dict[str, object]], fold_results).values()
        if cast(dict[str, object], value["aggregate"])["mean_r"] is not None
    ]
    return {
        "description": description,
        "research_only": True,
        "runtime_rule_selected": False,
        "fold_results": fold_results,
        "cross_fold": {
            "folds_with_positive_mean": sum(mean > 0 for mean in fold_means),
            "folds_with_negative_mean": sum(mean < 0 for mean in fold_means),
            "all_fold_means_positive": bool(fold_means) and all(
                mean > 0 for mean in fold_means
            ),
            "all_fold_means_negative": bool(fold_means) and all(
                mean < 0 for mean in fold_means
            ),
        },
        "halfyear_stability": {
            "minimum_sample_per_eligible_block": MIN_HALFYEAR_SAMPLE,
            "eligible_blocks": eligible_halfyears,
            "positive_blocks": positive_halfyears,
            "negative_blocks": negative_halfyears,
            "positive_share": (
                format(Decimal(positive_halfyears) / Decimal(eligible_halfyears), "f")
                if eligible_halfyears else None
            ),
            "min_mean_r": (
                format(min(halfyear_means), "f") if halfyear_means else None
            ),
            "max_mean_r": (
                format(max(halfyear_means), "f") if halfyear_means else None
            ),
        },
    }


def analyze(paths: list[Path]) -> dict[str, object]:
    payloads = [json.loads(path.read_text()) for path in paths]
    folds: dict[str, list[Row]] = {}
    source_bindings: dict[str, object] = {}
    for payload in payloads:
        if payload.get("schema") != "qore.vt31.nas100.market_state_lab.v2":
            raise ValueError("unexpected market-state payload schema")
        if payload.get("research_only") is not True:
            raise ValueError("market-state payload is not research-only")
        contract = cast(dict[str, object], payload["causal_contract"])
        if contract.get("date_level_outcome_lookup") is not False:
            raise ValueError("causal governance mismatch")
        if contract.get("future_bar_lookup") is not False:
            raise ValueError("future-bar governance mismatch")
        partition = cast(str, payload["partition"])
        if partition in folds:
            raise ValueError(f"duplicate partition: {partition}")
        folds[partition] = cast(list[Row], payload["state_matrix"])
        source_bindings[partition] = payload["evidence"]

    required = {"r8_fresh", "r6", "r5"}
    if set(folds) != required:
        raise ValueError(f"required consumed folds are {sorted(required)}")

    hypotheses = {
        name: _diagnose_hypothesis(folds, description, predicate)
        for name, (description, predicate) in HYPOTHESES.items()
    }
    target_geometry = {
        fold: cast(dict[str, object], payload["feature_summaries"])["target_r_bin"]
        for fold, payload in (
            (cast(str, item["partition"]), item) for item in payloads
        )
    }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "research_only": True,
        "opens_new_holdout": False,
        "live_authorized": False,
        "production_authorized": False,
        "selection_governance": {
            "hypotheses_are_diagnostics_not_rules": True,
            "aggregate_profit_cannot_select_policy": True,
            "halfyear_instability_blocks_freeze": True,
            "date_level_lookup_prohibited": True,
        },
        "source_bindings": source_bindings,
        "hypotheses": hypotheses,
        "target_geometry_by_fold": target_geometry,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = analyze(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "hypotheses": {
                    key: {
                        "cross_fold": value["cross_fold"],
                        "halfyear_stability": value["halfyear_stability"],
                    }
                    for key, value in cast(
                        dict[str, dict[str, object]], payload["hypotheses"]
                    ).items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
