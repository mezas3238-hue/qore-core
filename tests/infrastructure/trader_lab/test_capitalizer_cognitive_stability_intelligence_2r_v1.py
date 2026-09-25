from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_stability_intelligence_2r_v1 as lab,
)


def test_empty_history_is_stable() -> None:
    state, dd, recent5, loss_streak, stop_streak = lab._state(())
    assert state is lab.StabilityState.STABLE
    assert str(dd) == "0"
    assert str(recent5) == "0"
    assert loss_streak == 0
    assert stop_streak == 0


def test_mode_mapping_is_monotonic_in_defensiveness() -> None:
    assert lab._selected_mode(lab.StabilityState.STABLE) == "ORIGINAL"
    assert (
        lab._selected_mode(lab.StabilityState.WATCH)
        == "M3_PROFITABLE_SWING_LOCK"
    )
    assert (
        lab._selected_mode(lab.StabilityState.DEFENSIVE)
        == "M3_SWING_IMPROVE"
    )
