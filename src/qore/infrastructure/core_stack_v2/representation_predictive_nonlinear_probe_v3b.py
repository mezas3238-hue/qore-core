"""WP-04 V3B symmetric second-order incremental-information probe.

V3 showed that a target-blind temporal representation can be stable across
consumed partitions, while a linear decoder fails to extract consistent
incremental information. V3B tests a narrower hypothesis: latent information
may be nonlinearly decodable.

The comparison is symmetric and fixed before evaluation:
- baseline: intercept + ontology linear + ontology squares + ontology pairs;
- augmented: exact baseline + latent linear + latent squares + latent pairs
  + ontology-by-latent interactions.

Representation learning is unchanged. No target-specific representation
selection or threshold search occurs. Holdout evaluation may never refit this
probe.
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
from qore.infrastructure.core_stack_v2.representation_predictive_probe_v3 import (
    predictive_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    PredictiveRepresentationModel,
    project_predictive_representation,
)

BASIS_ID = "SYMMETRIC_SECOND_ORDER_V1"


@dataclass(frozen=True, slots=True)
class PredictiveSecondOrderProbe:
    fitted_at: datetime
    calibration_partitions: tuple[str, ...]
    target_name: str
    representation_fingerprint: str
    ontology_names: tuple[str, ...]
    concept_ids: tuple[str, ...]
    basis_id: str
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
            raise ValueError("calibration_partitions must be non-empty")
        if len(set(self.calibration_partitions)) != len(self.calibration_partitions):
            raise ValueError("calibration_partitions must be unique")
        if not self.target_name:
            raise ValueError("target_name must be non-empty")
        if self.basis_id != BASIS_ID:
            raise ValueError("unexpected V3B basis")
        if len(self.representation_fingerprint) != 64:
            raise ValueError("representation fingerprint must be sha256")
        if len(self.probe_fingerprint) != 64:
            raise ValueError("probe fingerprint must be sha256")
        if not self.representation_training_future_only:
            raise ValueError("V3B must preserve training-only future semantics")
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
            raise ValueError("V3B probe cannot leak future/identity or authority")


@dataclass(frozen=True, slots=True)
class PredictiveSecondOrderEvaluation:
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
            raise ValueError("partition and target_name are required")
        if self.sample_count < 1:
            raise ValueError("sample_count must be positive")
        if self.baseline_mse_micros < 0 or self.augmented_mse_micros < 0:
            raise ValueError("MSE cannot be negative")
        if len(self.probe_fingerprint) != 64:
            raise ValueError("probe fingerprint must be sha256")
        if (
            self.holdout_refit
            or self.runtime_future_market_used
            or self.identity_used
            or self.knowledge_promotion_authority
        ):
            raise ValueError("evaluation cannot refit, leak future, or promote")


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(
            range(column, size),
            key=lambda row: abs(augmented[row][column]),
        )
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("V3B linear system is singular")
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


def _bounded_ontology(
    model: PredictiveRepresentationModel,
    episode: RepresentationEpisode,
) -> list[float]:
    mapping = {item.name: item.value for item in episode.ontology}
    if set(mapping) != set(model.ontology_names):
        raise ValueError("ontology schema drift is forbidden")
    return [
        tanh(
            (mapping[name] - model.ontology_centers[index])
            / (model.ontology_scales[index] * model.robust_width)
        )
        for index, name in enumerate(model.ontology_names)
    ]


def _bounded_latent(
    model: PredictiveRepresentationModel,
    episode: RepresentationEpisode,
) -> list[float]:
    representation = project_predictive_representation(
        model=model,
        episode=episode,
    )
    mapping = {
        item.concept_id: tanh(item.activation_milli_z / 1_000.0)
        for item in representation.activations
    }
    expected = tuple(item.concept_id for item in model.concepts)
    if set(mapping) != set(expected):
        raise ValueError("latent concept drift is forbidden")
    return [mapping[concept_id] for concept_id in expected]


def _second_order(values: Sequence[float]) -> list[float]:
    result = list(values)
    result.extend(value * value for value in values)
    for left in range(len(values)):
        for right in range(left + 1, len(values)):
            result.append(values[left] * values[right])
    return result


def _baseline_design(
    model: PredictiveRepresentationModel,
    episode: RepresentationEpisode,
) -> list[float]:
    ontology = _bounded_ontology(model, episode)
    return [1.0] + _second_order(ontology)


def _augmented_design(
    model: PredictiveRepresentationModel,
    episode: RepresentationEpisode,
) -> list[float]:
    ontology = _bounded_ontology(model, episode)
    latent = _bounded_latent(model, episode)
    result = [1.0] + _second_order(ontology)
    result.extend(_second_order(latent))
    result.extend(
        ontology_value * latent_value
        for ontology_value in ontology
        for latent_value in latent
    )
    return result


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
        raise ValueError("V3B requires matched episodes and targets")
    if any(target.observed_at <= episode.as_of for episode, target in rows):
        raise ValueError("target must mature after source episode")
    return rows


def _probe_fingerprint(
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
        BASIS_ID,
        representation_fingerprint,
        calibration_partitions,
        target_name,
        ontology_names,
        concept_ids,
        baseline,
        augmented,
    )
    return sha256(repr(payload).encode()).hexdigest()


def fit_predictive_second_order_probe(
    *,
    model: PredictiveRepresentationModel,
    fitted_at: datetime,
    calibration_partitions: tuple[str, ...],
    target_name: str,
    episodes: tuple[RepresentationEpisode, ...],
    targets: tuple[RepresentationEvaluationTarget, ...],
    ridge: float = 1.0,
) -> PredictiveSecondOrderProbe:
    if fitted_at.tzinfo is None or fitted_at.utcoffset() is None:
        raise ValueError("fitted_at must be timezone-aware")
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

    baseline_rows = [
        _baseline_design(model, episode)
        for episode, _target in rows
    ]
    augmented_rows = [
        _augmented_design(model, episode)
        for episode, _target in rows
    ]
    minimum = 4 * len(augmented_rows[0])
    if len(rows) < minimum:
        raise ValueError("insufficient calibration rows for V3B probe")

    response = [target.value for _episode, target in rows]
    baseline_float = _ridge_fit(baseline_rows, response, ridge=ridge)
    augmented_float = _ridge_fit(augmented_rows, response, ridge=ridge)
    baseline = tuple(int(round(value * 1_000_000)) for value in baseline_float)
    augmented = tuple(int(round(value * 1_000_000)) for value in augmented_float)

    representation_fingerprint = predictive_representation_fingerprint(model)
    concept_ids = tuple(item.concept_id for item in model.concepts)
    probe_fingerprint = _probe_fingerprint(
        representation_fingerprint=representation_fingerprint,
        calibration_partitions=calibration_partitions,
        target_name=target_name,
        ontology_names=model.ontology_names,
        concept_ids=concept_ids,
        baseline=baseline,
        augmented=augmented,
    )
    return PredictiveSecondOrderProbe(
        fitted_at=fitted_at,
        calibration_partitions=calibration_partitions,
        target_name=target_name,
        representation_fingerprint=representation_fingerprint,
        ontology_names=model.ontology_names,
        concept_ids=concept_ids,
        basis_id=BASIS_ID,
        baseline_coefficients_micros=baseline,
        augmented_coefficients_micros=augmented,
        probe_fingerprint=probe_fingerprint,
    )


def _predict(coefficients: tuple[int, ...], row: list[float]) -> float:
    if len(coefficients) != len(row):
        raise ValueError("V3B coefficient shape mismatch")
    prediction = sum(
        coefficient / 1_000_000.0 * value
        for coefficient, value in zip(coefficients, row, strict=True)
    )
    if not isfinite(prediction):
        raise ValueError("non-finite V3B prediction")
    return prediction


def evaluate_predictive_second_order_probe(
    *,
    model: PredictiveRepresentationModel,
    probe: PredictiveSecondOrderProbe,
    partition: str,
    episodes: tuple[RepresentationEpisode, ...],
    targets: tuple[RepresentationEvaluationTarget, ...],
) -> PredictiveSecondOrderEvaluation:
    if partition in probe.calibration_partitions:
        raise ValueError("evaluation partition was used for probe fitting")
    if any(item.partition != partition for item in episodes):
        raise ValueError("evaluation cannot mix partitions")
    if probe.representation_fingerprint != predictive_representation_fingerprint(
        model
    ):
        raise ValueError("representation fingerprint drift")
    if probe.basis_id != BASIS_ID:
        raise ValueError("basis drift")
    if probe.ontology_names != model.ontology_names:
        raise ValueError("ontology drift")
    if probe.concept_ids != tuple(item.concept_id for item in model.concepts):
        raise ValueError("concept drift")

    rows = _matched(episodes=episodes, targets=targets)
    baseline_errors: list[float] = []
    augmented_errors: list[float] = []
    for episode, target in rows:
        baseline_prediction = _predict(
            probe.baseline_coefficients_micros,
            _baseline_design(model, episode),
        )
        augmented_prediction = _predict(
            probe.augmented_coefficients_micros,
            _augmented_design(model, episode),
        )
        baseline_errors.append((target.value - baseline_prediction) ** 2)
        augmented_errors.append((target.value - augmented_prediction) ** 2)

    baseline_mse = sum(baseline_errors) / len(baseline_errors)
    augmented_mse = sum(augmented_errors) / len(augmented_errors)
    incremental = 0
    if baseline_mse > 1e-12:
        incremental = int(
            round((baseline_mse - augmented_mse) / baseline_mse * 10_000)
        )
    return PredictiveSecondOrderEvaluation(
        partition=partition,
        target_name=probe.target_name,
        sample_count=len(rows),
        baseline_mse_micros=max(0, int(round(baseline_mse * 1_000_000))),
        augmented_mse_micros=max(0, int(round(augmented_mse * 1_000_000))),
        incremental_information_bps=incremental,
        probe_fingerprint=probe.probe_fingerprint,
    )
