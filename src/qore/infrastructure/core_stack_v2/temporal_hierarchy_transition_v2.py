"""WP-05 V2 generative temporal-hierarchy propagation model.

V1 classified one current multi-scale snapshot and was falsified OOS. V2 models
*how* adversity evolves through the hierarchy before the current as-of time.

The representation is structural rather than a threshold stack:
- each source-only snapshot preserves its per-scale state;
- a trajectory embedding measures containment, bottom-up propagation,
  higher-level fragility/resilience and their change through time;
- terminal and recoverable paths are represented by class-conditional
  generative prototypes learned on consumed research evidence;
- declaration threshold is calibrated on the fit partition for terminal recall
  and then frozen.

Historical terminal labels may be used offline after maturation. Runtime
projection consumes only source snapshots and has no trader, sizing, Risk,
order or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import exp, fsum, log
from statistics import fmean

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalScaleState,
    baseline_local_opposition,
)

_LOW_SCALES = (
    WorldScale.M1,
    WorldScale.M3,
    WorldScale.M5,
)
_PROPAGATION_SCALES = (
    WorldScale.M15,
    WorldScale.H1,
    WorldScale.H4,
)
_HIGH_SCALES = (
    WorldScale.H1,
    WorldScale.H4,
    WorldScale.DAILY,
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _mean(values: list[float]) -> float:
    return 0.0 if not values else fmean(values)


def _level_map(snapshot: TemporalHierarchySnapshot) -> dict[WorldScale, TemporalScaleState]:
    return {item.scale: item for item in snapshot.levels}


def _mean_direction(
    levels: dict[WorldScale, TemporalScaleState],
    scales: tuple[WorldScale, ...],
) -> float:
    return _mean(
        [
            levels[scale].direction_milli / 1_000.0
            for scale in scales
            if scale in levels
        ]
    )


def _high_anchor(levels: dict[WorldScale, TemporalScaleState]) -> float:
    daily = levels.get(WorldScale.DAILY)
    if daily is not None and daily.direction_milli != 0:
        return daily.direction_milli / 1_000.0
    return _mean_direction(levels, _HIGH_SCALES)


def _high_fragility(levels: dict[WorldScale, TemporalScaleState]) -> float:
    rows = [levels[scale] for scale in _HIGH_SCALES if scale in levels]
    return _mean(
        [
            (item.fragility_bps + item.transition_bps) / 20_000.0
            for item in rows
        ]
    )


def _high_resilience(levels: dict[WorldScale, TemporalScaleState]) -> float:
    rows = [levels[scale] for scale in _HIGH_SCALES if scale in levels]
    return _mean(
        [
            (
                (item.persistence_bps + item.coherence_bps) / 20_000.0
                * (1.0 - item.fragility_bps / 10_000.0)
            )
            for item in rows
        ]
    )


def _propagation(levels: dict[WorldScale, TemporalScaleState]) -> float:
    anchor = _high_anchor(levels)
    sign = 1.0 if anchor > 0 else -1.0 if anchor < 0 else 0.0
    if sign == 0.0:
        return 0.0
    weighted: list[float] = []
    weights = {
        WorldScale.M15: 1.0,
        WorldScale.H1: 2.0,
        WorldScale.H4: 3.0,
    }
    for scale in _PROPAGATION_SCALES:
        item = levels.get(scale)
        if item is None:
            continue
        adverse = max(0.0, -sign * item.direction_milli / 1_000.0)
        transition = item.transition_bps / 10_000.0
        fragility = item.fragility_bps / 10_000.0
        weighted.append(
            weights[scale]
            * adverse
            * (0.50 + 0.25 * transition + 0.25 * fragility)
        )
    denominator = sum(
        weights[scale] for scale in _PROPAGATION_SCALES if scale in levels
    )
    return 0.0 if denominator <= 0 else fsum(weighted) / denominator


def _containment(levels: dict[WorldScale, TemporalScaleState]) -> float:
    low = _mean_direction(levels, _LOW_SCALES)
    high = _mean_direction(levels, _HIGH_SCALES)
    opposition = max(0.0, -(low * high))
    return max(0.0, opposition - _propagation(levels))


def _cross_scale_disagreement(
    levels: dict[WorldScale, TemporalScaleState],
) -> float:
    ordered = (
        WorldScale.M1,
        WorldScale.M3,
        WorldScale.M5,
        WorldScale.M15,
        WorldScale.H1,
        WorldScale.H4,
        WorldScale.DAILY,
    )
    values = [
        levels[scale].direction_milli / 1_000.0
        for scale in ordered
        if scale in levels
    ]
    if len(values) < 2:
        return 0.0
    return fmean(
        abs(right - left) / 2.0
        for left, right in zip(values, values[1:], strict=False)
    )


@dataclass(frozen=True, slots=True)
class TemporalHierarchyTrajectory:
    episode_id: str
    snapshots: tuple[TemporalHierarchySnapshot, ...]
    future_market_used: bool = False
    outcome_used: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("trajectory episode_id must be non-empty")
        if len(self.snapshots) < 3:
            raise ValueError("hierarchy trajectory requires at least three snapshots")
        times = tuple(_utc(item.as_of) for item in self.snapshots)
        if tuple(sorted(times)) != times or len(set(times)) != len(times):
            raise ValueError("trajectory snapshots must be strictly time ordered")
        if (
            self.future_market_used
            or self.outcome_used
            or self.trader_identity_used
            or self.symbol_identity_used
        ):
            raise ValueError("runtime hierarchy trajectory carries forbidden evidence")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyTrajectoryTrainingEpisode:
    trajectory: TemporalHierarchyTrajectory
    observed_at: datetime
    terminal_failure: bool

    def __post_init__(self) -> None:
        if _utc(self.observed_at) <= _utc(self.trajectory.snapshots[-1].as_of):
            raise ValueError("terminal label must mature after source trajectory")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyTransitionModel:
    fitted_at: datetime
    fit_partition: str
    feature_names: tuple[str, ...]
    terminal_means_micros: tuple[int, ...]
    terminal_scales_micros: tuple[int, ...]
    recovery_means_micros: tuple[int, ...]
    recovery_scales_micros: tuple[int, ...]
    terminal_prior_micros: int
    declaration_threshold_micros: int
    minimum_training_recall_bps: int
    threshold_calibration_recall_bps: int
    fit_opposition_count: int
    fit_terminal_count: int
    target_used_for_training_only: bool = True
    runtime_future_market_used: bool = False
    outcome_used_at_runtime: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    methodology_authority: bool = False
    knowledge_promotion_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _utc(self.fitted_at)
        if not self.fit_partition:
            raise ValueError("fit_partition must be non-empty")
        width = len(self.feature_names)
        if width < 6:
            raise ValueError("transition model requires structural path features")
        if not (
            len(self.terminal_means_micros)
            == len(self.terminal_scales_micros)
            == len(self.recovery_means_micros)
            == len(self.recovery_scales_micros)
            == width
        ):
            raise ValueError("transition prototype width mismatch")
        if any(value <= 0 for value in self.terminal_scales_micros):
            raise ValueError("terminal scales must be positive")
        if any(value <= 0 for value in self.recovery_scales_micros):
            raise ValueError("recovery scales must be positive")
        if not 0 < self.terminal_prior_micros < 1_000_000:
            raise ValueError("terminal prior must be within (0, 1)")
        if not 0 <= self.declaration_threshold_micros <= 1_000_000:
            raise ValueError("declaration threshold out of range")
        if not (
            0
            <= self.minimum_training_recall_bps
            <= self.threshold_calibration_recall_bps
            <= 10_000
        ):
            raise ValueError("invalid recall calibration")
        if self.fit_opposition_count < 1 or self.fit_terminal_count < 1:
            raise ValueError("fit population must be non-empty")
        if (
            self.runtime_future_market_used
            or self.outcome_used_at_runtime
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.methodology_authority
            or self.knowledge_promotion_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("transition model carries forbidden authority")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyTransitionAssessment:
    episode_id: str
    as_of: datetime
    baseline_local_opposition: bool
    terminal_probability_micros: int
    structural_failure_declared: bool
    recoverable_pullback: bool
    future_market_used: bool = False
    target_used: bool = False

    def __post_init__(self) -> None:
        _utc(self.as_of)
        if not 0 <= self.terminal_probability_micros <= 1_000_000:
            raise ValueError("terminal probability out of range")
        if self.structural_failure_declared and self.recoverable_pullback:
            raise ValueError("failure and recoverable pullback cannot coexist")
        if self.future_market_used or self.target_used:
            raise ValueError("runtime transition assessment uses forbidden evidence")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyTransitionEvaluation:
    partition: str
    sample_count: int
    baseline_declaration_count: int
    baseline_terminal_count: int
    baseline_false_declaration_count: int
    hierarchy_declaration_count: int
    hierarchy_terminal_count: int
    hierarchy_false_declaration_count: int
    hierarchy_missed_terminal_count: int
    false_declaration_reduction_bps: int
    terminal_detection_preservation_bps: int


def _trajectory_features(
    trajectory: TemporalHierarchyTrajectory,
) -> tuple[tuple[str, ...], tuple[float, ...]]:
    series = []
    for snapshot in trajectory.snapshots:
        levels = _level_map(snapshot)
        series.append(
            {
                "propagation": _propagation(levels),
                "containment": _containment(levels),
                "high_fragility": _high_fragility(levels),
                "high_resilience": _high_resilience(levels),
                "disagreement": _cross_scale_disagreement(levels),
                "high_direction": _mean_direction(levels, _HIGH_SCALES),
                "low_direction": _mean_direction(levels, _LOW_SCALES),
            }
        )

    first = series[0]
    last = series[-1]
    propagation_steps = [
        right["propagation"] - left["propagation"]
        for left, right in zip(series, series[1:], strict=False)
    ]
    fragility_steps = [
        right["high_fragility"] - left["high_fragility"]
        for left, right in zip(series, series[1:], strict=False)
    ]
    resilience_steps = [
        right["high_resilience"] - left["high_resilience"]
        for left, right in zip(series, series[1:], strict=False)
    ]

    propagation_monotonicity = _mean(
        [1.0 if value > 0 else 0.0 if value == 0 else -1.0 for value in propagation_steps]
    )
    fragility_monotonicity = _mean(
        [1.0 if value > 0 else 0.0 if value == 0 else -1.0 for value in fragility_steps]
    )
    resilience_decay_monotonicity = _mean(
        [1.0 if value < 0 else 0.0 if value == 0 else -1.0 for value in resilience_steps]
    )
    high_direction_erosion = max(
        0.0,
        abs(first["high_direction"]) - abs(last["high_direction"]),
    )

    names = (
        "CURRENT_PROPAGATION",
        "CURRENT_CONTAINMENT",
        "CURRENT_HIGH_FRAGILITY",
        "CURRENT_HIGH_RESILIENCE",
        "CURRENT_DISAGREEMENT",
        "PROPAGATION_CHANGE",
        "FRAGILITY_CHANGE",
        "RESILIENCE_CHANGE",
        "DISAGREEMENT_CHANGE",
        "HIGH_DIRECTION_EROSION",
        "PROPAGATION_MONOTONICITY",
        "FRAGILITY_MONOTONICITY",
        "RESILIENCE_DECAY_MONOTONICITY",
    )
    values = (
        last["propagation"],
        last["containment"],
        last["high_fragility"],
        last["high_resilience"],
        last["disagreement"],
        last["propagation"] - first["propagation"],
        last["high_fragility"] - first["high_fragility"],
        last["high_resilience"] - first["high_resilience"],
        last["disagreement"] - first["disagreement"],
        high_direction_erosion,
        propagation_monotonicity,
        fragility_monotonicity,
        resilience_decay_monotonicity,
    )
    return names, values


def _means_scales(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    width = len(rows[0])
    means = tuple(fmean(row[index] for row in rows) for index in range(width))
    scales = []
    for index, mean in enumerate(means):
        variance = fmean((row[index] - mean) ** 2 for row in rows)
        scales.append(max(1e-4, variance ** 0.5))
    return means, tuple(scales)


def _quantize(values: tuple[float, ...]) -> tuple[int, ...]:
    return tuple(int(round(value * 1_000_000)) for value in values)


def _dequantize(values: tuple[int, ...]) -> tuple[float, ...]:
    return tuple(value / 1_000_000.0 for value in values)


def _posterior_probability(
    *,
    row: tuple[float, ...],
    terminal_means: tuple[float, ...],
    terminal_scales: tuple[float, ...],
    recovery_means: tuple[float, ...],
    recovery_scales: tuple[float, ...],
    terminal_prior: float,
) -> int:
    terminal_nll = 0.0
    recovery_nll = 0.0
    for value, t_mean, t_scale, r_mean, r_scale in zip(
        row,
        terminal_means,
        terminal_scales,
        recovery_means,
        recovery_scales,
        strict=True,
    ):
        terminal_nll += log(t_scale) + 0.5 * ((value - t_mean) / t_scale) ** 2
        recovery_nll += log(r_scale) + 0.5 * ((value - r_mean) / r_scale) ** 2

    prior = _clamp(terminal_prior, 1e-6, 1.0 - 1e-6)
    log_odds = (
        recovery_nll
        - terminal_nll
        + log(prior)
        - log(1.0 - prior)
    )
    if log_odds >= 40.0:
        probability = 1.0
    elif log_odds <= -40.0:
        probability = 0.0
    else:
        probability = 1.0 / (1.0 + exp(-log_odds))
    return int(round(_clamp(probability, 0.0, 1.0) * 1_000_000))


def _score(model: TemporalHierarchyTransitionModel, trajectory: TemporalHierarchyTrajectory) -> int:
    names, row = _trajectory_features(trajectory)
    if names != model.feature_names:
        raise ValueError("temporal transition feature schema drift")
    return _posterior_probability(
        row=row,
        terminal_means=_dequantize(model.terminal_means_micros),
        terminal_scales=_dequantize(model.terminal_scales_micros),
        recovery_means=_dequantize(model.recovery_means_micros),
        recovery_scales=_dequantize(model.recovery_scales_micros),
        terminal_prior=model.terminal_prior_micros / 1_000_000.0,
    )


def fit_temporal_hierarchy_transition_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
    minimum_training_recall_bps: int = 9_500,
) -> TemporalHierarchyTransitionModel:
    cutoff = _utc(fitted_at)
    if not 0 <= minimum_training_recall_bps <= 10_000:
        raise ValueError("minimum_training_recall_bps out of range")
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future training evidence beyond fitted_at")

    opposed = tuple(
        item
        for item in episodes
        if baseline_local_opposition(item.trajectory.snapshots[-1])
    )
    terminal = tuple(item for item in opposed if item.terminal_failure)
    recovery = tuple(item for item in opposed if not item.terminal_failure)
    if len(opposed) < 100 or len(terminal) < 20 or len(recovery) < 20:
        raise ValueError("insufficient terminal/recovery hierarchy trajectories")

    names, first = _trajectory_features(opposed[0].trajectory)
    rows = [first]
    for item in opposed[1:]:
        row_names, row = _trajectory_features(item.trajectory)
        if row_names != names:
            raise ValueError("trajectory feature schema drift")
        rows.append(row)

    terminal_rows = tuple(
        row for row, item in zip(rows, opposed, strict=True) if item.terminal_failure
    )
    recovery_rows = tuple(
        row for row, item in zip(rows, opposed, strict=True) if not item.terminal_failure
    )
    terminal_means, terminal_scales = _means_scales(terminal_rows)
    recovery_means, recovery_scales = _means_scales(recovery_rows)
    prior = len(terminal) / len(opposed)

    q_t_mean = _quantize(terminal_means)
    q_t_scale = tuple(max(1, value) for value in _quantize(terminal_scales))
    q_r_mean = _quantize(recovery_means)
    q_r_scale = tuple(max(1, value) for value in _quantize(recovery_scales))
    q_prior = max(1, min(999_999, int(round(prior * 1_000_000))))

    prototype = TemporalHierarchyTransitionModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        feature_names=names,
        terminal_means_micros=q_t_mean,
        terminal_scales_micros=q_t_scale,
        recovery_means_micros=q_r_mean,
        recovery_scales_micros=q_r_scale,
        terminal_prior_micros=q_prior,
        declaration_threshold_micros=0,
        minimum_training_recall_bps=minimum_training_recall_bps,
        threshold_calibration_recall_bps=max(minimum_training_recall_bps, 9_900),
        fit_opposition_count=len(opposed),
        fit_terminal_count=len(terminal),
    )
    terminal_scores = sorted(
        _score(prototype, item.trajectory)
        for item in terminal
    )
    calibration_recall = prototype.threshold_calibration_recall_bps
    allowed_misses = len(terminal_scores) * (10_000 - calibration_recall) // 10_000
    rank = min(len(terminal_scores) - 1, allowed_misses)
    threshold = terminal_scores[rank]

    return TemporalHierarchyTransitionModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        feature_names=names,
        terminal_means_micros=q_t_mean,
        terminal_scales_micros=q_t_scale,
        recovery_means_micros=q_r_mean,
        recovery_scales_micros=q_r_scale,
        terminal_prior_micros=q_prior,
        declaration_threshold_micros=threshold,
        minimum_training_recall_bps=minimum_training_recall_bps,
        threshold_calibration_recall_bps=calibration_recall,
        fit_opposition_count=len(opposed),
        fit_terminal_count=len(terminal),
    )


def assess_temporal_hierarchy_transition(
    *,
    model: TemporalHierarchyTransitionModel,
    trajectory: TemporalHierarchyTrajectory,
) -> TemporalHierarchyTransitionAssessment:
    current = trajectory.snapshots[-1]
    opposition = baseline_local_opposition(current)
    probability = _score(model, trajectory) if opposition else 0
    declared = opposition and probability >= model.declaration_threshold_micros
    return TemporalHierarchyTransitionAssessment(
        episode_id=trajectory.episode_id,
        as_of=current.as_of,
        baseline_local_opposition=opposition,
        terminal_probability_micros=probability,
        structural_failure_declared=declared,
        recoverable_pullback=opposition and not declared,
    )


def evaluate_temporal_hierarchy_transition(
    *,
    model: TemporalHierarchyTransitionModel,
    partition: str,
    episodes: tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
) -> TemporalHierarchyTransitionEvaluation:
    opposed = tuple(
        item
        for item in episodes
        if baseline_local_opposition(item.trajectory.snapshots[-1])
    )
    baseline_terminals = sum(item.terminal_failure for item in opposed)
    baseline_false = len(opposed) - baseline_terminals

    hierarchy_declarations = 0
    hierarchy_terminals = 0
    hierarchy_false = 0
    missed = 0
    for item in opposed:
        assessment = assess_temporal_hierarchy_transition(
            model=model,
            trajectory=item.trajectory,
        )
        if assessment.structural_failure_declared:
            hierarchy_declarations += 1
            if item.terminal_failure:
                hierarchy_terminals += 1
            else:
                hierarchy_false += 1
        elif item.terminal_failure:
            missed += 1

    false_reduction = (
        0
        if baseline_false <= 0
        else int(round((baseline_false - hierarchy_false) / baseline_false * 10_000))
    )
    preservation = (
        10_000
        if baseline_terminals <= 0
        else int(round(hierarchy_terminals / baseline_terminals * 10_000))
    )
    return TemporalHierarchyTransitionEvaluation(
        partition=partition,
        sample_count=len(episodes),
        baseline_declaration_count=len(opposed),
        baseline_terminal_count=baseline_terminals,
        baseline_false_declaration_count=baseline_false,
        hierarchy_declaration_count=hierarchy_declarations,
        hierarchy_terminal_count=hierarchy_terminals,
        hierarchy_false_declaration_count=hierarchy_false,
        hierarchy_missed_terminal_count=missed,
        false_declaration_reduction_bps=max(0, min(10_000, false_reduction)),
        terminal_detection_preservation_bps=max(0, min(10_000, preservation)),
    )
