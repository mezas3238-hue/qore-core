"""WP-04 Market Representation Discovery for Shared Brain.

Shared must not be limited to concepts humans already named. This module learns
provisional latent concepts from the portion of generic market-sequence features
that the existing ontology does not explain.

Discovery is deliberately target-blind:
- only point-in-time feature vectors and contemporaneous ontology state enter
  fitting;
- no trade outcome, PnL, side, entry, stop, target, account or trader identity;
- no future evaluation label;
- no methodology, knowledge-promotion, Risk, sizing, order or execution
  authority.

The fitted representation is frozen before an external evaluator measures
incremental information out of sample.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite, sqrt


_BANNED_IDENTITY_TOKENS = (
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
)


@dataclass(frozen=True, slots=True)
class RepresentationValue:
    name: str
    value: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("representation value name must be non-empty")
        upper = self.name.upper()
        if any(token in upper for token in _BANNED_IDENTITY_TOKENS):
            raise ValueError(
                f"identity/outcome leakage token is forbidden: {self.name}"
            )
        if not isfinite(self.value):
            raise ValueError("representation values must be finite")


@dataclass(frozen=True, slots=True)
class RepresentationEpisode:
    episode_id: str
    as_of: datetime
    partition: str
    features: tuple[RepresentationValue, ...]
    ontology: tuple[RepresentationValue, ...]
    integrity_bps: int = 10_000

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("episode_id must be non-empty")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("episode as_of must be timezone-aware")
        if not self.partition:
            raise ValueError("partition must be non-empty")
        if not 0 <= self.integrity_bps <= 10_000:
            raise ValueError("integrity_bps must be within 0..10000")
        feature_names = [item.name for item in self.features]
        ontology_names = [item.name for item in self.ontology]
        if not feature_names or not ontology_names:
            raise ValueError("features and ontology must both be non-empty")
        if len(set(feature_names)) != len(feature_names):
            raise ValueError("feature names must be unique")
        if len(set(ontology_names)) != len(ontology_names):
            raise ValueError("ontology names must be unique")


@dataclass(frozen=True, slots=True)
class RepresentationDiscoveryPolicy:
    maximum_concepts: int = 6
    minimum_episode_count: int = 500
    minimum_integrity_bps: int = 9_500
    minimum_feature_scale: float = 1e-9
    residualization_ridge: float = 0.20
    minimum_component_variance_bps: int = 250
    power_iterations: int = 120
    cluster_episode_count: int = 12

    def __post_init__(self) -> None:
        if self.maximum_concepts < 1:
            raise ValueError("maximum_concepts must be positive")
        if self.minimum_episode_count < 10:
            raise ValueError("minimum_episode_count must be at least 10")
        if not 0 <= self.minimum_integrity_bps <= 10_000:
            raise ValueError("minimum_integrity_bps must be within 0..10000")
        if self.minimum_feature_scale <= 0:
            raise ValueError("minimum_feature_scale must be positive")
        if self.residualization_ridge <= 0:
            raise ValueError("residualization_ridge must be positive")
        if not 0 <= self.minimum_component_variance_bps <= 10_000:
            raise ValueError(
                "minimum_component_variance_bps must be within 0..10000"
            )
        if self.power_iterations < 10:
            raise ValueError("power_iterations must be at least 10")
        if self.cluster_episode_count < 1:
            raise ValueError("cluster_episode_count must be positive")


@dataclass(frozen=True, slots=True)
class FeatureResidualizer:
    feature_name: str
    ontology_coefficients_micros: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class LatentConceptDefinition:
    concept_id: str
    loading_micros: tuple[int, ...]
    explained_residual_variance_bps: int
    positive_probe_features: tuple[str, ...]
    negative_probe_features: tuple[str, ...]
    positive_cluster_episode_ids: tuple[str, ...]
    negative_cluster_episode_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.concept_id.startswith("LATENT_CONCEPT_"):
            raise ValueError("latent concept id must be provisional")
        if not self.loading_micros:
            raise ValueError("latent concept must carry feature loadings")
        if not 0 <= self.explained_residual_variance_bps <= 10_000:
            raise ValueError(
                "explained residual variance must be within 0..10000"
            )
        if not (
            self.positive_probe_features
            or self.negative_probe_features
        ):
            raise ValueError("latent concept requires interpretable probes")


@dataclass(frozen=True, slots=True)
class RepresentationDiscoveryModel:
    fitted_at: datetime
    evidence_cutoff_at: datetime
    discovery_partition: str
    episode_count: int
    feature_names: tuple[str, ...]
    ontology_names: tuple[str, ...]
    feature_means: tuple[float, ...]
    feature_scales: tuple[float, ...]
    ontology_means: tuple[float, ...]
    ontology_scales: tuple[float, ...]
    residualizers: tuple[FeatureResidualizer, ...]
    concepts: tuple[LatentConceptDefinition, ...]
    target_used: bool = False
    future_market_used: bool = False
    outcome_used: bool = False
    pnl_used: bool = False
    trader_identity_used: bool = False
    methodology_authority: bool = False
    knowledge_promotion_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.fitted_at.tzinfo is None or self.fitted_at.utcoffset() is None:
            raise ValueError("fitted_at must be timezone-aware")
        if (
            self.evidence_cutoff_at.tzinfo is None
            or self.evidence_cutoff_at.utcoffset() is None
        ):
            raise ValueError("evidence_cutoff_at must be timezone-aware")
        if self.evidence_cutoff_at > self.fitted_at:
            raise ValueError("future discovery evidence is forbidden")
        if self.episode_count < 1:
            raise ValueError("episode_count must be positive")
        if len(self.feature_names) != len(self.feature_means):
            raise ValueError("feature mean shape mismatch")
        if len(self.feature_names) != len(self.feature_scales):
            raise ValueError("feature scale shape mismatch")
        if len(self.ontology_names) != len(self.ontology_means):
            raise ValueError("ontology mean shape mismatch")
        if len(self.ontology_names) != len(self.ontology_scales):
            raise ValueError("ontology scale shape mismatch")
        if len(self.residualizers) != len(self.feature_names):
            raise ValueError("residualizer shape mismatch")
        if len({item.concept_id for item in self.concepts}) != len(
            self.concepts
        ):
            raise ValueError("latent concept ids must be unique")
        if (
            self.target_used
            or self.future_market_used
            or self.outcome_used
            or self.pnl_used
            or self.trader_identity_used
            or self.methodology_authority
            or self.knowledge_promotion_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError(
                "representation discovery cannot use targets/identity "
                "or carry authority"
            )


@dataclass(frozen=True, slots=True)
class LatentConceptActivation:
    concept_id: str
    activation_milli_z: int


@dataclass(frozen=True, slots=True)
class LatentRepresentation:
    episode_id: str
    as_of: datetime
    activations: tuple[LatentConceptActivation, ...]
    target_used: bool = False
    future_market_used: bool = False
    trader_identity_used: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("representation as_of must be timezone-aware")
        if (
            self.target_used
            or self.future_market_used
            or self.trader_identity_used
        ):
            raise ValueError("latent projection must remain point-in-time")


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


def _mean_scale(
    rows: list[list[float]],
    minimum_scale: float,
) -> tuple[list[float], list[float]]:
    width = len(rows[0])
    means = [
        sum(row[index] for row in rows) / len(rows)
        for index in range(width)
    ]
    scales: list[float] = []
    for index in range(width):
        variance = sum(
            (row[index] - means[index]) ** 2
            for row in rows
        ) / max(1, len(rows) - 1)
        scales.append(max(minimum_scale, sqrt(variance)))
    return means, scales


def _standardize(
    rows: list[list[float]],
    means: list[float] | tuple[float, ...],
    scales: list[float] | tuple[float, ...],
) -> list[list[float]]:
    return [
        [
            (value - means[index]) / scales[index]
            for index, value in enumerate(row)
        ]
        for row in rows
    ]


def _solve(
    matrix: list[list[float]],
    vector: list[float],
) -> list[float]:
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
            raise ValueError("representation linear system is singular")
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


def _residual_matrix(
    features: list[list[float]],
    ontology: list[list[float]],
    ridge: float,
) -> tuple[list[list[float]], list[list[float]]]:
    feature_count = len(features[0])
    residualizers: list[list[float]] = []
    residuals = [
        [0.0 for _ in range(feature_count)]
        for _ in features
    ]
    for feature_index in range(feature_count):
        target = [row[feature_index] for row in features]
        coefficients = _ridge_coefficients(ontology, target, ridge)
        residualizers.append(coefficients)
        for row_index, ontology_row in enumerate(ontology):
            predicted = sum(
                coefficient * value
                for coefficient, value in zip(
                    coefficients,
                    ontology_row,
                    strict=True,
                )
            )
            residuals[row_index][feature_index] = (
                target[row_index] - predicted
            )
    return residuals, residualizers


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
    vector: list[float],
) -> list[float]:
    return [
        sum(
            value * vector[column]
            for column, value in enumerate(row)
        )
        for row in matrix
    ]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _normalize(vector: list[float]) -> list[float]:
    norm = sqrt(_dot(vector, vector))
    if norm < 1e-12:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def _components(
    covariance: list[list[float]],
    policy: RepresentationDiscoveryPolicy,
) -> list[tuple[float, list[float]]]:
    work = [row[:] for row in covariance]
    original_trace = sum(covariance[index][index] for index in range(len(covariance)))
    if original_trace <= 1e-12:
        return []

    result: list[tuple[float, list[float]]] = []
    for _ in range(min(policy.maximum_concepts, len(covariance))):
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
        variance_bps = int(round(eigenvalue / original_trace * 10_000))
        if (
            eigenvalue <= 1e-12
            or variance_bps < policy.minimum_component_variance_bps
        ):
            break

        largest = max(
            range(len(vector)),
            key=lambda index: abs(vector[index]),
        )
        if vector[largest] < 0:
            vector = [-value for value in vector]

        result.append((eigenvalue, vector))
        for row in range(len(work)):
            for column in range(len(work)):
                work[row][column] -= (
                    eigenvalue * vector[row] * vector[column]
                )
    return result


def _concept_id(
    feature_names: tuple[str, ...],
    vector: list[float],
) -> str:
    payload = "|".join(
        f"{name}:{int(round(value * 1_000_000))}"
        for name, value in zip(feature_names, vector, strict=True)
    )
    return "LATENT_CONCEPT_" + sha256(payload.encode()).hexdigest()[:12].upper()


def _probes(
    feature_names: tuple[str, ...],
    vector: list[float],
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


def fit_representation_discovery(
    *,
    fitted_at: datetime,
    episodes: tuple[RepresentationEpisode, ...],
    policy: RepresentationDiscoveryPolicy | None = None,
) -> RepresentationDiscoveryModel:
    """Fit target-blind latent concepts from residual market representation."""

    if fitted_at.tzinfo is None or fitted_at.utcoffset() is None:
        raise ValueError("fitted_at must be timezone-aware")
    effective = policy or RepresentationDiscoveryPolicy()
    eligible = tuple(
        item
        for item in episodes
        if item.integrity_bps >= effective.minimum_integrity_bps
    )
    if len(eligible) < effective.minimum_episode_count:
        raise ValueError("insufficient episodes for representation discovery")
    if any(item.as_of > fitted_at for item in eligible):
        raise ValueError("future representation evidence is forbidden")

    partitions = {item.partition for item in eligible}
    if len(partitions) != 1:
        raise ValueError("representation discovery must fit one partition only")
    discovery_partition = next(iter(partitions))

    first = eligible[0]
    feature_names = tuple(sorted(item.name for item in first.features))
    ontology_names = tuple(sorted(item.name for item in first.ontology))
    feature_rows = [
        _ordered_values(item, feature_names, ontology=False)
        for item in eligible
    ]
    ontology_rows = [
        _ordered_values(item, ontology_names, ontology=True)
        for item in eligible
    ]

    feature_means, feature_scales = _mean_scale(
        feature_rows,
        effective.minimum_feature_scale,
    )
    ontology_means, ontology_scales = _mean_scale(
        ontology_rows,
        effective.minimum_feature_scale,
    )
    standardized_features = _standardize(
        feature_rows,
        feature_means,
        feature_scales,
    )
    standardized_ontology = _standardize(
        ontology_rows,
        ontology_means,
        ontology_scales,
    )
    residuals, coefficients = _residual_matrix(
        standardized_features,
        standardized_ontology,
        effective.residualization_ridge,
    )
    covariance = _covariance(residuals)
    components = _components(covariance, effective)
    total_residual_variance = sum(
        covariance[index][index] for index in range(len(covariance))
    )

    definitions: list[LatentConceptDefinition] = []
    for eigenvalue, vector in components:
        scores = [
            _dot(row, vector)
            for row in residuals
        ]
        positive_indexes = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[: effective.cluster_episode_count]
        negative_indexes = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
        )[: effective.cluster_episode_count]
        definitions.append(
            LatentConceptDefinition(
                concept_id=_concept_id(feature_names, vector),
                loading_micros=tuple(
                    int(round(value * 1_000_000))
                    for value in vector
                ),
                explained_residual_variance_bps=(
                    0
                    if total_residual_variance <= 1e-12
                    else int(
                        round(
                            eigenvalue
                            / total_residual_variance
                            * 10_000
                        )
                    )
                ),
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
                    eligible[index].episode_id
                    for index in positive_indexes
                ),
                negative_cluster_episode_ids=tuple(
                    eligible[index].episode_id
                    for index in negative_indexes
                ),
            )
        )

    residualizer_models = tuple(
        FeatureResidualizer(
            feature_name=feature_names[index],
            ontology_coefficients_micros=tuple(
                int(round(value * 1_000_000))
                for value in coefficients[index]
            ),
        )
        for index in range(len(feature_names))
    )
    cutoff = max(item.as_of for item in eligible)
    return RepresentationDiscoveryModel(
        fitted_at=fitted_at,
        evidence_cutoff_at=cutoff,
        discovery_partition=discovery_partition,
        episode_count=len(eligible),
        feature_names=feature_names,
        ontology_names=ontology_names,
        feature_means=tuple(feature_means),
        feature_scales=tuple(feature_scales),
        ontology_means=tuple(ontology_means),
        ontology_scales=tuple(ontology_scales),
        residualizers=residualizer_models,
        concepts=tuple(definitions),
    )


def project_representation(
    *,
    model: RepresentationDiscoveryModel,
    episode: RepresentationEpisode,
) -> LatentRepresentation:
    """Project a point-in-time episode into a frozen latent representation."""

    feature_row = _ordered_values(
        episode,
        model.feature_names,
        ontology=False,
    )
    ontology_row = _ordered_values(
        episode,
        model.ontology_names,
        ontology=True,
    )
    standardized_features = _standardize(
        [feature_row],
        model.feature_means,
        model.feature_scales,
    )[0]
    standardized_ontology = _standardize(
        [ontology_row],
        model.ontology_means,
        model.ontology_scales,
    )[0]

    residual: list[float] = []
    for index, residualizer in enumerate(model.residualizers):
        coefficients = [
            value / 1_000_000.0
            for value in residualizer.ontology_coefficients_micros
        ]
        predicted = sum(
            coefficient * value
            for coefficient, value in zip(
                coefficients,
                standardized_ontology,
                strict=True,
            )
        )
        residual.append(standardized_features[index] - predicted)

    activations = []
    for concept in model.concepts:
        vector = [
            value / 1_000_000.0
            for value in concept.loading_micros
        ]
        activations.append(
            LatentConceptActivation(
                concept_id=concept.concept_id,
                activation_milli_z=int(
                    round(_dot(residual, vector) * 1_000)
                ),
            )
        )
    return LatentRepresentation(
        episode_id=episode.episode_id,
        as_of=episode.as_of,
        activations=tuple(activations),
    )
