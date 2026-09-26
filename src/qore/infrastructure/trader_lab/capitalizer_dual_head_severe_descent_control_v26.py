"""Dual-head severe-descent continuation control for Capitalizer V26.

V25 learned useful local continuation value but almost never intervened on the
entry-ordered sequence that creates portfolio max drawdown. V26 adds a second,
independent training target: whether the trade belongs to the peak-to-trough
descent of a severe (>=4R) Surface-control drawdown episode.

Held-out inference still uses only causal information available by the current
completed M1 observation. Future severe-descent labels and current trade
outcomes are training-only.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

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
    capitalizer_hypothesis_survival_model_v21 as v21,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_invalidation_v18 as v18,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_state_machine_v20 as v20,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_DUAL_HEAD_SEVERE_DESCENT_CONTROL_V26"
POLICY = "INVALIDATING_POSBOTH_SEVEREBOTH_P2"
POLICIES = ("SURFACE_CONTROL", POLICY)
SEVERE_DD_R = Decimal("4")
SEVERE_CLASS_BOUNDARY = 0.50
PERSISTENCE_REQUIRED = 2


@dataclass(frozen=True, slots=True)
class DualHeadDecision:
    period: str
    policy: str
    symbol: str
    entry_at: str
    observed_at: str
    phase: str
    trainer_a_period: str
    trainer_b_period: str
    continuation_a_r: str
    continuation_b_r: str
    severe_a_score: str
    severe_b_score: str
    persistence: int
    structural_gate: bool
    continuation_gate: bool
    severe_gate: bool
    exit_applied: bool
    current_outcome_visible: bool = False
    future_bars_visible: bool = False
    heldout_severe_label_visible: bool = False
    heldout_continuation_label_visible: bool = False
    open_peer_outcome_visible: bool = False


DualExample = tuple[
    tuple[float, ...],
    float,
    float,
    float,
    tuple[str, str],
]


def _scaled_control_r(decision: v18.InvalidationDecision) -> Decimal:
    return (
        Decimal(decision.normalized_realized_r)
        * Decimal(decision.base_multiplier)
    )


def _severe_descent_labels(
    decisions: dict[tuple[str, str], v18.InvalidationDecision],
) -> tuple[dict[tuple[str, str], bool], int]:
    ordered = tuple(
        sorted(
            decisions.values(),
            key=lambda row: (v18._aware(row.entry_at), row.symbol),
        )
    )
    labels = {
        (row.symbol, row.entry_at): False
        for row in ordered
    }

    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    max_depth = Decimal("0")
    trough_index: int | None = None
    severe_episode_count = 0

    def finalize_episode() -> None:
        nonlocal severe_episode_count
        if trough_index is None or max_depth < SEVERE_DD_R:
            return
        severe_episode_count += 1
        for index in range(peak_index + 1, trough_index + 1):
            row = ordered[index]
            labels[(row.symbol, row.entry_at)] = True

    for index, row in enumerate(ordered):
        equity += _scaled_control_r(row)
        if equity >= peak:
            finalize_episode()
            peak = equity
            peak_index = index
            max_depth = Decimal("0")
            trough_index = None
            continue

        depth = peak - equity
        if depth > max_depth:
            max_depth = depth
            trough_index = index

    finalize_episode()
    return labels, severe_episode_count


def _dynamic_portfolio_features(
    *,
    observation: v25.AugmentedObservation,
    decisions: dict[tuple[str, str], v18.InvalidationDecision],
) -> tuple[float, ...]:
    row = observation.row
    observed_at = v18._aware(row.observed_at)
    entry_at = v18._aware(row.entry_at)
    current_key = (row.symbol, row.entry_at)

    closed = tuple(
        sorted(
            (
                decision
                for decision in decisions.values()
                if v18._aware(decision.final_exit_at) <= observed_at
            ),
            key=lambda decision: (
                v18._aware(decision.final_exit_at),
                decision.symbol,
            ),
        )
    )

    equity = Decimal("0")
    peak = Decimal("0")
    scaled_values: list[Decimal] = []
    for decision in closed:
        value = _scaled_control_r(decision)
        scaled_values.append(value)
        equity += value
        peak = max(peak, equity)
    realized_dd = peak - equity

    recent5 = sum(scaled_values[-5:], Decimal("0"))
    loss_streak = 0
    for value in reversed(scaled_values):
        if value < 0:
            loss_streak += 1
        else:
            break

    closed_since_entry = tuple(
        decision
        for decision in closed
        if v18._aware(decision.final_exit_at) > entry_at
        and (decision.symbol, decision.entry_at) != current_key
    )
    since_values = tuple(
        _scaled_control_r(decision)
        for decision in closed_since_entry
    )

    active_other = sum(
        (decision.symbol, decision.entry_at) != current_key
        and v18._aware(decision.entry_at) <= observed_at
        and observed_at < v18._aware(decision.final_exit_at)
        for decision in decisions.values()
    )

    return (
        float(realized_dd),
        float(recent5),
        float(loss_streak),
        float(len(closed_since_entry)),
        float(sum(since_values, Decimal("0"))),
        float(sum(value < 0 for value in since_values)),
        float(active_other),
    )


def _feature_vector(
    *,
    observation: v25.AugmentedObservation,
    pretrade: v10.Pretrade,
    decisions: dict[tuple[str, str], v18.InvalidationDecision],
) -> tuple[float, ...]:
    return (
        *v25._feature_vector(observation, pretrade),
        *_dynamic_portfolio_features(
            observation=observation,
            decisions=decisions,
        ),
    )


def _dual_examples(
    *,
    period: str,
    observations: tuple[v25.AugmentedObservation, ...],
    pretrades: dict[tuple[str, str], v10.Pretrade],
    control_decisions: dict[
        tuple[str, str], v18.InvalidationDecision
    ],
    severe_labels: dict[tuple[str, str], bool],
) -> tuple[DualExample, ...]:
    raw: list[
        tuple[tuple[float, ...], float, float, tuple[str, str]]
    ] = []

    for item in observations:
        row = item.row
        if row.period != period:
            continue
        key = (row.symbol, row.entry_at)
        decision = control_decisions.get(key)
        pretrade = pretrades.get(key)
        if decision is None or pretrade is None:
            continue
        if v18._aware(row.observed_at) >= v18._aware(decision.final_exit_at):
            continue

        continuation_target = float(
            Decimal(row.close_r) - Decimal(decision.normalized_realized_r)
        )
        severe_target = 1.0 if severe_labels[key] else 0.0
        raw.append(
            (
                _feature_vector(
                    observation=item,
                    pretrade=pretrade,
                    decisions=control_decisions,
                ),
                continuation_target,
                severe_target,
                key,
            )
        )

    counts: dict[tuple[str, str], int] = defaultdict(int)
    for _features, _continuation, _severe, key in raw:
        counts[key] += 1
    if not counts:
        raise ValueError("V26 training period has no causal observations")

    return tuple(
        (
            features,
            continuation,
            severe,
            1.0 / counts[key],
            key,
        )
        for features, continuation, severe, key in raw
    )


def _as_v25_examples(
    examples: tuple[DualExample, ...],
    *,
    target_index: int,
) -> tuple[v25.TrainingExample, ...]:
    if target_index not in {1, 2}:
        raise ValueError("V26 target index must be continuation or severe")
    result: list[v25.TrainingExample] = []
    for features, continuation, severe, weight, key in examples:
        target = continuation if target_index == 1 else severe
        result.append((features, target, weight, key))
    return tuple(result)


def _fit_models(
    *,
    windows: dict[str, Any],
    observations: tuple[v25.AugmentedObservation, ...],
    pretrade_maps: dict[str, dict[tuple[str, str], v10.Pretrade]],
    control_maps: dict[
        str, dict[tuple[str, str], v18.InvalidationDecision]
    ],
) -> tuple[
    dict[str, tuple[v25.RidgeModel, v25.RidgeModel]],
    dict[str, dict[str, Any]],
]:
    models: dict[str, tuple[v25.RidgeModel, v25.RidgeModel]] = {}
    diagnostics: dict[str, dict[str, Any]] = {}

    for period in windows:
        labels, severe_episodes = _severe_descent_labels(
            control_maps[period]
        )
        examples = _dual_examples(
            period=period,
            observations=observations,
            pretrades=pretrade_maps[period],
            control_decisions=control_maps[period],
            severe_labels=labels,
        )
        continuation = v25._fit_model(
            period=period,
            examples=_as_v25_examples(examples, target_index=1),
        )
        severe = v25._fit_model(
            period=period,
            examples=_as_v25_examples(examples, target_index=2),
        )
        models[period] = (continuation, severe)
        diagnostics[period] = {
            "severe_descent_trade_count": sum(labels.values()),
            "severe_episode_count": severe_episodes,
            "continuation_model": {
                "unique_training_trades": continuation.unique_training_trades,
                "feature_dimension": continuation.feature_dimension,
                "weighted_target_mean": str(
                    continuation.weighted_target_mean
                ),
                "weighted_training_rmse": str(
                    continuation.weighted_training_rmse
                ),
                "coefficient_l2_norm": str(
                    continuation.coefficient_l2_norm
                ),
            },
            "severe_model": {
                "unique_training_trades": severe.unique_training_trades,
                "feature_dimension": severe.feature_dimension,
                "weighted_target_mean": str(severe.weighted_target_mean),
                "weighted_training_rmse": str(
                    severe.weighted_training_rmse
                ),
                "coefficient_l2_norm": str(severe.coefficient_l2_norm),
            },
        }

    return models, diagnostics


def _build_events(
    *,
    windows: dict[str, Any],
    observations: tuple[v25.AugmentedObservation, ...],
    control_maps: dict[
        str, dict[tuple[str, str], v18.InvalidationDecision]
    ],
    pretrade_maps: dict[str, dict[tuple[str, str], v10.Pretrade]],
    models: dict[str, tuple[v25.RidgeModel, v25.RidgeModel]],
) -> tuple[
    dict[tuple[str, str, str, str], v18.TriggerEvent],
    tuple[DualHeadDecision, ...],
]:
    grouped: dict[
        tuple[str, str, str], list[v25.AugmentedObservation]
    ] = defaultdict(list)
    for item in observations:
        row = item.row
        grouped[(row.period, row.symbol, row.entry_at)].append(item)

    events: dict[tuple[str, str, str, str], v18.TriggerEvent] = {}
    audits: list[DualHeadDecision] = []

    for heldout, (ledgers, _contexts) in windows.items():
        selected_keys = {
            (row.symbol, row.entry_at)
            for row in ledgers[milestone.ProtectionMode.ORIGINAL.value]
        }
        if set(control_maps[heldout]) != selected_keys:
            raise ValueError("V26 control identity mismatch")
        if set(pretrade_maps[heldout]) != selected_keys:
            raise ValueError("V26 pretrade identity mismatch")

        trainers = tuple(period for period in windows if period != heldout)
        if len(trainers) != 2:
            raise ValueError("V26 requires exactly two external periods")
        trainer_a, trainer_b = trainers
        continuation_a, severe_a = models[trainer_a]
        continuation_b, severe_b = models[trainer_b]

        for symbol, entry_at in sorted(selected_keys):
            key = (symbol, entry_at)
            rows = sorted(
                grouped.get((heldout, symbol, entry_at), ()),
                key=lambda item: v18._aware(item.row.observed_at),
            )
            if not rows:
                continue

            decision = control_maps[heldout][key]
            pretrade = pretrade_maps[heldout][key]
            persistence = 0
            triggered = False

            for item in rows:
                if triggered:
                    break
                row = item.row
                if v18._aware(row.observed_at) >= v18._aware(
                    decision.final_exit_at
                ):
                    break

                features = _feature_vector(
                    observation=item,
                    pretrade=pretrade,
                    decisions=control_maps[heldout],
                )
                continuation_pred_a = v25._predict(
                    continuation_a, features
                )
                continuation_pred_b = v25._predict(
                    continuation_b, features
                )
                severe_pred_a = v25._predict(severe_a, features)
                severe_pred_b = v25._predict(severe_b, features)

                structural_gate = row.phase == v20.Phase.INVALIDATING.value
                continuation_gate = (
                    continuation_pred_a > 0.0
                    and continuation_pred_b > 0.0
                )
                severe_gate = (
                    severe_pred_a >= SEVERE_CLASS_BOUNDARY
                    and severe_pred_b >= SEVERE_CLASS_BOUNDARY
                )
                condition = (
                    structural_gate
                    and continuation_gate
                    and severe_gate
                )
                persistence = persistence + 1 if condition else 0

                close_r = Decimal(row.close_r)
                apply = (
                    persistence >= PERSISTENCE_REQUIRED
                    and close_r > Decimal("-1")
                )
                audits.append(
                    DualHeadDecision(
                        period=heldout,
                        policy=POLICY,
                        symbol=row.symbol,
                        entry_at=row.entry_at,
                        observed_at=row.observed_at,
                        phase=row.phase,
                        trainer_a_period=trainer_a,
                        trainer_b_period=trainer_b,
                        continuation_a_r=str(continuation_pred_a),
                        continuation_b_r=str(continuation_pred_b),
                        severe_a_score=str(severe_pred_a),
                        severe_b_score=str(severe_pred_b),
                        persistence=persistence,
                        structural_gate=structural_gate,
                        continuation_gate=continuation_gate,
                        severe_gate=severe_gate,
                        exit_applied=apply,
                    )
                )
                if not apply:
                    continue

                triggered = True
                events[(heldout, symbol, entry_at, POLICY)] = v18.TriggerEvent(
                    period=heldout,
                    symbol=row.symbol,
                    session=row.session,
                    operating_date=row.operating_date,
                    entry_at=row.entry_at,
                    trigger=POLICY,
                    trigger_at=row.observed_at,
                    trigger_r=row.close_r,
                    elapsed_full_bars=row.elapsed_full_bars,
                    max_favorable_r_before_trigger=row.max_favorable_r,
                )

    return events, tuple(audits)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    v21_evidence_root: Path,
) -> tuple[
    dict[str, Any],
    tuple[DualHeadDecision, ...],
    tuple[v18.InvalidationDecision, ...],
]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    raw_observations, _labels = v21._load_market_evidence(v21_evidence_root)
    observations = v25._augment_observations(raw_observations)

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
        observations=observations,
        pretrade_maps=pretrade_maps,
        control_maps=control_maps,
    )
    events, dual_audits = _build_events(
        windows=windows,
        observations=observations,
        control_maps=control_maps,
        pretrade_maps=pretrade_maps,
        models=models,
    )

    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous_simultaneous = dict(v11._SIMULTANEOUS)
    previous_policy_specs = dict(v18.POLICY_SPECS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    v18.POLICY_SPECS.clear()
    v18.POLICY_SPECS[POLICY] = (POLICY, None, None)

    economic_audits: list[v18.InvalidationDecision] = []
    try:
        results: list[dict[str, Any]] = []
        for policy in POLICIES:
            heldouts: dict[str, Any] = {}
            for period, (ledgers, contexts) in windows.items():
                if policy == "SURFACE_CONTROL":
                    current = controls[period]
                else:
                    current, audit = v18._simulate(
                        period=period,
                        policy=policy,
                        ledgers=ledgers,
                        contexts=contexts,
                        contextual_model=contextual_model,
                        events=events,
                    )
                    economic_audits.extend(audit)

                v10._annotate(current, controls[period])
                current["losing_streak_not_worse"] = (
                    int(current["metrics"]["max_losing_streak"])
                    <= int(controls[period]["metrics"]["max_losing_streak"])
                )
                heldouts[period] = current

            full_gate = all(
                row["pf_at_least_surface_control"]
                and row["total_r_at_least_surface_control"]
                and row["dd_below_surface_control"]
                and row["dd_at_or_below_6r"]
                and row["losing_streak_not_worse"]
                for row in heldouts.values()
            )
            total_exits = sum(
                int(row["invalidation_count"])
                for row in heldouts.values()
            )
            results.append(
                {
                    "policy": policy,
                    "heldouts": heldouts,
                    "total_dual_head_exits": total_exits,
                    "all_consumed_full_gate": full_gate,
                }
            )
    finally:
        v18.POLICY_SPECS.clear()
        v18.POLICY_SPECS.update(previous_policy_specs)
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous_simultaneous)

    candidates = tuple(
        row
        for row in results
        if row["policy"] != "SURFACE_CONTROL"
        and row["total_dual_head_exits"] > 0
        and row["all_consumed_full_gate"]
    )

    return {
        "identity": IDENTITY,
        "evaluation": "DUAL_HEAD_CONTINUATION_AND_SEVERE_DESCENT",
        "policy": POLICY,
        "severe_drawdown_training_threshold_r": str(SEVERE_DD_R),
        "severe_class_boundary": str(SEVERE_CLASS_BOUNDARY),
        "persistence_required": PERSISTENCE_REQUIRED,
        "l2_prior_strength_effective_trades": str(
            v25.L2_PRIOR_STRENGTH
        ),
        "dynamic_portfolio_features": [
            "REALIZED_DD_AT_OBSERVATION",
            "RECENT5_CLOSED_SCALED_R",
            "REALIZED_LOSS_STREAK",
            "OTHER_CLOSED_SINCE_ENTRY_COUNT",
            "OTHER_CLOSED_SINCE_ENTRY_SUM_R",
            "OTHER_CLOSED_SINCE_ENTRY_NEGATIVE_COUNT",
            "OTHER_ACTIVE_POSITION_COUNT",
        ],
        "severe_label_excludes_post_trough_recovery": True,
        "model_diagnostics": model_diagnostics,
        "decision_rows": len(dual_audits),
        "continuation_gate_rows": sum(
            row.continuation_gate for row in dual_audits
        ),
        "severe_gate_rows": sum(row.severe_gate for row in dual_audits),
        "joint_gate_rows": sum(
            row.continuation_gate and row.severe_gate
            for row in dual_audits
        ),
        "applied_exit_rows": sum(row.exit_applied for row in dual_audits),
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved": True,
        "max3_preserved": True,
        "current_outcome_visible_to_decision": False,
        "future_bars_visible_to_decision": False,
        "heldout_severe_label_visible_to_inference": False,
        "heldout_continuation_label_visible_to_inference": False,
        "open_peer_outcome_visible_to_inference": False,
        "dynamic_features_use_closed_outcomes_only": True,
        "full_source_recompetition_required_before_freeze": True,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_RECOMPETITION_V26_SURVIVOR"
            if candidates
            else "V26_FALSIFIED_PORTFOLIO_POLICY_LEARNING_REQUIRED"
        ),
    }, dual_audits, tuple(economic_audits)


def write_report(
    report: dict[str, Any],
    dual_audits: tuple[DualHeadDecision, ...],
    economic_audits: tuple[v18.InvalidationDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-dual-head-severe-descent-control-v26.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-dual-head-severe-descent-control-v26-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for dual_row in dual_audits:
            handle.write(json.dumps(asdict(dual_row), sort_keys=True) + "\n")
    with (
        output / "capitalizer-dual-head-severe-descent-control-v26-economics.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for economic_row in economic_audits:
            handle.write(json.dumps(asdict(economic_row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("v21_evidence_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, dual_audits, economic_audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.v21_evidence_root,
    )
    write_report(report, dual_audits, economic_audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
