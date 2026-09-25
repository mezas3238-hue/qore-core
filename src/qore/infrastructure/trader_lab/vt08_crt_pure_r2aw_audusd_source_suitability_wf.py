"""R2-AW AUDUSD source-context suitability walk-forward.

R2-AU identified persistent loss concentration in selected Model #1 source and
confirmation state. R2-AW validates the *predeclared source-context family* via
causal walk-forward rather than applying any full-history winning bucket.

High-density core:
- ROLLING_H4;
- FIXED_1_5R;
- no EFF gate;
- one selected Model #1 hypothesis max per parent;
- structural source stop;
- C3 expiry;
- STOP_FIRST.

Candidate source dimensions are exactly those frozen in R2-AU:
generation, reference multiplicity, confirmation delay, source body fraction,
source range/C1 and source penetration.

Each OOS year:
- train on the immediately preceding 3 years;
- candidate source state must be negative in every training year;
- at least 12 removed trades in every training year;
- residual training density must retain >=70%;
- select most negative aggregate qualifying source state;
- if none qualify, exclude nothing.

Research only. No final certification or capital authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _summary,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2au_audusd_causal_loss_atlas import (
    ARM,
    END,
    START,
    AtlasRecord,
    run_atlas,
)

IDENTITY = "VT08_CRT_PURE_R2AW_AUDUSD_SOURCE_SUITABILITY_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2aw_audusd_source_suitability_wf.v1"
TRAINING_YEARS = 3
MIN_RETENTION = Decimal("0.70")
MIN_REMOVED_TRADES_PER_YEAR = 12
ADVANCEMENT_MIN_TRADES_PER_YEAR = Decimal("170")
ADVANCEMENT_MIN_PF = Decimal("1.05")
ADVANCEMENT_MIN_POSITIVE_YEAR_FRACTION = Decimal("0.60")

SOURCE_DIMENSIONS: tuple[str, ...] = (
    "source_generation",
    "source_reference_count",
    "confirmation_delay",
    "source_body_fraction",
    "source_range_to_c1",
    "source_penetration",
)


@dataclass(frozen=True, slots=True)
class SourceRule:
    dimension: str
    label: str

    @property
    def code(self) -> str:
        return f"{self.dimension}={self.label}"


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[AtlasRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[AtlasRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _trades(records: tuple[AtlasRecord, ...]) -> tuple[Model1LabTrade, ...]:
    return tuple(record.trade for record in records)


def _total_r(records: tuple[AtlasRecord, ...]) -> float:
    return sum(record.trade.r_multiple for record in records)


def _candidate_rules(
    records: tuple[AtlasRecord, ...],
) -> tuple[SourceRule, ...]:
    values: set[tuple[str, str]] = set()
    for record in records:
        for dimension, label in record.buckets:
            if dimension in SOURCE_DIMENSIONS:
                values.add((dimension, label))
    return tuple(
        SourceRule(dimension=dimension, label=label)
        for dimension, label in sorted(values)
    )


def _matches(record: AtlasRecord, rule: SourceRule) -> bool:
    return record.bucket(rule.dimension) == rule.label


def _select_rule(
    *,
    training: tuple[AtlasRecord, ...],
    training_start_year: int,
) -> tuple[SourceRule | None, dict[str, Any]]:
    if not training:
        return None, {"eligible_rules": 0, "reason": "EMPTY_TRAINING"}

    candidates: list[tuple[float, SourceRule, dict[str, Any]]] = []
    for rule in _candidate_rules(training):
        removed = tuple(record for record in training if _matches(record, rule))
        residual = tuple(record for record in training if not _matches(record, rule))
        if not removed:
            continue

        retention = Decimal(len(residual)) / Decimal(len(training))
        if retention < MIN_RETENTION:
            continue

        yearly_removed: dict[str, float] = {}
        stable_negative = True
        for offset in range(TRAINING_YEARS):
            left = _year_start(training_start_year + offset)
            right = _year_start(training_start_year + offset + 1)
            rows = _slice(removed, left, right)
            value = _total_r(rows)
            yearly_removed[f"{left.year}_{right.year}"] = round(value, 8)
            if len(rows) < MIN_REMOVED_TRADES_PER_YEAR or value >= 0:
                stable_negative = False
                break
        if not stable_negative:
            continue

        removed_total = _total_r(removed)
        if removed_total >= 0:
            continue

        candidates.append(
            (
                removed_total,
                rule,
                {
                    "removed_trades": len(removed),
                    "removed_total_r": round(removed_total, 8),
                    "residual_trades": len(residual),
                    "retention": round(float(retention), 8),
                    "yearly_removed_total_r": yearly_removed,
                },
            )
        )

    if not candidates:
        return None, {"eligible_rules": 0, "reason": "NO_STABLE_TOXIC_SOURCE_STATE"}

    candidates.sort(key=lambda item: (item[0], item[1].code))
    _, rule, evidence = candidates[0]
    return rule, {
        "eligible_rules": len(candidates),
        "selected_rule": rule.code,
        **evidence,
    }


def _positive_year_fraction(folds: list[dict[str, Any]], key: str) -> float:
    if not folds:
        return 0.0
    return sum(float(fold[key]["total_r"]) > 0 for fold in folds) / len(folds)


def run_walk_forward() -> tuple[
    tuple[AtlasRecord, ...],
    tuple[AtlasRecord, ...],
    dict[str, Any],
]:
    records, _ = run_atlas()
    baseline_oos: list[AtlasRecord] = []
    suitability_oos: list[AtlasRecord] = []
    folds: list[dict[str, Any]] = []

    first_oos_year = START.year + TRAINING_YEARS
    for oos_year in range(first_oos_year, END.year):
        training_start_year = oos_year - TRAINING_YEARS
        training = _slice(
            records,
            _year_start(training_start_year),
            _year_start(oos_year),
        )
        oos = _slice(records, _year_start(oos_year), _year_start(oos_year + 1))
        rule, selection = _select_rule(
            training=training,
            training_start_year=training_start_year,
        )
        retained = (
            oos
            if rule is None
            else tuple(record for record in oos if not _matches(record, rule))
        )

        baseline_oos.extend(oos)
        suitability_oos.extend(retained)
        folds.append(
            {
                "training_start": _year_start(training_start_year).isoformat(),
                "training_end_exclusive": _year_start(oos_year).isoformat(),
                "oos_start": _year_start(oos_year).isoformat(),
                "oos_end_exclusive": _year_start(oos_year + 1).isoformat(),
                "training_trades": len(training),
                "oos_baseline_trades": len(oos),
                "oos_retained_trades": len(retained),
                "selected_unsuitable_source_state": (
                    None if rule is None else rule.code
                ),
                "selection_evidence": selection,
                "oos_baseline": _summary(_trades(oos)),
                "oos_suitability": _summary(_trades(retained)),
            }
        )

    baseline = tuple(
        sorted(baseline_oos, key=lambda record: record.trade.entry_opened_at)
    )
    suitability = tuple(
        sorted(suitability_oos, key=lambda record: record.trade.entry_opened_at)
    )
    baseline_summary = _summary(_trades(baseline))
    suitability_summary = _summary(_trades(suitability))
    evaluated_years = len(folds)
    trades_per_year = (
        Decimal(len(suitability)) / Decimal(evaluated_years)
        if evaluated_years
        else Decimal("0")
    )
    positive_fraction = Decimal(
        str(_positive_year_fraction(folds, "oos_suitability"))
    )
    pf_raw = suitability_summary["profit_factor"]
    pf = Decimal("0") if pf_raw is None else Decimal(str(pf_raw))
    advancement_gate = {
        "density_pass": trades_per_year >= ADVANCEMENT_MIN_TRADES_PER_YEAR,
        "pf_pass": pf >= ADVANCEMENT_MIN_PF,
        "total_r_pass": float(suitability_summary["total_r"]) > 0,
        "temporal_breadth_pass": (
            positive_fraction >= ADVANCEMENT_MIN_POSITIVE_YEAR_FRACTION
        ),
        "drawdown_pass": (
            float(suitability_summary["max_drawdown_r"])
            <= float(baseline_summary["max_drawdown_r"])
        ),
    }
    advancement_gate["all_pass"] = all(advancement_gate.values())

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "AUDUSD",
        "period_start": START.isoformat(),
        "period_end_exclusive": END.isoformat(),
        "training_years": TRAINING_YEARS,
        "minimum_training_retention": str(MIN_RETENTION),
        "minimum_removed_trades_per_training_year": MIN_REMOVED_TRADES_PER_YEAR,
        "source_dimensions": list(SOURCE_DIMENSIONS),
        "source_family_frozen_in_r2au_before_r2aw_results": True,
        "high_density_core": {
            "timing_lattice": "ROLLING_H4",
            "target": ARM.value,
            "efficiency_filter": "OFF",
        },
        "selection_rule": (
            "ONE_SOURCE_STATE_NEGATIVE_IN_ALL_3_TRAINING_YEARS;"
            "MIN_12_REMOVED_TRADES_EACH_TRAINING_YEAR;"
            "RETAIN_GE_70_PERCENT;"
            "MOST_NEGATIVE_AGGREGATE_SOURCE_STATE"
        ),
        "folds": folds,
        "combined_oos_baseline": baseline_summary,
        "combined_oos_suitability": suitability_summary,
        "oos_retention": (
            None if not baseline else round(len(suitability) / len(baseline), 8)
        ),
        "oos_trades_per_year": round(float(trades_per_year), 8),
        "positive_oos_year_fraction": round(float(positive_fraction), 8),
        "advancement_gate": advancement_gate,
        "walk_forward_no_future_leakage": True,
        "automatic_promotion": False,
        "final_untouched_certification_claim": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return records, suitability, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records, suitability, report = run_walk_forward()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    with (args.output / "oos_suitability.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in suitability:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2AW_SOURCE_WF_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
