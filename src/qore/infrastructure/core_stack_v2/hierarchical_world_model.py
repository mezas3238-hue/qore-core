"""Hierarchical multi-timescale world model for Shared Core.

Each temporal level owns its own state and transition belief. The hierarchy
reconciles levels without collapsing lower-timeframe pressure into an
unsupported higher-timeframe regime reversal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorldScale(StrEnum):
    MICROSTRUCTURE = "MICROSTRUCTURE"
    SECONDS = "SECONDS"
    M1 = "M1"
    M3 = "M3"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    CROSS_MARKET_REGIME = "CROSS_MARKET_REGIME"
    MACRO_REGIME = "MACRO_REGIME"


class DirectionalState(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    CONTESTED = "CONTESTED"


@dataclass(frozen=True, slots=True)
class WorldLevelState:
    scale: WorldScale
    directional_state: DirectionalState
    confidence_bps: int
    persistence_bps: int
    fragility_bps: int
    transition_probability_bps: int

    def __post_init__(self) -> None:
        for name in (
            "confidence_bps",
            "persistence_bps",
            "fragility_bps",
            "transition_probability_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class HierarchicalWorldState:
    levels: tuple[WorldLevelState, ...]
    cross_level_coherence_bps: int
    contradiction_bps: int
    structural_reversal_confirmed: bool
    lower_timeframe_pullback_only: bool
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        if len({level.scale for level in self.levels}) != len(self.levels):
            raise ValueError("world scales must be unique")
        for name in ("cross_level_coherence_bps", "contradiction_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("hierarchical world state cannot carry trading authority")


_SCALE_WEIGHT: dict[WorldScale, int] = {
    WorldScale.MICROSTRUCTURE: 1,
    WorldScale.SECONDS: 1,
    WorldScale.M1: 2,
    WorldScale.M3: 2,
    WorldScale.M5: 3,
    WorldScale.M15: 4,
    WorldScale.H1: 5,
    WorldScale.H4: 6,
    WorldScale.DAILY: 7,
    WorldScale.WEEKLY: 8,
    WorldScale.CROSS_MARKET_REGIME: 5,
    WorldScale.MACRO_REGIME: 7,
}


def reconcile_world_levels(
    levels: tuple[WorldLevelState, ...],
) -> HierarchicalWorldState:
    """Reconcile multi-timescale states conservatively."""

    if len(levels) < 2:
        raise ValueError("hierarchical world model requires multiple levels")

    directional = [
        level
        for level in levels
        if level.directional_state
        in {DirectionalState.BULLISH, DirectionalState.BEARISH}
    ]
    if not directional:
        return HierarchicalWorldState(
            levels=levels,
            cross_level_coherence_bps=0,
            contradiction_bps=10_000,
            structural_reversal_confirmed=False,
            lower_timeframe_pullback_only=False,
        )

    weighted_total = 0
    signed_total = 0
    high_timeframe = []
    low_timeframe = []
    for level in directional:
        weight = _SCALE_WEIGHT[level.scale] * level.confidence_bps
        sign = 1 if level.directional_state is DirectionalState.BULLISH else -1
        weighted_total += weight
        signed_total += sign * weight
        if level.scale in {
            WorldScale.H1,
            WorldScale.H4,
            WorldScale.DAILY,
            WorldScale.WEEKLY,
            WorldScale.MACRO_REGIME,
        }:
            high_timeframe.append(level)
        else:
            low_timeframe.append(level)

    coherence = (
        0
        if weighted_total <= 0
        else min(10_000, abs(signed_total) * 10_000 // weighted_total)
    )
    contradiction = 10_000 - coherence

    high_direction = None
    if high_timeframe:
        high_score = sum(
            (
                1 if level.directional_state is DirectionalState.BULLISH else -1
            )
            * _SCALE_WEIGHT[level.scale]
            * level.confidence_bps
            for level in high_timeframe
        )
        high_direction = (
            DirectionalState.BULLISH
            if high_score > 0
            else DirectionalState.BEARISH
            if high_score < 0
            else DirectionalState.CONTESTED
        )

    low_direction = None
    if low_timeframe:
        low_score = sum(
            (
                1 if level.directional_state is DirectionalState.BULLISH else -1
            )
            * _SCALE_WEIGHT[level.scale]
            * level.confidence_bps
            for level in low_timeframe
        )
        low_direction = (
            DirectionalState.BULLISH
            if low_score > 0
            else DirectionalState.BEARISH
            if low_score < 0
            else DirectionalState.CONTESTED
        )

    higher_fragility = max(
        (level.fragility_bps for level in high_timeframe),
        default=0,
    )
    higher_transition = max(
        (level.transition_probability_bps for level in high_timeframe),
        default=0,
    )
    opposed = (
        high_direction
        in {DirectionalState.BULLISH, DirectionalState.BEARISH}
        and low_direction
        in {DirectionalState.BULLISH, DirectionalState.BEARISH}
        and high_direction is not low_direction
    )
    structural_reversal = (
        opposed
        and higher_fragility >= 6_500
        and higher_transition >= 6_500
        and contradiction >= 4_000
    )
    pullback_only = opposed and not structural_reversal

    return HierarchicalWorldState(
        levels=levels,
        cross_level_coherence_bps=coherence,
        contradiction_bps=contradiction,
        structural_reversal_confirmed=structural_reversal,
        lower_timeframe_pullback_only=pullback_only,
    )
