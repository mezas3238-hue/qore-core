from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_r2_all_session import (
    DetectionStatus,
    LiquiditySide,
    M5Bar,
    QualifiedLiquidityPool,
    Side,
    detect_ict_turtle_soup_r2_event,
)

D = Decimal


def _bar(ts: datetime, open_: str, high: str, low: str, close: str) -> M5Bar:
    return M5Bar(
        opened_at=ts,
        closed_at=ts + timedelta(minutes=5),
        open=D(open_),
        high=D(high),
        low=D(low),
        close=D(close),
    )


def _long_event(start: datetime) -> tuple[M5Bar, ...]:
    return (
        _bar(start, "101.5", "101.7", "101.0", "101.2"),
        _bar(start + timedelta(minutes=5), "101.2", "101.3", "99.7", "100.4"),
        _bar(start + timedelta(minutes=10), "100.4", "102.0", "100.2", "101.9"),
        _bar(start + timedelta(minutes=15), "101.9", "102.4", "101.6", "102.1"),
    )


def _sellside(symbol: str, known_at: datetime) -> QualifiedLiquidityPool:
    return QualifiedLiquidityPool(
        pool_id="prev-day-low",
        symbol=symbol,
        family="previous-day",
        side=LiquiditySide.SELL_SIDE,
        level=D("100"),
        known_at=known_at,
    )


def _buyside(symbol: str, known_at: datetime, level: str = "106") -> QualifiedLiquidityPool:
    return QualifiedLiquidityPool(
        pool_id=f"target-{level}",
        symbol=symbol,
        family="previous-day",
        side=LiquiditySide.BUY_SIDE,
        level=D(level),
        known_at=known_at,
    )


def test_signal_is_valid_at_midnight_without_clock_filter() -> None:
    start = datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
    result = detect_ict_turtle_soup_r2_event(
        symbol="EURUSD",
        bars=_long_event(start),
        tick_size=D("0.1"),
        swept_pool=_sellside("EURUSD", start - timedelta(hours=2)),
        opposing_pools=(_buyside("EURUSD", start - timedelta(hours=2)),),
    )

    assert result.status is DetectionStatus.SIGNAL
    assert result.signal is not None
    assert result.signal.side is Side.LONG
    assert result.signal.entry_at == start + timedelta(minutes=15)


def test_signal_is_valid_in_afternoon_with_same_causal_rules() -> None:
    start = datetime(2026, 1, 15, 17, 0, tzinfo=UTC)
    result = detect_ict_turtle_soup_r2_event(
        symbol="XAUUSD",
        bars=_long_event(start),
        tick_size=D("0.1"),
        swept_pool=_sellside("XAUUSD", start - timedelta(hours=6)),
        opposing_pools=(_buyside("XAUUSD", start - timedelta(hours=6)),),
    )

    assert result.status is DetectionStatus.SIGNAL
    assert result.signal is not None
    assert result.signal.symbol == "XAUUSD"


def test_future_defined_target_is_rejected() -> None:
    start = datetime(2026, 1, 15, 8, 0, tzinfo=UTC)
    result = detect_ict_turtle_soup_r2_event(
        symbol="NAS100",
        bars=_long_event(start),
        tick_size=D("0.1"),
        swept_pool=_sellside("NAS100", start - timedelta(hours=1)),
        opposing_pools=(_buyside("NAS100", start + timedelta(hours=1)),),
    )

    assert result.status is DetectionStatus.NO_OPPOSING_TARGET
    assert result.signal is None


def test_no_cisd_means_no_trade() -> None:
    start = datetime(2026, 1, 15, 6, 0, tzinfo=UTC)
    bars = (
        _bar(start, "101.5", "101.7", "101.0", "101.2"),
        _bar(start + timedelta(minutes=5), "101.2", "101.3", "99.7", "100.4"),
        _bar(start + timedelta(minutes=10), "100.4", "101.0", "100.2", "100.8"),
        _bar(start + timedelta(minutes=15), "100.8", "101.1", "100.4", "100.9"),
    )
    result = detect_ict_turtle_soup_r2_event(
        symbol="GBPJPY",
        bars=bars,
        tick_size=D("0.1"),
        swept_pool=_sellside("GBPJPY", start - timedelta(hours=2)),
        opposing_pools=(_buyside("GBPJPY", start - timedelta(hours=2)),),
    )

    assert result.status is DetectionStatus.NO_CISD
    assert result.signal is None


def test_evidence_before_pool_known_fails_closed() -> None:
    start = datetime(2026, 1, 15, 3, 0, tzinfo=UTC)
    result = detect_ict_turtle_soup_r2_event(
        symbol="SP500",
        bars=_long_event(start),
        tick_size=D("0.1"),
        swept_pool=_sellside("SP500", start + timedelta(minutes=1)),
        opposing_pools=(_buyside("SP500", start - timedelta(hours=1)),),
    )

    assert result.status is DetectionStatus.DATA_INVALID
    assert result.signal is None
