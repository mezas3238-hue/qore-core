"""Temporal hierarchical reasoning for Shared Core WP-05.

The engine separates local adverse pressure from genuine higher-timeframe
structural failure. It learns a compact probabilistic readout over continuous
multi-scale state, rather than accumulating threshold rules.

Training may use matured historical terminal labels. Runtime projection is
strictly as-of and never consumes future outcomes, PnL, trader identity,
symbol identity or trading authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import sqrt
from statistics import fmean

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale

_MODEL_SCALES = (
    WorldScale.M1,
    WorldScale.M3,
    WorldScale.M5,
    WorldScale.M15,
    WorldScale.H1,
    WorldScale.H4,
    WorldScale.DAILY,
)
_LOW_SCALES = (
    WorldScale.M1,
    WorldScale.M3,
    WorldScale.M5,
    WorldScale.M15,
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


@dataclass(frozen=True, slots=True)
class TemporalScaleState:
    scale: WorldScale
    direction_milli: int
    persistence_bps: int
    coherence_bps: int
    efficiency_bps: int
    fragility_bps: int
    transition_bps: int

    def __post_init__(self) -> None:
        if not -1_000 <= self.direction_milli <= 1_000:
            raise ValueError("direction_milli must be within -1000..1000")
        for name in (
            "persistence_bps",
            "coherence_bps",
            "efficiency_bps",
            "fragility_bps",
            "transition_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class TemporalHierarchySnapshot:
    episode_id: str
    as_of: datetime
    levels: tuple[TemporalScaleState, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("episode_id must be non-empty")
        _utc(self.as_of)
        if len({item.scale for item in self.levels}) != len(self.levels):
            raise ValueError("temporal hierarchy scales must be unique")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError(
                "runtime temporal hierarchy cannot carry forbidden evidence "
                "or trading authority"
            )


@dataclass(frozen=True, slots=True)
class TemporalHierarchyTrainingEpisode:
    snapshot: TemporalHierarchySnapshot
    observed_at: datetime
    terminal_failure: bool

    def __post_init__(self) -> None:
        observed = _utc(self.observed_at)
        if observed <= _utc(self.snapshot.as_of):
            raise ValueError("terminal label must mature after source snapshot")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyModel:
    fitted_at: datetime
    fit_partition: str
    feature_names: tuple[str, ...]
    feature_centers_micros: tuple[int, ...]
    feature_scales_micros: tuple[int, ...]
    coefficients_micros: tuple[int, ...]
    intercept_micros: int
    declaration_threshold_micros: int
    minimum_training_recall_bps: int
    threshold_calibration_recall_bps: int
    baseline_training_count: int
    baseline_terminal_count: int
    target_used_for_training_only: bool = True
    runtime_future_market_used: bool = False
    outcome_used_at_runtime: bool = False
    trader_identity_used: bool = False
    symbol_identity_used: bool = False
    knowledge_promotion_authority: bool = False
    methodology_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _utc(self.fitted_at)
        if not self.fit_partition:
            raise ValueError("fit_partition must be non-empty")
        width = len(self.feature_names)
        if not width:
            raise ValueError("temporal hierarchy model requires features")
        if not (
            len(self.feature_centers_micros)
            == len(self.feature_scales_micros)
            == len(self.coefficients_micros)
            == width
        ):
            raise ValueError("temporal hierarchy model vector width mismatch")
        if any(value <= 0 for value in self.feature_scales_micros):
            raise ValueError("feature scales must be positive")
        if not 0 <= self.minimum_training_recall_bps <= 10_000:
            raise ValueError("minimum_training_recall_bps out of range")
        if not (
            self.minimum_training_recall_bps
            <= self.threshold_calibration_recall_bps
            <= 10_000
        ):
            raise ValueError("threshold calibration recall must dominate gate")
        if self.baseline_training_count < 1:
            raise ValueError("baseline training population must be non-empty")
        if self.baseline_terminal_count < 1:
            raise ValueError("baseline training terminals must be non-empty")
        if (
            self.runtime_future_market_used
            or self.outcome_used_at_runtime
            or self.trader_identity_used
            or self.symbol_identity_used
            or self.knowledge_promotion_authority
            or self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("temporal hierarchy model carries forbidden authority")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyAssessment:
    episode_id: str
    as_of: datetime
    baseline_local_opposition: bool
    failure_probability_micros: int
    structural_failure_declared: bool
    pullback_only: bool
    target_used: bool = False
    future_market_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        _utc(self.as_of)
        if not 0 <= self.failure_probability_micros <= 1_000_000:
            raise ValueError("failure_probability_micros out of range")
        if self.structural_failure_declared and self.pullback_only:
            raise ValueError("failure and pullback cannot both be declared")
        if (
            self.target_used
            or self.future_market_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("runtime hierarchy assessment carries forbidden authority")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyEvaluation:
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

    def __post_init__(self) -> None:
        if not self.partition:
            raise ValueError("partition must be non-empty")
        for name in (
            "sample_count",
            "baseline_declaration_count",
            "baseline_terminal_count",
            "baseline_false_declaration_count",
            "hierarchy_declaration_count",
            "hierarchy_terminal_count",
            "hierarchy_false_declaration_count",
            "hierarchy_missed_terminal_count",
        ):
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} cannot be negative")
        for name in (
            "false_declaration_reduction_bps",
            "terminal_detection_preservation_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


def _level_map(
    snapshot: TemporalHierarchySnapshot,
) -> dict[WorldScale, TemporalScaleState]:
    return {item.scale: item for item in snapshot.levels}


def _mean_direction(
    levels: dict[WorldScale, TemporalScaleState],
    scales: tuple[WorldScale, ...],
) -> float:
    values = [
        levels[scale].direction_milli / 1_000.0
        for scale in scales
        if scale in levels
    ]
    return 0.0 if not values else fmean(values)


def baseline_local_opposition(snapshot: TemporalHierarchySnapshot) -> bool:
    levels = _level_map(snapshot)
    low = _mean_direction(levels, _LOW_SCALES)
    high = _mean_direction(levels, _HIGH_SCALES)
    return low != 0.0 and high != 0.0 and low * high < 0.0


def _feature_vector(
    snapshot: TemporalHierarchySnapshot,
) -> tuple[tuple[str, ...], tuple[float, ...]]:
    levels = _level_map(snapshot)
    names: list[str] = []
    values: list[float] = []

    for scale in _MODEL_SCALES:
        level = levels.get(scale)
        present = 1.0 if level is not None else 0.0
        direction = 0.0 if level is None else level.direction_milli / 1_000.0
        persistence = 0.0 if level is None else level.persistence_bps / 10_000.0
        coherence = 0.0 if level is None else level.coherence_bps / 10_000.0
        efficiency = 0.0 if level is None else level.efficiency_bps / 10_000.0
        fragility = 0.0 if level is None else level.fragility_bps / 10_000.0
        transition = 0.0 if level is None else level.transition_bps / 10_000.0
        prefix = scale.value
        names.extend(
            (
                f"{prefix}_PRESENT",
                f"{prefix}_DIRECTION",
                f"{prefix}_PERSISTENCE",
                f"{prefix}_COHERENCE",
                f"{prefix}_EFFICIENCY",
                f"{prefix}_FRAGILITY",
                f"{prefix}_TRANSITION",
            )
        )
        values.extend(
            (
                present,
                direction,
                persistence,
                coherence,
                efficiency,
                fragility,
                transition,
            )
        )

    low_direction = _mean_direction(levels, _LOW_SCALES)
    high_direction = _mean_direction(levels, _HIGH_SCALES)
    mid_direction = _mean_direction(
        levels,
        (WorldScale.M15, WorldScale.H1),
    )
    opposition = max(0.0, -(low_direction * high_direction))

    high_levels = [
        levels[scale]
        for scale in _HIGH_SCALES
        if scale in levels
    ]
    high_resilience = 0.0
    high_fragility = 0.0
    if high_levels:
        high_resilience = fmean(
            (
                (item.persistence_bps + item.coherence_bps) / 20_000.0
                * (1.0 - item.fragility_bps / 10_000.0)
            )
            for item in high_levels
        )
        high_fragility = fmean(
            (item.fragility_bps + item.transition_bps) / 20_000.0
            for item in high_levels
        )

    anchor = levels.get(WorldScale.DAILY)
    anchor_direction = (
        high_direction
        if anchor is None or anchor.direction_milli == 0
        else anchor.direction_milli / 1_000.0
    )
    anchor_sign = 1.0 if anchor_direction > 0 else -1.0 if anchor_direction < 0 else 0.0
    propagation_scales = (
        WorldScale.M15,
        WorldScale.H1,
        WorldScale.H4,
    )
    propagated = [
        max(0.0, -anchor_sign * levels[scale].direction_milli / 1_000.0)
        for scale in propagation_scales
        if scale in levels and anchor_sign != 0.0
    ]
    adverse_propagation = 0.0 if not propagated else fmean(propagated)

    ordered_directions = [
        levels[scale].direction_milli / 1_000.0
        for scale in _MODEL_SCALES
        if scale in levels
    ]
    adjacent_disagreement = 0.0
    if len(ordered_directions) >= 2:
        adjacent_disagreement = fmean(
            abs(right - left) / 2.0
            for left, right in zip(ordered_directions, ordered_directions[1:], strict=False)
        )

    names.extend(
        (
            "LOW_DIRECTION",
            "MID_DIRECTION",
            "HIGH_DIRECTION",
            "LOW_HIGH_OPPOSITION",
            "HIGH_RESILIENCE",
            "HIGH_FRAGILITY",
            "ADVERSE_PROPAGATION",
            "ADJACENT_DISAGREEMENT",
        )
    )
    values.extend(
        (
            low_direction,
            mid_direction,
            high_direction,
            opposition,
            high_resilience,
            high_fragility,
            adverse_propagation,
            adjacent_disagreement,
        )
    )
    return tuple(names), tuple(values)


def _solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    width = len(vector)
    augmented = [
        [*matrix[row], vector[row]]
        for row in range(width)
    ]
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
                for left, right in zip(augmented[row], augmented[column], strict=True)
            ]
    return [augmented[row][-1] for row in range(width)]


def _ridge_fit(
    rows: tuple[tuple[float, ...], ...],
    targets: tuple[float, ...],
    *,
    ridge: float,
) -> tuple[float, tuple[float, ...]]:
    if not rows or len(rows) != len(targets):
        raise ValueError("ridge fit requires aligned non-empty rows and targets")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("ridge rows must share width")

    design = tuple((1.0, *row) for row in rows)
    full_width = width + 1
    matrix = [[0.0] * full_width for _ in range(full_width)]
    vector = [0.0] * full_width
    for row, target in zip(design, targets, strict=True):
        for left in range(full_width):
            vector[left] += row[left] * target
            for right in range(full_width):
                matrix[left][right] += row[left] * row[right]
    for index in range(1, full_width):
        matrix[index][index] += ridge

    solved = _solve_linear(matrix, vector)
    return solved[0], tuple(solved[1:])


def _standardization(
    rows: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    width = len(rows[0])
    centers = tuple(
        fmean(row[index] for row in rows)
        for index in range(width)
    )
    scales: list[float] = []
    for index, center in enumerate(centers):
        variance = fmean(
            (row[index] - center) ** 2
            for row in rows
        )
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


def _predict_raw(
    *,
    intercept: float,
    coefficients: tuple[float, ...],
    row: tuple[float, ...],
) -> float:
    return intercept + sum(
        coefficient * value
        for coefficient, value in zip(coefficients, row, strict=True)
    )


def _probability_micros(raw: float) -> int:
    bounded = _clamp(raw, 0.0, 1.0)
    return int(round(bounded * 1_000_000))


def fit_temporal_hierarchy_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[TemporalHierarchyTrainingEpisode, ...],
    minimum_training_recall_bps: int = 9_500,
    ridge: float = 1.0,
) -> TemporalHierarchyModel:
    cutoff = _utc(fitted_at)
    if not 0 <= minimum_training_recall_bps <= 10_000:
        raise ValueError("minimum_training_recall_bps out of range")
    if ridge <= 0:
        raise ValueError("ridge must be positive")
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future training evidence beyond fitted_at")

    opposed = tuple(
        item
        for item in episodes
        if baseline_local_opposition(item.snapshot)
    )
    if len(opposed) < 50:
        raise ValueError("insufficient local-opposition training episodes")
    terminal_count = sum(item.terminal_failure for item in opposed)
    if terminal_count < 10:
        raise ValueError("insufficient terminal failures for hierarchy fit")

    names, first = _feature_vector(opposed[0].snapshot)
    raw_rows = [first]
    for item in opposed[1:]:
        row_names, row = _feature_vector(item.snapshot)
        if row_names != names:
            raise ValueError("temporal hierarchy feature schema drift")
        raw_rows.append(row)
    raw_rows_tuple = tuple(raw_rows)
    centers, scales = _standardization(raw_rows_tuple)
    rows = tuple(
        _standardize(row, centers, scales)
        for row in raw_rows_tuple
    )
    targets = tuple(
        1.0 if item.terminal_failure else 0.0
        for item in opposed
    )
    intercept, coefficients = _ridge_fit(rows, targets, ridge=ridge)

    centers_micros = tuple(
        int(round(value * 1_000_000))
        for value in centers
    )
    scales_micros = tuple(
        max(1, int(round(value * 1_000_000)))
        for value in scales
    )
    coefficients_micros = tuple(
        int(round(value * 1_000_000))
        for value in coefficients
    )
    intercept_micros = int(round(intercept * 1_000_000))

    frozen_centers = tuple(
        value / 1_000_000.0
        for value in centers_micros
    )
    frozen_scales = tuple(
        value / 1_000_000.0
        for value in scales_micros
    )
    frozen_coefficients = tuple(
        value / 1_000_000.0
        for value in coefficients_micros
    )
    frozen_intercept = intercept_micros / 1_000_000.0

    frozen_scores = tuple(
        _probability_micros(
            _predict_raw(
                intercept=frozen_intercept,
                coefficients=frozen_coefficients,
                row=_standardize(
                    raw_row,
                    frozen_centers,
                    frozen_scales,
                ),
            )
        )
        for raw_row in raw_rows_tuple
    )

    positive_scores = sorted(
        score
        for score, item in zip(frozen_scores, opposed, strict=True)
        if item.terminal_failure
    )
    calibration_recall_bps = max(minimum_training_recall_bps, 9_900)
    allowed_misses = (
        terminal_count * (10_000 - calibration_recall_bps) // 10_000
    )
    rank = min(len(positive_scores) - 1, allowed_misses)
    threshold = positive_scores[rank]

    return TemporalHierarchyModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        feature_names=names,
        feature_centers_micros=centers_micros,
        feature_scales_micros=scales_micros,
        coefficients_micros=coefficients_micros,
        intercept_micros=intercept_micros,
        declaration_threshold_micros=threshold,
        minimum_training_recall_bps=minimum_training_recall_bps,
        threshold_calibration_recall_bps=calibration_recall_bps,
        baseline_training_count=len(opposed),
        baseline_terminal_count=terminal_count,
    )


def assess_temporal_hierarchy(
    *,
    model: TemporalHierarchyModel,
    snapshot: TemporalHierarchySnapshot,
) -> TemporalHierarchyAssessment:
    names, raw = _feature_vector(snapshot)
    if names != model.feature_names:
        raise ValueError("temporal hierarchy runtime feature schema drift")
    centers = tuple(
        value / 1_000_000.0
        for value in model.feature_centers_micros
    )
    scales = tuple(
        value / 1_000_000.0
        for value in model.feature_scales_micros
    )
    coefficients = tuple(
        value / 1_000_000.0
        for value in model.coefficients_micros
    )
    row = _standardize(raw, centers, scales)
    score = _probability_micros(
        _predict_raw(
            intercept=model.intercept_micros / 1_000_000.0,
            coefficients=coefficients,
            row=row,
        )
    )
    opposed = baseline_local_opposition(snapshot)
    declared = opposed and score >= model.declaration_threshold_micros
    return TemporalHierarchyAssessment(
        episode_id=snapshot.episode_id,
        as_of=snapshot.as_of,
        baseline_local_opposition=opposed,
        failure_probability_micros=score,
        structural_failure_declared=declared,
        pullback_only=opposed and not declared,
    )


def evaluate_temporal_hierarchy(
    *,
    model: TemporalHierarchyModel,
    partition: str,
    episodes: tuple[TemporalHierarchyTrainingEpisode, ...],
) -> TemporalHierarchyEvaluation:
    opposed = tuple(
        item
        for item in episodes
        if baseline_local_opposition(item.snapshot)
    )
    baseline_terminals = sum(item.terminal_failure for item in opposed)
    baseline_false = len(opposed) - baseline_terminals

    hierarchy_terminal = 0
    hierarchy_false = 0
    hierarchy_declarations = 0
    missed = 0
    for item in opposed:
        assessment = assess_temporal_hierarchy(
            model=model,
            snapshot=item.snapshot,
        )
        if assessment.structural_failure_declared:
            hierarchy_declarations += 1
            if item.terminal_failure:
                hierarchy_terminal += 1
            else:
                hierarchy_false += 1
        elif item.terminal_failure:
            missed += 1

    false_reduction = (
        0
        if baseline_false <= 0
        else int(
            round(
                (baseline_false - hierarchy_false)
                / baseline_false
                * 10_000
            )
        )
    )
    preservation = (
        10_000
        if baseline_terminals <= 0
        else int(round(hierarchy_terminal / baseline_terminals * 10_000))
    )
    return TemporalHierarchyEvaluation(
        partition=partition,
        sample_count=len(episodes),
        baseline_declaration_count=len(opposed),
        baseline_terminal_count=baseline_terminals,
        baseline_false_declaration_count=baseline_false,
        hierarchy_declaration_count=hierarchy_declarations,
        hierarchy_terminal_count=hierarchy_terminal,
        hierarchy_false_declaration_count=hierarchy_false,
        hierarchy_missed_terminal_count=missed,
        false_declaration_reduction_bps=max(0, min(10_000, false_reduction)),
        terminal_detection_preservation_bps=max(0, min(10_000, preservation)),
    )
