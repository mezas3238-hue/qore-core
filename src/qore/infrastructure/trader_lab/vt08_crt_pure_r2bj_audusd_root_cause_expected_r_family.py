"""R2-BJ AUDUSD root-cause hierarchical expected-R family.

Purpose
-------
R2-BH showed that dead-on-arrival classification reduces bad-stop incidence but
does not improve economics. R2-BI tests a broad expected-R score across all
pre-entry features.

R2-BJ isolates the root-cause information into three small, interpretable market
memory heads, with no automatic winner selection:

1. REF_DELAY
2. REF_DELAY_DIRECTION
3. TIMING_REF_DELAY

All heads:
- train on prior 4Y;
- use fixed 20% training-score abstention threshold;
- estimate expected R with strong empirical-Bayes shrinkage;
- apply the frozen threshold to the next 1Y OOS;
- use only information known before entry.

No signal, stop, target, BE protection or lifecycle rule changes.
Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import StrEnum
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

IDENTITY = "VT08_CRT_PURE_R2BJ_AUDUSD_ROOT_CAUSE_EXPECTED_R_FAMILY_001"
SCHEMA = "qore.vt08.crt_pure.r2bj_audusd_root_cause_expected_r_family.v1"
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
class CellModel:
    head: MemoryHead
    baseline_mean_r: float
    cell_expected_r: tuple[tuple[str, float], ...]
    threshold: float

    def score(self, record: ViabilityRecord) -> float:
        lookup = dict(self.cell_expected_r)
        return lookup.get(_cell_key(record, self.head), self.baseline_mean_r)


def _feature_map(record: ViabilityRecord) -> dict[str, str]:
    return dict(record.features)


def _coarse_ref(value: str) -> str:
    return "REF1" if value == "REF1" else "REF2_PLUS"


def _coarse_delay(value: str) -> str:
    if value in {"D1", "D2"}:
        return value
    return "D3_PLUS"


def _cell_key(record: ViabilityRecord, head: MemoryHead) -> str:
    features = _feature_map(record)
    ref = _coarse_ref(features["source_reference_count"])
    delay = _coarse_delay(features["confirmation_delay"])
    if head is MemoryHead.REF_DELAY:
        return f"{ref}|{delay}"
    if head is MemoryHead.REF_DELAY_DIRECTION:
        return f"{ref}|{delay}|{features['direction']}"
    if head is MemoryHead.TIMING_REF_DELAY:
        return f"{features['timing_triplet']}|{ref}|{delay}"
    raise ValueError(head)


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


def _fit(
    training: tuple[ViabilityRecord, ...],
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
    records: tuple[ViabilityRecord, ...],
    model: CellModel,
) -> tuple[ViabilityRecord, ...]:
    return tuple(
        record for record in records if model.score(record) > model.threshold
    )


def _run_head(
    records: tuple[ViabilityRecord, ...],
    head: MemoryHead,
) -> dict[str, Any]:
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
        model, fit = _fit(training, head)
        retained = _apply(oos, model)
        baseline_oos.extend(oos)
        retained_oos.extend(retained)
        folds.append(
            {
                "training_start": _year_start(training_start).isoformat(),
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
                float(retained_metrics["mean_r"])
                > float(baseline_metrics["mean_r"])
            ),
        },
    }


def run_family() -> tuple[tuple[ViabilityRecord, ...], dict[str, Any]]:
    records, diagnostics = _build_records()
    heads = {
        head.value: _run_head(records, head)
        for head in MemoryHead
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "AUDUSD",
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "training_years": TRAINING_YEARS,
        "abstention_fraction_fixed": ABSTENTION_FRACTION,
        "minimum_cell_support": MIN_CELL_SUPPORT,
        "prior_strength": PRIOR_STRENGTH,
        "heads_frozen_before_results": [head.value for head in MemoryHead],
        "generic_backoff": "TRAINING_BASELINE_MEAN_R",
        "diagnostics": diagnostics,
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

    records, report = run_family()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2BJ_ROOT_CAUSE_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
