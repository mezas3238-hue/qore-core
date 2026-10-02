"""Evaluation-only incremental-information gate for WP-04.

Representation discovery itself is target-blind. This module is deliberately
separate: after a representation has been frozen on a discovery partition, a
probe may use matured future labels from that same consumed calibration
partition to ask whether latent activations add predictive information beyond
the existing ontology. The fitted probe is then frozen and evaluated unchanged
on later holdouts.

This layer never promotes concepts into runtime knowledge and carries no
methodology, sizing, Risk, order or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationDiscoveryModel,
    RepresentationEpisode,
    project_representation,
)


@dataclass(frozen=True, slots=True)
class RepresentationEvaluationTarget:
    episode_id: str
    observed_at: datetime
    value: float

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("episode_id must be non-empty")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("target observed_at must be timezone-aware")
        if not isfinite(self.value):
            raise ValueError("target value must be finite")


@dataclass(frozen=True, slots=True)
class IncrementalRepresentationProbe:
    fitted_at: datetime
    calibration_partition: str
    target_name: str
    ontology_names: tuple[str, ...]
    concept_ids: tuple[str, ...]
    baseline_coefficients_micros: tuple[int, ...]
    augmented_coefficients_micros: tuple[int, ...]
    representation_target_blind: bool = True
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
        if not self.calibration_partition or not self.target_name:
            raise ValueError("probe partition and target name must be non-empty")
        if not self.representation_target_blind or self.holdout_used_for_fit:
            raise ValueError("probe must preserve target-blind representation")
        if (
            self.identity_used
            or self.knowledge_promotion_authority
            or self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("representation probe cannot carry authority")


@dataclass(frozen=True, slots=True)
class IncrementalRepresentationEvaluation:
    partition: str
    target_name: str
    sample_count: int
    baseline_mse_micros: int
    augmented_mse_micros: int
    incremental_information_bps: int
    holdout_refit: bool = False
    identity_used: bool = False
    knowledge_promotion_authority: bool = False

    def __post_init__(self) -> None:
        if not self.partition or not self.target_name:
            raise ValueError("evaluation partition and target name must be non-empty")
        if self.sample_count < 1:
            raise ValueError("sample_count must be positive")
        if self.baseline_mse_micros < 0 or self.augmented_mse_micros < 0:
            raise ValueError("MSE cannot be negative")
        if (
            self.holdout_refit
            or self.identity_used
            or self.knowledge_promotion_authority
        ):
            raise ValueError("holdout evaluation cannot refit or promote knowledge")


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(
            range(column, size),
            key=lambda row: abs(augmented[row][column]),
        )
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("representation probe linear system is singular")
        augmented[column], augmented[pivot] = (
            augmented[pivot],
            augmented[column],
        )
        divisor = augmented[column][column]
        augmented[column] = [
            value / divisor for value in augmented[column]
        ]
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
    model: RepresentationDiscoveryModel,
    episode: RepresentationEpisode,
) -> list[float]:
    mapping = {item.name: item.value for item in episode.ontology}
    if set(mapping) != set(model.ontology_names):
        raise ValueError("ontology schema drift is forbidden")
    standardized = [
        (mapping[name] - model.ontology_means[index])
        / model.ontology_scales[index]
        for index, name in enumerate(model.ontology_names)
    ]
    return [1.0] + standardized


def _design(
    model: RepresentationDiscoveryModel,
    episode: RepresentationEpisode,
    *,
    augmented: bool,
) -> list[float]:
    baseline = _ontology_vector(model, episode)
    if not augmented:
        return baseline
    latent = project_representation(model=model, episode=episode)
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
    episodes: tuple[RepresentationEpisode, ...],
    targets: tuple[RepresentationEvaluationTarget, ...],
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
        raise ValueError("evaluation requires matched episodes and targets")
    for episode, target in rows:
        if target.observed_at <= episode.as_of:
            raise ValueError("evaluation target must mature after source episode")
    return rows


def fit_incremental_representation_probe(
    *,
    model: RepresentationDiscoveryModel,
    fitted_at: datetime,
    calibration_partition: str,
    target_name: str,
    episodes: tuple[RepresentationEpisode, ...],
    targets: tuple[RepresentationEvaluationTarget, ...],
    ridge: float = 1.0,
) -> IncrementalRepresentationProbe:
    """Fit ontology-only and ontology+latent probes on one consumed partition."""

    if fitted_at.tzinfo is None or fitted_at.utcoffset() is None:
        raise ValueError("probe fitted_at must be timezone-aware")
    if ridge <= 0:
        raise ValueError("ridge must be positive")
    if calibration_partition != model.discovery_partition:
        raise ValueError("probe calibration must match discovery partition")
    if any(item.partition != calibration_partition for item in episodes):
        raise ValueError("probe fit cannot mix partitions")

    rows = _matched(episodes=episodes, targets=targets)
    if any(target.observed_at > fitted_at for _, target in rows):
        raise ValueError("future calibration target is forbidden")
    minimum = 4 * (
        1 + len(model.ontology_names) + len(model.concepts)
    )
    if len(rows) < minimum:
        raise ValueError("insufficient calibration rows for representation probe")

    baseline_design = [
        _design(model, episode, augmented=False)
        for episode, _ in rows
    ]
    augmented_design = [
        _design(model, episode, augmented=True)
        for episode, _ in rows
    ]
    response = [target.value for _, target in rows]
    baseline = _ridge_fit(baseline_design, response, ridge=ridge)
    augmented = _ridge_fit(augmented_design, response, ridge=ridge)

    return IncrementalRepresentationProbe(
        fitted_at=fitted_at,
        calibration_partition=calibration_partition,
        target_name=target_name,
        ontology_names=model.ontology_names,
        concept_ids=tuple(item.concept_id for item in model.concepts),
        baseline_coefficients_micros=tuple(
            int(round(value * 1_000_000))
            for value in baseline
        ),
        augmented_coefficients_micros=tuple(
            int(round(value * 1_000_000))
            for value in augmented
        ),
    )


def _predict(coefficients_micros: tuple[int, ...], row: list[float]) -> float:
    if len(coefficients_micros) != len(row):
        raise ValueError("representation probe coefficient shape mismatch")
    return sum(
        coefficient / 1_000_000.0 * value
        for coefficient, value in zip(
            coefficients_micros,
            row,
            strict=True,
        )
    )


def evaluate_incremental_representation(
    *,
    model: RepresentationDiscoveryModel,
    probe: IncrementalRepresentationProbe,
    partition: str,
    episodes: tuple[RepresentationEpisode, ...],
    targets: tuple[RepresentationEvaluationTarget, ...],
) -> IncrementalRepresentationEvaluation:
    """Evaluate a frozen probe without using holdout data for refitting."""

    if partition == probe.calibration_partition:
        raise ValueError("out-of-sample evaluation requires a later partition")
    if any(item.partition != partition for item in episodes):
        raise ValueError("evaluation cannot mix partitions")
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
            round(
                (baseline_mse - augmented_mse)
                / baseline_mse
                * 10_000
            )
        )

    return IncrementalRepresentationEvaluation(
        partition=partition,
        target_name=probe.target_name,
        sample_count=len(rows),
        baseline_mse_micros=max(
            0,
            int(round(baseline_mse * 1_000_000)),
        ),
        augmented_mse_micros=max(
            0,
            int(round(augmented_mse * 1_000_000)),
        ),
        incremental_information_bps=incremental,
    )
