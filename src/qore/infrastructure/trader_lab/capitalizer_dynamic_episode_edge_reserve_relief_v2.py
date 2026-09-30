"""Dynamic edge-reserve / drawdown-relief feasibility oracle.

Diagnostic only.  This extends Sequence Feasibility V1 by allowing the system to
build a Pareto-monotone PF/Total-R reserve using right-tail-preserving actions
before spending that reserve on actions that reduce DD.  Every candidate plan
is replayed exactly through the existing V11/V10 Surface cognition.

No result from this module is a runtime policy or certification candidate.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_counterfactual_portfolio_episode_simulator_v1 as simulator,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_sequence_feasibility_v1 as sequence_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_first_intervention_cross_trigger_optionality_v30 as v30,
)
from qore.infrastructure.trader_lab import (
    capitalizer_portfolio_drawdown_feasibility_episode_anatomy_v1 as anatomy,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_DYNAMIC_EPISODE_EDGE_RESERVE_RELIEF_V2"


@dataclass(frozen=True, slots=True)
class ActionSeed:
    symbol: str
    entry_at: str
    action: str
    source_dynamic_total_delta_r: str
    source_legacy_dd_relief_r: str
    source_rollout_profit_factor: str | None
    source_in_max_dd_descent: bool


@dataclass(frozen=True, slots=True)
class V2Step:
    step: int
    role: str
    symbol: str
    entry_at: str
    action: str
    current_surface_mode_at_application: str
    current_trigger_family_at_application: str
    current_trigger_at: str
    prior_profit_factor: str | None
    resulting_profit_factor: str | None
    prior_total_r: str
    resulting_total_r: str
    prior_dd_r: str
    resulting_dd_r: str
    prior_losing_streak: int
    resulting_losing_streak: int


def _mode_order(action: str) -> int:
    return tuple(
        mode.value for mode in milestone.ProtectionMode
    ).index(action)


def _load_seeds(
    transition_path: Path,
    *,
    period: str,
    baseline_profit_factor: str,
) -> tuple[tuple[ActionSeed, ...], tuple[ActionSeed, ...]]:
    reserve: dict[tuple[str, str, str], ActionSeed] = {}
    relief: dict[tuple[str, str, str], ActionSeed] = {}
    baseline_pf = Decimal(baseline_profit_factor)

    with transition_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row["period"] != period:
                continue
            seed = ActionSeed(
                symbol=row["symbol"],
                entry_at=row["entry_at"],
                action=row["action"],
                source_dynamic_total_delta_r=row["dynamic_total_delta_r"],
                source_legacy_dd_relief_r=row["legacy_dd_relief_r"],
                source_rollout_profit_factor=row["rollout_profit_factor"],
                source_in_max_dd_descent=bool(
                    row["entrant_in_surface_max_dd_descent"]
                ),
            )
            key = (seed.symbol, seed.entry_at, seed.action)
            dynamic_total = Decimal(seed.source_dynamic_total_delta_r)
            dd_relief = Decimal(seed.source_legacy_dd_relief_r)
            source_pf = (
                None
                if seed.source_rollout_profit_factor is None
                else Decimal(seed.source_rollout_profit_factor)
            )

            if (
                dynamic_total > 0
                and dd_relief >= 0
                and source_pf is not None
                and source_pf >= baseline_pf
            ):
                reserve[key] = seed
            if dd_relief > 0:
                relief[key] = seed

    def sorter(row: ActionSeed) -> tuple[Any, ...]:
        return (
            milestone._aware(row.entry_at),
            row.symbol,
            _mode_order(row.action),
        )

    return (
        tuple(sorted(reserve.values(), key=sorter)),
        tuple(sorted(relief.values(), key=sorter)),
    )


def _profit_factor(metrics: dict[str, Any]) -> Decimal:
    value = metrics["profit_factor"]
    if value is None:
        raise ValueError("V2 requires finite non-null profit factor")
    return Decimal(value)


def _full_gate(
    metrics: dict[str, Any],
    *,
    baseline: dict[str, Any],
    intervention_count: int,
) -> bool:
    return sequence_v1._full_gate(
        metrics,
        baseline=baseline,
        intervention_count=intervention_count,
    )


def _relief_admissible(
    metrics: dict[str, Any],
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    return (
        _profit_factor(metrics) >= _profit_factor(baseline)
        and Decimal(metrics["total_r"]) >= Decimal(baseline["total_r"])
        and int(metrics["max_losing_streak"])
        <= int(baseline["max_losing_streak"])
        and Decimal(metrics["max_drawdown_r"])
        < Decimal(current["max_drawdown_r"])
        and int(metrics["trades"]) == int(baseline["trades"])
    )


def _reserve_admissible(
    metrics: dict[str, Any],
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    return (
        Decimal(metrics["max_drawdown_r"])
        <= Decimal(current["max_drawdown_r"])
        and Decimal(metrics["total_r"]) > Decimal(current["total_r"])
        and _profit_factor(metrics) >= _profit_factor(current)
        and int(metrics["max_losing_streak"])
        <= int(baseline["max_losing_streak"])
        and int(metrics["trades"]) == int(baseline["trades"])
    )


def _relief_rank(
    metrics: dict[str, Any],
    seed: ActionSeed,
) -> tuple[Any, ...]:
    return (
        Decimal(metrics["max_drawdown_r"]),
        -Decimal(metrics["total_r"]),
        -_profit_factor(metrics),
        milestone._aware(seed.entry_at),
        seed.symbol,
        _mode_order(seed.action),
    )


def _reserve_rank(
    metrics: dict[str, Any],
    seed: ActionSeed,
) -> tuple[Any, ...]:
    return (
        -Decimal(metrics["total_r"]),
        -_profit_factor(metrics),
        Decimal(metrics["max_drawdown_r"]),
        milestone._aware(seed.entry_at),
        seed.symbol,
        _mode_order(seed.action),
    )


def _plan_cache_key(
    plan: dict[tuple[str, str], str],
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted(
            (
                symbol,
                entry_at,
                action,
            )
            for (symbol, entry_at), action in plan.items()
        )
    )


def _replay_extension_from_current_prefix(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    ordered: tuple[milestone.SimulatedTrade, ...],
    modes: dict[
        str,
        dict[tuple[str, str], milestone.SimulatedTrade],
    ],
    order_index: dict[tuple[str, str], int],
    current_plan: dict[tuple[str, str], str],
    current_ledger: tuple[milestone.SimulatedTrade, ...],
    current_records: tuple[memory.MemoryRecord, ...],
    current_decisions: tuple[simulator.ReplayDecision, ...],
    current_applied: dict[tuple[str, str], tuple[str, str, str]],
    seed: ActionSeed,
) -> tuple[
    tuple[milestone.SimulatedTrade, ...],
    tuple[memory.MemoryRecord, ...],
    tuple[simulator.ReplayDecision, ...],
    dict[tuple[str, str], tuple[str, str, str]],
    int,
]:
    key = (seed.symbol, seed.entry_at)
    if key in current_plan:
        raise sequence_v1.InvalidPlanError(
            f"V2 extension key already committed: {key}"
        )
    start_index = order_index[key]
    trial_plan = dict(current_plan)
    trial_plan[key] = seed.action

    chosen: list[milestone.SimulatedTrade] = list(
        current_ledger[:start_index]
    )
    records: list[memory.MemoryRecord] = list(
        current_records[:start_index]
    )
    decisions: list[simulator.ReplayDecision] = list(
        current_decisions[:start_index]
    )
    applied = {
        planned_key: value
        for planned_key, value in current_applied.items()
        if order_index[planned_key] < start_index
    }

    for trade in ordered[start_index:]:
        trade_key = (trade.symbol, trade.entry_at)
        pretrade = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        selected_mode = pretrade.mode
        action = trial_plan.get(trade_key)

        if action is not None:
            family = v30._mode_family(pretrade.mode)
            if family is None:
                raise sequence_v1.InvalidPlanError(
                    "V2 planned key has no current trigger family: "
                    f"{trade_key}"
                )
            surface = modes[pretrade.mode][trade_key]
            trigger_at = surface.first_protection_at
            if trigger_at is None:
                raise sequence_v1.InvalidPlanError(
                    "V2 planned key has no actual current trigger: "
                    f"{trade_key}"
                )
            if action == pretrade.mode:
                raise sequence_v1.InvalidPlanError(
                    "V2 planned action became current Surface no-op: "
                    f"{trade_key}"
                )
            if action not in v30._eligible_actions(family):
                raise sequence_v1.InvalidPlanError(
                    "V2 planned action no longer reachable after feedback: "
                    f"{trade_key}"
                )
            v30._assert_common_path(
                key=trade_key,
                trigger_at=trigger_at,
                actions=(action,),
                modes=modes,
            )
            selected_mode = action
            applied[trade_key] = (
                pretrade.mode,
                family,
                trigger_at,
            )

        selected = modes[selected_mode][trade_key]
        scaled_r = (
            Decimal(selected.realized_gross_r) * pretrade.base_multiplier
        )
        chosen.append(
            replace(selected, realized_gross_r=str(scaled_r))
        )
        records.append(
            memory.MemoryRecord(
                symbol=pretrade.ctx.symbol,
                session=pretrade.ctx.session,
                destination_state=pretrade.ctx.destination_state,
                context_signature=pretrade.ctx.context_signature,
                exit_at=selected.exit_at,
                normalized_realized_r=selected.realized_gross_r,
            )
        )
        decisions.append(
            simulator.ReplayDecision(
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                surface_hint_mode=pretrade.mode,
                selected_mode=selected_mode,
                base_multiplier=str(pretrade.base_multiplier),
                scaled_realized_r=str(scaled_r),
            )
        )

    if set(applied) != set(trial_plan):
        missing = set(trial_plan) - set(applied)
        raise sequence_v1.InvalidPlanError(
            f"V2 trial plan keys not applied: {sorted(missing)}"
        )
    return (
        tuple(chosen),
        tuple(records),
        tuple(decisions),
        applied,
        len(ordered) - start_index,
    )


def _evaluate_extension(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    ordered: tuple[milestone.SimulatedTrade, ...],
    modes: dict[
        str,
        dict[tuple[str, str], milestone.SimulatedTrade],
    ],
    order_index: dict[tuple[str, str], int],
    plan: dict[tuple[str, str], str],
    current_ledger: tuple[milestone.SimulatedTrade, ...],
    current_records: tuple[memory.MemoryRecord, ...],
    current_decisions: tuple[simulator.ReplayDecision, ...],
    current_applied: dict[tuple[str, str], tuple[str, str, str]],
    iteration_cache: dict[
        tuple[tuple[str, str, str], ...],
        tuple[
            dict[str, Any],
            tuple[milestone.SimulatedTrade, ...],
            tuple[memory.MemoryRecord, ...],
            tuple[simulator.ReplayDecision, ...],
            dict[tuple[str, str], tuple[str, str, str]],
        ],
    ],
    seed: ActionSeed,
) -> tuple[
    dict[str, Any],
    tuple[milestone.SimulatedTrade, ...],
    tuple[memory.MemoryRecord, ...],
    tuple[simulator.ReplayDecision, ...],
    dict[tuple[str, str], tuple[str, str, str]],
    bool,
    int,
]:
    trial_plan = dict(plan)
    trial_plan[(seed.symbol, seed.entry_at)] = seed.action
    cache_key = _plan_cache_key(trial_plan)
    cached = iteration_cache.get(cache_key)
    if cached is not None:
        metrics, ledger, records, decisions, applied = cached
        return (
            metrics,
            ledger,
            records,
            decisions,
            applied,
            False,
            0,
        )

    (
        ledger,
        records,
        decisions,
        applied,
        replayed_trades,
    ) = _replay_extension_from_current_prefix(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
        ordered=ordered,
        modes=modes,
        order_index=order_index,
        current_plan=plan,
        current_ledger=current_ledger,
        current_records=current_records,
        current_decisions=current_decisions,
        current_applied=current_applied,
        seed=seed,
    )
    metrics = milestone._metrics(ledger)
    iteration_cache[cache_key] = (
        metrics,
        ledger,
        records,
        decisions,
        applied,
    )
    return (
        metrics,
        ledger,
        records,
        decisions,
        applied,
        True,
        replayed_trades,
    )


def _run_period(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    reserve_seeds: tuple[ActionSeed, ...],
    relief_seeds: tuple[ActionSeed, ...],
) -> tuple[dict[str, Any], tuple[V2Step, ...]]:
    control, _control_ledger, _surface_decisions = anatomy._surface_ledger(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    baseline_ledger, baseline_decisions, baseline_applied = (
        sequence_v1._replay_plan(
            period=period,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            plan={},
        )
    )
    baseline = milestone._metrics(baseline_ledger)
    if baseline != control["metrics"]:
        raise ValueError("V2 empty-plan Surface drift")

    modes = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = simulator._ordered(
        ledgers[milestone.ProtectionMode.ORIGINAL.value]
    )
    order_index = {
        (row.symbol, row.entry_at): index
        for index, row in enumerate(ordered)
    }
    baseline_records = simulator._baseline_records(
        ordered=ordered,
        decisions=baseline_decisions,
        modes=modes,
        contexts=contexts,
    )

    plan: dict[tuple[str, str], str] = {}
    current = baseline
    current_ledger = baseline_ledger
    current_records = baseline_records
    current_decisions = baseline_decisions
    current_applied = baseline_applied
    steps: list[V2Step] = []
    invalid_trials = 0
    replay_evaluations = 0
    replayed_trade_evaluations = 0

    while not _full_gate(
        current,
        baseline=baseline,
        intervention_count=len(plan),
    ):
        iteration_cache: dict[
            tuple[tuple[str, str, str], ...],
            tuple[
                dict[str, Any],
                tuple[milestone.SimulatedTrade, ...],
                tuple[memory.MemoryRecord, ...],
                tuple[simulator.ReplayDecision, ...],
                dict[tuple[str, str], tuple[str, str, str]],
            ],
        ] = {}

        relief_candidates: list[
            tuple[
                tuple[Any, ...],
                ActionSeed,
                dict[str, Any],
                tuple[milestone.SimulatedTrade, ...],
                tuple[memory.MemoryRecord, ...],
                tuple[simulator.ReplayDecision, ...],
                dict[tuple[str, str], tuple[str, str, str]],
            ]
        ] = []
        for seed in relief_seeds:
            key = (seed.symbol, seed.entry_at)
            if key in plan:
                continue
            try:
                (
                    metrics,
                    ledger,
                    records,
                    decisions,
                    applied,
                    newly_replayed,
                    replayed_trades,
                ) = _evaluate_extension(
                    period=period,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                    ordered=ordered,
                    modes=modes,
                    order_index=order_index,
                    plan=plan,
                    current_ledger=current_ledger,
                    current_records=current_records,
                    current_decisions=current_decisions,
                    current_applied=current_applied,
                    iteration_cache=iteration_cache,
                    seed=seed,
                )
                if newly_replayed:
                    replay_evaluations += 1
                    replayed_trade_evaluations += replayed_trades
            except sequence_v1.InvalidPlanError:
                invalid_trials += 1
                continue
            if _relief_admissible(
                metrics,
                baseline=baseline,
                current=current,
            ):
                relief_candidates.append(
                    (
                        _relief_rank(metrics, seed),
                        seed,
                        metrics,
                        ledger,
                        records,
                        decisions,
                        applied,
                    )
                )

        role = "RELIEF"
        candidates = relief_candidates

        if not candidates:
            reserve_candidates: list[
                tuple[
                    tuple[Any, ...],
                    ActionSeed,
                    dict[str, Any],
                    tuple[milestone.SimulatedTrade, ...],
                    tuple[memory.MemoryRecord, ...],
                    tuple[simulator.ReplayDecision, ...],
                    dict[tuple[str, str], tuple[str, str, str]],
                ]
            ] = []
            for seed in reserve_seeds:
                key = (seed.symbol, seed.entry_at)
                if key in plan:
                    continue
                try:
                    (
                        metrics,
                        ledger,
                        records,
                        decisions,
                        applied,
                        newly_replayed,
                        replayed_trades,
                    ) = _evaluate_extension(
                        period=period,
                        ledgers=ledgers,
                        contexts=contexts,
                        contextual_model=contextual_model,
                        ordered=ordered,
                        modes=modes,
                        order_index=order_index,
                        plan=plan,
                        current_ledger=current_ledger,
                        current_records=current_records,
                        current_decisions=current_decisions,
                        current_applied=current_applied,
                        iteration_cache=iteration_cache,
                        seed=seed,
                    )
                    if newly_replayed:
                        replay_evaluations += 1
                        replayed_trade_evaluations += replayed_trades
                except sequence_v1.InvalidPlanError:
                    invalid_trials += 1
                    continue
                if _reserve_admissible(
                    metrics,
                    baseline=baseline,
                    current=current,
                ):
                    reserve_candidates.append(
                        (
                            _reserve_rank(metrics, seed),
                            seed,
                            metrics,
                            ledger,
                            records,
                            decisions,
                            applied,
                        )
                    )
            role = "RESERVE"
            candidates = reserve_candidates

        if not candidates:
            break

        (
            _rank,
            seed,
            resulting,
            resulting_ledger,
            resulting_records,
            resulting_decisions,
            applied,
        ) = min(candidates, key=lambda row: row[0])
        key = (seed.symbol, seed.entry_at)
        prior = current
        plan[key] = seed.action
        current = resulting
        current_ledger = resulting_ledger
        current_records = resulting_records
        current_decisions = resulting_decisions
        current_applied = applied
        current_surface, family, trigger_at = applied[key]
        steps.append(
            V2Step(
                step=len(steps) + 1,
                role=role,
                symbol=seed.symbol,
                entry_at=seed.entry_at,
                action=seed.action,
                current_surface_mode_at_application=current_surface,
                current_trigger_family_at_application=family,
                current_trigger_at=trigger_at,
                prior_profit_factor=prior["profit_factor"],
                resulting_profit_factor=current["profit_factor"],
                prior_total_r=prior["total_r"],
                resulting_total_r=current["total_r"],
                prior_dd_r=prior["max_drawdown_r"],
                resulting_dd_r=current["max_drawdown_r"],
                prior_losing_streak=int(prior["max_losing_streak"]),
                resulting_losing_streak=int(
                    current["max_losing_streak"]
                ),
            )
        )

    passed = _full_gate(
        current,
        baseline=baseline,
        intervention_count=len(plan),
    )
    full_period_trade_evaluations = (
        replay_evaluations * len(ordered)
    )
    return (
        {
            "period": period,
            "surface": baseline,
            "reserve_seed_count": len(reserve_seeds),
            "reserve_seed_entrant_count": len(
                {(row.symbol, row.entry_at) for row in reserve_seeds}
            ),
            "relief_seed_count": len(relief_seeds),
            "relief_seed_entrant_count": len(
                {(row.symbol, row.entry_at) for row in relief_seeds}
            ),
            "replay_evaluations": replay_evaluations,
            "replayed_trade_evaluations": replayed_trade_evaluations,
            "full_period_trade_evaluations_without_prefix_reuse": (
                full_period_trade_evaluations
            ),
            "causal_prefix_reuse_enabled": True,
            "invalid_after_feedback_trials": invalid_trials,
            "committed_intervention_count": len(plan),
            "reserve_step_count": sum(
                row.role == "RESERVE" for row in steps
            ),
            "relief_step_count": sum(
                row.role == "RELIEF" for row in steps
            ),
            "final_metrics": current,
            "full_gate_passed": passed,
            "density_retention": "1",
            "same_entrant_identities": True,
            "stop_reason": (
                "FULL_GATE_REACHED"
                if passed
                else "NO_REACHABLE_RESERVE_OR_RELIEF_EXTENSION"
            ),
        },
        tuple(steps),
    )


def build_period_report(
    *,
    period: str,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    transition_path: Path,
) -> tuple[dict[str, Any], tuple[V2Step, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    if period not in windows:
        raise ValueError(f"unknown V2 period: {period}")

    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for current_period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(
                period=current_period,
                ledgers=ledgers,
            )
        )

    ledgers, contexts = windows[period]
    control, _ledger, _decisions = anatomy._surface_ledger(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    baseline_pf = control["metrics"]["profit_factor"]
    if baseline_pf is None:
        raise ValueError("V2 Surface profit factor unavailable")

    reserve_seeds, relief_seeds = _load_seeds(
        transition_path,
        period=period,
        baseline_profit_factor=baseline_pf,
    )
    if not reserve_seeds:
        raise ValueError("V2 found no reserve seeds")
    if not relief_seeds:
        raise ValueError("V2 found no relief seeds")

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        result, steps = _run_period(
            period=period,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            reserve_seeds=reserve_seeds,
            relief_seeds=relief_seeds,
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    return (
        {
            "identity": IDENTITY,
            "evaluation": "DYNAMIC_EDGE_RESERVE_THEN_DD_RELIEF_FEASIBILITY",
            "period": period,
            "outcome_aware_diagnostic": True,
            "runtime_policy_candidate": False,
            "reserve_is_pareto_monotone": True,
            "relief_requires_final_edge_gate": True,
            "arbitrary_step_limit": False,
            "admission_changed": False,
            "sizing_changed": False,
            "new_protection_geometry_created": False,
            "result": result,
            "candidate_count": 0,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
        },
        steps,
    )


def write_report(
    report: dict[str, Any],
    steps: tuple[V2Step, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-dynamic-episode-edge-reserve-relief-v2"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-steps.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in steps:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--reserved-root", type=Path, required=True)
    parser.add_argument(
        "--development-validation-context-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--reserved-context-root", type=Path, required=True)
    parser.add_argument("--transition-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report, steps = build_period_report(
        period=args.period,
        development_root=args.development_root,
        validation_root=args.validation_root,
        reserved_root=args.reserved_root,
        development_validation_context_root=(
            args.development_validation_context_root
        ),
        reserved_context_root=args.reserved_context_root,
        transition_path=args.transition_path,
    )
    write_report(report, steps, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
