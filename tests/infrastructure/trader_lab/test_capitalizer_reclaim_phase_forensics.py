from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
)
from qore.infrastructure.trader_lab.capitalizer_reclaim_phase_forensics import (
    _reclaim_phase,
)


def _trade() -> CapitalizerR0Trade:
    signal = datetime(2026, 1, 5, 3, 15, tzinfo=UTC)
    return CapitalizerR0Trade(
        symbol="USDJPY",
        side=CapitalizerSide.LONG,
        signal_at=signal,
        entry_at=signal,
        exit_at=signal + timedelta(minutes=5),
        event_labels=("HIGH_ACCEPTANCE",),
        entry_price=Decimal("100"),
        stop_price=Decimal("99"),
        target_price=Decimal("102"),
        initial_risk_price=Decimal("1"),
        planned_reward_r=Decimal("2"),
        realized_gross_r=Decimal("1"),
        exit_reason="TARGET",
        bars_held=1,
        same_bar_stop_target_ambiguity=False,
    )


def test_reclaim_strictly_before_is_separate_from_same_departure() -> None:
    trade = _trade()
    episode_index = {(trade.signal_at.isoformat(), trade.side): ("a",)}
    assert _reclaim_phase(
        trade,
        episode_index=episode_index,
        reclaim_times={
            "a": (
                trade.signal_at,
                trade.signal_at - timedelta(minutes=5),
            )
        },
    ) == "RECLAIM_STRICTLY_BEFORE"

    assert _reclaim_phase(
        trade,
        episode_index=episode_index,
        reclaim_times={"a": (trade.signal_at, trade.signal_at)},
    ) == "RECLAIM_AT_DEPARTURE"


def test_future_reclaim_is_not_available_to_cognition() -> None:
    trade = _trade()
    episode_index = {(trade.signal_at.isoformat(), trade.side): ("a",)}
    assert _reclaim_phase(
        trade,
        episode_index=episode_index,
        reclaim_times={
            "a": (
                trade.signal_at,
                trade.signal_at + timedelta(minutes=5),
            )
        },
    ) == "NO_RECLAIM_OBSERVED"
