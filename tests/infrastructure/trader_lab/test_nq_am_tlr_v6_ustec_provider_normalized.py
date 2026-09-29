from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar
from qore.infrastructure.trader_lab.nq_am_tlr_v6_ustec_provider_normalized import (
    FINAL_WINDOW_CLOSE,
    FINAL_WINDOW_OPEN,
    build_provider_rth_sessions,
)


def _bar(
    hour: int,
    minute: int,
    *,
    price: str = "100",
) -> Bar:
    opened = datetime(2016, 11, 11, hour, minute, tzinfo=UTC)
    value = Decimal(price)
    return Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=value,
        high=value + 1,
        low=value - 1,
        close=value,
    )


def test_provider_final_window_is_frozen() -> None:
    assert FINAL_WINDOW_OPEN.hour == 15
    assert FINAL_WINDOW_OPEN.minute == 30
    assert FINAL_WINDOW_CLOSE.hour == 16
    assert FINAL_WINDOW_CLOSE.minute == 30


def test_provider_session_uses_latest_available_bar_not_synthetic_1614() -> None:
    # 2016-11-11 is EST, so 14:30 UTC = 09:30 NY and 20:58 UTC = 15:58 NY.
    bars = (
        _bar(14, 30, price="100"),
        _bar(20, 55, price="101"),
        _bar(20, 58, price="102"),
    )
    sessions = build_provider_rth_sessions(bars)
    assert len(sessions) == 1
    session = sessions[0]
    assert session.open == Decimal("100")
    assert session.settle == Decimal("102")
    assert session.settle_at == bars[-1].opened_at


def test_provider_normalization_does_not_invent_missing_final_bar() -> None:
    bars = (
        _bar(14, 30, price="100"),
        _bar(19, 0, price="101"),
    )
    assert build_provider_rth_sessions(bars) == ()
