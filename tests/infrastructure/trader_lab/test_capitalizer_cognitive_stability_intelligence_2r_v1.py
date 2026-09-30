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


def _outcome(entry: str, exit_: str, r: str) -> lab.TradeOutcome:
    return lab.TradeOutcome(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date="2026-01-05",
        side="LONG",
        entry_at=entry,
        exit_at=exit_,
        realized_gross_r=r,
        exit_reason="TARGET" if not r.startswith("-") else "STOP",
        mode="ORIGINAL",
    )


def test_stability_uses_current_not_historical_max_drawdown() -> None:
    history = (
        _outcome(
            "2026-01-05T10:00:00+00:00",
            "2026-01-05T10:10:00+00:00",
            "-1",
        ),
        _outcome(
            "2026-01-05T10:20:00+00:00",
            "2026-01-05T10:30:00+00:00",
            "-1",
        ),
        _outcome(
            "2026-01-05T10:40:00+00:00",
            "2026-01-05T10:50:00+00:00",
            "2",
        ),
    )
    state, current_dd, _, loss_streak, stop_streak = lab._state(history)
    assert str(current_dd) == "0"
    assert loss_streak == 0
    assert stop_streak == 0
    assert state is lab.StabilityState.STABLE
