from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import CapitalizerM5Bar
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import CapitalizerR0Trade
from qore.infrastructure.trader_lab.capitalizer_r0_root_cause_forensics import (
    _acceptance_state,
    _bars_by_close,
)


def _bar(
    opened_at: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM5Bar:
    return CapitalizerM5Bar(
        symbol="USDJPY",
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=100,
        digits=3,
    )


def _trade(signal_at: datetime) -> CapitalizerR0Trade:
    return CapitalizerR0Trade(
        symbol="USDJPY",
        side=CapitalizerSide.SHORT,
        signal_at=signal_at,
        entry_at=signal_at,
        exit_at=signal_at + timedelta(minutes=5),
        event_labels=("LOW_ACCEPTANCE",),
        entry_price=Decimal("99.70"),
        stop_price=Decimal("100.20"),
        target_price=Decimal("98.70"),
        initial_risk_price=Decimal("0.50"),
        planned_reward_r=Decimal("2"),
        realized_gross_r=Decimal("-1"),
        exit_reason="STOP",
        bars_held=1,
        same_bar_stop_target_ambiguity=False,
    )


def test_acceptance_state_uses_all_exact_h1_episodes_and_prior_m5_only() -> None:
    start = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    bars = (
        _bar(start, open_="100.10", high="100.20", low="100.00", close="100.10"),
        _bar(
            start + timedelta(minutes=5),
            open_="100.08",
            high="100.12",
            low="99.80",
            close="99.90",
        ),
        _bar(
            start + timedelta(minutes=10),
            open_="99.90",
            high="100.00",
            low="99.60",
            close="99.70",
        ),
    )
    trade = _trade(bars[2].closed_at)
    episode_index = {
        (trade.signal_at.isoformat(), trade.side): ("episode-a", "episode-b")
    }
    sequences = {
        "episode-a": (
            ("LIQUIDITY_RAID", trade.signal_at - timedelta(minutes=20)),
            ("RECLAIM", trade.signal_at - timedelta(minutes=10)),
            ("DEPARTURE_CONFIRMATION", trade.signal_at),
        ),
        "episode-b": (
            ("LIQUIDITY_RAID", trade.signal_at - timedelta(minutes=15)),
            ("DEPARTURE_CONFIRMATION", trade.signal_at),
        ),
    }

    state = _acceptance_state(
        trade=trade,
        bars=bars,
        by_close=_bars_by_close(bars),
        episode_index=episode_index,
        sequences=sequences,
    )
    assert state == "RECLAIM_MIXED_REPEAT"


def test_acceptance_state_rejects_future_journey_information() -> None:
    start = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    bars = (
        _bar(start, open_="100.10", high="100.20", low="100.00", close="100.10"),
        _bar(
            start + timedelta(minutes=5),
            open_="100.08",
            high="100.12",
            low="99.80",
            close="99.90",
        ),
        _bar(
            start + timedelta(minutes=10),
            open_="99.90",
            high="100.00",
            low="99.60",
            close="99.70",
        ),
    )
    trade = _trade(bars[2].closed_at)
    episode_index = {(trade.signal_at.isoformat(), trade.side): ("episode-a",)}
    sequences = {
        "episode-a": (
            ("LIQUIDITY_RAID", trade.signal_at - timedelta(minutes=10)),
            ("RECLAIM", trade.signal_at + timedelta(minutes=5)),
        )
    }

    with pytest.raises(ValueError, match="future journey state"):
        _acceptance_state(
            trade=trade,
            bars=bars,
            by_close=_bars_by_close(bars),
            episode_index=episode_index,
            sequences=sequences,
        )
