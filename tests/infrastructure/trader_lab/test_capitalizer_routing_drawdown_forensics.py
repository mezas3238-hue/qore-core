from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
)
from qore.infrastructure.trader_lab.capitalizer_routing_drawdown_forensics import (
    _contributions,
    _max_drawdown_episode,
)


def _candidate(
    symbol: str,
    side: CapitalizerSide,
    *,
    at: datetime,
    minutes: int,
    realized: str,
) -> CapitalizerExposureCandidate:
    return CapitalizerExposureCandidate(
        symbol=symbol,
        side=side,
        signal_at=at,
        entry_at=at,
        exit_at=at + timedelta(minutes=minutes),
        event_labels=("HIGH_ACCEPTANCE",),
        planned_reward_r=Decimal("2"),
        state_family="NO_RECLAIM_FRESH",
        cisd_timing_state="ALL_WITHIN_H1",
        source_age_state="CURRENT_H1_SOURCE",
        boundary_type_state="PRIOR_HIGH_LOW_ONLY",
        reclaim_phase="NO_RECLAIM_OBSERVED",
        realized_r=Decimal(realized),
    )


def test_max_drawdown_reconstructs_exact_peak_to_trough_interval() -> None:
    base = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    winner = _candidate(
        "NAS100",
        CapitalizerSide.LONG,
        at=base,
        minutes=10,
        realized="2",
    )
    loss_one = _candidate(
        "USDCAD",
        CapitalizerSide.SHORT,
        at=base + timedelta(minutes=1),
        minutes=20,
        realized="-1",
    )
    loss_two = _candidate(
        "XAUUSD",
        CapitalizerSide.SHORT,
        at=base + timedelta(minutes=2),
        minutes=30,
        realized="-2",
    )
    recovery = _candidate(
        "NAS100",
        CapitalizerSide.LONG,
        at=base + timedelta(hours=1),
        minutes=10,
        realized="1",
    )

    peak, trough, drawdown, peak_trade, trough_trade, episode = (
        _max_drawdown_episode((winner, loss_one, loss_two, recovery))
    )

    assert peak == Decimal("2")
    assert trough == Decimal("-1")
    assert drawdown == Decimal("3")
    assert peak_trade == winner
    assert trough_trade == loss_two
    assert episode == (loss_one, loss_two)


def test_drawdown_contribution_keeps_session_side_and_ordinal() -> None:
    base = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
    first = _candidate(
        "NAS100",
        CapitalizerSide.LONG,
        at=base,
        minutes=10,
        realized="1",
    )
    second = _candidate(
        "USDCAD",
        CapitalizerSide.SHORT,
        at=base + timedelta(minutes=1),
        minutes=20,
        realized="-1",
    )
    third = _candidate(
        "XAUUSD",
        CapitalizerSide.SHORT,
        at=base + timedelta(minutes=2),
        minutes=30,
        realized="-2",
    )

    cells = _contributions(
        policy="MAX3_BASELINE",
        tie_policy="SYMBOL_ASC",
        selected=(first, second, third),
        episode=(second, third),
    )

    usdcad = next(cell for cell in cells if cell.symbol == "USDCAD")
    xauusd = next(cell for cell in cells if cell.symbol == "XAUUSD")
    assert usdcad.session == "NEW_YORK"
    assert usdcad.side == "SHORT"
    assert usdcad.ordinal == 2
    assert usdcad.total_r == "-1"
    assert xauusd.ordinal == 3
    assert xauusd.total_r == "-2"
