from __future__ import annotations

from qore.infrastructure.core_stack_v2.hierarchical_world_model import (
    DirectionalState,
    WorldLevelState,
    WorldScale,
    reconcile_world_levels,
)


def test_m1_bearish_against_h1_h4_bullish_is_pullback_not_reversal() -> None:
    state = reconcile_world_levels(
        (
            WorldLevelState(
                WorldScale.M1,
                DirectionalState.BEARISH,
                confidence_bps=8_000,
                persistence_bps=6_000,
                fragility_bps=4_000,
                transition_probability_bps=4_000,
            ),
            WorldLevelState(
                WorldScale.M5,
                DirectionalState.BEARISH,
                confidence_bps=7_000,
                persistence_bps=5_000,
                fragility_bps=4_500,
                transition_probability_bps=4_500,
            ),
            WorldLevelState(
                WorldScale.H1,
                DirectionalState.BULLISH,
                confidence_bps=8_500,
                persistence_bps=8_000,
                fragility_bps=2_500,
                transition_probability_bps=2_000,
            ),
            WorldLevelState(
                WorldScale.H4,
                DirectionalState.BULLISH,
                confidence_bps=8_000,
                persistence_bps=8_500,
                fragility_bps=2_000,
                transition_probability_bps=1_500,
            ),
        )
    )

    assert state.lower_timeframe_pullback_only is True
    assert state.structural_reversal_confirmed is False
    assert state.execution_authority is False


def test_opposed_lower_timeframe_plus_fragile_higher_timeframe_can_confirm_reversal() -> None:
    state = reconcile_world_levels(
        (
            WorldLevelState(
                WorldScale.M5,
                DirectionalState.BEARISH,
                confidence_bps=9_000,
                persistence_bps=8_000,
                fragility_bps=7_000,
                transition_probability_bps=8_000,
            ),
            WorldLevelState(
                WorldScale.H1,
                DirectionalState.BULLISH,
                confidence_bps=7_000,
                persistence_bps=4_000,
                fragility_bps=7_500,
                transition_probability_bps=7_000,
            ),
        )
    )

    assert state.structural_reversal_confirmed is True
