"""Focused dynamic probe on Surface's actual maximum-DD descent.

This diagnostic reuses the frozen counterfactual portfolio episode simulator but
enumerates interventions only for entrants that belong to the Surface
peak-to-trough maximum-drawdown descent.  It exists to expose dynamic feedback
on the economically critical episode while the exhaustive simulator runs.

It is not a policy and cannot promote a candidate.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_counterfactual_portfolio_episode_simulator_v1 as simulator,
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

IDENTITY = "QORE_CAPITALIZER_COUNTERFACTUAL_MAX_DD_EPISODE_PROBE_V1"


def _period_probe(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[simulator.TransitionAudit, ...]]:
    control, control_ledger, surface_decisions = anatomy._surface_ledger(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    baseline_ledger, baseline_decisions = simulator._replay_period(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
        intervention=None,
    )
    if milestone._metrics(baseline_ledger) != control["metrics"]:
        raise ValueError("max-DD probe empty replay metrics drift")

    baseline_metrics = milestone._metrics(baseline_ledger)
    baseline_exit = chronology._exit_batch_metrics(baseline_ledger)
    baseline_total = Decimal(baseline_metrics["total_r"])
    baseline_dd = Decimal(baseline_metrics["max_drawdown_r"])
    baseline_exit_dd = Decimal(baseline_exit["max_drawdown_r"])
    max_dd_keys = simulator._surface_max_dd_keys(baseline_ledger)
    baseline_decision_map = simulator._decision_map(baseline_decisions)

    modes = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered_original = simulator._ordered(
        ledgers[milestone.ProtectionMode.ORIGINAL.value]
    )
    order_index = {
        (row.symbol, row.entry_at): index
        for index, row in enumerate(ordered_original)
    }
    baseline_records = simulator._baseline_records(
        ordered=ordered_original,
        decisions=baseline_decisions,
        modes=modes,
        contexts=contexts,
    )
    control_by_key = {
        (row.symbol, row.entry_at): row
        for row in anatomy._canonical_rows(control_ledger)
    }

    audits: list[simulator.TransitionAudit] = []
    probed_states = 0
    no_actual_trigger_count = 0
    for key, decision in surface_decisions.items():
        if key not in max_dd_keys:
            continue
        surface_mode = str(decision.surface_mode)
        family = v30._mode_family(surface_mode)
        if family is None:
            continue
        surface_raw = modes[surface_mode][key]
        trigger_at = surface_raw.first_protection_at
        if trigger_at is None:
            no_actual_trigger_count += 1
            continue
        reachable = v30._eligible_actions(family)
        v30._assert_common_path(
            key=key,
            trigger_at=trigger_at,
            actions=reachable,
            modes=modes,
        )
        probed_states += 1
        baseline_local_r = Decimal(
            control_by_key[key].realized_gross_r
        )
        baseline_index = order_index[key]

        for action in reachable:
            if action == surface_mode:
                continue
            spec = simulator.Intervention(
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
                rollout = baseline_ledger
                rollout_decisions = baseline_decisions
            else:
                rollout, rollout_decisions = simulator._replay_period(
                    period=period,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                    intervention=spec,
                    start_index=baseline_index,
                    prefix_chosen=baseline_ledger[:baseline_index],
                    prefix_records=baseline_records[:baseline_index],
                    prefix_decisions=baseline_decisions[:baseline_index],
                )
            rollout_metrics = milestone._metrics(rollout)
            rollout_exit = chronology._exit_batch_metrics(rollout)
            rollout_total = Decimal(rollout_metrics["total_r"])
            rollout_dd = Decimal(rollout_metrics["max_drawdown_r"])
            rollout_exit_dd = Decimal(
                rollout_exit["max_drawdown_r"]
            )

            multiplier = Decimal(decision.base_multiplier)
            action_local_r = (
                Decimal(modes[action][key].realized_gross_r)
                * multiplier
            )
            static_delta = action_local_r - baseline_local_r
            dynamic_delta = rollout_total - baseline_total
            feedback = dynamic_delta - static_delta
            dd_relief = baseline_dd - rollout_dd
            exit_dd_relief = baseline_exit_dd - rollout_exit_dd

            rollout_map = simulator._decision_map(rollout_decisions)
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

            local_sign = simulator._sign(static_delta)
            dynamic_sign = simulator._sign(dynamic_delta)
            full_gate = (
                simulator._pf_at_least(
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
                simulator.TransitionAudit(
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
                    entrant_in_surface_max_dd_descent=True,
                    static_local_delta_r=str(static_delta),
                    dynamic_total_delta_r=str(dynamic_delta),
                    downstream_feedback_r=str(feedback),
                    legacy_dd_relief_r=str(dd_relief),
                    realized_exit_batch_dd_relief_r=str(
                        exit_dd_relief
                    ),
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
                    downstream_multiplier_change_count=(
                        multiplier_changes
                    ),
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
                    improves_total_r_and_legacy_dd=(
                        dynamic_delta > 0 and dd_relief > 0
                    ),
                    diagnostic_single_intervention_full_gate=(
                        full_gate
                    ),
                    identical_downstream_trajectory_short_circuit=(
                        identical_downstream
                    ),
                )
            )

    frozen = tuple(audits)
    by_action: dict[str, list[simulator.TransitionAudit]] = defaultdict(list)
    for row in frozen:
        by_action[row.action].append(row)

    return (
        {
            "period": period,
            "surface": baseline_metrics,
            "surface_realized_exit_batch_dd_r": str(
                baseline_exit_dd
            ),
            "surface_max_dd_descent_entrant_count": len(
                max_dd_keys
            ),
            "surface_max_dd_trigger_state_count": probed_states,
            "surface_max_dd_no_actual_trigger_count": (
                no_actual_trigger_count
            ),
            "transition_count": len(frozen),
            "summary": simulator._action_summary(frozen),
            "by_action": {
                action: simulator._action_summary(tuple(rows))
                for action, rows in sorted(by_action.items())
            },
            "dynamic_feedback_nonzero_count": sum(
                Decimal(row.downstream_feedback_r) != 0
                for row in frozen
            ),
            "downstream_mode_change_transition_count": sum(
                row.downstream_mode_change_count > 0
                for row in frozen
            ),
            "downstream_multiplier_change_transition_count": sum(
                row.downstream_multiplier_change_count > 0
                for row in frozen
            ),
        },
        frozen,
    )


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[simulator.TransitionAudit, ...]]:
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
        audits: list[simulator.TransitionAudit] = []
        for period, (ledgers, contexts) in windows.items():
            result, rows = _period_probe(
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
            "evaluation": (
                "MAX_DD_DESCENT_SINGLE_DO_ACTION_DYNAMIC_ROLLOUT"
            ),
            "same_simulator_semantics_as_exhaustive_v1": True,
            "scope": "SURFACE_MAX_DD_PEAK_TO_TROUGH_ONLY",
            "policy_economics_run": False,
            "candidate_count": 0,
            "automatic_policy_promotion": False,
            "results": results,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
        },
        tuple(audits),
    )


def write_report(
    report: dict[str, Any],
    audits: tuple[simulator.TransitionAudit, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-counterfactual-max-dd-episode-probe-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-transitions.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in audits:
            handle.write(
                json.dumps(asdict(row), sort_keys=True) + "\n"
            )


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
