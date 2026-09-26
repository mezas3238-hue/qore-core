from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)


def _row(value: str, *, exit_at: str) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T10:00:00+00:00",
        exit_at=exit_at,
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r=value,
        exit_reason="STOP" if Decimal(value) < 0 else "TARGET",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def test_stability_state_uses_current_not_historical_max_drawdown() -> None:
    history = (
        _row("2", exit_at="2026-01-05T10:05:00+00:00"),
        _row("-1", exit_at="2026-01-05T10:06:00+00:00"),
        _row("-1", exit_at="2026-01-05T10:07:00+00:00"),
        _row("2", exit_at="2026-01-05T10:08:00+00:00"),
    )
    state, equity, peak, current_dd, loss_streak = governor._state(history)
    assert equity == Decimal("2")
    assert peak == Decimal("2")
    assert current_dd == Decimal("0")
    assert loss_streak == 0
    assert state is governor.StabilityState.STABLE


def test_defensive_state_after_three_closed_losses() -> None:
    history = (
        _row("-1", exit_at="2026-01-05T10:05:00+00:00"),
        _row("-1", exit_at="2026-01-05T10:06:00+00:00"),
        _row("-1", exit_at="2026-01-05T10:07:00+00:00"),
    )
    state, _equity, _peak, dd, streak = governor._state(history)
    assert state is governor.StabilityState.DEFENSIVE
    assert dd == Decimal("3")
    assert streak == 3


def test_all_policies_define_every_state() -> None:
    for mapping in governor.POLICIES.values():
        assert set(mapping) == set(governor.StabilityState)
