"""Regularized causal state-space continuation model for Capitalizer V25.

V24 proved that exact categorical regime cells collapse to destination/global
under honest support requirements. V25 therefore uses partial pooling through a
regularized continuous model over the already-causal V10/V11 pretrade vector
plus causal completed-M1 trajectory state.

Each held-out period is evaluated using two independent external-period models.
The held-out trade outcome, future bars, terminal reason and unchosen protection
outcomes are never inference features.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
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
    capitalizer_hypothesis_survival_model_v21 as v21,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_invalidation_v18 as v18,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_state_machine_v20 as v20,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_REGULARIZED_CAUSAL_STATE_SPACE_V25"
POLICY = "INVALIDATING_RIDGE_POSBOTH_P2"
POLICIES = ("SURFACE_CONTROL", POLICY)
L2_PRIOR_STRENGTH = 12.0
PERSISTENCE_REQUIRED = 2

MODE_VALUES = tuple(mode.value for mode in milestone.ProtectionMode)
PHASE_VALUES = tuple(phase.value for phase in v20.Phase)


@dataclass(frozen=True, slots=True)
class AugmentedObservation:
    row: v21.Observation
    velocity_1_r: float
    velocity_1_available: bool
    velocity_2_r: float
    velocity_2_available: bool


@dataclass(frozen=True, slots=True)
class RidgeModel:
    period: str
    feature_mean: tuple[float, ...]
    feature_scale: tuple[float, ...]
    coefficients: tuple[float, ...]
    unique_training_trades: int
    weighted_observations: float
    feature_dimension: int
    weighted_target_mean: float
    weighted_training_rmse: float
    coefficient_l2_norm: float


@dataclass(frozen=True, slots=True)
class RidgeDecision:
    period: str
    policy: str
    symbol: str
    entry_at: str
    observed_at: str
    phase: str
    trainer_a_period: str
    trainer_b_period: str
    trainer_a_prediction_r: str
    trainer_b_prediction_r: str
    persistence: int
    structural_gate: bool
    both_positive_gate: bool
    exit_applied: bool
    current_outcome_visible: bool = False
    future_bars_visible: bool = False
    original_exit_bar_used: bool = False
    unchosen_counterfactual_visible: bool = False
    heldout_training_label_visible: bool = False


TrainingExample = tuple[tuple[float, ...], float, float, tuple[str, str]]


def _augment_observations(
    observations: tuple[v21.Observation, ...],
) -> tuple[AugmentedObservation, ...]:
    grouped: dict[tuple[str, str, str], list[v21.Observation]] = defaultdict(list)
    for row in observations:
        grouped[(row.period, row.symbol, row.entry_at)].append(row)

    result: list[AugmentedObservation] = []
    for rows in grouped.values():
        ordered = sorted(rows, key=lambda item: v18._aware(item.observed_at))
        closes: list[float] = []
        for row in ordered:
            close_r = float(Decimal(row.close_r))
            velocity_1_available = len(closes) >= 1
            velocity_2_available = len(closes) >= 2
            velocity_1 = 0.0 if not velocity_1_available else close_r - closes[-1]
            velocity_2 = 0.0 if not velocity_2_available else close_r - closes[-2]
            result.append(
                AugmentedObservation(
                    row=row,
                    velocity_1_r=velocity_1,
                    velocity_1_available=velocity_1_available,
                    velocity_2_r=velocity_2,
                    velocity_2_available=velocity_2_available,
                )
            )
            closes.append(close_r)

    return tuple(
        sorted(
            result,
            key=lambda item: (
                item.row.period,
                item.row.entry_at,
                item.row.symbol,
                item.row.observed_at,
            ),
        )
    )


def _feature_vector(
    item: AugmentedObservation,
    pretrade: v10.Pretrade,
) -> tuple[float, ...]:
    row = item.row
    close_r = float(Decimal(row.close_r))
    mfe_r = float(Decimal(row.max_favorable_r))
    retracement_r = mfe_r - close_r

    mode_one_hot = tuple(
        1.0 if pretrade.mode == mode else 0.0 for mode in MODE_VALUES
    )
    phase_one_hot = tuple(
        1.0 if row.phase == phase else 0.0 for phase in PHASE_VALUES
    )

    trajectory = (
        float(row.elapsed_full_bars),
        close_r,
        mfe_r,
        retracement_r,
        item.velocity_1_r,
        1.0 if item.velocity_1_available else 0.0,
        item.velocity_2_r,
        1.0 if item.velocity_2_available else 0.0,
        float(row.adverse_close_count),
        float(row.invalidating_age),
        *phase_one_hot,
        1.0 if row.adverse_displacement_observed else 0.0,
        1.0 if row.displacement_midpoint_reclaimed else 0.0,
        1.0 if row.adverse_extreme_extended else 0.0,
        1.0 if row.recovered_since_deterioration else 0.0,
    )

    return (
        *pretrade.point.vector,
        float(pretrade.base_multiplier),
        *mode_one_hot,
        *trajectory,
    )


def _build_control_pretrades(
    *,
    windows: dict[str, Any],
    contextual_model: dict[str, Any],
    control_maps: dict[
        str, dict[tuple[str, str], v18.InvalidationDecision]
    ],
) -> dict[str, dict[tuple[str, str], v10.Pretrade]]:
    result: dict[str, dict[tuple[str, str], v10.Pretrade]] = {}

    for period, (ledgers, contexts) in windows.items():
        by_mode = {
            mode: {(row.symbol, row.entry_at): row for row in rows}
            for mode, rows in ledgers.items()
        }
        ordered = tuple(
            sorted(
                ledgers[milestone.ProtectionMode.ORIGINAL.value],
                key=lambda row: (v18._aware(row.entry_at), row.symbol),
            )
        )
        if set(control_maps[period]) != {
            (row.symbol, row.entry_at) for row in ordered
        }:
            raise ValueError("V25 control/pretrade identity mismatch")

        chosen: list[milestone.SimulatedTrade] = []
        records: list[memory.MemoryRecord] = []
        rows: dict[tuple[str, str], v10.Pretrade] = {}

        for trade in ordered:
            key = (trade.symbol, trade.entry_at)
            pre = v11._pretrade(
                period=period,
                trade=trade,
                contexts=contexts,
                contextual_model=contextual_model,
                chosen_scaled=tuple(chosen),
                records=tuple(records),
            )
            base = by_mode[pre.mode][key]
            decision = control_maps[period][key]

            if decision.surface_mode != pre.mode:
                raise ValueError("V25 control Surface mode mismatch")
            if Decimal(decision.current_drawdown_r) != pre.current_dd:
                raise ValueError("V25 control DD mismatch")
            if Decimal(decision.base_multiplier) != pre.base_multiplier:
                raise ValueError("V25 control multiplier mismatch")
            if decision.final_exit_at != base.exit_at:
                raise ValueError("V25 control exit mismatch")
            if Decimal(decision.normalized_realized_r) != Decimal(
                base.realized_gross_r
            ):
                raise ValueError("V25 control normalized R mismatch")

            rows[key] = pre

            normalized_r = Decimal(base.realized_gross_r)
            scaled_r = normalized_r * pre.base_multiplier
            chosen.append(
                replace(
                    base,
                    realized_gross_r=str(scaled_r),
                )
            )
            records.append(
                memory.MemoryRecord(
                    symbol=pre.ctx.symbol,
                    session=pre.ctx.session,
                    destination_state=pre.ctx.destination_state,
                    context_signature=pre.ctx.context_signature,
                    exit_at=base.exit_at,
                    normalized_realized_r=str(normalized_r),
                )
            )

        result[period] = rows

    return result


def _training_examples(
    *,
    period: str,
    observations: tuple[AugmentedObservation, ...],
    pretrades: dict[tuple[str, str], v10.Pretrade],
    control_decisions: dict[
        tuple[str, str], v18.InvalidationDecision
    ],
) -> tuple[TrainingExample, ...]:
    raw: list[
        tuple[tuple[float, ...], float, tuple[str, str]]
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

        target = float(
            Decimal(row.close_r) - Decimal(decision.normalized_realized_r)
        )
        raw.append((_feature_vector(item, pretrade), target, key))

    counts = defaultdict(int)
    for _features, _target, key in raw:
        counts[key] += 1
    if not counts:
        raise ValueError("V25 training period has no causal observations")

    result: list[TrainingExample] = []
    for features, target, key in raw:
        result.append((features, target, 1.0 / counts[key], key))

    return tuple(result)


def _weighted_scaling(
    examples: tuple[TrainingExample, ...],
) -> tuple[tuple[float, ...], tuple[float, ...], float]:
    dimension = len(examples[0][0])
    if any(len(row[0]) != dimension for row in examples):
        raise ValueError("V25 feature dimension drift")

    total_weight = sum(row[2] for row in examples)
    if total_weight <= 0:
        raise ValueError("V25 requires positive training weight")

    means: list[float] = []
    scales: list[float] = []
    for index in range(dimension):
        mean = (
            sum(weight * features[index] for features, _target, weight, _key in examples)
            / total_weight
        )
        variance = (
            sum(
                weight * (features[index] - mean) ** 2
                for features, _target, weight, _key in examples
            )
            / total_weight
        )
        means.append(mean)
        scale = math.sqrt(max(0.0, variance))
        scales.append(scale if scale > 1e-12 else 1.0)

    return tuple(means), tuple(scales), total_weight


def _solve_linear_system(
    matrix: list[list[float]],
    vector: list[float],
) -> tuple[float, ...]:
    size = len(vector)
    if len(matrix) != size or any(len(row) != size for row in matrix):
        raise ValueError("V25 linear system shape mismatch")

    a = [row[:] for row in matrix]
    b = vector[:]

    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(a[row][column]))
        if abs(a[pivot][column]) < 1e-12:
            raise ValueError("V25 ridge system is singular")
        if pivot != column:
            a[column], a[pivot] = a[pivot], a[column]
            b[column], b[pivot] = b[pivot], b[column]

        pivot_value = a[column][column]
        for j in range(column, size):
            a[column][j] /= pivot_value
        b[column] /= pivot_value

        for row in range(size):
            if row == column:
                continue
            factor = a[row][column]
            if factor == 0.0:
                continue
            for j in range(column, size):
                a[row][j] -= factor * a[column][j]
            b[row] -= factor * b[column]

    return tuple(b)


def _fit_model(
    *,
    period: str,
    examples: tuple[TrainingExample, ...],
) -> RidgeModel:
    means, scales, total_weight = _weighted_scaling(examples)
    dimension = len(means)
    size = dimension + 1

    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    vector = [0.0 for _ in range(size)]

    weighted_target_sum = 0.0
    unique_trades = {key for _features, _target, _weight, key in examples}

    for features, target, weight, _key in examples:
        standardized = tuple(
            (features[index] - means[index]) / scales[index]
            for index in range(dimension)
        )
        design = (1.0, *standardized)
        weighted_target_sum += weight * target

        for i in range(size):
            vector[i] += weight * design[i] * target
            for j in range(size):
                matrix[i][j] += weight * design[i] * design[j]

    for index in range(1, size):
        matrix[index][index] += L2_PRIOR_STRENGTH

    coefficients = _solve_linear_system(matrix, vector)

    squared_error = 0.0
    for features, target, weight, _key in examples:
        standardized = tuple(
            (features[index] - means[index]) / scales[index]
            for index in range(dimension)
        )
        prediction = coefficients[0] + sum(
            coefficients[index + 1] * standardized[index]
            for index in range(dimension)
        )
        squared_error += weight * (prediction - target) ** 2

    return RidgeModel(
        period=period,
        feature_mean=means,
        feature_scale=scales,
        coefficients=coefficients,
        unique_training_trades=len(unique_trades),
        weighted_observations=total_weight,
        feature_dimension=dimension,
        weighted_target_mean=weighted_target_sum / total_weight,
        weighted_training_rmse=math.sqrt(squared_error / total_weight),
        coefficient_l2_norm=math.sqrt(
            sum(value * value for value in coefficients[1:])
        ),
    )


def _predict(model: RidgeModel, features: tuple[float, ...]) -> float:
    if len(features) != model.feature_dimension:
        raise ValueError("V25 prediction feature dimension mismatch")
    standardized = tuple(
        (features[index] - model.feature_mean[index])
        / model.feature_scale[index]
        for index in range(model.feature_dimension)
    )
    return model.coefficients[0] + sum(
        model.coefficients[index + 1] * standardized[index]
        for index in range(model.feature_dimension)
    )


def _build_events(
    *,
    windows: dict[str, Any],
    observations: tuple[AugmentedObservation, ...],
    control_maps: dict[
        str, dict[tuple[str, str], v18.InvalidationDecision]
    ],
    pretrade_maps: dict[str, dict[tuple[str, str], v10.Pretrade]],
) -> tuple[
    dict[tuple[str, str, str, str], v18.TriggerEvent],
    tuple[RidgeDecision, ...],
    dict[str, RidgeModel],
]:
    models: dict[str, RidgeModel] = {}
    for period in windows:
        models[period] = _fit_model(
            period=period,
            examples=_training_examples(
                period=period,
                observations=observations,
                pretrades=pretrade_maps[period],
                control_decisions=control_maps[period],
            ),
        )

    grouped: dict[
        tuple[str, str, str], list[AugmentedObservation]
    ] = defaultdict(list)
    for item in observations:
        row = item.row
        grouped[(row.period, row.symbol, row.entry_at)].append(item)

    events: dict[tuple[str, str, str, str], v18.TriggerEvent] = {}
    audits: list[RidgeDecision] = []

    for heldout, (ledgers, _contexts) in windows.items():
        selected_keys = {
            (row.symbol, row.entry_at)
            for row in ledgers[milestone.ProtectionMode.ORIGINAL.value]
        }
        if set(control_maps[heldout]) != selected_keys:
            raise ValueError("V25 heldout control identity mismatch")
        if set(pretrade_maps[heldout]) != selected_keys:
            raise ValueError("V25 heldout pretrade identity mismatch")

        trainers = tuple(period for period in windows if period != heldout)
        if len(trainers) != 2:
            raise ValueError("V25 requires exactly two external trainer periods")
        trainer_a, trainer_b = trainers
        model_a = models[trainer_a]
        model_b = models[trainer_b]

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

                features = _feature_vector(item, pretrade)
                prediction_a = _predict(model_a, features)
                prediction_b = _predict(model_b, features)

                structural_gate = row.phase == v20.Phase.INVALIDATING.value
                both_positive = prediction_a > 0.0 and prediction_b > 0.0
                condition = structural_gate and both_positive
                persistence = persistence + 1 if condition else 0

                close_r = Decimal(row.close_r)
                apply = (
                    persistence >= PERSISTENCE_REQUIRED
                    and close_r > Decimal("-1")
                )

                audits.append(
                    RidgeDecision(
                        period=heldout,
                        policy=POLICY,
                        symbol=row.symbol,
                        entry_at=row.entry_at,
                        observed_at=row.observed_at,
                        phase=row.phase,
                        trainer_a_period=trainer_a,
                        trainer_b_period=trainer_b,
                        trainer_a_prediction_r=str(prediction_a),
                        trainer_b_prediction_r=str(prediction_b),
                        persistence=persistence,
                        structural_gate=structural_gate,
                        both_positive_gate=both_positive,
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

    return events, tuple(audits), models


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    v21_evidence_root: Path,
) -> tuple[
    dict[str, Any],
    tuple[RidgeDecision, ...],
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
    observations = _augment_observations(raw_observations)

    controls, _control_rows, control_maps = v22._control_decision_maps(
        windows,
        contextual_model,
    )
    pretrade_maps = _build_control_pretrades(
        windows=windows,
        contextual_model=contextual_model,
        control_maps=control_maps,
    )
    events, ridge_audits, models = _build_events(
        windows=windows,
        observations=observations,
        control_maps=control_maps,
        pretrade_maps=pretrade_maps,
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
                int(row["invalidation_count"]) for row in heldouts.values()
            )
            results.append(
                {
                    "policy": policy,
                    "heldouts": heldouts,
                    "total_ridge_exits": total_exits,
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
        and row["total_ridge_exits"] > 0
        and row["all_consumed_full_gate"]
    )

    model_diagnostics = {
        period: {
            "unique_training_trades": model.unique_training_trades,
            "weighted_observations": str(model.weighted_observations),
            "feature_dimension": model.feature_dimension,
            "weighted_target_mean": str(model.weighted_target_mean),
            "weighted_training_rmse": str(model.weighted_training_rmse),
            "coefficient_l2_norm": str(model.coefficient_l2_norm),
        }
        for period, model in models.items()
    }

    both_positive_rows = sum(row.both_positive_gate for row in ridge_audits)
    applied_rows = sum(row.exit_applied for row in ridge_audits)

    return {
        "identity": IDENTITY,
        "evaluation": "REGULARIZED_CAUSAL_STATE_SPACE_CONTINUATION_VALUE",
        "policy": POLICY,
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "persistence_required": PERSISTENCE_REQUIRED,
        "pretrade_vector_source": "V10_V11_POINT_VECTOR",
        "v10_identity_penalties_used": False,
        "anti_pseudoreplication": "EACH_TRADE_TOTAL_WEIGHT_EQUALS_ONE",
        "model_diagnostics": model_diagnostics,
        "decision_rows": len(ridge_audits),
        "both_positive_rows": both_positive_rows,
        "applied_exit_rows": applied_rows,
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "surface_multiplier_preserved": True,
        "surface_mode_used_as_causal_feature": True,
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved": True,
        "max3_preserved": True,
        "symbol_session_side_time_identity_features_used": False,
        "current_outcome_visible_to_decision": False,
        "future_bars_visible_to_decision": False,
        "original_exit_bar_excluded": True,
        "unchosen_counterfactual_visible_to_decision": False,
        "heldout_training_label_visible_to_decision": False,
        "training_label_uses_final_surface_r": True,
        "training_label_visible_to_heldout_inference": False,
        "full_source_recompetition_required_before_freeze": True,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_RECOMPETITION_V25_SURVIVOR"
            if candidates
            else "V25_FALSIFIED_INFORMATION_REPRESENTATION_INSUFFICIENT"
        ),
    }, ridge_audits, tuple(economic_audits)


def write_report(
    report: dict[str, Any],
    ridge_audits: tuple[RidgeDecision, ...],
    economic_audits: tuple[v18.InvalidationDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-regularized-causal-state-space-v25.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-regularized-causal-state-space-v25-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for ridge_row in ridge_audits:
            handle.write(json.dumps(asdict(ridge_row), sort_keys=True) + "\n")
    with (
        output / "capitalizer-regularized-causal-state-space-v25-economics.jsonl"
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

    report, ridge_audits, economic_audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.v21_evidence_root,
    )
    write_report(report, ridge_audits, economic_audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
