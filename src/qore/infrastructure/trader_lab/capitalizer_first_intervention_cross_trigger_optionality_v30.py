"""First-intervention cross-trigger optionality policy for Capitalizer V30.

V30 waits until the causal Surface policy is about to make its first real
protection intervention. At that exact timestamp, with V29's native-M1 state
known and no activation-bar OHLC visible, it may commit to any already-existing
protection mode whose nominal first intervention is at the same or a later
milestone, or ORIGINAL.

No new stop geometry is created and there is no sequential re-evaluation in
V30. The experiment isolates whether cross-trigger action optionality at the
first causally relevant intervention is sufficient.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_causal_trigger_state_veto_policy_v29 as v29,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_continuation_value_model_v22 as v22,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_FIRST_INTERVENTION_CROSS_TRIGGER_OPTIONALITY_V30"
POLICY = "FIRST_INTERVENTION_ROBUST_CROSS_TRIGGER_POSDELTA_NONDOWNSIDE"
L2_PRIOR_STRENGTH = v25.L2_PRIOR_STRENGTH
SOURCE_TRIGGER_STATE_RUN_ID = 36283499014
SOURCE_M1_RUN_ID = v29.SOURCE_M1_RUN_ID
SOURCE_M1_SHA = v29.SOURCE_M1_SHA

FAMILY_050 = "TRIGGER_050"
FAMILY_075 = "TRIGGER_075"
FAMILY_100 = "TRIGGER_100"
FAMILY_ORDER = (FAMILY_050, FAMILY_075, FAMILY_100)
FAMILY_RANK = {
    FAMILY_050: 0,
    FAMILY_075: 1,
    FAMILY_100: 2,
}

MODE_FIRST_FAMILY: dict[str, str | None] = {
    milestone.ProtectionMode.ORIGINAL.value: None,
    milestone.ProtectionMode.BE_AFTER_050.value: FAMILY_050,
    milestone.ProtectionMode.STAGED_050_100_150.value: FAMILY_050,
    milestone.ProtectionMode.BE_AFTER_075.value: FAMILY_075,
    milestone.ProtectionMode.LOCK025_AFTER_075.value: FAMILY_075,
    milestone.ProtectionMode.STAGED_075_125_150.value: FAMILY_075,
    milestone.ProtectionMode.BE_AFTER_100.value: FAMILY_100,
    milestone.ProtectionMode.LOCK025_AFTER_100.value: FAMILY_100,
    milestone.ProtectionMode.LOCK050_AFTER_100.value: FAMILY_100,
}

FamilyModels = dict[
    str,
    dict[str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]],
]


@dataclass(frozen=True, slots=True)
class V30Decision:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    causal_surface_mode: str
    surface_first_family: str | None
    surface_first_protection_at: str | None
    chosen_mode: str
    base_multiplier: str
    decision_made: bool
    switched: bool
    switched_to_original: bool
    switched_to_later_trigger: bool
    chosen_first_family: str | None
    completed_m1_bars: int | None
    trigger_delay_minutes: str | None
    trainer_a_period: str
    trainer_b_period: str
    robust_total_delta: str | None
    trainer_a_total_delta: str | None
    trainer_b_total_delta: str | None
    trainer_a_downside_delta: str | None
    trainer_b_downside_delta: str | None
    eligible_action_count: int
    current_outcome_visible: bool = False
    heldout_counterfactual_visible: bool = False
    future_after_trigger_visible: bool = False
    activation_bar_ohlc_visible: bool = False
    identity_features_used: bool = False


def _mode_family(mode: str) -> str | None:
    try:
        return MODE_FIRST_FAMILY[mode]
    except KeyError as exc:
        raise ValueError(f"V30 unknown protection mode {mode}") from exc


def _eligible_actions(family: str) -> tuple[str, ...]:
    if family not in FAMILY_RANK:
        raise ValueError(f"V30 unknown trigger family {family}")
    current_rank = FAMILY_RANK[family]
    result: list[str] = []
    for mode in milestone.ProtectionMode:
        first_family = _mode_family(mode.value)
        if first_family is None or FAMILY_RANK[first_family] >= current_rank:
            result.append(mode.value)
    return tuple(result)


def _assert_common_path(
    *,
    key: tuple[str, str],
    trigger_at: str,
    actions: tuple[str, ...],
    modes: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> None:
    decision_at = milestone._aware(trigger_at)
    for action in actions:
        first = modes[action][key].first_protection_at
        if first is not None and milestone._aware(first) < decision_at:
            raise ValueError(
                "V30 eligible action intervened before decision timestamp"
            )


def _training_examples(
    *,
    period: str,
    family: str,
    action: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    pretrades: dict[tuple[str, str], v10.Pretrade],
    control_decisions: dict[tuple[str, str], Any],
    trigger_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[
    tuple[v25.TrainingExample, ...],
    tuple[v25.TrainingExample, ...],
]:
    eligible = _eligible_actions(family)
    if action not in eligible:
        raise ValueError("V30 action outside frozen family horizon")

    modes = v29._by_mode(ledgers)
    total_examples: list[v25.TrainingExample] = []
    downside_examples: list[v25.TrainingExample] = []

    for key, pretrade in pretrades.items():
        surface_mode = str(control_decisions[key].surface_mode)
        if _mode_family(surface_mode) != family:
            continue
        surface = modes[surface_mode][key]
        trigger_at = surface.first_protection_at
        if trigger_at is None:
            continue

        state = trigger_states.get((period, key[0], key[1], family))
        if state is None:
            raise ValueError("V30 missing training trigger state")
        if milestone._aware(state.trigger_at) != milestone._aware(trigger_at):
            raise ValueError("V30 Surface/trigger-state timestamp mismatch")

        _assert_common_path(
            key=key,
            trigger_at=trigger_at,
            actions=eligible,
            modes=modes,
        )

        surface_r = Decimal(surface.realized_gross_r)
        action_r = Decimal(modes[action][key].realized_gross_r)
        total_delta = action_r - surface_r
        downside_delta = min(action_r, Decimal("0")) - min(
            surface_r, Decimal("0")
        )
        features = v29._trigger_features(
            pretrade,
            entry_at=key[1],
            trigger_at=trigger_at,
            state=state,
        )
        total_examples.append((features, float(total_delta), 1.0, key))
        downside_examples.append(
            (features, float(downside_delta), 1.0, key)
        )

    return tuple(total_examples), tuple(downside_examples)


def _fit_models(
    *,
    windows: dict[str, Any],
    pretrade_maps: dict[str, dict[tuple[str, str], v10.Pretrade]],
    control_maps: dict[str, dict[tuple[str, str], Any]],
    trigger_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[FamilyModels, dict[str, Any]]:
    models: FamilyModels = {}
    diagnostics: dict[str, Any] = {}

    for period, (ledgers, _contexts) in windows.items():
        period_models: dict[
            str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
        ] = {}
        period_diagnostics: dict[str, Any] = {}

        for family in FAMILY_ORDER:
            action_models: dict[
                str, tuple[v25.RidgeModel, v25.RidgeModel]
            ] = {}
            action_diagnostics: dict[str, Any] = {}
            for action in _eligible_actions(family):
                total_examples, downside_examples = _training_examples(
                    period=period,
                    family=family,
                    action=action,
                    ledgers=ledgers,
                    pretrades=pretrade_maps[period],
                    control_decisions=control_maps[period],
                    trigger_states=trigger_states,
                )
                if not total_examples:
                    action_diagnostics[action] = {
                        "available": False,
                        "training_trades": 0,
                    }
                    continue
                total_model = v25._fit_model(
                    period=f"{period}:{family}:{action}:TOTAL",
                    examples=total_examples,
                )
                downside_model = v25._fit_model(
                    period=f"{period}:{family}:{action}:DOWNSIDE",
                    examples=downside_examples,
                )
                action_models[action] = (total_model, downside_model)
                action_diagnostics[action] = {
                    "available": True,
                    "training_trades": total_model.unique_training_trades,
                    "feature_dimension": total_model.feature_dimension,
                    "total_target_mean": str(total_model.weighted_target_mean),
                    "downside_target_mean": str(
                        downside_model.weighted_target_mean
                    ),
                    "total_rmse": str(total_model.weighted_training_rmse),
                    "downside_rmse": str(
                        downside_model.weighted_training_rmse
                    ),
                }
            period_models[family] = action_models
            period_diagnostics[family] = action_diagnostics

        models[period] = period_models
        diagnostics[period] = period_diagnostics

    return models, diagnostics


def _choose_action(
    *,
    features: tuple[float, ...],
    surface_mode: str,
    actions: tuple[str, ...],
    model_a: dict[str, tuple[v25.RidgeModel, v25.RidgeModel]],
    model_b: dict[str, tuple[v25.RidgeModel, v25.RidgeModel]],
) -> tuple[
    str | None,
    float | None,
    tuple[float, float, float, float] | None,
]:
    chosen: str | None = None
    best_score: float | None = None
    best_predictions: tuple[float, float, float, float] | None = None

    for action in actions:
        if action == surface_mode:
            continue
        if action not in model_a or action not in model_b:
            continue
        total_a_model, downside_a_model = model_a[action]
        total_b_model, downside_b_model = model_b[action]
        total_a = v25._predict(total_a_model, features)
        total_b = v25._predict(total_b_model, features)
        downside_a = v25._predict(downside_a_model, features)
        downside_b = v25._predict(downside_b_model, features)
        if not (
            total_a > 0.0
            and total_b > 0.0
            and downside_a >= 0.0
            and downside_b >= 0.0
        ):
            continue
        score = min(total_a, total_b)
        if best_score is None or score > best_score:
            chosen = action
            best_score = score
            best_predictions = (
                total_a,
                total_b,
                downside_a,
                downside_b,
            )

    return chosen, best_score, best_predictions


def _simulate_period(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    trainer_a: str,
    trainer_b: str,
    model_a: dict[
        str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
    ],
    model_b: dict[
        str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
    ],
    trigger_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[dict[str, Any], tuple[V30Decision, ...]]:
    modes = v29._by_mode(ledgers)
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (milestone._aware(row.entry_at), row.symbol),
        )
    )
    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    audits: list[V30Decision] = []
    action_counts: Counter[str] = Counter()
    surface_family_decisions: Counter[str] = Counter()
    switches = 0
    original_switches = 0
    later_switches = 0
    first_intervention_decisions = 0

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        pretrade = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen_scaled),
            records=tuple(records),
        )
        surface_mode = pretrade.mode
        family = _mode_family(surface_mode)
        surface = modes[surface_mode][key]
        trigger_at = surface.first_protection_at

        chosen_mode = surface_mode
        decision_made = False
        completed_bars: int | None = None
        trigger_delay: str | None = None
        robust_score: float | None = None
        predictions: tuple[float, float, float, float] | None = None
        eligible = (
            ()
            if family is None or trigger_at is None
            else _eligible_actions(family)
        )

        if family is not None and trigger_at is not None:
            state = trigger_states.get(
                (period, trade.symbol, trade.entry_at, family)
            )
            if state is None:
                raise ValueError("V30 missing held-out trigger state")
            if milestone._aware(state.trigger_at) != milestone._aware(
                trigger_at
            ):
                raise ValueError(
                    "V30 held-out Surface/trigger timestamp mismatch"
                )
            _assert_common_path(
                key=key,
                trigger_at=trigger_at,
                actions=eligible,
                modes=modes,
            )
            features = v29._trigger_features(
                pretrade,
                entry_at=trade.entry_at,
                trigger_at=trigger_at,
                state=state,
            )
            action, robust_score, predictions = _choose_action(
                features=features,
                surface_mode=surface_mode,
                actions=eligible,
                model_a=model_a[family],
                model_b=model_b[family],
            )
            first_intervention_decisions += 1
            surface_family_decisions[family] += 1
            decision_made = True
            completed_bars = state.completed_m1_bars
            trigger_delay = str(
                (
                    milestone._aware(trigger_at)
                    - milestone._aware(trade.entry_at)
                ).total_seconds()
                / 60.0
            )
            if action is not None:
                chosen_mode = action

        selected = modes[chosen_mode][key]
        normalized_r = Decimal(selected.realized_gross_r)
        scaled_r = normalized_r * pretrade.base_multiplier
        chosen_scaled.append(
            replace(selected, realized_gross_r=str(scaled_r))
        )
        records.append(
            memory.MemoryRecord(
                symbol=pretrade.ctx.symbol,
                session=pretrade.ctx.session,
                destination_state=pretrade.ctx.destination_state,
                context_signature=pretrade.ctx.context_signature,
                exit_at=selected.exit_at,
                normalized_realized_r=str(normalized_r),
            )
        )

        switched = chosen_mode != surface_mode
        switches += int(switched)
        switched_to_original = (
            switched
            and chosen_mode == milestone.ProtectionMode.ORIGINAL.value
        )
        original_switches += int(switched_to_original)

        chosen_family = _mode_family(chosen_mode)
        switched_to_later = (
            switched
            and family is not None
            and chosen_family is not None
            and FAMILY_RANK[chosen_family] > FAMILY_RANK[family]
        )
        later_switches += int(switched_to_later)
        action_counts[chosen_mode] += 1

        if predictions is None:
            total_a = total_b = downside_a = downside_b = None
        else:
            total_a, total_b, downside_a, downside_b = predictions

        audits.append(
            V30Decision(
                period=period,
                policy=POLICY,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                causal_surface_mode=surface_mode,
                surface_first_family=family,
                surface_first_protection_at=trigger_at,
                chosen_mode=chosen_mode,
                base_multiplier=str(pretrade.base_multiplier),
                decision_made=decision_made,
                switched=switched,
                switched_to_original=switched_to_original,
                switched_to_later_trigger=switched_to_later,
                chosen_first_family=chosen_family,
                completed_m1_bars=completed_bars,
                trigger_delay_minutes=trigger_delay,
                trainer_a_period=trainer_a,
                trainer_b_period=trainer_b,
                robust_total_delta=(
                    None if robust_score is None else str(robust_score)
                ),
                trainer_a_total_delta=(
                    None if total_a is None else str(total_a)
                ),
                trainer_b_total_delta=(
                    None if total_b is None else str(total_b)
                ),
                trainer_a_downside_delta=(
                    None if downside_a is None else str(downside_a)
                ),
                trainer_b_downside_delta=(
                    None if downside_b is None else str(downside_b)
                ),
                eligible_action_count=len(eligible),
            )
        )

    ledger = tuple(chosen_scaled)
    return {
        "period": period,
        "policy": POLICY,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "first_intervention_decision_count": first_intervention_decisions,
        "action_switch_count": switches,
        "switch_to_original_count": original_switches,
        "switch_to_later_trigger_count": later_switches,
        "action_counts": dict(sorted(action_counts.items())),
        "surface_family_decision_counts": dict(
            sorted(surface_family_decisions.items())
        ),
    }, tuple(audits)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    trigger_state_root: Path,
) -> tuple[dict[str, Any], tuple[V30Decision, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    trigger_states = v29._load_trigger_states(trigger_state_root)

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
        controls, _control_rows, control_maps = v22._control_decision_maps(
            windows,
            contextual_model,
        )
        pretrade_maps = v25._build_control_pretrades(
            windows=windows,
            contextual_model=contextual_model,
            control_maps=control_maps,
        )
        models, model_diagnostics = _fit_models(
            windows=windows,
            pretrade_maps=pretrade_maps,
            control_maps=control_maps,
            trigger_states=trigger_states,
        )

        results: list[dict[str, Any]] = []
        audits: list[V30Decision] = []
        for heldout, (ledgers, contexts) in windows.items():
            trainers = tuple(period for period in windows if period != heldout)
            if len(trainers) != 2:
                raise ValueError("V30 requires exactly two external periods")
            trainer_a, trainer_b = trainers
            current, current_audits = _simulate_period(
                period=heldout,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                trainer_a=trainer_a,
                trainer_b=trainer_b,
                model_a=models[trainer_a],
                model_b=models[trainer_b],
                trigger_states=trigger_states,
            )
            v10._annotate(current, controls[heldout])
            current["losing_streak_not_worse"] = (
                int(current["metrics"]["max_losing_streak"])
                <= int(controls[heldout]["metrics"]["max_losing_streak"])
            )
            results.append(current)
            audits.extend(current_audits)
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    full_gate = all(
        row["pf_at_least_surface_control"]
        and row["total_r_at_least_surface_control"]
        and row["dd_below_surface_control"]
        and row["dd_at_or_below_6r"]
        and row["losing_streak_not_worse"]
        for row in results
    )
    total_switches = sum(int(row["action_switch_count"]) for row in results)
    candidate_count = int(full_gate and total_switches > 0)

    return {
        "identity": IDENTITY,
        "evaluation": "FIRST_SURFACE_INTERVENTION_CROSS_TRIGGER_MODE_ROUTING",
        "policy": POLICY,
        "source_trigger_state_run_id": SOURCE_TRIGGER_STATE_RUN_ID,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "feature_dimension": 75,
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "family_order": list(FAMILY_ORDER),
        "mode_first_family": MODE_FIRST_FAMILY,
        "eligible_actions_by_family": {
            family: list(_eligible_actions(family))
            for family in FAMILY_ORDER
        },
        "decision_time": "CAUSAL_SURFACE_FIRST_ACTUAL_PROTECTION_INTERVENTION",
        "single_decision_per_trade": True,
        "sequential_reevaluation_enabled": False,
        "later_trigger_commitment_enabled": True,
        "original_as_existing_mode_action": True,
        "native_m1_trigger_state_reused_from_v29": True,
        "trigger_time_portfolio_state_used": False,
        "trigger_time_cross_market_state_used": False,
        "model_diagnostics": model_diagnostics,
        "results": results,
        "total_action_switches": total_switches,
        "total_switches_to_original": sum(
            int(row["switch_to_original_count"]) for row in results
        ),
        "total_switches_to_later_trigger": sum(
            int(row["switch_to_later_trigger_count"]) for row in results
        ),
        "candidate_count": candidate_count,
        "all_entries_preserved": True,
        "density_retention": "1",
        "same_entrant_identities": True,
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved_at_entry": True,
        "new_protection_geometry_created": False,
        "max3_preserved": True,
        "max3_slot_recycling": False,
        "chosen_prior_outcomes_recompute_future_state": True,
        "current_outcome_visible_to_decision": False,
        "heldout_counterfactual_visible_to_decision": False,
        "future_after_trigger_visible_to_decision": False,
        "activation_bar_ohlc_visible_to_decision": False,
        "symbol_session_side_time_identity_features_used": False,
        "full_source_identity_proof_required_before_freeze": True,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_IDENTITY_PROOF_V30_SURVIVOR"
            if candidate_count
            else "V30_FALSIFIED_SEQUENTIAL_REEVALUATION_OR_PORTFOLIO_STATE_REQUIRED"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[V30Decision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-first-intervention-cross-trigger-optionality-v30.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-first-intervention-cross-trigger-optionality-v30-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("trigger_state_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.trigger_state_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
