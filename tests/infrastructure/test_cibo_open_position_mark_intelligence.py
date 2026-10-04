from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_open_position_mark_intelligence import (
    CiboPositionMarkRequest,
    observe_position_mark,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar


T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _bar(
    *,
    opened_minutes: int,
    closed_minutes: int,
    close: str,
) -> Bar:
    return Bar(
        opened_at=T0 + timedelta(minutes=opened_minutes),
        closed_at=T0 + timedelta(minutes=closed_minutes),
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
    )


def test_position_mark_uses_latest_fully_closed_bar_only() -> None:
    request = CiboPositionMarkRequest(
        signal_fingerprint="open-1",
        qore_symbol="EURUSD",
        observed_at=T0 + timedelta(minutes=10),
    )
    evidence = observe_position_mark(
        request,
        (
            _bar(opened_minutes=0, closed_minutes=5, close="100.2"),
            _bar(opened_minutes=5, closed_minutes=10, close="100.7"),
            _bar(opened_minutes=10, closed_minutes=15, close="101.3"),
        ),
    )

    assert evidence is not None
    assert evidence.mark_price == Decimal("100.7")
    assert evidence.source_bar_closed_at == request.observed_at
    assert evidence.outcome_used is False


def test_position_mark_ignores_future_closing_bar() -> None:
    request = CiboPositionMarkRequest(
        signal_fingerprint="open-2",
        qore_symbol="XAUUSD",
        observed_at=T0 + timedelta(minutes=7),
    )
    evidence = observe_position_mark(
        request,
        (
            _bar(opened_minutes=0, closed_minutes=5, close="2000"),
            _bar(opened_minutes=5, closed_minutes=10, close="2025"),
        ),
    )

    assert evidence is not None
    assert evidence.mark_price == Decimal("2000")


def test_position_mark_returns_none_without_causal_closed_bar() -> None:
    request = CiboPositionMarkRequest(
        signal_fingerprint="open-3",
        qore_symbol="NAS100",
        observed_at=T0 + timedelta(minutes=1),
    )

    assert observe_position_mark(
        request,
        (_bar(opened_minutes=0, closed_minutes=5, close="18000"),),
    ) is None
