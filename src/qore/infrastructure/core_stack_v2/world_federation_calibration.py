"""Evaluation-only calibration diagnostics for WP-02 Federation of Worlds.

This module measures whether federated world posteriors remain calibrated and
adapt under regime changes. Realized forward quality is an evaluation label
only: it is forbidden from feeding the runtime federation state.

The evaluator is intentionally trader-agnostic. It consumes world posterior
probabilities and forward predictive quality by world family; it does not
consume trade PnL, sizing, broker outcomes, stops, targets or order state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.multi_world_engine import (
    WorldModelFamily,
)
from qore.infrastructure.core_stack_v2.multi_world_federation import (
    WorldFederationState,
)


class WorldEvaluationPartition(StrEnum):
    CALIBRATION = "CALIBRATION"
    HOLDOUT = "HOLDOUT"


@dataclass(frozen=True, slots=True)
class RealizedWorldQuality:
    family: WorldModelFamily
    quality_bps: int

    def __post_init__(self) -> None:
        if not 0 <= self.quality_bps <= 10_000:
            raise ValueError("quality_bps must be within 0..10000")


@dataclass(frozen=True, slots=True)
class WorldCalibrationEpisode:
    as_of: datetime
    evaluated_at: datetime
    partition: WorldEvaluationPartition
    regime_key: str
    posterior_bps: tuple[tuple[WorldModelFamily, int], ...]
    realized_quality: tuple[RealizedWorldQuality, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    runtime_future_market_used: bool = False
    trading_authority: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("as_of", self.as_of),
            ("evaluated_at", self.evaluated_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evaluated_at <= self.as_of:
            raise ValueError("evaluation label must mature after as_of")
        if not self.regime_key:
            raise ValueError("regime_key must be non-empty")

        posterior_families = [family for family, _ in self.posterior_bps]
        if len(set(posterior_families)) != len(posterior_families):
            raise ValueError("posterior families must be unique")
        if set(posterior_families) != set(WorldModelFamily):
            raise ValueError("posterior must cover every world family")
        for _, probability_bps in self.posterior_bps:
            if not 0 <= probability_bps <= 10_000:
                raise ValueError("posterior probability must be within 0..10000")
        if sum(value for _, value in self.posterior_bps) != 10_000:
            raise ValueError("posterior probability mass must sum to 10000 bps")

        quality_families = [item.family for item in self.realized_quality]
        if len(set(quality_families)) != len(quality_families):
            raise ValueError("realized quality families must be unique")
        if set(quality_families) != set(WorldModelFamily):
            raise ValueError("realized quality must cover every world family")

        if (
            self.outcome_used
            or self.pnl_used
            or self.runtime_future_market_used
            or self.trading_authority
        ):
            raise ValueError("world calibration is evaluation-only")


@dataclass(frozen=True, slots=True)
class WorldCalibrationSummary:
    partition: WorldEvaluationPartition
    episode_count: int
    top_world_accuracy_bps: int
    expected_calibration_error_bps: int
    brier_score_bps: int
    mean_dominant_probability_bps: int
    mean_dominant_realized_quality_bps: int
    monopoly_episode_count: int
    monopoly_rate_bps: int
    regime_shift_count: int
    recovered_regime_shift_count: int
    unresolved_regime_shift_count: int
    mean_recovery_steps_milli: int
    evaluation_only: bool = True
    trading_authority: bool = False


@dataclass(frozen=True, slots=True)
class WorldCalibrationComparison:
    calibration: WorldCalibrationSummary
    holdout: WorldCalibrationSummary
    accuracy_delta_bps: int
    calibration_error_delta_bps: int
    brier_delta_bps: int
    monopoly_rate_delta_bps: int
    temporal_holdout: bool
    evaluation_only: bool = True
    trading_authority: bool = False


def episode_from_state(
    *,
    state: WorldFederationState,
    evaluated_at: datetime,
    partition: WorldEvaluationPartition,
    regime_key: str,
    realized_quality: tuple[RealizedWorldQuality, ...],
) -> WorldCalibrationEpisode:
    """Freeze a runtime posterior beside later evaluation-only labels."""

    return WorldCalibrationEpisode(
        as_of=state.as_of,
        evaluated_at=evaluated_at,
        partition=partition,
        regime_key=regime_key,
        posterior_bps=tuple(
            (item.family, item.probability_bps) for item in state.posteriors
        ),
        realized_quality=realized_quality,
    )


def _ratio_bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return max(0, min(10_000, numerator * 10_000 // denominator))


def _best_families(
    episode: WorldCalibrationEpisode,
) -> frozenset[WorldModelFamily]:
    best = max(item.quality_bps for item in episode.realized_quality)
    return frozenset(
        item.family for item in episode.realized_quality if item.quality_bps == best
    )


def _dominant(
    episode: WorldCalibrationEpisode,
) -> tuple[WorldModelFamily, int]:
    return min(
        episode.posterior_bps,
        key=lambda item: (-item[1], item[0].value),
    )


def _brier_bps(episode: WorldCalibrationEpisode) -> int:
    best = _best_families(episode)
    target = 10_000 // len(best)
    remainder = 10_000 - target * len(best)
    best_order = sorted(best, key=lambda family: family.value)
    target_by_family = {family: target for family in best}
    for family in best_order[:remainder]:
        target_by_family[family] += 1

    squared_error = 0
    for family, probability_bps in episode.posterior_bps:
        expected = target_by_family.get(family, 0)
        squared_error += (probability_bps - expected) ** 2

    denominator = len(WorldModelFamily) * 10_000
    return min(10_000, squared_error // denominator)


def summarize_world_calibration(
    episodes: tuple[WorldCalibrationEpisode, ...],
    *,
    monopoly_threshold_bps: int = 9_900,
) -> WorldCalibrationSummary:
    """Measure calibration, diversity and recovery without changing runtime."""

    if not episodes:
        raise ValueError("world calibration requires episodes")
    if not 0 <= monopoly_threshold_bps <= 10_000:
        raise ValueError("monopoly_threshold_bps must be within 0..10000")

    partition = episodes[0].partition
    if any(item.partition is not partition for item in episodes):
        raise ValueError("summary cannot mix calibration and holdout episodes")

    ordered = tuple(sorted(episodes, key=lambda item: item.as_of))
    if len({item.as_of for item in ordered}) != len(ordered):
        raise ValueError("world calibration episode timestamps must be unique")

    correct = 0
    brier_total = 0
    dominant_probability_total = 0
    dominant_quality_total = 0
    monopoly_count = 0
    calibration_bins: dict[int, list[int]] = {}

    shifts = 0
    recovered_shifts = 0
    unresolved_shifts = 0
    recovery_steps: list[int] = []

    previous_regime = ordered[0].regime_key
    pending_shift_index: int | None = None

    for index, episode in enumerate(ordered):
        dominant_family, confidence_bps = _dominant(episode)
        best = _best_families(episode)
        is_correct = dominant_family in best
        correct += int(is_correct)
        brier_total += _brier_bps(episode)
        dominant_probability_total += confidence_bps
        dominant_quality_total += next(
            item.quality_bps
            for item in episode.realized_quality
            if item.family is dominant_family
        )
        if confidence_bps >= monopoly_threshold_bps:
            monopoly_count += 1

        bucket = min(9, confidence_bps // 1_000)
        bucket_values = calibration_bins.setdefault(bucket, [0, 0, 0])
        bucket_values[0] += 1
        bucket_values[1] += confidence_bps
        bucket_values[2] += 10_000 if is_correct else 0

        if episode.regime_key != previous_regime:
            shifts += 1
            if pending_shift_index is not None:
                unresolved_shifts += 1
            pending_shift_index = index
            previous_regime = episode.regime_key

        if pending_shift_index is not None and is_correct:
            recovered_shifts += 1
            recovery_steps.append(index - pending_shift_index)
            pending_shift_index = None

    if pending_shift_index is not None:
        unresolved_shifts += 1

    ece_weighted = 0
    total = len(ordered)
    for count, confidence_sum, correctness_sum in calibration_bins.values():
        mean_confidence = confidence_sum // count
        empirical_accuracy = correctness_sum // count
        ece_weighted += abs(mean_confidence - empirical_accuracy) * count

    mean_recovery_steps_milli = (
        0
        if not recovery_steps
        else sum(recovery_steps) * 1_000 // len(recovery_steps)
    )

    return WorldCalibrationSummary(
        partition=partition,
        episode_count=total,
        top_world_accuracy_bps=_ratio_bps(correct, total),
        expected_calibration_error_bps=ece_weighted // total,
        brier_score_bps=brier_total // total,
        mean_dominant_probability_bps=dominant_probability_total // total,
        mean_dominant_realized_quality_bps=dominant_quality_total // total,
        monopoly_episode_count=monopoly_count,
        monopoly_rate_bps=_ratio_bps(monopoly_count, total),
        regime_shift_count=shifts,
        recovered_regime_shift_count=recovered_shifts,
        unresolved_regime_shift_count=unresolved_shifts,
        mean_recovery_steps_milli=mean_recovery_steps_milli,
    )


def compare_calibration_to_holdout(
    *,
    calibration: tuple[WorldCalibrationEpisode, ...],
    holdout: tuple[WorldCalibrationEpisode, ...],
    monopoly_threshold_bps: int = 9_900,
) -> WorldCalibrationComparison:
    """Compare frozen calibration against a temporally disjoint holdout."""

    calibration_summary = summarize_world_calibration(
        calibration,
        monopoly_threshold_bps=monopoly_threshold_bps,
    )
    holdout_summary = summarize_world_calibration(
        holdout,
        monopoly_threshold_bps=monopoly_threshold_bps,
    )
    if calibration_summary.partition is not WorldEvaluationPartition.CALIBRATION:
        raise ValueError("calibration input must use CALIBRATION partition")
    if holdout_summary.partition is not WorldEvaluationPartition.HOLDOUT:
        raise ValueError("holdout input must use HOLDOUT partition")

    calibration_end = max(item.evaluated_at for item in calibration)
    holdout_start = min(item.as_of for item in holdout)
    if calibration_end >= holdout_start:
        raise ValueError("holdout must be temporally disjoint from calibration")

    return WorldCalibrationComparison(
        calibration=calibration_summary,
        holdout=holdout_summary,
        accuracy_delta_bps=(
            holdout_summary.top_world_accuracy_bps
            - calibration_summary.top_world_accuracy_bps
        ),
        calibration_error_delta_bps=(
            holdout_summary.expected_calibration_error_bps
            - calibration_summary.expected_calibration_error_bps
        ),
        brier_delta_bps=(
            holdout_summary.brier_score_bps
            - calibration_summary.brier_score_bps
        ),
        monopoly_rate_delta_bps=(
            holdout_summary.monopoly_rate_bps
            - calibration_summary.monopoly_rate_bps
        ),
        temporal_holdout=True,
    )
