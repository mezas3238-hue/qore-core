"""VT08 R2-CF: strictly prior-only nested WAIT journal (read-only research).

The freeze was committed before this implementation or economic run:
docs/research/VT08-CRT-PURE-R2CF-STRICT-NESTED-WAIT-JOURNAL-FREEZE-001.md
No sizing, volume, leverage, risk allocation, merge or deployment.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bc_usdjpy_confirmation_geometry_atlas as r2bc,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bh_audusd_entry_viability_wf as r2bh,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2by_audusd_cognitive_experience_wf as r2by,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bz_usdjpy_cognitive_experience_wf as r2bz,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cc_audusd_cognitive_wait_resolution_wf as r2cc,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cd_usdjpy_cognitive_wait_resolution_wf as r2cd,
)
from qore.infrastructure.trader_lab import vt08_crt_pure_r2ce_wait_cohort_alignment as r2ce
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction,
)

IDENTITY = "VT08_CRT_PURE_R2CF_STRICT_NESTED_WAIT_JOURNAL_001"
SCHEMA = "qore.vt08.crt_pure.r2cf_strict_nested_wait_journal.v1"
INNER_YEARS = 4
ARMS = ("CONTROL_ALL", "STRICT_NESTED_WAIT_4Y")
MIN_DENSITY_PER_YEAR = 170.0


def _inner_fit_span(
    historical_year: int,
    *,
    earliest_year: int,
    year_start: Callable[[int], datetime],
) -> tuple[datetime, datetime] | None:
    """Only prior four COMPLETED years; no in-sample historical initial action."""
    if historical_year - INNER_YEARS < earliest_year:
        return None
    start, end = year_start(historical_year - INNER_YEARS), year_start(historical_year)
    if start >= end:
        raise ValueError("Invalid inner training chronology")
    return start, end


def _nested_membership(
    records: tuple[Any, ...],
    *,
    start: datetime,
    end: datetime,
    year_start: Callable[[int], datetime],
    slice_records: Callable[[tuple[Any, ...], datetime, datetime], tuple[Any, ...]],
    initial_fit: Callable[[tuple[Any, ...]], tuple[Any, dict[str, Any]]],
    initial_decision: Callable[[Any, Any], Any],
    record_key: Callable[[Any], Any],
) -> tuple[dict[Any, CrtPureReasoningAction], dict[int, dict[str, Any]]]:
    """Journal actions computed from each row's PRECEDING four years only."""
    historical_actions: dict[Any, CrtPureReasoningAction] = {}
    year_provenance: dict[int, dict[str, Any]] = {}
    for historical_year in range(start.year, end.year):
        span = _inner_fit_span(
            historical_year,
            earliest_year=start.year,
            year_start=year_start,
        )
        year_rows = cast(Any, slice_records)(
            records, year_start(historical_year), year_start(historical_year + 1)
        )
        if span is None:
            year_provenance[historical_year] = {
                "status": "INSUFFICIENT_FOUR_YEAR_WARMUP",
                "excluded_rows": len(year_rows),
            }
            continue

        begin, finish = span
        if finish > year_start(historical_year):
            raise ValueError("Inner training crosses observed-year boundary")
        prior = cast(Any, slice_records)(records, begin, finish)
        model, fit_metadata = cast(Any, initial_fit)(prior)
        action_counts: Counter[str] = Counter()
        for row in year_rows:
            key = record_key(row)
            if key in historical_actions:
                raise ValueError("Duplicate nested journal hypothesis key")
            action = r2ce._initial_action(initial_decision, model, row)
            action_counts[action.value] += 1
            historical_actions[key] = action
        year_provenance[historical_year] = {
            "status": "STRICT_PRIOR_ONLY",
            "training_start": begin.isoformat(),
            "training_end_exclusive": finish.isoformat(),
            "observed_start": year_start(historical_year).isoformat(),
            "training_records": len(prior),
            "observed_records": len(year_rows),
            "initial_fit": fit_metadata,
            "action_counts": dict(action_counts),
        }

    if any(
        entry.get("status") == "STRICT_PRIOR_ONLY"
        and entry["training_end_exclusive"] > entry["observed_start"]
        for entry in year_provenance.values()
    ):
        raise ValueError("Inner label chronological integrity failure")
    return historical_actions, year_provenance


def _nested_cohort(
    training: tuple[Any, ...],
    *,
    actions: dict[Any, CrtPureReasoningAction],
    delayed_by_key: dict[Any, Any],
    record_key: Callable[[Any], Any],
) -> tuple[tuple[Any, ...], dict[str, int]]:
    included: list[Any] = []
    counts: Counter[str] = Counter()
    for row in training:
        key = record_key(row)
        if key not in actions:
            counts["WARMUP_EXCLUDED"] += 1
            continue
        action = actions[key]
        counts[action.value] += 1
        if action is CrtPureReasoningAction.WAIT:
            delayed = delayed_by_key[key]
            if delayed.delayed_trade is None:
                counts["WAIT_TERMINAL"] += 1
            else:
                included.append(delayed)
                counts["WAIT_VIABLE"] += 1
    if counts["WAIT"] != counts["WAIT_TERMINAL"] + counts["WAIT_VIABLE"]:
        raise ValueError("Nested cohort WAIT accounting mismatch")
    if sum(counts[k] for k in ("EXECUTE", "WAIT", "ABSTAIN", "WARMUP_EXCLUDED")) != len(
        training
    ):
        raise ValueError("Nested training action reconciliation mismatch")
    return tuple(included), dict(sorted(counts.items()))


def run_market(
    market: str,
    *,
    frozen_ledger: Path,
    frozen_report: Path,
) -> dict[str, Any]:
    if market == "AUDUSD":
        module: Any = r2cc
        start, end, training_years = r2bh.START, r2bh.END, r2bh.TRAINING_YEARS
        year_start = r2bh._year_start
        slice_records = r2bh._slice
        initial_fit = r2by._fit
        initial_decision = r2ce._aud_initial_decision
    elif market == "USDJPY":
        module = r2cd
        start, end, training_years = r2bc.START, r2bc.END, r2bz.TRAINING_YEARS
        year_start = r2bz._year_start
        slice_records = r2bz._slice
        initial_fit = r2bz._fit
        initial_decision = r2bz._decision
    else:
        raise ValueError(f"Unsupported market: {market}")

    if training_years != INNER_YEARS:
        raise ValueError("Unexpected initial model 4Y training contract")
    delayed_rows = r2ce._load_frozen_delayed(market, frozen_ledger)
    records = tuple(row.source for row in delayed_rows)
    keys = tuple(module._record_key(row) for row in records)
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate frozen original-record keys")
    delayed_by_key = {
        module._record_key(row.source): row for row in delayed_rows
    }
    if len(delayed_by_key) != len(records):
        raise ValueError("Duplicate frozen delayed-record keys")

    actions, nested_provenance = _nested_membership(
        records,
        start=start,
        end=end,
        year_start=cast(Any, year_start),
        slice_records=cast(Any, slice_records),
        initial_fit=cast(Any, initial_fit),
        initial_decision=cast(Any, initial_decision),
        record_key=module._record_key,
    )
    all_portfolios: dict[str, list[Any]] = {arm: [] for arm in ARMS}
    positive_years: Counter[str] = Counter()
    pooled_initial: Counter[str] = Counter()
    pooled_second: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
    pooled_transitions: Counter[str] = Counter()
    pooled_terminal: Counter[str] = Counter()
    folds: list[dict[str, Any]] = []

    for year in range(start.year + training_years, end.year):
        training = cast(Any, slice_records)(
            records, year_start(year - training_years), year_start(year)
        )
        oos = cast(Any, slice_records)(
            records, year_start(year), year_start(year + 1)
        )
        initial_model, initial_fit_metadata = cast(Any, initial_fit)(training)
        original_train = tuple(delayed_by_key[module._record_key(row)] for row in training)
        nested_train, nested_cohort_counts = _nested_cohort(
            training,
            actions=actions,
            delayed_by_key=delayed_by_key,
            record_key=module._record_key,
        )
        control_memory, control_fit = module._fit_journey(original_train)
        nested_memory, nested_fit = module._fit_journey(nested_train)
        memories = {
            "CONTROL_ALL": control_memory,
            "STRICT_NESTED_WAIT_4Y": nested_memory,
        }
        fold_portfolio: dict[str, list[Any]] = {arm: [] for arm in ARMS}
        initial_counts: Counter[str] = Counter()
        second_counts: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
        terminal_counts: Counter[str] = Counter()
        transitions: Counter[str] = Counter()
        viable_wait = 0

        for row in oos:
            action = r2ce._initial_action(initial_decision, initial_model, row)
            initial_counts[action.value] += 1
            pooled_initial[action.value] += 1
            if action is CrtPureReasoningAction.EXECUTE:
                for arm in ARMS:
                    fold_portfolio[arm].append(
                        module.ExecutedRecord(row.trade, row.dead_on_arrival, "INITIAL_EXECUTE")
                    )
                continue
            if action is CrtPureReasoningAction.ABSTAIN:
                continue

            delayed = delayed_by_key[module._record_key(row)]
            if delayed.delayed_trade is None:
                terminal = delayed.terminal_reason or "UNKNOWN_TERMINAL"
                terminal_counts[terminal] += 1
                pooled_terminal[terminal] += 1
                continue
            viable_wait += 1
            second_pair: dict[str, str] = {}
            for arm in ARMS:
                decision = module._second_decision(memories[arm], delayed)
                second = decision.action
                if second not in (
                    CrtPureReasoningAction.EXECUTE,
                    CrtPureReasoningAction.WAIT,
                    CrtPureReasoningAction.ABSTAIN,
                ):
                    raise ValueError("Unexpected nested second action")
                second_counts[arm][second.value] += 1
                pooled_second[arm][second.value] += 1
                second_pair[arm] = second.value
                if second is CrtPureReasoningAction.EXECUTE:
                    if delayed.delayed_doa is None:
                        raise ValueError("Missing delayed DOA")
                    fold_portfolio[arm].append(
                        module.ExecutedRecord(
                            delayed.delayed_trade, delayed.delayed_doa, "WAIT_DELAYED_EXECUTE"
                        )
                    )
            transition = (
                second_pair["CONTROL_ALL"] + " -> "
                + second_pair["STRICT_NESTED_WAIT_4Y"]
            )
            transitions[transition] += 1
            pooled_transitions[transition] += 1

        if len(oos) != sum(initial_counts.values()):
            raise ValueError("Outer initial actions do not reconcile")
        if initial_counts["WAIT"] != sum(terminal_counts.values()) + viable_wait:
            raise ValueError("Outer WAIT accounting does not reconcile")

        fold_metrics: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            if sum(second_counts[arm].values()) != viable_wait:
                raise ValueError("Outer second actions do not reconcile")
            if len(fold_portfolio[arm]) != (
                initial_counts["EXECUTE"] + second_counts[arm]["EXECUTE"]
            ):
                raise ValueError("Outer portfolio count does not reconcile")
            executed = tuple(sorted(fold_portfolio[arm], key=lambda x: x.trade.entry_opened_at))
            all_portfolios[arm].extend(executed)
            fold_metrics[arm] = module._metrics(executed)
            positive_years[arm] += float(fold_metrics[arm]["total_r"]) > 0

        folds.append(
            {
                "oos_year": year,
                "outer_initial_fit": initial_fit_metadata,
                "training_cohort_nested": nested_cohort_counts,
                "journey_fit": {
                    "CONTROL_ALL": control_fit,
                    "STRICT_NESTED_WAIT_4Y": nested_fit,
                },
                "initial_actions": dict(initial_counts),
                "terminal_wait": dict(terminal_counts),
                "viable_wait": viable_wait,
                "second_actions": {arm: dict(second_counts[arm]) for arm in ARMS},
                "transitions": dict(transitions),
                "portfolio": fold_metrics,
            }
        )

    results = {
        arm: module._metrics(
            tuple(sorted(
                all_portfolios[arm], key=lambda x: x.trade.entry_opened_at
            ))
        )
        for arm in ARMS
    }
    reference = r2ce._reference_check(market, results["CONTROL_ALL"])
    direct_reproduction = r2ce._verify_frozen_report(
        results["CONTROL_ALL"], frozen_report
    )
    if not reference["matches_frozen_publication"]:
        raise ValueError("Frozen control economic result failed reproduction")
    if len(folds) == 0:
        raise ValueError("No outer OOS folds")
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market,
        "input_ledger_sha256": __import__("hashlib").sha256(
            frozen_ledger.read_bytes()
        ).hexdigest(),
        "source_run_id": r2ce.FROZEN_LEDGER_RUNS[market],
        "strict_inner_warmup_years": INNER_YEARS,
        "inner_historical_years": nested_provenance,
        "nested_journal_actions_available": len(actions),
        "control_reproduction": reference,
        "control_source_report_reproduction": direct_reproduction,
        "results": results,
        "trades_per_year": {
            arm: round(results[arm]["trades"] / len(folds), 8) for arm in ARMS
        },
        "density_ge_170": {
            arm: results[arm]["trades"] / len(folds) >= MIN_DENSITY_PER_YEAR
            for arm in ARMS
        },
        "positive_year_fraction": {
            arm: round(positive_years[arm] / len(folds), 8) for arm in ARMS
        },
        "initial_actions": dict(pooled_initial),
        "wait_terminal": dict(pooled_terminal),
        "second_actions": {arm: dict(pooled_second[arm]) for arm in ARMS},
        "second_transitions": dict(pooled_transitions),
        "folds": folds,
        "automatic_promotion": False,
        "market_candidate_certified": False,
        "fresh_holdout_used": False,
        "research_only": True,
        "no_sizing_or_volume": True,
        "no_merge_or_deployment": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--market", choices=("AUDUSD", "USDJPY"), required=True)
    parser.add_argument("--frozen-ledger", type=Path, required=True)
    parser.add_argument("--frozen-report", type=Path, required=True)
    args = parser.parse_args()
    result = run_market(
        args.market,
        frozen_ledger=args.frozen_ledger,
        frozen_report=args.frozen_report,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    summary = {
        "market": result["market"],
        "results": result["results"],
        "trades_per_year": result["trades_per_year"],
        "positive_year_fraction": result["positive_year_fraction"],
        "second_actions": result["second_actions"],
        "nested_journal_actions_available": result["nested_journal_actions_available"],
        "control_reproduction": result["control_reproduction"],
        "folds": [
            {
                "year": item["oos_year"],
                "training_nested": item["training_cohort_nested"],
                "portfolio": {
                    arm: {
                        "trades": item["portfolio"][arm]["trades"],
                        "total_r": item["portfolio"][arm]["total_r"],
                        "profit_factor": item["portfolio"][arm]["profit_factor"],
                    }
                    for arm in ARMS
                },
            }
            for item in result["folds"]
        ],
    }
    print("VT08_R2CF_STRICT_NESTED_WAIT=" + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
