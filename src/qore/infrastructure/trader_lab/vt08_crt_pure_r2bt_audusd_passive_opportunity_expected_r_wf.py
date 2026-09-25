"""R2-BT AUDUSD passive-opportunity Expected-R walk-forward.

R2-BS showed that the frozen BJ REF_DELAY_DIRECTION selector separates some
passive losers, but BJ was trained on the original next-open trade outcome rather
than the passive execution outcome.

R2-BT changes only the learning target:
- each selected CRT opportunity is represented before entry;
- if CONF_RANGE_MID fills causally, target = corrected passive trade R;
- if the passive order does not fill, target = 0R;
- no passive outcome is used outside the prior 4Y training window;
- the next 1Y OOS fold is scored only from frozen prior-year cell estimates.

The same small memory heads are reused:
1. REF_DELAY
2. REF_DELAY_DIRECTION
3. TIMING_REF_DELAY

This is deliberately not a new high-dimensional model. It tests whether label
alignment, rather than missing feature dimensionality, is the source of the thin
edge.

Research only. No automatic promotion.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bh_audusd_entry_viability_wf import (
    END,
    START,
    TRAINING_YEARS,
    ViabilityRecord,
    _build_records,
    _slice,
    _year_start,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bj_audusd_root_cause_expected_r_family import (
    ABSTENTION_FRACTION,
    MIN_CELL_SUPPORT,
    PRIOR_STRENGTH,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bk_audusd_passive_entry_capacity import (
    EntryArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bm_audusd_passive_entry_economics import (
    COST_STRESS_R,
    PassiveTrade,
    _stress,
    _summary,
    run_replay,
)

IDENTITY = "VT08_CRT_PURE_R2BT_AUDUSD_PASSIVE_OPPORTUNITY_EXPECTED_R_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2bt_audusd_passive_opportunity_expected_r_wf.v1"
PASSIVE_ARM = EntryArm.CONF_RANGE_MID
MIN_DENSITY_PER_YEAR = 170.0


class MemoryHead(StrEnum):
    REF_DELAY = "REF_DELAY"
    REF_DELAY_DIRECTION = "REF_DELAY_DIRECTION"
    TIMING_REF_DELAY = "TIMING_REF_DELAY"


@dataclass(frozen=True, slots=True)
class OpportunityRecord:
    base: ViabilityRecord
    passive_trade: PassiveTrade | None
    opportunity_r: float

    @property
    def filled(self) -> bool:
        return self.passive_trade is not None

    def feature(self, name: str) -> str:
        return self.base.feature(name)


@dataclass(frozen=True, slots=True)
class CellModel:
    head: MemoryHead
    baseline_mean_r: float
    cell_expected_r: tuple[tuple[str, float], ...]
    threshold: float

    def score(self, record: OpportunityRecord) -> float:
        return dict(self.cell_expected_r).get(
            _cell_key(record, self.head),
            self.baseline_mean_r,
        )


def _coarse_ref(value: str) -> str:
    return "REF1" if value == "REF1" else "REF2_PLUS"


def _coarse_delay(value: str) -> str:
    if value in {"D1", "D2"}:
        return value
    return "D3_PLUS"


def _cell_key(record: OpportunityRecord, head: MemoryHead) -> str:
    ref = _coarse_ref(record.feature("source_reference_count"))
    delay = _coarse_delay(record.feature("confirmation_delay"))
    if head is MemoryHead.REF_DELAY:
        return f"{ref}|{delay}"
    if head is MemoryHead.REF_DELAY_DIRECTION:
        return f"{ref}|{delay}|{record.feature('direction')}"
    if head is MemoryHead.TIMING_REF_DELAY:
        return (
            f"{record.feature('timing_triplet')}|{ref}|{delay}"
        )
    raise ValueError(head)


def _base_key(record: ViabilityRecord) -> tuple[str, str, str, str, str]:
    trade = record.trade
    return (
        trade.source_opened_at,
        trade.confirmation_opened_at,
        trade.entry_opened_at,
        trade.parent_direction,
        trade.timing_triplet,
    )


def _passive_key(trade: PassiveTrade) -> tuple[str, str, str, str, str]:
    return (
        trade.source_opened_at,
        trade.confirmation_opened_at,
        trade.decision_opened_at,
        trade.parent_direction,
        trade.timing_triplet,
    )


def _opportunity_slice(
    records: tuple[OpportunityRecord, ...],
    start: Any,
    end: Any,
) -> tuple[OpportunityRecord, ...]:
    base_rows = _slice(
        tuple(record.base for record in records),
        start,
        end,
    )
    keys = {_base_key(record) for record in base_rows}
    return tuple(
        record for record in records if _base_key(record.base) in keys
    )


def _passive_rows(
    records: tuple[OpportunityRecord, ...],
) -> tuple[PassiveTrade, ...]:
    return tuple(
        record.passive_trade
        for record in records
        if record.passive_trade is not None
    )


def _metrics(
    records: tuple[OpportunityRecord, ...],
) -> dict[str, Any]:
    passive = _passive_rows(records)
    opportunity_total_r = sum(record.opportunity_r for record in records)
    filled = len(passive)
    return {
        "opportunities": len(records),
        "fills": filled,
        "fill_rate": (
            0.0 if not records else round(filled / len(records), 8)
        ),
        "opportunity_total_r": round(opportunity_total_r, 8),
        "opportunity_mean_r": (
            None
            if not records
            else round(opportunity_total_r / len(records), 8)
        ),
        "passive_economics": _summary(passive),
        "cost_stress": {
            f"COST_{cost:.2f}R": _stress(passive, cost)
            for cost in COST_STRESS_R
        },
    }


def _fit(
    training: tuple[OpportunityRecord, ...],
    head: MemoryHead,
) -> tuple[CellModel, dict[str, Any]]:
    if not training:
        model = CellModel(
            head=head,
            baseline_mean_r=0.0,
            cell_expected_r=(),
            threshold=float("-inf"),
        )
        return model, {"reason": "EMPTY_TRAINING"}

    baseline = sum(record.opportunity_r for record in training) / len(training)
    totals: Counter[str] = Counter()
    sums: defaultdict[str, float] = defaultdict(float)
    for record in training:
        key = _cell_key(record, head)
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
    records: tuple[OpportunityRecord, ...],
    model: CellModel,
) -> tuple[OpportunityRecord, ...]:
    return tuple(
        record for record in records
        if model.score(record) > model.threshold
    )


def _run_head(
    records: tuple[OpportunityRecord, ...],
    head: MemoryHead,
) -> dict[str, Any]:
    baseline_oos: list[OpportunityRecord] = []
    retained_oos: list[OpportunityRecord] = []
    folds: list[dict[str, Any]] = []

    for oos_year in range(START.year + TRAINING_YEARS, END.year):
        training_start = oos_year - TRAINING_YEARS
        training = _opportunity_slice(
            records,
            _year_start(training_start),
            _year_start(oos_year),
        )
        oos = _opportunity_slice(
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
        sorted(
            baseline_oos,
            key=lambda record: record.base.trade.entry_opened_at,
        )
    )
    retained = tuple(
        sorted(
            retained_oos,
            key=lambda record: record.base.trade.entry_opened_at,
        )
    )
    years = len(folds)
    baseline_metrics = _metrics(baseline)
    retained_metrics = _metrics(retained)
    fills_per_year = (
        0.0
        if years == 0
        else int(retained_metrics["fills"]) / years
    )
    positive_year_fraction = (
        0.0
        if not folds
        else sum(
            float(fold["oos_retained"]["opportunity_total_r"]) > 0
            for fold in folds
        )
        / len(folds)
    )
    return {
        "head": head.value,
        "folds": folds,
        "combined_oos_baseline": baseline_metrics,
        "combined_oos_retained": retained_metrics,
        "oos_signal_retention": (
            None
            if not baseline
            else round(len(retained) / len(baseline), 8)
        ),
        "oos_fills_per_year": round(fills_per_year, 8),
        "positive_oos_year_fraction": round(
            positive_year_fraction,
            8,
        ),
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
    tuple[OpportunityRecord, ...],
    dict[str, Any],
]:
    base_records, base_diagnostics = _build_records()
    arms, bm_report = run_replay()
    passive = arms[PASSIVE_ARM]

    passive_by_key: dict[
        tuple[str, str, str, str, str],
        PassiveTrade,
    ] = {}
    for trade in passive:
        key = _passive_key(trade)
        if key in passive_by_key:
            raise RuntimeError(f"duplicate passive key: {key}")
        passive_by_key[key] = trade

    base_keys = {_base_key(record) for record in base_records}
    orphan_passive = set(passive_by_key) - base_keys
    # A tiny number of passive-valid rows can lack a homologous BH next-open
    # record because the original next-open geometry and passive geometry are
    # not identical. Do not fabricate features or leak the passive outcome back
    # into feature construction. Keep the causal common population and report
    # the mismatch explicitly.
    joined_passive_by_key = {
        key: trade
        for key, trade in passive_by_key.items()
        if key in base_keys
    }

    opportunities = tuple(
        OpportunityRecord(
            base=record,
            passive_trade=joined_passive_by_key.get(_base_key(record)),
            opportunity_r=(
                0.0
                if _base_key(record) not in joined_passive_by_key
                else joined_passive_by_key[_base_key(record)].r_multiple
            ),
        )
        for record in base_records
    )

    heads = {
        head.value: _run_head(opportunities, head)
        for head in MemoryHead
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "AUDUSD",
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "training_years": TRAINING_YEARS,
        "passive_arm": PASSIVE_ARM.value,
        "passive_source_identity": bm_report["identity"],
        "passive_semantics": {
            "same_m15_stop_target_ambiguity": (
                bm_report["same_m15_stop_target_ambiguity"]
            ),
            "management": bm_report["management"],
            "target": bm_report["target"],
            "expiry": bm_report["expiry"],
        },
        "target_variable": (
            "PASSIVE_OPPORTUNITY_R_FILL_R_ELSE_ZERO"
        ),
        "abstention_fraction_fixed": ABSTENTION_FRACTION,
        "minimum_cell_support": MIN_CELL_SUPPORT,
        "prior_strength": PRIOR_STRENGTH,
        "heads_frozen_before_results": [
            head.value for head in MemoryHead
        ],
        "base_diagnostics": base_diagnostics,
        "opportunity_count": len(opportunities),
        "passive_fill_count_full_bm": len(passive),
        "passive_fill_count_joined": len(joined_passive_by_key),
        "passive_fill_orphan_count": len(orphan_passive),
        "passive_fill_orphan_fraction": (
            0.0
            if not passive
            else round(len(orphan_passive) / len(passive), 8)
        ),
        "orphan_policy": "EXCLUDE_NO_FEATURE_FABRICATION",
        "heads": heads,
        "new_feature_dimensions_added": False,
        "automatic_winner_ranking": False,
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return opportunities, report


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
        "CRT_R2BT_PASSIVE_OPPORTUNITY_EXPECTED_R_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
