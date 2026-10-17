"""R2-BN USDJPY root-cause Expected-R walk-forward.

This lab starts from the exact R2-BL USDJPY high-density population and learns
USDJPY from USDJPY only. It does not transfer AUDUSD state outcomes.

Frozen small-memory heads:
1. REF_DELAY
2. REF_DELAY_DIRECTION
3. TIMING_REF_DELAY

Each head:
- trains on prior 4Y only;
- estimates expected R with empirical-Bayes shrinkage;
- freezes a 20% training-score abstention threshold;
- applies that frozen threshold to the next 1Y OOS fold;
- uses only pre-entry information already present in R2-BL trade identity.

No stop, target, lifecycle or signal-generation rule changes.
No automatic winner selection or promotion.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _summary,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bl_usdjpy_pf_root_cause import (
    END,
    MARKET,
    START,
    _delay_bucket,
    _reference_bucket,
    run_forensics,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2m_survivor_robustness import (
    _stress_summary,
)

IDENTITY = "VT08_CRT_PURE_R2BN_USDJPY_ROOT_CAUSE_EXPECTED_R_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2bn_usdjpy_root_cause_expected_r_wf.v1"
TRAINING_YEARS = 4
ABSTENTION_FRACTION = 0.20
MIN_CELL_SUPPORT = 30
PRIOR_STRENGTH = 100.0
MIN_DENSITY_PER_YEAR = 170.0
COST_DIAGNOSTICS_R: tuple[float, ...] = (0.02, 0.05)


class MemoryHead(StrEnum):
    REF_DELAY = "REF_DELAY"
    REF_DELAY_DIRECTION = "REF_DELAY_DIRECTION"
    TIMING_REF_DELAY = "TIMING_REF_DELAY"


@dataclass(frozen=True, slots=True)
class UsdJpyRecord:
    trade: Model1LabTrade
    features: tuple[tuple[str, str], ...]

    def feature(self, name: str) -> str:
        return dict(self.features)[name]


@dataclass(frozen=True, slots=True)
class CellModel:
    head: MemoryHead
    baseline_mean_r: float
    cell_expected_r: tuple[tuple[str, float], ...]
    threshold: float

    def score(self, record: UsdJpyRecord) -> float:
        lookup = dict(self.cell_expected_r)
        return lookup.get(_cell_key(record, self.head), self.baseline_mean_r)


def _record(trade: Model1LabTrade) -> UsdJpyRecord:
    return UsdJpyRecord(
        trade=trade,
        features=(
            ("confirmation_delay", _delay_bucket(trade)),
            ("direction", trade.parent_direction),
            ("source_reference_count", _reference_bucket(trade)),
            ("timing_triplet", trade.timing_triplet),
        ),
    )


def _cell_key(record: UsdJpyRecord, head: MemoryHead) -> str:
    features = dict(record.features)
    ref = features["source_reference_count"]
    delay = features["confirmation_delay"]
    if head is MemoryHead.REF_DELAY:
        return f"{ref}|{delay}"
    if head is MemoryHead.REF_DELAY_DIRECTION:
        return f"{ref}|{delay}|{features['direction']}"
    if head is MemoryHead.TIMING_REF_DELAY:
        return f"{features['timing_triplet']}|{ref}|{delay}"
    raise ValueError(head)


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[UsdJpyRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[UsdJpyRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _trades(
    records: tuple[UsdJpyRecord, ...],
) -> tuple[Model1LabTrade, ...]:
    return tuple(record.trade for record in records)


def _metrics(records: tuple[UsdJpyRecord, ...]) -> dict[str, Any]:
    trades = _trades(records)
    summary = _summary(trades)
    values = tuple(float(trade.r_multiple) for trade in trades)
    return {
        **summary,
        "mean_r": (
            None if not values else round(sum(values) / len(values), 8)
        ),
        "cost_stress": {
            f"COST_{cost:.2f}R": _stress_summary(trades, cost)
            for cost in COST_DIAGNOSTICS_R
        },
    }


def _fit(
    training: tuple[UsdJpyRecord, ...],
    head: MemoryHead,
) -> tuple[CellModel, dict[str, Any]]:
    if not training:
        return (
            CellModel(
                head=head,
                baseline_mean_r=0.0,
                cell_expected_r=(),
                threshold=float("-inf"),
            ),
            {"reason": "EMPTY_TRAINING"},
        )

    baseline = sum(
        float(record.trade.r_multiple) for record in training
    ) / len(training)
    totals: Counter[str] = Counter()
    sums: defaultdict[str, float] = defaultdict(float)
    for record in training:
        key = _cell_key(record, head)
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

    provisional = CellModel(
        head=head,
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
        head=head,
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
        "head": head.value,
        "baseline_mean_r": round(baseline, 10),
        "eligible_cells": len(expected),
        "threshold": round(threshold, 10),
        "training_retained": len(retained),
        "training_rejected": len(rejected),
        "training_retention": round(len(retained) / len(training), 8),
        "training_baseline_metrics": _metrics(training),
        "training_retained_metrics": _metrics(retained),
        "training_rejected_metrics": _metrics(rejected),
    }


def _apply(
    records: tuple[UsdJpyRecord, ...],
    model: CellModel,
) -> tuple[UsdJpyRecord, ...]:
    return tuple(
        record for record in records if model.score(record) > model.threshold
    )


def _run_head(
    records: tuple[UsdJpyRecord, ...],
    head: MemoryHead,
) -> dict[str, Any]:
    baseline_oos: list[UsdJpyRecord] = []
    retained_oos: list[UsdJpyRecord] = []
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
        model, fit = _fit(training, head)
        retained = _apply(oos, model)
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
    positive_fraction = (
        0.0
        if not folds
        else sum(
            float(fold["oos_retained"]["total_r"]) > 0 for fold in folds
        )
        / len(folds)
    )
    return {
        "head": head.value,
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
    tuple[UsdJpyRecord, ...],
    dict[str, Any],
]:
    path_records, bl_report = run_forensics()
    records = tuple(
        _record(record.trade)
        for record in path_records
    )
    heads = {
        head.value: _run_head(records, head)
        for head in MemoryHead
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "source_population_identity": bl_report["identity"],
        "source_population_trades": bl_report["overall"]["trades"],
        "source_population_rebuilt_from_r2bl": True,
        "training_years": TRAINING_YEARS,
        "abstention_fraction_fixed": ABSTENTION_FRACTION,
        "minimum_cell_support": MIN_CELL_SUPPORT,
        "prior_strength": PRIOR_STRENGTH,
        "heads_frozen_before_results": [head.value for head in MemoryHead],
        "feature_family": [
            "source_reference_count",
            "confirmation_delay",
            "timing_triplet",
            "direction",
        ],
        "target_variable": "EXPECTED_R",
        "generic_backoff": "TRAINING_BASELINE_MEAN_R",
        "usd_jpy_learns_usd_jpy_only": True,
        "audusd_outcomes_transferred": False,
        "heads": heads,
        "automatic_winner_ranking": False,
        "automatic_promotion": False,
        "candidate_certified": False,
        "research_only": True,
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
    print("CRT_R2BN_USDJPY_EXPECTED_R_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
