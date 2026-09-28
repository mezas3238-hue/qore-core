"""Distributed/checkpointable executor for the Capitalizer V2 diagnostic.

This runner preserves the exact V2 economic law. Candidate extensions are evaluated
with V2's own exact causal replay, distributed across forked worker processes, and
the globally best admissible candidate is selected with the original deterministic
rank. The selected candidate is replayed once in the parent before commit.

The runner is diagnostic/outcome-aware only. It is not a runtime policy candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_counterfactual_portfolio_episode_simulator_v1 as simulator,
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
    capitalizer_portfolio_drawdown_feasibility_episode_anatomy_v1 as anatomy,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_V2_DISTRIBUTED_CHECKPOINT_RUNNER_V1"
CHECKPOINT_VERSION = 1
_WORKER_STATE: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CandidateProbe:
    seed: v2.ActionSeed
    metrics: dict[str, Any] | None
    invalid: bool
    replayed_trades: int


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed_key(seed: v2.ActionSeed) -> tuple[str, str, str]:
    return (seed.symbol, seed.entry_at, seed.action)


def _probe_seed(seed: v2.ActionSeed) -> CandidateProbe:
    state = _WORKER_STATE
    if state is None:
        raise RuntimeError("distributed V2 worker state unavailable")
    try:
        (
            metrics,
            _ledger,
            _records,
            _decisions,
            _applied,
            newly_replayed,
            replayed_trades,
        ) = v2._evaluate_extension(
            period=state["period"],
            ledgers=state["ledgers"],
            contexts=state["contexts"],
            contextual_model=state["contextual_model"],
            ordered=state["ordered"],
            modes=state["modes"],
            order_index=state["order_index"],
            plan=state["plan"],
            current_ledger=state["current_ledger"],
            current_records=state["current_records"],
            current_decisions=state["current_decisions"],
            current_applied=state["current_applied"],
            iteration_cache={},
            seed=seed,
        )
    except sequence_v1.InvalidPlanError:
        return CandidateProbe(
            seed=seed,
            metrics=None,
            invalid=True,
            replayed_trades=0,
        )
    if not newly_replayed:
        raise RuntimeError("fresh distributed candidate unexpectedly hit cache")
    return CandidateProbe(
        seed=seed,
        metrics=metrics,
        invalid=False,
        replayed_trades=replayed_trades,
    )


def _evaluate_batch(
    seeds: tuple[v2.ActionSeed, ...],
    *,
    state: dict[str, Any],
    workers: int,
) -> tuple[CandidateProbe, ...]:
    if not seeds:
        return ()
    global _WORKER_STATE
    _WORKER_STATE = state
    try:
        if workers <= 1 or "fork" not in multiprocessing.get_all_start_methods():
            return tuple(_probe_seed(seed) for seed in seeds)
        context = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
        ) as executor:
            return tuple(executor.map(_probe_seed, seeds, chunksize=1))
    finally:
        _WORKER_STATE = None


def _select_next_probe(
    *,
    relief_probes: tuple[CandidateProbe, ...],
    reserve_probes: tuple[CandidateProbe, ...],
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> tuple[str, CandidateProbe] | None:
    relief = tuple(
        probe
        for probe in relief_probes
        if not probe.invalid
        and probe.metrics is not None
        and v2._relief_admissible(
            probe.metrics,
            baseline=baseline,
            current=current,
        )
    )
    if relief:
        return (
            "RELIEF",
            min(
                relief,
                key=lambda probe: v2._relief_rank(
                    probe.metrics or {},
                    probe.seed,
                ),
            ),
        )

    reserve = tuple(
        probe
        for probe in reserve_probes
        if not probe.invalid
        and probe.metrics is not None
        and v2._reserve_admissible(
            probe.metrics,
            baseline=baseline,
            current=current,
        )
    )
    if reserve:
        return (
            "RESERVE",
            min(
                reserve,
                key=lambda probe: v2._reserve_rank(
                    probe.metrics or {},
                    probe.seed,
                ),
            ),
        )
    return None


def _write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _checkpoint_payload(
    *,
    period: str,
    transition_sha256: str,
    baseline: dict[str, Any],
    current: dict[str, Any],
    steps: list[v2.V2Step],
    replay_evaluations: int,
    replayed_trade_evaluations: int,
    invalid_trials: int,
    complete: bool,
    stop_reason: str,
) -> dict[str, Any]:
    return {
        "identity": IDENTITY,
        "checkpoint_version": CHECKPOINT_VERSION,
        "period": period,
        "transition_sha256": transition_sha256,
        "surface": baseline,
        "current_metrics": current,
        "steps": [asdict(step) for step in steps],
        "replay_evaluations": replay_evaluations,
        "replayed_trade_evaluations": replayed_trade_evaluations,
        "invalid_after_feedback_trials": invalid_trials,
        "complete": complete,
        "stop_reason": stop_reason,
        "candidate_count": 0,
        "trader_certified": False,
    }


def _load_checkpoint(
    path: Path,
    *,
    period: str,
    transition_sha256: str,
    baseline: dict[str, Any],
) -> tuple[
    dict[tuple[str, str], str],
    list[v2.V2Step],
    int,
    int,
    int,
    dict[str, Any] | None,
]:
    if not path.exists():
        return {}, [], 0, 0, 0, None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["identity"] != IDENTITY:
        raise ValueError("distributed V2 checkpoint identity mismatch")
    if int(payload["checkpoint_version"]) != CHECKPOINT_VERSION:
        raise ValueError("distributed V2 checkpoint version mismatch")
    if payload["period"] != period:
        raise ValueError("distributed V2 checkpoint period mismatch")
    if payload["transition_sha256"] != transition_sha256:
        raise ValueError("distributed V2 transition evidence drift")
    if payload["surface"] != baseline:
        raise ValueError("distributed V2 Surface drift on resume")

    steps = [v2.V2Step(**row) for row in payload["steps"]]
    plan: dict[tuple[str, str], str] = {}
    for step in steps:
        key = (step.symbol, step.entry_at)
        if key in plan:
            raise ValueError("distributed V2 checkpoint duplicate entrant")
        plan[key] = step.action
    return (
        plan,
        steps,
        int(payload["replay_evaluations"]),
        int(payload["replayed_trade_evaluations"]),
        int(payload["invalid_after_feedback_trials"]),
        payload["current_metrics"],
    )


def _prepare_period(
    *,
    period: str,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    transition_path: Path,
) -> tuple[
    dict[str, tuple[milestone.SimulatedTrade, ...]],
    dict[tuple[str, str], Any],
    dict[str, Any],
    tuple[v2.ActionSeed, ...],
    tuple[v2.ActionSeed, ...],
    dict[str, Any],
    dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
    tuple[milestone.SimulatedTrade, ...],
    dict[tuple[str, str], int],
    dict[tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]],
]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    if period not in windows:
        raise ValueError(f"unknown distributed V2 period: {period}")

    simultaneous: dict[
        tuple[str, str, str],
        tuple[milestone.SimulatedTrade, ...],
    ] = {}
    for current_period, (period_ledgers, _period_contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(
                period=current_period,
                ledgers=period_ledgers,
            )
        )

    ledgers, contexts = windows[period]
    control, _control_ledger, _surface_decisions = anatomy._surface_ledger(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    baseline = control["metrics"]
    baseline_pf = baseline["profit_factor"]
    if baseline_pf is None:
        raise ValueError("distributed V2 Surface profit factor unavailable")

    reserve_seeds, relief_seeds = v2._load_seeds(
        transition_path,
        period=period,
        baseline_profit_factor=baseline_pf,
    )
    if not reserve_seeds or not relief_seeds:
        raise ValueError("distributed V2 seed set unexpectedly empty")

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
    return (
        ledgers,
        contexts,
        contextual_model,
        reserve_seeds,
        relief_seeds,
        baseline,
        modes,
        ordered,
        order_index,
        simultaneous,
    )


def run_period(
    *,
    period: str,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    transition_path: Path,
    checkpoint_path: Path,
    workers: int,
    soft_budget_minutes: int,
) -> tuple[dict[str, Any], tuple[v2.V2Step, ...]]:
    if workers < 1:
        raise ValueError("workers must be >= 1")
    transition_sha256 = _sha256(transition_path)
    (
        ledgers,
        contexts,
        contextual_model,
        reserve_seeds,
        relief_seeds,
        baseline,
        modes,
        ordered,
        order_index,
        simultaneous,
    ) = _prepare_period(
        period=period,
        development_root=development_root,
        validation_root=validation_root,
        reserved_root=reserved_root,
        development_validation_context_root=(
            development_validation_context_root
        ),
        reserved_context_root=reserved_context_root,
        transition_path=transition_path,
    )

    previous_simultaneous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        (
            plan,
            steps,
            replay_evaluations,
            replayed_trade_evaluations,
            invalid_trials,
            checkpoint_metrics,
        ) = _load_checkpoint(
            checkpoint_path,
            period=period,
            transition_sha256=transition_sha256,
            baseline=baseline,
        )

        current_ledger, current_decisions, current_applied = (
            sequence_v1._replay_plan(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                plan=plan,
            )
        )
        current_records = simulator._baseline_records(
            ordered=ordered,
            decisions=current_decisions,
            modes=modes,
            contexts=contexts,
        )
        current = milestone._metrics(current_ledger)
        if checkpoint_metrics is not None and current != checkpoint_metrics:
            raise ValueError("distributed V2 checkpoint replay drift")

        start = time.monotonic()
        stop_reason = "NO_REACHABLE_RESERVE_OR_RELIEF_EXTENSION"
        complete = False

        while not v2._full_gate(
            current,
            baseline=baseline,
            intervention_count=len(plan),
        ):
            if (
                soft_budget_minutes > 0
                and time.monotonic() - start
                >= soft_budget_minutes * 60
            ):
                stop_reason = "SOFT_BUDGET_REACHED"
                break

            state = {
                "period": period,
                "ledgers": ledgers,
                "contexts": contexts,
                "contextual_model": contextual_model,
                "ordered": ordered,
                "modes": modes,
                "order_index": order_index,
                "plan": plan,
                "current_ledger": current_ledger,
                "current_records": current_records,
                "current_decisions": current_decisions,
                "current_applied": current_applied,
            }
            remaining_relief = tuple(
                seed
                for seed in relief_seeds
                if (seed.symbol, seed.entry_at) not in plan
            )
            relief_probes = _evaluate_batch(
                remaining_relief,
                state=state,
                workers=workers,
            )
            invalid_trials += sum(probe.invalid for probe in relief_probes)
            replay_evaluations += sum(
                not probe.invalid for probe in relief_probes
            )
            replayed_trade_evaluations += sum(
                probe.replayed_trades
                for probe in relief_probes
                if not probe.invalid
            )

            successful_relief = {
                _seed_key(probe.seed): probe
                for probe in relief_probes
                if not probe.invalid
            }
            remaining_reserve = tuple(
                seed
                for seed in reserve_seeds
                if (seed.symbol, seed.entry_at) not in plan
            )
            reserve_probes: tuple[CandidateProbe, ...] = ()
            relief_admissible = tuple(
                probe
                for probe in relief_probes
                if not probe.invalid
                and probe.metrics is not None
                and v2._relief_admissible(
                    probe.metrics,
                    baseline=baseline,
                    current=current,
                )
            )
            if relief_admissible:
                selection = _select_next_probe(
                    relief_probes=relief_probes,
                    reserve_probes=(),
                    baseline=baseline,
                    current=current,
                )
            else:
                reused: list[CandidateProbe] = []
                to_evaluate: list[v2.ActionSeed] = []
                for seed in remaining_reserve:
                    cached = successful_relief.get(_seed_key(seed))
                    if cached is None:
                        to_evaluate.append(seed)
                    else:
                        reused.append(cached)
                new_reserve = _evaluate_batch(
                    tuple(to_evaluate),
                    state=state,
                    workers=workers,
                )
                invalid_trials += sum(probe.invalid for probe in new_reserve)
                replay_evaluations += sum(
                    not probe.invalid for probe in new_reserve
                )
                replayed_trade_evaluations += sum(
                    probe.replayed_trades
                    for probe in new_reserve
                    if not probe.invalid
                )
                reserve_probes = tuple(reused) + new_reserve
                selection = _select_next_probe(
                    relief_probes=relief_probes,
                    reserve_probes=reserve_probes,
                    baseline=baseline,
                    current=current,
                )

            if selection is None:
                stop_reason = "NO_REACHABLE_RESERVE_OR_RELIEF_EXTENSION"
                complete = True
                break

            role, selected_probe = selection
            materialized = v2._evaluate_extension(
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
                iteration_cache={},
                seed=selected_probe.seed,
            )
            (
                resulting,
                resulting_ledger,
                resulting_records,
                resulting_decisions,
                resulting_applied,
                _newly_replayed,
                _replayed_trades,
            ) = materialized
            if selected_probe.metrics != resulting:
                raise ValueError("distributed V2 worker/parent replay drift")

            seed = selected_probe.seed
            key = (seed.symbol, seed.entry_at)
            prior = current
            plan[key] = seed.action
            current = resulting
            current_ledger = resulting_ledger
            current_records = resulting_records
            current_decisions = resulting_decisions
            current_applied = resulting_applied
            current_surface, family, trigger_at = current_applied[key]
            steps.append(
                v2.V2Step(
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
            _write_checkpoint(
                checkpoint_path,
                _checkpoint_payload(
                    period=period,
                    transition_sha256=transition_sha256,
                    baseline=baseline,
                    current=current,
                    steps=steps,
                    replay_evaluations=replay_evaluations,
                    replayed_trade_evaluations=(
                        replayed_trade_evaluations
                    ),
                    invalid_trials=invalid_trials,
                    complete=False,
                    stop_reason="CHECKPOINT_AFTER_COMMIT",
                ),
            )

        if v2._full_gate(
            current,
            baseline=baseline,
            intervention_count=len(plan),
        ):
            complete = True
            stop_reason = "FULL_GATE_REACHED"

        checkpoint = _checkpoint_payload(
            period=period,
            transition_sha256=transition_sha256,
            baseline=baseline,
            current=current,
            steps=steps,
            replay_evaluations=replay_evaluations,
            replayed_trade_evaluations=replayed_trade_evaluations,
            invalid_trials=invalid_trials,
            complete=complete,
            stop_reason=stop_reason,
        )
        _write_checkpoint(checkpoint_path, checkpoint)

        result = {
            "period": period,
            "surface": baseline,
            "reserve_seed_count": len(reserve_seeds),
            "reserve_seed_entrant_count": len(
                {(seed.symbol, seed.entry_at) for seed in reserve_seeds}
            ),
            "relief_seed_count": len(relief_seeds),
            "relief_seed_entrant_count": len(
                {(seed.symbol, seed.entry_at) for seed in relief_seeds}
            ),
            "replay_evaluations": replay_evaluations,
            "replayed_trade_evaluations": replayed_trade_evaluations,
            "causal_prefix_reuse_enabled": True,
            "distributed_candidate_evaluation": workers > 1,
            "worker_count": workers,
            "checkpoint_after_each_committed_action": True,
            "resume_exact_from_committed_plan": True,
            "invalid_after_feedback_trials": invalid_trials,
            "committed_intervention_count": len(plan),
            "reserve_step_count": sum(
                step.role == "RESERVE" for step in steps
            ),
            "relief_step_count": sum(
                step.role == "RELIEF" for step in steps
            ),
            "final_metrics": current,
            "full_gate_passed": v2._full_gate(
                current,
                baseline=baseline,
                intervention_count=len(plan),
            ),
            "density_retention": "1",
            "same_entrant_identities": True,
            "complete": complete,
            "stop_reason": stop_reason,
        }
        report = {
            "identity": IDENTITY,
            "economic_identity": v2.IDENTITY,
            "evaluation": "DISTRIBUTED_EXACT_V2_WITH_CHECKPOINT_RESUME",
            "period": period,
            "outcome_aware_diagnostic": True,
            "runtime_policy_candidate": False,
            "same_reserve_seed_law": True,
            "same_relief_seed_law": True,
            "same_relief_first_law": True,
            "same_deterministic_rank": True,
            "same_exact_dynamic_replay": True,
            "sampling": False,
            "economic_pruning": False,
            "admission_changed": False,
            "sizing_changed": False,
            "new_protection_geometry_created": False,
            "result": result,
            "candidate_count": 0,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
        }
        return report, tuple(steps)
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous_simultaneous)


def write_report(
    report: dict[str, Any],
    steps: tuple[v2.V2Step, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-v2-distributed-checkpoint-runner-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-steps.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for step in steps:
            handle.write(json.dumps(asdict(step), sort_keys=True) + "\n")


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
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, os.cpu_count() or 1),
    )
    parser.add_argument("--soft-budget-minutes", type=int, default=0)
    args = parser.parse_args()

    report, steps = run_period(
        period=args.period,
        development_root=args.development_root,
        validation_root=args.validation_root,
        reserved_root=args.reserved_root,
        development_validation_context_root=(
            args.development_validation_context_root
        ),
        reserved_context_root=args.reserved_context_root,
        transition_path=args.transition_path,
        checkpoint_path=args.checkpoint,
        workers=args.workers,
        soft_budget_minutes=args.soft_budget_minutes,
    )
    write_report(report, steps, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
