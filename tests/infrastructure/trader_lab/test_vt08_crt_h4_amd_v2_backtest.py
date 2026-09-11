from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_crt_h4_amd_v2_backtest import (
    _source_window_bounds,
)

_NY = ZoneInfo("America/New_York")


def test_forex_source_h4_uses_ttrades_new_york_local_anchors() -> None:
    instant = datetime(2026, 7, 6, 14, 30, tzinfo=_NY).astimezone(UTC)
    opened, closed = _source_window_bounds("EURUSD", instant)
    assert opened.astimezone(_NY).hour == 13
    assert closed.astimezone(_NY).hour == 17


def test_index_source_h4_uses_ttrades_futures_new_york_local_anchors() -> None:
    instant = datetime(2026, 7, 6, 15, 30, tzinfo=_NY).astimezone(UTC)
    opened, closed = _source_window_bounds("NAS100", instant)
    assert opened.astimezone(_NY).hour == 14
    assert closed.astimezone(_NY).hour == 18


def test_source_windows_follow_dst_in_new_york_not_fixed_utc_offset() -> None:
    winter = datetime(2026, 1, 6, 10, 30, tzinfo=_NY).astimezone(UTC)
    summer = datetime(2026, 7, 6, 10, 30, tzinfo=_NY).astimezone(UTC)
    winter_open, _ = _source_window_bounds("NAS100", winter)
    summer_open, _ = _source_window_bounds("NAS100", summer)
    assert winter_open.hour == 15
    assert summer_open.hour == 14
