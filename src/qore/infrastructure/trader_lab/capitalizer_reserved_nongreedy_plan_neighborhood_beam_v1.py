"""Bounded non-greedy plan-neighborhood beam for Reserved Capitalizer V2.

Outcome-aware feasibility diagnostic only.

The greedy V2 Reserved plan is already complete and locally exhausted. This
module starts from that exact committed plan and explores a fixed local
mutation neighborhood using exact full causal replay. It does not create new
actions, alter entries, change sizing, or authorize a runtime policy.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_edge_reserve_relief_v2 as v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_sequence_feasibility_v1 as sequence_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v2_distributed_checkpoint_runner_v1 as distributed,
)

IDENTITY = "QORE_CAPITALIZER_RESERVED_NON_GREEDY_PLAN_NEIGHBORHOOD_BEAM_V1"
PERIOD = "CONSUMED_RESERVED_2020_2022"
RELIEF_POOL = 24
RESERVE_POOL = 24
BEAM_WIDTH = 6
MAX_MUTATION_DEPTH = 4


Plan = dict[tuple[str, str], str]


@dataclass(frozen=True, slots=True)
class SearchNode:
    depth: int
    plan: Plan
    metrics: dict[str, Any]
    parent_signature: tuple[tuple[str, str, str], ...] | None
    mutation: str


def _signature(plan: Plan) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        sorted(
            (symbol, entry_at, action)
            for (symbol, entry_at), action in plan.items()
        )
    )


def _pf(metrics: dict[str, Any]) -> Decimal:
    value = metrics["profit_factor"]
    if value is None:
        raise ValueError("beam search requires finite profit factor")
    return Decimal(str(value))


def _gate_violations(
    metrics: dict[str, Any],
    *,
    baseline: dict[str, Any],
) -> tuple[int, Decimal, Decimal, Decimal, int]:
    dd = Decimal(str(metrics["max_drawdown_r"]))
    pf = _pf(metrics)
    total = Decimal(str(metrics["total_r"]))
    ls = int(metrics["max_losing_streak"])
    base_pf = _pf(baseline)
    base_total = Decimal(str(baseline["total_r"]))
    base_dd = Decimal(str(baseline["max_drawdown_r"]))
    base_ls = int(baseline["max_losing_streak"])

    dd_excess = max(Decimal("0"), dd - Decimal("6"))
    pf_deficit = max(Decimal("0"), base_pf - pf)
    total_deficit = max(Decimal("0"), base_total - total)
    ls_excess = max(0, ls - base_ls)
    no_dd_improvement = int(dd >= base_dd)
    violated = (
        int(dd_excess > 0)
        + int(pf_deficit > 0)
        + int(total_deficit > 0)
        + int(ls_excess > 0)
        + no_dd_improvement
    )
    return violated, dd_excess, pf_deficit, total_deficit, ls_excess


def _rank(
    node: SearchNode,
    *,
    baseline: dict[str, Any],
) -> tuple[Any, ...]:
    violated, dd_excess, pf_deficit, total_deficit, ls_excess = (
        _gate_violations(node.metrics, baseline=baseline)
    )
    return (
        violated,
        dd_excess,
        pf_deficit,
        total_deficit,
        ls_excess,
        Decimal(str(node.metrics["max_drawdown_r"])),
        -Decimal(str(node.metrics["total_r"])),
        -_pf(node.metrics),
        _signature(node.plan),
    )


def _seed_sort_relief(seed: v2.ActionSeed) -> tuple[Any, ...]:
    return (
        -Decimal(seed.source_legacy_dd_relief_r),
        milestone._aware(seed.entry_at),
        seed.symbol,
        v2._mode_order(seed.action),
    )


def _seed_sort_reserve(seed: v2.ActionSeed) -> tuple[Any, ...]:
    return (
        -Decimal(seed.source_dynamic_total_delta_r),
        milestone._aware(seed.entry_at),
        seed.symbol,
        v2._mode_order(seed.action),
    )


def _frozen_pool(
    *,
    plan: Plan,
    reserve_seeds: tuple[v2.ActionSeed, ...],
    relief_seeds: tuple[v2.ActionSeed, ...],
) -> tuple[v2.ActionSeed, ...]:
    all_seeds = {
        (seed.symbol, seed.entry_at, seed.action): seed
        for seed in (*reserve_seeds, *relief_seeds)
    }
    selected: dict[tuple[str, str, str], v2.ActionSeed] = {}
    for (symbol, entry_at), action in plan.items():
        key = (symbol, entry_at, action)
        seed = all_seeds.get(key)
        if seed is None:
            raise ValueError(f"committed V2 action missing seed: {key}")
        selected[key] = seed

    for seed in sorted(relief_seeds, key=_seed_sort_relief)[:RELIEF_POOL]:
        selected[(seed.symbol, seed.entry_at, seed.action)] = seed
    for seed in sorted(reserve_seeds, key=_seed_sort_reserve)[:RESERVE_POOL]:
        selected[(seed.symbol, seed.entry_at, seed.action)] = seed

    return tuple(
        sorted(
            selected.values(),
            key=lambda seed: (
                milestone._aware(seed.entry_at),
                seed.symbol,
                v2._mode_order(seed.action),
            ),
        )
    )


def _mutations(
    plan: Plan,
    *,
    pool: tuple[v2.ActionSeed, ...],
) -> tuple[tuple[str, Plan], ...]:
    result: list[tuple[str, Plan]] = []

    for key in sorted(plan):
        child = dict(plan)
        old = child.pop(key)
        result.append((f"DROP:{key[0]}:{key[1]}:{old}", child))

    for seed in pool:
        key = (seed.symbol, seed.entry_at)
        if plan.get(key) == seed.action:
            continue
        child = dict(plan)
        prior = child.get(key)
        child[key] = seed.action
        mutation = (
            f"SET:{seed.symbol}:{seed.entry_at}:"
            f"{prior or 'NONE'}->{seed.action}"
        )
        result.append((mutation, child))

    return tuple(result)


def _replay(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    plan: Plan,
) -> dict[str, Any]:
    ledger, _decisions, applied = sequence_v1._replay_plan(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
        plan=plan,
    )
    if set(applied) != set(plan):
        raise sequence_v1.InvalidPlanError(
            "beam exact replay did not apply every planned intervention"
        )
    return milestone._metrics(ledger)


def run_search(
    *,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    transition_path: Path,
    checkpoint_path: Path,
) -> tuple[dict[str, Any], tuple[SearchNode, ...]]:
    (
        ledgers,
        contexts,
        contextual_model,
        reserve_seeds,
        relief_seeds,
        baseline,
        _modes,
        _ordered,
        _order_index,
        simultaneous,
    ) = distributed._prepare_period(
        period=PERIOD,
        development_root=development_root,
        validation_root=validation_root,
        reserved_root=reserved_root,
        development_validation_context_root=(
            development_validation_context_root
        ),
        reserved_context_root=reserved_context_root,
        transition_path=transition_path,
    )

    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if payload["identity"] != distributed.IDENTITY:
        raise ValueError("beam start checkpoint identity mismatch")
    if payload["period"] != PERIOD:
        raise ValueError("beam start checkpoint period mismatch")
    if payload["complete"] is not True:
        raise ValueError("beam requires completed greedy Reserved checkpoint")
    if payload["stop_reason"] != "NO_REACHABLE_RESERVE_OR_RELIEF_EXTENSION":
        raise ValueError("beam requires greedy local exhaustion checkpoint")

    transition_sha = distributed._sha256(transition_path)
    (
        start_plan,
        start_steps,
        _replay_evaluations,
        _replayed_trade_evaluations,
        _invalid_trials,
        checkpoint_metrics,
    ) = distributed._load_checkpoint(
        checkpoint_path,
        period=PERIOD,
        transition_sha256=transition_sha,
        baseline=baseline,
    )
    if len(start_plan) != 45 or len(start_steps) != 45:
        raise ValueError("beam start plan must have 45 greedy interventions")
    if checkpoint_metrics is None:
        raise ValueError("beam start checkpoint metrics missing")

    pool = _frozen_pool(
        plan=start_plan,
        reserve_seeds=reserve_seeds,
        relief_seeds=relief_seeds,
    )

    previous_simultaneous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        start_metrics = _replay(
            period=PERIOD,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            plan=start_plan,
        )
        if start_metrics != checkpoint_metrics:
            raise ValueError("beam greedy checkpoint exact replay drift")

        start = SearchNode(
            depth=0,
            plan=dict(start_plan),
            metrics=start_metrics,
            parent_signature=None,
            mutation="START_GREEDY_V2_COMPLETE",
        )
        beam: tuple[SearchNode, ...] = (start,)
        visited = {_signature(start.plan)}
        accepted: list[SearchNode] = []
        trace: list[SearchNode] = [start]
        exact_replays = 1
        invalid_plans = 0
        generated_plans = 0

        for depth in range(1, MAX_MUTATION_DEPTH + 1):
            candidates: list[SearchNode] = []
            for parent in beam:
                parent_sig = _signature(parent.plan)
                for mutation, child_plan in _mutations(
                    parent.plan,
                    pool=pool,
                ):
                    generated_plans += 1
                    signature = _signature(child_plan)
                    if signature in visited:
                        continue
                    visited.add(signature)
                    try:
                        metrics = _replay(
                            period=PERIOD,
                            ledgers=ledgers,
                            contexts=contexts,
                            contextual_model=contextual_model,
                            plan=child_plan,
                        )
                    except sequence_v1.InvalidPlanError:
                        invalid_plans += 1
                        continue
                    exact_replays += 1
                    node = SearchNode(
                        depth=depth,
                        plan=child_plan,
                        metrics=metrics,
                        parent_signature=parent_sig,
                        mutation=mutation,
                    )
                    candidates.append(node)
                    trace.append(node)
                    if v2._full_gate(
                        metrics,
                        baseline=baseline,
                        intervention_count=len(child_plan),
                    ):
                        accepted.append(node)

            if accepted:
                break
            candidates.sort(key=lambda node: _rank(node, baseline=baseline))
            beam = tuple(candidates[:BEAM_WIDTH])
            if not beam:
                break

        survivors = accepted if accepted else list(beam)
        if not survivors:
            survivors = [start]
        survivors.sort(key=lambda node: _rank(node, baseline=baseline))
        best = survivors[0]
        passed = v2._full_gate(
            best.metrics,
            baseline=baseline,
            intervention_count=len(best.plan),
        )

        report = {
            "identity": IDENTITY,
            "period": PERIOD,
            "evaluation": "EXACT_LOCAL_NON_GREEDY_PLAN_FEASIBILITY",
            "start_checkpoint_identity": distributed.IDENTITY,
            "start_checkpoint_interventions": len(start_plan),
            "frozen_relief_pool_size": RELIEF_POOL,
            "frozen_reserve_pool_size": RESERVE_POOL,
            "actual_unique_pool_size": len(pool),
            "beam_width": BEAM_WIDTH,
            "max_mutation_depth": MAX_MUTATION_DEPTH,
            "allowed_mutations": ["DROP", "SET_ADD_OR_REPLACE"],
            "exact_full_causal_replay": True,
            "same_existing_action_geometry_only": True,
            "outcome_aware_diagnostic": True,
            "runtime_policy_candidate": False,
            "sampling": False,
            "threshold_grid_searched": False,
            "sizing_changed": False,
            "entry_changed": False,
            "new_protection_geometry_created": False,
            "fresh_holdout_opened": False,
            "baseline": baseline,
            "greedy_start_metrics": start_metrics,
            "generated_plans": generated_plans,
            "unique_plans_seen": len(visited),
            "exact_replays": exact_replays,
            "invalid_after_feedback_plans": invalid_plans,
            "best_depth": best.depth,
            "best_intervention_count": len(best.plan),
            "best_metrics": best.metrics,
            "full_gate_passed": passed,
            "candidate_count": 0,
            "trader_certified": False,
            "next_phase": (
                "NON_GREEDY_PM_SEQUENCE_FEASIBILITY_ESTABLISHED"
                if passed
                else "LOCAL_BEAM_FALSIFIED_REQUIRE_BROADER_EPISODE_SEARCH_OR_WORLD_MODEL"
            ),
        }
        return report, tuple(trace)
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous_simultaneous)


def write_report(
    report: dict[str, Any],
    trace: tuple[SearchNode, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-reserved-nongreedy-plan-neighborhood-beam-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trace.jsonl").open("w", encoding="utf-8") as handle:
        for row in trace:
            payload = asdict(row)
            payload["plan_signature"] = _signature(row.plan)
            payload["plan"] = [
                {
                    "symbol": symbol,
                    "entry_at": entry_at,
                    "action": action,
                }
                for symbol, entry_at, action in _signature(row.plan)
            ]
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
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
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report, trace = run_search(
        development_root=args.development_root,
        validation_root=args.validation_root,
        reserved_root=args.reserved_root,
        development_validation_context_root=(
            args.development_validation_context_root
        ),
        reserved_context_root=args.reserved_context_root,
        transition_path=args.transition_path,
        checkpoint_path=args.checkpoint,
    )
    write_report(report, trace, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
