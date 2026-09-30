"""Conservative dynamic multi-intervention feasibility oracle.

This is diagnostic infrastructure, not a runtime policy.  It composes only
one-step interventions that the authoritative counterfactual episode simulator
already showed to improve both Total-R and legacy DD inside Surface's actual
maximum-DD descent.  After each committed intervention the whole period is
replayed causally and every later Surface mode/multiplier is recomputed.

A candidate extension is admitted only when it keeps PF and Total-R at or above
the original Surface control, keeps losing streak no worse, and strictly lowers
DD versus the current plan.  No temporary edge sacrifice is borrowed from the
future.
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

IDENTITY = "QORE_CAPITALIZER_DYNAMIC_EPISODE_SEQUENCE_FEASIBILITY_V1"


@dataclass(frozen=True, slots=True)
class SeedAction:
    symbol: str
    entry_at: str
    action: str
    source_dynamic_total_delta_r: str
    source_legacy_dd_relief_r: str


@dataclass(frozen=True, slots=True)
class SequenceStep:
    step: int
    symbol: str
    entry_at: str
    action: str
    prior_dd_r: str
    resulting_dd_r: str
    dd_relief_from_prior_r: str
    resulting_total_r: str
    resulting_profit_factor: str | None
    resulting_losing_streak: int
    current_surface_mode_at_application: str
    current_trigger_family_at_application: str
    current_trigger_at: str


class InvalidPlanError(ValueError):
    """Plan cannot be applied causally after prior feedback."""


def _load_seeds(
    transition_path: Path,
    *,
    period: str,
) -> tuple[SeedAction, ...]:
    result: dict[tuple[str, str, str], SeedAction] = {}
    with transition_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row["period"] != period:
                continue
            if not row["entrant_in_surface_max_dd_descent"]:
                continue
            if not row["improves_total_r_and_legacy_dd"]:
                continue
            seed = SeedAction(
                symbol=row["symbol"],
                entry_at=row["entry_at"],
                action=row["action"],
                source_dynamic_total_delta_r=row["dynamic_total_delta_r"],
                source_legacy_dd_relief_r=row["legacy_dd_relief_r"],
            )
            result[(seed.symbol, seed.entry_at, seed.action)] = seed
    return tuple(
        sorted(
            result.values(),
            key=lambda row: (
                milestone._aware(row.entry_at),
                row.symbol,
                tuple(mode.value for mode in milestone.ProtectionMode).index(
                    row.action
                ),
            ),
        )
    )


def _replay_plan(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    plan: dict[tuple[str, str], str],
) -> tuple[
    tuple[milestone.SimulatedTrade, ...],
    tuple[simulator.ReplayDecision, ...],
    dict[tuple[str, str], tuple[str, str, str]],
]:
    modes = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = simulator._ordered(
        ledgers[milestone.ProtectionMode.ORIGINAL.value]
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[simulator.ReplayDecision] = []
    applied: dict[tuple[str, str], tuple[str, str, str]] = {}

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        pretrade = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        selected_mode = pretrade.mode
        action = plan.get(key)

        if action is not None:
            family = v30._mode_family(pretrade.mode)
            if family is None:
                raise InvalidPlanError(
                    f"planned key has no current trigger family: {key}"
                )
            surface = modes[pretrade.mode][key]
            trigger_at = surface.first_protection_at
            if trigger_at is None:
                raise InvalidPlanError(
                    f"planned key has no actual current trigger: {key}"
                )
            if action == pretrade.mode:
                raise InvalidPlanError(
                    f"planned action became current Surface no-op: {key}"
                )
            if action not in v30._eligible_actions(family):
                raise InvalidPlanError(
                    f"planned action no longer reachable after feedback: {key}"
                )
            v30._assert_common_path(
                key=key,
                trigger_at=trigger_at,
                actions=(action,),
                modes=modes,
            )
            selected_mode = action
            applied[key] = (pretrade.mode, family, trigger_at)

        selected = modes[selected_mode][key]
        scaled_r = (
            Decimal(selected.realized_gross_r) * pretrade.base_multiplier
        )
        chosen.append(replace(selected, realized_gross_r=str(scaled_r)))
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

    if set(applied) != set(plan):
        missing = set(plan) - set(applied)
        raise InvalidPlanError(f"plan keys not applied: {sorted(missing)}")
    return tuple(chosen), tuple(decisions), applied


def _pf_at_least(
    candidate: str | None,
    baseline: str | None,
) -> bool:
    return simulator._pf_at_least(candidate, baseline)


def _full_gate(
    metrics: dict[str, Any],
    *,
    baseline: dict[str, Any],
    intervention_count: int,
) -> bool:
    return (
        intervention_count > 0
        and _pf_at_least(
            metrics["profit_factor"],
            baseline["profit_factor"],
        )
        and Decimal(metrics["total_r"]) >= Decimal(baseline["total_r"])
        and Decimal(metrics["max_drawdown_r"])
        < Decimal(baseline["max_drawdown_r"])
        and Decimal(metrics["max_drawdown_r"]) <= Decimal("6")
        and int(metrics["max_losing_streak"])
        <= int(baseline["max_losing_streak"])
        and int(metrics["trades"]) == int(baseline["trades"])
    )


def _admissible_extension(
    metrics: dict[str, Any],
    *,
    baseline: dict[str, Any],
    current_dd: Decimal,
) -> bool:
    return (
        _pf_at_least(
            metrics["profit_factor"],
            baseline["profit_factor"],
        )
        and Decimal(metrics["total_r"]) >= Decimal(baseline["total_r"])
        and int(metrics["max_losing_streak"])
        <= int(baseline["max_losing_streak"])
        and Decimal(metrics["max_drawdown_r"]) < current_dd
        and int(metrics["trades"]) == int(baseline["trades"])
    )


def _candidate_rank(
    *,
    metrics: dict[str, Any],
    seed: SeedAction,
) -> tuple[Any, ...]:
    pf = metrics["profit_factor"]
    pf_value = Decimal("-Infinity") if pf is None else Decimal(pf)
    mode_order = tuple(
        mode.value for mode in milestone.ProtectionMode
    ).index(seed.action)
    return (
        Decimal(metrics["max_drawdown_r"]),
        -Decimal(metrics["total_r"]),
        -pf_value,
        milestone._aware(seed.entry_at),
        seed.symbol,
        mode_order,
    )


def _run_period(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    seeds: tuple[SeedAction, ...],
) -> tuple[dict[str, Any], tuple[SequenceStep, ...]]:
    control, _control_ledger, _surface_decisions = anatomy._surface_ledger(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    baseline_ledger, _baseline_decisions, _baseline_applied = _replay_plan(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
        plan={},
    )
    baseline_metrics = milestone._metrics(baseline_ledger)
    if baseline_metrics != control["metrics"]:
        raise ValueError("sequence feasibility empty-plan Surface drift")

    plan: dict[tuple[str, str], str] = {}
    remaining = list(seeds)
    steps: list[SequenceStep] = []
    current_metrics = baseline_metrics
    invalid_extensions = 0
    evaluated_extensions = 0

    while remaining and not _full_gate(
        current_metrics,
        baseline=baseline_metrics,
        intervention_count=len(plan),
    ):
        current_dd = Decimal(current_metrics["max_drawdown_r"])
        candidates: list[
            tuple[
                tuple[Any, ...],
                SeedAction,
                dict[str, Any],
                dict[tuple[str, str], tuple[str, str, str]],
            ]
        ] = []

        for seed in remaining:
            key = (seed.symbol, seed.entry_at)
            if key in plan:
                continue
            trial_plan = dict(plan)
            trial_plan[key] = seed.action
            evaluated_extensions += 1
            try:
                ledger, _decisions, applied = _replay_plan(
                    period=period,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                    plan=trial_plan,
                )
            except InvalidPlanError:
                invalid_extensions += 1
                continue
            metrics = milestone._metrics(ledger)
            if not _admissible_extension(
                metrics,
                baseline=baseline_metrics,
                current_dd=current_dd,
            ):
                continue
            candidates.append(
                (
                    _candidate_rank(metrics=metrics, seed=seed),
                    seed,
                    metrics,
                    applied,
                )
            )

        if not candidates:
            break

        _rank, chosen_seed, chosen_metrics, applied = min(
            candidates,
            key=lambda row: row[0],
        )
        key = (chosen_seed.symbol, chosen_seed.entry_at)
        prior_dd = Decimal(current_metrics["max_drawdown_r"])
        plan[key] = chosen_seed.action
        current_metrics = chosen_metrics
        current_surface, family, trigger_at = applied[key]
        resulting_dd = Decimal(current_metrics["max_drawdown_r"])
        steps.append(
            SequenceStep(
                step=len(steps) + 1,
                symbol=chosen_seed.symbol,
                entry_at=chosen_seed.entry_at,
                action=chosen_seed.action,
                prior_dd_r=str(prior_dd),
                resulting_dd_r=str(resulting_dd),
                dd_relief_from_prior_r=str(prior_dd - resulting_dd),
                resulting_total_r=current_metrics["total_r"],
                resulting_profit_factor=current_metrics["profit_factor"],
                resulting_losing_streak=int(
                    current_metrics["max_losing_streak"]
                ),
                current_surface_mode_at_application=current_surface,
                current_trigger_family_at_application=family,
                current_trigger_at=trigger_at,
            )
        )
        remaining = [
            seed
            for seed in remaining
            if (seed.symbol, seed.entry_at) != key
        ]

    passed = _full_gate(
        current_metrics,
        baseline=baseline_metrics,
        intervention_count=len(plan),
    )
    return (
        {
            "period": period,
            "surface": baseline_metrics,
            "seed_action_count": len(seeds),
            "seed_entrant_count": len(
                {(seed.symbol, seed.entry_at) for seed in seeds}
            ),
            "evaluated_extensions": evaluated_extensions,
            "invalid_after_feedback_extensions": invalid_extensions,
            "committed_intervention_count": len(plan),
            "final_metrics": current_metrics,
            "full_gate_passed": passed,
            "density_retention": "1",
            "same_entrant_identities": True,
            "stop_reason": (
                "FULL_GATE_REACHED"
                if passed
                else "NO_MORE_CONSERVATIVE_ADMISSIBLE_EXTENSIONS"
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
) -> tuple[dict[str, Any], tuple[SequenceStep, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    if period not in windows:
        raise ValueError(f"unknown sequence-feasibility period: {period}")

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

    seeds = _load_seeds(transition_path, period=period)
    if not seeds:
        raise ValueError("sequence feasibility found no seed actions")

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        ledgers, contexts = windows[period]
        result, steps = _run_period(
            period=period,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            seeds=seeds,
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    return (
        {
            "identity": IDENTITY,
            "evaluation": (
                "CONSERVATIVE_GREEDY_DYNAMIC_MULTI_INTERVENTION_FEASIBILITY"
            ),
            "period": period,
            "seed_law": (
                "AUTHORITATIVE_SINGLE_INTERVENTION_MAX_DD_"
                "IMPROVES_TOTAL_R_AND_DD"
            ),
            "extension_gate": (
                "PF_GE_SURFACE__TOTAL_R_GE_SURFACE__LS_LE_SURFACE__"
                "DD_STRICTLY_LOWER_THAN_CURRENT"
            ),
            "outcome_aware_diagnostic": True,
            "runtime_policy_candidate": False,
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
    steps: tuple[SequenceStep, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-dynamic-episode-sequence-feasibility-v1"
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
