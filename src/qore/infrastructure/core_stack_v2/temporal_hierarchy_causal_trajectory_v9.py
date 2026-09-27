"""WP-05 V9 causal trajectory discrimination with censor-aware abstention.

V9 replaces static source geometry with a 30-minute pre-source causal trajectory.
It fits eventness over terminal/recovery vs censored paths and a separate
recovery contrast over verified-recovery vs terminal event families only.
Runtime cognition is source-time only and has no trading authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import exp, isfinite, sqrt
from statistics import fmean
from typing import Protocol

from qore.infrastructure.core_stack_v2.temporal_hierarchy_event_manifold_v8 import (
    EventManifoldLabel,
)

V9_DISCOVERY_FRACTION_BPS = 7_000
V9_CALIBRATION_TERMINAL_PRESERVATION_BPS = 9_800
V9_RIDGE = 4.0
V9_TRAINING_STEPS = 500
V9_LEARNING_RATE = 0.05
V9_EVENTNESS_THRESHOLDS_MICROS = (
    500_000,
    550_000,
    600_000,
    650_000,
    700_000,
    750_000,
    800_000,
)
V9_RECOVERY_THRESHOLDS_MICROS = (
    550_000,
    600_000,
    650_000,
    700_000,
    750_000,
    800_000,
    850_000,
    900_000,
)

_BLOCK_FEATURE_BASE = (
    "NAS_MEAN_DISTANCE",
    "NAS_MIN_DISTANCE",
    "NAS_TOUCH_FRACTION",
    "NAS_BREACH_CLOSE_FRACTION",
    "NAS_ANCHOR_SIGNED_RETURN",
    "NAS_MEAN_RANGE",
    "SP500_ADVERSE_RETURN",
    "US30_ADVERSE_RETURN",
)
_BLOCK_FEATURE_NAMES = tuple(
    f"B{block}_{name}"
    for block in range(1, 7)
    for name in _BLOCK_FEATURE_BASE
)
_TRANSITION_FEATURE_NAMES = (
    "DISTANCE_VELOCITY_LAST",
    "DISTANCE_ACCELERATION_LAST",
    "TOUCH_RATE_VELOCITY",
    "BREACH_RATE_VELOCITY",
    "NAS_ADVERSE_RETURN_ACCELERATION",
    "SP500_ADVERSE_RETURN_ACCELERATION",
    "US30_ADVERSE_RETURN_ACCELERATION",
    "PEER_BREADTH_LAST",
    "PEER_BREADTH_CHANGE",
    "TOUCH_STATE_TRANSITIONS",
    "BREACH_STATE_TRANSITIONS",
    "LAST_BLOCK_RECLAIM_FRACTION",
)
V9_FEATURE_NAMES = _BLOCK_FEATURE_NAMES + _TRANSITION_FEATURE_NAMES


class MarketBarLike(Protocol):
    opened: float
    high: float
    low: float
    close: float


class CausalTrajectoryState(StrEnum):
    RECOVERY_SUPPORTED = "RECOVERY_SUPPORTED"
    TERMINAL_SUPPORTED = "TERMINAL_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _mean_range(bars: Sequence[MarketBarLike]) -> float:
    return max(1e-9, fmean(max(0.0, bar.high - bar.low) for bar in bars))


def _signed_distance(
    *,
    close: float,
    frontier: float,
    scale: float,
    anchor_direction: int,
) -> float:
    return (
        (close - frontier) / scale
        if anchor_direction > 0
        else (frontier - close) / scale
    )


def _touch(bar: MarketBarLike, frontier: float, anchor_direction: int) -> bool:
    return (
        bar.low <= frontier
        if anchor_direction > 0
        else bar.high >= frontier
    )


def _breach_close(
    bar: MarketBarLike,
    frontier: float,
    anchor_direction: int,
) -> bool:
    return (
        bar.close < frontier
        if anchor_direction > 0
        else bar.close > frontier
    )


def _block_return(
    bars: Sequence[MarketBarLike],
    *,
    anchor_direction: int,
    adverse: bool,
) -> float:
    first = bars[0].close
    last = bars[-1].close
    if first == 0:
        return 0.0
    signed = anchor_direction * (last / first - 1.0) * 100.0
    value = -signed if adverse else signed
    return _clamp(value, -5.0, 5.0)


def _state_transitions(values: tuple[float, ...]) -> float:
    states = tuple(value > 0.0 for value in values)
    return float(
        sum(left != right for left, right in zip(states, states[1:], strict=False))
    )


@dataclass(frozen=True, slots=True)
class CausalTrajectorySourceState:
    episode_id: str
    as_of: datetime
    anchor_direction: int
    features: tuple[float, ...]
    evidence_complete: bool = True
    future_market_used: bool = False
    target_used: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    setup_identity_used: bool = False
    pnl_used: bool = False

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("V9 episode_id must be non-empty")
        _utc(self.as_of)
        if self.anchor_direction not in (-1, 1):
            raise ValueError("V9 source requires identifiable anchor")
        if len(self.features) != len(V9_FEATURE_NAMES):
            raise ValueError("V9 feature width mismatch")
        if any(not isfinite(value) for value in self.features):
            raise ValueError("V9 features must be finite")
        if (
            self.future_market_used
            or self.target_used
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.setup_identity_used
            or self.pnl_used
        ):
            raise ValueError("V9 source carries forbidden evidence")


def build_causal_trajectory_source_state(
    *,
    episode_id: str,
    as_of: datetime,
    anchor_direction: int,
    nas_bars: Sequence[MarketBarLike],
    nas_index: int,
    sp500_bars: Sequence[MarketBarLike],
    sp500_index: int,
    us30_bars: Sequence[MarketBarLike],
    us30_index: int,
) -> CausalTrajectorySourceState:
    """Build the frozen 60-feature pre-source trajectory."""

    if anchor_direction not in (-1, 1):
        raise ValueError("V9 trajectory requires identifiable anchor")
    for index in (nas_index, sp500_index, us30_index):
        if index < 29:
            raise ValueError("V9 trajectory requires 30 pre-source M1 bars")
    if nas_index < 19:
        raise ValueError("V9 source frontier requires 20 closed M1 bars")

    frontier_rows = nas_bars[nas_index - 19 : nas_index + 1]
    if len(frontier_rows) != 20:
        raise ValueError("V9 Target-V2 source frontier is incomplete")
    frontier = (
        min(bar.low for bar in frontier_rows)
        if anchor_direction > 0
        else max(bar.high for bar in frontier_rows)
    )
    scale = _mean_range(frontier_rows)

    nas_window = nas_bars[nas_index - 29 : nas_index + 1]
    sp_window = sp500_bars[sp500_index - 29 : sp500_index + 1]
    us_window = us30_bars[us30_index - 29 : us30_index + 1]
    if not (len(nas_window) == len(sp_window) == len(us_window) == 30):
        raise ValueError("V9 pre-source trajectory is incomplete")

    block_rows: list[tuple[float, ...]] = []
    mean_distances: list[float] = []
    touch_rates: list[float] = []
    breach_rates: list[float] = []
    nas_signed_returns: list[float] = []
    sp_adverse_returns: list[float] = []
    us_adverse_returns: list[float] = []

    for block in range(6):
        start = block * 5
        end = start + 5
        nas = nas_window[start:end]
        sp = sp_window[start:end]
        us = us_window[start:end]
        distances = tuple(
            _signed_distance(
                close=bar.close,
                frontier=frontier,
                scale=scale,
                anchor_direction=anchor_direction,
            )
            for bar in nas
        )
        touches = tuple(_touch(bar, frontier, anchor_direction) for bar in nas)
        breaches = tuple(
            _breach_close(bar, frontier, anchor_direction) for bar in nas
        )
        mean_distance = fmean(distances)
        touch_rate = sum(touches) / 5.0
        breach_rate = sum(breaches) / 5.0
        nas_signed = _block_return(
            nas,
            anchor_direction=anchor_direction,
            adverse=False,
        )
        sp_adverse = _block_return(
            sp,
            anchor_direction=anchor_direction,
            adverse=True,
        )
        us_adverse = _block_return(
            us,
            anchor_direction=anchor_direction,
            adverse=True,
        )
        block_rows.append(
            (
                mean_distance,
                min(distances),
                touch_rate,
                breach_rate,
                nas_signed,
                fmean((bar.high - bar.low) / scale for bar in nas),
                sp_adverse,
                us_adverse,
            )
        )
        mean_distances.append(mean_distance)
        touch_rates.append(touch_rate)
        breach_rates.append(breach_rate)
        nas_signed_returns.append(nas_signed)
        sp_adverse_returns.append(sp_adverse)
        us_adverse_returns.append(us_adverse)

    distance_velocity = mean_distances[-1] - mean_distances[-2]
    prior_velocity = mean_distances[-2] - mean_distances[-3]
    last_nas_adverse = -nas_signed_returns[-1]
    prior_nas_adverse = -nas_signed_returns[-2]
    peer_breadth_last = (
        int(sp_adverse_returns[-1] > 0.0) + int(us_adverse_returns[-1] > 0.0)
    ) / 2.0
    peer_breadth_prior = (
        int(sp_adverse_returns[-2] > 0.0) + int(us_adverse_returns[-2] > 0.0)
    ) / 2.0

    last_block = nas_window[-5:]
    touched_last = [
        bar for bar in last_block if _touch(bar, frontier, anchor_direction)
    ]
    reclaimed = sum(
        (
            bar.close > frontier
            if anchor_direction > 0
            else bar.close < frontier
        )
        for bar in touched_last
    )
    reclaim_fraction = (
        reclaimed / len(touched_last) if touched_last else 0.0
    )

    transition = (
        distance_velocity,
        distance_velocity - prior_velocity,
        touch_rates[-1] - touch_rates[-2],
        breach_rates[-1] - breach_rates[-2],
        last_nas_adverse - prior_nas_adverse,
        sp_adverse_returns[-1] - sp_adverse_returns[-2],
        us_adverse_returns[-1] - us_adverse_returns[-2],
        peer_breadth_last,
        peer_breadth_last - peer_breadth_prior,
        _state_transitions(tuple(touch_rates)),
        _state_transitions(tuple(breach_rates)),
        reclaim_fraction,
    )
    features = tuple(value for row in block_rows for value in row) + transition
    return CausalTrajectorySourceState(
        episode_id=episode_id,
        as_of=as_of,
        anchor_direction=anchor_direction,
        features=features,
    )


@dataclass(frozen=True, slots=True)
class CausalTrajectoryTrainingEpisode:
    source: CausalTrajectorySourceState
    observed_at: datetime
    label: EventManifoldLabel

    def __post_init__(self) -> None:
        if _utc(self.observed_at) <= _utc(self.source.as_of):
            raise ValueError("V9 label must mature after source state")


@dataclass(frozen=True, slots=True)
class CausalTrajectoryModel:
    fitted_at: datetime
    fit_partition: str
    feature_names: tuple[str, ...]
    centers_micros: tuple[int, ...]
    scales_micros: tuple[int, ...]
    eventness_coefficients_micros: tuple[int, ...]
    eventness_intercept_micros: int
    recovery_coefficients_micros: tuple[int, ...]
    recovery_intercept_micros: int
    eventness_threshold_micros: int
    recovery_threshold_micros: int
    calibration_terminal_preservation_bps: int
    calibration_false_reduction_bps: int
    calibration_gate_pass: bool
    fit_count: int
    fit_terminal_count: int
    fit_recovery_count: int
    fit_censored_count: int
    calibration_count: int
    calibration_terminal_count: int
    calibration_recovery_count: int
    calibration_censored_count: int
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
            raise ValueError("V9 fit partition must be r8")
        if self.feature_names != V9_FEATURE_NAMES:
            raise ValueError("V9 feature schema drift")
        width = len(V9_FEATURE_NAMES)
        if width != 60:
            raise ValueError("V9 representation must contain exactly 60 features")
        if not (
            len(self.centers_micros)
            == len(self.scales_micros)
            == len(self.eventness_coefficients_micros)
            == len(self.recovery_coefficients_micros)
            == width
        ):
            raise ValueError("V9 model vector width mismatch")
        if any(value <= 0 for value in self.scales_micros):
            raise ValueError("V9 scales must be positive")
        if self.eventness_threshold_micros not in V9_EVENTNESS_THRESHOLDS_MICROS:
            raise ValueError("V9 eventness threshold outside frozen grid")
        if self.recovery_threshold_micros not in V9_RECOVERY_THRESHOLDS_MICROS:
            raise ValueError("V9 recovery threshold outside frozen grid")
        if self.fit_terminal_count < 10 or self.fit_recovery_count < 10:
            raise ValueError("V9 discovery requires both event families")
        if self.calibration_terminal_count < 5:
            raise ValueError("V9 calibration requires terminal evidence")
        if self.purged_discovery_count < 0:
            raise ValueError("V9 purge count cannot be negative")
        if _utc(self.discovery_observed_max) >= _utc(self.calibration_source_min):
            raise ValueError("V9 chronological purge boundary is not strict")
        for value in (
            self.calibration_terminal_preservation_bps,
            self.calibration_false_reduction_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("V9 calibration metric out of range")
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
            raise ValueError("V9 model carries forbidden authority or evidence")


@dataclass(frozen=True, slots=True)
class CausalTrajectoryAssessment:
    episode_id: str
    as_of: datetime
    anchor_direction: int
    eventness_micros: int
    recovery_contrast_micros: int
    state: CausalTrajectoryState
    structural_failure_declared: bool
    target_used: bool = False
    future_market_used: bool = False


@dataclass(frozen=True, slots=True)
class CausalTrajectoryEvaluation:
    partition: str
    sample_count: int
    baseline_terminal_count: int
    baseline_false_declaration_count: int
    trajectory_false_declaration_count: int
    trajectory_missed_terminal_count: int
    recovery_supported_count: int
    terminal_supported_count: int
    unresolved_count: int
    false_declaration_reduction_bps: int
    terminal_detection_preservation_bps: int


def _standardization(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    centers = tuple(fmean(row[i] for row in rows) for i in range(len(rows[0])))
    scales = []
    for i, center in enumerate(centers):
        variance = fmean((row[i] - center) ** 2 for row in rows)
        scales.append(max(1e-6, sqrt(variance)))
    return centers, tuple(scales)


def _standardize(
    row: tuple[float, ...],
    centers: tuple[float, ...],
    scales: tuple[float, ...],
) -> tuple[float, ...]:
    return tuple(
        (value - center) / scale
        for value, center, scale in zip(row, centers, scales, strict=True)
    )


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-max(-30.0, min(30.0, value))))


def _fit_logistic(
    rows: tuple[tuple[float, ...], ...],
    targets: tuple[float, ...],
) -> tuple[float, tuple[float, ...]]:
    coefficients = [0.0] * len(rows[0])
    intercept = 0.0
    count = float(len(rows))
    regularization = V9_RIDGE / count
    for _ in range(V9_TRAINING_STEPS):
        intercept_gradient = 0.0
        gradients = [0.0] * len(coefficients)
        for row, target in zip(rows, targets, strict=True):
            raw = intercept + sum(
                coefficient * value
                for coefficient, value in zip(coefficients, row, strict=True)
            )
            error = _sigmoid(raw) - target
            intercept_gradient += error
            for index, value in enumerate(row):
                gradients[index] += error * value
        intercept -= V9_LEARNING_RATE * intercept_gradient / count
        for index in range(len(coefficients)):
            gradient = gradients[index] / count
            gradient += regularization * coefficients[index]
            coefficients[index] -= V9_LEARNING_RATE * gradient
    return intercept, tuple(coefficients)


def _score(
    *,
    row: tuple[float, ...],
    centers_micros: tuple[int, ...],
    scales_micros: tuple[int, ...],
    coefficients_micros: tuple[int, ...],
    intercept_micros: int,
) -> int:
    centers = tuple(value / 1_000_000 for value in centers_micros)
    scales = tuple(value / 1_000_000 for value in scales_micros)
    coefficients = tuple(value / 1_000_000 for value in coefficients_micros)
    standardized = _standardize(row, centers, scales)
    raw = intercept_micros / 1_000_000 + sum(
        coefficient * value
        for coefficient, value in zip(coefficients, standardized, strict=True)
    )
    return int(round(_sigmoid(raw) * 1_000_000))


def _classify(
    *,
    eventness_micros: int,
    recovery_contrast_micros: int,
    eventness_threshold_micros: int,
    recovery_threshold_micros: int,
    evidence_complete: bool,
) -> CausalTrajectoryState:
    if not evidence_complete or eventness_micros < eventness_threshold_micros:
        return CausalTrajectoryState.UNRESOLVED
    if recovery_contrast_micros >= recovery_threshold_micros:
        return CausalTrajectoryState.RECOVERY_SUPPORTED
    if recovery_contrast_micros <= 1_000_000 - recovery_threshold_micros:
        return CausalTrajectoryState.TERMINAL_SUPPORTED
    return CausalTrajectoryState.UNRESOLVED


def _metrics(
    *,
    scores: tuple[tuple[int, int, EventManifoldLabel, bool], ...],
    eventness_threshold_micros: int,
    recovery_threshold_micros: int,
) -> tuple[int, int]:
    terminal_count = sum(
        label is EventManifoldLabel.TERMINAL_EVENT for _, _, label, _ in scores
    )
    false_count = len(scores) - terminal_count
    missed_terminal = 0
    false_suppressed = 0
    for eventness, recovery, label, complete in scores:
        state = _classify(
            eventness_micros=eventness,
            recovery_contrast_micros=recovery,
            eventness_threshold_micros=eventness_threshold_micros,
            recovery_threshold_micros=recovery_threshold_micros,
            evidence_complete=complete,
        )
        if state is CausalTrajectoryState.RECOVERY_SUPPORTED:
            if label is EventManifoldLabel.TERMINAL_EVENT:
                missed_terminal += 1
            else:
                false_suppressed += 1
    preservation = (
        0
        if terminal_count == 0
        else (terminal_count - missed_terminal) * 10_000 // terminal_count
    )
    reduction = (
        0
        if false_count == 0
        else false_suppressed * 10_000 // false_count
    )
    return preservation, reduction


def fit_causal_trajectory_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[CausalTrajectoryTrainingEpisode, ...],
) -> CausalTrajectoryModel:
    cutoff = _utc(fitted_at)
    if fit_partition != "r8":
        raise ValueError("V9 fit partition is frozen to r8")
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future V9 training evidence beyond fitted_at")

    ordered = tuple(sorted(episodes, key=lambda item: item.source.as_of))
    split = len(ordered) * V9_DISCOVERY_FRACTION_BPS // 10_000
    if split < 100 or len(ordered) - split < 50:
        raise ValueError("insufficient chronological V9 evidence")
    raw_discovery = ordered[:split]
    calibration = ordered[split:]
    calibration_source_min = _utc(calibration[0].source.as_of)
    discovery = tuple(
        item
        for item in raw_discovery
        if item.source.evidence_complete
        and _utc(item.observed_at) < calibration_source_min
    )
    purged = len(raw_discovery) - len(discovery)
    if len(discovery) < 100:
        raise ValueError("V9 purge leaves insufficient discovery evidence")
    discovery_observed_max = max(_utc(item.observed_at) for item in discovery)
    if discovery_observed_max >= calibration_source_min:
        raise AssertionError("V9 chronological purge boundary is not strict")

    rows = tuple(item.source.features for item in discovery)
    centers, scales = _standardization(rows)
    standardized = tuple(_standardize(row, centers, scales) for row in rows)
    eventness_targets = tuple(
        0.0 if item.label is EventManifoldLabel.CENSORED_UNKNOWN else 1.0
        for item in discovery
    )
    event_intercept, event_coefficients = _fit_logistic(
        standardized,
        eventness_targets,
    )

    event_pairs = tuple(
        (row, item)
        for row, item in zip(standardized, discovery, strict=True)
        if item.label is not EventManifoldLabel.CENSORED_UNKNOWN
    )
    recovery_intercept, recovery_coefficients = _fit_logistic(
        tuple(row for row, _ in event_pairs),
        tuple(
            1.0 if item.label is EventManifoldLabel.VERIFIED_RECOVERY_EVENT else 0.0
            for _, item in event_pairs
        ),
    )

    centers_micros = tuple(int(round(value * 1_000_000)) for value in centers)
    scales_micros = tuple(
        max(1, int(round(value * 1_000_000))) for value in scales
    )
    event_coefficients_micros = tuple(
        int(round(value * 1_000_000)) for value in event_coefficients
    )
    recovery_coefficients_micros = tuple(
        int(round(value * 1_000_000)) for value in recovery_coefficients
    )
    event_intercept_micros = int(round(event_intercept * 1_000_000))
    recovery_intercept_micros = int(round(recovery_intercept * 1_000_000))

    calibration_scores = tuple(
        (
            _score(
                row=item.source.features,
                centers_micros=centers_micros,
                scales_micros=scales_micros,
                coefficients_micros=event_coefficients_micros,
                intercept_micros=event_intercept_micros,
            ),
            _score(
                row=item.source.features,
                centers_micros=centers_micros,
                scales_micros=scales_micros,
                coefficients_micros=recovery_coefficients_micros,
                intercept_micros=recovery_intercept_micros,
            ),
            item.label,
            item.source.evidence_complete,
        )
        for item in calibration
    )

    candidates = []
    for event_threshold in V9_EVENTNESS_THRESHOLDS_MICROS:
        for recovery_threshold in V9_RECOVERY_THRESHOLDS_MICROS:
            preservation, reduction = _metrics(
                scores=calibration_scores,
                eventness_threshold_micros=event_threshold,
                recovery_threshold_micros=recovery_threshold,
            )
            legal = preservation >= V9_CALIBRATION_TERMINAL_PRESERVATION_BPS
            candidates.append(
                (
                    legal,
                    reduction,
                    preservation,
                    event_threshold,
                    recovery_threshold,
                )
            )
    legal_candidates = [candidate for candidate in candidates if candidate[0]]
    selected = max(legal_candidates or candidates)
    (
        calibration_gate_pass,
        calibration_reduction,
        calibration_preservation,
        event_threshold,
        recovery_threshold,
    ) = selected

    return CausalTrajectoryModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        feature_names=V9_FEATURE_NAMES,
        centers_micros=centers_micros,
        scales_micros=scales_micros,
        eventness_coefficients_micros=event_coefficients_micros,
        eventness_intercept_micros=event_intercept_micros,
        recovery_coefficients_micros=recovery_coefficients_micros,
        recovery_intercept_micros=recovery_intercept_micros,
        eventness_threshold_micros=event_threshold,
        recovery_threshold_micros=recovery_threshold,
        calibration_terminal_preservation_bps=calibration_preservation,
        calibration_false_reduction_bps=calibration_reduction,
        calibration_gate_pass=calibration_gate_pass,
        fit_count=len(discovery),
        fit_terminal_count=sum(
            item.label is EventManifoldLabel.TERMINAL_EVENT for item in discovery
        ),
        fit_recovery_count=sum(
            item.label is EventManifoldLabel.VERIFIED_RECOVERY_EVENT
            for item in discovery
        ),
        fit_censored_count=sum(
            item.label is EventManifoldLabel.CENSORED_UNKNOWN for item in discovery
        ),
        calibration_count=len(calibration),
        calibration_terminal_count=sum(
            item.label is EventManifoldLabel.TERMINAL_EVENT for item in calibration
        ),
        calibration_recovery_count=sum(
            item.label is EventManifoldLabel.VERIFIED_RECOVERY_EVENT
            for item in calibration
        ),
        calibration_censored_count=sum(
            item.label is EventManifoldLabel.CENSORED_UNKNOWN
            for item in calibration
        ),
        purged_discovery_count=purged,
        discovery_observed_max=discovery_observed_max,
        calibration_source_min=calibration_source_min,
    )


def assess_causal_trajectory(
    *,
    model: CausalTrajectoryModel,
    source: CausalTrajectorySourceState,
) -> CausalTrajectoryAssessment:
    eventness = _score(
        row=source.features,
        centers_micros=model.centers_micros,
        scales_micros=model.scales_micros,
        coefficients_micros=model.eventness_coefficients_micros,
        intercept_micros=model.eventness_intercept_micros,
    )
    recovery = _score(
        row=source.features,
        centers_micros=model.centers_micros,
        scales_micros=model.scales_micros,
        coefficients_micros=model.recovery_coefficients_micros,
        intercept_micros=model.recovery_intercept_micros,
    )
    state = _classify(
        eventness_micros=eventness,
        recovery_contrast_micros=recovery,
        eventness_threshold_micros=model.eventness_threshold_micros,
        recovery_threshold_micros=model.recovery_threshold_micros,
        evidence_complete=source.evidence_complete,
    )
    return CausalTrajectoryAssessment(
        episode_id=source.episode_id,
        as_of=source.as_of,
        anchor_direction=source.anchor_direction,
        eventness_micros=eventness,
        recovery_contrast_micros=recovery,
        state=state,
        structural_failure_declared=(
            state is not CausalTrajectoryState.RECOVERY_SUPPORTED
        ),
    )


def evaluate_causal_trajectory(
    *,
    model: CausalTrajectoryModel,
    partition: str,
    episodes: tuple[CausalTrajectoryTrainingEpisode, ...],
) -> CausalTrajectoryEvaluation:
    assessed = tuple(
        (item, assess_causal_trajectory(model=model, source=item.source))
        for item in episodes
    )
    terminal_count = sum(
        item.label is EventManifoldLabel.TERMINAL_EVENT for item, _ in assessed
    )
    false_count = len(assessed) - terminal_count
    missed = sum(
        item.label is EventManifoldLabel.TERMINAL_EVENT
        and not assessment.structural_failure_declared
        for item, assessment in assessed
    )
    false_kept = sum(
        item.label is not EventManifoldLabel.TERMINAL_EVENT
        and assessment.structural_failure_declared
        for item, assessment in assessed
    )
    return CausalTrajectoryEvaluation(
        partition=partition,
        sample_count=len(assessed),
        baseline_terminal_count=terminal_count,
        baseline_false_declaration_count=false_count,
        trajectory_false_declaration_count=false_kept,
        trajectory_missed_terminal_count=missed,
        recovery_supported_count=sum(
            assessment.state is CausalTrajectoryState.RECOVERY_SUPPORTED
            for _, assessment in assessed
        ),
        terminal_supported_count=sum(
            assessment.state is CausalTrajectoryState.TERMINAL_SUPPORTED
            for _, assessment in assessed
        ),
        unresolved_count=sum(
            assessment.state is CausalTrajectoryState.UNRESOLVED
            for _, assessment in assessed
        ),
        false_declaration_reduction_bps=(
            0
            if false_count == 0
            else (false_count - false_kept) * 10_000 // false_count
        ),
        terminal_detection_preservation_bps=(
            0
            if terminal_count == 0
            else (terminal_count - missed) * 10_000 // terminal_count
        ),
    )


def causal_trajectory_model_fingerprint(model: CausalTrajectoryModel) -> str:
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


def causal_trajectory_representation_fingerprint() -> str:
    payload = {
        "identity": "QORE_SHARED_WP05_CAUSAL_TRAJECTORY_DISCRIMINATION_V9_001",
        "target": "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2",
        "feature_names": list(V9_FEATURE_NAMES),
        "blocks": 6,
        "block_minutes": 5,
        "source_minutes": 30,
        "future_market_used": False,
        "event_ontology": [item.value for item in EventManifoldLabel],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
