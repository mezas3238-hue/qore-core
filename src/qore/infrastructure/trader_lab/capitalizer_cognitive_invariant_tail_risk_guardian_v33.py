"""Cognitive invariant tail-risk guardian for Capitalizer V33.

V33 preserves the causal Surface policy by default and allows a protection-mode
override only when two independent consumed eras support the same action through
an invariant feature subspace and conservative out-of-time lower bounds.

The primary target is not isolated trade PnL. It is relief of the active
Surface drawdown episode caused by a single existing-mode substitution. This
aligns the learning target with the actual acceptance bottleneck: portfolio
max drawdown.

No entries, sizing, original stop/target geometry, MAX3 semantics, or physical
protection modes are changed.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
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

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_INVARIANT_TAIL_RISK_GUARDIAN_V33"
POLICY = "SURFACE_DEFAULT_COGNITIVE_INVARIANT_TAIL_RISK_OVERRIDE"
L2_PRIOR_STRENGTH = v25.L2_PRIOR_STRENGTH
SOURCE_TRIGGER_STATE_RUN_ID = 36283499014
CHRONOLOGICAL_FOLDS = 5
MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES = CHRONOLOGICAL_FOLDS * 2
RESIDUAL_QUANTILE = 0.20
EXPECTED_FEATURE_DIMENSION = v31.EXPECTED_FEATURE_DIMENSION

ACTION_ORDER = tuple(mode.value for mode in milestone.ProtectionMode)


@dataclass(frozen=True, slots=True)
class CalibratedHead:
    model: v25.RidgeModel
    residual_q20: float
    chronological_residual_count: int


@dataclass(frozen=True, slots=True)
class ActionHeads:
    episode_relief: CalibratedHead
    total_delta: CalibratedHead
    downside_delta: CalibratedHead


FamilyModels = dict[str, dict[str, dict[str, ActionHeads]]]


@dataclass(frozen=True, slots=True)
class V33Decision:
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
    invariant_episode_dimensions: int
    invariant_total_dimensions: int
    invariant_downside_dimensions: int
    eligible_action_count: int
    current_outcome_visible: bool = False
    heldout_counterfactual_visible: bool = False
    future_after_trigger_visible: bool = False
    activation_bar_ohlc_visible: bool = False
    era_identity_feature_used: bool = False
    symbol_session_side_time_identity_features_used: bool = False


@dataclass(frozen=True, slots=True)
class _Episode:
    start_index: int
    end_index: int
    peak_equity: Decimal
    control_max_dd: Decimal


def _aware(value: str) -> datetime:
    return milestone._aware(value)


def _canonical_rows(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[milestone.SimulatedTrade, ...]:
    return tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at), row.symbol))
    )


def _episode_for_index(
    control_ledger: tuple[milestone.SimulatedTrade, ...],
    *,
    index: int,
) -> _Episode:
    rows = _canonical_rows(control_ledger)
    if not 0 <= index < len(rows):
        raise ValueError("V33 episode index outside ledger")
    values = tuple(Decimal(row.realized_gross_r) for row in rows)

    equities: list[Decimal] = [Decimal("0")]
    running = Decimal("0")
    for value in values:
        running += value
        equities.append(running)

    running_peak = equities[0]
    latest_peak_point = 0
    for point in range(1, index + 1):
        if equities[point] >= running_peak:
            running_peak = equities[point]
            latest_peak_point = point

    peak_equity = running_peak
    end_index = len(rows) - 1
    for trade_index in range(index, len(rows)):
        if equities[trade_index + 1] >= peak_equity:
            end_index = trade_index
            break

    control_dd = Decimal("0")
    for trade_index in range(latest_peak_point, end_index + 1):
        control_dd = max(
            control_dd,
            peak_equity - equities[trade_index + 1],
        )

    return _Episode(
        start_index=latest_peak_point,
        end_index=end_index,
        peak_equity=peak_equity,
        control_max_dd=control_dd,
    )


def _episode_relief(
    control_ledger: tuple[milestone.SimulatedTrade, ...],
    *,
    key: tuple[str, str],
    counterfactual_scaled_r: Decimal,
) -> Decimal:
    rows = _canonical_rows(control_ledger)
    keys = tuple((row.symbol, row.entry_at) for row in rows)
    if key not in keys:
        raise ValueError("V33 episode key absent from Surface ledger")
    index = keys.index(key)
    episode = _episode_for_index(rows, index=index)

    values = [Decimal(row.realized_gross_r) for row in rows]
    values[index] = counterfactual_scaled_r

    equity = Decimal("0")
    for value in values[: episode.start_index]:
        equity += value
    if equity != episode.peak_equity:
        raise ValueError("V33 episode peak reconstruction drift")

    cf_dd = Decimal("0")
    for trade_index in range(
        episode.start_index,
        episode.end_index + 1,
    ):
        equity += values[trade_index]
        cf_dd = max(cf_dd, episode.peak_equity - equity)

    return episode.control_max_dd - cf_dd


def _training_examples(
    *,
    family: str,
    action: str,
    states: dict[tuple[str, str, str], v31.ControlTriggerState],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    control_ledger: tuple[milestone.SimulatedTrade, ...],
) -> tuple[
    tuple[v25.TrainingExample, ...],
    tuple[v25.TrainingExample, ...],
    tuple[v25.TrainingExample, ...],
]:
    if action not in v30._eligible_actions(family):
        raise ValueError("V33 action outside V30 reachability")

    modes = v29._by_mode(ledgers)
    control_map = {
        (row.symbol, row.entry_at): row
        for row in _canonical_rows(control_ledger)
    }
    episode_examples: list[v25.TrainingExample] = []
    total_examples: list[v25.TrainingExample] = []
    downside_examples: list[v25.TrainingExample] = []

    for (symbol, entry_at, state_family), state in states.items():
        if state_family != family:
            continue
        key = (symbol, entry_at)
        actions = v30._eligible_actions(family)
        v30._assert_common_path(
            key=key,
            trigger_at=state.trigger_at,
            actions=actions,
            modes=modes,
        )
        surface = modes[state.surface_mode][key]
        action_row = modes[action][key]
        surface_r = Decimal(surface.realized_gross_r)
        action_r = Decimal(action_row.realized_gross_r)
        multiplier = Decimal(state.base_multiplier)

        if key not in control_map:
            raise ValueError("V33 Surface control ledger identity drift")
        control_scaled = Decimal(control_map[key].realized_gross_r)
        expected_scaled = surface_r * multiplier
        if control_scaled != expected_scaled:
            raise ValueError("V33 Surface scaled R mismatch")

        counterfactual_scaled = action_r * multiplier
        relief = _episode_relief(
            control_ledger,
            key=key,
            counterfactual_scaled_r=counterfactual_scaled,
        )
        total_delta = action_r - surface_r
        downside_delta = min(action_r, Decimal("0")) - min(
            surface_r,
            Decimal("0"),
        )

        episode_examples.append(
            (state.vector, float(relief), 1.0, key)
        )
        total_examples.append(
            (state.vector, float(total_delta), 1.0, key)
        )
        downside_examples.append(
            (state.vector, float(downside_delta), 1.0, key)
        )

    return (
        tuple(episode_examples),
        tuple(total_examples),
        tuple(downside_examples),
    )


def _quantile(values: tuple[float, ...], quantile: float) -> float:
    if not values:
        raise ValueError("V33 quantile requires values")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("V33 quantile outside [0,1]")
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            math.ceil(quantile * len(ordered)) - 1,
        ),
    )
    return ordered[index]


def _chronological_residuals(
    *,
    label: str,
    examples: tuple[v25.TrainingExample, ...],
) -> tuple[float, ...]:
    ordered = tuple(
        sorted(
            examples,
            key=lambda row: (_aware(row[3][1]), row[3][0]),
        )
    )
    if len(ordered) < CHRONOLOGICAL_FOLDS * 2:
        raise ValueError("V33 insufficient examples for chronological calibration")

    block_size = math.ceil(len(ordered) / CHRONOLOGICAL_FOLDS)
    residuals: list[float] = []

    for fold in range(1, CHRONOLOGICAL_FOLDS):
        test_start = fold * block_size
        if test_start >= len(ordered):
            break
        test_end = min(len(ordered), (fold + 1) * block_size)
        train = ordered[:test_start]
        test = ordered[test_start:test_end]
        if not train or not test:
            continue
        model = v25._fit_model(
            period=f"{label}:OOF{fold}",
            examples=train,
        )
        for features, target, _weight, _key in test:
            residuals.append(target - v25._predict(model, features))

    if not residuals:
        raise ValueError("V33 produced no chronological residuals")
    return tuple(residuals)


def _fit_head(
    *,
    label: str,
    examples: tuple[v25.TrainingExample, ...],
) -> CalibratedHead:
    model = v25._fit_model(period=label, examples=examples)
    residuals = _chronological_residuals(
        label=label,
        examples=examples,
    )
    return CalibratedHead(
        model=model,
        residual_q20=_quantile(residuals, RESIDUAL_QUANTILE),
        chronological_residual_count=len(residuals),
    )


def _family_training_table(
    *,
    family: str,
    states: dict[tuple[str, str, str], v31.ControlTriggerState],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    control_ledger: tuple[milestone.SimulatedTrade, ...],
) -> tuple[
    tuple[tuple[float, ...], ...],
    tuple[tuple[str, str], ...],
    dict[tuple[str, str], tuple[float, ...]],
]:
    modes = v29._by_mode(ledgers)
    control_map = {
        (row.symbol, row.entry_at): row
        for row in _canonical_rows(control_ledger)
    }
    eligible = v30._eligible_actions(family)
    selected = tuple(
        sorted(
            (
                (symbol, entry_at, state)
                for (symbol, entry_at, state_family), state in states.items()
                if state_family == family
            ),
            key=lambda item: (_aware(item[1]), item[0]),
        )
    )
    if not selected:
        raise ValueError(f"V33 has no training states for {family}")

    features: list[tuple[float, ...]] = []
    keys: list[tuple[str, str]] = []
    targets: dict[tuple[str, str], list[float]] = {
        (action, head): []
        for action in eligible
        for head in ("EPISODE", "TOTAL", "DOWNSIDE")
    }

    for symbol, entry_at, state in selected:
        key = (symbol, entry_at)
        v30._assert_common_path(
            key=key,
            trigger_at=state.trigger_at,
            actions=eligible,
            modes=modes,
        )
        surface = modes[state.surface_mode][key]
        surface_r = Decimal(surface.realized_gross_r)
        multiplier = Decimal(state.base_multiplier)
        control_scaled = Decimal(control_map[key].realized_gross_r)
        if control_scaled != surface_r * multiplier:
            raise ValueError("V33 Surface scaled R mismatch")

        features.append(state.vector)
        keys.append(key)

        for action in eligible:
            action_r = Decimal(modes[action][key].realized_gross_r)
            counterfactual_scaled = action_r * multiplier
            relief = _episode_relief(
                control_ledger,
                key=key,
                counterfactual_scaled_r=counterfactual_scaled,
            )
            total_delta = action_r - surface_r
            downside_delta = min(action_r, Decimal("0")) - min(
                surface_r,
                Decimal("0"),
            )
            targets[(action, "EPISODE")].append(float(relief))
            targets[(action, "TOTAL")].append(float(total_delta))
            targets[(action, "DOWNSIDE")].append(float(downside_delta))

    return (
        tuple(features),
        tuple(keys),
        {target: tuple(values) for target, values in targets.items()},
    )


def _solve_many(
    matrix: list[list[float]],
    right_hand_sides: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise ValueError("V33 batch ridge matrix shape mismatch")
    if any(len(vector) != size for vector in right_hand_sides):
        raise ValueError("V33 batch ridge RHS shape mismatch")

    a = [row[:] for row in matrix]
    rhs_count = len(right_hand_sides)
    b = [
        [right_hand_sides[target][row] for target in range(rhs_count)]
        for row in range(size)
    ]

    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(a[row][column]))
        if abs(a[pivot][column]) < 1e-12:
            raise ValueError("V33 batch ridge system is singular")
        if pivot != column:
            a[column], a[pivot] = a[pivot], a[column]
            b[column], b[pivot] = b[pivot], b[column]

        pivot_value = a[column][column]
        for j in range(column, size):
            a[column][j] /= pivot_value
        for target in range(rhs_count):
            b[column][target] /= pivot_value

        for row in range(size):
            if row == column:
                continue
            factor = a[row][column]
            if factor == 0.0:
                continue
            for j in range(column, size):
                a[row][j] -= factor * a[column][j]
            for target in range(rhs_count):
                b[row][target] -= factor * b[column][target]

    return tuple(
        tuple(b[row][target] for row in range(size))
        for target in range(rhs_count)
    )


def _fit_many(
    *,
    label: str,
    features: tuple[tuple[float, ...], ...],
    keys: tuple[tuple[str, str], ...],
    targets: dict[tuple[str, str], tuple[float, ...]],
) -> dict[tuple[str, str], v25.RidgeModel]:
    if not features or len(features) != len(keys):
        raise ValueError("V33 batch ridge requires aligned examples")
    count = len(features)
    dimension = len(features[0])
    if any(len(row) != dimension for row in features):
        raise ValueError("V33 batch ridge feature dimension drift")
    if any(len(values) != count for values in targets.values()):
        raise ValueError("V33 batch ridge target length drift")

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
    for design in designs:
        for i in range(size):
            left = design[i]
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
        for design, target in zip(designs, values, strict=True):
            for i in range(size):
                vector[i] += design[i] * target
        rhs.append(tuple(vector))

    coefficient_sets = _solve_many(matrix, tuple(rhs))
    result: dict[tuple[str, str], v25.RidgeModel] = {}
    unique_trades = len(set(keys))

    for target_id, coefficients in zip(
        target_ids,
        coefficient_sets,
        strict=True,
    ):
        values = targets[target_id]
        squared_error = 0.0
        for design, target in zip(designs, values, strict=True):
            prediction = sum(
                coefficients[index] * design[index]
                for index in range(size)
            )
            squared_error += (prediction - target) ** 2
        result[target_id] = v25.RidgeModel(
            period=f"{label}:{target_id[0]}:{target_id[1]}",
            feature_mean=means,
            feature_scale=scales,
            coefficients=coefficients,
            unique_training_trades=unique_trades,
            weighted_observations=float(count),
            feature_dimension=dimension,
            weighted_target_mean=sum(values) / count,
            weighted_training_rmse=math.sqrt(squared_error / count),
            coefficient_l2_norm=math.sqrt(
                sum(value * value for value in coefficients[1:])
            ),
        )

    return result


def _fit_family_heads(
    *,
    period: str,
    family: str,
    features: tuple[tuple[float, ...], ...],
    keys: tuple[tuple[str, str], ...],
    targets: dict[tuple[str, str], tuple[float, ...]],
) -> dict[str, ActionHeads]:
    count = len(features)
    if count < CHRONOLOGICAL_FOLDS * 2:
        raise ValueError("V33 insufficient examples for chronological calibration")

    full_models = _fit_many(
        label=f"{period}:{family}:FULL",
        features=features,
        keys=keys,
        targets=targets,
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
        train_targets = {
            target_id: values[:test_start]
            for target_id, values in targets.items()
        }
        fold_models = _fit_many(
            label=f"{period}:{family}:OOF{fold}",
            features=features[:test_start],
            keys=keys[:test_start],
            targets=train_targets,
        )
        for target_id, model in fold_models.items():
            values = targets[target_id]
            for index in range(test_start, test_end):
                residuals[target_id].append(
                    values[index] - v25._predict(model, features[index])
                )

    calibrated: dict[tuple[str, str], CalibratedHead] = {}
    for target_id, model in full_models.items():
        current = tuple(residuals[target_id])
        if not current:
            raise ValueError("V33 produced no chronological residuals")
        calibrated[target_id] = CalibratedHead(
            model=model,
            residual_q20=_quantile(current, RESIDUAL_QUANTILE),
            chronological_residual_count=len(current),
        )

    result: dict[str, ActionHeads] = {}
    for action in v30._eligible_actions(family):
        result[action] = ActionHeads(
            episode_relief=calibrated[(action, "EPISODE")],
            total_delta=calibrated[(action, "TOTAL")],
            downside_delta=calibrated[(action, "DOWNSIDE")],
        )
    return result


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
        period_models: dict[str, dict[str, ActionHeads]] = {}
        period_diagnostics: dict[str, Any] = {}

        for family in v30.FAMILY_ORDER:
            features, keys, targets = _family_training_table(
                family=family,
                states=control_states[period],
                ledgers=ledgers,
                control_ledger=control_ledgers[period],
            )
            action_diagnostics: dict[str, Any] = {}
            if len(features) < MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES:
                action_models: dict[str, ActionHeads] = {}
                for action in v30._eligible_actions(family):
                    action_diagnostics[action] = {
                        "available": False,
                        "training_trades": len(keys),
                        "feature_dimension": (
                            len(features[0]) if features else 0
                        ),
                        "reason": (
                            "INSUFFICIENT_CHRONOLOGICAL_CALIBRATION_SUPPORT"
                        ),
                        "minimum_required": (
                            MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES
                        ),
                    }
            else:
                action_models = _fit_family_heads(
                    period=period,
                    family=family,
                    features=features,
                    keys=keys,
                    targets=targets,
                )
                for action, heads in action_models.items():
                    action_diagnostics[action] = {
                        "available": True,
                        "training_trades": (
                            heads.episode_relief.model.unique_training_trades
                        ),
                        "feature_dimension": (
                            heads.episode_relief.model.feature_dimension
                        ),
                        "episode_target_mean": str(
                            heads.episode_relief.model.weighted_target_mean
                        ),
                        "episode_rmse": str(
                            heads.episode_relief.model.weighted_training_rmse
                        ),
                        "episode_residual_q20": str(
                            heads.episode_relief.residual_q20
                        ),
                        "episode_oof_residuals": (
                            heads.episode_relief.chronological_residual_count
                        ),
                        "total_target_mean": str(
                            heads.total_delta.model.weighted_target_mean
                        ),
                        "total_residual_q20": str(
                            heads.total_delta.residual_q20
                        ),
                        "downside_target_mean": str(
                            heads.downside_delta.model.weighted_target_mean
                        ),
                        "downside_residual_q20": str(
                            heads.downside_delta.residual_q20
                        ),
                    }

            period_models[family] = action_models
            period_diagnostics[family] = action_diagnostics

        models[period] = period_models
        diagnostics[period] = period_diagnostics

    return models, diagnostics


def _invariant_mask(
    left: v25.RidgeModel,
    right: v25.RidgeModel,
) -> tuple[bool, ...]:
    if left.feature_dimension != right.feature_dimension:
        raise ValueError("V33 invariant model dimension mismatch")
    return tuple(
        (left.coefficients[index + 1] * right.coefficients[index + 1]) > 0.0
        for index in range(left.feature_dimension)
    )


def _masked_predict(
    model: v25.RidgeModel,
    features: tuple[float, ...],
    mask: tuple[bool, ...],
) -> float:
    if (
        len(features) != model.feature_dimension
        or len(mask) != model.feature_dimension
    ):
        raise ValueError("V33 masked prediction dimension mismatch")
    standardized = tuple(
        (features[index] - model.feature_mean[index])
        / model.feature_scale[index]
        for index in range(model.feature_dimension)
    )
    return model.coefficients[0] + sum(
        model.coefficients[index + 1] * standardized[index]
        for index in range(model.feature_dimension)
        if mask[index]
    )


def _pair_lcbs(
    *,
    left: CalibratedHead,
    right: CalibratedHead,
    features: tuple[float, ...],
) -> tuple[float, float, int]:
    mask = _invariant_mask(left.model, right.model)
    invariant_count = sum(mask)
    if invariant_count == 0:
        return float("-inf"), float("-inf"), 0
    left_lcb = _masked_predict(left.model, features, mask) + left.residual_q20
    right_lcb = _masked_predict(right.model, features, mask) + right.residual_q20
    return left_lcb, right_lcb, invariant_count


def _choose_action(
    *,
    features: tuple[float, ...],
    surface_mode: str,
    actions: tuple[str, ...],
    model_a: dict[str, ActionHeads],
    model_b: dict[str, ActionHeads],
) -> tuple[
    str | None,
    float | None,
    tuple[float, float, float, float, float, float] | None,
    tuple[int, int, int],
    str,
]:
    chosen: str | None = None
    best_score: float | None = None
    best_lcbs: tuple[float, float, float, float, float, float] | None = None
    best_dims = (0, 0, 0)
    saw_conflict = False
    saw_supported_dimensions = False

    for action in ACTION_ORDER:
        if action not in actions or action == surface_mode:
            continue
        if action not in model_a or action not in model_b:
            continue

        heads_a = model_a[action]
        heads_b = model_b[action]

        ep_a, ep_b, ep_dims = _pair_lcbs(
            left=heads_a.episode_relief,
            right=heads_b.episode_relief,
            features=features,
        )
        total_a, total_b, total_dims = _pair_lcbs(
            left=heads_a.total_delta,
            right=heads_b.total_delta,
            features=features,
        )
        down_a, down_b, down_dims = _pair_lcbs(
            left=heads_a.downside_delta,
            right=heads_b.downside_delta,
            features=features,
        )
        dims = (ep_dims, total_dims, down_dims)
        if min(dims) == 0:
            saw_conflict = True
            continue
        saw_supported_dimensions = True

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
            best_dims = dims

    if chosen is not None:
        epistemic = "WELL_SUPPORTED"
    elif saw_conflict:
        epistemic = "CONFLICTED"
    elif saw_supported_dimensions:
        epistemic = "UNRESOLVED"
    else:
        epistemic = "UNRESOLVED"

    return chosen, best_score, best_lcbs, best_dims, epistemic


def _simulate_period(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    trainer_a: str,
    trainer_b: str,
    model_a: dict[str, dict[str, ActionHeads]],
    model_b: dict[str, dict[str, ActionHeads]],
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[dict[str, Any], tuple[V33Decision, ...]]:
    modes = v29._by_mode(ledgers)
    ordered = _canonical_rows(
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

        trigger_updates: dict[
            tuple[str, str],
            tuple[
                str,
                float | None,
                tuple[float, float, float, float, float, float] | None,
                tuple[int, int, int],
                str,
                int,
            ],
        ] = {}

        for key in trigger_keys:
            trigger_at, family = pending[key]
            pretrade = pretrades[key]
            trade = modes[milestone.ProtectionMode.ORIGINAL.value][key]
            native = native_states.get(
                (period, trade.symbol, trade.entry_at, family)
            )
            if native is None:
                raise ValueError("V33 missing held-out native trigger state")
            if _aware(native.trigger_at) != trigger_at:
                raise ValueError("V33 held-out trigger timestamp drift")

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

            action, score, lcbs, dims, epistemic = _choose_action(
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
                dims,
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
            chosen_mode, score, lcbs, dims, epistemic, completed = (
                trigger_updates[key]
            )
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
                dims=dims,
                metacognitive_state=epistemic,
                eligible_action_count=len(v30._eligible_actions(family)),
            )

        for key, pretrade in new_pretrades.items():
            trade = modes[milestone.ProtectionMode.ORIGINAL.value][key]
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
                "dims": (0, 0, 0),
                "metacognitive_state": "UNRESOLVED",
                "eligible_action_count": 0,
            }

        pretrades.update(new_pretrades)
        projections.update(new_projections)
        records.update(new_records)
        pending.update(new_triggers)

    ledger = v31._snapshot_rows(projections)
    if len(ledger) != len(ordered):
        raise ValueError("V33 held-out replay lost entrants")

    audits: list[V33Decision] = []
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
        ep_dims, total_dims, down_dims = row["dims"]

        audits.append(
            V33Decision(
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
                invariant_episode_dimensions=int(ep_dims),
                invariant_total_dimensions=int(total_dims),
                invariant_downside_dimensions=int(down_dims),
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
) -> tuple[dict[str, Any], tuple[V33Decision, ...]]:
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
                    f"V33 Surface control replay drift in {period}"
                )
            control_states[period] = states
            control_ledgers[period] = ledger

        models, model_diagnostics = _fit_models(
            windows=windows,
            control_states=control_states,
            control_ledgers=control_ledgers,
        )

        results: list[dict[str, Any]] = []
        audits: list[V33Decision] = []

        for heldout, (ledgers, contexts) in windows.items():
            trainers = tuple(period for period in windows if period != heldout)
            if len(trainers) != 2:
                raise ValueError("V33 requires exactly two external periods")
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
        "evaluation": "COGNITIVE_CROSS_ERA_INVARIANT_EPISODE_DD_RELIEF",
        "policy": POLICY,
        "surface_default": True,
        "source_trigger_state_run_id": SOURCE_TRIGGER_STATE_RUN_ID,
        "source_trigger_state_identity": v29.IDENTITY,
        "v31_causal_state_preserved": True,
        "episode_dd_relief_target_used": True,
        "local_trade_delta_is_primary_target": False,
        "cross_era_invariant_subspace": True,
        "conflicting_sign_features_zeroed": True,
        "chronological_calibration_folds": CHRONOLOGICAL_FOLDS,
        "minimum_chronological_calibration_examples": (
            MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES
        ),
        "sparse_family_policy": "FAIL_CLOSED_KEEP_SURFACE",
        "residual_lower_quantile": str(RESIDUAL_QUANTILE),
        "metacognitive_uncertainty_can_only_preserve_surface": True,
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "expected_full_feature_dimension": EXPECTED_FEATURE_DIMENSION,
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
        "full_source_identity_proof_required_before_freeze": True,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_IDENTITY_PROOF_V33_SURVIVOR"
            if candidate_count
            else "V33_FALSIFIED_LATENT_ENVIRONMENT_CAUSAL_DISCOVERY_REQUIRED"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[V33Decision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-cognitive-invariant-tail-risk-guardian-v33"
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
