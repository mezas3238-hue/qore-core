from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.ict_turtle_soup_r1 import (
    DetectionStatus,
    ExitReason,
    M5Bar,
    Side,
    detect_ict_turtle_soup_r1,
    replay_ict_turtle_soup_r1,
)

NY = ZoneInfo("America/New_York")
D = Decimal


def _bar(local: datetime, open_: str, high: str, low: str, close: str) -> M5Bar:
    opened = local.replace(tzinfo=NY).astimezone(UTC)
    return M5Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=5),
        open=D(open_),
        high=D(high),
        low=D(low),
        close=D(close),
    )


def _base_day(*, london_high: str = "110", london_low: str = "100") -> list[M5Bar]:
    day = date(2026, 1, 15)
    high_bound = D(london_high)
    low_bound = D(london_low)
    price = (high_bound + low_bound) / D("2")
    bars: list[M5Bar] = []
    current = datetime.combine(day, datetime.min.time()).replace(hour=2)
    for index in range(36):
        high = high_bound if index == 4 else price + D("0.5")
        low = low_bound if index == 20 else price - D("0.5")
        bars.append(_bar(current, str(price), str(high), str(low), str(price)))
        current += timedelta(minutes=5)

    current = datetime.combine(day, datetime.min.time()).replace(hour=8, minute=30)
    for _ in range(30):
        bars.append(
            _bar(
                current,
                str(price),
                str(price + D("0.5")),
                str(price - D("0.5")),
                str(price),
            )
        )
        current += timedelta(minutes=5)
    return bars


def _replace_ny(bars: list[M5Bar], index: int, bar: M5Bar) -> None:
    ny_indices = [
        idx
        for idx, item in enumerate(bars)
        if item.opened_at.astimezone(NY).time().hour >= 8
    ]
    bars[ny_indices[index]] = bar


def _local_ny(index: int) -> datetime:
    return datetime(2026, 1, 15, 8, 30) + timedelta(minutes=5 * index)


def _long_signal_day() -> tuple[M5Bar, ...]:
    bars = _base_day()
    _replace_ny(bars, 0, _bar(_local_ny(0), "102", "102.2", "101.2", "101.5"))
    _replace_ny(bars, 1, _bar(_local_ny(1), "101.5", "101.7", "100.5", "100.8"))
    _replace_ny(bars, 2, _bar(_local_ny(2), "100.8", "101", "99.75", "100.5"))
    _replace_ny(bars, 3, _bar(_local_ny(3), "100.5", "102.7", "100.4", "102.5"))
    _replace_ny(bars, 4, _bar(_local_ny(4), "102.5", "103", "102", "102.8"))
    return tuple(bars)


def _short_signal_day() -> tuple[M5Bar, ...]:
    bars = _base_day()
    _replace_ny(bars, 0, _bar(_local_ny(0), "108", "108.7", "107.8", "108.5"))
    _replace_ny(bars, 1, _bar(_local_ny(1), "108.5", "109.4", "108.4", "109.2"))
    _replace_ny(bars, 2, _bar(_local_ny(2), "109.2", "110.25", "109", "109.5"))
    _replace_ny(bars, 3, _bar(_local_ny(3), "109.5", "109.7", "107.6", "107.8"))
    _replace_ny(bars, 4, _bar(_local_ny(4), "107.5", "108", "107", "107.4"))
    return tuple(bars)


def test_long_requires_sweep_reclaim_cisd_then_enters_next_bar() -> None:
    result = detect_ict_turtle_soup_r1("NAS100", _long_signal_day(), D("0.25"))

    assert result.status is DetectionStatus.SIGNAL
    assert result.signal is not None
    signal = result.signal
    assert signal.side is Side.LONG
    assert signal.sweep_at == _bar(_local_ny(2), "1", "1", "1", "1").opened_at
    assert signal.reclaim_at == _bar(_local_ny(2), "1", "1", "1", "1").closed_at
    assert signal.cisd_threshold == D("102")
    assert signal.cisd_at == _bar(_local_ny(3), "1", "1", "1", "1").closed_at
    assert signal.entry_at == _bar(_local_ny(4), "1", "1", "1", "1").opened_at
    assert signal.entry == D("102.5")
    assert signal.stop == D("99.50")
    assert signal.target == D("110")
    assert signal.projected_r == D("2.5")


def test_short_is_exact_mirror() -> None:
    result = detect_ict_turtle_soup_r1("SP500", _short_signal_day(), D("0.25"))

    assert result.status is DetectionStatus.SIGNAL
    assert result.signal is not None
    signal = result.signal
    assert signal.side is Side.SHORT
    assert signal.cisd_threshold == D("108")
    assert signal.entry == D("107.5")
    assert signal.stop == D("110.50")
    assert signal.target == D("100")
    assert signal.projected_r == D("2.5")


def test_sweep_without_cisd_abstains() -> None:
    bars = list(_long_signal_day())
    for index in range(3, 30):
        _replace_ny(
            bars,
            index,
            _bar(_local_ny(index), "101", "101.8", "100.5", "101.5"),
        )

    result = detect_ict_turtle_soup_r1("US30", tuple(bars), D("0.25"))

    assert result.status is DetectionStatus.NO_CISD
    assert result.signal is None


def test_projected_reward_below_one_point_five_r_abstains() -> None:
    bars = list(_base_day(london_high="104", london_low="100"))
    _replace_ny(bars, 0, _bar(_local_ny(0), "102", "102.2", "101.2", "101.5"))
    _replace_ny(bars, 1, _bar(_local_ny(1), "101.5", "101.7", "100.5", "100.8"))
    _replace_ny(bars, 2, _bar(_local_ny(2), "100.8", "101", "99.75", "100.5"))
    _replace_ny(bars, 3, _bar(_local_ny(3), "100.5", "102.7", "100.4", "102.5"))
    _replace_ny(bars, 4, _bar(_local_ny(4), "102.5", "103", "102", "102.8"))

    result = detect_ict_turtle_soup_r1("NAS100", tuple(bars), D("0.25"))

    assert result.status is DetectionStatus.INSUFFICIENT_PROJECTED_R
    assert result.signal is None


def test_missing_london_bar_fails_closed() -> None:
    bars = list(_long_signal_day())
    bars.pop(0)

    result = detect_ict_turtle_soup_r1("NAS100", tuple(bars), D("0.25"))

    assert result.status is DetectionStatus.DATA_INVALID
    assert result.signal is None


def test_same_m5_stop_and_target_is_stop_first() -> None:
    bars = list(_long_signal_day())
    result = detect_ict_turtle_soup_r1("NAS100", tuple(bars), D("0.25"))
    assert result.signal is not None
    _replace_ny(bars, 4, _bar(_local_ny(4), "102.5", "111", "99", "105"))

    trade = replay_ict_turtle_soup_r1(result.signal, tuple(bars))

    assert trade.exit_reason is ExitReason.STOP
    assert trade.exit_price == D("99.50")
    assert trade.gross_r == D("-1")


def test_gap_through_stop_keeps_adverse_open_slippage() -> None:
    bars = list(_long_signal_day())
    result = detect_ict_turtle_soup_r1("NAS100", tuple(bars), D("0.25"))
    assert result.signal is not None
    _replace_ny(bars, 4, _bar(_local_ny(4), "99", "100", "98", "99.5"))

    trade = replay_ict_turtle_soup_r1(result.signal, tuple(bars))

    assert trade.exit_reason is ExitReason.GAP_STOP
    assert trade.exit_price == D("99")
    assert trade.gross_r < D("-1")


def test_bar_rejects_non_five_minute_duration() -> None:
    opened = datetime(2026, 1, 15, 13, 30, tzinfo=UTC)
    with pytest.raises(ValueError, match="five-minute"):
        M5Bar(opened, opened + timedelta(minutes=4), D("1"), D("2"), D("0"), D("1"))
