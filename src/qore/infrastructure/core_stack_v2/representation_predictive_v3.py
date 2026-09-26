"""WP-04 V3 time-lagged predictive representation for Shared Brain.

V1 learned residual variance and failed out of sample.
V2 added cross-partition invariance and produced stable but non-informative modes.
V3 changes the representation-learning objective itself: discover source-state
directions that are consistently coupled to *future residual state change*
across consumed development partitions.

This is self-supervised research training, not runtime leakage:
- matured future market state may be used to learn temporal structure offline;
- no named evaluation target, trade outcome, PnL, trader/symbol identity or
  methodology identity participates in representation discovery;
- runtime projection uses only the point-in-time source episode;
- all concepts remain RESEARCH knowledge with no methodology, sizing, Risk,
  order, execution or promotion authority.

The architecture contract explicitly permits future-state prediction for
training while forbidding runtime future information.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite, sqrt, tanh
from statistics import median
from typing import Final

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    LatentConceptActivation,
    LatentRepresentation,
    RepresentationEpisode,
)

_BANNED_IDENTITY_TOKENS: Final = (
    "TRADER",
    "STRATEGY",
    "SETUP",
    "SIGNAL_ID",
    "TRADE_ID",
    "ACCOUNT",
    "POSITION_ID",
    "ENTRY",
    "STOP",
    "TARGET",
    "PNL",
    "OUTCOME",
    "WINNER",
    "LOSER",
    "SYMBOL_ID",
    "MARKET_ID",
    "INSTRUMENT_ID",
    "FOLD_ID",
    "PARTITION_ID",
)


@dataclass(frozen=True, slots=True)
class PredictiveTransitionEpisode:
    source: RepresentationEpisode
    future: RepresentationEpisode
    horizon_minutes: int

    def __post_init__(self) -> None:
        if self.horizon_minutes < 1:
            raise ValueError("predictive horizon must be positive")
        if self.source.partition != self.future.partition:
            raise ValueError("predictive transition cannot cross partitions")
        if self.future.as_of <= self.source.as_of:
            raise ValueError("future episode must follow source episode")
        elapsed = int(
            round(
                (self.future.as_of - self.source.as_of).total_seconds()
                / 60.0
            )
        )
        if elapsed != self.horizon_minutes:
            raise ValueError("predictive transition horizon mismatch")
        if self.source.integrity_bps != self.future.integrity_bps:
            raise ValueError("predictive transition integrity mismatch")


@dataclass(frozen=True, slots=True)
class PredictiveRepresentationPolicy:
    maximum_concepts: int = 6
    candidate_multiplier: int = 4
    minimum_transition_count_per_partition: int = 5_000
    minimum_integrity_bps: int = 9_500
    minimum_scale: float = 1e-9
    robust_width: float = 3.0
    residualization_ridge: float = 0.20
    minimum_predictive_strength_bps: int = 25
    power_iterations: int = 120
    minimum_future_profile_alignment_bps: int = 7_500
    minimum_predictive_strength_ratio: float = 0.50
    maximum_predictive_strength_ratio: float = 2.00
    minimum_source_scale_ratio: float = 0.50
    maximum_source_scale_ratio: float = 2.00
    maximum_source_median_shift_scale: float = 1.50
    cluster_episode_count: int = 12

    def __post_init__(self) -> None:
        if self.maximum_concepts < 1:
            raise ValueError("maximum_concepts must be positive")
        if self.candidate_multiplier < 1:
            raise ValueError("candidate_multiplier must be positive")
        if self.minimum_transition_count_per_partition < 10:
            raise ValueError(
                "minimum_transition_count_per_partition must be at least 10"
            )
        if not 0 <= self.minimum_integrity_bps <= 10_000:
            raise ValueError("minimum_integrity_bps must be within 0..10000")
        if self.minimum_scale <= 0:
            raise ValueError("minimum_scale must be positive")
        if self.robust_width <= 0:
            raise ValueError("robust_width must be positive")
        if self.residualization_ridge <= 0:
            raise ValueError("residualization_ridge must be positive")
        if not 0 <= self.minimum_predictive_strength_bps <= 10_000:
            raise ValueError(
                "minimum_predictive_strength_bps must be within 0..10000"
            )
        if self.power_iterations < 10:
            raise ValueError("power_iterations must be at least 10")
        if not 0 <= self.minimum_future_profile_alignment_bps <= 10_000:
            raise ValueError(
                "minimum_future_profile_alignment_bps must be within 0..10000"
            )
        for name, value in (
            ("minimum_predictive_strength_ratio", self.minimum_predictive_strength_ratio),
            ("minimum_source_scale_ratio", self.minimum_source_scale_ratio),
        ):
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be within (0, 1]")
        for name, value in (
            ("maximum_predictive_strength_ratio", self.maximum_predictive_strength_ratio),
            ("maximum_source_scale_ratio", self.maximum_source_scale_ratio),
        ):
            if value < 1:
                raise ValueError(f"{name} must be at least 1")
        if (
            self.minimum_predictive_strength_ratio
            > self.maximum_predictive_strength_ratio
        ):
            raise ValueError("predictive strength-ratio bounds are invalid")
        if self.minimum_source_scale_ratio > self.maximum_source_scale_ratio:
            raise ValueError("source scale-ratio bounds are invalid")
        if self.maximum_source_median_shift_scale <= 0:
            raise ValueError("maximum_source_median_shift_scale must be positive")
        if self.cluster_episode_count < 1:
            raise ValueError("cluster_episode_count must be positive")


@dataclass(frozen=True, slots=True)
class PredictiveResidualizer:
    feature_name: str
    ontology_coefficients_micros: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PredictiveInvarianceDiagnostic:
    partition: str
    transition_count: int
    future_profile_alignment_bps: int
    predictive_strength_ratio_milli: int
    predictive_strength_stability_bps: int
    source_scale_ratio_milli: int
    source_scale_stability_bps: int
    source_median_shift_milli_scale: int
    source_median_stability_bps: int
    passes: bool

    def __post_init__(self) -> None:
        if not self.partition:
            raise ValueError("diagnostic partition must be non-empty")
        if self.transition_count < 1:
            raise ValueError("diagnostic transition_count must be positive")
        for value in (
            self.future_profile_alignment_bps,
            self.predictive_strength_stability_bps,
            self.source_scale_stability_bps,
            self.source_median_stability_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("diagnostic bps must be within 0..10000")
        if self.predictive_strength_ratio_milli < 0:
            raise ValueError("predictive strength ratio cannot be negative")
        if self.source_scale_ratio_milli < 0:
            raise ValueError("source scale ratio cannot be negative")
        if self.source_median_shift_milli_scale < 0:
            raise ValueError("source median shift cannot be negative")


@dataclass(frozen=True, slots=True)
class PredictiveLatentConcept:
    concept_id: str
    source_loading_micros: tuple[int, ...]
    future_profile_micros: tuple[int, ...]
    discovery_predictive_strength_bps: int
    temporal_invariance_bps: int
    positive_probe_features: tuple[str, ...]
    negative_probe_features: tuple[str, ...]
    positive_cluster_episode_ids: tuple[str, ...]
    negative_cluster_episode_ids: tuple[str, ...]
    diagnostics: tuple[PredictiveInvarianceDiagnostic, ...]

    def __post_init__(self) -> None:
        if not self.concept_id.startswith("LATENT_CONCEPT_"):
            raise ValueError("predictive concept id must remain provisional")
        if not self.source_loading_micros or not self.future_profile_micros:
            raise ValueError("predictive concept requires source and future profiles")
        if not 0 <= self.discovery_predictive_strength_bps <= 10_000:
            raise ValueError("predictive strength must be within 0..10000")
        if not 0 <= self.temporal_invariance_bps <= 10_000:
            raise ValueError("temporal invariance must be within 0..10000")
        if not (self.positive_probe_features or self.negative_probe_features):
            raise ValueError("predictive concept requires interpretable probes")
        if not self.diagnostics:
            raise ValueError("predictive concept requires development diagnostics")
        if not all(item.passes for item in self.diagnostics):
            raise ValueError("selected predictive concept contains failed diagnostic")


@dataclass(frozen=True, slots=True)
class PredictiveRepresentationModel:
    fitted_at: datetime
    evidence_cutoff_at: datetime
    horizon_minutes: int
    discovery_partition: str
    development_partitions: tuple[str, ...]
    transition_counts: tuple[tuple[str, int], ...]
    feature_names: tuple[str, ...]
    ontology_names: tuple[str, ...]
    feature_centers: tuple[float, ...]
    feature_scales: tuple[float, ...]
    ontology_centers: tuple[float, ...]
    ontology_scales: tuple[float, ...]
    robust_width: float
    residualizers: tuple[PredictiveResidualizer, ...]
    residual_centers: tuple[float, ...]
    concepts: tuple[PredictiveLatentConcept, ...]
    candidate_count: int
    rejected_candidate_count: int
    training_future_market_used: bool = True
    runtime_future_market_used: bool = False
    named_evaluation_target_used: bool = False
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
            raise ValueError("future training evidence is forbidden")
        if self.horizon_minutes < 1:
            raise ValueError("horizon_minutes must be positive")
        if not self.discovery_partition or not self.development_partitions:
            raise ValueError("discovery/development partitions are required")
        if self.discovery_partition in self.development_partitions:
            raise ValueError("discovery partition cannot repeat as development")
        if len(set(self.development_partitions)) != len(
            self.development_partitions
        ):
            raise ValueError("development partitions must be unique")
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
        if not self.training_future_market_used:
            raise ValueError("V3 must explicitly record temporal training evidence")
        if (
            self.runtime_future_market_used
            or self.named_evaluation_target_used
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
                "predictive representation cannot leak runtime future/identity "
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


def _identity_guard(names: Sequence[str]) -> None:
    for name in names:
        upper = name.upper()
        if any(token in upper for token in _BANNED_IDENTITY_TOKENS):
            raise ValueError(f"identity/outcome shortcut is forbidden: {name}")


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
    centers: list[float] = []
    scales: list[float] = []
    for column in range(len(rows[0])):
        values = [row[column] for row in rows]
        center = median(values)
        q25 = _percentile(values, 0.25)
        q75 = _percentile(values, 0.75)
        scale = (q75 - q25) / 1.349
        if scale < minimum_scale:
            scale = median(abs(value - center) for value in values) * 1.4826
        centers.append(center)
        scales.append(max(minimum_scale, scale))
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
    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(
            range(column, size),
            key=lambda row: abs(augmented[row][column]),
        )
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("predictive representation linear system is singular")
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
    return [
        _ridge_coefficients(
            ontology,
            [row[index] for row in features],
            ridge,
        )
        for index in range(len(features[0]))
    ]


def _residuals(
    features: list[list[float]],
    ontology: list[list[float]],
    coefficients: Sequence[Sequence[float]],
) -> list[list[float]]:
    rows: list[list[float]] = []
    for feature_row, ontology_row in zip(features, ontology, strict=True):
        rows.append(
            [
                target
                - sum(
                    coefficient * value
                    for coefficient, value in zip(
                        coefficients[index],
                        ontology_row,
                        strict=True,
                    )
                )
                for index, target in enumerate(feature_row)
            ]
        )
    return rows


def _center_rows(
    rows: list[list[float]],
    centers: Sequence[float] | None = None,
) -> tuple[list[list[float]], list[float]]:
    if centers is None:
        centers = [
            sum(row[column] for row in rows) / len(rows)
            for column in range(len(rows[0]))
        ]
    return (
        [
            [
                value - centers[column]
                for column, value in enumerate(row)
            ]
            for row in rows
        ],
        list(centers),
    )


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _normalize(vector: Sequence[float]) -> list[float]:
    norm = sqrt(_dot(vector, vector))
    if norm < 1e-12:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def _matrix_vector(
    matrix: Sequence[Sequence[float]],
    vector: Sequence[float],
) -> list[float]:
    return [
        sum(value * vector[column] for column, value in enumerate(row))
        for row in matrix
    ]


def _cross_covariance(
    source_rows: Sequence[Sequence[float]],
    future_delta_rows: Sequence[Sequence[float]],
) -> list[list[float]]:
    if len(source_rows) != len(future_delta_rows) or not source_rows:
        raise ValueError("predictive covariance shape mismatch")
    source_width = len(source_rows[0])
    future_width = len(future_delta_rows[0])
    result = [
        [0.0 for _ in range(future_width)]
        for _ in range(source_width)
    ]
    denominator = max(1, len(source_rows) - 1)
    for source, future_delta in zip(
        source_rows,
        future_delta_rows,
        strict=True,
    ):
        for left in range(source_width):
            for right in range(future_width):
                result[left][right] += source[left] * future_delta[right]
    for left in range(source_width):
        for right in range(future_width):
            result[left][right] /= denominator
    return result


def _predictive_operator(
    cross: Sequence[Sequence[float]],
) -> list[list[float]]:
    width = len(cross)
    result = [[0.0 for _ in range(width)] for _ in range(width)]
    for left in range(width):
        for right in range(left, width):
            value = _dot(cross[left], cross[right])
            result[left][right] = value
            result[right][left] = value
    return result


def _trace(matrix: Sequence[Sequence[float]]) -> float:
    return sum(matrix[index][index] for index in range(len(matrix)))


def _candidate_components(
    operator: list[list[float]],
    policy: PredictiveRepresentationPolicy,
) -> list[tuple[float, int, list[float]]]:
    work = [row[:] for row in operator]
    total = _trace(operator)
    if total <= 1e-12:
        return []
    maximum = min(
        len(operator),
        policy.maximum_concepts * policy.candidate_multiplier,
    )
    result: list[tuple[float, int, list[float]]] = []
    for _ in range(maximum):
        seed = max(range(len(work)), key=lambda index: work[index][index])
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
        strength_bps = int(round(eigenvalue / total * 10_000))
        if (
            eigenvalue <= 1e-12
            or strength_bps < policy.minimum_predictive_strength_bps
        ):
            break

        largest = max(
            range(len(vector)),
            key=lambda index: abs(vector[index]),
        )
        if vector[largest] < 0:
            vector = [-value for value in vector]
        result.append((eigenvalue, strength_bps, vector))
        for row in range(len(work)):
            for column in range(len(work)):
                work[row][column] -= (
                    eigenvalue * vector[row] * vector[column]
                )
    return result


def _future_profile(
    cross: Sequence[Sequence[float]],
    source_loading: Sequence[float],
) -> list[float]:
    width = len(cross[0])
    return [
        sum(
            source_loading[source_index] * cross[source_index][future_index]
            for source_index in range(len(cross))
        )
        for future_index in range(width)
    ]


def _activation(
    source_rows: Sequence[Sequence[float]],
    loading: Sequence[float],
) -> list[float]:
    return [_dot(row, loading) for row in source_rows]


def _mad(values: Sequence[float], minimum_scale: float) -> float:
    center = median(values)
    return max(
        minimum_scale,
        median(abs(value - center) for value in values) * 1.4826,
    )


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


def _ratio_stability_bps(ratio: float) -> int:
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
                    (
                        1.0
                        - min(1.0, shift_scale / maximum_shift_scale)
                    )
                    * 10_000
                )
            ),
        ),
    )


def _concept_id(
    feature_names: Sequence[str],
    source_loading: Sequence[float],
    future_profile: Sequence[float],
    horizon_minutes: int,
) -> str:
    payload = "|".join(
        [
            f"H={horizon_minutes}",
            *(
                f"S:{name}:{int(round(value * 1_000_000))}"
                for name, value in zip(
                    feature_names,
                    source_loading,
                    strict=True,
                )
            ),
            *(
                f"F:{name}:{int(round(value * 1_000_000))}"
                for name, value in zip(
                    feature_names,
                    future_profile,
                    strict=True,
                )
            ),
        ]
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


def _eligible_transitions(
    transitions: Sequence[PredictiveTransitionEpisode],
    policy: PredictiveRepresentationPolicy,
) -> tuple[PredictiveTransitionEpisode, ...]:
    return tuple(
        item
        for item in transitions
        if (
            item.source.integrity_bps >= policy.minimum_integrity_bps
            and item.future.integrity_bps >= policy.minimum_integrity_bps
        )
    )


def _raw_rows(
    transitions: Sequence[PredictiveTransitionEpisode],
    feature_names: tuple[str, ...],
    ontology_names: tuple[str, ...],
) -> tuple[
    list[list[float]],
    list[list[float]],
    list[list[float]],
    list[list[float]],
]:
    source_features = [
        _ordered_values(item.source, feature_names, ontology=False)
        for item in transitions
    ]
    source_ontology = [
        _ordered_values(item.source, ontology_names, ontology=True)
        for item in transitions
    ]
    future_features = [
        _ordered_values(item.future, feature_names, ontology=False)
        for item in transitions
    ]
    future_ontology = [
        _ordered_values(item.future, ontology_names, ontology=True)
        for item in transitions
    ]
    return (
        source_features,
        source_ontology,
        future_features,
        future_ontology,
    )


def fit_predictive_representation(
    *,
    fitted_at: datetime,
    discovery_partition: str,
    development_partitions: tuple[str, ...],
    transitions_by_partition: Mapping[
        str,
        tuple[PredictiveTransitionEpisode, ...],
    ],
    policy: PredictiveRepresentationPolicy | None = None,
) -> PredictiveRepresentationModel:
    """Learn target-blind time-lagged residual concepts on consumed evidence."""

    if fitted_at.tzinfo is None or fitted_at.utcoffset() is None:
        raise ValueError("fitted_at must be timezone-aware")
    effective = policy or PredictiveRepresentationPolicy()
    required = (discovery_partition, *development_partitions)
    if not development_partitions:
        raise ValueError("at least one development partition is required")
    if discovery_partition in development_partitions:
        raise ValueError("discovery partition cannot also be development")
    if set(transitions_by_partition) != set(required):
        raise ValueError(
            "transitions_by_partition must exactly match declared partitions"
        )

    eligible = {
        partition: _eligible_transitions(
            transitions_by_partition[partition],
            effective,
        )
        for partition in required
    }
    horizons = {
        item.horizon_minutes
        for rows in eligible.values()
        for item in rows
    }
    if len(horizons) != 1:
        raise ValueError("V3 requires one frozen predictive horizon")
    horizon_minutes = next(iter(horizons))

    for partition, rows in eligible.items():
        if len(rows) < effective.minimum_transition_count_per_partition:
            raise ValueError(
                f"insufficient transitions for predictive partition {partition}"
            )
        if any(item.source.partition != partition for item in rows):
            raise ValueError("source partition label drift is forbidden")
        if any(item.future.partition != partition for item in rows):
            raise ValueError("future partition label drift is forbidden")
        if any(item.future.as_of > fitted_at for item in rows):
            raise ValueError("future training evidence beyond fitted_at is forbidden")

    first = eligible[discovery_partition][0].source
    feature_names = tuple(sorted(item.name for item in first.features))
    ontology_names = tuple(sorted(item.name for item in first.ontology))
    _identity_guard(feature_names)
    _identity_guard(ontology_names)

    raw: dict[
        str,
        tuple[
            list[list[float]],
            list[list[float]],
            list[list[float]],
            list[list[float]],
        ],
    ] = {
        partition: _raw_rows(
            eligible[partition],
            feature_names,
            ontology_names,
        )
        for partition in required
    }

    discovery_source_features = raw[discovery_partition][0]
    discovery_source_ontology = raw[discovery_partition][1]
    feature_centers, feature_scales = _robust_center_scale(
        discovery_source_features,
        effective.minimum_scale,
    )
    ontology_centers, ontology_scales = _robust_center_scale(
        discovery_source_ontology,
        effective.minimum_scale,
    )

    transformed: dict[
        str,
        tuple[
            list[list[float]],
            list[list[float]],
            list[list[float]],
            list[list[float]],
        ],
    ] = {}
    for partition in required:
        (
            source_features,
            source_ontology,
            future_features,
            future_ontology,
        ) = raw[partition]
        transformed[partition] = (
            _bounded_transform(
                source_features,
                feature_centers,
                feature_scales,
                effective.robust_width,
            ),
            _bounded_transform(
                source_ontology,
                ontology_centers,
                ontology_scales,
                effective.robust_width,
            ),
            _bounded_transform(
                future_features,
                feature_centers,
                feature_scales,
                effective.robust_width,
            ),
            _bounded_transform(
                future_ontology,
                ontology_centers,
                ontology_scales,
                effective.robust_width,
            ),
        )

    coefficients = _fit_residualizers(
        transformed[discovery_partition][0],
        transformed[discovery_partition][1],
        effective.residualization_ridge,
    )

    source_uncentered: dict[str, list[list[float]]] = {}
    future_uncentered: dict[str, list[list[float]]] = {}
    for partition in required:
        (
            source_features,
            source_ontology,
            future_features,
            future_ontology,
        ) = transformed[partition]
        source_uncentered[partition] = _residuals(
            source_features,
            source_ontology,
            coefficients,
        )
        future_uncentered[partition] = _residuals(
            future_features,
            future_ontology,
            coefficients,
        )

    discovery_source, residual_centers = _center_rows(
        source_uncentered[discovery_partition]
    )
    source_rows: dict[str, list[list[float]]] = {
        discovery_partition: discovery_source
    }
    future_rows: dict[str, list[list[float]]] = {}
    for partition in required:
        if partition != discovery_partition:
            source_rows[partition], _ = _center_rows(
                source_uncentered[partition],
                residual_centers,
            )
        future_rows[partition], _ = _center_rows(
            future_uncentered[partition],
            residual_centers,
        )

    future_delta_rows = {
        partition: [
            [
                future_value - source_value
                for future_value, source_value in zip(
                    future_row,
                    source_row,
                    strict=True,
                )
            ]
            for source_row, future_row in zip(
                source_rows[partition],
                future_rows[partition],
                strict=True,
            )
        ]
        for partition in required
    }
    cross = {
        partition: _cross_covariance(
            source_rows[partition],
            future_delta_rows[partition],
        )
        for partition in required
    }
    operator = _predictive_operator(cross[discovery_partition])
    candidates = _candidate_components(operator, effective)

    selected: list[
        tuple[
            int,
            int,
            list[float],
            list[float],
            tuple[PredictiveInvarianceDiagnostic, ...],
        ]
    ] = []

    for _eigenvalue, strength_bps, source_loading in candidates:
        reference_future_profile = _future_profile(
            cross[discovery_partition],
            source_loading,
        )
        reference_future_strength = sqrt(
            _dot(reference_future_profile, reference_future_profile)
        )
        reference_activation = _activation(
            source_rows[discovery_partition],
            source_loading,
        )
        reference_source_scale = _mad(
            reference_activation,
            effective.minimum_scale,
        )
        reference_source_median = median(reference_activation)
        diagnostics: list[PredictiveInvarianceDiagnostic] = []

        for partition in development_partitions:
            candidate_future_profile = _future_profile(
                cross[partition],
                source_loading,
            )
            candidate_future_strength = sqrt(
                _dot(candidate_future_profile, candidate_future_profile)
            )
            predictive_ratio = (
                candidate_future_strength / reference_future_strength
                if reference_future_strength > effective.minimum_scale
                else 0.0
            )
            alignment = _cosine_bps(
                reference_future_profile,
                candidate_future_profile,
            )
            candidate_activation = _activation(
                source_rows[partition],
                source_loading,
            )
            candidate_source_scale = _mad(
                candidate_activation,
                effective.minimum_scale,
            )
            source_scale_ratio = (
                candidate_source_scale / reference_source_scale
            )
            source_median_shift = (
                abs(median(candidate_activation) - reference_source_median)
                / reference_source_scale
            )
            passed = (
                alignment
                >= effective.minimum_future_profile_alignment_bps
                and effective.minimum_predictive_strength_ratio
                <= predictive_ratio
                <= effective.maximum_predictive_strength_ratio
                and effective.minimum_source_scale_ratio
                <= source_scale_ratio
                <= effective.maximum_source_scale_ratio
                and source_median_shift
                <= effective.maximum_source_median_shift_scale
            )
            diagnostics.append(
                PredictiveInvarianceDiagnostic(
                    partition=partition,
                    transition_count=len(eligible[partition]),
                    future_profile_alignment_bps=alignment,
                    predictive_strength_ratio_milli=int(
                        round(predictive_ratio * 1_000)
                    ),
                    predictive_strength_stability_bps=_ratio_stability_bps(
                        predictive_ratio
                    ),
                    source_scale_ratio_milli=int(
                        round(source_scale_ratio * 1_000)
                    ),
                    source_scale_stability_bps=_ratio_stability_bps(
                        source_scale_ratio
                    ),
                    source_median_shift_milli_scale=int(
                        round(source_median_shift * 1_000)
                    ),
                    source_median_stability_bps=_median_stability_bps(
                        source_median_shift,
                        effective.maximum_source_median_shift_scale,
                    ),
                    passes=passed,
                )
            )

        if all(item.passes for item in diagnostics):
            temporal_invariance = min(
                min(
                    item.future_profile_alignment_bps,
                    item.predictive_strength_stability_bps,
                    item.source_scale_stability_bps,
                    item.source_median_stability_bps,
                )
                for item in diagnostics
            )
            selected.append(
                (
                    temporal_invariance,
                    strength_bps,
                    source_loading,
                    reference_future_profile,
                    tuple(diagnostics),
                )
            )

    selected.sort(
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    selected = selected[: effective.maximum_concepts]

    discovery_transitions = eligible[discovery_partition]
    concepts: list[PredictiveLatentConcept] = []
    for (
        temporal_invariance,
        strength_bps,
        source_loading,
        future_profile,
        diagnostics,
    ) in selected:
        scores = _activation(
            source_rows[discovery_partition],
            source_loading,
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
        normalized_future = _normalize(future_profile)
        concepts.append(
            PredictiveLatentConcept(
                concept_id=_concept_id(
                    feature_names,
                    source_loading,
                    normalized_future,
                    horizon_minutes,
                ),
                source_loading_micros=tuple(
                    int(round(value * 1_000_000))
                    for value in source_loading
                ),
                future_profile_micros=tuple(
                    int(round(value * 1_000_000))
                    for value in normalized_future
                ),
                discovery_predictive_strength_bps=strength_bps,
                temporal_invariance_bps=temporal_invariance,
                positive_probe_features=_probes(
                    feature_names,
                    source_loading,
                    positive=True,
                ),
                negative_probe_features=_probes(
                    feature_names,
                    source_loading,
                    positive=False,
                ),
                positive_cluster_episode_ids=tuple(
                    discovery_transitions[index].source.episode_id
                    for index in positive
                ),
                negative_cluster_episode_ids=tuple(
                    discovery_transitions[index].source.episode_id
                    for index in negative
                ),
                diagnostics=diagnostics,
            )
        )

    evidence_cutoff_at = max(
        item.future.as_of
        for partition in required
        for item in eligible[partition]
    )
    return PredictiveRepresentationModel(
        fitted_at=fitted_at,
        evidence_cutoff_at=evidence_cutoff_at,
        horizon_minutes=horizon_minutes,
        discovery_partition=discovery_partition,
        development_partitions=development_partitions,
        transition_counts=tuple(
            (partition, len(eligible[partition]))
            for partition in required
        ),
        feature_names=feature_names,
        ontology_names=ontology_names,
        feature_centers=tuple(feature_centers),
        feature_scales=tuple(feature_scales),
        ontology_centers=tuple(ontology_centers),
        ontology_scales=tuple(ontology_scales),
        robust_width=effective.robust_width,
        residualizers=tuple(
            PredictiveResidualizer(
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


def project_predictive_representation(
    *,
    model: PredictiveRepresentationModel,
    episode: RepresentationEpisode,
) -> LatentRepresentation:
    """Project a source episode using no future information."""

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
        loading = [
            value / 1_000_000.0
            for value in concept.source_loading_micros
        ]
        score = _dot(centered, loading)
        if not isfinite(score):
            raise ValueError("non-finite predictive activation")
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
        target_used=False,
        future_market_used=False,
        trader_identity_used=False,
    )
