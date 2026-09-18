from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from qore.infrastructure.fundednext_vt08_realtime_market_data import (
    vt08_boundary_ready,
)

_SERVER_TZ = ZoneInfo("Europe/Helsinki")


def _server_epoch(value: datetime) -> int:
    local = value.astimezone(_SERVER_TZ)
    pseudo_utc = local.replace(tzinfo=None).replace(tzinfo=UTC)
    return int(pseudo_utc.timestamp())


class _Api:
    TIMEFRAME_M15 = 15

    def __init__(
        self,
        *,
        anchor: datetime,
        include_current: bool,
        tick_at: datetime,
    ) -> None:
        self.anchor = anchor
        self.include_current = include_current
        self.tick_at = tick_at

    def copy_rates_from_pos(
        self,
        _symbol: str,
        _timeframe: int,
        _start: int,
        _count: int,
    ) -> tuple[dict[str, int], ...]:
        opened = [self.anchor - timedelta(minutes=15)]
        opened.append(
            self.anchor
            if self.include_current
            else self.anchor - timedelta(minutes=30)
        )
        return tuple({"time": _server_epoch(item)} for item in opened)

    def symbol_info_tick(self, _symbol: str) -> SimpleNamespace:
        return SimpleNamespace(time=_server_epoch(self.tick_at))


def test_vt08_boundary_probe_accepts_exact_m15_and_fresh_tick() -> None:
    anchor = datetime(2026, 9, 18, 13, 0, tzinfo=UTC)
    api = _Api(
        anchor=anchor,
        include_current=True,
        tick_at=anchor + timedelta(milliseconds=400),
    )
    ready, reason = vt08_boundary_ready(
        api,
        symbol="GBPUSD",
        anchor=anchor,
        now_fn=lambda: anchor + timedelta(milliseconds=500),
    )
    assert ready is True
    assert reason is None


def test_vt08_boundary_probe_rejects_missing_current_m15() -> None:
    anchor = datetime(2026, 9, 18, 13, 0, tzinfo=UTC)
    api = _Api(
        anchor=anchor,
        include_current=False,
        tick_at=anchor + timedelta(milliseconds=400),
    )
    ready, reason = vt08_boundary_ready(
        api,
        symbol="AUDJPY",
        anchor=anchor,
        now_fn=lambda: anchor + timedelta(milliseconds=500),
    )
    assert ready is False
    assert reason is not None
    assert "exact M15 boundary unavailable" in reason


def test_vt08_boundary_probe_rejects_tick_older_than_two_seconds() -> None:
    anchor = datetime(2026, 9, 18, 13, 0, tzinfo=UTC)
    api = _Api(
        anchor=anchor,
        include_current=True,
        tick_at=anchor - timedelta(seconds=2, milliseconds=100),
    )
    ready, reason = vt08_boundary_ready(
        api,
        symbol="GBPJPY",
        anchor=anchor,
        now_fn=lambda: anchor,
    )
    assert ready is False
    assert reason is not None
    assert "tick stale" in reason
