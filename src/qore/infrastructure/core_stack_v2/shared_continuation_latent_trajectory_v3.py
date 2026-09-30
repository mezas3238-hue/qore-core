"""Unsupervised latent trajectory state model for STI-6 V3.

The representation is fit from source-time trajectory features without trade
outcomes. State IDs are intentionally semantic-free until separate development
evidence associates them with future outcomes.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)
from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_v2 import (
    continuation_trajectory_v2_features,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)

FEATURE_NAMES = (
    "continuation_velocity_bps",
    "tail_velocity_bps",
    "local_expansion_bps",
    "expansion_persistence_bps",
    "failure_hazard_bps",
    "world_coherence_bps",
    "uncertainty_bps",
)


@dataclass(frozen=True, slots=True)
class SharedLatentTrajectoryModel:
    model_id: str
    feature_names: tuple[str, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    centroids: tuple[tuple[float, ...], ...]
    cluster_count: int
    iterations: int
    sequence_window: int
    source_only_fit: bool
    evidence_refs: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory model_id must be non-empty"
            )
        if self.feature_names != FEATURE_NAMES:
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory features must remain preregistered"
            )
        width = len(FEATURE_NAMES)
        if len(self.means) != width or len(self.scales) != width:
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory normalization width mismatch"
            )
        if any(scale <= 0 or not math.isfinite(scale) for scale in self.scales):
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory scales must be positive finite"
            )
        if self.cluster_count != 6 or len(self.centroids) != self.cluster_count:
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V3 cluster_count is preregistered at 6"
            )
        if self.iterations != 25:
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V3 iterations are preregistered at 25"
            )
        if self.sequence_window != 5:
            raise SharedTraderIntelligenceValidationError(
                "STI-6 V3 sequence_window is preregistered at 5"
            )
        for centroid in self.centroids:
            if len(centroid) != width or any(
                not math.isfinite(value) for value in centroid
            ):
                raise SharedTraderIntelligenceValidationError(
                    "latent trajectory centroid malformed"
                )
        if not self.source_only_fit:
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory model must be fit source-only"
            )
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory evidence refs must be canonical"
            )
        if self.productive_authority:
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory research model has no productive authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedLatentTrajectoryState:
    state_id: str
    cluster_index: int
    distance: float
    model_fingerprint: str
    outcome_semantics_assigned: bool = False
    mandatory_hold: bool = False
    position_management_authority: bool = False
    execution_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if self.state_id != f"LATENT_TRAJECTORY_STATE_{self.cluster_index + 1:02d}":
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory state_id must derive from cluster index"
            )
        if self.cluster_index < 0 or self.cluster_index >= 6:
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory cluster_index out of range"
            )
        if self.distance < 0 or not math.isfinite(self.distance):
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory distance must be non-negative finite"
            )
        if len(self.model_fingerprint) != 64:
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory model fingerprint must be sha256"
            )
        if self.outcome_semantics_assigned:
            raise SharedTraderIntelligenceValidationError(
                "raw latent state cannot contain outcome semantics"
            )
        if (
            self.mandatory_hold
            or self.position_management_authority
            or self.execution_authority
            or self.sizing_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "latent trajectory state cannot command position management"
            )


def trajectory_feature_vector(
    observations: Sequence[SharedPositionCausalObservation],
    *,
    sequence_window: int = 5,
) -> tuple[float, ...]:
    raw = continuation_trajectory_v2_features(
        observations,
        sequence_window=sequence_window,
    )
    return tuple(float(value) for value in raw)


def _normalize_rows(
    rows: Sequence[tuple[float, ...]],
) -> tuple[
    tuple[float, ...],
    tuple[float, ...],
    tuple[tuple[float, ...], ...],
]:
    if not rows:
        raise SharedTraderIntelligenceValidationError(
            "latent trajectory fit requires rows"
        )
    width = len(FEATURE_NAMES)
    if any(len(row) != width for row in rows):
        raise SharedTraderIntelligenceValidationError(
            "latent trajectory row width mismatch"
        )
    count = float(len(rows))
    means = tuple(sum(row[i] for row in rows) / count for i in range(width))
    scales_list: list[float] = []
    for i in range(width):
        variance = sum((row[i] - means[i]) ** 2 for row in rows) / count
        scale = math.sqrt(variance)
        scales_list.append(scale if scale > 1e-12 else 1.0)
    scales = tuple(scales_list)
    normalized = tuple(
        tuple((row[i] - means[i]) / scales[i] for i in range(width))
        for row in rows
    )
    return means, scales, normalized


def _distance_sq(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))


def _initial_centroids(
    rows: tuple[tuple[float, ...], ...],
    *,
    cluster_count: int,
) -> tuple[tuple[float, ...], ...]:
    first = min(rows, key=lambda row: (sum(value * value for value in row), row))
    centroids = [first]
    while len(centroids) < cluster_count:
        candidate = max(
            rows,
            key=lambda row: (
                min(_distance_sq(row, centroid) for centroid in centroids),
                tuple(-value for value in row),
            ),
        )
        if candidate in centroids:
            for row in sorted(rows):
                if row not in centroids:
                    candidate = row
                    break
        centroids.append(candidate)
    return tuple(centroids)


def fit_latent_trajectory_model(
    rows: Sequence[tuple[float, ...]],
    *,
    model_id: str = "QORE_SHARED_STI6_V3_LATENT_TRAJECTORY_MODEL_001",
    cluster_count: int = 6,
    iterations: int = 25,
    sequence_window: int = 5,
    evidence_refs: tuple[str, ...] = (
        "immutable-r8-source-only-latent-trajectory-fit",
        "sti6-v3-preregistration-001",
    ),
) -> SharedLatentTrajectoryModel:
    means, scales, normalized = _normalize_rows(rows)
    if len(normalized) < cluster_count:
        raise SharedTraderIntelligenceValidationError(
            "latent trajectory fit has fewer rows than clusters"
        )
    centroids = list(
        _initial_centroids(normalized, cluster_count=cluster_count)
    )

    for _ in range(iterations):
        groups: list[list[tuple[float, ...]]] = [
            [] for _ in range(cluster_count)
        ]
        for row in normalized:
            index = min(
                range(cluster_count),
                key=lambda i: (_distance_sq(row, centroids[i]), i),
            )
            groups[index].append(row)

        new_centroids: list[tuple[float, ...]] = []
        for index, group in enumerate(groups):
            if not group:
                new_centroids.append(centroids[index])
                continue
            new_centroids.append(
                tuple(
                    sum(row[j] for row in group) / len(group)
                    for j in range(len(FEATURE_NAMES))
                )
            )
        centroids = new_centroids

    canonical_centroids = tuple(
        tuple(round(value, 12) for value in centroid)
        for centroid in centroids
    )
    return SharedLatentTrajectoryModel(
        model_id=model_id,
        feature_names=FEATURE_NAMES,
        means=tuple(round(value, 12) for value in means),
        scales=tuple(round(value, 12) for value in scales),
        centroids=canonical_centroids,
        cluster_count=cluster_count,
        iterations=iterations,
        sequence_window=sequence_window,
        source_only_fit=True,
        evidence_refs=tuple(sorted(evidence_refs)),
    )


def assign_latent_trajectory_state(
    observations: Sequence[SharedPositionCausalObservation],
    *,
    model: SharedLatentTrajectoryModel,
) -> SharedLatentTrajectoryState:
    raw = trajectory_feature_vector(
        observations,
        sequence_window=model.sequence_window,
    )
    normalized = tuple(
        (raw[i] - model.means[i]) / model.scales[i]
        for i in range(len(FEATURE_NAMES))
    )
    index = min(
        range(model.cluster_count),
        key=lambda i: (_distance_sq(normalized, model.centroids[i]), i),
    )
    distance = math.sqrt(_distance_sq(normalized, model.centroids[index]))
    return SharedLatentTrajectoryState(
        state_id=f"LATENT_TRAJECTORY_STATE_{index + 1:02d}",
        cluster_index=index,
        distance=distance,
        model_fingerprint=model.fingerprint(),
    )
