"""WP-05 V7 competing survival hypotheses.

V7 tests a preregistered structural hypothesis: terminality and recoverability
are competing mechanisms, not opposite ends of one scalar. The module is
authority-free and deterministic. Historical terminal labels are legal only
for offline R8 fitting/calibration; runtime assessment consumes source-time
mechanism evidence only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import exp, isfinite, sqrt
from statistics import fmean

V7_DISCOVERY_FRACTION_BPS = 7_000
V7_CALIBRATION_TERMINAL_PRESERVATION_BPS = 9_800
V7_RIDGE = 4.0
V7_TRAINING_STEPS = 500
V7_LEARNING_RATE = 0.05
V7_THRESHOLD_MIN_MICROS = 500_000
V7_THRESHOLD_MAX_MICROS = 900_000
V7_THRESHOLD_STEP_MICROS = 20_000
V7_CONFLICT_MARGIN_MICROS = 50_000


TERMINAL_FEATURE_NAMES = (
    "DISTANCE_NOW",
    "DISTANCE_1M",
    "DISTANCE_5M",
    "DISTANCE_15M",
    "DISTANCE_30M",
    "APPROACH_1M",
    "APPROACH_5M",
    "APPROACH_15M",
    "ACCELERATION_5M",
    "ACCELERATION_15M",
    "BREACH_DEPTH",
    "ACCEPTANCE_DURATION",
    "ADVERSE_PERSISTENCE_5M",
    "ADVERSE_PERSISTENCE_15M",
    "CONSECUTIVE_ADVERSE_CLOSES",
    "HIERARCHY_DEPTH",
    "HIERARCHY_DEPTH_VELOCITY",
    "HIGHER_FRAGILITY_MINUS_RESILIENCE",
    "TRANSITION_PRESSURE_DELTA_15M",
    "TRANSITION_PRESSURE_DELTA_30M",
    "PEER_ADVERSE_1M",
    "PEER_ADVERSE_5M",
    "PEER_ADVERSE_15M",
    "PEER_ADVERSE_ACCEL_5M",
    "PEER_ADVERSE_ACCEL_15M",
    "PEER_ADVERSE_BREADTH",
    "LEAD_LAG_SIGN_CONSISTENCY",
    "VOLATILITY_EXPANSION_MINUS_COMPRESSION",
    "NORMALIZED_ADVERSE_MOVE",
)

RECOVERY_FEATURE_NAMES = (
    "DISTANCE_NOW",
    "RECLAIM_DISTANCE",
    "FRONTIER_TOUCHES_15M",
    "FRONTIER_TOUCHES_30M",
    "BREACH_RECLAIM_TRANSITIONS_15M",
    "BREACH_RECLAIM_TRANSITIONS_30M",
    "FAVORABLE_PERSISTENCE_5M",
    "FAVORABLE_PERSISTENCE_15M",
    "CONSECUTIVE_FAVORABLE_CLOSES",
    "REJECTION_FRACTION_5M",
    "REJECTION_FRACTION_15M",
    "CLOSE_LOCATION_RECOVERY",
    "RECOVERY_VELOCITY",
    "TIME_SINCE_WORST_EXCURSION",
    "HIERARCHY_RECESSION_COUNT",
    "HIERARCHY_ADVANCE_COUNT",
    "HIGHER_RESILIENCE_MINUS_FRAGILITY",
    "HIGHER_RESILIENCE_DELTA_15M",
    "HIGHER_RESILIENCE_DELTA_30M",
    "COHERENCE_DELTA_15M",
    "COHERENCE_DELTA_30M",
    "PEER_CONTRADICTION",
    "PEER_RECOVERY_VELOCITY",
    "RANGE_RATIO_1M_5M",
    "RANGE_RATIO_5M_20M",
    "NORMALIZED_RECOVERY_MOVE",
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _check_features(
    name: str,
    values: tuple[float, ...],
    expected: tuple[str, ...],
) -> None:
    if len(values) != len(expected):
        raise ValueError(f"{name} feature width mismatch")
    if any(not isfinite(value) for value in values):
        raise ValueError(f"{name} features must be finite")


class CompetingSurvivalState(StrEnum):
    TERMINAL_SUPPORTED = "TERMINAL_SUPPORTED"
    RECOVERY_SUPPORTED = "RECOVERY_SUPPORTED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class CompetingSurvivalSourceState:
    episode_id: str
    as_of: datetime
    anchor_direction: int
    terminal_features: tuple[float, ...]
    recovery_features: tuple[float, ...]
    evidence_complete: bool = True
    future_market_used: bool = False
    target_used: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    setup_identity_used: bool = False
    pnl_used: bool = False

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("episode_id must be non-empty")
        _utc(self.as_of)
        if self.anchor_direction not in (-1, 1):
            raise ValueError("V7 source state requires identifiable anchor")
        _check_features("terminal", self.terminal_features, TERMINAL_FEATURE_NAMES)
        _check_features("recovery", self.recovery_features, RECOVERY_FEATURE_NAMES)
        if (
            self.future_market_used
            or self.target_used
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.setup_identity_used
            or self.pnl_used
        ):
            raise ValueError("V7 source state carries forbidden evidence")


@dataclass(frozen=True, slots=True)
class CompetingSurvivalTrainingEpisode:
    source: CompetingSurvivalSourceState
    observed_at: datetime
    terminal_failure: bool

    def __post_init__(self) -> None:
        if _utc(self.observed_at) <= _utc(self.source.as_of):
            raise ValueError("terminal label must mature after source state")


@dataclass(frozen=True, slots=True)
class CompetingSurvivalModel:
    fitted_at: datetime
    fit_partition: str
    terminal_feature_names: tuple[str, ...]
    recovery_feature_names: tuple[str, ...]
    terminal_centers_micros: tuple[int, ...]
    terminal_scales_micros: tuple[int, ...]
    terminal_coefficients_micros: tuple[int, ...]
    terminal_intercept_micros: int
    recovery_centers_micros: tuple[int, ...]
    recovery_scales_micros: tuple[int, ...]
    recovery_coefficients_micros: tuple[int, ...]
    recovery_intercept_micros: int
    terminal_threshold_micros: int
    recovery_threshold_micros: int
    calibration_terminal_preservation_bps: int
    calibration_false_reduction_bps: int
    calibration_gate_pass: bool
    fit_count: int
    fit_terminal_count: int
    calibration_count: int
    calibration_terminal_count: int
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
            raise ValueError("V7 fit partition must be r8")
        if self.terminal_feature_names != TERMINAL_FEATURE_NAMES:
            raise ValueError("V7 terminal feature schema drift")
        if self.recovery_feature_names != RECOVERY_FEATURE_NAMES:
            raise ValueError("V7 recovery feature schema drift")
        terminal_width = len(TERMINAL_FEATURE_NAMES)
        recovery_width = len(RECOVERY_FEATURE_NAMES)
        if not (
            len(self.terminal_centers_micros)
            == len(self.terminal_scales_micros)
            == len(self.terminal_coefficients_micros)
            == terminal_width
        ):
            raise ValueError("V7 terminal model width mismatch")
        if not (
            len(self.recovery_centers_micros)
            == len(self.recovery_scales_micros)
            == len(self.recovery_coefficients_micros)
            == recovery_width
        ):
            raise ValueError("V7 recovery model width mismatch")
        if self.fit_count < 100 or self.fit_terminal_count < 10:
            raise ValueError("V7 fit evidence is insufficient")
        if self.calibration_count < 50 or self.calibration_terminal_count < 5:
            raise ValueError("V7 calibration evidence is insufficient")
        if self.purged_discovery_count < 0:
            raise ValueError("purged_discovery_count cannot be negative")
        if _utc(self.discovery_observed_max) >= _utc(self.calibration_source_min):
            raise ValueError("V7 chronological purge boundary is not strict")
        for threshold in (
            self.terminal_threshold_micros,
            self.recovery_threshold_micros,
        ):
            if not V7_THRESHOLD_MIN_MICROS <= threshold <= V7_THRESHOLD_MAX_MICROS:
                raise ValueError("V7 threshold outside preregistered grid")
            if (threshold - V7_THRESHOLD_MIN_MICROS) % V7_THRESHOLD_STEP_MICROS:
                raise ValueError("V7 threshold is not on preregistered grid")
        for bps in (
            self.calibration_terminal_preservation_bps,
            self.calibration_false_reduction_bps,
        ):
            if not 0 <= bps <= 10_000:
                raise ValueError("V7 calibration metric out of range")
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
            raise ValueError("V7 model carries forbidden authority or evidence")


@dataclass(frozen=True, slots=True)
class CompetingSurvivalAssessment:
    episode_id: str
    as_of: datetime
    anchor_direction: int
    terminal_hazard_micros: int
    recovery_support_micros: int
    mechanism_conflict_micros: int
    state: CompetingSurvivalState
    structural_failure_declared: bool
    target_used: bool = False
    future_market_used: bool = False

    def __post_init__(self) -> None:
        _utc(self.as_of)
        if self.anchor_direction not in (-1, 1):
            raise ValueError("assessment requires identifiable anchor")
        for value in (
            self.terminal_hazard_micros,
            self.recovery_support_micros,
            self.mechanism_conflict_micros,
        ):
            if not 0 <= value <= 1_000_000:
                raise ValueError("V7 score out of range")
        if self.state is CompetingSurvivalState.RECOVERY_SUPPORTED:
            if self.structural_failure_declared:
                raise ValueError("recovery-supported state must suppress declaration")
        elif not self.structural_failure_declared:
            raise ValueError("terminal/unresolved state must preserve declaration")
        if self.target_used or self.future_market_used:
            raise ValueError("runtime assessment uses forbidden evidence")


@dataclass(frozen=True, slots=True)
class CompetingSurvivalEvaluation:
    partition: str
    sample_count: int
    baseline_terminal_count: int
    baseline_false_declaration_count: int
    competing_false_declaration_count: int
    competing_missed_terminal_count: int
    recovery_supported_count: int
    unresolved_count: int
    terminal_supported_count: int
    false_declaration_reduction_bps: int
    terminal_detection_preservation_bps: int


def _standardization(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    width = len(rows[0])
    centers = tuple(fmean(row[index] for row in rows) for index in range(width))
    scales = []
    for index, center in enumerate(centers):
        variance = fmean((row[index] - center) ** 2 for row in rows)
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
    clipped = max(-30.0, min(30.0, value))
    return 1.0 / (1.0 + exp(-clipped))


def _fit_logistic(
    rows: tuple[tuple[float, ...], ...],
    targets: tuple[float, ...],
    *,
    ridge: float,
) -> tuple[float, tuple[float, ...]]:
    width = len(rows[0])
    coefficients = [0.0] * width
    intercept = 0.0
    count = float(len(rows))
    regularization = ridge / count
    for _ in range(V7_TRAINING_STEPS):
        intercept_gradient = 0.0
        gradients = [0.0] * width
        for row, target in zip(rows, targets, strict=True):
            raw = intercept + sum(
                coefficient * value
                for coefficient, value in zip(coefficients, row, strict=True)
            )
            error = _sigmoid(raw) - target
            intercept_gradient += error
            for index, value in enumerate(row):
                gradients[index] += error * value
        intercept -= V7_LEARNING_RATE * intercept_gradient / count
        for index in range(width):
            gradient = gradients[index] / count
            gradient += regularization * coefficients[index]
            coefficients[index] -= V7_LEARNING_RATE * gradient
    return intercept, tuple(coefficients)


def _frozen_score(
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
    terminal_hazard_micros: int,
    recovery_support_micros: int,
    terminal_threshold_micros: int,
    recovery_threshold_micros: int,
    evidence_complete: bool,
) -> tuple[CompetingSurvivalState, int]:
    if not evidence_complete:
        return CompetingSurvivalState.UNRESOLVED, 1_000_000

    both_high = (
        terminal_hazard_micros >= terminal_threshold_micros
        and recovery_support_micros >= recovery_threshold_micros
    )
    both_near = (
        abs(terminal_hazard_micros - terminal_threshold_micros)
        <= V7_CONFLICT_MARGIN_MICROS
        and abs(recovery_support_micros - recovery_threshold_micros)
        <= V7_CONFLICT_MARGIN_MICROS
    )
    conflict = both_high or both_near
    conflict_score = (
        max(
            0,
            1_000_000
            - abs(terminal_hazard_micros - recovery_support_micros),
        )
        if conflict
        else 0
    )
    if conflict:
        return CompetingSurvivalState.UNRESOLVED, conflict_score
    if (
        recovery_support_micros >= recovery_threshold_micros
        and terminal_hazard_micros < terminal_threshold_micros
    ):
        return CompetingSurvivalState.RECOVERY_SUPPORTED, 0
    if (
        terminal_hazard_micros >= terminal_threshold_micros
        and recovery_support_micros < recovery_threshold_micros
    ):
        return CompetingSurvivalState.TERMINAL_SUPPORTED, 0
    return CompetingSurvivalState.UNRESOLVED, conflict_score


def _metrics_for_thresholds(
    *,
    scores: tuple[tuple[int, int, bool, bool], ...],
    terminal_threshold_micros: int,
    recovery_threshold_micros: int,
) -> tuple[int, int]:
    terminal_count = sum(terminal for _, _, terminal, _ in scores)
    false_count = len(scores) - terminal_count
    missed_terminal = 0
    false_suppressed = 0
    for terminal_score, recovery_score, terminal, complete in scores:
        state, _ = _classify(
            terminal_hazard_micros=terminal_score,
            recovery_support_micros=recovery_score,
            terminal_threshold_micros=terminal_threshold_micros,
            recovery_threshold_micros=recovery_threshold_micros,
            evidence_complete=complete,
        )
        if state is CompetingSurvivalState.RECOVERY_SUPPORTED:
            if terminal:
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


def fit_competing_survival_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[CompetingSurvivalTrainingEpisode, ...],
    discovery_fraction_bps: int = V7_DISCOVERY_FRACTION_BPS,
    calibration_terminal_preservation_bps: int = (
        V7_CALIBRATION_TERMINAL_PRESERVATION_BPS
    ),
    ridge: float = V7_RIDGE,
) -> CompetingSurvivalModel:
    cutoff = _utc(fitted_at)
    if fit_partition != "r8":
        raise ValueError("V7 fit partition is frozen to r8")
    if discovery_fraction_bps != V7_DISCOVERY_FRACTION_BPS:
        raise ValueError("V7 discovery split is frozen at 7000 bps")
    if (
        calibration_terminal_preservation_bps
        != V7_CALIBRATION_TERMINAL_PRESERVATION_BPS
    ):
        raise ValueError("V7 calibration preservation is frozen at 9800 bps")
    if ridge != V7_RIDGE:
        raise ValueError("V7 ridge is frozen at 4.0")
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future training evidence beyond fitted_at")

    ordered = tuple(sorted(episodes, key=lambda item: item.source.as_of))
    split = len(ordered) * discovery_fraction_bps // 10_000
    if split < 100 or len(ordered) - split < 50:
        raise ValueError("insufficient chronological discovery/calibration evidence")
    raw_discovery = ordered[:split]
    calibration = ordered[split:]
    calibration_source_min = _utc(calibration[0].source.as_of)
    discovery = tuple(
        item
        for item in raw_discovery
        if _utc(item.observed_at) < calibration_source_min
    )
    purged_discovery_count = len(raw_discovery) - len(discovery)
    if len(discovery) < 100:
        raise ValueError("chronological purge leaves insufficient discovery evidence")
    discovery_observed_max = max(_utc(item.observed_at) for item in discovery)
    if discovery_observed_max >= calibration_source_min:
        raise AssertionError("V7 chronological purge boundary is not strict")

    terminal_rows = tuple(item.source.terminal_features for item in discovery)
    recovery_rows = tuple(item.source.recovery_features for item in discovery)
    terminal_centers, terminal_scales = _standardization(terminal_rows)
    recovery_centers, recovery_scales = _standardization(recovery_rows)
    terminal_standardized = tuple(
        _standardize(row, terminal_centers, terminal_scales)
        for row in terminal_rows
    )
    recovery_standardized = tuple(
        _standardize(row, recovery_centers, recovery_scales)
        for row in recovery_rows
    )
    terminal_targets = tuple(
        1.0 if item.terminal_failure else 0.0 for item in discovery
    )
    recovery_targets = tuple(1.0 - target for target in terminal_targets)

    terminal_intercept, terminal_coefficients = _fit_logistic(
        terminal_standardized,
        terminal_targets,
        ridge=ridge,
    )
    recovery_intercept, recovery_coefficients = _fit_logistic(
        recovery_standardized,
        recovery_targets,
        ridge=ridge,
    )

    terminal_centers_micros = tuple(
        int(round(value * 1_000_000)) for value in terminal_centers
    )
    terminal_scales_micros = tuple(
        max(1, int(round(value * 1_000_000))) for value in terminal_scales
    )
    terminal_coefficients_micros = tuple(
        int(round(value * 1_000_000)) for value in terminal_coefficients
    )
    terminal_intercept_micros = int(round(terminal_intercept * 1_000_000))
    recovery_centers_micros = tuple(
        int(round(value * 1_000_000)) for value in recovery_centers
    )
    recovery_scales_micros = tuple(
        max(1, int(round(value * 1_000_000))) for value in recovery_scales
    )
    recovery_coefficients_micros = tuple(
        int(round(value * 1_000_000)) for value in recovery_coefficients
    )
    recovery_intercept_micros = int(round(recovery_intercept * 1_000_000))

    calibration_scores = tuple(
        (
            _frozen_score(
                row=item.source.terminal_features,
                centers_micros=terminal_centers_micros,
                scales_micros=terminal_scales_micros,
                coefficients_micros=terminal_coefficients_micros,
                intercept_micros=terminal_intercept_micros,
            ),
            _frozen_score(
                row=item.source.recovery_features,
                centers_micros=recovery_centers_micros,
                scales_micros=recovery_scales_micros,
                coefficients_micros=recovery_coefficients_micros,
                intercept_micros=recovery_intercept_micros,
            ),
            item.terminal_failure,
            item.source.evidence_complete,
        )
        for item in calibration
    )

    threshold_values = range(
        V7_THRESHOLD_MIN_MICROS,
        V7_THRESHOLD_MAX_MICROS + 1,
        V7_THRESHOLD_STEP_MICROS,
    )
    candidates = []
    for terminal_threshold in threshold_values:
        for recovery_threshold in threshold_values:
            preservation, reduction = _metrics_for_thresholds(
                scores=calibration_scores,
                terminal_threshold_micros=terminal_threshold,
                recovery_threshold_micros=recovery_threshold,
            )
            legal = preservation >= calibration_terminal_preservation_bps
            candidates.append(
                (
                    legal,
                    reduction,
                    preservation,
                    abs(recovery_threshold - terminal_threshold),
                    -terminal_threshold,
                    -recovery_threshold,
                    terminal_threshold,
                    recovery_threshold,
                )
            )
    legal_candidates = [candidate for candidate in candidates if candidate[0]]
    selected = max(legal_candidates or candidates)
    (
        calibration_gate_pass,
        calibration_false_reduction,
        calibration_terminal_preservation,
        _,
        _,
        _,
        terminal_threshold,
        recovery_threshold,
    ) = selected

    return CompetingSurvivalModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        terminal_feature_names=TERMINAL_FEATURE_NAMES,
        recovery_feature_names=RECOVERY_FEATURE_NAMES,
        terminal_centers_micros=terminal_centers_micros,
        terminal_scales_micros=terminal_scales_micros,
        terminal_coefficients_micros=terminal_coefficients_micros,
        terminal_intercept_micros=terminal_intercept_micros,
        recovery_centers_micros=recovery_centers_micros,
        recovery_scales_micros=recovery_scales_micros,
        recovery_coefficients_micros=recovery_coefficients_micros,
        recovery_intercept_micros=recovery_intercept_micros,
        terminal_threshold_micros=terminal_threshold,
        recovery_threshold_micros=recovery_threshold,
        calibration_terminal_preservation_bps=calibration_terminal_preservation,
        calibration_false_reduction_bps=calibration_false_reduction,
        calibration_gate_pass=calibration_gate_pass,
        fit_count=len(discovery),
        fit_terminal_count=sum(item.terminal_failure for item in discovery),
        calibration_count=len(calibration),
        calibration_terminal_count=sum(
            item.terminal_failure for item in calibration
        ),
        purged_discovery_count=purged_discovery_count,
        discovery_observed_max=discovery_observed_max,
        calibration_source_min=calibration_source_min,
    )


def assess_competing_survival(
    *,
    model: CompetingSurvivalModel,
    source: CompetingSurvivalSourceState,
) -> CompetingSurvivalAssessment:
    terminal_score = _frozen_score(
        row=source.terminal_features,
        centers_micros=model.terminal_centers_micros,
        scales_micros=model.terminal_scales_micros,
        coefficients_micros=model.terminal_coefficients_micros,
        intercept_micros=model.terminal_intercept_micros,
    )
    recovery_score = _frozen_score(
        row=source.recovery_features,
        centers_micros=model.recovery_centers_micros,
        scales_micros=model.recovery_scales_micros,
        coefficients_micros=model.recovery_coefficients_micros,
        intercept_micros=model.recovery_intercept_micros,
    )
    state, conflict = _classify(
        terminal_hazard_micros=terminal_score,
        recovery_support_micros=recovery_score,
        terminal_threshold_micros=model.terminal_threshold_micros,
        recovery_threshold_micros=model.recovery_threshold_micros,
        evidence_complete=source.evidence_complete,
    )
    return CompetingSurvivalAssessment(
        episode_id=source.episode_id,
        as_of=source.as_of,
        anchor_direction=source.anchor_direction,
        terminal_hazard_micros=terminal_score,
        recovery_support_micros=recovery_score,
        mechanism_conflict_micros=conflict,
        state=state,
        structural_failure_declared=(
            state is not CompetingSurvivalState.RECOVERY_SUPPORTED
        ),
    )


def evaluate_competing_survival(
    *,
    model: CompetingSurvivalModel,
    partition: str,
    episodes: tuple[CompetingSurvivalTrainingEpisode, ...],
) -> CompetingSurvivalEvaluation:
    assessments = tuple(
        (item, assess_competing_survival(model=model, source=item.source))
        for item in episodes
    )
    terminal_count = sum(item.terminal_failure for item, _ in assessments)
    false_count = len(assessments) - terminal_count
    missed_terminal = sum(
        item.terminal_failure and not assessment.structural_failure_declared
        for item, assessment in assessments
    )
    false_kept = sum(
        (not item.terminal_failure) and assessment.structural_failure_declared
        for item, assessment in assessments
    )
    recovery_count = sum(
        assessment.state is CompetingSurvivalState.RECOVERY_SUPPORTED
        for _, assessment in assessments
    )
    unresolved_count = sum(
        assessment.state is CompetingSurvivalState.UNRESOLVED
        for _, assessment in assessments
    )
    terminal_supported_count = sum(
        assessment.state is CompetingSurvivalState.TERMINAL_SUPPORTED
        for _, assessment in assessments
    )
    return CompetingSurvivalEvaluation(
        partition=partition,
        sample_count=len(assessments),
        baseline_terminal_count=terminal_count,
        baseline_false_declaration_count=false_count,
        competing_false_declaration_count=false_kept,
        competing_missed_terminal_count=missed_terminal,
        recovery_supported_count=recovery_count,
        unresolved_count=unresolved_count,
        terminal_supported_count=terminal_supported_count,
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


def competing_survival_model_fingerprint(
    model: CompetingSurvivalModel,
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
