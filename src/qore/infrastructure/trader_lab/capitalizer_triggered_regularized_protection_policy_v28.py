"""Triggered regularized counterfactual protection policy for Capitalizer V28.

V27 proved that entry-time action selection is structurally zero-inflated because
most selected protection modes never activate. V28 moves action selection to the
exact causally observed protection milestone and compares only same-trigger
existing modes with a common realized path before the decision.

The historical V18 trigger router used coarse delay/context cells. V28 instead
uses the full continuous V10/V11 causal state plus exact trigger delay, with
L2-regularized partial pooling and two independent external-period model sets.
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
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_continuation_value_model_v22 as v22,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_recovery_trajectory_trigger_v18 as recovery,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_robust_counterfactual_protection_policy_v27 as v27,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_TRIGGERED_REGULARIZED_PROTECTION_POLICY_V28"
POLICY = "TRIGGERED_ROBUST_POSDELTA_NONDOWNSIDE"
L2_PRIOR_STRENGTH = v25.L2_PRIOR_STRENGTH

FAMILIES: dict[str, tuple[Decimal, tuple[str, ...]]] = {
    "TRIGGER_050": (
        Decimal("0.50"),
        (
            milestone.ProtectionMode.BE_AFTER_050.value,
            milestone.ProtectionMode.STAGED_050_100_150.value,
        ),
    ),
    "TRIGGER_075": (
        Decimal("0.75"),
        (
            milestone.ProtectionMode.BE_AFTER_075.value,
            milestone.ProtectionMode.LOCK025_AFTER_075.value,
            milestone.ProtectionMode.STAGED_075_125_150.value,
        ),
    ),
    "TRIGGER_100": (
        Decimal("1.00"),
        (
            milestone.ProtectionMode.BE_AFTER_100.value,
            milestone.ProtectionMode.LOCK025_AFTER_100.value,
            milestone.ProtectionMode.LOCK050_AFTER_100.value,
        ),
    ),
}

FamilyModels = dict[
    str,
    dict[str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]],
]


@dataclass(frozen=True, slots=True)
class TriggeredDecision:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    causal_surface_mode: str
    chosen_mode: str
    base_multiplier: str
    switched: bool
    chosen_family: str | None
    trigger_at: str | None
    trigger_delay_minutes: str | None
    trainer_a_period: str
    trainer_b_period: str
    robust_total_delta: str | None
    trainer_a_total_delta: str | None
    trainer_b_total_delta: str | None
    trainer_a_downside_delta: str | None
    trainer_b_downside_delta: str | None
    valid_common_trigger_count: int
    current_outcome_visible: bool = False
    heldout_counterfactual_visible: bool = False
    future_after_trigger_visible: bool = False
    identity_features_used: bool = False


def _trigger_features(
    pretrade: v10.Pretrade,
    *,
    entry_at: str,
    trigger_at: str,
) -> tuple[float, ...]:
    delay = recovery._trigger_delay(entry_at, trigger_at)
    return (*v27._entry_features(pretrade), float(delay))


def _by_mode(
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> dict[str, dict[tuple[str, str], milestone.SimulatedTrade]]:
    return {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }


def _training_examples(
    *,
    family: str,
    action: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    pretrades: dict[tuple[str, str], v10.Pretrade],
    control_decisions: dict[tuple[str, str], Any],
) -> tuple[
    tuple[v25.TrainingExample, ...],
    tuple[v25.TrainingExample, ...],
]:
    _trigger_r, family_arms = FAMILIES[family]
    if action not in family_arms:
        raise ValueError("V28 action outside family")

    modes = _by_mode(ledgers)
    total_examples: list[v25.TrainingExample] = []
    downside_examples: list[v25.TrainingExample] = []

    for key, pretrade in pretrades.items():
        decision = control_decisions[key]
        surface_mode = str(decision.surface_mode)
        trigger_at = recovery._common_trigger(
            key=key,
            surface_mode=surface_mode,
            family_arms=family_arms,
            by_mode=modes,
        )
        if trigger_at is None:
            continue

        surface_r = Decimal(modes[surface_mode][key].realized_gross_r)
        action_r = Decimal(modes[action][key].realized_gross_r)
        total_delta = action_r - surface_r
        downside_delta = (
            min(action_r, Decimal("0"))
            - min(surface_r, Decimal("0"))
        )
        features = _trigger_features(
            pretrade,
            entry_at=key[1],
            trigger_at=trigger_at,
        )
        total_examples.append((features, float(total_delta), 1.0, key))
        downside_examples.append((features, float(downside_delta), 1.0, key))

    return tuple(total_examples), tuple(downside_examples)


def _fit_models(
    *,
    windows: dict[str, Any],
    pretrade_maps: dict[str, dict[tuple[str, str], v10.Pretrade]],
    control_maps: dict[str, dict[tuple[str, str], Any]],
) -> tuple[FamilyModels, dict[str, Any]]:
    models: FamilyModels = {}
    diagnostics: dict[str, Any] = {}

    for period, (ledgers, _contexts) in windows.items():
        period_models: dict[
            str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
        ] = {}
        period_diagnostics: dict[str, Any] = {}

        for family, (_trigger_r, arms) in FAMILIES.items():
            action_models: dict[
                str, tuple[v25.RidgeModel, v25.RidgeModel]
            ] = {}
            family_diagnostics: dict[str, Any] = {}

            for action in arms:
                total_examples, downside_examples = _training_examples(
                    family=family,
                    action=action,
                    ledgers=ledgers,
                    pretrades=pretrade_maps[period],
                    control_decisions=control_maps[period],
                )
                if not total_examples:
                    raise ValueError(
                        f"V28 no trigger examples for {period}/{family}/{action}"
                    )
                total_model = v25._fit_model(
                    period=f"{period}:{family}:{action}:TOTAL",
                    examples=total_examples,
                )
                downside_model = v25._fit_model(
                    period=f"{period}:{family}:{action}:DOWNSIDE",
                    examples=downside_examples,
                )
                action_models[action] = (total_model, downside_model)
                family_diagnostics[action] = {
                    "training_trades": total_model.unique_training_trades,
                    "feature_dimension": total_model.feature_dimension,
                    "total_target_mean": str(
                        total_model.weighted_target_mean
                    ),
                    "downside_target_mean": str(
                        downside_model.weighted_target_mean
                    ),
                    "total_rmse": str(
                        total_model.weighted_training_rmse
                    ),
                    "downside_rmse": str(
                        downside_model.weighted_training_rmse
                    ),
                }

            period_models[family] = action_models
            period_diagnostics[family] = family_diagnostics

        models[period] = period_models
        diagnostics[period] = period_diagnostics

    return models, diagnostics


def _choose_family_action(
    *,
    features: tuple[float, ...],
    surface_mode: str,
    arms: tuple[str, ...],
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

    for action in arms:
        if action == surface_mode:
            continue
        total_a_model, downside_a_model = model_a[action]
        total_b_model, downside_b_model = model_b[action]

        total_a = v25._predict(total_a_model, features)
        total_b = v25._predict(total_b_model, features)
        downside_a = v25._predict(downside_a_model, features)
        downside_b = v25._predict(downside_b_model, features)

        eligible = (
            total_a > 0.0
            and total_b > 0.0
            and downside_a >= 0.0
            and downside_b >= 0.0
        )
        if not eligible:
            continue

        robust_score = min(total_a, total_b)
        if best_score is None or robust_score > best_score:
            chosen = action
            best_score = robust_score
            best_predictions = (
                total_a,
                total_b,
                downside_a,
                downside_b,
            )

    return chosen, best_score, best_predictions


def _valid_triggers(
    *,
    key: tuple[str, str],
    surface_mode: str,
    modes: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for family, (_trigger_r, arms) in FAMILIES.items():
        trigger_at = recovery._common_trigger(
            key=key,
            surface_mode=surface_mode,
            family_arms=arms,
            by_mode=modes,
        )
        if trigger_at is not None:
            result.append((family, trigger_at))
    return tuple(
        sorted(
            result,
            key=lambda row: (milestone._aware(row[1]), row[0]),
        )
    )


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
) -> tuple[dict[str, Any], tuple[TriggeredDecision, ...]]:
    modes = _by_mode(ledgers)
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (milestone._aware(row.entry_at), row.symbol),
        )
    )

    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    audits: list[TriggeredDecision] = []
    action_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    switches = 0

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
        triggers = _valid_triggers(
            key=key,
            surface_mode=surface_mode,
            modes=modes,
        )

        chosen_mode = surface_mode
        chosen_family: str | None = None
        chosen_trigger_at: str | None = None
        chosen_delay: str | None = None
        robust_score: float | None = None
        predictions: tuple[float, float, float, float] | None = None

        for family, trigger_at in triggers:
            _trigger_r, arms = FAMILIES[family]
            features = _trigger_features(
                pretrade,
                entry_at=trade.entry_at,
                trigger_at=trigger_at,
            )
            action, score, candidate_predictions = _choose_family_action(
                features=features,
                surface_mode=surface_mode,
                arms=arms,
                model_a=model_a[family],
                model_b=model_b[family],
            )
            if action is None:
                continue
            chosen_mode = action
            chosen_family = family
            chosen_trigger_at = trigger_at
            chosen_delay = str(
                recovery._trigger_delay(trade.entry_at, trigger_at)
            )
            robust_score = score
            predictions = candidate_predictions
            break

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
        action_counts[chosen_mode] += 1
        if chosen_family is not None:
            family_counts[chosen_family] += 1

        if predictions is None:
            total_a = total_b = downside_a = downside_b = None
        else:
            total_a, total_b, downside_a, downside_b = predictions

        audits.append(
            TriggeredDecision(
                period=period,
                policy=POLICY,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                causal_surface_mode=surface_mode,
                chosen_mode=chosen_mode,
                base_multiplier=str(pretrade.base_multiplier),
                switched=switched,
                chosen_family=chosen_family,
                trigger_at=chosen_trigger_at,
                trigger_delay_minutes=chosen_delay,
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
                valid_common_trigger_count=len(triggers),
            )
        )

    ledger = tuple(chosen_scaled)
    return {
        "period": period,
        "policy": POLICY,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "triggered_switch_count": switches,
        "action_counts": dict(sorted(action_counts.items())),
        "family_switch_counts": dict(sorted(family_counts.items())),
    }, tuple(audits)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[TriggeredDecision, ...]]:
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
        )

        results: list[dict[str, Any]] = []
        audits: list[TriggeredDecision] = []
        for heldout, (ledgers, contexts) in windows.items():
            trainers = tuple(period for period in windows if period != heldout)
            if len(trainers) != 2:
                raise ValueError("V28 requires exactly two external periods")
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
    total_switches = sum(
        int(row["triggered_switch_count"]) for row in results
    )
    candidate_count = int(full_gate and total_switches > 0)

    return {
        "identity": IDENTITY,
        "evaluation": "TRIGGERED_REGULARIZED_COUNTERFACTUAL_MODE_POLICY",
        "policy": POLICY,
        "families": {
            family: {
                "trigger_r": str(trigger_r),
                "arms": list(arms),
            }
            for family, (trigger_r, arms) in FAMILIES.items()
        },
        "family_count": len(FAMILIES),
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "state_source": "FULL_V10_V11_CAUSAL_PRETRADE_PLUS_EXACT_TRIGGER_DELAY",
        "coarse_delay_bands_used": False,
        "hard_recovery_gate_used": False,
        "same_trigger_common_path_required": True,
        "complete_075_family_includes_lock025": True,
        "model_diagnostics": model_diagnostics,
        "results": results,
        "total_triggered_switches": total_switches,
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
        "symbol_session_side_time_identity_features_used": False,
        "full_source_identity_proof_required_before_freeze": True,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_IDENTITY_PROOF_V28_SURVIVOR"
            if candidate_count
            else "V28_FALSIFIED_RICHER_TRIGGER_STATE_REQUIRED"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[TriggeredDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-triggered-regularized-protection-policy-v28.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-triggered-regularized-protection-policy-v28-decisions.jsonl"
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


if __name__ == "__main__":
    main()
