"""Preregistered consumed-evidence falsification for VT-08 Index V5 context.

Consumes the V4 feature census only; fresh holdout evidence remains sealed.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

STRESS_R = Decimal("0.05")


def _closure_from_sweep(sweep: str) -> str:
    mapping = {
        "high_breakout": "bullish_continuation",
        "low_breakout": "bearish_continuation",
        "high_reclaim": "bearish_reversal",
        "low_reclaim": "bullish_reversal",
    }
    return mapping.get(sweep, "inconclusive")


def _direction(context: str) -> str | None:
    if context.startswith("bullish_"):
        return "long"
    if context.startswith("bearish_"):
        return "short"
    return None


def _mean(rows: list[dict[str, str]]) -> str | None:
    if not rows:
        return None
    total = sum((Decimal(row["outcome_r"]) - STRESS_R for row in rows), Decimal())
    return str(total / len(rows))


def _group(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return {
        name: {"sample": len(items), "stressed_mean_r": _mean(items)}
        for name, items in sorted(grouped.items())
    }


def analyze(rows: list[dict[str, str]]) -> dict[str, Any]:
    enriched: list[dict[str, str]] = []
    matrix: Counter[tuple[str, str]] = Counter()
    for source in rows:
        row = dict(source)
        context = _closure_from_sweep(row["previous_day_sweep_type"])
        direction = _direction(context)
        row["v5_previous_closed_day_context"] = context
        if direction is None:
            relation = "inconclusive"
        elif direction == row["side"]:
            relation = "with_side"
        else:
            relation = "against_side"
        row["v5_context_side_relation"] = relation
        matrix[(row["previous_source_day_body_alignment"], context)] += 1
        enriched.append(row)

    resolvable = [
        row
        for row in enriched
        if row["v5_previous_closed_day_context"] != "inconclusive"
    ]
    opposed = [
        row
        for row in resolvable
        if row["previous_source_day_body_alignment"] == "opposed"
    ]
    opposed_reversal = [
        row
        for row in opposed
        if row["v5_previous_closed_day_context"].endswith("reversal")
    ]
    qualified = [
        row for row in enriched if row["v5_context_side_relation"] == "with_side"
    ]
    agreement = (
        None
        if not opposed
        else str(Decimal(len(opposed_reversal)) / len(opposed))
    )
    confusion_matrix = [
        {"body_alignment": alignment, "closure_context": context, "sample": sample}
        for (alignment, context), sample in sorted(matrix.items())
    ]
    return {
        "schema": "qore.trader_lab.vt08_index_v5_context_falsification.v1",
        "contract": (
            "consumed-evidence-only; no fresh holdout; primary friction 0.05R/trade"
        ),
        "sample": len(enriched),
        "resolvable_sample": len(resolvable),
        "confusion_matrix": confusion_matrix,
        "opposed_reversal_agreement": agreement,
        "by_context_side_relation": _group(enriched, "v5_context_side_relation"),
        "qualified": {
            "sample": len(qualified),
            "stressed_mean_r": _mean(qualified),
            "by_window": _group(qualified, "window_id"),
            "by_market": _group(qualified, "symbol"),
            "by_side": _group(qualified, "side"),
            "by_anchor": _group(qualified, "anchor"),
        },
        "rows": enriched,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    with args.census_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    report = analyze(rows)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
