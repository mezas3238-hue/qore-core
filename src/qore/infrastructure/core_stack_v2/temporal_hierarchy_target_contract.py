"""WP-05 structural-failure target-semantics audit.

WP-05 asks whether local adverse pressure becomes a genuine higher-timeframe
structural failure. The current historical target in the consumed lab is
oriented by the source M15 direction. This module makes the directional
semantics explicit so the research program can prove that its label points in
the same direction as the higher-timeframe structural thesis before spending
more modelling capacity.

This is an audit-only cognitive contract. It carries no methodology, sizing,
Risk, order, execution or knowledge-promotion authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalScaleState,
    baseline_local_opposition,
)

_HIGH_SCALES = (
    WorldScale.H1,
    WorldScale.H4,
    WorldScale.DAILY,
)


def _sign(value: float | int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _level_map(
    snapshot: TemporalHierarchySnapshot,
) -> dict[WorldScale, TemporalScaleState]:
    return {item.scale: item for item in snapshot.levels}


def higher_timeframe_anchor_direction(
    snapshot: TemporalHierarchySnapshot,
) -> int:
    """Return the direction used by the WP-05 baseline higher-timeframe state."""

    levels = _level_map(snapshot)
    values = [
        levels[scale].direction_milli
        for scale in _HIGH_SCALES
        if scale in levels
    ]
    if not values:
        return 0
    return _sign(fmean(values))


def m15_source_direction(snapshot: TemporalHierarchySnapshot) -> int:
    levels = _level_map(snapshot)
    level = levels.get(WorldScale.M15)
    return 0 if level is None else _sign(level.direction_milli)


@dataclass(frozen=True, slots=True)
class TemporalHierarchyTargetSemantics:
    baseline_local_opposition: bool
    m15_source_direction: int
    higher_timeframe_anchor_direction: int
    current_target_terminal_break_direction: int
    expected_structural_failure_break_direction: int
    directionally_identifiable: bool
    directionally_aligned: bool
    directionally_inverted: bool
    methodology_authority: bool = False
    knowledge_promotion_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "m15_source_direction",
            "higher_timeframe_anchor_direction",
            "current_target_terminal_break_direction",
            "expected_structural_failure_break_direction",
        ):
            if int(getattr(self, name)) not in (-1, 0, 1):
                raise ValueError(f"{name} must be -1, 0 or 1")
        if self.directionally_aligned and self.directionally_inverted:
            raise ValueError("target semantics cannot be aligned and inverted")
        if not self.directionally_identifiable and (
            self.directionally_aligned or self.directionally_inverted
        ):
            raise ValueError("unidentifiable target cannot be classified")
        if (
            self.methodology_authority
            or self.knowledge_promotion_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("target audit cannot carry trading authority")


def assess_temporal_hierarchy_target_semantics(
    snapshot: TemporalHierarchySnapshot,
) -> TemporalHierarchyTargetSemantics:
    """Audit whether the consumed terminal target matches WP-05 direction.

    The current consumed target declares terminal failure in the direction
    opposite M15:
      M15 positive -> downside break;
      M15 negative -> upside break.

    A higher-timeframe structural-failure target must instead point opposite
    the higher-timeframe anchor. The two definitions agree iff M15 and the
    higher-timeframe anchor have the same non-zero sign.
    """

    local_opposition = baseline_local_opposition(snapshot)
    m15 = m15_source_direction(snapshot)
    high = higher_timeframe_anchor_direction(snapshot)
    identifiable = m15 != 0 and high != 0
    current_break = -m15 if m15 else 0
    expected_break = -high if high else 0
    aligned = identifiable and current_break == expected_break
    inverted = identifiable and current_break == -expected_break
    return TemporalHierarchyTargetSemantics(
        baseline_local_opposition=local_opposition,
        m15_source_direction=m15,
        higher_timeframe_anchor_direction=high,
        current_target_terminal_break_direction=current_break,
        expected_structural_failure_break_direction=expected_break,
        directionally_identifiable=identifiable,
        directionally_aligned=aligned,
        directionally_inverted=inverted,
    )
