"""R2-BS AUDUSD passive-entry vs BJ selector overlap decomposition.

R2-BM established CONF_RANGE_MID as a causal entry-price lever.
R2-BJ established REF_DELAY_DIRECTION as the strongest small-memory pre-entry
selector, though its standalone margin remained too thin.

This lab does NOT combine the two rules. It replays both frozen mechanisms over
their common OOS window and decomposes whether the passive-entry fills belong to
BJ-retained or BJ-rejected signal populations.

Important:
- BJ models are fit exactly on prior 4Y and applied to next 1Y OOS as frozen.
- Passive PnL is never used to fit or retune BJ.
- BM CONF_RANGE_MID is unchanged.
- no combined candidate is created or promoted.

Research only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
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
    MemoryHead,
    _apply,
    _fit,
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

IDENTITY = "VT08_CRT_PURE_R2BS_AUDUSD_PASSIVE_BJ_OVERLAP_001"
SCHEMA = "qore.vt08.crt_pure.r2bs_audusd_passive_bj_overlap.v1"
BJ_HEAD = MemoryHead.REF_DELAY_DIRECTION
PASSIVE_ARM = EntryArm.CONF_RANGE_MID


def _bj_key(record: ViabilityRecord) -> tuple[str, str, str, str, str]:
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


def _passive_metrics(rows: tuple[PassiveTrade, ...]) -> dict[str, Any]:
    return {
        "economics": _summary(rows),
        "cost_stress": {
            f"COST_{cost:.2f}R": _stress(rows, cost)
            for cost in COST_STRESS_R
        },
    }


def _bj_oos_classes(
    records: tuple[ViabilityRecord, ...],
) -> tuple[
    set[tuple[str, str, str, str, str]],
    set[tuple[str, str, str, str, str]],
    list[dict[str, Any]],
]:
    retained_keys: set[tuple[str, str, str, str, str]] = set()
    rejected_keys: set[tuple[str, str, str, str, str]] = set()
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
        model, fit = _fit(training, BJ_HEAD)
        retained = _apply(oos, model)
        retained_fold = {_bj_key(record) for record in retained}
        baseline_fold = {_bj_key(record) for record in oos}
        rejected_fold = baseline_fold - retained_fold

        retained_keys.update(retained_fold)
        rejected_keys.update(rejected_fold)
        folds.append(
            {
                "oos_year": f"{oos_year}_{oos_year + 1}",
                "baseline_signals": len(baseline_fold),
                "retained_signals": len(retained_fold),
                "rejected_signals": len(rejected_fold),
                "fit_threshold": fit.get("threshold"),
                "eligible_cells": fit.get("eligible_cells"),
            }
        )

    if retained_keys & rejected_keys:
        raise RuntimeError("BJ OOS class keys overlap")
    return retained_keys, rejected_keys, folds


def run_decomposition() -> tuple[
    tuple[PassiveTrade, ...],
    dict[str, Any],
]:
    records, bj_diagnostics = _build_records()
    retained_keys, rejected_keys, folds = _bj_oos_classes(records)
    baseline_keys = retained_keys | rejected_keys

    passive_arms, bm_report = run_replay()
    passive_all = passive_arms[PASSIVE_ARM]
    passive_common = tuple(
        row for row in passive_all if _passive_key(row) in baseline_keys
    )
    passive_retained = tuple(
        row for row in passive_common if _passive_key(row) in retained_keys
    )
    passive_rejected = tuple(
        row for row in passive_common if _passive_key(row) in rejected_keys
    )

    passive_keys = {_passive_key(row) for row in passive_common}
    retained_fill_keys = passive_keys & retained_keys
    rejected_fill_keys = passive_keys & rejected_keys

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "AUDUSD",
        "common_oos_start": _year_start(
            START.year + TRAINING_YEARS
        ).isoformat(),
        "common_oos_end_exclusive": END.isoformat(),
        "bj_head": BJ_HEAD.value,
        "passive_arm": PASSIVE_ARM.value,
        "bj_training_years": TRAINING_YEARS,
        "bj_models_reconstructed_exactly_from_frozen_contract": True,
        "passive_outcomes_used_for_bj_fit": False,
        "bj_diagnostics": bj_diagnostics,
        "bm_identity": bm_report["identity"],
        "folds": folds,
        "signal_overlap": {
            "bj_oos_baseline_signals": len(baseline_keys),
            "bj_retained_signals": len(retained_keys),
            "bj_rejected_signals": len(rejected_keys),
            "passive_fills_in_common_oos": len(passive_common),
            "passive_fills_bj_retained": len(passive_retained),
            "passive_fills_bj_rejected": len(passive_rejected),
            "bj_retained_passive_fill_rate": (
                None
                if not retained_keys
                else round(len(retained_fill_keys) / len(retained_keys), 8)
            ),
            "bj_rejected_passive_fill_rate": (
                None
                if not rejected_keys
                else round(len(rejected_fill_keys) / len(rejected_keys), 8)
            ),
        },
        "passive_economics_by_bj_class": {
            "ALL_COMMON_OOS_PASSIVE_FILLS": _passive_metrics(passive_common),
            "BJ_RETAINED_PASSIVE_FILLS": _passive_metrics(passive_retained),
            "BJ_REJECTED_PASSIVE_FILLS": _passive_metrics(passive_rejected),
        },
        "combined_execution_tested": False,
        "automatic_independence_claim": False,
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return passive_common, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    passive, report = run_decomposition()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "passive_common_oos.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in passive:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    print("CRT_R2BS_PASSIVE_BJ_OVERLAP_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
