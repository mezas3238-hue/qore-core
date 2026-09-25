"""R2-BW AUDUSD passive-opportunity overlap Expected-R walk-forward.

Frozen before R2-BT outcome inspection.

Prior consumed evidence from R2-AX identified confirmation/source overlap
0.50-0.75 as the strongest broad toxic confirmation state. R2-BW asks one
narrow question: does that pre-entry geometry add information to the strongest
small root-cause memory when the learning target is the passive opportunity
itself?

Only one new binary feature is introduced:
- OVERLAP_TOXIC_050_075
- OVERLAP_OTHER

Single head:
- REF_DELAY_DIRECTION_OVERLAP_FLAG

The target and causal population come from R2-BT:
- corrected CONF_RANGE_MID passive R on fill;
- 0R on no-fill;
- prior 4Y training -> next 1Y OOS;
- empirical-Bayes shrinkage;
- fixed 20% training-score abstention semantics.

No target, stop, lifecycle, fill rule, or passive arm changes.
Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bt_audusd_passive_opportunity_expected_r_wf as r2bt,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bh_audusd_entry_viability_wf import (
    END,
    START,
    TRAINING_YEARS,
    _year_start,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bj_audusd_root_cause_expected_r_family import (
    ABSTENTION_FRACTION,
    MIN_CELL_SUPPORT,
    PRIOR_STRENGTH,
)

IDENTITY = "VT08_CRT_PURE_R2BW_AUDUSD_PASSIVE_OVERLAP_EXPECTED_R_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2bw_audusd_passive_overlap_expected_r_wf.v1"
HEAD = "REF_DELAY_DIRECTION_OVERLAP_FLAG"
MIN_DENSITY_PER_YEAR = 170.0
TOXIC_OVERLAP_LABEL = "CONFOVERLAP_0_50_TO_0_75"


@dataclass(frozen=True, slots=True)
class CellModel:
    baseline_mean_r: float
    cell_expected_r: tuple[tuple[str, float], ...]
    threshold: float

    def score(self, record: r2bt.OpportunityRecord) -> float:
        return dict(self.cell_expected_r).get(
            _cell_key(record),
            self.baseline_mean_r,
        )


def _coarse_ref(value: str) -> str:
    return "REF1" if value == "REF1" else "REF2_PLUS"


def _coarse_delay(value: str) -> str:
    if value in {"D1", "D2"}:
        return value
    return "D3_PLUS"


def _overlap_flag(record: r2bt.OpportunityRecord) -> str:
    return (
        "OVERLAP_TOXIC_050_075"
        if record.feature("confirmation_source_overlap")
        == TOXIC_OVERLAP_LABEL
        else "OVERLAP_OTHER"
    )


def _cell_key(record: r2bt.OpportunityRecord) -> str:
    return "|".join(
        (
            _coarse_ref(record.feature("source_reference_count")),
            _coarse_delay(record.feature("confirmation_delay")),
            record.feature("direction"),
            _overlap_flag(record),
        )
    )


def _fit(
    training: tuple[r2bt.OpportunityRecord, ...],
) -> tuple[CellModel, dict[str, Any]]:
    if not training:
        return (
            CellModel(
                baseline_mean_r=0.0,
                cell_expected_r=(),
                threshold=float("-inf"),
            ),
            {"reason": "EMPTY_TRAINING"},
        )

    baseline = sum(record.opportunity_r for record in training) / len(training)
    totals: Counter[str] = Counter()
    sums: defaultdict[str, float] = defaultdict(float)
    for record in training:
        key = _cell_key(record)
        totals[key] += 1
        sums[key] += record.opportunity_r

    expected: list[tuple[str, float]] = []
    for key, count in sorted(totals.items()):
        if count < MIN_CELL_SUPPORT:
            continue
        estimate = (
            sums[key] + PRIOR_STRENGTH * baseline
        ) / (count + PRIOR_STRENGTH)
        expected.append((key, round(estimate, 10)))

    provisional = CellModel(
        baseline_mean_r=baseline,
        cell_expected_r=tuple(expected),
        threshold=float("-inf"),
    )
    scores = sorted(provisional.score(record) for record in training)
    cutoff_index = min(
        len(scores) - 1,
        max(0, int(len(scores) * ABSTENTION_FRACTION) - 1),
    )
    threshold = scores[cutoff_index]
    model = CellModel(
        baseline_mean_r=baseline,
        cell_expected_r=tuple(expected),
        threshold=threshold,
    )
    retained = tuple(
        record for record in training if model.score(record) > threshold
    )
    rejected = tuple(
        record for record in training if model.score(record) <= threshold
    )
    return model, {
        "head": HEAD,
        "baseline_mean_r": round(baseline, 10),
        "eligible_cells": len(expected),
        "threshold": round(threshold, 10),
        "training_retained": len(retained),
        "training_rejected": len(rejected),
        "training_retention": round(len(retained) / len(training), 8),
        "training_baseline_metrics": r2bt._metrics(training),
        "training_retained_metrics": r2bt._metrics(retained),
        "training_rejected_metrics": r2bt._metrics(rejected),
    }


def _run(
    records: tuple[r2bt.OpportunityRecord, ...],
) -> dict[str, Any]:
    baseline_oos: list[r2bt.OpportunityRecord] = []
    retained_oos: list[r2bt.OpportunityRecord] = []
    folds: list[dict[str, Any]] = []

    for oos_year in range(START.year + TRAINING_YEARS, END.year):
        training = r2bt._opportunity_slice(
            records,
            _year_start(oos_year - TRAINING_YEARS),
            _year_start(oos_year),
        )
        oos = r2bt._opportunity_slice(
            records,
            _year_start(oos_year),
            _year_start(oos_year + 1),
        )
        model, fit = _fit(training)
        retained = tuple(
            record for record in oos if model.score(record) > model.threshold
        )
        baseline_oos.extend(oos)
        retained_oos.extend(retained)
        folds.append(
            {
                "training_start": _year_start(
                    oos_year - TRAINING_YEARS
                ).isoformat(),
                "oos_start": _year_start(oos_year).isoformat(),
                "fit": fit,
                "oos_baseline": r2bt._metrics(oos),
                "oos_retained": r2bt._metrics(retained),
                "oos_retention": (
                    None if not oos else round(len(retained) / len(oos), 8)
                ),
            }
        )

    baseline = tuple(
        sorted(
            baseline_oos,
            key=lambda row: row.base.trade.entry_opened_at,
        )
    )
    retained = tuple(
        sorted(
            retained_oos,
            key=lambda row: row.base.trade.entry_opened_at,
        )
    )
    baseline_metrics = r2bt._metrics(baseline)
    retained_metrics = r2bt._metrics(retained)
    years = len(folds)
    fills_per_year = (
        0.0
        if years == 0
        else int(retained_metrics["fills"]) / years
    )
    positive_fraction = (
        0.0
        if not folds
        else sum(
            float(fold["oos_retained"]["opportunity_total_r"]) > 0
            for fold in folds
        )
        / len(folds)
    )
    return {
        "folds": folds,
        "combined_oos_baseline": baseline_metrics,
        "combined_oos_retained": retained_metrics,
        "oos_signal_retention": (
            None if not baseline else round(len(retained) / len(baseline), 8)
        ),
        "oos_fills_per_year": round(fills_per_year, 8),
        "positive_oos_year_fraction": round(positive_fraction, 8),
        "research_checks": {
            "fill_density_ge_170": fills_per_year >= MIN_DENSITY_PER_YEAR,
            "opportunity_total_r_improved": (
                float(retained_metrics["opportunity_total_r"])
                > float(baseline_metrics["opportunity_total_r"])
            ),
            "opportunity_mean_r_improved": (
                float(retained_metrics["opportunity_mean_r"] or 0.0)
                > float(baseline_metrics["opportunity_mean_r"] or 0.0)
            ),
            "passive_pf_improved": (
                float(
                    retained_metrics["passive_economics"][
                        "profit_factor"
                    ] or 0.0
                )
                > float(
                    baseline_metrics["passive_economics"][
                        "profit_factor"
                    ] or 0.0
                )
            ),
        },
    }


def run_walk_forward() -> tuple[
    tuple[r2bt.OpportunityRecord, ...],
    dict[str, Any],
]:
    records, bt_report = r2bt.run_walk_forward()
    result = _run(records)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "AUDUSD",
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "source_identity": bt_report["identity"],
        "head": HEAD,
        "training_years": TRAINING_YEARS,
        "abstention_fraction_fixed": ABSTENTION_FRACTION,
        "minimum_cell_support": MIN_CELL_SUPPORT,
        "prior_strength": PRIOR_STRENGTH,
        "new_dimension": "confirmation_source_overlap",
        "new_dimension_encoding": {
            TOXIC_OVERLAP_LABEL: "OVERLAP_TOXIC_050_075",
            "all_other_states": "OVERLAP_OTHER",
        },
        "frozen_before_r2bt_outcome_inspection": True,
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
    with (args.output / "opportunities.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print(
        "CRT_R2BW_AUDUSD_PASSIVE_OVERLAP_EXPECTED_R_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
