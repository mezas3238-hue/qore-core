"""WP-05 V3 semi-Markov hierarchy absorption / propagation model.

V1 classified one hierarchy snapshot. V2 modelled continuous trajectory
prototypes but remained unable to separate recoverable opposition from terminal
failure on R6/R5. V3 changes the representation rather than retuning V2.

V3 treats adversity as a front moving through ordered market scales. It models:
- the highest scale reached by the adverse front;
- advance, dwell, recession and re-propagation events;
- absorption when the front recedes while adverse mass falls;
- higher-scale resilience change;
- duration-conditioned terminal hazard with hierarchical state backoff.

Only R8 may fit hazards and the declaration threshold. Runtime projection uses
source-only hierarchy snapshots. Matured future terminal labels are offline
research targets only; no trader identity, symbol identity, PnL, methodology,
capital, Risk, order or execution authority is present.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import fmean

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchyEvaluation,
    TemporalHierarchySnapshot,
    TemporalScaleState,
    baseline_local_opposition,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
    TemporalHierarchyTrajectoryTrainingEpisode,
)

_ORDERED_SCALES = (
    WorldScale.M1,
    WorldScale.M3,
    WorldScale.M5,
    WorldScale.M15,
    WorldScale.H1,
    WorldScale.H4,
    WorldScale.DAILY,
)
_HIGH_SCALES = (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
_PRIOR_STRENGTH = 16


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _sign(value: int | float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _levels(
    snapshot: TemporalHierarchySnapshot,
) -> dict[WorldScale, TemporalScaleState]:
    return {item.scale: item for item in snapshot.levels}


def _anchor_sign(levels: dict[WorldScale, TemporalScaleState]) -> int:
    daily = levels.get(WorldScale.DAILY)
    if daily is not None and daily.direction_milli != 0:
        return _sign(daily.direction_milli)
    directions = [
        levels[scale].direction_milli
        for scale in _HIGH_SCALES
        if scale in levels and levels[scale].direction_milli != 0
    ]
    if not directions:
        return 0
    return _sign(fmean(directions))


@dataclass(frozen=True, slots=True)
class HierarchyFrontState:
    depth: int
    adverse_mass: int
    high_resilience: int


def _front_state(snapshot: TemporalHierarchySnapshot) -> HierarchyFrontState:
    levels = _levels(snapshot)
    anchor = _anchor_sign(levels)
    if anchor == 0:
        return HierarchyFrontState(depth=0, adverse_mass=0, high_resilience=0)

    depth = 0
    mass = 0
    for index, scale in enumerate(_ORDERED_SCALES, start=1):
        item = levels.get(scale)
        if item is None:
            continue
        adverse_direction = max(0, -anchor * item.direction_milli)
        if adverse_direction > 0:
            depth = max(depth, index)
        pressure = (
            10_000
            + item.fragility_bps
            + item.transition_bps
        )
        mass += adverse_direction * pressure

    high_rows = [levels[scale] for scale in _HIGH_SCALES if scale in levels]
    if not high_rows:
        resilience = 0
    else:
        resilience = int(
            round(
                fmean(
                    (
                        item.persistence_bps
                        + item.coherence_bps
                        - item.fragility_bps
                        - item.transition_bps
                        + 20_000
                    )
                    / 4
                    for item in high_rows
                )
            )
        )
    return HierarchyFrontState(
        depth=depth,
        adverse_mass=mass,
        high_resilience=resilience,
    )


@dataclass(frozen=True, slots=True)
class HierarchyAbsorptionSignature:
    current_depth: int
    maximum_depth: int
    frontier_trend: int
    advance_balance: int
    absorption_count: int
    repropagation_seen: int
    dwell_at_max: int
    current_high_breach: int
    adverse_mass_trend: int
    resilience_trend: int


def hierarchy_absorption_signature(
    trajectory: TemporalHierarchyTrajectory,
) -> HierarchyAbsorptionSignature:
    states = tuple(_front_state(snapshot) for snapshot in trajectory.snapshots)
    depths = tuple(state.depth for state in states)
    maximum = max(depths)

    advances = 0
    recessions = 0
    absorption = 0
    repropagation = False
    recession_seen = False
    for left, right in zip(states, states[1:], strict=False):
        if right.depth > left.depth:
            advances += 1
            if recession_seen:
                repropagation = True
        elif right.depth < left.depth:
            recessions += 1
            recession_seen = True
            if right.adverse_mass < left.adverse_mass:
                absorption += 1

    return HierarchyAbsorptionSignature(
        current_depth=depths[-1],
        maximum_depth=maximum,
        frontier_trend=_sign(depths[-1] - depths[0]),
        advance_balance=_sign(advances - recessions),
        absorption_count=min(absorption, 3),
        repropagation_seen=int(repropagation),
        dwell_at_max=min(sum(depth == maximum for depth in depths), 3),
        current_high_breach=int(depths[-1] >= 5),
        adverse_mass_trend=_sign(
            states[-1].adverse_mass - states[0].adverse_mass
        ),
        resilience_trend=_sign(
            states[-1].high_resilience - states[0].high_resilience
        ),
    )


def _keys(signature: HierarchyAbsorptionSignature) -> tuple[str, ...]:
    s = signature
    return (
        "L0|GLOBAL",
        f"L1|d={s.current_depth}|h={s.current_high_breach}",
        (
            f"L2|d={s.current_depth}|t={s.frontier_trend}"
            f"|h={s.current_high_breach}"
        ),
        (
            f"L3|d={s.current_depth}|t={s.frontier_trend}"
            f"|a={int(s.absorption_count > 0)}"
            f"|h={s.current_high_breach}"
        ),
        (
            f"L4|d={s.current_depth}|m={s.maximum_depth}"
            f"|t={s.frontier_trend}|a={int(s.absorption_count > 0)}"
            f"|r={s.repropagation_seen}|h={s.current_high_breach}"
        ),
        (
            f"L5|d={s.current_depth}|m={s.maximum_depth}"
            f"|t={s.frontier_trend}|b={s.advance_balance}"
            f"|a={s.absorption_count}|r={s.repropagation_seen}"
            f"|w={s.dwell_at_max}|h={s.current_high_breach}"
            f"|q={s.adverse_mass_trend}|s={s.resilience_trend}"
        ),
    )


@dataclass(frozen=True, slots=True)
class HierarchyHazardCell:
    level: int
    key: str
    support: int
    terminal_count: int
    hazard_micros: int

    def __post_init__(self) -> None:
        if not 0 <= self.level <= 5:
            raise ValueError("hazard level out of range")
        if not self.key:
            raise ValueError("hazard key must be non-empty")
        if self.support < 1:
            raise ValueError("hazard support must be positive")
        if not 0 <= self.terminal_count <= self.support:
            raise ValueError("terminal count exceeds support")
        if not 0 <= self.hazard_micros <= 1_000_000:
            raise ValueError("hazard probability out of range")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyAbsorptionModel:
    fitted_at: datetime
    fit_partition: str
    hazard_cells: tuple[HierarchyHazardCell, ...]
    declaration_threshold_micros: int
    minimum_training_recall_bps: int
    threshold_calibration_recall_bps: int
    fit_opposition_count: int
    fit_terminal_count: int
    minimum_cell_support: int
    prior_strength: int
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
        if self.fit_opposition_count < 1 or self.fit_terminal_count < 1:
            raise ValueError("fit population must contain terminal opposition")
        if not 1 <= self.minimum_cell_support <= self.fit_opposition_count:
            raise ValueError("invalid minimum cell support")
        if self.prior_strength < 1:
            raise ValueError("prior strength must be positive")
        if not 0 <= self.declaration_threshold_micros <= 1_000_000:
            raise ValueError("declaration threshold out of range")
        if not (
            0
            <= self.minimum_training_recall_bps
            <= self.threshold_calibration_recall_bps
            <= 10_000
        ):
            raise ValueError("invalid recall calibration")
        keys = [cell.key for cell in self.hazard_cells]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate hazard cells")
        if "L0|GLOBAL" not in keys:
            raise ValueError("global hazard cell missing")
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
            raise ValueError("absorption model carries forbidden authority")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyAbsorptionAssessment:
    episode_id: str
    as_of: datetime
    baseline_local_opposition: bool
    terminal_hazard_micros: int
    structural_failure_declared: bool
    recoverable_pullback: bool
    selected_state_level: int
    selected_state_support: int
    future_market_used: bool = False
    target_used: bool = False

    def __post_init__(self) -> None:
        _utc(self.as_of)
        if not 0 <= self.terminal_hazard_micros <= 1_000_000:
            raise ValueError("terminal hazard out of range")
        if self.structural_failure_declared and self.recoverable_pullback:
            raise ValueError("failure and recoverable pullback cannot coexist")
        if self.future_market_used or self.target_used:
            raise ValueError("runtime assessment uses forbidden evidence")


TemporalHierarchyAbsorptionEvaluation = TemporalHierarchyEvaluation


def _cell_map(
    model: TemporalHierarchyAbsorptionModel,
) -> dict[str, HierarchyHazardCell]:
    return {cell.key: cell for cell in model.hazard_cells}


def _score(
    model: TemporalHierarchyAbsorptionModel,
    trajectory: TemporalHierarchyTrajectory,
) -> tuple[int, int, int]:
    cells = _cell_map(model)
    keys = _keys(hierarchy_absorption_signature(trajectory))
    for level in range(5, 0, -1):
        cell = cells.get(keys[level])
        if cell is not None and cell.support >= model.minimum_cell_support:
            return cell.hazard_micros, level, cell.support
    global_cell = cells["L0|GLOBAL"]
    return global_cell.hazard_micros, 0, global_cell.support


def _threshold_for_recall(
    terminal_scores: list[int],
    minimum_recall_bps: int,
) -> int:
    if not terminal_scores:
        raise ValueError("threshold calibration requires terminal scores")
    ordered = sorted(terminal_scores)
    allowed_misses = (
        len(ordered) * (10_000 - minimum_recall_bps)
    ) // 10_000
    index = min(allowed_misses, len(ordered) - 1)
    return ordered[index]


def fit_temporal_hierarchy_absorption_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
    minimum_training_recall_bps: int = 9_500,
    minimum_cell_support: int = 12,
) -> TemporalHierarchyAbsorptionModel:
    cutoff = _utc(fitted_at)
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future training evidence is not allowed")

    opposition = tuple(
        item
        for item in episodes
        if baseline_local_opposition(item.trajectory.snapshots[-1])
    )
    terminals = sum(item.terminal_failure for item in opposition)
    if not opposition or terminals < 1:
        raise ValueError("fit requires baseline-opposition terminal evidence")
    if not 0 <= minimum_training_recall_bps <= 10_000:
        raise ValueError("minimum training recall out of range")
    if not 1 <= minimum_cell_support <= len(opposition):
        raise ValueError("minimum cell support out of range")

    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for item in opposition:
        for key in _keys(hierarchy_absorption_signature(item.trajectory)):
            counts[key][0] += 1
            counts[key][1] += int(item.terminal_failure)

    prior = terminals / len(opposition)
    cells = tuple(
        HierarchyHazardCell(
            level=int(key[1]),
            key=key,
            support=support,
            terminal_count=terminal_count,
            hazard_micros=int(
                round(
                    (
                        terminal_count + prior * _PRIOR_STRENGTH
                    )
                    / (support + _PRIOR_STRENGTH)
                    * 1_000_000
                )
            ),
        )
        for key, (support, terminal_count) in sorted(counts.items())
    )

    provisional = TemporalHierarchyAbsorptionModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        hazard_cells=cells,
        declaration_threshold_micros=0,
        minimum_training_recall_bps=minimum_training_recall_bps,
        threshold_calibration_recall_bps=10_000,
        fit_opposition_count=len(opposition),
        fit_terminal_count=terminals,
        minimum_cell_support=minimum_cell_support,
        prior_strength=_PRIOR_STRENGTH,
    )
    terminal_scores = [
        _score(provisional, item.trajectory)[0]
        for item in opposition
        if item.terminal_failure
    ]
    threshold = _threshold_for_recall(
        terminal_scores,
        minimum_training_recall_bps,
    )
    detected = sum(score >= threshold for score in terminal_scores)
    calibration_recall = detected * 10_000 // len(terminal_scores)

    return TemporalHierarchyAbsorptionModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        hazard_cells=cells,
        declaration_threshold_micros=threshold,
        minimum_training_recall_bps=minimum_training_recall_bps,
        threshold_calibration_recall_bps=calibration_recall,
        fit_opposition_count=len(opposition),
        fit_terminal_count=terminals,
        minimum_cell_support=minimum_cell_support,
        prior_strength=_PRIOR_STRENGTH,
    )


def assess_temporal_hierarchy_absorption(
    *,
    model: TemporalHierarchyAbsorptionModel,
    trajectory: TemporalHierarchyTrajectory,
) -> TemporalHierarchyAbsorptionAssessment:
    baseline = baseline_local_opposition(trajectory.snapshots[-1])
    if not baseline:
        return TemporalHierarchyAbsorptionAssessment(
            episode_id=trajectory.episode_id,
            as_of=trajectory.snapshots[-1].as_of,
            baseline_local_opposition=False,
            terminal_hazard_micros=0,
            structural_failure_declared=False,
            recoverable_pullback=False,
            selected_state_level=0,
            selected_state_support=model.fit_opposition_count,
        )

    hazard, level, support = _score(model, trajectory)
    declared = hazard >= model.declaration_threshold_micros
    return TemporalHierarchyAbsorptionAssessment(
        episode_id=trajectory.episode_id,
        as_of=trajectory.snapshots[-1].as_of,
        baseline_local_opposition=True,
        terminal_hazard_micros=hazard,
        structural_failure_declared=declared,
        recoverable_pullback=not declared,
        selected_state_level=level,
        selected_state_support=support,
    )


def evaluate_temporal_hierarchy_absorption(
    *,
    model: TemporalHierarchyAbsorptionModel,
    partition: str,
    episodes: tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
) -> TemporalHierarchyAbsorptionEvaluation:
    baseline_declarations = 0
    baseline_terminals = 0
    baseline_false = 0
    hierarchy_declarations = 0
    hierarchy_terminals = 0
    hierarchy_false = 0

    for item in episodes:
        baseline = baseline_local_opposition(item.trajectory.snapshots[-1])
        if baseline:
            baseline_declarations += 1
            if item.terminal_failure:
                baseline_terminals += 1
            else:
                baseline_false += 1

        assessment = assess_temporal_hierarchy_absorption(
            model=model,
            trajectory=item.trajectory,
        )
        if assessment.structural_failure_declared:
            hierarchy_declarations += 1
            if item.terminal_failure:
                hierarchy_terminals += 1
            else:
                hierarchy_false += 1

    missed = max(0, baseline_terminals - hierarchy_terminals)
    false_reduction = (
        0
        if baseline_false == 0
        else max(
            0,
            min(
                10_000,
                (baseline_false - hierarchy_false) * 10_000
                // baseline_false,
            ),
        )
    )
    terminal_preservation = (
        0
        if baseline_terminals == 0
        else max(
            0,
            min(
                10_000,
                hierarchy_terminals * 10_000 // baseline_terminals,
            ),
        )
    )
    return TemporalHierarchyAbsorptionEvaluation(
        partition=partition,
        sample_count=len(episodes),
        baseline_declaration_count=baseline_declarations,
        baseline_terminal_count=baseline_terminals,
        baseline_false_declaration_count=baseline_false,
        hierarchy_declaration_count=hierarchy_declarations,
        hierarchy_terminal_count=hierarchy_terminals,
        hierarchy_false_declaration_count=hierarchy_false,
        hierarchy_missed_terminal_count=missed,
        false_declaration_reduction_bps=false_reduction,
        terminal_detection_preservation_bps=terminal_preservation,
    )
