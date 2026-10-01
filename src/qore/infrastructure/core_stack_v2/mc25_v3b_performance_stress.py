"""MC-25 same-lineage performance-stress transforms for frozen WP04 V3B."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Final, Sequence

import numpy as np

from qore.infrastructure.core_stack_v2.representation_predictive_nonlinear_probe_v3b import (
    PredictiveSecondOrderEvaluation,
    PreparedSecondOrderDesign,
)

MINIMUM_POOLED_INCREMENTAL_BPS: Final = 100
MINIMUM_POSITIVE_TARGETS: Final = 4


class V3BStressKind(StrEnum):
    HASH_ROW_DROP = "HASH_ROW_DROP"
    CONTIGUOUS_TIME_DROP = "CONTIGUOUS_TIME_DROP"
    LATENT_ATTENUATION = "LATENT_ATTENUATION"
    LATENT_QUANTIZATION = "LATENT_QUANTIZATION"
    HASH_DROP_AND_ATTENUATION = "HASH_DROP_AND_ATTENUATION"


@dataclass(frozen=True, slots=True)
class V3BStressScenario:
    scenario_id: str
    kind: V3BStressKind
    drop_bps: int = 0
    attenuation_bps: int = 10_000
    quantization_milli: int = 0

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("stress scenario_id must be non-empty")
        if not isinstance(self.kind, V3BStressKind):
            raise ValueError("stress kind invalid")
        if not 0 <= self.drop_bps < 5_000:
            raise ValueError("stress drop_bps must be within 0..4999")
        if not 5_000 <= self.attenuation_bps <= 10_000:
            raise ValueError(
                "stress attenuation_bps must be within 5000..10000"
            )
        if not 0 <= self.quantization_milli <= 500:
            raise ValueError(
                "stress quantization_milli must be within 0..500"
            )


FROZEN_STRESS_SCENARIOS: Final = (
    V3BStressScenario(
        "HASH_ROW_DROP_10PCT",
        V3BStressKind.HASH_ROW_DROP,
        drop_bps=1_000,
    ),
    V3BStressScenario(
        "HASH_ROW_DROP_20PCT",
        V3BStressKind.HASH_ROW_DROP,
        drop_bps=2_000,
    ),
    V3BStressScenario(
        "CONTIGUOUS_TIME_DROP_10PCT",
        V3BStressKind.CONTIGUOUS_TIME_DROP,
        drop_bps=1_000,
    ),
    V3BStressScenario(
        "LATENT_ATTENUATION_10PCT",
        V3BStressKind.LATENT_ATTENUATION,
        attenuation_bps=9_000,
    ),
    V3BStressScenario(
        "LATENT_QUANTIZATION_0_05",
        V3BStressKind.LATENT_QUANTIZATION,
        quantization_milli=50,
    ),
    V3BStressScenario(
        "COMBINED_DROP10_ATTENUATION10",
        V3BStressKind.HASH_DROP_AND_ATTENUATION,
        drop_bps=1_000,
        attenuation_bps=9_000,
    ),
)


def _hash_bucket(episode_id: str) -> int:
    digest = sha256(episode_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % 10_000


def _hash_keep_mask(
    episode_ids: tuple[str, ...],
    *,
    drop_bps: int,
) -> np.ndarray:
    return np.asarray(
        [_hash_bucket(item) >= drop_bps for item in episode_ids],
        dtype=np.bool_,
    )


def _contiguous_keep_mask(
    row_count: int,
    *,
    drop_bps: int,
) -> np.ndarray:
    if row_count <= 0:
        raise ValueError("contiguous stress requires rows")
    drop_count = max(1, row_count * drop_bps // 10_000)
    start = max(0, (row_count - drop_count) // 2)
    end = min(row_count, start + drop_count)
    mask = np.ones(row_count, dtype=np.bool_)
    mask[start:end] = False
    return mask


def _subset(
    prepared: PreparedSecondOrderDesign,
    mask: np.ndarray,
) -> PreparedSecondOrderDesign:
    if mask.ndim != 1 or mask.shape[0] != len(prepared.episode_ids):
        raise ValueError("stress row mask shape mismatch")
    if int(mask.sum()) <= 0:
        raise ValueError("stress removed every evaluation row")
    baseline = np.asarray(prepared.baseline[mask], dtype=np.float64)
    augmented = np.asarray(prepared.augmented[mask], dtype=np.float64)
    baseline.setflags(write=False)
    augmented.setflags(write=False)
    indexes = np.flatnonzero(mask)
    return PreparedSecondOrderDesign(
        partitions=prepared.partitions,
        episode_ids=tuple(prepared.episode_ids[int(i)] for i in indexes),
        as_of=tuple(prepared.as_of[int(i)] for i in indexes),
        baseline=baseline,
        augmented=augmented,
    )


def _alter_augmented(
    prepared: PreparedSecondOrderDesign,
    *,
    attenuation_bps: int = 10_000,
    quantization_milli: int = 0,
) -> PreparedSecondOrderDesign:
    baseline_width = prepared.baseline.shape[1]
    if prepared.augmented.shape[1] <= baseline_width:
        raise ValueError("V3B augmented design lost latent additions")
    augmented = np.array(prepared.augmented, dtype=np.float64, copy=True)
    added = augmented[:, baseline_width:]
    if attenuation_bps != 10_000:
        added *= attenuation_bps / 10_000.0
    if quantization_milli:
        step = quantization_milli / 1_000.0
        added[:] = np.round(added / step) * step
    augmented.setflags(write=False)
    baseline = np.asarray(prepared.baseline, dtype=np.float64)
    baseline.setflags(write=False)
    return PreparedSecondOrderDesign(
        partitions=prepared.partitions,
        episode_ids=prepared.episode_ids,
        as_of=prepared.as_of,
        baseline=baseline,
        augmented=augmented,
    )


def apply_v3b_performance_stress(
    prepared: PreparedSecondOrderDesign,
    scenario: V3BStressScenario,
) -> PreparedSecondOrderDesign:
    """Apply one frozen, target-blind perturbation without refitting."""

    if not isinstance(scenario, V3BStressScenario):
        raise TypeError("scenario must be V3BStressScenario")
    result = prepared
    if scenario.kind in {
        V3BStressKind.HASH_ROW_DROP,
        V3BStressKind.HASH_DROP_AND_ATTENUATION,
    }:
        result = _subset(
            result,
            _hash_keep_mask(
                result.episode_ids,
                drop_bps=scenario.drop_bps,
            ),
        )
    elif scenario.kind is V3BStressKind.CONTIGUOUS_TIME_DROP:
        result = _subset(
            result,
            _contiguous_keep_mask(
                len(result.episode_ids),
                drop_bps=scenario.drop_bps,
            ),
        )

    if scenario.kind in {
        V3BStressKind.LATENT_ATTENUATION,
        V3BStressKind.HASH_DROP_AND_ATTENUATION,
    }:
        result = _alter_augmented(
            result,
            attenuation_bps=scenario.attenuation_bps,
        )
    elif scenario.kind is V3BStressKind.LATENT_QUANTIZATION:
        result = _alter_augmented(
            result,
            quantization_milli=scenario.quantization_milli,
        )
    return result


def summarize_v3b_stress_evaluations(
    evaluations: Sequence[PredictiveSecondOrderEvaluation],
) -> dict[str, object]:
    if not evaluations:
        raise ValueError("stress summary requires evaluations")
    total_weight = sum(item.sample_count for item in evaluations)
    if total_weight <= 0:
        raise ValueError("stress summary requires positive sample weight")
    baseline = sum(
        item.baseline_mse_micros * item.sample_count
        for item in evaluations
    ) / total_weight
    augmented = sum(
        item.augmented_mse_micros * item.sample_count
        for item in evaluations
    ) / total_weight
    incremental = (
        0
        if baseline <= 0
        else int(round((baseline - augmented) / baseline * 10_000))
    )
    positive = sum(
        item.incremental_information_bps > 0
        for item in evaluations
    )
    passed = (
        incremental >= MINIMUM_POOLED_INCREMENTAL_BPS
        and positive >= MINIMUM_POSITIVE_TARGETS
    )
    return {
        "target_count": len(evaluations),
        "sample_count_per_target": min(
            item.sample_count for item in evaluations
        ),
        "positive_target_count": positive,
        "minimum_positive_target_count": MINIMUM_POSITIVE_TARGETS,
        "pooled_baseline_mse_micros": int(round(baseline)),
        "pooled_augmented_mse_micros": int(round(augmented)),
        "pooled_incremental_information_bps": incremental,
        "minimum_pooled_incremental_bps": (
            MINIMUM_POOLED_INCREMENTAL_BPS
        ),
        "pass": passed,
        "targets": [
            {
                "target_name": item.target_name,
                "sample_count": item.sample_count,
                "baseline_mse_micros": item.baseline_mse_micros,
                "augmented_mse_micros": item.augmented_mse_micros,
                "incremental_information_bps": (
                    item.incremental_information_bps
                ),
                "probe_fingerprint": item.probe_fingerprint,
            }
            for item in evaluations
        ],
    }
