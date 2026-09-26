"""WP-04 V2 invariant residual representation for Shared Brain.

V1 selected residual concepts primarily because they explained variance in one
discovery partition. Historical falsification showed that a high-variance
component can be a partition-specific scale mode rather than a stable market
representation.

V2 changes the scientific question:

    does a residual concept preserve its source-only geometry across already
    consumed development partitions before any future target is consulted?

The representation remains generic and target-blind:
- only point-in-time sequence features and contemporaneous ontology enter;
- discovery normalization/residualization is fitted on one discovery partition;
- candidate concepts are generated from discovery residual covariance;
- consumed development partitions may reject candidates using source-only
  activation invariance, but cannot use future labels or trade outcomes;
- no trader, symbol, setup, account, side, PnL or outcome identity is a feature;
- no methodology, knowledge-promotion, sizing, Risk, order or execution
  authority exists here.

A concept that survives this module is still RESEARCH knowledge. Incremental
information must be measured later with a frozen probe on an independent
one-shot holdout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite, sqrt, tanh
from collections.abc import Mapping, Sequence
from statistics import median
from typing import Final

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    LatentConceptActivation,
    LatentRepresentation,
    RepresentationEpisode,
)

_BANNED_V2_IDENTITY_TOKENS: Final = (
    "SYMBOL_ID",
    "MARKET_ID",
    "INSTRUMENT_ID",
    "FOLD_ID",
    "PARTITION_ID",
)


@dataclass(frozen=True, slots=True)
class InvariantRepresentationPolicy:
    maximum_concepts: int = 6
    candidate_multiplier: int = 4
    minimum_episode_count_per_partition: int = 500
    minimum_integrity_bps: int = 9_500
    minimum_scale: float = 1e-9
    robust_width: float = 3.0
    residualization_ridge: float = 0.20
    minimum_candidate_variance_bps: int = 50
    power_iterations: int = 120
    minimum_loading_alignment_bps: int = 7_000
    minimum_scale_ratio: float = 0.50
    maximum_scale_ratio: float = 2.00
    maximum_median_shift_scale: float = 1.50
    cluster_episode_count: int = 12

    def __post_init__(self) -> None:
        if self.maximum_concepts < 1:
            raise ValueError("maximum_concepts must be positive")
        if self.candidate_multiplier < 1:
            raise ValueError("candidate_multiplier must be positive")
        if self.minimum_episode_count_per_partition < 10:
            raise ValueError(
                "minimum_episode_count_per_partition must be at least 10"
            )
        if not 0 <= self.minimum_integrity_bps <= 10_000:
            raise ValueError("minimum_integrity_bps must be within 0..10000")
        if self.minimum_scale <= 0:
            raise ValueError("minimum_scale must be positive")
        if self.robust_width <= 0:
            raise ValueError("robust_width must be positive")
        if self.residualization_ridge <= 0:
            raise ValueError("residualization_ridge must be positive")
        if not 0 <= self.minimum_candidate_variance_bps <= 10_000:
            raise ValueError(
                "minimum_candidate_variance_bps must be within 0..10000"
            )
        if self.power_iterations < 10:
            raise ValueError("power_iterations must be at least 10")
        if not 0 <= self.minimum_loading_alignment_bps <= 10_000:
            raise ValueError(
                "minimum_loading_alignment_bps must be within 0..10000"
            )
        if not 0 < self.minimum_scale_ratio <= 1:
            raise ValueError("minimum_scale_ratio must be within (0, 1]")
        if self.maximum_scale_ratio < 1:
            raise ValueError("maximum_scale_ratio must be at least 1")
        if self.minimum_scale_ratio > self.maximum_scale_ratio:
            raise ValueError("scale-ratio bounds are invalid")
        if self.maximum_median_shift_scale <= 0:
            raise ValueError("maximum_median_shift_scale must be positive")
        if self.cluster_episode_count < 1:
            raise ValueError("cluster_episode_count must be positive")


@dataclass(frozen=True, slots=True)
class InvarianceDiagnostic:
    partition: str
    episode_count: int
    loading_alignment_bps: int
    activation_scale_ratio_milli: int
    activation_median_shift_milli_scale: int
    scale_stability_bps: int
    median_stability_bps: int
    passes: bool

    def __post_init__(self) -> None:
        if not self.partition:
            raise ValueError("diagnostic partition must be non-empty")
        if self.episode_count < 1:
            raise ValueError("diagnostic episode_count must be positive")
        for value in (
            self.loading_alignment_bps,
            self.scale_stability_bps,
            self.median_stability_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("diagnostic bps must be within 0..10000")
        if self.activation_scale_ratio_milli < 0:
            raise ValueError("scale ratio cannot be negative")
        if self.activation_median_shift_milli_scale < 0:
            raise ValueError("median shift cannot be negative")


@dataclass(frozen=True, slots=True)
class InvariantResidualizer:
    feature_name: str
    ontology_coefficients_micros: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class InvariantLatentConcept:
    concept_id: str
    loading_micros: tuple[int, ...]
    discovery_explained_residual_variance_bps: int
    source_invariance_bps: int
    positive_probe_features: tuple[str, ...]
    negative_probe_features: tuple[str, ...]
    positive_cluster_episode_ids: tuple[str, ...]
    negative_cluster_episode_ids: tuple[str, ...]
    diagnostics: tuple[InvarianceDiagnostic, ...]

    def __post_init__(self) -> None:
        if not self.concept_id.startswith("LATENT_CONCEPT_"):
            raise ValueError("invariant concept id must remain provisional")
        if not self.loading_micros:
            raise ValueError("invariant concept requires loadings")
        if not 0 <= self.discovery_explained_residual_variance_bps <= 10_000:
            raise ValueError("explained variance must be within 0..10000")
        if not 0 <= self.source_invariance_bps <= 10_000:
            raise ValueError("source invariance must be within 0..10000")
        if not (self.positive_probe_features or self.negative_probe_features):
            raise ValueError("invariant concept requires interpretable probes")
        if not self.diagnostics:
            raise ValueError("invariant concept requires development diagnostics")
        if not all(item.passes for item in self.diagnostics):
            raise ValueError("selected invariant concept contains failed diagnostic")


@dataclass(frozen=True, slots=True)
class InvariantRepresentationModel:
    fitted_at: datetime
    evidence_cutoff_at: datetime
    discovery_partition: str
    development_partitions: tuple[str, ...]
    discovery_episode_count: int
    development_episode_counts: tuple[tuple[str, int], ...]
    feature_names: tuple[str, ...]
    ontology_names: tuple[str, ...]
    feature_centers: tuple[float, ...]
    feature_scales: tuple[float, ...]
    ontology_centers: tuple[float, ...]
    ontology_scales: tuple[float, ...]
    robust_width: float
    residualizers: tuple[InvariantResidualizer, ...]
    residual_centers: tuple[float, ...]
    concepts: tuple[InvariantLatentConcept, ...]
    candidate_count: int
    rejected_candidate_count: int
    target_used: bool = False
    future_market_used: bool = False
    outcome_used: bool = False
    pnl_used: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    partition_identity_as_feature_used: bool = False
    methodology_authority: bool = False
    knowledge_promotion_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for value, name in (
            (self.fitted_at, "fitted_at"),
            (self.evidence_cutoff_at, "evidence_cutoff_at"),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.fitted_at:
            raise ValueError("future source evidence is forbidden")
        if not self.discovery_partition:
            raise ValueError("discovery_partition must be non-empty")
        if not self.development_partitions:
            raise ValueError("development_partitions must be non-empty")
        if self.discovery_partition in self.development_partitions:
            raise ValueError("discovery partition cannot repeat as development")
        if len(set(self.development_partitions)) != len(
            self.development_partitions
        ):
            raise ValueError("development partitions must be unique")
        if self.discovery_episode_count < 1:
            raise ValueError("discovery_episode_count must be positive")
        if len(self.feature_names) != len(self.feature_centers):
            raise ValueError("feature center shape mismatch")
        if len(self.feature_names) != len(self.feature_scales):
            raise ValueError("feature scale shape mismatch")
        if len(self.ontology_names) != len(self.ontology_centers):
            raise ValueError("ontology center shape mismatch")
        if len(self.ontology_names) != len(self.ontology_scales):
            raise ValueError("ontology scale shape mismatch")
        if len(self.feature_names) != len(self.residualizers):
            raise ValueError("residualizer shape mismatch")
        if len(self.feature_names) != len(self.residual_centers):
            raise ValueError("residual center shape mismatch")
        if self.candidate_count < len(self.concepts):
            raise ValueError("candidate_count cannot be below selected concepts")
        if self.rejected_candidate_count != self.candidate_count - len(
            self.concepts
        ):
            raise ValueError("rejected candidate count mismatch")
        if (
            self.target_used
            or self.future_market_used
            or self.outcome_used
            or self.pnl_used
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.partition_identity_as_feature_used
            or self.methodology_authority
            or self.knowledge_promotion_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError(
                "invariant representation cannot use labels/identity "
                "or carry trading authority"
            )


def _ordered_values(
    episode: RepresentationEpisode,
    names: tuple[str, ...],
    *,
    ontology: bool,
) -> list[float]:
    source = episode.ontology if ontology else episode.features
    mapping = {item.name: item.value for item in source}
    if set(mapping) != set(names):
        kind = "ontology" if ontology else "feature"
        raise ValueError(f"{kind} schema drift is forbidden")
    return [mapping[name] for name in names]


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires values")
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    weight = position - left
    return ordered[left] * (1.0 - weight) + ordered[right] * weight


def _robust_center_scale(
    rows: list[list[float]],
    minimum_scale: float,
) -> tuple[list[float], list[float]]:
    width = len(rows[0])
    centers: list[float] = []
    scales: list[float] = []
    for column in range(width):
        values = [row[column] for row in rows]
        center = median(values)
        q25 = _percentile(values, 0.25)
        q75 = _percentile(values, 0.75)
        robust_sigma = (q75 - q25) / 1.349
        if robust_sigma < minimum_scale:
            deviations = [abs(value - center) for value in values]
            robust_sigma = median(deviations) * 1.4826
        centers.append(center)
        scales.append(max(minimum_scale, robust_sigma))
    return centers, scales


def _bounded_transform(
    rows: list[list[float]],
    centers: Sequence[float],
    scales: Sequence[float],
    robust_width: float,
) -> list[list[float]]:
    return [
        [
            tanh(
                (value - centers[column])
                / (scales[column] * robust_width)
            )
            for column, value in enumerate(row)
        ]
        for row in rows
    ]


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    augmented = [
        matrix[row][:] + [vector[row]]
        for row in range(n)
    ]
    for column in range(n):
        pivot = max(
            range(column, n),
            key=lambda row: abs(augmented[row][column]),
        )
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("invariant representation linear system is singular")
        augmented[column], augmented[pivot] = (
            augmented[pivot],
            augmented[column],
        )
        divisor = augmented[column][column]
        augmented[column] = [
            value / divisor for value in augmented[column]
        ]
        for row in range(n):
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
    return [augmented[row][-1] for row in range(n)]


def _ridge_coefficients(
    design: list[list[float]],
    target: list[float],
    ridge: float,
) -> list[float]:
    width = len(design[0])
    gram = [[0.0 for _ in range(width)] for _ in range(width)]
    rhs = [0.0 for _ in range(width)]
    for row, value in zip(design, target, strict=True):
        for left in range(width):
            rhs[left] += row[left] * value
            for right in range(width):
                gram[left][right] += row[left] * row[right]
    for index in range(width):
        gram[index][index] += ridge * len(design)
    return _solve(gram, rhs)


def _fit_residualizers(
    features: list[list[float]],
    ontology: list[list[float]],
    ridge: float,
) -> list[list[float]]:
    coefficients: list[list[float]] = []
    for feature_index in range(len(features[0])):
        coefficients.append(
            _ridge_coefficients(
                ontology,
                [row[feature_index] for row in features],
                ridge,
            )
        )
    return coefficients


def _residuals(
    features: list[list[float]],
    ontology: list[list[float]],
    coefficients: Sequence[Sequence[float]],
) -> list[list[float]]:
    rows: list[list[float]] = []
    for feature_row, ontology_row in zip(features, ontology, strict=True):
        residual_row: list[float] = []
        for feature_index, target in enumerate(feature_row):
            predicted = sum(
                coefficient * value
                for coefficient, value in zip(
                    coefficients[feature_index],
                    ontology_row,
                    strict=True,
                )
            )
            residual_row.append(target - predicted)
        rows.append(residual_row)
    return rows


def _center_columns(
    rows: list[list[float]],
    centers: Sequence[float] | None = None,
) -> tuple[list[list[float]], list[float]]:
    if centers is None:
        centers = [
            sum(row[column] for row in rows) / len(rows)
            for column in range(len(rows[0]))
        ]
    centered = [
        [
            value - centers[column]
            for column, value in enumerate(row)
        ]
        for row in rows
    ]
    return centered, list(centers)


def _covariance(rows: list[list[float]]) -> list[list[float]]:
    width = len(rows[0])
    result = [[0.0 for _ in range(width)] for _ in range(width)]
    denominator = max(1, len(rows) - 1)
    for row in rows:
        for left in range(width):
            for right in range(left, width):
                result[left][right] += row[left] * row[right]
    for left in range(width):
        for right in range(left, width):
            value = result[left][right] / denominator
            result[left][right] = value
            result[right][left] = value
    return result


def _matrix_vector(
    matrix: list[list[float]],
    vector: Sequence[float],
) -> list[float]:
    return [
        sum(value * vector[column] for column, value in enumerate(row))
        for row in matrix
    ]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _normalize(vector: Sequence[float]) -> list[float]:
    norm = sqrt(_dot(vector, vector))
    if norm < 1e-12:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def _candidate_components(
    covariance: list[list[float]],
    policy: InvariantRepresentationPolicy,
) -> list[tuple[float, int, list[float]]]:
    work = [row[:] for row in covariance]
    trace = sum(
        covariance[index][index]
        for index in range(len(covariance))
    )
    if trace <= 1e-12:
        return []

    maximum_candidates = min(
        len(covariance),
        policy.maximum_concepts * policy.candidate_multiplier,
    )
    result: list[tuple[float, int, list[float]]] = []
    for _ in range(maximum_candidates):
        seed = max(
            range(len(work)),
            key=lambda index: work[index][index],
        )
        vector = [
            1.0 if index == seed else 0.0
            for index in range(len(work))
        ]
        for _iteration in range(policy.power_iterations):
            updated = _normalize(_matrix_vector(work, vector))
            if not any(abs(value) > 1e-12 for value in updated):
                break
            delta = sum(
                abs(left - right)
                for left, right in zip(updated, vector, strict=True)
            )
            vector = updated
            if delta < 1e-10:
                break

        eigenvalue = max(0.0, _dot(vector, _matrix_vector(work, vector)))
        variance_bps = int(round(eigenvalue / trace * 10_000))
        if (
            eigenvalue <= 1e-12
            or variance_bps < policy.minimum_candidate_variance_bps
        ):
            break

        largest = max(
            range(len(vector)),
            key=lambda index: abs(vector[index]),
        )
        if vector[largest] < 0:
            vector = [-value for value in vector]
        result.append((eigenvalue, variance_bps, vector))
        for row in range(len(work)):
            for column in range(len(work)):
                work[row][column] -= (
                    eigenvalue * vector[row] * vector[column]
                )
    return result


def _activation(
    residual_rows: Sequence[Sequence[float]],
    vector: Sequence[float],
) -> list[float]:
    return [_dot(row, vector) for row in residual_rows]


def _mad(values: Sequence[float], minimum_scale: float) -> float:
    center = median(values)
    return max(
        minimum_scale,
        median(abs(value - center) for value in values) * 1.4826,
    )


def _correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("correlation shape mismatch")
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_scale = sqrt(sum(value * value for value in left_centered))
    right_scale = sqrt(sum(value * value for value in right_centered))
    if left_scale < 1e-12 or right_scale < 1e-12:
        return 0.0
    return _dot(left_centered, right_centered) / (left_scale * right_scale)


def _correlation_profile(
    activations: Sequence[float],
    residual_rows: Sequence[Sequence[float]],
) -> list[float]:
    return [
        _correlation(
            activations,
            [row[column] for row in residual_rows],
        )
        for column in range(len(residual_rows[0]))
    ]


def _cosine_bps(
    reference: Sequence[float],
    candidate: Sequence[float],
) -> int:
    left = sqrt(_dot(reference, reference))
    right = sqrt(_dot(candidate, candidate))
    if left < 1e-12 or right < 1e-12:
        return 0
    cosine = _dot(reference, candidate) / (left * right)
    return max(0, min(10_000, int(round(cosine * 10_000))))


def _scale_stability_bps(ratio: float) -> int:
    if ratio <= 0:
        return 0
    return max(
        0,
        min(10_000, int(round(min(ratio, 1.0 / ratio) * 10_000))),
    )


def _median_stability_bps(
    shift_scale: float,
    maximum_shift_scale: float,
) -> int:
    return max(
        0,
        min(
            10_000,
            int(
                round(
                    (1.0 - min(1.0, shift_scale / maximum_shift_scale))
                    * 10_000
                )
            ),
        ),
    )


def _concept_id(
    feature_names: Sequence[str],
    vector: Sequence[float],
) -> str:
    payload = "|".join(
        f"{name}:{int(round(value * 1_000_000))}"
        for name, value in zip(feature_names, vector, strict=True)
    )
    return "LATENT_CONCEPT_" + sha256(payload.encode()).hexdigest()[:12].upper()


def _probes(
    feature_names: Sequence[str],
    vector: Sequence[float],
    *,
    positive: bool,
) -> tuple[str, ...]:
    indexes = [
        index
        for index, value in enumerate(vector)
        if (value > 0 if positive else value < 0)
    ]
    indexes.sort(key=lambda index: abs(vector[index]), reverse=True)
    return tuple(feature_names[index] for index in indexes[:4])


def _eligible(
    episodes: Sequence[RepresentationEpisode],
    policy: InvariantRepresentationPolicy,
) -> tuple[RepresentationEpisode, ...]:
    return tuple(
        item
        for item in episodes
        if item.integrity_bps >= policy.minimum_integrity_bps
    )


def _identity_guard(names: Sequence[str]) -> None:
    for name in names:
        upper = name.upper()
        if any(token in upper for token in _BANNED_V2_IDENTITY_TOKENS):
            raise ValueError(f"identity shortcut feature is forbidden: {name}")


def fit_invariant_representation(
    *,
    fitted_at: datetime,
    discovery_partition: str,
    development_partitions: tuple[str, ...],
    episodes_by_partition: Mapping[str, tuple[RepresentationEpisode, ...]],
    policy: InvariantRepresentationPolicy | None = None,
) -> InvariantRepresentationModel:
    """Fit source-only residual concepts and reject partition-specific modes."""

    if fitted_at.tzinfo is None or fitted_at.utcoffset() is None:
        raise ValueError("fitted_at must be timezone-aware")
    effective = policy or InvariantRepresentationPolicy()
    if not development_partitions:
        raise ValueError("at least one development partition is required")
    if discovery_partition in development_partitions:
        raise ValueError("discovery partition cannot also be development")
    required = (discovery_partition, *development_partitions)
    if set(episodes_by_partition) != set(required):
        raise ValueError("episodes_by_partition must exactly match declared partitions")

    eligible: dict[str, tuple[RepresentationEpisode, ...]] = {
        partition: _eligible(episodes_by_partition[partition], effective)
        for partition in required
    }
    for partition, rows in eligible.items():
        if len(rows) < effective.minimum_episode_count_per_partition:
            raise ValueError(
                f"insufficient source episodes for invariant partition {partition}"
            )
        if any(item.partition != partition for item in rows):
            raise ValueError("episode partition label drift is forbidden")
        if any(item.as_of > fitted_at for item in rows):
            raise ValueError("future source evidence is forbidden")

    first = eligible[discovery_partition][0]
    feature_names = tuple(sorted(item.name for item in first.features))
    ontology_names = tuple(sorted(item.name for item in first.ontology))
    _identity_guard(feature_names)
    _identity_guard(ontology_names)

    raw_features: dict[str, list[list[float]]] = {}
    raw_ontology: dict[str, list[list[float]]] = {}
    for partition in required:
        raw_features[partition] = [
            _ordered_values(item, feature_names, ontology=False)
            for item in eligible[partition]
        ]
        raw_ontology[partition] = [
            _ordered_values(item, ontology_names, ontology=True)
            for item in eligible[partition]
        ]

    discovery_features = raw_features[discovery_partition]
    discovery_ontology = raw_ontology[discovery_partition]
    feature_centers, feature_scales = _robust_center_scale(
        discovery_features,
        effective.minimum_scale,
    )
    ontology_centers, ontology_scales = _robust_center_scale(
        discovery_ontology,
        effective.minimum_scale,
    )

    transformed_features = {
        partition: _bounded_transform(
            raw_features[partition],
            feature_centers,
            feature_scales,
            effective.robust_width,
        )
        for partition in required
    }
    transformed_ontology = {
        partition: _bounded_transform(
            raw_ontology[partition],
            ontology_centers,
            ontology_scales,
            effective.robust_width,
        )
        for partition in required
    }

    coefficients = _fit_residualizers(
        transformed_features[discovery_partition],
        transformed_ontology[discovery_partition],
        effective.residualization_ridge,
    )
    uncentered = {
        partition: _residuals(
            transformed_features[partition],
            transformed_ontology[partition],
            coefficients,
        )
        for partition in required
    }
    discovery_centered, residual_centers = _center_columns(
        uncentered[discovery_partition]
    )
    residual_rows: dict[str, list[list[float]]] = {
        discovery_partition: discovery_centered,
    }
    for partition in development_partitions:
        residual_rows[partition], _ = _center_columns(
            uncentered[partition],
            residual_centers,
        )

    covariance = _covariance(residual_rows[discovery_partition])
    candidates = _candidate_components(covariance, effective)
    selected: list[
        tuple[
            int,
            int,
            list[float],
            tuple[InvarianceDiagnostic, ...],
        ]
    ] = []

    for _eigenvalue, variance_bps, vector in candidates:
        reference_activation = _activation(
            residual_rows[discovery_partition],
            vector,
        )
        reference_scale = _mad(
            reference_activation,
            effective.minimum_scale,
        )
        reference_median = median(reference_activation)
        reference_profile = _correlation_profile(
            reference_activation,
            residual_rows[discovery_partition],
        )
        diagnostics: list[InvarianceDiagnostic] = []

        for partition in development_partitions:
            current_activation = _activation(
                residual_rows[partition],
                vector,
            )
            current_scale = _mad(
                current_activation,
                effective.minimum_scale,
            )
            ratio = current_scale / reference_scale
            shift_scale = (
                abs(median(current_activation) - reference_median)
                / reference_scale
            )
            alignment = _cosine_bps(
                reference_profile,
                _correlation_profile(
                    current_activation,
                    residual_rows[partition],
                ),
            )
            scale_stability = _scale_stability_bps(ratio)
            median_stability = _median_stability_bps(
                shift_scale,
                effective.maximum_median_shift_scale,
            )
            passed = (
                alignment >= effective.minimum_loading_alignment_bps
                and effective.minimum_scale_ratio
                <= ratio
                <= effective.maximum_scale_ratio
                and shift_scale <= effective.maximum_median_shift_scale
            )
            diagnostics.append(
                InvarianceDiagnostic(
                    partition=partition,
                    episode_count=len(eligible[partition]),
                    loading_alignment_bps=alignment,
                    activation_scale_ratio_milli=int(round(ratio * 1_000)),
                    activation_median_shift_milli_scale=int(
                        round(shift_scale * 1_000)
                    ),
                    scale_stability_bps=scale_stability,
                    median_stability_bps=median_stability,
                    passes=passed,
                )
            )

        if all(item.passes for item in diagnostics):
            source_invariance = min(
                min(
                    item.loading_alignment_bps,
                    item.scale_stability_bps,
                    item.median_stability_bps,
                )
                for item in diagnostics
            )
            selected.append(
                (
                    source_invariance,
                    variance_bps,
                    vector,
                    tuple(diagnostics),
                )
            )

    selected.sort(
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    selected = selected[: effective.maximum_concepts]

    concepts: list[InvariantLatentConcept] = []
    discovery_episodes = eligible[discovery_partition]
    for source_invariance, variance_bps, vector, diagnostics in selected:
        scores = _activation(
            residual_rows[discovery_partition],
            vector,
        )
        positive = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[: effective.cluster_episode_count]
        negative = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
        )[: effective.cluster_episode_count]
        concepts.append(
            InvariantLatentConcept(
                concept_id=_concept_id(feature_names, vector),
                loading_micros=tuple(
                    int(round(value * 1_000_000))
                    for value in vector
                ),
                discovery_explained_residual_variance_bps=variance_bps,
                source_invariance_bps=source_invariance,
                positive_probe_features=_probes(
                    feature_names,
                    vector,
                    positive=True,
                ),
                negative_probe_features=_probes(
                    feature_names,
                    vector,
                    positive=False,
                ),
                positive_cluster_episode_ids=tuple(
                    discovery_episodes[index].episode_id
                    for index in positive
                ),
                negative_cluster_episode_ids=tuple(
                    discovery_episodes[index].episode_id
                    for index in negative
                ),
                diagnostics=diagnostics,
            )
        )

    evidence_cutoff = max(
        item.as_of
        for partition in required
        for item in eligible[partition]
    )
    if evidence_cutoff > fitted_at:
        raise ValueError("future source evidence is forbidden")

    return InvariantRepresentationModel(
        fitted_at=fitted_at,
        evidence_cutoff_at=evidence_cutoff,
        discovery_partition=discovery_partition,
        development_partitions=development_partitions,
        discovery_episode_count=len(discovery_episodes),
        development_episode_counts=tuple(
            (partition, len(eligible[partition]))
            for partition in development_partitions
        ),
        feature_names=feature_names,
        ontology_names=ontology_names,
        feature_centers=tuple(feature_centers),
        feature_scales=tuple(feature_scales),
        ontology_centers=tuple(ontology_centers),
        ontology_scales=tuple(ontology_scales),
        robust_width=effective.robust_width,
        residualizers=tuple(
            InvariantResidualizer(
                feature_name=feature_names[index],
                ontology_coefficients_micros=tuple(
                    int(round(value * 1_000_000))
                    for value in coefficients[index]
                ),
            )
            for index in range(len(feature_names))
        ),
        residual_centers=tuple(residual_centers),
        concepts=tuple(concepts),
        candidate_count=len(candidates),
        rejected_candidate_count=len(candidates) - len(concepts),
    )


def project_invariant_representation(
    *,
    model: InvariantRepresentationModel,
    episode: RepresentationEpisode,
) -> LatentRepresentation:
    """Project one point-in-time episode through the frozen V2 representation."""

    raw_features = [
        _ordered_values(episode, model.feature_names, ontology=False)
    ]
    raw_ontology = [
        _ordered_values(episode, model.ontology_names, ontology=True)
    ]
    transformed_features = _bounded_transform(
        raw_features,
        model.feature_centers,
        model.feature_scales,
        model.robust_width,
    )
    transformed_ontology = _bounded_transform(
        raw_ontology,
        model.ontology_centers,
        model.ontology_scales,
        model.robust_width,
    )
    coefficients = [
        [
            value / 1_000_000.0
            for value in residualizer.ontology_coefficients_micros
        ]
        for residualizer in model.residualizers
    ]
    residual = _residuals(
        transformed_features,
        transformed_ontology,
        coefficients,
    )[0]
    centered = [
        value - model.residual_centers[index]
        for index, value in enumerate(residual)
    ]

    activations: list[LatentConceptActivation] = []
    for concept in model.concepts:
        vector = [
            value / 1_000_000.0
            for value in concept.loading_micros
        ]
        score = _dot(centered, vector)
        if not isfinite(score):
            raise ValueError("non-finite invariant activation")
        activations.append(
            LatentConceptActivation(
                concept_id=concept.concept_id,
                activation_milli_z=int(round(score * 1_000)),
            )
        )
    return LatentRepresentation(
        episode_id=episode.episode_id,
        as_of=episode.as_of,
        activations=tuple(activations),
    )
