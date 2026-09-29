"""Bounded global chronological episode-sequence search for Capitalizer V43.

Outcome-aware feasibility diagnostic only.

V43 deliberately starts from the empty Surface intervention plan rather than
from the exhausted 45-action greedy V2 checkpoint.  It searches one canonical
chronological construction path per final plan and replays every unique plan
exactly through the existing dynamic Surface cognition.

The search contract was frozen in PR #623 comments 5882543976 and 5882555652
before V43 code/economics.
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

IDENTITY = "QORE_CAPITALIZER_RESERVED_GLOBAL_EPISODE_SEQUENCE_BEAM_V43"
PERIOD = "CONSUMED_RESERVED_2020_2022"

MAXDD_RELIEF_POOL = 24
MAXDD_RESERVE_POOL = 24
OUTSIDE_RELIEF_POOL = 16
OUTSIDE_RESERVE_POOL = 16
BEAM_WIDTH = 8
MAX_MUTATION_DEPTH = 8

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
        raise ValueError("V43 requires finite profit factor")
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
        len(node.plan),
        _signature(node.plan),
    )


def _seed_from_row(row: dict[str, Any]) -> v2.ActionSeed:
    return v2.ActionSeed(
        symbol=str(row["symbol"]),
        entry_at=str(row["entry_at"]),
        action=str(row["action"]),
        source_dynamic_total_delta_r=str(row["dynamic_total_delta_r"]),
        source_legacy_dd_relief_r=str(row["legacy_dd_relief_r"]),
        source_rollout_profit_factor=(
            None
            if row.get("rollout_profit_factor") is None
            else str(row["rollout_profit_factor"])
        ),
        source_in_max_dd_descent=bool(
            row["entrant_in_surface_max_dd_descent"]
        ),
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


def _frozen_global_pool(
    transition_path: Path,
) -> tuple[tuple[v2.ActionSeed, ...], dict[str, int]]:
    rows: list[v2.ActionSeed] = []
    with transition_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            payload = json.loads(raw)
            if payload["period"] != PERIOD:
                continue
            rows.append(_seed_from_row(payload))

    if not rows:
        raise ValueError("V43 transition corpus has no Reserved rows")

    inside = tuple(seed for seed in rows if seed.source_in_max_dd_descent)
    outside = tuple(seed for seed in rows if not seed.source_in_max_dd_descent)

    selected: dict[tuple[str, str, str], v2.ActionSeed] = {}

    def add_many(items: tuple[v2.ActionSeed, ...]) -> None:
        for seed in items:
            selected[(seed.symbol, seed.entry_at, seed.action)] = seed

    inside_relief = tuple(sorted(inside, key=_seed_sort_relief))[
        :MAXDD_RELIEF_POOL
    ]
    inside_reserve = tuple(sorted(inside, key=_seed_sort_reserve))[
        :MAXDD_RESERVE_POOL
    ]
    outside_relief = tuple(sorted(outside, key=_seed_sort_relief))[
        :OUTSIDE_RELIEF_POOL
    ]
    outside_reserve = tuple(sorted(outside, key=_seed_sort_reserve))[
        :OUTSIDE_RESERVE_POOL
    ]

    add_many(inside_relief)
    add_many(inside_reserve)
    add_many(outside_relief)
    add_many(outside_reserve)

    pool = tuple(
        sorted(
            selected.values(),
            key=lambda seed: (
                milestone._aware(seed.entry_at),
                seed.symbol,
                v2._mode_order(seed.action),
            ),
        )
    )
    metadata = {
        "transition_rows": len(rows),
        "inside_max_dd_rows": len(inside),
        "outside_max_dd_rows": len(outside),
        "selected_inside_relief": len(inside_relief),
        "selected_inside_reserve": len(inside_reserve),
        "selected_outside_relief": len(outside_relief),
        "selected_outside_reserve": len(outside_reserve),
        "unique_pool_size": len(pool),
    }
    return pool, metadata


def _latest_entry_at(plan: Plan) -> Any | None:
    if not plan:
        return None
    return max(milestone._aware(entry_at) for _symbol, entry_at in plan)


def _mutations(
    plan: Plan,
    *,
    pool: tuple[v2.ActionSeed, ...],
) -> tuple[tuple[str, Plan], ...]:
    result: list[tuple[str, Plan]] = []
    latest = _latest_entry_at(plan)

    for seed in pool:
        key = (seed.symbol, seed.entry_at)
        prior = plan.get(key)

        if prior is not None:
            if prior == seed.action:
                continue
            child = dict(plan)
            child[key] = seed.action
            result.append(
                (
                    f"REPLACE:{seed.symbol}:{seed.entry_at}:"
                    f"{prior}->{seed.action}",
                    child,
                )
            )
            continue

        seed_time = milestone._aware(seed.entry_at)
        if latest is not None and seed_time <= latest:
            continue

        child = dict(plan)
        child[key] = seed.action
        result.append(
            (
                f"ADD:{seed.symbol}:{seed.entry_at}:{seed.action}",
                child,
            )
        )

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
            "V43 exact replay did not apply every planned intervention"
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
) -> tuple[dict[str, Any], tuple[SearchNode, ...]]:
    (
        ledgers,
        contexts,
        contextual_model,
        _reserve_seeds,
        _relief_seeds,
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

    pool, pool_metadata = _frozen_global_pool(transition_path)
    if not pool or len(pool) > 80:
        raise ValueError("V43 frozen pool size outside predeclared bound")

    previous_simultaneous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        start_plan: Plan = {}
        start_metrics = _replay(
            period=PERIOD,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            plan=start_plan,
        )
        if start_metrics != baseline:
            raise ValueError("V43 empty exact replay must reproduce Surface")
        if int(start_metrics["trades"]) != 1088:
            raise ValueError("V43 Surface entrant count drift")

        start = SearchNode(
            depth=0,
            plan=start_plan,
            metrics=start_metrics,
            parent_signature=None,
            mutation="START_SURFACE_EMPTY_PLAN",
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

        report: dict[str, Any] = {
            "identity": IDENTITY,
            "period": PERIOD,
            "predeclaration_comment_ids": [5882543976, 5882555652],
            "evaluation": "EXACT_GLOBAL_CHRONOLOGICAL_EPISODE_SEQUENCE_FEASIBILITY",
            "start_plan": "SURFACE_EMPTY_INTERVENTION_PLAN",
            "start_intervention_count": 0,
            "frozen_pool_contract": {
                "maxdd_relief": MAXDD_RELIEF_POOL,
                "maxdd_reserve": MAXDD_RESERVE_POOL,
                "outside_relief": OUTSIDE_RELIEF_POOL,
                "outside_reserve": OUTSIDE_RESERVE_POOL,
                **pool_metadata,
            },
            "beam_width": BEAM_WIDTH,
            "max_mutation_depth": MAX_MUTATION_DEPTH,
            "allowed_mutations": ["ADD_CHRONOLOGICALLY", "REPLACE_EXISTING"],
            "canonical_chronological_addition": True,
            "drop_mutation_allowed": False,
            "exact_full_causal_replay": True,
            "same_existing_action_geometry_only": True,
            "outcome_aware_diagnostic": True,
            "runtime_policy_candidate": False,
            "sampling": False,
            "threshold_grid_searched": False,
            "sizing_changed": False,
            "entry_changed": False,
            "stop_target_changed": False,
            "new_protection_geometry_created": False,
            "fresh_holdout_opened": False,
            "baseline": baseline,
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
                "GLOBAL_EPISODE_SEQUENCE_FEASIBILITY_ESTABLISHED"
                if passed
                else "GLOBAL_BOUNDED_EPISODE_SEQUENCE_FALSIFIED"
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
    stem = "capitalizer-reserved-global-episode-sequence-beam-v43"
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
    )
    write_report(report, trace, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
