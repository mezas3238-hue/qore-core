"""R2-BU USDJPY root-cause + confirmation-overlap Expected-R WFO.

R2-BN showed that small REF/DELAY memories alone do not repair USDJPY.
R2-BD showed that standalone adaptive confirmation-state exclusion also fails.

R2-BU tests one still-unresolved interaction while preserving low dimensionality:
does confirmation/source range overlap add causal information to the root-cause
memory?

The only new feature is a predeclared coarse binary overlap state:
- CONF_OVERLAP_LT_050
- CONF_OVERLAP_GE_050

Frozen heads:
1. REF_DELAY_DIRECTION_CONTROL
2. REF_DELAY_OVERLAP
3. REF_DELAY_DIRECTION_OVERLAP

All state outcomes are learned from USDJPY only with prior 4Y -> next 1Y OOS,
20% fixed training-score abstention and empirical-Bayes shrinkage.

No AUDUSD state, winner, threshold or economic outcome is transferred.
Research only.
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

IDENTITY = "VT08_CRT_PURE_R2BU_USDJPY_OVERLAP_EXPECTED_R_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2bu_usdjpy_overlap_expected_r_wf.v1"
TRAINING_YEARS = 4
MIN_DENSITY_PER_YEAR = 170.0
COST_DIAGNOSTICS_R: tuple[float, ...] = (0.02, 0.05)


class MemoryHead(StrEnum):
    REF_DELAY_DIRECTION_CONTROL = "REF_DELAY_DIRECTION_CONTROL"
    REF_DELAY_OVERLAP = "REF_DELAY_OVERLAP"
    REF_DELAY_DIRECTION_OVERLAP = "REF_DELAY_DIRECTION_OVERLAP"


@dataclass(frozen=True, slots=True)
class OverlapRecord:
    trade: Model1LabTrade
    reference: str
    delay: str
    direction: str
    timing: str
    overlap: str


@dataclass(frozen=True, slots=True)
class CellModel:
    head: MemoryHead
    baseline_mean_r: float
    cell_expected_r: tuple[tuple[str, float], ...]
    threshold: float

    def score(self, record: OverlapRecord) -> float:
        return dict(self.cell_expected_r).get(
            _cell_key(record, self.head),
            self.baseline_mean_r,
        )


def _coarse_overlap(record: ConfirmationRecord) -> str:
    buckets = dict(record.buckets)
    value = buckets["confirmation_source_overlap"]
    if value in {
        "CONFOVERLAP_LT_0_25",
        "CONFOVERLAP_0_25_TO_0_50",
    }:
        return "CONF_OVERLAP_LT_050"
    if value in {
        "CONFOVERLAP_0_50_TO_0_75",
        "CONFOVERLAP_GE_0_75",
    }:
        return "CONF_OVERLAP_GE_050"
    raise RuntimeError(f"unexpected confirmation overlap bucket: {value}")


def _record(record: ConfirmationRecord) -> OverlapRecord:
    trade = record.trade
    return OverlapRecord(
        trade=trade,
        reference=_reference_bucket(trade),
        delay=_delay_bucket(trade),
        direction=trade.parent_direction,
        timing=trade.timing_triplet,
        overlap=_coarse_overlap(record),
    )


def _cell_key(record: OverlapRecord, head: MemoryHead) -> str:
    if head is MemoryHead.REF_DELAY_DIRECTION_CONTROL:
        return f"{record.reference}|{record.delay}|{record.direction}"
    if head is MemoryHead.REF_DELAY_OVERLAP:
        return f"{record.reference}|{record.delay}|{record.overlap}"
    if head is MemoryHead.REF_DELAY_DIRECTION_OVERLAP:
        return (
            f"{record.reference}|{record.delay}|"
            f"{record.direction}|{record.overlap}"
        )
    raise ValueError(head)


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[OverlapRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[OverlapRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _trades(
    records: tuple[OverlapRecord, ...],
) -> tuple[Model1LabTrade, ...]:
    return tuple(record.trade for record in records)


def _metrics(records: tuple[OverlapRecord, ...]) -> dict[str, Any]:
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
    training: tuple[OverlapRecord, ...],
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
    records: tuple[OverlapRecord, ...],
    model: CellModel,
) -> tuple[OverlapRecord, ...]:
    return tuple(
        record for record in records
        if model.score(record) > model.threshold
    )


def _run_head(
    records: tuple[OverlapRecord, ...],
    head: MemoryHead,
) -> dict[str, Any]:
    baseline_oos: list[OverlapRecord] = []
    retained_oos: list[OverlapRecord] = []
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
        model, fit = _fit(training, head)
        retained = _apply(oos, model)
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
        sorted(baseline_oos, key=lambda record: record.trade.entry_opened_at)
    )
    retained = tuple(
        sorted(retained_oos, key=lambda record: record.trade.entry_opened_at)
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
    tuple[OverlapRecord, ...],
    dict[str, Any],
]:
    confirmation_records, bc_report = run_atlas()
    records = tuple(_record(record) for record in confirmation_records)
    heads = {
        head.value: _run_head(records, head)
        for head in MemoryHead
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "USDJPY",
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "training_years": TRAINING_YEARS,
        "source_population_identity": bc_report["identity"],
        "source_population_trades": len(records),
        "target_variable": "EXPECTED_R",
        "abstention_fraction_fixed": ABSTENTION_FRACTION,
        "minimum_cell_support": MIN_CELL_SUPPORT,
        "prior_strength": PRIOR_STRENGTH,
        "new_dimension": "confirmation_source_overlap",
        "new_dimension_buckets": [
            "CONF_OVERLAP_LT_050",
            "CONF_OVERLAP_GE_050",
        ],
        "heads_frozen_before_results": [
            head.value for head in MemoryHead
        ],
        "usd_jpy_learns_usd_jpy_only": True,
        "audusd_state_transfer_forbidden": True,
        "heads": heads,
        "automatic_winner_ranking": False,
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
        "CRT_R2BU_USDJPY_OVERLAP_EXPECTED_R_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
