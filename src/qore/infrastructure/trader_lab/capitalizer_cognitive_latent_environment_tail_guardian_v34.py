"""Cognitive latent-environment tail guardian for Capitalizer V34.

V33 proved that a single global invariant action-value surface is too coarse:
rare tail-protective states are averaged with ordinary states where the same
protection action is neutral or harmful.

V34 preserves Surface by default. Each external training world independently
discovers four outcome-blind soft cognitive environments from the same causal
95-dimensional Capitalizer state, fits environment-weighted ridge experts, and
calibrates the complete mixture chronologically. Held-out action inference
still requires two independent worlds to support episode-DD relief, total value
and downside preservation.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
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
    capitalizer_cognitive_invariant_tail_risk_guardian_v33 as v33,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_continuation_value_model_v22 as v22,
)
from qore.infrastructure.trader_lab import (
    capitalizer_event_time_portfolio_trigger_state_v31 as v31,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_first_intervention_cross_trigger_optionality_v30 as v30,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_LATENT_ENVIRONMENT_TAIL_GUARDIAN_V34"
POLICY = "SURFACE_DEFAULT_DUAL_WORLD_SOFT_ENVIRONMENT_TAIL_OVERRIDE"
ENVIRONMENT_COUNT = 4
MAX_KMEANS_ITERATIONS = 20
CHRONOLOGICAL_FOLDS = v33.CHRONOLOGICAL_FOLDS
MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES = (
    v33.MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES
)
RESIDUAL_QUANTILE = v33.RESIDUAL_QUANTILE
L2_PRIOR_STRENGTH = v33.L2_PRIOR_STRENGTH
SOURCE_TRIGGER_STATE_RUN_ID = v33.SOURCE_TRIGGER_STATE_RUN_ID
EXPECTED_FEATURE_DIMENSION = v31.EXPECTED_FEATURE_DIMENSION
ACTION_ORDER = tuple(mode.value for mode in milestone.ProtectionMode)


@dataclass(frozen=True, slots=True)
class EnvironmentGeometry:
    feature_mean: tuple[float, ...]
    feature_scale: tuple[float, ...]
    centroids: tuple[tuple[float, ...], ...]
    hard_counts: tuple[int, ...]
    iterations: int


@dataclass(frozen=True, slots=True)
class MixtureHead:
    experts: tuple[v25.RidgeModel, ...]
    residual_q20: float
    chronological_residual_count: int


@dataclass(frozen=True, slots=True)
class LatentActionHeads:
    episode_relief: MixtureHead
    total_delta: MixtureHead
    downside_delta: MixtureHead


@dataclass(frozen=True, slots=True)
class LatentFamilyModel:
    geometry: EnvironmentGeometry
    actions: dict[str, LatentActionHeads]


FamilyModels = dict[str, dict[str, LatentFamilyModel | None]]


@dataclass(frozen=True, slots=True)
class V34Decision:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    causal_surface_mode: str
    chosen_mode: str
    surface_first_family: str | None
    surface_first_protection_at: str | None
    decision_made: bool
    switched: bool
    metacognitive_state: str
    base_multiplier: str
    completed_m1_bars: int | None
    trigger_delay_minutes: str | None
    trainer_a_period: str
    trainer_b_period: str
    robust_episode_relief_lcb: str | None
    trainer_a_episode_relief_lcb: str | None
    trainer_b_episode_relief_lcb: str | None
    trainer_a_total_delta_lcb: str | None
    trainer_b_total_delta_lcb: str | None
    trainer_a_downside_delta_lcb: str | None
    trainer_b_downside_delta_lcb: str | None
    trainer_a_environment_weights: tuple[float, ...] | None
    trainer_b_environment_weights: tuple[float, ...] | None
    eligible_action_count: int
    current_outcome_visible: bool = False
    heldout_counterfactual_visible: bool = False
    future_after_trigger_visible: bool = False
    activation_bar_ohlc_visible: bool = False
    era_identity_feature_used: bool = False
    symbol_session_side_time_identity_features_used: bool = False


def _aware(value: str) -> datetime:
    return milestone._aware(value)


def _standardize(
    features: tuple[tuple[float, ...], ...],
) -> tuple[
    tuple[float, ...],
    tuple[float, ...],
    tuple[tuple[float, ...], ...],
]:
    if not features:
        raise ValueError("V34 environment discovery requires features")
    dimension = len(features[0])
    if any(len(row) != dimension for row in features):
        raise ValueError("V34 environment feature dimension drift")
    count = len(features)
    means = tuple(
        sum(row[index] for row in features) / count
        for index in range(dimension)
    )
    scales_list: list[float] = []
    for index in range(dimension):
        variance = sum(
            (row[index] - means[index]) ** 2 for row in features
        ) / count
        scale = math.sqrt(max(0.0, variance))
        scales_list.append(scale if scale > 1e-12 else 1.0)
    scales = tuple(scales_list)
    standardized = tuple(
        tuple(
            (row[index] - means[index]) / scales[index]
            for index in range(dimension)
        )
        for row in features
    )
    return means, scales, standardized


def _distance_sq(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    if len(left) != len(right):
        raise ValueError("V34 environment distance dimension mismatch")
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))


def _discover_geometry(
    features: tuple[tuple[float, ...], ...],
) -> EnvironmentGeometry:
    means, scales, rows = _standardize(features)
    if len(rows) < ENVIRONMENT_COUNT:
        raise ValueError("V34 requires at least four states for environments")

    first_index = min(
        range(len(rows)),
        key=lambda index: (
            sum(value * value for value in rows[index]),
            index,
        ),
    )
    selected = [first_index]
    centroids = [rows[first_index]]

    while len(centroids) < ENVIRONMENT_COUNT:
        next_index = max(
            (
                index
                for index in range(len(rows))
                if index not in selected
            ),
            key=lambda index: (
                min(
                    _distance_sq(rows[index], centroid)
                    for centroid in centroids
                ),
                -index,
            ),
        )
        selected.append(next_index)
        centroids.append(rows[next_index])

    assignments: tuple[int, ...] = ()
    iterations = 0
    for iteration in range(1, MAX_KMEANS_ITERATIONS + 1):
        current = tuple(
            min(
                range(ENVIRONMENT_COUNT),
                key=lambda env: (
                    _distance_sq(row, centroids[env]),
                    env,
                ),
            )
            for row in rows
        )
        iterations = iteration
        if current == assignments:
            break
        assignments = current

        updated: list[tuple[float, ...]] = []
        for env in range(ENVIRONMENT_COUNT):
            members = tuple(
                rows[index]
                for index, assigned in enumerate(assignments)
                if assigned == env
            )
            if not members:
                updated.append(centroids[env])
                continue
            updated.append(
                tuple(
                    sum(row[index] for row in members) / len(members)
                    for index in range(len(means))
                )
            )
        centroids = updated

    hard_counts = tuple(
        sum(assigned == env for assigned in assignments)
        for env in range(ENVIRONMENT_COUNT)
    )
    return EnvironmentGeometry(
        feature_mean=means,
        feature_scale=scales,
        centroids=tuple(centroids),
        hard_counts=hard_counts,
        iterations=iterations,
    )


def _environment_weights(
    geometry: EnvironmentGeometry,
    features: tuple[float, ...],
) -> tuple[float, ...]:
    if len(features) != len(geometry.feature_mean):
        raise ValueError("V34 environment inference dimension mismatch")
    standardized = tuple(
        (features[index] - geometry.feature_mean[index])
        / geometry.feature_scale[index]
        for index in range(len(features))
    )
    raw = tuple(
        1.0 / (1.0 + _distance_sq(standardized, centroid))
        for centroid in geometry.centroids
    )
    total = sum(raw)
    if total <= 0.0:
        raise ValueError("V34 environment weights must be positive")
    return tuple(value / total for value in raw)


def _fit_weighted_many(
    *,
    label: str,
    features: tuple[tuple[float, ...], ...],
    keys: tuple[tuple[str, str], ...],
    targets: dict[tuple[str, str], tuple[float, ...]],
    weights: tuple[float, ...],
) -> dict[tuple[str, str], v25.RidgeModel]:
    if not features or len(features) != len(keys) or len(features) != len(weights):
        raise ValueError("V34 weighted ridge requires aligned examples")
    count = len(features)
    dimension = len(features[0])
    if any(len(row) != dimension for row in features):
        raise ValueError("V34 weighted ridge feature dimension drift")
    if any(len(values) != count for values in targets.values()):
        raise ValueError("V34 weighted ridge target length drift")

    total_weight = sum(weights)
    if total_weight <= 0.0:
        raise ValueError("V34 weighted ridge requires positive weight")

    means = tuple(
        sum(
            weights[row_index] * features[row_index][index]
            for row_index in range(count)
        )
        / total_weight
        for index in range(dimension)
    )
    scales_list: list[float] = []
    for index in range(dimension):
        variance = (
            sum(
                weights[row_index]
                * (features[row_index][index] - means[index]) ** 2
                for row_index in range(count)
            )
            / total_weight
        )
        scale = math.sqrt(max(0.0, variance))
        scales_list.append(scale if scale > 1e-12 else 1.0)
    scales = tuple(scales_list)

    designs = tuple(
        (
            1.0,
            *(
                (row[index] - means[index]) / scales[index]
                for index in range(dimension)
            ),
        )
        for row in features
    )
    size = dimension + 1
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]
    for design, weight in zip(designs, weights, strict=True):
        for i in range(size):
            left = weight * design[i]
            for j in range(i, size):
                matrix[i][j] += left * design[j]
    for i in range(size):
        for j in range(i):
            matrix[i][j] = matrix[j][i]
    for index in range(1, size):
        matrix[index][index] += L2_PRIOR_STRENGTH

    target_ids = tuple(sorted(targets))
    rhs: list[tuple[float, ...]] = []
    for target_id in target_ids:
        values = targets[target_id]
        vector = [0.0 for _ in range(size)]
        for design, target, weight in zip(
            designs,
            values,
            weights,
            strict=True,
        ):
            for i in range(size):
                vector[i] += weight * design[i] * target
        rhs.append(tuple(vector))

    coefficient_sets = v33._solve_many(matrix, tuple(rhs))
    result: dict[tuple[str, str], v25.RidgeModel] = {}
    unique_trades = len(set(keys))

    for target_id, coefficients in zip(
        target_ids,
        coefficient_sets,
        strict=True,
    ):
        values = targets[target_id]
        squared_error = 0.0
        target_sum = 0.0
        for design, target, weight in zip(
            designs,
            values,
            weights,
            strict=True,
        ):
            prediction = sum(
                coefficients[index] * design[index]
                for index in range(size)
            )
            squared_error += weight * (prediction - target) ** 2
            target_sum += weight * target
        result[target_id] = v25.RidgeModel(
            period=f"{label}:{target_id[0]}:{target_id[1]}",
            feature_mean=means,
            feature_scale=scales,
            coefficients=coefficients,
            unique_training_trades=unique_trades,
            weighted_observations=total_weight,
            feature_dimension=dimension,
            weighted_target_mean=target_sum / total_weight,
            weighted_training_rmse=math.sqrt(
                squared_error / total_weight
            ),
            coefficient_l2_norm=math.sqrt(
                sum(value * value for value in coefficients[1:])
            ),
        )
    return result


def _fit_environment_experts(
    *,
    label: str,
    features: tuple[tuple[float, ...], ...],
    keys: tuple[tuple[str, str], ...],
    targets: dict[tuple[str, str], tuple[float, ...]],
    geometry: EnvironmentGeometry,
) -> dict[tuple[str, str], tuple[v25.RidgeModel, ...]]:
    memberships = tuple(
        _environment_weights(geometry, row) for row in features
    )
    by_target: dict[tuple[str, str], list[v25.RidgeModel]] = {
        target_id: [] for target_id in targets
    }
    for env in range(ENVIRONMENT_COUNT):
        weights = tuple(row[env] for row in memberships)
        fitted = _fit_weighted_many(
            label=f"{label}:ENV{env}",
            features=features,
            keys=keys,
            targets=targets,
            weights=weights,
        )
        for target_id, model in fitted.items():
            by_target[target_id].append(model)
    return {
        target_id: tuple(models)
        for target_id, models in by_target.items()
    }


def _mixture_predict(
    *,
    geometry: EnvironmentGeometry,
    experts: tuple[v25.RidgeModel, ...],
    features: tuple[float, ...],
) -> tuple[float, tuple[float, ...]]:
    if len(experts) != ENVIRONMENT_COUNT:
        raise ValueError("V34 mixture expert count drift")
    weights = _environment_weights(geometry, features)
    prediction = sum(
        weights[env] * v25._predict(experts[env], features)
        for env in range(ENVIRONMENT_COUNT)
    )
    return prediction, weights


def _fit_family_model(
    *,
    period: str,
    family: str,
    features: tuple[tuple[float, ...], ...],
    keys: tuple[tuple[str, str], ...],
    targets: dict[tuple[str, str], tuple[float, ...]],
) -> LatentFamilyModel:
    count = len(features)
    if count < MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES:
        raise ValueError("V34 insufficient chronological support")

    geometry = _discover_geometry(features)
    full_experts = _fit_environment_experts(
        label=f"{period}:{family}:FULL",
        features=features,
        keys=keys,
        targets=targets,
        geometry=geometry,
    )

    residuals: dict[tuple[str, str], list[float]] = {
        target_id: [] for target_id in targets
    }
    block_size = math.ceil(count / CHRONOLOGICAL_FOLDS)

    for fold in range(1, CHRONOLOGICAL_FOLDS):
        test_start = fold * block_size
        if test_start >= count:
            break
        test_end = min(count, (fold + 1) * block_size)
        train_features = features[:test_start]
        train_keys = keys[:test_start]
        if len(train_features) < ENVIRONMENT_COUNT:
            continue
        train_targets = {
            target_id: values[:test_start]
            for target_id, values in targets.items()
        }
        fold_geometry = _discover_geometry(train_features)
        fold_experts = _fit_environment_experts(
            label=f"{period}:{family}:OOF{fold}",
            features=train_features,
            keys=train_keys,
            targets=train_targets,
            geometry=fold_geometry,
        )
        for target_id, experts in fold_experts.items():
            values = targets[target_id]
            for index in range(test_start, test_end):
                prediction, _weights = _mixture_predict(
                    geometry=fold_geometry,
                    experts=experts,
                    features=features[index],
                )
                residuals[target_id].append(values[index] - prediction)

    action_heads: dict[str, LatentActionHeads] = {}
    for action in v30._eligible_actions(family):
        def head(
            name: str,
            *,
            action_name: str = action,
        ) -> MixtureHead:
            target_id = (action_name, name)
            current = tuple(residuals[target_id])
            if not current:
                raise ValueError("V34 produced no chronological residuals")
            return MixtureHead(
                experts=full_experts[target_id],
                residual_q20=v33._quantile(
                    current,
                    RESIDUAL_QUANTILE,
                ),
                chronological_residual_count=len(current),
            )

        action_heads[action] = LatentActionHeads(
            episode_relief=head("EPISODE"),
            total_delta=head("TOTAL"),
            downside_delta=head("DOWNSIDE"),
        )

    return LatentFamilyModel(
        geometry=geometry,
        actions=action_heads,
    )


def _fit_models(
    *,
    windows: dict[str, Any],
    control_states: dict[
        str, dict[tuple[str, str, str], v31.ControlTriggerState]
    ],
    control_ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> tuple[FamilyModels, dict[str, Any]]:
    models: FamilyModels = {}
    diagnostics: dict[str, Any] = {}

    for period, (ledgers, _contexts) in windows.items():
        period_models: dict[str, LatentFamilyModel | None] = {}
        period_diagnostics: dict[str, Any] = {}

        for family in v30.FAMILY_ORDER:
            features, keys, targets = v33._family_training_table(
                family=family,
                states=control_states[period],
                ledgers=ledgers,
                control_ledger=control_ledgers[period],
            )
            if len(features) < MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES:
                period_models[family] = None
                period_diagnostics[family] = {
                    "available": False,
                    "training_states": len(features),
                    "reason": (
                        "INSUFFICIENT_CHRONOLOGICAL_CALIBRATION_SUPPORT"
                    ),
                    "minimum_required": (
                        MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES
                    ),
                }
                continue

            model = _fit_family_model(
                period=period,
                family=family,
                features=features,
                keys=keys,
                targets=targets,
            )
            period_models[family] = model

            action_diagnostics: dict[str, Any] = {}
            for action, heads in model.actions.items():
                action_diagnostics[action] = {
                    "episode_residual_q20": str(
                        heads.episode_relief.residual_q20
                    ),
                    "total_residual_q20": str(
                        heads.total_delta.residual_q20
                    ),
                    "downside_residual_q20": str(
                        heads.downside_delta.residual_q20
                    ),
                    "episode_oof_residuals": (
                        heads.episode_relief.chronological_residual_count
                    ),
                }
            period_diagnostics[family] = {
                "available": True,
                "training_states": len(features),
                "feature_dimension": len(features[0]),
                "environment_count": ENVIRONMENT_COUNT,
                "hard_environment_counts": list(
                    model.geometry.hard_counts
                ),
                "kmeans_iterations": model.geometry.iterations,
                "actions": action_diagnostics,
            }

        models[period] = period_models
        diagnostics[period] = period_diagnostics

    return models, diagnostics


def _head_lcb(
    *,
    model: LatentFamilyModel,
    head: MixtureHead,
    features: tuple[float, ...],
) -> tuple[float, tuple[float, ...]]:
    prediction, weights = _mixture_predict(
        geometry=model.geometry,
        experts=head.experts,
        features=features,
    )
    return prediction + head.residual_q20, weights


def _choose_action(
    *,
    features: tuple[float, ...],
    surface_mode: str,
    actions: tuple[str, ...],
    model_a: LatentFamilyModel | None,
    model_b: LatentFamilyModel | None,
) -> tuple[
    str | None,
    float | None,
    tuple[float, float, float, float, float, float] | None,
    tuple[float, ...] | None,
    tuple[float, ...] | None,
    str,
]:
    if model_a is None or model_b is None:
        return None, None, None, None, None, "UNRESOLVED"

    chosen: str | None = None
    best_score: float | None = None
    best_lcbs: tuple[float, float, float, float, float, float] | None = None
    best_weights_a: tuple[float, ...] | None = None
    best_weights_b: tuple[float, ...] | None = None
    saw_conflict = False

    for action in ACTION_ORDER:
        if action not in actions or action == surface_mode:
            continue
        if action not in model_a.actions or action not in model_b.actions:
            continue
        a = model_a.actions[action]
        b = model_b.actions[action]

        ep_a, weights_a = _head_lcb(
            model=model_a,
            head=a.episode_relief,
            features=features,
        )
        ep_b, weights_b = _head_lcb(
            model=model_b,
            head=b.episode_relief,
            features=features,
        )
        total_a, _ = _head_lcb(
            model=model_a,
            head=a.total_delta,
            features=features,
        )
        total_b, _ = _head_lcb(
            model=model_b,
            head=b.total_delta,
            features=features,
        )
        down_a, _ = _head_lcb(
            model=model_a,
            head=a.downside_delta,
            features=features,
        )
        down_b, _ = _head_lcb(
            model=model_b,
            head=b.downside_delta,
            features=features,
        )

        if not (
            ep_a > 0.0
            and ep_b > 0.0
            and total_a >= 0.0
            and total_b >= 0.0
            and down_a >= 0.0
            and down_b >= 0.0
        ):
            saw_conflict = True
            continue

        score = min(ep_a, ep_b)
        if best_score is None or score > best_score:
            chosen = action
            best_score = score
            best_lcbs = (
                ep_a,
                ep_b,
                total_a,
                total_b,
                down_a,
                down_b,
            )
            best_weights_a = weights_a
            best_weights_b = weights_b

    epistemic = (
        "WELL_SUPPORTED"
        if chosen is not None
        else ("CONFLICTED" if saw_conflict else "UNRESOLVED")
    )
    return (
        chosen,
        best_score,
        best_lcbs,
        best_weights_a,
        best_weights_b,
        epistemic,
    )


def _simulate_period(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    trainer_a: str,
    trainer_b: str,
    model_a: dict[str, LatentFamilyModel | None],
    model_b: dict[str, LatentFamilyModel | None],
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[dict[str, Any], tuple[V34Decision, ...]]:
    modes = v29._by_mode(ledgers)
    ordered = v33._canonical_rows(
        ledgers[milestone.ProtectionMode.ORIGINAL.value]
    )
    pointer = 0
    projections: dict[tuple[str, str], milestone.SimulatedTrade] = {}
    records: dict[tuple[str, str], memory.MemoryRecord] = {}
    pretrades: dict[tuple[str, str], v10.Pretrade] = {}
    pending: dict[tuple[str, str], tuple[Any, str]] = {}
    audit_data: dict[tuple[str, str], dict[str, Any]] = {}

    while pointer < len(ordered) or pending:
        now = v31._next_event_time(
            ordered=ordered,
            pointer=pointer,
            pending=pending,
        )
        if now is None:
            break

        snapshot_projections = v31._snapshot_rows(projections)
        snapshot_records = v31._snapshot_records(records)
        trigger_keys = tuple(
            sorted(
                (
                    key
                    for key, (trigger_at, _family) in pending.items()
                    if trigger_at == now
                ),
                key=lambda key: (key[1], key[0]),
            )
        )
        trigger_updates: dict[tuple[str, str], tuple[Any, ...]] = {}

        for key in trigger_keys:
            trigger_at, family = pending[key]
            pretrade = pretrades[key]
            trade = modes[milestone.ProtectionMode.ORIGINAL.value][key]
            native = native_states.get(
                (period, trade.symbol, trade.entry_at, family)
            )
            if native is None:
                raise ValueError("V34 missing held-out native trigger state")
            if _aware(native.trigger_at) != trigger_at:
                raise ValueError("V34 held-out trigger timestamp drift")

            portfolio = v31._portfolio_vector(
                current_trade=trade,
                observed_at=trigger_at,
                projections=snapshot_projections,
            )
            features = v31._full_trigger_vector(
                pretrade=pretrade,
                trade=trade,
                trigger_at=native.trigger_at,
                native_state=native,
                portfolio=portfolio,
            )
            actions = v30._eligible_actions(family)
            v30._assert_common_path(
                key=key,
                trigger_at=native.trigger_at,
                actions=actions,
                modes=modes,
            )
            (
                action,
                score,
                lcbs,
                weights_a,
                weights_b,
                epistemic,
            ) = _choose_action(
                features=features,
                surface_mode=pretrade.mode,
                actions=actions,
                model_a=model_a[family],
                model_b=model_b[family],
            )
            chosen_mode = pretrade.mode if action is None else action
            trigger_updates[key] = (
                chosen_mode,
                score,
                lcbs,
                weights_a,
                weights_b,
                epistemic,
                native.completed_m1_bars,
            )

        entry_rows: list[milestone.SimulatedTrade] = []
        while pointer < len(ordered) and _aware(ordered[pointer].entry_at) == now:
            entry_rows.append(ordered[pointer])
            pointer += 1

        if entry_rows:
            (
                new_pretrades,
                new_projections,
                new_records,
                new_triggers,
            ) = v31._entry_batch(
                period=period,
                rows=tuple(entry_rows),
                modes=modes,
                contexts=contexts,
                contextual_model=contextual_model,
                snapshot_projections=snapshot_projections,
                snapshot_records=snapshot_records,
            )
        else:
            new_pretrades = {}
            new_projections = {}
            new_records = {}
            new_triggers = {}

        for key in trigger_keys:
            trigger_at, family = pending.pop(key)
            (
                chosen_mode,
                score,
                lcbs,
                weights_a,
                weights_b,
                epistemic,
                completed,
            ) = trigger_updates[key]
            pretrade = pretrades[key]
            selected = modes[chosen_mode][key]
            projections[key] = v31._scaled_trade(
                selected,
                multiplier=pretrade.base_multiplier,
            )
            records[key] = v31._record(
                pretrade=pretrade,
                selected=selected,
            )
            row = audit_data[key]
            row.update(
                decision_made=True,
                chosen_mode=chosen_mode,
                completed_m1_bars=completed,
                trigger_delay_minutes=str(
                    (trigger_at - _aware(key[1])).total_seconds() / 60.0
                ),
                robust_episode_relief_lcb=(
                    None if score is None else str(score)
                ),
                lcbs=lcbs,
                weights_a=weights_a,
                weights_b=weights_b,
                metacognitive_state=epistemic,
                eligible_action_count=len(v30._eligible_actions(family)),
            )

        for key, pretrade in new_pretrades.items():
            selected = modes[pretrade.mode][key]
            entry_family: str | None = v30._mode_family(pretrade.mode)
            audit_data[key] = {
                "causal_surface_mode": pretrade.mode,
                "chosen_mode": pretrade.mode,
                "surface_first_family": entry_family,
                "surface_first_protection_at": selected.first_protection_at,
                "base_multiplier": str(pretrade.base_multiplier),
                "decision_made": False,
                "completed_m1_bars": None,
                "trigger_delay_minutes": None,
                "robust_episode_relief_lcb": None,
                "lcbs": None,
                "weights_a": None,
                "weights_b": None,
                "metacognitive_state": "UNRESOLVED",
                "eligible_action_count": 0,
            }

        pretrades.update(new_pretrades)
        projections.update(new_projections)
        records.update(new_records)
        pending.update(new_triggers)

    ledger = v31._snapshot_rows(projections)
    if len(ledger) != len(ordered):
        raise ValueError("V34 held-out replay lost entrants")

    audits: list[V34Decision] = []
    action_counts: Counter[str] = Counter()
    epistemic_counts: Counter[str] = Counter()
    switches = 0
    decisions = 0

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        row = audit_data[key]
        surface_mode = str(row["causal_surface_mode"])
        chosen_mode = str(row["chosen_mode"])
        switched = chosen_mode != surface_mode
        switches += int(switched)
        decisions += int(bool(row["decision_made"]))
        action_counts[chosen_mode] += 1
        epistemic_counts[str(row["metacognitive_state"])] += 1

        lcbs = row["lcbs"]
        if lcbs is None:
            ep_a = ep_b = total_a = total_b = down_a = down_b = None
        else:
            ep_a, ep_b, total_a, total_b, down_a, down_b = lcbs

        audits.append(
            V34Decision(
                period=period,
                policy=POLICY,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                causal_surface_mode=surface_mode,
                chosen_mode=chosen_mode,
                surface_first_family=row["surface_first_family"],
                surface_first_protection_at=row[
                    "surface_first_protection_at"
                ],
                decision_made=bool(row["decision_made"]),
                switched=switched,
                metacognitive_state=str(row["metacognitive_state"]),
                base_multiplier=str(row["base_multiplier"]),
                completed_m1_bars=row["completed_m1_bars"],
                trigger_delay_minutes=row["trigger_delay_minutes"],
                trainer_a_period=trainer_a,
                trainer_b_period=trainer_b,
                robust_episode_relief_lcb=row[
                    "robust_episode_relief_lcb"
                ],
                trainer_a_episode_relief_lcb=(
                    None if ep_a is None else str(ep_a)
                ),
                trainer_b_episode_relief_lcb=(
                    None if ep_b is None else str(ep_b)
                ),
                trainer_a_total_delta_lcb=(
                    None if total_a is None else str(total_a)
                ),
                trainer_b_total_delta_lcb=(
                    None if total_b is None else str(total_b)
                ),
                trainer_a_downside_delta_lcb=(
                    None if down_a is None else str(down_a)
                ),
                trainer_b_downside_delta_lcb=(
                    None if down_b is None else str(down_b)
                ),
                trainer_a_environment_weights=row["weights_a"],
                trainer_b_environment_weights=row["weights_b"],
                eligible_action_count=int(row["eligible_action_count"]),
            )
        )

    return {
        "period": period,
        "policy": POLICY,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "surface_trigger_decision_count": decisions,
        "action_override_count": switches,
        "action_counts": dict(sorted(action_counts.items())),
        "metacognitive_state_counts": dict(sorted(epistemic_counts.items())),
    }, tuple(audits)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    trigger_state_root: Path,
) -> tuple[dict[str, Any], tuple[V34Decision, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    native_states = v29._load_trigger_states(trigger_state_root)

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
        controls, _control_rows, _control_maps = v22._control_decision_maps(
            windows,
            contextual_model,
        )
        control_states: dict[
            str, dict[tuple[str, str, str], v31.ControlTriggerState]
        ] = {}
        control_ledgers: dict[
            str, tuple[milestone.SimulatedTrade, ...]
        ] = {}
        for period, (ledgers, contexts) in windows.items():
            states, ledger = v31._control_event_replay(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                native_states=native_states,
            )
            if milestone._metrics(ledger) != controls[period]["metrics"]:
                raise ValueError(
                    f"V34 Surface control replay drift in {period}"
                )
            control_states[period] = states
            control_ledgers[period] = ledger

        models, model_diagnostics = _fit_models(
            windows=windows,
            control_states=control_states,
            control_ledgers=control_ledgers,
        )

        results: list[dict[str, Any]] = []
        audits: list[V34Decision] = []
        for heldout, (ledgers, contexts) in windows.items():
            trainers = tuple(period for period in windows if period != heldout)
            if len(trainers) != 2:
                raise ValueError("V34 requires exactly two external periods")
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
                native_states=native_states,
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
    total_overrides = sum(int(row["action_override_count"]) for row in results)
    candidate_count = int(full_gate and total_overrides > 0)

    return {
        "identity": IDENTITY,
        "evaluation": "DUAL_WORLD_SOFT_LATENT_COGNITIVE_ENVIRONMENT_TAIL_RISK",
        "policy": POLICY,
        "surface_default": True,
        "source_trigger_state_run_id": SOURCE_TRIGGER_STATE_RUN_ID,
        "source_trigger_state_identity": v29.IDENTITY,
        "causal_state_dimension": EXPECTED_FEATURE_DIMENSION,
        "environment_count": ENVIRONMENT_COUNT,
        "environment_semantic_anchor": [
            "NORMAL",
            "CAUTIOUS",
            "HIGH_SELECTIVITY",
            "RECOVERY_OBSERVATION",
        ],
        "environment_discovery_outcome_blind": True,
        "environment_discovery_per_training_world": True,
        "environment_initialization": "MEAN_NEAREST_THEN_FARTHEST_POINT",
        "environment_membership": "NORMALIZED_INVERSE_ONE_PLUS_SQUARED_DISTANCE",
        "max_kmeans_iterations": MAX_KMEANS_ITERATIONS,
        "chronological_calibration_folds": CHRONOLOGICAL_FOLDS,
        "minimum_chronological_calibration_examples": (
            MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES
        ),
        "sparse_family_policy": "FAIL_CLOSED_KEEP_SURFACE",
        "residual_lower_quantile": str(RESIDUAL_QUANTILE),
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "episode_dd_relief_target_used": True,
        "dual_world_lcb_gate": True,
        "model_diagnostics": model_diagnostics,
        "results": results,
        "total_action_overrides": total_overrides,
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
        "era_identity_feature_used": False,
        "symbol_session_side_time_identity_features_used": False,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_IDENTITY_PROOF_V34_SURVIVOR"
            if candidate_count
            else "V34_FALSIFIED_STRUCTURAL_DRAWDOWN_HAZARD_MODEL_REQUIRED"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[V34Decision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-cognitive-latent-environment-tail-guardian-v34"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-decisions.jsonl").open(
        "w",
        encoding="utf-8",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
