"""R2-BV USDJPY tie-safe REF_DELAY_OVERLAP walk-forward.

R2-BU found useful but insufficient information in REF_DELAY_OVERLAP. It also
showed that the nominal 20% score-abstention contract could reject materially
more than 20% when many records shared the cutoff score.

R2-BV changes only cutoff semantics:
- same USDJPY-only population;
- same REF_DELAY_OVERLAP cells;
- same 4Y -> 1Y OOS;
- same empirical-Bayes estimates;
- same nominal 20% abstention budget;
- whole tied score groups are rejected only while cumulative training rejection
  stays <= the fixed budget;
- the cutoff tie group is retained if rejecting it would exceed the budget.

No new market feature, threshold fraction, target, stop, lifecycle, or economic
state search is introduced.

Research only.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bc_usdjpy_confirmation_geometry_atlas import (
    END,
    START,
    run_atlas,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bn_usdjpy_root_cause_expected_r_wf import (
    ABSTENTION_FRACTION,
    MIN_CELL_SUPPORT,
    PRIOR_STRENGTH,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bu_usdjpy_overlap_expected_r_wf import (
    COST_DIAGNOSTICS_R,
    OverlapRecord,
    _cell_key,
    _metrics,
    _record,
    _slice,
    _year_start,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bu_usdjpy_overlap_expected_r_wf import (
    MemoryHead as BuMemoryHead,
)

IDENTITY = "VT08_CRT_PURE_R2BV_USDJPY_OVERLAP_TIE_SAFE_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2bv_usdjpy_overlap_tie_safe_wf.v1"
HEAD = BuMemoryHead.REF_DELAY_OVERLAP
MIN_DENSITY_PER_YEAR = 170.0


@dataclass(frozen=True, slots=True)
class TieSafeModel:
    baseline_mean_r: float
    cell_expected_r: tuple[tuple[str, float], ...]
    retain_at_or_above: float

    def score(self, record: OverlapRecord) -> float:
        return dict(self.cell_expected_r).get(
            _cell_key(record, HEAD),
            self.baseline_mean_r,
        )

    def retain(self, record: OverlapRecord) -> bool:
        return self.score(record) >= self.retain_at_or_above


def _fit_tie_safe(
    training: tuple[OverlapRecord, ...],
) -> tuple[TieSafeModel, dict[str, Any]]:
    if not training:
        model = TieSafeModel(
            baseline_mean_r=0.0,
            cell_expected_r=(),
            retain_at_or_above=float("-inf"),
        )
        return model, {"reason": "EMPTY_TRAINING"}

    baseline = sum(
        float(record.trade.r_multiple) for record in training
    ) / len(training)
    totals: Counter[str] = Counter()
    sums: defaultdict[str, float] = defaultdict(float)
    for record in training:
        key = _cell_key(record, HEAD)
        totals[key] += 1
        sums[key] += float(record.trade.r_multiple)

    expected: list[tuple[str, float]] = []
    for key, count in sorted(totals.items()):
        if count < MIN_CELL_SUPPORT:
            continue
        estimate = (
            sums[key] + PRIOR_STRENGTH * baseline
        ) / (count + PRIOR_STRENGTH)
        expected.append((key, round(estimate, 10)))

    provisional = TieSafeModel(
        baseline_mean_r=baseline,
        cell_expected_r=tuple(expected),
        retain_at_or_above=float("-inf"),
    )
    score_counts: Counter[float] = Counter(
        provisional.score(record) for record in training
    )
    rejection_budget = math.floor(len(training) * ABSTENTION_FRACTION)
    rejected = 0
    rejected_scores: list[float] = []
    for score, count in sorted(score_counts.items()):
        if rejected + count > rejection_budget:
            break
        rejected += count
        rejected_scores.append(score)

    if rejected_scores:
        higher_scores = sorted(
            score for score in score_counts if score > rejected_scores[-1]
        )
        retain_at_or_above = (
            higher_scores[0] if higher_scores else float("inf")
        )
    else:
        retain_at_or_above = min(score_counts)

    model = TieSafeModel(
        baseline_mean_r=baseline,
        cell_expected_r=tuple(expected),
        retain_at_or_above=retain_at_or_above,
    )
    retained_rows = tuple(
        record for record in training if model.retain(record)
    )
    rejected_rows = tuple(
        record for record in training if not model.retain(record)
    )
    return model, {
        "head": HEAD.value,
        "baseline_mean_r": round(baseline, 10),
        "eligible_cells": len(expected),
        "nominal_abstention_fraction": ABSTENTION_FRACTION,
        "rejection_budget": rejection_budget,
        "actual_rejected": len(rejected_rows),
        "actual_rejection_fraction": round(
            len(rejected_rows) / len(training),
            8,
        ),
        "retain_at_or_above": round(retain_at_or_above, 10),
        "cutoff_tie_retained": True,
        "training_baseline_metrics": _metrics(training),
        "training_retained_metrics": _metrics(retained_rows),
        "training_rejected_metrics": _metrics(rejected_rows),
    }


def _run_walk_forward(
    records: tuple[OverlapRecord, ...],
) -> dict[str, Any]:
    baseline_oos: list[OverlapRecord] = []
    retained_oos: list[OverlapRecord] = []
    folds: list[dict[str, Any]] = []

    for oos_year in range(START.year + 4, END.year):
        training = _slice(
            records,
            _year_start(oos_year - 4),
            _year_start(oos_year),
        )
        oos = _slice(
            records,
            _year_start(oos_year),
            _year_start(oos_year + 1),
        )
        model, fit = _fit_tie_safe(training)
        retained = tuple(
            record for record in oos if model.retain(record)
        )
        baseline_oos.extend(oos)
        retained_oos.extend(retained)
        folds.append(
            {
                "training_start": _year_start(oos_year - 4).isoformat(),
                "oos_start": _year_start(oos_year).isoformat(),
                "fit": fit,
                "oos_baseline": _metrics(oos),
                "oos_retained": _metrics(retained),
                "oos_retention": (
                    None if not oos else round(len(retained) / len(oos), 8)
                ),
            }
        )

    baseline = tuple(
        sorted(baseline_oos, key=lambda row: row.trade.entry_opened_at)
    )
    retained = tuple(
        sorted(retained_oos, key=lambda row: row.trade.entry_opened_at)
    )
    baseline_metrics = _metrics(baseline)
    retained_metrics = _metrics(retained)
    years = len(folds)
    trades_per_year = 0.0 if years == 0 else len(retained) / years
    positive_fraction = (
        0.0
        if not folds
        else sum(
            float(fold["oos_retained"]["total_r"]) > 0
            for fold in folds
        )
        / len(folds)
    )
    return {
        "folds": folds,
        "combined_oos_baseline": baseline_metrics,
        "combined_oos_retained": retained_metrics,
        "oos_retention": (
            None if not baseline else round(len(retained) / len(baseline), 8)
        ),
        "oos_trades_per_year": round(trades_per_year, 8),
        "positive_oos_year_fraction": round(positive_fraction, 8),
        "research_checks": {
            "density_ge_170": trades_per_year >= MIN_DENSITY_PER_YEAR,
            "pf_improved": (
                float(retained_metrics["profit_factor"] or 0.0)
                > float(baseline_metrics["profit_factor"] or 0.0)
            ),
            "total_r_improved": (
                float(retained_metrics["total_r"])
                > float(baseline_metrics["total_r"])
            ),
            "mean_r_improved": (
                float(retained_metrics["mean_r"] or 0.0)
                > float(baseline_metrics["mean_r"] or 0.0)
            ),
        },
    }


def run_walk_forward() -> tuple[
    tuple[OverlapRecord, ...],
    dict[str, Any],
]:
    confirmation_records, source_report = run_atlas()
    records = tuple(_record(record) for record in confirmation_records)
    result = _run_walk_forward(records)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "USDJPY",
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "source_population_identity": source_report["identity"],
        "source_population_trades": len(records),
        "head": HEAD.value,
        "training_years": 4,
        "abstention_fraction_fixed": ABSTENTION_FRACTION,
        "tie_policy": "RETAIN_CUTOFF_TIE_IF_REJECTING_IT_EXCEEDS_BUDGET",
        "minimum_cell_support": MIN_CELL_SUPPORT,
        "prior_strength": PRIOR_STRENGTH,
        "cost_diagnostics_r": list(COST_DIAGNOSTICS_R),
        "new_feature_dimensions_added": False,
        **result,
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return records, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records, report = run_walk_forward()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print(
        "CRT_R2BV_USDJPY_OVERLAP_TIE_SAFE_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
