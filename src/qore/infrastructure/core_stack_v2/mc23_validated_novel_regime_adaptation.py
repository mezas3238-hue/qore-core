"""MC-23 preregistered real novel-regime representation adaptation.

The mechanism is intentionally narrow:
- fit only on consumed R6 NOVEL/NEAR_KNOWN source-time observations;
- evaluate once on temporally later R5;
- use no P/L or Trader methodology;
- compare a frozen linear source-state baseline with a frozen interaction basis;
- never mutate certified knowledge or acquire productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

import numpy as np

BASELINE_FEATURE_NAMES: Final = (
    "compression",
    "liquidity_accumulation",
    "failed_auction",
    "displacement",
    "acceptance",
    "absorption",
    "leader_confirmation",
    "leader_divergence",
    "momentum_persistence",
    "momentum_decay",
    "structural_fragility",
    "liquidity_vacuum",
    "regime_transition",
    "anomaly",
)

ADAPTIVE_INTERACTION_NAMES: Final = (
    "anomaly_x_regime_transition",
    "leader_divergence_x_structural_fragility",
    "liquidity_vacuum_x_anomaly",
    "momentum_persistence_x_inverse_momentum_decay",
    "displacement_x_acceptance",
    "compression_x_liquidity_accumulation",
)

TARGET_NAMES: Final = (
    "NAS100_FUTURE_30M_NET_RETURN_Z",
    "NAS100_FUTURE_30M_ABS_RETURN_Z",
    "NAS100_FUTURE_30M_MEAN_RANGE_Z",
    "NAS100_FUTURE_30M_PATH_EFFICIENCY_Z",
)

RIDGE_LAMBDA: Final = 1.0
MINIMUM_R5_SCORED_OBSERVATIONS: Final = 5_000
MINIMUM_POSITIVE_TARGETS: Final = 3
MINIMUM_POOLED_INCREMENTAL_BPS: Final = 100
MAXIMUM_TARGET_REGRESSION_BPS: Final = 500


@dataclass(frozen=True, slots=True)
class FrozenRidgeProjection:
    feature_names: tuple[str, ...]
    target_names: tuple[str, ...]
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: np.ndarray
    y_scale: np.ndarray
    coefficients: np.ndarray
    ridge_lambda: float

    def __post_init__(self) -> None:
        if not self.feature_names or not self.target_names:
            raise ValueError("projection names must be non-empty")
        if self.ridge_lambda != RIDGE_LAMBDA:
            raise ValueError("MC23 ridge lambda drift")
        feature_count = len(self.feature_names)
        target_count = len(self.target_names)
        if self.x_mean.shape != (feature_count,):
            raise ValueError("x_mean shape drift")
        if self.x_scale.shape != (feature_count,):
            raise ValueError("x_scale shape drift")
        if self.y_mean.shape != (target_count,):
            raise ValueError("y_mean shape drift")
        if self.y_scale.shape != (target_count,):
            raise ValueError("y_scale shape drift")
        if self.coefficients.shape != (feature_count + 1, target_count):
            raise ValueError("coefficient shape drift")
        if np.any(self.x_scale <= 0) or np.any(self.y_scale <= 0):
            raise ValueError("projection scales must be positive")
        for array in (
            self.x_mean,
            self.x_scale,
            self.y_mean,
            self.y_scale,
            self.coefficients,
        ):
            if not np.isfinite(array).all():
                raise ValueError("projection arrays must be finite")

    def fingerprint(self) -> str:
        payload = {
            "feature_names": self.feature_names,
            "target_names": self.target_names,
            "ridge_lambda": self.ridge_lambda,
            "x_mean": np.round(self.x_mean, 12).tolist(),
            "x_scale": np.round(self.x_scale, 12).tolist(),
            "y_mean": np.round(self.y_mean, 12).tolist(),
            "y_scale": np.round(self.y_scale, 12).tolist(),
            "coefficients": np.round(self.coefficients, 12).tolist(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class AdaptationValidation:
    sample_count: int
    baseline_mse: tuple[float, ...]
    adaptive_mse: tuple[float, ...]
    incremental_information_bps: tuple[int, ...]
    pooled_incremental_information_bps: int
    positive_target_count: int
    maximum_target_regression_bps: int
    pass_gate: bool


def adaptive_interactions(baseline: np.ndarray) -> np.ndarray:
    """Build the six preregistered target-blind interaction features."""

    if baseline.ndim != 2 or baseline.shape[1] != len(BASELINE_FEATURE_NAMES):
        raise ValueError("baseline feature matrix shape drift")
    idx = {name: i for i, name in enumerate(BASELINE_FEATURE_NAMES)}
    x = baseline
    one = np.ones(x.shape[0], dtype=np.float64)
    interactions = np.column_stack(
        (
            x[:, idx["anomaly"]] * x[:, idx["regime_transition"]],
            x[:, idx["leader_divergence"]] * x[:, idx["structural_fragility"]],
            x[:, idx["liquidity_vacuum"]] * x[:, idx["anomaly"]],
            x[:, idx["momentum_persistence"]]
            * (one - x[:, idx["momentum_decay"]]),
            x[:, idx["displacement"]] * x[:, idx["acceptance"]],
            x[:, idx["compression"]] * x[:, idx["liquidity_accumulation"]],
        )
    )
    return np.asarray(interactions, dtype=np.float64)


def build_adaptive_design(baseline: np.ndarray) -> np.ndarray:
    interactions = adaptive_interactions(baseline)
    return np.hstack((baseline, interactions))


def _safe_scale(values: np.ndarray) -> np.ndarray:
    scale = np.asarray(values.std(axis=0), dtype=np.float64)
    return np.where(scale > 1e-12, scale, 1.0)


def fit_frozen_ridge_projection(
    *,
    features: np.ndarray,
    targets: np.ndarray,
    feature_names: tuple[str, ...],
) -> FrozenRidgeProjection:
    if features.ndim != 2 or targets.ndim != 2:
        raise ValueError("features and targets must be matrices")
    if features.shape[0] != targets.shape[0] or features.shape[0] < 2:
        raise ValueError("fit requires aligned non-trivial samples")
    if features.shape[1] != len(feature_names):
        raise ValueError("feature name cardinality drift")
    if targets.shape[1] != len(TARGET_NAMES):
        raise ValueError("target cardinality drift")
    if not np.isfinite(features).all() or not np.isfinite(targets).all():
        raise ValueError("fit matrices must be finite")

    x_mean = np.asarray(features.mean(axis=0), dtype=np.float64)
    x_scale = _safe_scale(features)
    y_mean = np.asarray(targets.mean(axis=0), dtype=np.float64)
    y_scale = _safe_scale(targets)
    xz = (features - x_mean) / x_scale
    yz = (targets - y_mean) / y_scale
    design = np.column_stack((np.ones(xz.shape[0]), xz))
    gram = design.T @ design
    penalty = np.eye(gram.shape[0], dtype=np.float64) * RIDGE_LAMBDA
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(
        gram + penalty,
        design.T @ yz,
    )
    for array in (x_mean, x_scale, y_mean, y_scale, coefficients):
        array.setflags(write=False)
    return FrozenRidgeProjection(
        feature_names=feature_names,
        target_names=TARGET_NAMES,
        x_mean=x_mean,
        x_scale=x_scale,
        y_mean=y_mean,
        y_scale=y_scale,
        coefficients=coefficients,
        ridge_lambda=RIDGE_LAMBDA,
    )


def predict_target_z(
    model: FrozenRidgeProjection,
    features: np.ndarray,
) -> np.ndarray:
    if features.ndim != 2 or features.shape[1] != len(model.feature_names):
        raise ValueError("prediction feature shape drift")
    xz = (features - model.x_mean) / model.x_scale
    design = np.column_stack((np.ones(xz.shape[0]), xz))
    return np.asarray(design @ model.coefficients, dtype=np.float64)


def target_z(model: FrozenRidgeProjection, targets: np.ndarray) -> np.ndarray:
    if targets.ndim != 2 or targets.shape[1] != len(model.target_names):
        raise ValueError("target matrix shape drift")
    return np.asarray((targets - model.y_mean) / model.y_scale, dtype=np.float64)


def _incremental_bps(baseline: float, adaptive: float) -> int:
    if baseline <= 0:
        return 0
    return int(round((baseline - adaptive) / baseline * 10_000))


def evaluate_adaptation(
    *,
    baseline_model: FrozenRidgeProjection,
    adaptive_model: FrozenRidgeProjection,
    baseline_features: np.ndarray,
    adaptive_features: np.ndarray,
    targets: np.ndarray,
) -> AdaptationValidation:
    if baseline_features.shape[0] != adaptive_features.shape[0]:
        raise ValueError("baseline/adaptive sample mismatch")
    if baseline_features.shape[0] != targets.shape[0]:
        raise ValueError("feature/target sample mismatch")

    baseline_truth = target_z(baseline_model, targets)
    adaptive_truth = target_z(adaptive_model, targets)
    if not np.allclose(baseline_truth, adaptive_truth, rtol=0.0, atol=1e-12):
        raise ValueError("baseline/adaptive target normalization drift")

    baseline_pred = predict_target_z(baseline_model, baseline_features)
    adaptive_pred = predict_target_z(adaptive_model, adaptive_features)
    baseline_mse_array = np.mean((baseline_truth - baseline_pred) ** 2, axis=0)
    adaptive_mse_array = np.mean((adaptive_truth - adaptive_pred) ** 2, axis=0)
    increments = tuple(
        _incremental_bps(float(base), float(adapt))
        for base, adapt in zip(baseline_mse_array, adaptive_mse_array, strict=True)
    )
    pooled_baseline = float(np.mean(baseline_mse_array))
    pooled_adaptive = float(np.mean(adaptive_mse_array))
    pooled_incremental = _incremental_bps(pooled_baseline, pooled_adaptive)
    positive = sum(value >= 1 for value in increments)
    max_regression = max((max(0, -value) for value in increments), default=0)
    passed = (
        baseline_features.shape[0] >= MINIMUM_R5_SCORED_OBSERVATIONS
        and positive >= MINIMUM_POSITIVE_TARGETS
        and pooled_incremental >= MINIMUM_POOLED_INCREMENTAL_BPS
        and max_regression <= MAXIMUM_TARGET_REGRESSION_BPS
    )
    return AdaptationValidation(
        sample_count=baseline_features.shape[0],
        baseline_mse=tuple(float(x) for x in baseline_mse_array),
        adaptive_mse=tuple(float(x) for x in adaptive_mse_array),
        incremental_information_bps=increments,
        pooled_incremental_information_bps=pooled_incremental,
        positive_target_count=positive,
        maximum_target_regression_bps=max_regression,
        pass_gate=passed,
    )
