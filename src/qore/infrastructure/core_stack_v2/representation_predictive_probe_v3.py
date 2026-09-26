"""Frozen incremental-information probe for WP-04 predictive representation V3.

The temporal representation is learned first from generic source->future market
transitions on consumed research evidence. Named evaluation targets are used
only after the representation is frozen.

The probe asks whether the frozen temporal concepts add information beyond the
existing ontology. It has no runtime trading authority and a fresh holdout may
never refit either the representation or the probe.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite, tanh

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationEpisode,
)
from qore.infrastructure.core_stack_v2.representation_discovery_evaluation import (
    RepresentationEvaluationTarget,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    PredictiveRepresentationModel,
    project_predictive_representation,
)


@dataclass(frozen=True, slots=True)
class PredictiveIncrementalProbe:
    fitted_at: datetime
    calibration_partitions: tuple[str, ...]
    target_name: str
    representation_fingerprint: str
    ontology_names: tuple[str, ...]
    concept_ids: tuple[str, ...]
    baseline_coefficients_micros: tuple[int, ...]
    augmented_coefficients_micros: tuple[int, ...]
    probe_fingerprint: str
    representation_training_future_only: bool = True
    runtime_future_market_used: bool = False
    holdout_used_for_fit: bool = False
    identity_used: bool = False
    knowledge_promotion_authority: bool = False
    methodology_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.fitted_at.tzinfo is None or self.fitted_at.utcoffset() is None:
            raise ValueError("probe fitted_at must be timezone-aware")
        if not self.calibration_partitions:
            raise ValueError("probe calibration partitions must be non-empty")
        if len(set(self.calibration_partitions)) != len(self.calibration_partitions):
            raise ValueError("probe calibration partitions must be unique")
        if not self.target_name:
            raise ValueError("probe target name must be non-empty")
        if len(self.representation_fingerprint) != 64:
            raise ValueError("representation fingerprint must be sha256")
        if len(self.probe_fingerprint) != 64:
            raise ValueError("probe fingerprint must be sha256")
        if not self.representation_training_future_only:
            raise ValueError("V3 probe must preserve training-only future semantics")
        if (
            self.runtime_future_market_used
            or self.holdout_used_for_fit
            or self.identity_used
            or self.knowledge_promotion_authority
            or self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("predictive probe cannot leak future/identity or authority")


@dataclass(frozen=True, slots=True)
class PredictiveIncrementalEvaluation:
    partition: str
    target_name: str
    sample_count: int
    baseline_mse_micros: int
    augmented_mse_micros: int
    incremental_information_bps: int
    probe_fingerprint: str
    holdout_refit: bool = False
    runtime_future_market_used: bool = False
    identity_used: bool = False
    knowledge_promotion_authority: bool = False

    def __post_init__(self) -> None:
        if not self.partition or not self.target_name:
            raise ValueError("evaluation partition and target name are required")
        if self.sample_count < 1:
            raise ValueError("evaluation sample_count must be positive")
        if self.baseline_mse_micros < 0 or self.augmented_mse_micros < 0:
            raise ValueError("evaluation MSE cannot be negative")
        if len(self.probe_fingerprint) != 64:
            raise ValueError("probe fingerprint must be sha256")
        if (
            self.holdout_refit
            or self.runtime_future_market_used
            or self.identity_used
            or self.knowledge_promotion_authority
        ):
            raise ValueError("evaluation cannot refit, leak future, or promote")


def predictive_representation_fingerprint(
    model: PredictiveRepresentationModel,
) -> str:
    payload = (
        model.horizon_minutes,
        model.discovery_partition,
        model.development_partitions,
        model.feature_names,
        model.ontology_names,
        tuple(round(value, 12) for value in model.feature_centers),
        tuple(round(value, 12) for value in model.feature_scales),
        tuple(round(value, 12) for value in model.ontology_centers),
        tuple(round(value, 12) for value in model.ontology_scales),
        round(model.robust_width, 12),
        tuple(
            (item.feature_name, item.ontology_coefficients_micros)
            for item in model.residualizers
        ),
        tuple(round(value, 12) for value in model.residual_centers),
        tuple(
            (
                concept.concept_id,
                concept.source_loading_micros,
                concept.future_profile_micros,
                concept.discovery_predictive_strength_bps,
                concept.temporal_invariance_bps,
            )
            for concept in model.concepts
        ),
    )
    return sha256(repr(payload).encode()).hexdigest()


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(
            range(column, size),
            key=lambda row: abs(augmented[row][column]),
        )
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("predictive probe linear system is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if abs(factor) < 1e-15:
                continue
            augmented[row] = [
                left - factor * right
                for left, right in zip(
                    augmented[row],
                    augmented[column],
                    strict=True,
                )
            ]
    return [augmented[row][-1] for row in range(size)]


def _ridge_fit(
    rows: list[list[float]],
    target: list[float],
    *,
    ridge: float,
) -> tuple[float, ...]:
    width = len(rows[0])
    gram = [[0.0 for _ in range(width)] for _ in range(width)]
    rhs = [0.0 for _ in range(width)]
    for row, value in zip(rows, target, strict=True):
        for left in range(width):
            rhs[left] += row[left] * value
            for right in range(width):
                gram[left][right] += row[left] * row[right]
    for index in range(width):
        gram[index][index] += ridge * len(rows)
    return tuple(_solve(gram, rhs))


def _ontology_vector(
    model: PredictiveRepresentationModel,
    episode: RepresentationEpisode,
) -> list[float]:
    mapping = {item.name: item.value for item in episode.ontology}
    if set(mapping) != set(model.ontology_names):
        raise ValueError("ontology schema drift is forbidden")
    bounded = [
        tanh(
            (mapping[name] - model.ontology_centers[index])
            / (model.ontology_scales[index] * model.robust_width)
        )
        for index, name in enumerate(model.ontology_names)
    ]
    return [1.0] + bounded


def _design(
    model: PredictiveRepresentationModel,
    episode: RepresentationEpisode,
    *,
    augmented: bool,
) -> list[float]:
    baseline = _ontology_vector(model, episode)
    if not augmented:
        return baseline
    latent = project_predictive_representation(model=model, episode=episode)
    activations = {
        item.concept_id: item.activation_milli_z / 1_000.0
        for item in latent.activations
    }
    return baseline + [
        activations[concept.concept_id]
        for concept in model.concepts
    ]


def _matched(
    *,
    episodes: Sequence[RepresentationEpisode],
    targets: Sequence[RepresentationEvaluationTarget],
) -> list[tuple[RepresentationEpisode, RepresentationEvaluationTarget]]:
    target_by_id = {item.episode_id: item for item in targets}
    if len(target_by_id) != len(targets):
        raise ValueError("target episode ids must be unique")
    rows = [
        (episode, target_by_id[episode.episode_id])
        for episode in episodes
        if episode.episode_id in target_by_id
    ]
    if not rows:
        raise ValueError("probe requires matched episodes and targets")
    for episode, target in rows:
        if target.observed_at <= episode.as_of:
            raise ValueError("probe target must mature after source episode")
    return rows


def _fingerprint_probe(
    *,
    representation_fingerprint: str,
    calibration_partitions: tuple[str, ...],
    target_name: str,
    ontology_names: tuple[str, ...],
    concept_ids: tuple[str, ...],
    baseline: tuple[int, ...],
    augmented: tuple[int, ...],
) -> str:
    payload = (
        representation_fingerprint,
        calibration_partitions,
        target_name,
        ontology_names,
        concept_ids,
        baseline,
        augmented,
    )
    return sha256(repr(payload).encode()).hexdigest()


def fit_predictive_incremental_probe(
    *,
    model: PredictiveRepresentationModel,
    fitted_at: datetime,
    calibration_partitions: tuple[str, ...],
    target_name: str,
    episodes: tuple[RepresentationEpisode, ...],
    targets: tuple[RepresentationEvaluationTarget, ...],
    ridge: float = 1.0,
) -> PredictiveIncrementalProbe:
    if fitted_at.tzinfo is None or fitted_at.utcoffset() is None:
        raise ValueError("probe fitted_at must be timezone-aware")
    if ridge <= 0:
        raise ValueError("ridge must be positive")
    if not calibration_partitions:
        raise ValueError("calibration_partitions must be non-empty")
    if any(
        episode.partition not in calibration_partitions
        for episode in episodes
    ):
        raise ValueError("probe fit contains undeclared partition")

    rows = _matched(episodes=episodes, targets=targets)
    if any(target.observed_at > fitted_at for _, target in rows):
        raise ValueError("future calibration target is forbidden")
    minimum = 4 * (1 + len(model.ontology_names) + len(model.concepts))
    if len(rows) < minimum:
        raise ValueError("insufficient calibration rows for predictive probe")

    baseline_design = [
        _design(model, episode, augmented=False)
        for episode, _target in rows
    ]
    augmented_design = [
        _design(model, episode, augmented=True)
        for episode, _target in rows
    ]
    response = [target.value for _episode, target in rows]
    baseline_float = _ridge_fit(baseline_design, response, ridge=ridge)
    augmented_float = _ridge_fit(augmented_design, response, ridge=ridge)
    baseline = tuple(int(round(value * 1_000_000)) for value in baseline_float)
    augmented = tuple(int(round(value * 1_000_000)) for value in augmented_float)

    representation_fingerprint = predictive_representation_fingerprint(model)
    concept_ids = tuple(item.concept_id for item in model.concepts)
    probe_fingerprint = _fingerprint_probe(
        representation_fingerprint=representation_fingerprint,
        calibration_partitions=calibration_partitions,
        target_name=target_name,
        ontology_names=model.ontology_names,
        concept_ids=concept_ids,
        baseline=baseline,
        augmented=augmented,
    )
    return PredictiveIncrementalProbe(
        fitted_at=fitted_at,
        calibration_partitions=calibration_partitions,
        target_name=target_name,
        representation_fingerprint=representation_fingerprint,
        ontology_names=model.ontology_names,
        concept_ids=concept_ids,
        baseline_coefficients_micros=baseline,
        augmented_coefficients_micros=augmented,
        probe_fingerprint=probe_fingerprint,
    )


def _predict(coefficients_micros: tuple[int, ...], row: list[float]) -> float:
    if len(coefficients_micros) != len(row):
        raise ValueError("predictive probe coefficient shape mismatch")
    prediction = sum(
        coefficient / 1_000_000.0 * value
        for coefficient, value in zip(coefficients_micros, row, strict=True)
    )
    if not isfinite(prediction):
        raise ValueError("non-finite predictive probe prediction")
    return prediction


def evaluate_predictive_incremental_probe(
    *,
    model: PredictiveRepresentationModel,
    probe: PredictiveIncrementalProbe,
    partition: str,
    episodes: tuple[RepresentationEpisode, ...],
    targets: tuple[RepresentationEvaluationTarget, ...],
) -> PredictiveIncrementalEvaluation:
    if partition in probe.calibration_partitions:
        raise ValueError("evaluation partition was used for probe fitting")
    if any(item.partition != partition for item in episodes):
        raise ValueError("evaluation cannot mix partitions")
    if probe.representation_fingerprint != predictive_representation_fingerprint(
        model
    ):
        raise ValueError("representation fingerprint drift")
    if probe.ontology_names != model.ontology_names:
        raise ValueError("probe ontology drift")
    if probe.concept_ids != tuple(item.concept_id for item in model.concepts):
        raise ValueError("probe concept drift")

    rows = _matched(episodes=episodes, targets=targets)
    baseline_errors: list[float] = []
    augmented_errors: list[float] = []
    for episode, target in rows:
        baseline = _predict(
            probe.baseline_coefficients_micros,
            _design(model, episode, augmented=False),
        )
        augmented = _predict(
            probe.augmented_coefficients_micros,
            _design(model, episode, augmented=True),
        )
        baseline_errors.append((target.value - baseline) ** 2)
        augmented_errors.append((target.value - augmented) ** 2)

    baseline_mse = sum(baseline_errors) / len(baseline_errors)
    augmented_mse = sum(augmented_errors) / len(augmented_errors)
    incremental = 0
    if baseline_mse > 1e-12:
        incremental = int(
            round((baseline_mse - augmented_mse) / baseline_mse * 10_000)
        )
    return PredictiveIncrementalEvaluation(
        partition=partition,
        target_name=probe.target_name,
        sample_count=len(rows),
        baseline_mse_micros=max(0, int(round(baseline_mse * 1_000_000))),
        augmented_mse_micros=max(0, int(round(augmented_mse * 1_000_000))),
        incremental_information_bps=incremental,
        probe_fingerprint=probe.probe_fingerprint,
    )
