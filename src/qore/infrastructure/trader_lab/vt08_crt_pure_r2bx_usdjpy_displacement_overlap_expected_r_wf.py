"""R2-BX USDJPY displacement-overlap Expected-R walk-forward.

Frozen before R2-BV outcome inspection.

R2-BC identified the strongest consumed-window toxic confirmation state as:
CONFDISP_LT_0_50 | CONFOVERLAP_0_50_TO_0_75.

R2-BX tests that prior state only as a binary causal flag inside a small
USDJPY-only REF+DELAY memory:
- TOXIC_DISP_OVERLAP
- OTHER_CONFIRMATION_GEOMETRY

No AUDUSD state is transferred. No new threshold fraction is searched.
The abstention semantics intentionally match R2-BU so the incremental value of
this exact geometry flag can be measured independently of the tie-safe change
tested separately in R2-BV.

Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _summary,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bc_usdjpy_confirmation_geometry_atlas import (
    END,
    START,
    ConfirmationRecord,
    run_atlas,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bl_usdjpy_pf_root_cause import (
    _delay_bucket,
    _reference_bucket,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bn_usdjpy_root_cause_expected_r_wf import (
    ABSTENTION_FRACTION,
    MIN_CELL_SUPPORT,
    PRIOR_STRENGTH,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2m_survivor_robustness import (
    _stress_summary,
)

IDENTITY = "VT08_CRT_PURE_R2BX_USDJPY_DISPLACEMENT_OVERLAP_EXPECTED_R_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2bx_usdjpy_displacement_overlap_expected_r_wf.v1"
TRAINING_YEARS = 4
MIN_DENSITY_PER_YEAR = 170.0
COST_DIAGNOSTICS_R: tuple[float, ...] = (0.02, 0.05)
TOXIC_STATE = "CONFDISP_LT_0_50|CONFOVERLAP_0_50_TO_0_75"


@dataclass(frozen=True, slots=True)
class GeometryRecord:
    trade: Model1LabTrade
    reference: str
    delay: str
    toxic_flag: str


@dataclass(frozen=True, slots=True)
class CellModel:
    baseline_mean_r: float
    cell_expected_r: tuple[tuple[str, float], ...]
    threshold: float

    def score(self, record: GeometryRecord) -> float:
        return dict(self.cell_expected_r).get(
            _cell_key(record),
            self.baseline_mean_r,
        )


def _record(record: ConfirmationRecord) -> GeometryRecord:
    trade = record.trade
    buckets = dict(record.buckets)
    state = buckets["displacement_x_overlap"]
    return GeometryRecord(
        trade=trade,
        reference=_reference_bucket(trade),
        delay=_delay_bucket(trade),
        toxic_flag=(
            "TOXIC_DISP_OVERLAP"
            if state == TOXIC_STATE
            else "OTHER_CONFIRMATION_GEOMETRY"
        ),
    )


def _cell_key(record: GeometryRecord) -> str:
    return f"{record.reference}|{record.delay}|{record.toxic_flag}"


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[GeometryRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[GeometryRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _trades(
    records: tuple[GeometryRecord, ...],
) -> tuple[Model1LabTrade, ...]:
    return tuple(record.trade for record in records)


def _metrics(records: tuple[GeometryRecord, ...]) -> dict[str, Any]:
    trades = _trades(records)
    values = tuple(float(trade.r_multiple) for trade in trades)
    summary = _summary(trades)
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
    training: tuple[GeometryRecord, ...],
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

    baseline = sum(
        float(record.trade.r_multiple) for record in training
    ) / len(training)
    totals: Counter[str] = Counter()
    sums: defaultdict[str, float] = defaultdict(float)
    for record in training:
        key = _cell_key(record)
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


def _run(
    records: tuple[GeometryRecord, ...],
) -> dict[str, Any]:
    baseline_oos: list[GeometryRecord] = []
    retained_oos: list[GeometryRecord] = []
    folds: list[dict[str, Any]] = []

    for oos_year in range(START.year + TRAINING_YEARS, END.year):
        training = _slice(
            records,
            _year_start(oos_year - TRAINING_YEARS),
            _year_start(oos_year),
        )
        oos = _slice(
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
    tuple[GeometryRecord, ...],
    dict[str, Any],
]:
    confirmation_records, source_report = run_atlas()
    records = tuple(_record(record) for record in confirmation_records)
    result = _run(records)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "USDJPY",
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "source_population_identity": source_report["identity"],
        "source_population_trades": len(records),
        "training_years": TRAINING_YEARS,
        "abstention_fraction_fixed": ABSTENTION_FRACTION,
        "minimum_cell_support": MIN_CELL_SUPPORT,
        "prior_strength": PRIOR_STRENGTH,
        "new_feature": "displacement_x_overlap_toxic_flag",
        "toxic_state_frozen_from_r2bc": TOXIC_STATE,
        "frozen_before_r2bv_outcome_inspection": True,
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
        "CRT_R2BX_USDJPY_DISPLACEMENT_OVERLAP_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
