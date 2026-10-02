"""WP-05 V4 terminal-safe recovery veto over temporal hierarchy motifs.

V3 proved that absorption carries signal, but a terminal classifier spent too
much recall to obtain that signal. V4 changes the decision architecture.

Baseline structural-failure declaration remains the default. Shared may veto
that declaration only when a source-only temporal motif has demonstrated a
high-purity recoverable history on R8. The model therefore learns recovery
safe-zones rather than terminal prototypes.

R8 is internally chronological:
- early R8 builds motif statistics;
- late R8 calibrates motif resolution / support / contamination constraints;
- the selected contract is then refit on all consumed R8 and frozen.

R6/R5 are falsification only. Runtime uses no future market, outcome, PnL,
trader/symbol identity, methodology, sizing, Risk, order or execution authority.
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

_ORDERED = (
    WorldScale.M1,
    WorldScale.M3,
    WorldScale.M5,
    WorldScale.M15,
    WorldScale.H1,
    WorldScale.H4,
    WorldScale.DAILY,
)
_HIGH = (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
_LEVELS = (1, 2, 3, 4, 5)
_SUPPORT_GRID = (8, 12, 20, 30, 50)
_CONTAMINATION_GRID_BPS = (100, 200, 300, 400, 500)
_CALIBRATION_TERMINAL_PRESERVATION_BPS = 9_700


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _sign(value: float | int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _map(snapshot: TemporalHierarchySnapshot) -> dict[WorldScale, TemporalScaleState]:
    return {row.scale: row for row in snapshot.levels}


def _anchor(levels: dict[WorldScale, TemporalScaleState]) -> int:
    daily = levels.get(WorldScale.DAILY)
    if daily is not None and daily.direction_milli != 0:
        return _sign(daily.direction_milli)
    values = [
        levels[scale].direction_milli
        for scale in _HIGH
        if scale in levels and levels[scale].direction_milli != 0
    ]
    return 0 if not values else _sign(fmean(values))


@dataclass(frozen=True, slots=True)
class RecoveryMotifSignature:
    depth_path: tuple[int, ...]
    current_depth: int
    maximum_depth: int
    current_below_max: int
    recession_count: int
    advance_count: int
    high_breach_count: int
    current_high_breach: int
    adverse_mass_trend: int
    high_resilience_trend: int
    h1_relative_path: tuple[int, ...]
    h4_relative_path: tuple[int, ...]


def _snapshot_state(
    snapshot: TemporalHierarchySnapshot,
) -> tuple[int, int, int, int, int]:
    levels = _map(snapshot)
    anchor = _anchor(levels)
    if anchor == 0:
        return 0, 0, 0, 0, 0
    depth = 0
    mass = 0
    for index, scale in enumerate(_ORDERED, start=1):
        item = levels.get(scale)
        if item is None:
            continue
        adverse = max(0, -anchor * item.direction_milli)
        if adverse > 0:
            depth = max(depth, index)
        mass += adverse * (
            10_000 + item.fragility_bps + item.transition_bps
        )
    high_rows = [levels[scale] for scale in _HIGH if scale in levels]
    resilience = (
        0
        if not high_rows
        else int(
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
    )
    h1 = levels.get(WorldScale.H1)
    h4 = levels.get(WorldScale.H4)
    h1_relative = (
        0 if h1 is None else _sign(anchor * h1.direction_milli)
    )
    h4_relative = (
        0 if h4 is None else _sign(anchor * h4.direction_milli)
    )
    return depth, mass, resilience, h1_relative, h4_relative


def recovery_motif_signature(
    trajectory: TemporalHierarchyTrajectory,
) -> RecoveryMotifSignature:
    states = tuple(_snapshot_state(item) for item in trajectory.snapshots)
    depths = tuple(item[0] for item in states)
    recession = sum(
        right < left
        for left, right in zip(depths, depths[1:], strict=False)
    )
    advance = sum(
        right > left
        for left, right in zip(depths, depths[1:], strict=False)
    )
    maximum = max(depths)
    return RecoveryMotifSignature(
        depth_path=depths,
        current_depth=depths[-1],
        maximum_depth=maximum,
        current_below_max=int(depths[-1] < maximum),
        recession_count=recession,
        advance_count=advance,
        high_breach_count=sum(depth >= 5 for depth in depths),
        current_high_breach=int(depths[-1] >= 5),
        adverse_mass_trend=_sign(states[-1][1] - states[0][1]),
        high_resilience_trend=_sign(states[-1][2] - states[0][2]),
        h1_relative_path=tuple(item[3] for item in states),
        h4_relative_path=tuple(item[4] for item in states),
    )


def _compress_path(values: tuple[int, ...]) -> str:
    compact: list[int] = []
    for value in values:
        if not compact or value != compact[-1]:
            compact.append(value)
    return ".".join(str(value) for value in compact)


def _motif_keys(signature: RecoveryMotifSignature) -> tuple[str, ...]:
    s = signature
    return (
        "L0|GLOBAL",
        (
            f"L1|d={s.current_depth}|m={s.maximum_depth}"
            f"|below={s.current_below_max}|hb={s.current_high_breach}"
        ),
        (
            f"L2|d={s.current_depth}|m={s.maximum_depth}"
            f"|rec={min(s.recession_count,2)}|adv={min(s.advance_count,2)}"
            f"|hb={s.current_high_breach}"
        ),
        (
            f"L3|shape={_compress_path(s.depth_path)}"
            f"|hb={s.high_breach_count}|curhb={s.current_high_breach}"
        ),
        (
            f"L4|shape={_compress_path(s.depth_path)}"
            f"|mass={s.adverse_mass_trend}|res={s.high_resilience_trend}"
            f"|below={s.current_below_max}"
        ),
        (
            f"L5|shape={_compress_path(s.depth_path)}"
            f"|h1={_compress_path(s.h1_relative_path)}"
            f"|h4={_compress_path(s.h4_relative_path)}"
            f"|mass={s.adverse_mass_trend}|res={s.high_resilience_trend}"
        ),
    )


@dataclass(frozen=True, slots=True)
class RecoveryMotifCell:
    level: int
    key: str
    support: int
    recovery_count: int
    terminal_count: int
    terminal_rate_bps: int

    def __post_init__(self) -> None:
        if not 0 <= self.level <= 5:
            raise ValueError("motif level out of range")
        if not self.key or self.support < 1:
            raise ValueError("motif cell must have identity/support")
        if self.recovery_count + self.terminal_count != self.support:
            raise ValueError("motif cell accounting mismatch")
        if not 0 <= self.terminal_rate_bps <= 10_000:
            raise ValueError("terminal contamination out of range")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyRecoveryVetoModel:
    fitted_at: datetime
    fit_partition: str
    selected_level: int
    minimum_cell_support: int
    maximum_terminal_contamination_bps: int
    calibration_false_reduction_bps: int
    calibration_terminal_preservation_bps: int
    fit_opposition_count: int
    fit_terminal_count: int
    motif_cells: tuple[RecoveryMotifCell, ...]
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
        if self.selected_level not in _LEVELS:
            raise ValueError("selected motif level out of range")
        if self.minimum_cell_support < 1:
            raise ValueError("minimum support must be positive")
        if not 0 <= self.maximum_terminal_contamination_bps <= 10_000:
            raise ValueError("contamination limit out of range")
        if self.fit_opposition_count < 1 or self.fit_terminal_count < 1:
            raise ValueError("fit evidence must contain terminal opposition")
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
            raise ValueError("recovery veto carries forbidden authority")


@dataclass(frozen=True, slots=True)
class TemporalHierarchyRecoveryVetoAssessment:
    episode_id: str
    as_of: datetime
    baseline_local_opposition: bool
    recovery_veto: bool
    structural_failure_declared: bool
    recoverable_pullback: bool
    motif_level: int
    motif_support: int
    motif_terminal_rate_bps: int
    future_market_used: bool = False
    target_used: bool = False

    def __post_init__(self) -> None:
        _utc(self.as_of)
        if self.recovery_veto and self.structural_failure_declared:
            raise ValueError("veto and declaration cannot coexist")
        if self.future_market_used or self.target_used:
            raise ValueError("runtime assessment uses forbidden evidence")


TemporalHierarchyRecoveryVetoEvaluation = TemporalHierarchyEvaluation


def _cells(
    episodes: tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
) -> dict[tuple[int, str], RecoveryMotifCell]:
    counts: dict[tuple[int, str], list[int]] = defaultdict(lambda: [0, 0])
    for item in episodes:
        if not baseline_local_opposition(item.trajectory.snapshots[-1]):
            continue
        keys = _motif_keys(recovery_motif_signature(item.trajectory))
        for level, key in enumerate(keys):
            counts[(level, key)][int(item.terminal_failure)] += 1

    result: dict[tuple[int, str], RecoveryMotifCell] = {}
    for (level, key), (recoveries, terminals) in counts.items():
        support = recoveries + terminals
        result[(level, key)] = RecoveryMotifCell(
            level=level,
            key=key,
            support=support,
            recovery_count=recoveries,
            terminal_count=terminals,
            terminal_rate_bps=terminals * 10_000 // support,
        )
    return result


def _eligible(
    *,
    cell: RecoveryMotifCell | None,
    support: int,
    contamination_bps: int,
) -> bool:
    return bool(
        cell is not None
        and cell.support >= support
        and cell.terminal_rate_bps <= contamination_bps
    )


def _evaluate_contract(
    *,
    cells: dict[tuple[int, str], RecoveryMotifCell],
    episodes: tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
    level: int,
    support: int,
    contamination_bps: int,
) -> tuple[int, int]:
    baseline_false = 0
    baseline_terminal = 0
    veto_false = 0
    veto_terminal = 0
    for item in episodes:
        if not baseline_local_opposition(item.trajectory.snapshots[-1]):
            continue
        if item.terminal_failure:
            baseline_terminal += 1
        else:
            baseline_false += 1
        key = _motif_keys(recovery_motif_signature(item.trajectory))[level]
        if _eligible(
            cell=cells.get((level, key)),
            support=support,
            contamination_bps=contamination_bps,
        ):
            if item.terminal_failure:
                veto_terminal += 1
            else:
                veto_false += 1

    reduction = (
        0
        if baseline_false == 0
        else veto_false * 10_000 // baseline_false
    )
    preservation = (
        0
        if baseline_terminal == 0
        else (baseline_terminal - veto_terminal) * 10_000 // baseline_terminal
    )
    return reduction, preservation


def fit_temporal_hierarchy_recovery_veto_model(
    *,
    fitted_at: datetime,
    fit_partition: str,
    episodes: tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
) -> TemporalHierarchyRecoveryVetoModel:
    cutoff = _utc(fitted_at)
    if any(_utc(item.observed_at) > cutoff for item in episodes):
        raise ValueError("future training evidence is not allowed")
    opposition = tuple(
        item
        for item in episodes
        if baseline_local_opposition(item.trajectory.snapshots[-1])
    )
    if len(opposition) < 100:
        raise ValueError("recovery-veto fit population is too small")
    terminals = sum(item.terminal_failure for item in opposition)
    if terminals < 1:
        raise ValueError("recovery-veto fit requires terminal evidence")

    ordered = tuple(sorted(opposition, key=lambda item: item.trajectory.snapshots[-1].as_of))
    split = max(1, min(len(ordered) - 1, len(ordered) * 7 // 10))
    discovery = ordered[:split]
    calibration = ordered[split:]
    discovery_cells = _cells(discovery)

    candidates: list[tuple[int, int, int, int, int]] = []
    for level in _LEVELS:
        for support in _SUPPORT_GRID:
            for contamination in _CONTAMINATION_GRID_BPS:
                reduction, preservation = _evaluate_contract(
                    cells=discovery_cells,
                    episodes=calibration,
                    level=level,
                    support=support,
                    contamination_bps=contamination,
                )
                if preservation >= _CALIBRATION_TERMINAL_PRESERVATION_BPS:
                    candidates.append(
                        (
                            reduction,
                            preservation,
                            level,
                            support,
                            contamination,
                        )
                    )
    if not candidates:
        raise ValueError("no terminal-safe R8 recovery-veto contract")

    # Maximize recoverable-false veto on late R8 while keeping a stricter 97%
    # terminal-preservation calibration buffer. Ties favor higher preservation,
    # coarser support and lower contamination.
    selected = max(
        candidates,
        key=lambda row: (
            row[0],
            row[1],
            row[3],
            -row[4],
            -row[2],
        ),
    )
    reduction, preservation, level, support, contamination = selected
    full_cells = _cells(opposition)

    return TemporalHierarchyRecoveryVetoModel(
        fitted_at=cutoff,
        fit_partition=fit_partition,
        selected_level=level,
        minimum_cell_support=support,
        maximum_terminal_contamination_bps=contamination,
        calibration_false_reduction_bps=reduction,
        calibration_terminal_preservation_bps=preservation,
        fit_opposition_count=len(opposition),
        fit_terminal_count=terminals,
        motif_cells=tuple(
            cell
            for (_level, _key), cell in sorted(full_cells.items())
            if _level == level
        ),
    )


def _model_cell_map(
    model: TemporalHierarchyRecoveryVetoModel,
) -> dict[str, RecoveryMotifCell]:
    return {cell.key: cell for cell in model.motif_cells}


def assess_temporal_hierarchy_recovery_veto(
    *,
    model: TemporalHierarchyRecoveryVetoModel,
    trajectory: TemporalHierarchyTrajectory,
) -> TemporalHierarchyRecoveryVetoAssessment:
    baseline = baseline_local_opposition(trajectory.snapshots[-1])
    if not baseline:
        return TemporalHierarchyRecoveryVetoAssessment(
            episode_id=trajectory.episode_id,
            as_of=trajectory.snapshots[-1].as_of,
            baseline_local_opposition=False,
            recovery_veto=False,
            structural_failure_declared=False,
            recoverable_pullback=False,
            motif_level=model.selected_level,
            motif_support=0,
            motif_terminal_rate_bps=10_000,
        )
    key = _motif_keys(recovery_motif_signature(trajectory))[model.selected_level]
    cell = _model_cell_map(model).get(key)
    veto = _eligible(
        cell=cell,
        support=model.minimum_cell_support,
        contamination_bps=model.maximum_terminal_contamination_bps,
    )
    return TemporalHierarchyRecoveryVetoAssessment(
        episode_id=trajectory.episode_id,
        as_of=trajectory.snapshots[-1].as_of,
        baseline_local_opposition=True,
        recovery_veto=veto,
        structural_failure_declared=not veto,
        recoverable_pullback=veto,
        motif_level=model.selected_level,
        motif_support=0 if cell is None else cell.support,
        motif_terminal_rate_bps=(
            10_000 if cell is None else cell.terminal_rate_bps
        ),
    )


def evaluate_temporal_hierarchy_recovery_veto(
    *,
    model: TemporalHierarchyRecoveryVetoModel,
    partition: str,
    episodes: tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...],
) -> TemporalHierarchyRecoveryVetoEvaluation:
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

        assessment = assess_temporal_hierarchy_recovery_veto(
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
    reduction = (
        0
        if baseline_false == 0
        else (baseline_false - hierarchy_false) * 10_000 // baseline_false
    )
    preservation = (
        0
        if baseline_terminals == 0
        else hierarchy_terminals * 10_000 // baseline_terminals
    )
    return TemporalHierarchyRecoveryVetoEvaluation(
        partition=partition,
        sample_count=len(episodes),
        baseline_declaration_count=baseline_declarations,
        baseline_terminal_count=baseline_terminals,
        baseline_false_declaration_count=baseline_false,
        hierarchy_declaration_count=hierarchy_declarations,
        hierarchy_terminal_count=hierarchy_terminals,
        hierarchy_false_declaration_count=hierarchy_false,
        hierarchy_missed_terminal_count=missed,
        false_declaration_reduction_bps=max(0, min(10_000, reduction)),
        terminal_detection_preservation_bps=max(
            0, min(10_000, preservation)
        ),
    )
