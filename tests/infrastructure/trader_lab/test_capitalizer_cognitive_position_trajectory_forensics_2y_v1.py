from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_position_trajectory_forensics_2y_v1 as trajectory,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import Pivot


def _bar(
    minute: int,
    *,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 9, minute, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal("1.2500"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def test_excursions_use_initial_risk_units() -> None:
    trade = {
        "entry_price": "1.2500",
        "stop_price": "1.2490",
        "side": "LONG",
    }
    prior = (
        _bar(0, high="1.2504", low="1.2498", close="1.2502"),
        _bar(1, high="1.2507", low="1.2495", close="1.2503"),
    )

    mfe, mae = trajectory._excursions(trade, prior)

    assert mfe == Decimal("0.7")
    assert mae == Decimal("0.5")


def test_profitable_m3_pivot_requires_confirmation_before_exit() -> None:
    trade = {
        "entry_at": "2026-01-05T09:00:00+00:00",
        "exit_at": "2026-01-05T09:10:00+00:00",
        "entry_price": "1.2500",
        "stop_price": "1.2490",
        "side": "LONG",
    }
    confirmed = datetime(2026, 1, 5, 9, 6, tzinfo=UTC)
    pivots = (
        Pivot(
            occurred_at=datetime(2026, 1, 5, 9, 3, tzinfo=UTC),
            confirmed_at=confirmed,
            price=Decimal("1.2502"),
            kind="LOW",
        ),
    )

    improving, profitable = trajectory._usable_pivots(
        trade,
        pivots=pivots,
        close_by_at={confirmed: Decimal("1.2506")},
    )

    assert improving == confirmed
    assert profitable == confirmed


def test_pivot_confirmed_at_exit_is_too_late() -> None:
    trade = {
        "entry_at": "2026-01-05T09:00:00+00:00",
        "exit_at": "2026-01-05T09:10:00+00:00",
        "entry_price": "1.2500",
        "stop_price": "1.2490",
        "side": "LONG",
    }
    exit_at = datetime(2026, 1, 5, 9, 10, tzinfo=UTC)
    pivots = (
        Pivot(
            occurred_at=datetime(2026, 1, 5, 9, 7, tzinfo=UTC),
            confirmed_at=exit_at,
            price=Decimal("1.2502"),
            kind="LOW",
        ),
    )

    improving, profitable = trajectory._usable_pivots(
        trade,
        pivots=pivots,
        close_by_at={exit_at: Decimal("1.2506")},
    )

    assert improving is None
    assert profitable is None
