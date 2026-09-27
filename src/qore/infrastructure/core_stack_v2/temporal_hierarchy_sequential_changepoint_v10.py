"""WP-05 V10 causal sequential structural-failure detection.

V10 stops forcing a source-time binary answer. It models structural failure as an
online early-warning problem over causal checkpoints. Historical 30m Target-V2
labels are used only for offline R8 fitting/calibration. Runtime evidence at
each checkpoint contains no bar after that checkpoint and carries no trading
authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite, log
from statistics import fmean, median
from typing import Protocol

from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_v7 import (
    RECOVERY_FEATURE_NAMES,
    TERMINAL_FEATURE_NAMES,
    CompetingSurvivalSourceState,
)

V10_CHECKPOINTS_MINUTES = (0, 3, 5, 10, 15)
V10_DISCOVERY_FRACTION_BPS = 7_000
V10_CALIBRATION_TERMINAL_PRESERVATION_BPS = 9_800
V10_FEATURE_NAMES = (
    "FIXED_FRONTIER_DISTANCE",
    "WORST_BREACH_DEPTH",
    "ADVERSE_DISTANCE_INTEGRAL",
    "CONSECUTIVE_BREACH_CLOSES",
    "BREACH_CLOSE_FRACTION",
    "BREACH_RECLAIM_TRANSITIONS",
    "RECLAIM_DISTANCE",
    "ADVERSE_VELOCITY_3M",
    "FAVORABLE_VELOCITY_3M",
    "RANGE_EXPANSION",
    "PEER_ADVERSE_MEAN",
    "PEER_ADVERSE_BREADTH",
    "PEER_CONTRADICTION",
    "SOURCE_HIERARCHY_DEPTH",
    "SOURCE_HIGHER_FRAGILITY_MINUS_RESILIENCE",
    "SOURCE_HIGHER_RESILIENCE_MINUS_FRAGILITY",
)


class MarketBarLike(Protocol):
    opened: float
    high: float
    low: float
    close: float


class SequentialCognitiveState(StrEnum):
    TERMINAL_SUPPORTED = "TERMINAL_SUPPORTED"
    RECOVERY_SUPPORTED = "RECOVERY_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _source_maps(
    source: CompetingSurvivalSourceState,
) -> tuple[dict[str, float], dict[str, float]]:
    return (
        dict(zip(TERMINAL_FEATURE_NAMES, source.terminal_features, strict=True)),
        dict(zip(RECOVERY_FEATURE_NAMES, source.recovery_features, strict=True)),
    )


def _safe_range(rows: Sequence[MarketBarLike]) -> float:
    if not rows:
        raise ValueError("range requires bars")
    return max(1e-9, fmean(max(0.0, row.high - row.low) for row in rows))


def _fixed_distance(
    *,
    bar: MarketBarLike,
    frontier: float,
    scale: float,
    anchor_direction: int,
) -> float:
    if anchor_direction > 0:
        return (bar.close - frontier) / scale
    return (frontier - bar.close) / scale


def _wick_breach_depth(
    *,
    bar: MarketBarLike,
    frontier: float,
    scale: float,
    anchor_direction: int,
) -> float:
    if anchor_direction > 0:
        return max(0.0, (frontier - bar.low) / scale)
    return max(0.0, (bar.high - frontier) / scale)


def _adverse_return(
    *,
    source_close: float,
    current_close: float,
    anchor_direction: int,
) -> float:
    if source_close == 0.0:
        return 0.0
    bps = (current_close / source_close - 1.0) * 10_000.0
    return max(-10.0, min(10.0, -anchor_direction * bps / 100.0))


@dataclass(frozen=True, slots=True)
class SequentialCheckpointEvidence:
    episode_id: str
    checkpoint_minutes: int
    as_of: datetime
    anchor_direction: int
    features: tuple[float, ...]
    breach_observed: bool
    safe_reclaim_streak: int
    evidence_complete: bool = True
    future_market_used: bool = False
    target_used: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    setup_identity_used: bool = False
    pnl_used: bool = False

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("V10 episode_id must be non-empty")
        if self.checkpoint_minutes not in V10_CHECKPOINTS_MINUTES:
            raise ValueError("V10 checkpoint outside frozen schedule")
        _utc(self.as_of)
        if self.anchor_direction not in (-1, 1):
            raise ValueError("V10 requires identifiable anchor")
        if len(self.features) != len(V10_FEATURE_NAMES):
            raise ValueError("V10 feature width mismatch")
        if any(not isfinite(value) for value in self.features):
            raise ValueError("V10 features must be finite")
        if self.safe_reclaim_streak < 0:
            raise ValueError("V10 reclaim streak cannot be negative")
        if (
            self.future_market_used
            or self.target_used
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.setup_identity_used
            or self.pnl_used
        ):
            raise ValueError("V10 checkpoint carries forbidden evidence")


@dataclass(frozen=True, slots=True)
class SequentialChangePointTrainingEpisode:
    checkpoints: tuple[SequentialCheckpointEvidence, ...]
    observed_at: datetime
    terminal_failure: bool

    def __post_init__(self) -> None:
        if tuple(item.checkpoint_minutes for item in self.checkpoints) != (
            V10_CHECKPOINTS_MINUTES
        ):
            raise ValueError("V10 training episode requires frozen checkpoints")
        times = tuple(_utc(item.as_of) for item in self.checkpoints)
        if times != tuple(sorted(times)):
            raise ValueError("V10 checkpoints must be time ordered")
        if _utc(self.observed_at) <= times[-1]:
            raise ValueError("V10 matured target must occur after 15m checkpoint")
        ids = {item.episode_id for item in self.checkpoints}
        anchors = {item.anchor_direction for item in self.checkpoints}
        if len(ids) != 1 or len(anchors) != 1:
            raise ValueError("V10 checkpoint identity drift")


@dataclass(frozen=True, slots=True)
class CheckpointDensity:
    checkpoint_minutes: int
    terminal_centers_micros: tuple[int, ...]
    terminal_scales_micros: tuple[int, ...]
    nonterminal_centers_micros: tuple[int, ...]
    nonterminal_scales_micros: tuple[int, ...]
    terminal_count: int
    nonterminal_count: int

    def __post_init__(self) -> None:
        if self.checkpoint_minutes not in V10_CHECKPOINTS_MINUTES:
            raise ValueError("V10 density checkpoint outside frozen schedule")
        width = len(V10_FEATURE_NAMES)
        vectors = (
            self.terminal_centers_micros,
            self.terminal_scales_micros,
            self.nonterminal_centers_micros,
            self.nonterminal_scales_micros,
        )
        if any(len(values) != width for values in vectors):
            raise ValueError("V10 density width mismatch")
        if any(value <= 0 for value in self.terminal_scales_micros):
            raise ValueError("V10 terminal scales must be positive")
        if any(value <= 0 for value in self.nonterminal_scales_micros):
            raise ValueError("V10 nonterminal scales must be positive")
        if self.terminal_count < 10 or self.nonterminal_count < 10:
            raise ValueError("V10 density requires both classes")


@dataclass(frozen=True, slots=True)
class SequentialChangePointModel:
    fitted_at: datetime
    fit_partition: str
    feature_names: tuple[str, ...]
    checkpoints_minutes: tuple[int, ...]
    densities: tuple[CheckpointDensity, ...]
    source_only_threshold_micros: int
    sequential_threshold_micros: int
    calibration_source_terminal_preservation_bps: int
    calibration_source_false_reduction_bps: int
    calibration_sequential_terminal_preservation_bps: int
    calibration_sequential_false_reduction_bps: int
    calibration_gate_pass: bool
    fit_count: int
    fit_terminal_count: int
    fit_nonterminal_count: int
    calibration_count: int
    calibration_terminal_count: int
    calibration_nonterminal_count: int
    purged_discovery_count: int
    discovery_observed_max: datetime
    calibration_source_min: datetime
    target_used_for_training_only: bool = True
    runtime_future_market_used: bool = False
    outcome_used_at_runtime: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    setup_identity_used: bool = False
    pnl_used_at_runtime: bool = False
    methodology_authority: bool = False
    knowledge_promotion_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _utc(self.fitted_at)
        if self.fit_partition != "r8":
            raise ValueError("V10 fit partition must be r8")
        if self.feature_names != V10_FEATURE_NAMES:
            raise ValueError("V10 feature schema drift")
        if self.checkpoints_minutes != V10_CHECKPOINTS_MINUTES:
            raise ValueError("V10 checkpoint schedule drift")
        if tuple(item.checkpoint_minutes for item in self.densities) != (
            V10_CHECKPOINTS_MINUTES
        ):
            raise ValueError("V10 density checkpoint drift")
        if self.fit_terminal_count < 10 or self.fit_nonterminal_count < 10:
            raise ValueError("V10 fit requires both target classes")
        if self.calibration_terminal_count < 5:
            raise ValueError("V10 calibration requires terminal evidence")
        if self.purged_discovery_count < 0:
            raise ValueError("V10 purge count cannot be negative")
        if _utc(self.discovery_observed_max) >= _utc(self.calibration_source_min):
            raise ValueError("V10 chronological purge boundary is not strict")
        for value in (
            self.calibration_source_terminal_preservation_bps,
            self.calibration_source_false_reduction_bps,
            self.calibration_sequential_terminal_preservation_bps,
            self.calibration_sequential_false_reduction_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("V10 calibration metric out of range")
        if self.calibration_gate_pass and (
            self.calibration_sequential_terminal_preservation_bps
            < V10_CALIBRATION_TERMINAL_PRESERVATION_BPS
        ):
            raise ValueError("V10 calibration gate inconsistent")
        if (
            self.runtime_future_market_used
            or self.outcome_used_at_runtime
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.setup_identity_used
            or self.pnl_used_at_runtime
            or self.methodology_authority
            or self.knowledge_promotion_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("V10 model carries forbidden authority or evidence")


@dataclass(frozen=True, slots=True)
class SequentialCheckpointAssessment:
    checkpoint_minutes: int
    llr_micros: int
    state: SequentialCognitiveState
    structural_failure_declared: bool
    target_used: bool = False
    future_market_used: bool = False


@dataclass(frozen=True, slots=True)
class SequentialEpisodeAssessment:
    episode_id: str
    checkpoints: tuple[SequentialCheckpointAssessment, ...]
    first_terminal_detection_minute: int | None
    source_only_declared: bool


@dataclass(frozen=True, slots=True)
class SequentialChangePointEvaluation:
    partition: str
    sample_count: int
    baseline_terminal_count: int
    baseline_false_declaration_count: int
    source_only_false_declaration_count: int
    source_only_missed_terminal_count: int
    source_only_false_declaration_reduction_bps: int
    source_only_terminal_detection_preservation_bps: int
    sequential_false_declaration_count: int
    sequential_missed_terminal_count: int
    sequential_false_declaration_reduction_bps: int
    sequential_terminal_detection_preservation_bps: int
    terminal_detection_latency_p50_minutes: int
    terminal_detection_latency_p95_minutes: int
    detections_at_0m: int
    detections_at_3m: int
    detections_at_5m: int
    detections_at_10m: int
    detections_at_15m: int
    recovery_supported_final_count: int
    unresolved_final_count: int


def build_sequential_checkpoint_evidence(
    *,
    source: CompetingSurvivalSourceState,
    checkpoint_minutes: int,
    as_of: datetime,
    nas_bars: Sequence[MarketBarLike],
    nas_source_index: int,
    sp500_bars: Sequence[MarketBarLike],
    sp500_source_index: int,
    us30_bars: Sequence[MarketBarLike],
    us30_source_index: int,
) -> SequentialCheckpointEvidence:
    """Build one checkpoint using no market bar after that checkpoint."""

    if checkpoint_minutes not in V10_CHECKPOINTS_MINUTES:
        raise ValueError("V10 checkpoint outside frozen schedule")
    if not source.evidence_complete:
        return SequentialCheckpointEvidence(
            episode_id=source.episode_id,
            checkpoint_minutes=checkpoint_minutes,
            as_of=as_of,
            anchor_direction=source.anchor_direction,
            features=(0.0,) * len(V10_FEATURE_NAMES),
            breach_observed=False,
            safe_reclaim_streak=0,
            evidence_complete=False,
        )
    if nas_source_index < 19:
        raise ValueError("V10 source requires 20-bar structural frontier")
    for bars, index in (
        (nas_bars, nas_source_index),
        (sp500_bars, sp500_source_index),
        (us30_bars, us30_source_index),
    ):
        if index < 0 or index + checkpoint_minutes >= len(bars):
            raise ValueError("V10 checkpoint market evidence incomplete")

    prior = nas_bars[nas_source_index - 19 : nas_source_index + 1]
    if len(prior) != 20:
        raise ValueError("V10 source frontier incomplete")
    anchor = source.anchor_direction
    frontier = (
        min(item.low for item in prior)
        if anchor > 0
        else max(item.high for item in prior)
    )
    source_scale = _safe_range(prior)
    source_bar = nas_bars[nas_source_index]
    post = tuple(
        nas_bars[nas_source_index + 1 : nas_source_index + checkpoint_minutes + 1]
    )
    current = source_bar if not post else post[-1]
    distances = tuple(
        _fixed_distance(
            bar=item,
            frontier=frontier,
            scale=source_scale,
            anchor_direction=anchor,
        )
        for item in post
    )
    current_distance = _fixed_distance(
        bar=current,
        frontier=frontier,
        scale=source_scale,
        anchor_direction=anchor,
    )
    worst_breach = max(
        (
            _wick_breach_depth(
                bar=item,
                frontier=frontier,
                scale=source_scale,
                anchor_direction=anchor,
            )
            for item in post
        ),
        default=0.0,
    )
    breach_close_flags = tuple(value < 0.0 for value in distances)
    adverse_integral = (
        0.0
        if not distances
        else fmean(max(0.0, -value) for value in distances)
    )
    consecutive_breach = 0
    for flag in reversed(breach_close_flags):
        if not flag:
            break
        consecutive_breach += 1
    breach_fraction = (
        0.0
        if not breach_close_flags
        else sum(breach_close_flags) / len(breach_close_flags)
    )
    transitions = sum(
        left != right
        for left, right in zip(
            breach_close_flags,
            breach_close_flags[1:],
            strict=False,
        )
    )
    transition_fraction = transitions / max(1, len(breach_close_flags) - 1)
    breach_observed = worst_breach > 0.0
    reclaim_distance = (
        0.0
        if not distances or not breach_observed
        else max(0.0, current_distance - min(distances))
    )

    safe_reclaim_streak = 0
    if breach_observed:
        for value in reversed(distances):
            if value <= 0.0:
                break
            safe_reclaim_streak += 1

    all_path = (source_bar,) + post
    velocity_horizon = min(3, max(0, len(all_path) - 1))
    adverse_velocity = 0.0
    favorable_velocity = 0.0
    if velocity_horizon:
        past = all_path[-1 - velocity_horizon]
        past_distance = _fixed_distance(
            bar=past,
            frontier=frontier,
            scale=source_scale,
            anchor_direction=anchor,
        )
        delta = (current_distance - past_distance) / velocity_horizon
        adverse_velocity = max(0.0, -delta)
        favorable_velocity = max(0.0, delta)

    range_expansion = (
        1.0 if not post else _safe_range(post) / source_scale
    )

    peer_adverse: list[float] = []
    for bars, index in (
        (sp500_bars, sp500_source_index),
        (us30_bars, us30_source_index),
    ):
        peer_adverse.append(
            _adverse_return(
                source_close=bars[index].close,
                current_close=bars[index + checkpoint_minutes].close,
                anchor_direction=anchor,
            )
        )
    peer_adverse_mean = fmean(peer_adverse)
    peer_breadth = fmean(float(value > 0.0) for value in peer_adverse)
    peer_contradiction = fmean(max(0.0, -value) for value in peer_adverse)

    terminal_map, recovery_map = _source_maps(source)
    features = (
        current_distance,
        worst_breach,
        adverse_integral,
        float(consecutive_breach),
        breach_fraction,
        transition_fraction,
        reclaim_distance,
        adverse_velocity,
        favorable_velocity,
        range_expansion,
        peer_adverse_mean,
        peer_breadth,
        peer_contradiction,
        terminal_map["HIERARCHY_DEPTH"],
        terminal_map["HIGHER_FRAGILITY_MINUS_RESILIENCE"],
        recovery_map["HIGHER_RESILIENCE_MINUS_FRAGILITY"],
    )
    return SequentialCheckpointEvidence(
        episode_id=source.episode_id,
        checkpoint_minutes=checkpoint_minutes,
        as_of=as_of,
        anchor_direction=anchor,
        features=tuple(float(value) for value in features),
        breach_observed=breach_observed,
        safe_reclaim_streak=safe_reclaim_streak,
    )


def _robust_center_scale(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not rows:
        raise ValueError("V10 robust density requires rows")
    width = len(rows[0])
    centers = tuple(median(row[index] for row in rows) for index in range(width))
    scales = []
    for index, center in enumerate(centers):
        mad = median(abs(row[index] - center) for row in rows)
        scales.append(max(1e-4, mad * 1.4826))
    return centers, tuple(scales)


def _micros(values: tuple[float, ...], *, positive: bool = False) -> tuple[int, ...]:
    if positive:
        return tuple(max(1, int(round(value * 1_000_000))) for value in values)
    return tuple(int(round(value * 1_000_000)) for value in values)


def _fit_density(
    *,
    checkpoint_minutes: int,
    episodes: tuple[SequentialChangePointTrainingEpisode, ...],
) -> CheckpointDensity:
    index = V10_CHECKPOINTS_MINUTES.index(checkpoint_minutes)
    terminal = tuple(
        item.checkpoints[index].features
        for item in episodes
        if item.terminal_failure and item.checkpoints[index].evidence_complete
    )
    nonterminal = tuple(
        item.checkpoints[index].features
        for item in episodes
        if not item.terminal_failure and item.checkpoints[index].evidence_complete
    )
    if len(terminal) < 10 or len(nonterminal) < 10:
        raise ValueError("V10 discovery lacks target-family evidence")
    t_center, t_scale = _robust_center_scale(terminal)
    n_center, n_scale = _robust_center_scale(nonterminal)
    return CheckpointDensity(
        checkpoint_minutes=checkpoint_minutes,
        terminal_centers_micros=_micros(t_center),
        terminal_scales_micros=_micros(t_scale, positive=True),
        nonterminal_centers_micros=_micros(n_center),
        nonterminal_scales_micros=_micros(n_scale, positive=True),
        terminal_count=len(terminal),
        nonterminal_count=len(nonterminal),
    )


def _llr_micros(
    *,
    evidence: SequentialCheckpointEvidence,
    density: CheckpointDensity,
) -> int:
    if not evidence.evidence_complete:
        return -10**12
    total = 0.0
    for value, tc, ts, nc, ns in zip(
        evidence.features,
        density.terminal_centers_micros,
        density.terminal_scales_micros,
        density.nonterminal_centers_micros,
        density.nonterminal_scales_micros,
        strict=True,
    ):
        t_center = tc / 1_000_000.0
        t_scale = ts / 1_000_000.0
        n_center = nc / 1_000_000.0
        n_scale = ns / 1_000_000.0
        terminal_log = -log(t_scale) - 0.5 * ((value - t_center) / t_scale) ** 2
        nonterminal_log = -log(n_scale) - 0.5 * ((value - n_center) / n_scale) ** 2
        total += max(-20.0, min(20.0, terminal_log - nonterminal_log))
    return int(round(total / len(V10_FEATURE_NAMES) * 1_000_000))


def _episode_scores(
    *,
    episode: SequentialChangePointTrainingEpisode,
    densities: tuple[CheckpointDensity, ...],
) -> tuple[int, tuple[int, ...]]:
    scores = tuple(
        _llr_micros(evidence=evidence, density=density)
        for evidence, density in zip(episode.checkpoints, densities, strict=True)
    )
    return scores[0], scores


def _highest_threshold_for_preservation(
    *,
    terminal_scores: tuple[int, ...],
    minimum_preservation_bps: int,
) -> int:
    if not terminal_scores:
        raise ValueError("V10 calibration requires terminal scores")
    candidates = sorted(set(terminal_scores), reverse=True)
    count = len(terminal_scores)
    for threshold in candidates:
        preserved = sum(score >= threshold for score in terminal_scores)
        preservation = preserved * 10_000 // count
        if preservation >= minimum_preservation_bps:
            return threshold
    return min(terminal_scores)


def _threshold_metrics(
    *,
    scores: tuple[tuple[int, bool], ...],
    threshold: int,
) -> tuple[int, int]:
    terminal_count = sum(label for _, label in scores)
    nonterminal_count = len(scores) - terminal_count
    terminal_detected = sum(
        label and score >= threshold for score, label in scores
    )
    nonterminal_declared = sum(
        (not label) and score >= threshold for score, label in scores
    )
    preservation = (
        0
        if terminal_count == 0
        else terminal_detected * 10_000 // terminal_count
    )
    reduction = (
        0
        if nonterminal_count == 0
        else (nonterminal_count - nonterminal_declared) * 10_000
        // nonterminal_count
    )
    return preservation, reduction


def fit_sequential_changepoint_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[SequentialChangePointTrainingEpisode, ...],
    discovery_fraction_bps: int = V10_DISCOVERY_FRACTION_BPS,
    calibration_terminal_preservation_bps: int = (
        V10_CALIBRATION_TERMINAL_PRESERVATION_BPS
    ),
) -> SequentialChangePointModel:
    cutoff = _utc(fitted_at)
    if fit_partition != "r8":
        raise ValueError("V10 fit partition is frozen to r8")
    if discovery_fraction_bps != V10_DISCOVERY_FRACTION_BPS:
        raise ValueError("V10 discovery split is frozen at 7000 bps")
    if (
        calibration_terminal_preservation_bps
        != V10_CALIBRATION_TERMINAL_PRESERVATION_BPS
    ):
        raise ValueError("V10 calibration preservation is frozen at 9800 bps")
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future V10 training evidence beyond fitted_at")

    ordered = tuple(sorted(episodes, key=lambda item: item.checkpoints[0].as_of))
    split = len(ordered) * discovery_fraction_bps // 10_000
    if split < 100 or len(ordered) - split < 50:
        raise ValueError("insufficient chronological V10 evidence")
    raw_discovery = ordered[:split]
    calibration = ordered[split:]
    calibration_source_min = _utc(calibration[0].checkpoints[0].as_of)
    discovery = tuple(
        item
        for item in raw_discovery
        if all(point.evidence_complete for point in item.checkpoints)
        and _utc(item.observed_at) < calibration_source_min
    )
    purged = len(raw_discovery) - len(discovery)
    if len(discovery) < 100:
        raise ValueError("V10 purge leaves insufficient discovery evidence")
    discovery_observed_max = max(_utc(item.observed_at) for item in discovery)
    if discovery_observed_max >= calibration_source_min:
        raise AssertionError("V10 chronological purge boundary is not strict")

    densities = tuple(
        _fit_density(checkpoint_minutes=minute, episodes=discovery)
        for minute in V10_CHECKPOINTS_MINUTES
    )

    source_rows: list[tuple[int, bool]] = []
    sequential_rows: list[tuple[int, bool]] = []
    source_terminal_scores: list[int] = []
    sequential_terminal_scores: list[int] = []
    for item in calibration:
        source_score, checkpoint_scores = _episode_scores(
            episode=item,
            densities=densities,
        )
        sequential_score = max(checkpoint_scores)
        source_rows.append((source_score, item.terminal_failure))
        sequential_rows.append((sequential_score, item.terminal_failure))
        if item.terminal_failure:
            source_terminal_scores.append(source_score)
            sequential_terminal_scores.append(sequential_score)

    source_threshold = _highest_threshold_for_preservation(
        terminal_scores=tuple(source_terminal_scores),
        minimum_preservation_bps=calibration_terminal_preservation_bps,
    )
    sequential_threshold = _highest_threshold_for_preservation(
        terminal_scores=tuple(sequential_terminal_scores),
        minimum_preservation_bps=calibration_terminal_preservation_bps,
    )
    source_preservation, source_reduction = _threshold_metrics(
        scores=tuple(source_rows),
        threshold=source_threshold,
    )
    sequential_preservation, sequential_reduction = _threshold_metrics(
        scores=tuple(sequential_rows),
        threshold=sequential_threshold,
    )

    fit_terminal = sum(item.terminal_failure for item in discovery)
    calibration_terminal = sum(item.terminal_failure for item in calibration)
    return SequentialChangePointModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        feature_names=V10_FEATURE_NAMES,
        checkpoints_minutes=V10_CHECKPOINTS_MINUTES,
        densities=densities,
        source_only_threshold_micros=source_threshold,
        sequential_threshold_micros=sequential_threshold,
        calibration_source_terminal_preservation_bps=source_preservation,
        calibration_source_false_reduction_bps=source_reduction,
        calibration_sequential_terminal_preservation_bps=sequential_preservation,
        calibration_sequential_false_reduction_bps=sequential_reduction,
        calibration_gate_pass=(
            sequential_preservation >= calibration_terminal_preservation_bps
        ),
        fit_count=len(discovery),
        fit_terminal_count=fit_terminal,
        fit_nonterminal_count=len(discovery) - fit_terminal,
        calibration_count=len(calibration),
        calibration_terminal_count=calibration_terminal,
        calibration_nonterminal_count=len(calibration) - calibration_terminal,
        purged_discovery_count=purged,
        discovery_observed_max=discovery_observed_max,
        calibration_source_min=calibration_source_min,
    )


def assess_sequential_episode(
    *,
    model: SequentialChangePointModel,
    episode: SequentialChangePointTrainingEpisode,
) -> SequentialEpisodeAssessment:
    assessments: list[SequentialCheckpointAssessment] = []
    first_terminal: int | None = None
    source_only_declared = False

    for index, (evidence, density) in enumerate(
        zip(episode.checkpoints, model.densities, strict=True)
    ):
        score = _llr_micros(evidence=evidence, density=density)
        if index == 0:
            source_only_declared = score >= model.source_only_threshold_micros

        if first_terminal is not None:
            state = SequentialCognitiveState.TERMINAL_SUPPORTED
            declared = True
        elif score >= model.sequential_threshold_micros:
            first_terminal = evidence.checkpoint_minutes
            state = SequentialCognitiveState.TERMINAL_SUPPORTED
            declared = True
        elif (
            evidence.breach_observed
            and evidence.safe_reclaim_streak >= 3
            and evidence.features[0] > 0.0
        ):
            state = SequentialCognitiveState.RECOVERY_SUPPORTED
            declared = False
        else:
            state = SequentialCognitiveState.UNRESOLVED
            declared = False

        assessments.append(
            SequentialCheckpointAssessment(
                checkpoint_minutes=evidence.checkpoint_minutes,
                llr_micros=score,
                state=state,
                structural_failure_declared=declared,
            )
        )

    return SequentialEpisodeAssessment(
        episode_id=episode.checkpoints[0].episode_id,
        checkpoints=tuple(assessments),
        first_terminal_detection_minute=first_terminal,
        source_only_declared=source_only_declared,
    )


def _latency_quantile(values: tuple[int, ...], bps: int) -> int:
    if not values:
        return -1
    ordered = sorted(values)
    index = (len(ordered) - 1) * bps // 10_000
    return ordered[index]


def evaluate_sequential_changepoint(
    *,
    model: SequentialChangePointModel,
    partition: str,
    episodes: tuple[SequentialChangePointTrainingEpisode, ...],
) -> SequentialChangePointEvaluation:
    assessed = tuple(
        (item, assess_sequential_episode(model=model, episode=item))
        for item in episodes
    )
    terminal_count = sum(item.terminal_failure for item, _ in assessed)
    false_count = len(assessed) - terminal_count

    source_false = sum(
        (not item.terminal_failure) and result.source_only_declared
        for item, result in assessed
    )
    source_missed = sum(
        item.terminal_failure and not result.source_only_declared
        for item, result in assessed
    )
    sequential_false = sum(
        (not item.terminal_failure)
        and result.first_terminal_detection_minute is not None
        for item, result in assessed
    )
    sequential_missed = sum(
        item.terminal_failure
        and result.first_terminal_detection_minute is None
        for item, result in assessed
    )
    terminal_latencies = tuple(
        int(result.first_terminal_detection_minute)
        for item, result in assessed
        if item.terminal_failure and result.first_terminal_detection_minute is not None
    )
    detections = {
        minute: sum(
            item.terminal_failure
            and result.first_terminal_detection_minute == minute
            for item, result in assessed
        )
        for minute in V10_CHECKPOINTS_MINUTES
    }
    final_states = tuple(result.checkpoints[-1].state for _, result in assessed)

    return SequentialChangePointEvaluation(
        partition=partition,
        sample_count=len(assessed),
        baseline_terminal_count=terminal_count,
        baseline_false_declaration_count=false_count,
        source_only_false_declaration_count=source_false,
        source_only_missed_terminal_count=source_missed,
        source_only_false_declaration_reduction_bps=(
            0 if false_count == 0 else (false_count - source_false) * 10_000 // false_count
        ),
        source_only_terminal_detection_preservation_bps=(
            0
            if terminal_count == 0
            else (terminal_count - source_missed) * 10_000 // terminal_count
        ),
        sequential_false_declaration_count=sequential_false,
        sequential_missed_terminal_count=sequential_missed,
        sequential_false_declaration_reduction_bps=(
            0
            if false_count == 0
            else (false_count - sequential_false) * 10_000 // false_count
        ),
        sequential_terminal_detection_preservation_bps=(
            0
            if terminal_count == 0
            else (terminal_count - sequential_missed) * 10_000 // terminal_count
        ),
        terminal_detection_latency_p50_minutes=_latency_quantile(
            terminal_latencies,
            5_000,
        ),
        terminal_detection_latency_p95_minutes=_latency_quantile(
            terminal_latencies,
            9_500,
        ),
        detections_at_0m=detections[0],
        detections_at_3m=detections[3],
        detections_at_5m=detections[5],
        detections_at_10m=detections[10],
        detections_at_15m=detections[15],
        recovery_supported_final_count=sum(
            state is SequentialCognitiveState.RECOVERY_SUPPORTED
            for state in final_states
        ),
        unresolved_final_count=sum(
            state is SequentialCognitiveState.UNRESOLVED for state in final_states
        ),
    )


def sequential_changepoint_model_fingerprint(
    model: SequentialChangePointModel,
) -> str:
    payload = asdict(model)
    payload["fitted_at"] = _utc(model.fitted_at).isoformat()
    payload["discovery_observed_max"] = _utc(
        model.discovery_observed_max
    ).isoformat()
    payload["calibration_source_min"] = _utc(
        model.calibration_source_min
    ).isoformat()
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sequential_changepoint_representation_fingerprint() -> str:
    payload = {
        "identity": "QORE_SHARED_WP05_CAUSAL_SEQUENTIAL_CHANGEPOINT_V10_001",
        "target": "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2",
        "checkpoints_minutes": list(V10_CHECKPOINTS_MINUTES),
        "feature_names": list(V10_FEATURE_NAMES),
        "frontier": "FIXED_SOURCE_TARGET_V2_PRIOR20",
        "max_decision_latency_minutes": 15,
        "unresolved_is_abstention": True,
        "terminal_detection_absorbing": True,
        "runtime_future_market_used": False,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
