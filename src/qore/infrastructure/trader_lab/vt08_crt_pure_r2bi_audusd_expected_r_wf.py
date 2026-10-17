"""R2-BI AUDUSD causal expected-R selection walk-forward.

R2-BH reduced dead-on-arrival risk but worsened PF and Total-R. That falsified
bad-stop probability as the economic objective.

R2-BI estimates *expected R* from the exact same pre-entry feature family using
only the immediately preceding four years.

To reduce researcher degrees of freedom:
- the abstention fraction is fixed at 20% before outcomes;
- no per-fold retention arm is selected by training PnL;
- categorical state means are shrunk strongly toward the training baseline;
- only states with >=30 training observations contribute;
- the training 20th-percentile score becomes the next OOS year's fixed threshold.

No signal, stop, target, protection or lifecycle rule changes.

Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    _summary,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bh_audusd_entry_viability_wf import (
    END,
    START,
    TRAINING_YEARS,
    ViabilityRecord,
    _build_records,
    _slice,
    _trades,
    _year_start,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2m_survivor_robustness import (
    _stress_summary,
)

IDENTITY = "VT08_CRT_PURE_R2BI_AUDUSD_EXPECTED_R_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2bi_audusd_expected_r_wf.v1"
ABSTENTION_FRACTION = 0.20
MIN_STATE_SUPPORT = 30
PRIOR_STRENGTH = 50.0
MIN_DENSITY_PER_YEAR = 170.0
COST_DIAGNOSTICS_R: tuple[float, ...] = (0.02, 0.05)


@dataclass(frozen=True, slots=True)
class ExpectedRModel:
    baseline_mean_r: float
    state_lifts: tuple[tuple[str, str, float], ...]
    score_threshold: float

    def score(self, record: ViabilityRecord) -> float:
        lookup = {
            (dimension, label): value
            for dimension, label, value in self.state_lifts
        }
        lifts = [
            lookup[(dimension, label)]
            for dimension, label in record.features
            if (dimension, label) in lookup
        ]
        if not lifts:
            return self.baseline_mean_r
        return self.baseline_mean_r + sum(lifts) / len(lifts)


def _metrics(records: tuple[ViabilityRecord, ...]) -> dict[str, Any]:
    trades = _trades(records)
    summary = _summary(trades)
    dead = sum(record.dead_on_arrival for record in records)
    return {
        **summary,
        "dead_on_arrival": dead,
        "dead_on_arrival_rate": (
            0.0 if not records else round(dead / len(records), 8)
        ),
        "cost_stress": {
            f"COST_{cost:.2f}R": _stress_summary(trades, cost)
            for cost in COST_DIAGNOSTICS_R
        },
    }


def _fit_model(
    training: tuple[ViabilityRecord, ...],
) -> tuple[ExpectedRModel, dict[str, Any]]:
    if not training:
        return (
            ExpectedRModel(
                baseline_mean_r=0.0,
                state_lifts=(),
                score_threshold=float("-inf"),
            ),
            {"reason": "EMPTY_TRAINING"},
        )

    baseline_mean = sum(
        float(record.trade.r_multiple) for record in training
    ) / len(training)

    totals: Counter[tuple[str, str]] = Counter()
    sums: defaultdict[tuple[str, str], float] = defaultdict(float)
    for record in training:
        value = float(record.trade.r_multiple)
        for key in record.features:
            totals[key] += 1
            sums[key] += value

    lifts: list[tuple[str, str, float]] = []
    for (dimension, label), count in sorted(totals.items()):
        if count < MIN_STATE_SUPPORT:
            continue
        shrunk_mean = (
            sums[(dimension, label)]
            + PRIOR_STRENGTH * baseline_mean
        ) / (count + PRIOR_STRENGTH)
        lifts.append(
            (
                dimension,
                label,
                round(shrunk_mean - baseline_mean, 10),
            )
        )

    provisional = ExpectedRModel(
        baseline_mean_r=baseline_mean,
        state_lifts=tuple(lifts),
        score_threshold=float("-inf"),
    )
    scores = sorted(provisional.score(record) for record in training)
    cutoff_index = min(
        len(scores) - 1,
        max(0, int(len(scores) * ABSTENTION_FRACTION) - 1),
    )
    threshold = scores[cutoff_index]
    model = ExpectedRModel(
        baseline_mean_r=baseline_mean,
        state_lifts=tuple(lifts),
        score_threshold=threshold,
    )

    retained = tuple(
        record
        for record in training
        if model.score(record) > threshold
    )
    rejected = tuple(
        record
        for record in training
        if model.score(record) <= threshold
    )
    return model, {
        "training_trades": len(training),
        "baseline_mean_r": round(baseline_mean, 10),
        "contributing_states": len(lifts),
        "score_threshold": round(threshold, 10),
        "training_retained_trades": len(retained),
        "training_rejected_trades": len(rejected),
        "training_retention": round(len(retained) / len(training), 8),
        "training_baseline": _metrics(training),
        "training_retained": _metrics(retained),
        "training_rejected": _metrics(rejected),
    }


def _apply_model(
    records: tuple[ViabilityRecord, ...],
    model: ExpectedRModel,
) -> tuple[ViabilityRecord, ...]:
    return tuple(
        record
        for record in records
        if model.score(record) > model.score_threshold
    )


def run_walk_forward() -> tuple[
    tuple[ViabilityRecord, ...],
    tuple[ViabilityRecord, ...],
    dict[str, Any],
]:
    records, diagnostics = _build_records()
    baseline_oos: list[ViabilityRecord] = []
    retained_oos: list[ViabilityRecord] = []
    folds: list[dict[str, Any]] = []

    for oos_year in range(START.year + TRAINING_YEARS, END.year):
        training_start = oos_year - TRAINING_YEARS
        training = _slice(
            records,
            _year_start(training_start),
            _year_start(oos_year),
        )
        oos = _slice(
            records,
            _year_start(oos_year),
            _year_start(oos_year + 1),
        )
        model, fit = _fit_model(training)
        retained = _apply_model(oos, model)

        baseline_oos.extend(oos)
        retained_oos.extend(retained)
        folds.append(
            {
                "training_start": _year_start(training_start).isoformat(),
                "training_end_exclusive": _year_start(oos_year).isoformat(),
                "oos_start": _year_start(oos_year).isoformat(),
                "oos_end_exclusive": _year_start(oos_year + 1).isoformat(),
                "fit": fit,
                "oos_baseline": _metrics(oos),
                "oos_retained": _metrics(retained),
                "oos_retention": (
                    None if not oos else round(len(retained) / len(oos), 8)
                ),
            }
        )

    baseline = tuple(
        sorted(baseline_oos, key=lambda record: record.trade.entry_opened_at)
    )
    retained = tuple(
        sorted(retained_oos, key=lambda record: record.trade.entry_opened_at)
    )
    years = len(folds)
    baseline_metrics = _metrics(baseline)
    retained_metrics = _metrics(retained)
    trades_per_year = 0.0 if years == 0 else len(retained) / years
    positive_year_fraction = (
        0.0
        if not folds
        else sum(
            float(fold["oos_retained"]["total_r"]) > 0
            for fold in folds
        )
        / len(folds)
    )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "AUDUSD",
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "training_years": TRAINING_YEARS,
        "objective": "PRE_ENTRY_EXPECTED_R",
        "model": "SHRUNK_CATEGORICAL_EXPECTED_R",
        "abstention_fraction_fixed_before_results": ABSTENTION_FRACTION,
        "minimum_state_support": MIN_STATE_SUPPORT,
        "prior_strength": PRIOR_STRENGTH,
        "threshold_source": "TRAINING_20TH_PERCENTILE_ONLY",
        "feature_family_reused_unchanged_from": "R2_BH",
        "no_future_leakage": True,
        "diagnostics": diagnostics,
        "folds": folds,
        "combined_oos_baseline": baseline_metrics,
        "combined_oos_retained": retained_metrics,
        "oos_retention": (
            None if not baseline else round(len(retained) / len(baseline), 8)
        ),
        "oos_trades_per_year": round(trades_per_year, 8),
        "positive_oos_year_fraction": round(positive_year_fraction, 8),
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
                float(retained_metrics["mean_r"])
                > float(baseline_metrics["mean_r"])
            ),
            "dead_on_arrival_rate_reduced": (
                retained_metrics["dead_on_arrival_rate"]
                < baseline_metrics["dead_on_arrival_rate"]
            ),
        },
        "automatic_promotion": False,
        "candidate_certified": False,
        "research_only": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return records, retained, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records, retained, report = run_walk_forward()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    with (args.output / "oos_retained.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in retained:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2BI_EXPECTED_R_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
