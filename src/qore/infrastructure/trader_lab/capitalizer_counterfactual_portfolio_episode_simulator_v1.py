"""Dynamic counterfactual portfolio episode simulator for Capitalizer.

This module is diagnostic infrastructure, not a policy.  It applies exactly one
existing protection intervention at a causal Surface first-protection trigger
and then replays every later frozen entrant through the existing V11/V10
Surface cognition.  Thus later modes, multipliers, active exposure, memory and
journey state are allowed to change causally as a consequence of the
intervention.

The empty-intervention replay must reproduce Surface exactly.  Outcome data are
used only to score counterfactual rollouts after the action boundary; no oracle
label is supplied to a runtime decision.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
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
    capitalizer_drawdown_chronology_semantics_audit_v1 as chronology,
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

IDENTITY = "QORE_CAPITALIZER_COUNTERFACTUAL_PORTFOLIO_EPISODE_SIMULATOR_V1"


@dataclass(frozen=True, slots=True)
class ReplayDecision:
    symbol: str
    session: str
    entry_at: str
    surface_hint_mode: str
    selected_mode: str
    base_multiplier: str
    scaled_realized_r: str


@dataclass(frozen=True, slots=True)
class Intervention:
    symbol: str
    entry_at: str
    trigger_at: str
    family: str
    expected_surface_mode: str
    expected_base_multiplier: str
    action: str


@dataclass(frozen=True, slots=True)
class TransitionAudit:
    period: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    trigger_at: str
    family: str
    surface_mode: str
    action: str
    base_multiplier: str
    entrant_in_surface_max_dd_descent: bool
    static_local_delta_r: str
    dynamic_total_delta_r: str
    downstream_feedback_r: str
    legacy_dd_relief_r: str
    realized_exit_batch_dd_relief_r: str
    rollout_profit_factor: str | None
    rollout_total_r: str
    rollout_legacy_dd_r: str
    rollout_realized_exit_batch_dd_r: str
    downstream_mode_change_count: int
    downstream_multiplier_change_count: int
    local_effect_sign: int
    dynamic_effect_sign: int
    feedback_changed_total_effect_sign: bool
    locally_positive_but_dynamic_negative: bool
    locally_negative_but_dynamic_positive: bool
    improves_total_r_and_legacy_dd: bool
    diagnostic_single_intervention_full_gate: bool
    identical_downstream_trajectory_short_circuit: bool
    intervention_outcome_used_for_runtime_decision: bool = False
    future_outcomes_used_for_runtime_decision: bool = False
    outcome_used_for_diagnostic_scoring: bool = True
    policy_candidate: bool = False


def _sign(value: Decimal) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _ordered(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[milestone.SimulatedTrade, ...]:
    return tuple(
        sorted(
            rows,
            key=lambda row: (milestone._aware(row.entry_at), row.symbol),
        )
    )


def _replay_period(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    intervention: Intervention | None,
    start_index: int = 0,
    prefix_chosen: tuple[milestone.SimulatedTrade, ...] = (),
    prefix_records: tuple[memory.MemoryRecord, ...] = (),
    prefix_decisions: tuple[ReplayDecision, ...] = (),
) -> tuple[
    tuple[milestone.SimulatedTrade, ...],
    tuple[ReplayDecision, ...],
]:
    modes = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = _ordered(
        ledgers[milestone.ProtectionMode.ORIGINAL.value]
    )
    if not 0 <= start_index <= len(ordered):
        raise ValueError("episode simulator start index outside ledger")
    if not (
        len(prefix_chosen)
        == len(prefix_records)
        == len(prefix_decisions)
        == start_index
    ):
        raise ValueError("episode simulator prefix length mismatch")
    chosen: list[milestone.SimulatedTrade] = list(prefix_chosen)
    records: list[memory.MemoryRecord] = list(prefix_records)
    decisions: list[ReplayDecision] = list(prefix_decisions)
    intervention_seen = False

    for trade in ordered[start_index:]:
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

        if (
            intervention is not None
            and key == (intervention.symbol, intervention.entry_at)
        ):
            if intervention_seen:
                raise ValueError("episode simulator duplicated intervention")
            intervention_seen = True
            if pretrade.mode != intervention.expected_surface_mode:
                raise ValueError(
                    "episode simulator intervention Surface mode drift"
                )
            if pretrade.base_multiplier != Decimal(
                intervention.expected_base_multiplier
            ):
                raise ValueError(
                    "episode simulator intervention multiplier drift"
                )
            surface = modes[pretrade.mode][key]
            if surface.first_protection_at is None:
                raise ValueError(
                    "episode simulator missing Surface trigger timestamp"
                )
            if milestone._aware(surface.first_protection_at) != milestone._aware(
                intervention.trigger_at
            ):
                raise ValueError(
                    "episode simulator Surface trigger timestamp drift"
                )
            v30._assert_common_path(
                key=key,
                trigger_at=intervention.trigger_at,
                actions=(intervention.action,),
                modes=modes,
            )
            if intervention.action not in v30._eligible_actions(
                intervention.family
            ):
                raise ValueError(
                    "episode simulator action outside reachable set"
                )
            selected_mode = intervention.action

        selected = modes[selected_mode][key]
        scaled_r = (
            Decimal(selected.realized_gross_r) * pretrade.base_multiplier
        )
        scaled = replace(selected, realized_gross_r=str(scaled_r))
        chosen.append(scaled)
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
            ReplayDecision(
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                surface_hint_mode=pretrade.mode,
                selected_mode=selected_mode,
                base_multiplier=str(pretrade.base_multiplier),
                scaled_realized_r=str(scaled_r),
            )
        )

    if intervention is not None and not intervention_seen:
        raise ValueError("episode simulator intervention key not found")
    return tuple(chosen), tuple(decisions)


def _baseline_records(
    *,
    ordered: tuple[milestone.SimulatedTrade, ...],
    decisions: tuple[ReplayDecision, ...],
    modes: dict[
        str,
        dict[tuple[str, str], milestone.SimulatedTrade],
    ],
    contexts: dict[tuple[str, str], Any],
) -> tuple[memory.MemoryRecord, ...]:
    if len(ordered) != len(decisions):
        raise ValueError("episode simulator baseline record length drift")
    records: list[memory.MemoryRecord] = []
    for trade, decision in zip(ordered, decisions, strict=True):
        key = (trade.symbol, trade.entry_at)
        selected = modes[decision.selected_mode][key]
        ctx = contexts[key]
        records.append(
            memory.MemoryRecord(
                symbol=ctx.symbol,
                session=ctx.session,
                destination_state=ctx.destination_state,
                context_signature=ctx.context_signature,
                exit_at=selected.exit_at,
                normalized_realized_r=selected.realized_gross_r,
            )
        )
    return tuple(records)


def _decision_map(
    rows: tuple[ReplayDecision, ...],
) -> dict[tuple[str, str], ReplayDecision]:
    result = {(row.symbol, row.entry_at): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("episode simulator duplicate decision identity")
    return result


def _surface_max_dd_keys(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> set[tuple[str, str]]:
    ordered = anatomy._canonical_rows(rows)
    values = tuple(Decimal(row.realized_gross_r) for row in ordered)
    episodes = anatomy._drawdown_episodes(values)
    if not episodes:
        return set()
    episode = max(
        episodes,
        key=lambda row: (Decimal(row.max_drawdown_r), -row.episode_id),
    )
    return {
        (ordered[index].symbol, ordered[index].entry_at)
        for index in range(episode.start_index, episode.trough_index + 1)
    }


def _pf_at_least(
    candidate: str | None,
    control: str | None,
) -> bool:
    if control is None:
        return candidate is None
    if candidate is None:
        return False
    return Decimal(candidate) >= Decimal(control)


def _action_summary(
    rows: tuple[TransitionAudit, ...],
) -> dict[str, Any]:
    if not rows:
        return {
            "transitions": 0,
            "improves_total_r_and_legacy_dd": 0,
            "feedback_sign_changes": 0,
            "single_intervention_full_gate": 0,
        }
    dd_reliefs = tuple(Decimal(row.legacy_dd_relief_r) for row in rows)
    total_deltas = tuple(Decimal(row.dynamic_total_delta_r) for row in rows)
    return {
        "transitions": len(rows),
        "improves_total_r_and_legacy_dd": sum(
            row.improves_total_r_and_legacy_dd for row in rows
        ),
        "feedback_sign_changes": sum(
            row.feedback_changed_total_effect_sign for row in rows
        ),
        "locally_positive_but_dynamic_negative": sum(
            row.locally_positive_but_dynamic_negative for row in rows
        ),
        "locally_negative_but_dynamic_positive": sum(
            row.locally_negative_but_dynamic_positive for row in rows
        ),
        "single_intervention_full_gate": sum(
            row.diagnostic_single_intervention_full_gate for row in rows
        ),
        "max_dynamic_total_delta_r": str(max(total_deltas)),
        "min_dynamic_total_delta_r": str(min(total_deltas)),
        "max_legacy_dd_relief_r": str(max(dd_reliefs)),
        "min_legacy_dd_relief_r": str(min(dd_reliefs)),
    }


def _period_report(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[TransitionAudit, ...]]:
    control, control_ledger, surface_decisions = anatomy._surface_ledger(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    replay_ledger, replay_decisions = _replay_period(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
        intervention=None,
    )
    control_ledger = anatomy._canonical_rows(control_ledger)
    replay_ledger = anatomy._canonical_rows(replay_ledger)

    if milestone._metrics(replay_ledger) != control["metrics"]:
        raise ValueError("episode simulator empty replay metrics drift")
    if len(replay_ledger) != len(control_ledger):
        raise ValueError("episode simulator empty replay lost entrants")

    control_by_key = {
        (row.symbol, row.entry_at): row for row in control_ledger
    }
    replay_by_key = {
        (row.symbol, row.entry_at): row for row in replay_ledger
    }
    baseline_decision_map = _decision_map(replay_decisions)
    if set(control_by_key) != set(replay_by_key):
        raise ValueError("episode simulator empty replay identity drift")

    for key, decision in surface_decisions.items():
        replay = baseline_decision_map[key]
        if replay.surface_hint_mode != decision.surface_mode:
            raise ValueError(
                "episode simulator empty replay Surface mode mismatch"
            )
        if Decimal(replay.base_multiplier) != Decimal(
            decision.base_multiplier
        ):
            raise ValueError(
                "episode simulator empty replay multiplier mismatch"
            )
        if Decimal(replay.scaled_realized_r) != Decimal(
            control_by_key[key].realized_gross_r
        ):
            raise ValueError(
                "episode simulator empty replay realized-R mismatch"
            )

    baseline_metrics = milestone._metrics(replay_ledger)
    baseline_exit = chronology._exit_batch_metrics(replay_ledger)
    baseline_dd = Decimal(baseline_metrics["max_drawdown_r"])
    baseline_exit_dd = Decimal(baseline_exit["max_drawdown_r"])
    baseline_total = Decimal(baseline_metrics["total_r"])
    max_dd_keys = _surface_max_dd_keys(replay_ledger)

    modes = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered_original = _ordered(
        ledgers[milestone.ProtectionMode.ORIGINAL.value]
    )
    order_index = {
        (row.symbol, row.entry_at): index
        for index, row in enumerate(ordered_original)
    }
    baseline_records = _baseline_records(
        ordered=ordered_original,
        decisions=replay_decisions,
        modes=modes,
        contexts=contexts,
    )

    audits: list[TransitionAudit] = []
    state_count = 0
    no_actual_trigger_count = 0
    short_circuit_count = 0
    for key, decision in surface_decisions.items():
        surface_mode = str(decision.surface_mode)
        family = v30._mode_family(surface_mode)
        if family is None:
            continue
        surface_raw = modes[surface_mode][key]
        trigger_at = surface_raw.first_protection_at
        if trigger_at is None:
            no_actual_trigger_count += 1
            continue
        state_count += 1
        reachable = v30._eligible_actions(family)
        v30._assert_common_path(
            key=key,
            trigger_at=trigger_at,
            actions=reachable,
            modes=modes,
        )
        baseline_trade = control_by_key[key]
        baseline_local_r = Decimal(baseline_trade.realized_gross_r)
        baseline_index = order_index[key]

        for action in reachable:
            if action == surface_mode:
                continue
            spec = Intervention(
                symbol=key[0],
                entry_at=key[1],
                trigger_at=trigger_at,
                family=family,
                expected_surface_mode=surface_mode,
                expected_base_multiplier=decision.base_multiplier,
                action=action,
            )
            action_raw = modes[action][key]
            identical_downstream = (
                action_raw.exit_at == surface_raw.exit_at
                and Decimal(action_raw.realized_gross_r)
                == Decimal(surface_raw.realized_gross_r)
            )
            if identical_downstream:
                short_circuit_count += 1
                rollout = replay_ledger
                rollout_decisions = replay_decisions
            else:
                rollout, rollout_decisions = _replay_period(
                    period=period,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                    intervention=spec,
                    start_index=baseline_index,
                    prefix_chosen=replay_ledger[:baseline_index],
                    prefix_records=baseline_records[:baseline_index],
                    prefix_decisions=replay_decisions[:baseline_index],
                )
            rollout_metrics = milestone._metrics(rollout)
            rollout_exit = chronology._exit_batch_metrics(rollout)
            rollout_total = Decimal(rollout_metrics["total_r"])
            rollout_dd = Decimal(rollout_metrics["max_drawdown_r"])
            rollout_exit_dd = Decimal(rollout_exit["max_drawdown_r"])

            multiplier = Decimal(decision.base_multiplier)
            action_local_r = (
                Decimal(modes[action][key].realized_gross_r) * multiplier
            )
            static_delta = action_local_r - baseline_local_r
            dynamic_delta = rollout_total - baseline_total
            feedback = dynamic_delta - static_delta

            rollout_map = _decision_map(rollout_decisions)
            mode_changes = 0
            multiplier_changes = 0
            for later_key, later_index in order_index.items():
                if later_index <= baseline_index:
                    continue
                baseline_later = baseline_decision_map[later_key]
                rollout_later = rollout_map[later_key]
                mode_changes += int(
                    baseline_later.surface_hint_mode
                    != rollout_later.surface_hint_mode
                )
                multiplier_changes += int(
                    Decimal(baseline_later.base_multiplier)
                    != Decimal(rollout_later.base_multiplier)
                )

            local_sign = _sign(static_delta)
            dynamic_sign = _sign(dynamic_delta)
            dd_relief = baseline_dd - rollout_dd
            exit_dd_relief = baseline_exit_dd - rollout_exit_dd
            improves_both = dynamic_delta > 0 and dd_relief > 0
            full_gate = (
                _pf_at_least(
                    rollout_metrics["profit_factor"],
                    baseline_metrics["profit_factor"],
                )
                and rollout_total >= baseline_total
                and rollout_dd < baseline_dd
                and rollout_dd <= Decimal("6")
                and int(rollout_metrics["max_losing_streak"])
                <= int(baseline_metrics["max_losing_streak"])
            )

            original_trade = modes[
                milestone.ProtectionMode.ORIGINAL.value
            ][key]
            audits.append(
                TransitionAudit(
                    period=period,
                    symbol=key[0],
                    session=original_trade.session,
                    operating_date=original_trade.operating_date,
                    entry_at=key[1],
                    trigger_at=trigger_at,
                    family=family,
                    surface_mode=surface_mode,
                    action=action,
                    base_multiplier=decision.base_multiplier,
                    entrant_in_surface_max_dd_descent=key in max_dd_keys,
                    static_local_delta_r=str(static_delta),
                    dynamic_total_delta_r=str(dynamic_delta),
                    downstream_feedback_r=str(feedback),
                    legacy_dd_relief_r=str(dd_relief),
                    realized_exit_batch_dd_relief_r=str(exit_dd_relief),
                    rollout_profit_factor=rollout_metrics[
                        "profit_factor"
                    ],
                    rollout_total_r=rollout_metrics["total_r"],
                    rollout_legacy_dd_r=rollout_metrics[
                        "max_drawdown_r"
                    ],
                    rollout_realized_exit_batch_dd_r=str(
                        rollout_exit_dd
                    ),
                    downstream_mode_change_count=mode_changes,
                    downstream_multiplier_change_count=multiplier_changes,
                    local_effect_sign=local_sign,
                    dynamic_effect_sign=dynamic_sign,
                    feedback_changed_total_effect_sign=(
                        local_sign != dynamic_sign
                    ),
                    locally_positive_but_dynamic_negative=(
                        local_sign > 0 and dynamic_sign < 0
                    ),
                    locally_negative_but_dynamic_positive=(
                        local_sign < 0 and dynamic_sign > 0
                    ),
                    improves_total_r_and_legacy_dd=improves_both,
                    diagnostic_single_intervention_full_gate=full_gate,
                    identical_downstream_trajectory_short_circuit=(
                        identical_downstream
                    ),
                )
            )

    frozen = tuple(audits)
    by_action: dict[str, list[TransitionAudit]] = defaultdict(list)
    by_family: dict[str, list[TransitionAudit]] = defaultdict(list)
    for row in frozen:
        by_action[row.action].append(row)
        by_family[row.family].append(row)

    max_dd_rows = tuple(
        row for row in frozen if row.entrant_in_surface_max_dd_descent
    )
    full_gate_rows = tuple(
        row for row in frozen
        if row.diagnostic_single_intervention_full_gate
    )
    best_dd = (
        None
        if not frozen
        else min(Decimal(row.rollout_legacy_dd_r) for row in frozen)
    )

    return (
        {
            "period": period,
            "surface": baseline_metrics,
            "surface_realized_exit_batch_dd_r": str(baseline_exit_dd),
            "surface_trigger_state_count": state_count,
            "surface_protection_mode_without_actual_trigger_count": (
                no_actual_trigger_count
            ),
            "transition_count": len(frozen),
            "identical_downstream_trajectory_short_circuit_count": (
                short_circuit_count
            ),
            "max_dd_descent_transition_count": len(max_dd_rows),
            "feedback_sign_change_count": sum(
                row.feedback_changed_total_effect_sign for row in frozen
            ),
            "locally_positive_but_dynamic_negative_count": sum(
                row.locally_positive_but_dynamic_negative for row in frozen
            ),
            "locally_negative_but_dynamic_positive_count": sum(
                row.locally_negative_but_dynamic_positive for row in frozen
            ),
            "downstream_mode_change_transition_count": sum(
                row.downstream_mode_change_count > 0 for row in frozen
            ),
            "downstream_multiplier_change_transition_count": sum(
                row.downstream_multiplier_change_count > 0 for row in frozen
            ),
            "improves_total_r_and_legacy_dd_count": sum(
                row.improves_total_r_and_legacy_dd for row in frozen
            ),
            "diagnostic_single_intervention_full_gate_count": len(
                full_gate_rows
            ),
            "best_single_intervention_legacy_dd_r": (
                None if best_dd is None else str(best_dd)
            ),
            "best_single_intervention_keys": (
                []
                if best_dd is None
                else [
                    {
                        "symbol": row.symbol,
                        "entry_at": row.entry_at,
                        "action": row.action,
                        "rollout_legacy_dd_r": row.rollout_legacy_dd_r,
                        "dynamic_total_delta_r": row.dynamic_total_delta_r,
                    }
                    for row in frozen
                    if Decimal(row.rollout_legacy_dd_r) == best_dd
                ]
            ),
            "by_action": {
                action: _action_summary(tuple(rows))
                for action, rows in sorted(by_action.items())
            },
            "by_family": {
                family: _action_summary(tuple(rows))
                for family, rows in sorted(by_family.items())
            },
            "max_dd_descent_summary": _action_summary(max_dd_rows),
        },
        frozen,
    )


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[TransitionAudit, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        results: list[dict[str, Any]] = []
        audits: list[TransitionAudit] = []
        for period, (ledgers, contexts) in windows.items():
            result, rows = _period_report(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            results.append(result)
            audits.extend(rows)
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    return (
        {
            "identity": IDENTITY,
            "evaluation": "SINGLE_DO_ACTION_DYNAMIC_SURFACE_ROLLOUT",
            "empty_intervention_reproduces_surface_required": True,
            "same_entrant_identities": True,
            "density_retention": "1",
            "max3_entrant_set_changed": False,
            "new_protection_geometry_created": False,
            "downstream_surface_mode_recomputed": True,
            "downstream_surface_multiplier_recomputed": True,
            "closed_outcomes_only_visible_to_memory": True,
            "legacy_certification_dd_preserved": True,
            "realized_exit_batch_dd_reported": True,
            "outcomes_used_for_runtime_decision": False,
            "counterfactual_outcomes_used_for_diagnostic_scoring": True,
            "results": results,
            "policy_economics_run": False,
            "automatic_policy_promotion": False,
            "candidate_count": 0,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "next_phase": (
                "BUILD_EPISODE_TRANSITION_WORLD_MODEL_FROM_DYNAMIC_ROLLOUTS"
            ),
        },
        tuple(audits),
    )


def write_report(
    report: dict[str, Any],
    audits: tuple[TransitionAudit, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-counterfactual-portfolio-episode-simulator-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-transitions.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
