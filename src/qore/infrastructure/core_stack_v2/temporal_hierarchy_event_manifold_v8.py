"""WP-05 V8 event manifolds with explicit censoring.

V8 removes the V7 assumption that every non-terminal episode is a recovery.
Historical offline evidence is partitioned into TERMINAL_EVENT,
VERIFIED_RECOVERY_EVENT and CENSORED_UNKNOWN. Only the first two classes define
robust source-state manifolds. Runtime cognition is source-time only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite, sqrt
from statistics import median
from typing import Protocol, Sequence

from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_v7 import (
    RECOVERY_FEATURE_NAMES,
    TERMINAL_FEATURE_NAMES,
    CompetingSurvivalSourceState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    higher_timeframe_structural_failure_target,
)

V8_DISCOVERY_FRACTION_BPS = 7_000
V8_CALIBRATION_TERMINAL_PRESERVATION_BPS = 9_800
V8_RADIUS_QUANTILES_BPS = (
    1_000,
    1_500,
    2_000,
    2_500,
    3_000,
    3_500,
    4_000,
    4_500,
    5_000,
)
V8_ADVANTAGE_MARGINS_MICROS = (
    0,
    250_000,
    500_000,
    750_000,
    1_000_000,
    1_250_000,
    1_500_000,
    2_000_000,
)
V8_FEATURE_NAMES = TERMINAL_FEATURE_NAMES + tuple(
    name for name in RECOVERY_FEATURE_NAMES if name not in TERMINAL_FEATURE_NAMES
)


class FutureBarLike(Protocol):
    high: float
    low: float
    close: float


class EventManifoldLabel(StrEnum):
    TERMINAL_EVENT = "TERMINAL_EVENT"
    VERIFIED_RECOVERY_EVENT = "VERIFIED_RECOVERY_EVENT"
    CENSORED_UNKNOWN = "CENSORED_UNKNOWN"


class EventManifoldState(StrEnum):
    RECOVERY_SUPPORTED = "RECOVERY_SUPPORTED"
    TERMINAL_SUPPORTED = "TERMINAL_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def matured_event_label(
    *,
    anchor_direction: int,
    prior_peak: float,
    prior_floor: float,
    future_bars: Sequence[FutureBarLike],
) -> EventManifoldLabel:
    """Classify the matured 30m path for offline V8 research only."""

    if anchor_direction not in (-1, 1):
        raise ValueError("V8 event label requires identifiable anchor")
    if len(future_bars) != 30:
        raise ValueError("V8 event label requires exactly 30 future bars")
    if not prior_floor < prior_peak:
        raise ValueError("invalid Target-V2 frontier")

    future_high = max(item.high for item in future_bars)
    future_low = min(item.low for item in future_bars)
    final_close = future_bars[-1].close
    terminal = higher_timeframe_structural_failure_target(
        anchor_direction=anchor_direction,
        prior_peak=prior_peak,
        prior_floor=prior_floor,
        future_high=future_high,
        future_low=future_low,
        future_final_close=final_close,
    )
    if terminal:
        return EventManifoldLabel.TERMINAL_EVENT

    if anchor_direction > 0:
        contact = tuple(
            index
            for index, item in enumerate(future_bars)
            if item.low <= prior_floor
        )
        final_safe = final_close > prior_floor

        def safe(item: FutureBarLike) -> bool:
            return item.close > prior_floor

    else:
        contact = tuple(
            index
            for index, item in enumerate(future_bars)
            if item.high >= prior_peak
        )
        final_safe = final_close < prior_peak

        def safe(item: FutureBarLike) -> bool:
            return item.close < prior_peak

    if not contact or not final_safe:
        return EventManifoldLabel.CENSORED_UNKNOWN

    last_contact = contact[-1]
    post_contact = future_bars[last_contact + 1 :]
    for start in range(max(0, len(post_contact) - 2)):
        window = post_contact[start : start + 3]
        if len(window) == 3 and all(safe(item) for item in window):
            return EventManifoldLabel.VERIFIED_RECOVERY_EVENT
    return EventManifoldLabel.CENSORED_UNKNOWN


def _combined_features(source: CompetingSurvivalSourceState) -> tuple[float, ...]:
    mapping = dict(zip(TERMINAL_FEATURE_NAMES, source.terminal_features, strict=True))
    mapping.update(
        zip(RECOVERY_FEATURE_NAMES, source.recovery_features, strict=True)
    )
    values = tuple(float(mapping[name]) for name in V8_FEATURE_NAMES)
    if any(not isfinite(value) for value in values):
        raise ValueError("V8 source features must be finite")
    return values


@dataclass(frozen=True, slots=True)
class EventManifoldTrainingEpisode:
    source: CompetingSurvivalSourceState
    observed_at: datetime
    label: EventManifoldLabel

    def __post_init__(self) -> None:
        if _utc(self.observed_at) <= _utc(self.source.as_of):
            raise ValueError("V8 matured event must occur after source state")


@dataclass(frozen=True, slots=True)
class EventManifoldModel:
    fitted_at: datetime
    fit_partition: str
    feature_names: tuple[str, ...]
    feature_centers_micros: tuple[int, ...]
    feature_scales_micros: tuple[int, ...]
    terminal_centers_micros: tuple[int, ...]
    terminal_scales_micros: tuple[int, ...]
    recovery_centers_micros: tuple[int, ...]
    recovery_scales_micros: tuple[int, ...]
    recovery_radius_micros: int
    recovery_radius_quantile_bps: int
    recovery_advantage_margin_micros: int
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
            raise ValueError("V8 fit partition must be r8")
        if self.feature_names != V8_FEATURE_NAMES:
            raise ValueError("V8 feature schema drift")
        width = len(self.feature_names)
        vectors = (
            self.feature_centers_micros,
            self.feature_scales_micros,
            self.terminal_centers_micros,
            self.terminal_scales_micros,
            self.recovery_centers_micros,
            self.recovery_scales_micros,
        )
        if any(len(vector) != width for vector in vectors):
            raise ValueError("V8 manifold vector width mismatch")
        if any(value <= 0 for value in self.feature_scales_micros):
            raise ValueError("V8 global scales must be positive")
        if any(value <= 0 for value in self.terminal_scales_micros):
            raise ValueError("V8 terminal scales must be positive")
        if any(value <= 0 for value in self.recovery_scales_micros):
            raise ValueError("V8 recovery scales must be positive")
        if self.fit_terminal_count < 10 or self.fit_recovery_count < 10:
            raise ValueError("V8 discovery requires both event families")
        if self.calibration_terminal_count < 5:
            raise ValueError("V8 calibration requires terminal evidence")
        if self.recovery_radius_quantile_bps not in V8_RADIUS_QUANTILES_BPS:
            raise ValueError("V8 recovery radius quantile outside frozen grid")
        if self.recovery_advantage_margin_micros not in V8_ADVANTAGE_MARGINS_MICROS:
            raise ValueError("V8 recovery advantage margin outside frozen grid")
        if self.recovery_radius_micros < 0:
            raise ValueError("V8 recovery radius cannot be negative")
        if self.purged_discovery_count < 0:
            raise ValueError("V8 purge count cannot be negative")
        if _utc(self.discovery_observed_max) >= _utc(self.calibration_source_min):
            raise ValueError("V8 chronological purge boundary is not strict")
        for value in (
            self.calibration_terminal_preservation_bps,
            self.calibration_false_reduction_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("V8 calibration metric out of range")
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
            raise ValueError("V8 model carries forbidden authority or evidence")


@dataclass(frozen=True, slots=True)
class EventManifoldAssessment:
    episode_id: str
    as_of: datetime
    anchor_direction: int
    terminal_distance_micros: int
    recovery_distance_micros: int
    recovery_advantage_micros: int
    state: EventManifoldState
    structural_failure_declared: bool
    target_used: bool = False
    future_market_used: bool = False

    def __post_init__(self) -> None:
        _utc(self.as_of)
        if self.anchor_direction not in (-1, 1):
            raise ValueError("V8 assessment requires identifiable anchor")
        if self.terminal_distance_micros < 0 or self.recovery_distance_micros < 0:
            raise ValueError("V8 manifold distance cannot be negative")
        if self.state is EventManifoldState.RECOVERY_SUPPORTED:
            if self.structural_failure_declared:
                raise ValueError("recovery-supported state must suppress declaration")
        elif not self.structural_failure_declared:
            raise ValueError("non-recovery V8 state must preserve declaration")
        if self.target_used or self.future_market_used:
            raise ValueError("V8 runtime assessment uses forbidden evidence")


@dataclass(frozen=True, slots=True)
class EventManifoldEvaluation:
    partition: str
    sample_count: int
    baseline_terminal_count: int
    baseline_false_declaration_count: int
    manifold_false_declaration_count: int
    manifold_missed_terminal_count: int
    recovery_supported_count: int
    terminal_supported_count: int
    unresolved_count: int
    false_declaration_reduction_bps: int
    terminal_detection_preservation_bps: int


def _median_scale(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    width = len(rows[0])
    centers = tuple(median(row[index] for row in rows) for index in range(width))
    scales = []
    for index, center in enumerate(centers):
        mad = median(abs(row[index] - center) for row in rows)
        scales.append(max(1e-6, mad * 1.4826))
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


def _quantile(values: tuple[float, ...], bps: int) -> float:
    if not values:
        raise ValueError("V8 quantile requires values")
    ordered = sorted(values)
    index = (len(ordered) - 1) * bps // 10_000
    return ordered[index]


def _distance(
    *,
    row: tuple[float, ...],
    global_centers_micros: tuple[int, ...],
    global_scales_micros: tuple[int, ...],
    class_centers_micros: tuple[int, ...],
    class_scales_micros: tuple[int, ...],
) -> int:
    global_centers = tuple(value / 1_000_000 for value in global_centers_micros)
    global_scales = tuple(value / 1_000_000 for value in global_scales_micros)
    class_centers = tuple(value / 1_000_000 for value in class_centers_micros)
    class_scales = tuple(value / 1_000_000 for value in class_scales_micros)
    standardized = _standardize(row, global_centers, global_scales)
    class_standardized = _standardize(
        class_centers,
        global_centers,
        global_scales,
    )
    class_scale_standardized = tuple(
        max(1e-6, local / global_scale)
        for local, global_scale in zip(
            class_scales,
            global_scales,
            strict=True,
        )
    )
    squared = sum(
        ((value - center) / scale) ** 2
        for value, center, scale in zip(
            standardized,
            class_standardized,
            class_scale_standardized,
            strict=True,
        )
    )
    return int(round(sqrt(squared / len(row)) * 1_000_000))


def _classify(
    *,
    terminal_distance_micros: int,
    recovery_distance_micros: int,
    recovery_radius_micros: int,
    recovery_advantage_margin_micros: int,
    evidence_complete: bool,
) -> tuple[EventManifoldState, int]:
    if not evidence_complete:
        return EventManifoldState.UNRESOLVED, 0
    advantage = terminal_distance_micros - recovery_distance_micros
    if (
        recovery_distance_micros <= recovery_radius_micros
        and advantage >= recovery_advantage_margin_micros
    ):
        return EventManifoldState.RECOVERY_SUPPORTED, advantage
    if terminal_distance_micros < recovery_distance_micros:
        return EventManifoldState.TERMINAL_SUPPORTED, advantage
    return EventManifoldState.UNRESOLVED, advantage


def _metrics(
    *,
    rows: tuple[tuple[int, int, EventManifoldLabel, bool], ...],
    recovery_radius_micros: int,
    recovery_advantage_margin_micros: int,
) -> tuple[int, int]:
    terminal_count = sum(
        label is EventManifoldLabel.TERMINAL_EVENT
        for _, _, label, _ in rows
    )
    false_count = len(rows) - terminal_count
    missed_terminal = 0
    false_suppressed = 0
    for terminal_distance, recovery_distance, label, complete in rows:
        state, _ = _classify(
            terminal_distance_micros=terminal_distance,
            recovery_distance_micros=recovery_distance,
            recovery_radius_micros=recovery_radius_micros,
            recovery_advantage_margin_micros=recovery_advantage_margin_micros,
            evidence_complete=complete,
        )
        if state is EventManifoldState.RECOVERY_SUPPORTED:
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


def fit_event_manifold_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[EventManifoldTrainingEpisode, ...],
    discovery_fraction_bps: int = V8_DISCOVERY_FRACTION_BPS,
    calibration_terminal_preservation_bps: int = (
        V8_CALIBRATION_TERMINAL_PRESERVATION_BPS
    ),
) -> EventManifoldModel:
    cutoff = _utc(fitted_at)
    if fit_partition != "r8":
        raise ValueError("V8 fit partition is frozen to r8")
    if discovery_fraction_bps != V8_DISCOVERY_FRACTION_BPS:
        raise ValueError("V8 discovery split is frozen at 7000 bps")
    if (
        calibration_terminal_preservation_bps
        != V8_CALIBRATION_TERMINAL_PRESERVATION_BPS
    ):
        raise ValueError("V8 calibration preservation is frozen at 9800 bps")
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future V8 training evidence beyond fitted_at")

    ordered = tuple(sorted(episodes, key=lambda item: item.source.as_of))
    split = len(ordered) * discovery_fraction_bps // 10_000
    if split < 100 or len(ordered) - split < 50:
        raise ValueError("insufficient chronological V8 discovery/calibration evidence")
    raw_discovery = ordered[:split]
    calibration = ordered[split:]
    calibration_source_min = _utc(calibration[0].source.as_of)
    discovery = tuple(
        item
        for item in raw_discovery
        if item.source.evidence_complete
        and _utc(item.observed_at) < calibration_source_min
    )
    purged_discovery_count = len(raw_discovery) - len(discovery)
    if len(discovery) < 100:
        raise ValueError("V8 purge leaves insufficient discovery evidence")
    discovery_observed_max = max(_utc(item.observed_at) for item in discovery)
    if discovery_observed_max >= calibration_source_min:
        raise AssertionError("V8 chronological purge boundary is not strict")

    terminal = tuple(
        _combined_features(item.source)
        for item in discovery
        if item.label is EventManifoldLabel.TERMINAL_EVENT
    )
    recovery = tuple(
        _combined_features(item.source)
        for item in discovery
        if item.label is EventManifoldLabel.VERIFIED_RECOVERY_EVENT
    )
    if len(terminal) < 10 or len(recovery) < 10:
        raise ValueError("V8 discovery lacks event-family evidence")

    event_rows = terminal + recovery
    global_centers, global_scales = _median_scale(event_rows)
    terminal_centers, terminal_scales = _median_scale(terminal)
    recovery_centers, recovery_scales = _median_scale(recovery)

    def micros(values: tuple[float, ...], *, positive: bool = False) -> tuple[int, ...]:
        if positive:
            return tuple(max(1, int(round(value * 1_000_000))) for value in values)
        return tuple(int(round(value * 1_000_000)) for value in values)

    global_centers_micros = micros(global_centers)
    global_scales_micros = micros(global_scales, positive=True)
    terminal_centers_micros = micros(terminal_centers)
    terminal_scales_micros = micros(terminal_scales, positive=True)
    recovery_centers_micros = micros(recovery_centers)
    recovery_scales_micros = micros(recovery_scales, positive=True)

    recovery_discovery_distances = tuple(
        _distance(
            row=row,
            global_centers_micros=global_centers_micros,
            global_scales_micros=global_scales_micros,
            class_centers_micros=recovery_centers_micros,
            class_scales_micros=recovery_scales_micros,
        )
        / 1_000_000
        for row in recovery
    )
    calibration_rows = tuple(
        (
            _distance(
                row=_combined_features(item.source),
                global_centers_micros=global_centers_micros,
                global_scales_micros=global_scales_micros,
                class_centers_micros=terminal_centers_micros,
                class_scales_micros=terminal_scales_micros,
            ),
            _distance(
                row=_combined_features(item.source),
                global_centers_micros=global_centers_micros,
                global_scales_micros=global_scales_micros,
                class_centers_micros=recovery_centers_micros,
                class_scales_micros=recovery_scales_micros,
            ),
            item.label,
            item.source.evidence_complete,
        )
        for item in calibration
    )

    candidates = []
    for quantile_bps in V8_RADIUS_QUANTILES_BPS:
        radius_micros = int(
            round(_quantile(recovery_discovery_distances, quantile_bps) * 1_000_000)
        )
        for margin_micros in V8_ADVANTAGE_MARGINS_MICROS:
            preservation, reduction = _metrics(
                rows=calibration_rows,
                recovery_radius_micros=radius_micros,
                recovery_advantage_margin_micros=margin_micros,
            )
            legal = preservation >= calibration_terminal_preservation_bps
            candidates.append(
                (
                    legal,
                    preservation,
                    reduction,
                    -radius_micros,
                    margin_micros,
                    quantile_bps,
                    radius_micros,
                )
            )

    legal_candidates = [candidate for candidate in candidates if candidate[0]]
    selected = max(legal_candidates or candidates)
    (
        calibration_gate_pass,
        selected_preservation,
        selected_reduction,
        _,
        selected_margin,
        selected_quantile,
        selected_radius,
    ) = selected

    return EventManifoldModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        feature_names=V8_FEATURE_NAMES,
        feature_centers_micros=global_centers_micros,
        feature_scales_micros=global_scales_micros,
        terminal_centers_micros=terminal_centers_micros,
        terminal_scales_micros=terminal_scales_micros,
        recovery_centers_micros=recovery_centers_micros,
        recovery_scales_micros=recovery_scales_micros,
        recovery_radius_micros=selected_radius,
        recovery_radius_quantile_bps=selected_quantile,
        recovery_advantage_margin_micros=selected_margin,
        calibration_terminal_preservation_bps=selected_preservation,
        calibration_false_reduction_bps=selected_reduction,
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
            item.label is EventManifoldLabel.CENSORED_UNKNOWN for item in calibration
        ),
        purged_discovery_count=purged_discovery_count,
        discovery_observed_max=discovery_observed_max,
        calibration_source_min=calibration_source_min,
    )


def assess_event_manifold(
    *,
    model: EventManifoldModel,
    source: CompetingSurvivalSourceState,
) -> EventManifoldAssessment:
    row = _combined_features(source)
    terminal_distance = _distance(
        row=row,
        global_centers_micros=model.feature_centers_micros,
        global_scales_micros=model.feature_scales_micros,
        class_centers_micros=model.terminal_centers_micros,
        class_scales_micros=model.terminal_scales_micros,
    )
    recovery_distance = _distance(
        row=row,
        global_centers_micros=model.feature_centers_micros,
        global_scales_micros=model.feature_scales_micros,
        class_centers_micros=model.recovery_centers_micros,
        class_scales_micros=model.recovery_scales_micros,
    )
    state, advantage = _classify(
        terminal_distance_micros=terminal_distance,
        recovery_distance_micros=recovery_distance,
        recovery_radius_micros=model.recovery_radius_micros,
        recovery_advantage_margin_micros=model.recovery_advantage_margin_micros,
        evidence_complete=source.evidence_complete,
    )
    return EventManifoldAssessment(
        episode_id=source.episode_id,
        as_of=source.as_of,
        anchor_direction=source.anchor_direction,
        terminal_distance_micros=terminal_distance,
        recovery_distance_micros=recovery_distance,
        recovery_advantage_micros=advantage,
        state=state,
        structural_failure_declared=(
            state is not EventManifoldState.RECOVERY_SUPPORTED
        ),
    )


def evaluate_event_manifold(
    *,
    model: EventManifoldModel,
    partition: str,
    episodes: tuple[EventManifoldTrainingEpisode, ...],
) -> EventManifoldEvaluation:
    assessed = tuple(
        (item, assess_event_manifold(model=model, source=item.source))
        for item in episodes
    )
    terminal_count = sum(
        item.label is EventManifoldLabel.TERMINAL_EVENT
        for item, _ in assessed
    )
    false_count = len(assessed) - terminal_count
    missed_terminal = sum(
        item.label is EventManifoldLabel.TERMINAL_EVENT
        and not assessment.structural_failure_declared
        for item, assessment in assessed
    )
    false_kept = sum(
        item.label is not EventManifoldLabel.TERMINAL_EVENT
        and assessment.structural_failure_declared
        for item, assessment in assessed
    )
    return EventManifoldEvaluation(
        partition=partition,
        sample_count=len(assessed),
        baseline_terminal_count=terminal_count,
        baseline_false_declaration_count=false_count,
        manifold_false_declaration_count=false_kept,
        manifold_missed_terminal_count=missed_terminal,
        recovery_supported_count=sum(
            assessment.state is EventManifoldState.RECOVERY_SUPPORTED
            for _, assessment in assessed
        ),
        terminal_supported_count=sum(
            assessment.state is EventManifoldState.TERMINAL_SUPPORTED
            for _, assessment in assessed
        ),
        unresolved_count=sum(
            assessment.state is EventManifoldState.UNRESOLVED
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
            else (terminal_count - missed_terminal) * 10_000 // terminal_count
        ),
    )


def event_manifold_model_fingerprint(model: EventManifoldModel) -> str:
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


def event_manifold_representation_fingerprint() -> str:
    payload = {
        "identity": "QORE_SHARED_WP05_EVENT_MANIFOLD_WITH_CENSORING_V8_001",
        "target": "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2",
        "feature_names": list(V8_FEATURE_NAMES),
        "source_representation": "V7_CAUSAL_SOURCE_FEATURES_FROZEN",
        "event_labels": [item.value for item in EventManifoldLabel],
        "recovery_persistence_closes": 3,
        "censored_defines_manifold": False,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
