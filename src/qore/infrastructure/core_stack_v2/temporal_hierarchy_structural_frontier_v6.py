"""WP-05 V6 structural-frontier survival model.

The active WP-05 target defines terminal failure relative to a source-time
higher-timeframe anchor and structural price frontier. V6 therefore models the
source state in the same coordinate system instead of asking a generic
multi-timescale classifier to infer that geometry indirectly.

Training may use matured historical terminal labels offline. Runtime consumes
only source-time structural-frontier, temporal-hierarchy and cross-market
features supplied by the caller. The model has no methodology, sizing, Risk,
order or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import sqrt
from statistics import fmean

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
)


V6_DISCOVERY_FRACTION_BPS = 7_000
V6_CALIBRATION_RECALL_BPS = 9_800
V6_RIDGE = 4.0


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class StructuralFrontierSourceState:
    episode_id: str
    as_of: datetime
    anchor_direction: int
    distance_now: float
    approach_5m: float
    approach_15m: float
    rejection_5m: float
    rejection_15m: float
    adverse_close_fraction_5m: float
    volatility_ratio_5m_20m: float
    peer_adverse_5m: float
    peer_adverse_15m: float
    higher_resilience_minus_fragility: float
    hierarchy_depth: float
    hierarchy_recession_minus_advance: float
    future_market_used: bool = False
    target_used: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("episode_id must be non-empty")
        _utc(self.as_of)
        if self.anchor_direction not in (-1, 1):
            raise ValueError("source state requires identifiable anchor")
        if (
            self.future_market_used
            or self.target_used
            or self.trader_identity_used
            or self.symbol_identity_used
        ):
            raise ValueError("source state carries forbidden evidence")


@dataclass(frozen=True, slots=True)
class StructuralFrontierTrainingEpisode:
    source: StructuralFrontierSourceState
    observed_at: datetime
    terminal_failure: bool

    def __post_init__(self) -> None:
        if _utc(self.observed_at) <= _utc(self.source.as_of):
            raise ValueError("terminal label must mature after source state")


@dataclass(frozen=True, slots=True)
class StructuralFrontierModel:
    fitted_at: datetime
    fit_partition: str
    feature_names: tuple[str, ...]
    feature_centers_micros: tuple[int, ...]
    feature_scales_micros: tuple[int, ...]
    coefficients_micros: tuple[int, ...]
    intercept_micros: int
    declaration_threshold_micros: int
    calibration_terminal_preservation_bps: int
    calibration_false_reduction_bps: int
    fit_count: int
    fit_terminal_count: int
    calibration_count: int
    calibration_terminal_count: int
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
        width = len(self.feature_names)
        if width < 1:
            raise ValueError("structural-frontier model requires features")
        if not (
            len(self.feature_centers_micros)
            == len(self.feature_scales_micros)
            == len(self.coefficients_micros)
            == width
        ):
            raise ValueError("structural-frontier model width mismatch")
        if self.fit_count < 100 or self.fit_terminal_count < 10:
            raise ValueError("structural-frontier fit evidence is insufficient")
        if self.calibration_count < 50 or self.calibration_terminal_count < 5:
            raise ValueError("structural-frontier calibration evidence is insufficient")
        if not 0 <= self.declaration_threshold_micros <= 1_000_000:
            raise ValueError("declaration threshold out of range")
        if not 0 <= self.calibration_terminal_preservation_bps <= 10_000:
            raise ValueError("calibration terminal preservation out of range")
        if not 0 <= self.calibration_false_reduction_bps <= 10_000:
            raise ValueError("calibration false reduction out of range")
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
            raise ValueError("structural-frontier model carries forbidden authority")


@dataclass(frozen=True, slots=True)
class StructuralFrontierAssessment:
    episode_id: str
    as_of: datetime
    anchor_direction: int
    failure_probability_micros: int
    structural_failure_declared: bool
    recoverable_pullback: bool
    target_used: bool = False
    future_market_used: bool = False

    def __post_init__(self) -> None:
        _utc(self.as_of)
        if self.anchor_direction not in (-1, 1):
            raise ValueError("assessment requires identifiable anchor")
        if not 0 <= self.failure_probability_micros <= 1_000_000:
            raise ValueError("failure probability out of range")
        if self.structural_failure_declared and self.recoverable_pullback:
            raise ValueError("failure and recoverable states cannot coexist")
        if self.target_used or self.future_market_used:
            raise ValueError("runtime assessment uses forbidden evidence")


@dataclass(frozen=True, slots=True)
class StructuralFrontierEvaluation:
    partition: str
    sample_count: int
    baseline_terminal_count: int
    baseline_false_declaration_count: int
    hierarchy_terminal_count: int
    hierarchy_false_declaration_count: int
    hierarchy_missed_terminal_count: int
    false_declaration_reduction_bps: int
    terminal_detection_preservation_bps: int


_HIERARCHY_SCALES = (
    WorldScale.M1,
    WorldScale.M3,
    WorldScale.M5,
    WorldScale.M15,
    WorldScale.H1,
    WorldScale.H4,
    WorldScale.DAILY,
)


@dataclass(frozen=True, slots=True)
class StructuralFrontierHierarchyMotif:
    depth_path: tuple[int, ...]
    current_depth: int
    recession_count: int
    advance_count: int

    def __post_init__(self) -> None:
        if len(self.depth_path) < 3:
            raise ValueError("frontier hierarchy motif requires a causal trajectory")
        if self.current_depth != self.depth_path[-1]:
            raise ValueError("current_depth must equal final depth")
        if any(not 0 <= value <= len(_HIERARCHY_SCALES) for value in self.depth_path):
            raise ValueError("hierarchy depth out of range")


def structural_frontier_hierarchy_motif(
    *,
    trajectory: TemporalHierarchyTrajectory,
    anchor_direction: int,
) -> StructuralFrontierHierarchyMotif:
    """Interpret the entire pre-source trajectory in one Target-V2 coordinate.

    The anchor is the identifiable higher-timeframe direction at the final
    source timestamp. It remains fixed while reading earlier causal snapshots,
    so depth/recession/advance cannot silently switch coordinate systems.
    """

    if anchor_direction not in (-1, 1):
        raise ValueError("structural-frontier motif requires identifiable anchor")

    depths: list[int] = []
    for snapshot in trajectory.snapshots:
        levels = {item.scale: item for item in snapshot.levels}
        depth = 0
        for index, scale in enumerate(_HIERARCHY_SCALES, start=1):
            level = levels.get(scale)
            if level is None:
                continue
            if anchor_direction * level.direction_milli < 0:
                depth = max(depth, index)
        depths.append(depth)

    depth_path = tuple(depths)
    recession = sum(
        right < left
        for left, right in zip(depth_path, depth_path[1:], strict=False)
    )
    advance = sum(
        right > left
        for left, right in zip(depth_path, depth_path[1:], strict=False)
    )
    return StructuralFrontierHierarchyMotif(
        depth_path=depth_path,
        current_depth=depth_path[-1],
        recession_count=recession,
        advance_count=advance,
    )


_BASE_NAMES = (
    "DISTANCE_NOW",
    "APPROACH_5M",
    "APPROACH_15M",
    "REJECTION_5M",
    "REJECTION_15M",
    "ADVERSE_CLOSE_FRACTION_5M",
    "VOLATILITY_RATIO_5M_20M",
    "PEER_ADVERSE_5M",
    "PEER_ADVERSE_15M",
    "HIGHER_RESILIENCE_MINUS_FRAGILITY",
    "HIERARCHY_DEPTH",
    "HIERARCHY_RECESSION_MINUS_ADVANCE",
)


def _base_values(state: StructuralFrontierSourceState) -> tuple[float, ...]:
    return (
        state.distance_now,
        state.approach_5m,
        state.approach_15m,
        state.rejection_5m,
        state.rejection_15m,
        state.adverse_close_fraction_5m,
        state.volatility_ratio_5m_20m,
        state.peer_adverse_5m,
        state.peer_adverse_15m,
        state.higher_resilience_minus_fragility,
        state.hierarchy_depth,
        state.hierarchy_recession_minus_advance,
    )


_INTERACTIONS = (
    (0, 1),
    (0, 2),
    (0, 3),
    (0, 4),
    (1, 7),
    (2, 8),
    (1, 6),
    (9, 10),
    (3, 11),
    (7, 8),
)


def _expanded_features(
    state: StructuralFrontierSourceState,
) -> tuple[tuple[str, ...], tuple[float, ...]]:
    base = _base_values(state)
    names = list(_BASE_NAMES)
    values = list(base)
    for index, name in enumerate(_BASE_NAMES):
        names.append(f"{name}_SQ")
        values.append(base[index] * base[index])
    for left, right in _INTERACTIONS:
        names.append(f"{_BASE_NAMES[left]}__X__{_BASE_NAMES[right]}")
        values.append(base[left] * base[right])
    return tuple(names), tuple(values)


def _solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    width = len(vector)
    augmented = [[*matrix[row], vector[row]] for row in range(width)]
    for column in range(width):
        pivot = max(
            range(column, width),
            key=lambda row: abs(augmented[row][column]),
        )
        if abs(augmented[pivot][column]) < 1e-12:
            continue
        augmented[column], augmented[pivot] = (
            augmented[pivot],
            augmented[column],
        )
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(width):
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
    return [augmented[row][-1] for row in range(width)]


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


def _ridge_fit(
    rows: tuple[tuple[float, ...], ...],
    targets: tuple[float, ...],
    *,
    ridge: float,
) -> tuple[float, tuple[float, ...]]:
    design = tuple((1.0, *row) for row in rows)
    width = len(design[0])
    matrix = [[0.0] * width for _ in range(width)]
    vector = [0.0] * width
    for row, target in zip(design, targets, strict=True):
        for left in range(width):
            vector[left] += row[left] * target
            for right in range(width):
                matrix[left][right] += row[left] * row[right]
    for index in range(1, width):
        matrix[index][index] += ridge
    solved = _solve_linear(matrix, vector)
    return solved[0], tuple(solved[1:])


def _score(
    *,
    intercept: float,
    coefficients: tuple[float, ...],
    row: tuple[float, ...],
) -> int:
    raw = intercept + sum(
        coefficient * value
        for coefficient, value in zip(coefficients, row, strict=True)
    )
    bounded = max(0.0, min(1.0, raw))
    return int(round(bounded * 1_000_000))


def fit_structural_frontier_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[StructuralFrontierTrainingEpisode, ...],
    discovery_fraction_bps: int = V6_DISCOVERY_FRACTION_BPS,
    calibration_recall_bps: int = V6_CALIBRATION_RECALL_BPS,
    ridge: float = V6_RIDGE,
) -> StructuralFrontierModel:
    cutoff = _utc(fitted_at)
    if fit_partition != "r8":
        raise ValueError("V6 fit partition is frozen to r8")
    if discovery_fraction_bps != V6_DISCOVERY_FRACTION_BPS:
        raise ValueError("V6 discovery split is frozen at 7000 bps")
    if calibration_recall_bps != V6_CALIBRATION_RECALL_BPS:
        raise ValueError("V6 calibration recall is frozen at 9800 bps")
    if ridge != V6_RIDGE:
        raise ValueError("V6 ridge is frozen at 4.0")
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future training evidence beyond fitted_at")
    ordered = tuple(sorted(episodes, key=lambda item: item.source.as_of))
    split = len(ordered) * discovery_fraction_bps // 10_000
    if split < 100 or len(ordered) - split < 50:
        raise ValueError("insufficient chronological discovery/calibration evidence")
    discovery = ordered[:split]
    calibration = ordered[split:]

    names, first = _expanded_features(discovery[0].source)
    raw_rows = [first]
    for item in discovery[1:]:
        row_names, row = _expanded_features(item.source)
        if row_names != names:
            raise ValueError("structural-frontier feature schema drift")
        raw_rows.append(row)
    raw_rows_tuple = tuple(raw_rows)
    centers, scales = _standardization(raw_rows_tuple)
    standardized = tuple(
        _standardize(row, centers, scales)
        for row in raw_rows_tuple
    )
    targets = tuple(
        1.0 if item.terminal_failure else 0.0
        for item in discovery
    )
    intercept, coefficients = _ridge_fit(
        standardized,
        targets,
        ridge=ridge,
    )

    centers_micros = tuple(int(round(value * 1_000_000)) for value in centers)
    scales_micros = tuple(
        max(1, int(round(value * 1_000_000))) for value in scales
    )
    coefficients_micros = tuple(
        int(round(value * 1_000_000)) for value in coefficients
    )
    intercept_micros = int(round(intercept * 1_000_000))

    frozen_centers = tuple(value / 1_000_000 for value in centers_micros)
    frozen_scales = tuple(value / 1_000_000 for value in scales_micros)
    frozen_coefficients = tuple(
        value / 1_000_000 for value in coefficients_micros
    )
    frozen_intercept = intercept_micros / 1_000_000

    calibration_scores = []
    for item in calibration:
        row_names, raw = _expanded_features(item.source)
        if row_names != names:
            raise ValueError("structural-frontier calibration schema drift")
        calibration_scores.append(
            (
                _score(
                    intercept=frozen_intercept,
                    coefficients=frozen_coefficients,
                    row=_standardize(raw, frozen_centers, frozen_scales),
                ),
                item.terminal_failure,
            )
        )
    terminal_scores = sorted(
        score for score, terminal in calibration_scores if terminal
    )
    terminal_count = len(terminal_scores)
    if terminal_count < 5:
        raise ValueError("calibration requires terminal failures")
    allowed_misses = (
        terminal_count * (10_000 - calibration_recall_bps) // 10_000
    )
    threshold = terminal_scores[min(terminal_count - 1, allowed_misses)]

    calibration_false = sum(not terminal for _, terminal in calibration_scores)
    false_kept = sum(
        (not terminal) and score >= threshold
        for score, terminal in calibration_scores
    )
    terminal_kept = sum(
        terminal and score >= threshold
        for score, terminal in calibration_scores
    )
    false_reduction = (
        0
        if calibration_false == 0
        else (calibration_false - false_kept) * 10_000 // calibration_false
    )
    terminal_preservation = terminal_kept * 10_000 // terminal_count

    fit_terminal_count = sum(item.terminal_failure for item in discovery)
    return StructuralFrontierModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        feature_names=names,
        feature_centers_micros=centers_micros,
        feature_scales_micros=scales_micros,
        coefficients_micros=coefficients_micros,
        intercept_micros=intercept_micros,
        declaration_threshold_micros=threshold,
        calibration_terminal_preservation_bps=terminal_preservation,
        calibration_false_reduction_bps=false_reduction,
        fit_count=len(discovery),
        fit_terminal_count=fit_terminal_count,
        calibration_count=len(calibration),
        calibration_terminal_count=terminal_count,
    )


def assess_structural_frontier(
    *,
    model: StructuralFrontierModel,
    source: StructuralFrontierSourceState,
) -> StructuralFrontierAssessment:
    names, raw = _expanded_features(source)
    if names != model.feature_names:
        raise ValueError("structural-frontier runtime feature schema drift")
    centers = tuple(value / 1_000_000 for value in model.feature_centers_micros)
    scales = tuple(value / 1_000_000 for value in model.feature_scales_micros)
    coefficients = tuple(
        value / 1_000_000 for value in model.coefficients_micros
    )
    probability = _score(
        intercept=model.intercept_micros / 1_000_000,
        coefficients=coefficients,
        row=_standardize(raw, centers, scales),
    )
    declared = probability >= model.declaration_threshold_micros
    return StructuralFrontierAssessment(
        episode_id=source.episode_id,
        as_of=source.as_of,
        anchor_direction=source.anchor_direction,
        failure_probability_micros=probability,
        structural_failure_declared=declared,
        recoverable_pullback=not declared,
    )


def evaluate_structural_frontier(
    *,
    model: StructuralFrontierModel,
    partition: str,
    episodes: tuple[StructuralFrontierTrainingEpisode, ...],
) -> StructuralFrontierEvaluation:
    terminals = sum(item.terminal_failure for item in episodes)
    false_count = len(episodes) - terminals
    kept_terminal = 0
    kept_false = 0
    for item in episodes:
        assessment = assess_structural_frontier(
            model=model,
            source=item.source,
        )
        if assessment.structural_failure_declared:
            if item.terminal_failure:
                kept_terminal += 1
            else:
                kept_false += 1
    missed = terminals - kept_terminal
    reduction = (
        0
        if false_count == 0
        else (false_count - kept_false) * 10_000 // false_count
    )
    preservation = 0 if terminals == 0 else kept_terminal * 10_000 // terminals
    return StructuralFrontierEvaluation(
        partition=partition,
        sample_count=len(episodes),
        baseline_terminal_count=terminals,
        baseline_false_declaration_count=false_count,
        hierarchy_terminal_count=kept_terminal,
        hierarchy_false_declaration_count=kept_false,
        hierarchy_missed_terminal_count=missed,
        false_declaration_reduction_bps=reduction,
        terminal_detection_preservation_bps=preservation,
    )
