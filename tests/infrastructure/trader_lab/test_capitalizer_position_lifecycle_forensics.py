from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import CapitalizerM5Bar
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_position_lifecycle_forensics import (
    CapitalizerLifecycleMode,
    _bar_indices,
    _simulate_trade,
    _state_family,
    _strict_prior_mfe_r,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
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


def _long_trade(
    *,
    entry_at: datetime,
    exit_at: datetime,
) -> CapitalizerR0Trade:
    return CapitalizerR0Trade(
        symbol="USDJPY",
        side=CapitalizerSide.LONG,
        signal_at=entry_at - timedelta(minutes=5),
        entry_at=entry_at,
        exit_at=exit_at,
        event_labels=("HIGH_ACCEPTANCE",),
        entry_price=Decimal("100"),
        stop_price=Decimal("99"),
        target_price=Decimal("105"),
        initial_risk_price=Decimal("1"),
        planned_reward_r=Decimal("5"),
        realized_gross_r=Decimal("-1"),
        exit_reason="STOP",
        bars_held=6,
        same_bar_stop_target_ambiguity=False,
    )


def test_profitable_swing_lock_uses_only_confirmed_prior_bar_information() -> None:
    start = datetime(2026, 1, 6, 1, 0, tzinfo=UTC)
    bars = (
        _bar(start, open_="100", high="100.8", low="99.8", close="100.6"),
        _bar(
            start + timedelta(minutes=5),
            open_="100.6",
            high="101.4",
            low="100.4",
            close="101.1",
        ),
        _bar(
            start + timedelta(minutes=10),
            open_="101.1",
            high="101.3",
            low="100.2",
            close="100.9",
        ),
        _bar(
            start + timedelta(minutes=15),
            open_="100.9",
            high="101.5",
            low="100.5",
            close="101.2",
        ),
        _bar(
            start + timedelta(minutes=20),
            open_="101.2",
            high="101.3",
            low="100.1",
            close="100.4",
        ),
        _bar(
            start + timedelta(minutes=25),
            open_="100.4",
            high="100.5",
            low="98.8",
            close="99.1",
        ),
    )
    trade = _long_trade(entry_at=bars[0].opened_at, exit_at=bars[-1].closed_at)
    by_open, _ = _bar_indices(bars)

    simulated = _simulate_trade(
        trade,
        bars=bars,
        by_open=by_open,
        mode=CapitalizerLifecycleMode.PROFITABLE_SWING_LOCK,
    )

    # The 100.2 swing is confirmed only after bar 3 closes, so it can protect bar 4.
    assert simulated.exit_at == bars[4].closed_at
    assert simulated.realized_gross_r == Decimal("0.2")
    assert simulated.exit_reason == "STOP"


def test_strict_prior_mfe_excludes_the_stop_bar() -> None:
    start = datetime(2026, 1, 6, 1, 0, tzinfo=UTC)
    bars = (
        _bar(start, open_="100", high="100.2", low="99.8", close="100.1"),
        _bar(
            start + timedelta(minutes=5),
            open_="100.1",
            high="104.0",
            low="98.9",
            close="99.2",
        ),
    )
    trade = CapitalizerR0Trade(
        symbol="USDJPY",
        side=CapitalizerSide.LONG,
        signal_at=start - timedelta(minutes=5),
        entry_at=bars[0].opened_at,
        exit_at=bars[1].closed_at,
        event_labels=("HIGH_ACCEPTANCE",),
        entry_price=Decimal("100"),
        stop_price=Decimal("99"),
        target_price=Decimal("105"),
        initial_risk_price=Decimal("1"),
        planned_reward_r=Decimal("5"),
        realized_gross_r=Decimal("-1"),
        exit_reason="STOP",
        bars_held=2,
        same_bar_stop_target_ambiguity=False,
    )
    by_open, by_close = _bar_indices(bars)

    assert _strict_prior_mfe_r(
        trade,
        bars=bars,
        by_open=by_open,
        by_close=by_close,
    ) == Decimal("0.2")


def test_state_family_separates_reclaim_from_rejection_route() -> None:
    start = datetime(2026, 1, 6, 1, 0, tzinfo=UTC)
    acceptance = _long_trade(
        entry_at=start,
        exit_at=start + timedelta(minutes=30),
    )
    state_index = {
        (acceptance.signal_at.isoformat(), acceptance.side): "RECLAIM_ALL_FRESH"
    }
    assert _state_family(acceptance, state_index) == "RECLAIM_ALL_FRESH"

    rejection = replace(
        acceptance,
        event_labels=("LOW_RAID_REJECTION",),
    )
    assert _state_family(rejection, {}) == "REJECTION_ROUTE"
