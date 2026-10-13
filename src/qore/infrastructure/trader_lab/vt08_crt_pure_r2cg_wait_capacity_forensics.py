"""R2-CG frozen R2-CF failure attribution and arithmetic WAIT capacity; no new strategy.

Preregistered in docs/research/VT08-CRT-PURE-R2CG-FAILURE-ATTRIBUTION-WAIT-CAPACITY-FREEZE-001.md.
Read-only historical forensics; no sizing, volume, trading, or certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import datetime
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
from qore.infrastructure.trader_lab import vt08_crt_pure_r2cf_strict_nested_wait_journal as r2cf
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureReasoningAction as Action,
)

IDENTITY = "VT08_CRT_PURE_R2CG_FAILURE_ATTRIBUTION_WAIT_CAPACITY_001"
ARMS = ("CONTROL_ALL", "STRICT_NESTED_WAIT_4Y")
COSTS = (0.02, 0.05)
TARGET_DENSITY_PER_YEAR = 170
BAD_YEARS = {"AUDUSD": 2016, "USDJPY": 2023}


def _compared_metrics(
    observed: dict[str, Any],
    frozen: dict[str, Any],
    *,
    scope: str,
) -> None:
    """Required metrics are not silently skipped if the source report changes."""
    keys = (
        "trades", "total_r", "profit_factor", "max_drawdown_r",
        "dead_on_arrival_rate", "origin_counts",
    )
    for key in keys:
        actual, expected = observed[key], frozen[key]
        if isinstance(actual, dict) or isinstance(actual, int):
            agrees = actual == expected
        elif actual is None or expected is None:
            agrees = actual is expected
        else:
            agrees = abs(float(actual) - float(expected)) <= 1e-7
        if not agrees:
            raise ValueError(
                f"{scope}: frozen reconciliation failed for {key}: "
                f"{actual!r} != {expected!r}"
            )
    for cost in COSTS:
        name = f"COST_{cost:.2f}R"
        for key in ("trades", "profit_factor", "total_r", "max_drawdown_r"):
            actual, expected = observed["cost_stress"][name][key], (
                frozen["cost_stress"][name][key]
            )
            if actual is None or expected is None:
                agrees = actual is expected
            else:
                agrees = abs(float(actual) - float(expected)) <= 1e-7
            if not agrees:
                raise ValueError(
                    f"{scope}: cost={cost} frozen reconciliation failed "
                    f"for {key}: {actual!r} != {expected!r}"
                )


def _capacity(
    initial_execute: int,
    viable_wait: int,
    nested_delayed_execute: int,
    *,
    fold_count: int,
) -> dict[str, Any]:
    if (
        initial_execute < 0 or viable_wait < 0
        or nested_delayed_execute < 0 or nested_delayed_execute > viable_wait
        or fold_count <= 0
    ):
        raise ValueError("Invalid WAIT capacity accounting")
    baseline_trades = initial_execute + nested_delayed_execute
    maximum = initial_execute + viable_wait
    target = TARGET_DENSITY_PER_YEAR * fold_count
    unselected = viable_wait - nested_delayed_execute
    shortfall = max(0, target - baseline_trades)
    return {
        "strict_nested_trades": baseline_trades,
        "initial_execute": initial_execute,
        "all_viable_first_wait": viable_wait,
        "strict_nested_delayed_execute": nested_delayed_execute,
        "viable_not_executed": unselected,
        "upper_bound_trades": maximum,
        "upper_bound_trades_per_year": round(maximum / fold_count, 8),
        "research_density_target_total": target,
        "remaining_trades_to_target": shortfall,
        "arithmetic_ceiling_reaches_target": maximum >= target,
        "unselected_viable_sufficient_in_count_only": unselected >= shortfall,
        "upper_bound_only_not_an_executable_or_profitable_portfolio": True,
    }


def _attribution_add(
    totals: dict[str, dict[str, float | int]],
    *,
    transition: str,
    delayed_r: float,
) -> None:
    item = totals.setdefault(
        transition, {"count": 0, "gross_r": 0.0, "minus_002_r": 0.0, "minus_005_r": 0.0}
    )
    item["count"] += 1
    item["gross_r"] += delayed_r
    item["minus_002_r"] += delayed_r - 0.02
    item["minus_005_r"] += delayed_r - 0.05


def _check_transition_delta(
    totals: dict[str, dict[str, float | int]],
    actual_delta: float,
    *,
    scope: str,
) -> None:
    expected_delta = float(totals.get("NESTED_ONLY_EXECUTE", {}).get("gross_r", 0.0)) - (
        float(totals.get("CONTROL_ONLY_EXECUTE", {}).get("gross_r", 0.0))
    )
    if abs(actual_delta - expected_delta) > 1e-6:
        raise ValueError(
            f"{scope}: transition-delta reconciliation failure "
            f"{actual_delta} != {expected_delta}"
        )


def _configure(
    market: str,
) -> tuple[
    Any, datetime, datetime, int,
    Callable[[int], datetime],
    Callable[[tuple[Any, ...], datetime, datetime], tuple[Any, ...]],
    Callable[[tuple[Any, ...]], tuple[Any, dict[str, Any]]],
    Callable[[Any, Any], Any],
]:
    year_start: Callable[[int], datetime]
    slice_records: Callable[[tuple[Any, ...], datetime, datetime], tuple[Any, ...]]
    initial_fit: Callable[[tuple[Any, ...]], tuple[Any, dict[str, Any]]]
    initial_decision: Callable[[Any, Any], Any]
    if market == "AUDUSD":
        module: Any = r2cc
        start, end, years = r2bh.START, r2bh.END, r2bh.TRAINING_YEARS
        year_start, slice_records = r2bh._year_start, r2bh._slice
        initial_fit, initial_decision = r2by._fit, r2ce._aud_initial_decision
    elif market == "USDJPY":
        module = r2cd
        start, end, years = r2bc.START, r2bc.END, r2bz.TRAINING_YEARS
        year_start, slice_records = r2bz._year_start, r2bz._slice
        initial_fit, initial_decision = r2bz._fit, r2bz._decision
    else:
        raise ValueError(f"Unsupported market {market}")
    return module, start, end, years, year_start, slice_records, initial_fit, initial_decision


def run_market(
    market: str, *, frozen_ledger: Path, frozen_report: Path, frozen_r2cf: Path
) -> dict[str, Any]:
    (
        module, start, end, years, year_start, slice_records, initial_fit, initial_decision
    ) = _configure(market)
    reference = json.loads(frozen_r2cf.read_text(encoding="utf-8"))
    if reference["market"] != market or reference["identity"] != r2cf.IDENTITY:
        raise ValueError("Wrong market or R2-CF reference identity")
    delayed = r2ce._load_frozen_delayed(market, frozen_ledger)
    records = tuple(item.source for item in delayed)
    keys = tuple(module._record_key(row) for row in records)
    if len(set(keys)) != len(keys):
        raise ValueError("Original ledger contains duplicate hypotheses")
    delayed_by_key = {module._record_key(item.source): item for item in delayed}
    historical_actions, _ = r2cf._nested_membership(
        records, start=start, end=end, year_start=cast(Any, year_start),
        slice_records=cast(Any, slice_records), initial_fit=cast(Any, initial_fit),
        initial_decision=cast(Any, initial_decision), record_key=module._record_key,
    )
    per_fold: list[dict[str, Any]] = []
    complete_executed: dict[str, list[Any]] = {arm: [] for arm in ARMS}
    pooled_transitions: dict[str, dict[str, float | int]] = {}
    pooled_state_r: dict[str, dict[str, float | int]] = {}
    pooled_states: dict[str, Counter[str]] = defaultdict(Counter)
    pooled_reasons: Counter[str] = Counter()
    pooled_initial: Counter[str] = Counter()
    pooled_second: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
    total_viable = 0
    total_initial_execute = 0

    reference_folds = {int(f["oos_year"]): f for f in reference["folds"]}
    if len(reference_folds) != end.year - (start.year + years):
        raise ValueError("Wrong R2-CF reference fold coverage")
    for year in range(start.year + years, end.year):
        outer_train = cast(Any, slice_records)(
            records, year_start(year - years), year_start(year)
        )
        outer_oos = cast(Any, slice_records)(
            records, year_start(year), year_start(year + 1)
        )
        initial_model, _ = cast(Any, initial_fit)(outer_train)
        control_train = tuple(delayed_by_key[module._record_key(x)] for x in outer_train)
        nested_train, _ = r2cf._nested_cohort(
            outer_train, actions=historical_actions, delayed_by_key=delayed_by_key,
            record_key=module._record_key,
        )
        memories = {
            "CONTROL_ALL": module._fit_journey(control_train)[0],
            "STRICT_NESTED_WAIT_4Y": module._fit_journey(nested_train)[0],
        }
        fold_executed: dict[str, list[Any]] = {arm: [] for arm in ARMS}
        first: Counter[str] = Counter()
        second: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
        terminal: Counter[str] = Counter()
        transition_totals: dict[str, dict[str, float | int]] = {}
        state_transition_r: dict[str, dict[str, float | int]] = {}
        state_counts: dict[str, Counter[str]] = defaultdict(Counter)
        viable = 0

        for row in outer_oos:
            action = r2ce._initial_action(initial_decision, initial_model, row)
            first[action.value] += 1
            pooled_initial[action.value] += 1
            if action is Action.EXECUTE:
                for arm in ARMS:
                    fold_executed[arm].append(
                        module.ExecutedRecord(row.trade, row.dead_on_arrival, "INITIAL_EXECUTE")
                    )
                continue
            if action is Action.ABSTAIN:
                continue

            item = delayed_by_key[module._record_key(row)]
            if item.delayed_trade is None:
                reason = item.terminal_reason or "UNKNOWN_TERMINAL"
                terminal[reason] += 1
                pooled_reasons[reason] += 1
                continue

            viable += 1
            delayed_r = float(item.delayed_trade.r_multiple)
            actions: dict[str, Action] = {}
            for arm in ARMS:
                decision = module._second_decision(memories[arm], item)
                second_action = cast(Action, decision.action)
                if second_action not in (Action.EXECUTE, Action.WAIT, Action.ABSTAIN):
                    raise ValueError("Second action outside frozen sovereign contract")
                actions[arm] = second_action
                second[arm][second_action.value] += 1
                pooled_second[arm][second_action.value] += 1
                if second_action is Action.EXECUTE:
                    if item.delayed_doa is None:
                        raise ValueError("Missing DOA for executed WAIT")
                    fold_executed[arm].append(
                        module.ExecutedRecord(
                            item.delayed_trade, item.delayed_doa, "WAIT_DELAYED_EXECUTE"
                        )
                    )

            know, _, _, cell = module._knowledge(
                memories["STRICT_NESTED_WAIT_4Y"], item.journey_state
            )
            nested_knowledge = know.value
            transition = (
                "BOTH_EXECUTE" if all(v is Action.EXECUTE for v in actions.values())
                else "CONTROL_ONLY_EXECUTE"
                if actions["CONTROL_ALL"] is Action.EXECUTE
                else "NESTED_ONLY_EXECUTE"
                if actions["STRICT_NESTED_WAIT_4Y"] is Action.EXECUTE
                else "NEITHER_EXECUTE"
            )
            state_key = (
                f"{item.journey_state}|{nested_knowledge}|"
                f"{actions['CONTROL_ALL'].value}->{actions['STRICT_NESTED_WAIT_4Y'].value}"
            )
            state_counts[state_key]["count"] += 1
            _attribution_add(
                state_transition_r, transition=state_key, delayed_r=delayed_r
            )
            _attribution_add(
                pooled_state_r, transition=state_key, delayed_r=delayed_r
            )
            pooled_states[item.journey_state][nested_knowledge] += 1
            pooled_states[item.journey_state][transition] += 1
            pooled_states[item.journey_state]["viable"] += 1
            if cell is None:
                pooled_states[item.journey_state]["unsupported"] += 1
            _attribution_add(
                transition_totals, transition=transition, delayed_r=delayed_r
            )
            _attribution_add(
                pooled_transitions, transition=transition, delayed_r=delayed_r
            )

        if sum(first.values()) != len(outer_oos):
            raise ValueError(f"{market} {year} initial actions not partitioned")
        if first["WAIT"] != sum(terminal.values()) + viable:
            raise ValueError(f"{market} {year} WAIT terminal/viable loss")
        row_metrics: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            if sum(second[arm].values()) != viable:
                raise ValueError(f"{market} {year} second actions mismatch")
            if len(fold_executed[arm]) != first["EXECUTE"] + second[arm]["EXECUTE"]:
                raise ValueError(f"{market} {year} portfolio count mismatch")
            frozen = tuple(
                sorted(fold_executed[arm], key=lambda x: x.trade.entry_opened_at)
            )
            complete_executed[arm].extend(frozen)
            row_metrics[arm] = module._metrics(frozen)
            _compared_metrics(
                row_metrics[arm], reference_folds[year]["portfolio"][arm],
                scope=f"{market}-{year}-{arm}",
            )
        delta = (
            float(row_metrics["STRICT_NESTED_WAIT_4Y"]["total_r"])
            - float(row_metrics["CONTROL_ALL"]["total_r"])
        )
        _check_transition_delta(transition_totals, delta, scope=f"{market}-{year}")
        total_initial_execute += first["EXECUTE"]
        total_viable += viable
        per_fold.append(
            {
                "year": year, "oos_opportunities": len(outer_oos),
                "initial_actions": dict(first),
                "wait_terminal_reasons": dict(terminal),
                "viable_wait": viable,
                "second_actions": {arm: dict(second[arm]) for arm in ARMS},
                "transitions": transition_totals,
                "strict_knowledge_action_state_counts": {
                    key: dict(values) for key, values in sorted(state_counts.items())
                },
                "retrospective_state_transition_R_not_a_rule": state_transition_r,
                "gross_R_delta_nested_minus_control": round(delta, 8),
                "reconciled_to_frozen_R2CF": True,
                "capacity": _capacity(
                    first["EXECUTE"], viable, second["STRICT_NESTED_WAIT_4Y"]["EXECUTE"],
                    fold_count=1,
                ),
            }
        )
    combined = {
        arm: module._metrics(tuple(
            sorted(complete_executed[arm], key=lambda x: x.trade.entry_opened_at)
        ))
        for arm in ARMS
    }
    for arm in ARMS:
        _compared_metrics(
            combined[arm], reference["results"][arm],
            scope=f"{market}-combined-{arm}",
        )
    r2ce._verify_frozen_report(combined["CONTROL_ALL"], frozen_report)
    assert len(per_fold) > 0
    aggregate_delta = (
        float(combined["STRICT_NESTED_WAIT_4Y"]["total_r"])
        - float(combined["CONTROL_ALL"]["total_r"])
    )
    _check_transition_delta(pooled_transitions, aggregate_delta, scope=market)
    capacity = _capacity(
        total_initial_execute, total_viable,
        pooled_second["STRICT_NESTED_WAIT_4Y"]["EXECUTE"],
        fold_count=len(per_fold),
    )
    if capacity["strict_nested_trades"] != combined["STRICT_NESTED_WAIT_4Y"]["trades"]:
        raise ValueError("Arithmetic upper bound failed exact portfolio reconciliation")
    focus = next((row for row in per_fold if row["year"] == BAD_YEARS[market]), None)
    if focus is None:
        raise ValueError("Required degradation year absent")
    return {
        "identity": IDENTITY, "market": market,
        "source_r2cf_run": 38442593863,
        "frozen_original_run": r2ce.FROZEN_LEDGER_RUNS[market],
        "input_sha256": {
            "original_ledger": hashlib.sha256(frozen_ledger.read_bytes()).hexdigest(),
            "r2cf_reference": hashlib.sha256(frozen_r2cf.read_bytes()).hexdigest(),
        },
        "reproduction_all_folds_and_pooled": True,
        "combined_results": combined,
        "capacity": capacity,
        "initial_actions": dict(pooled_initial),
        "terminal_wait_reasons": dict(pooled_reasons),
        "second_actions": {arm: dict(pooled_second[arm]) for arm in ARMS},
        "transition_attribution": pooled_transitions,
        "retrospective_state_transition_R_not_a_rule": pooled_state_r,
        "journey_state_knowledge_transitions": {
            k: dict(v) for k, v in sorted(pooled_states.items())
        },
        "focus_degradation_year": focus,
        "folds": per_fold,
        "no_rule_promotion": True, "research_only": True,
        "no_sizing_volume": True, "fresh_holdout_used": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("--market", choices=("AUDUSD", "USDJPY"), required=True)
    p.add_argument("--frozen-ledger", required=True, type=Path)
    p.add_argument("--frozen-report", required=True, type=Path)
    p.add_argument("--frozen-r2cf", required=True, type=Path)
    args = p.parse_args()
    result = run_market(
        args.market, frozen_ledger=args.frozen_ledger,
        frozen_report=args.frozen_report, frozen_r2cf=args.frozen_r2cf,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("VT08_R2CG_FORENSICS=" + json.dumps({
        k: result[k] for k in (
            "market", "capacity", "transition_attribution",
            "journey_state_knowledge_transitions", "focus_degradation_year",
            "retrospective_state_transition_R_not_a_rule",
            "reproduction_all_folds_and_pooled",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
