from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.fundednext_realtime_market_data import (
    MARKET_DATA_SLA_SECONDS,
    FundedNextRealtimeMarketData,
    MarketDataSlaError,
)

_SERVER_TZ = ZoneInfo("Europe/Helsinki")


class _FakeClock:
    def __init__(self, now: datetime) -> None:
        self.value = now

    def now(self) -> datetime:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


def _server_epoch(value: datetime) -> int:
    local = value.astimezone(_SERVER_TZ)
    pseudo_utc = local.replace(tzinfo=None).replace(tzinfo=UTC)
    return int(pseudo_utc.timestamp())


def _row(opened_at: datetime) -> dict[str, object]:
    return {
        "time": _server_epoch(opened_at),
        "open": 1.1000,
        "high": 1.1005,
        "low": 1.0995,
        "close": 1.1002,
    }


class _FakeApi:
    TIMEFRAME_M5 = 5

    def __init__(
        self,
        *,
        clock: _FakeClock,
        anchor: datetime,
        boundary_delay_seconds: float,
        tick_lag_seconds: float = 0.0,
    ) -> None:
        self.clock = clock
        self.anchor = anchor
        self.boundary_delay_seconds = boundary_delay_seconds
        self.tick_lag_seconds = tick_lag_seconds
        first = anchor - timedelta(minutes=5 * 2_000)
        self.rows = tuple(
            _row(first + timedelta(minutes=5 * index))
            for index in range(2_001)
        )
        self.copy_counts: list[int] = []

    def copy_rates_from_pos(
        self,
        _symbol: str,
        _timeframe: int,
        _start: int,
        count: int,
    ) -> tuple[dict[str, object], ...]:
        self.copy_counts.append(count)
        boundary_available = (
            self.clock.now()
            >= self.anchor + timedelta(seconds=self.boundary_delay_seconds)
        )
        last_open = self.anchor if boundary_available else self.anchor - timedelta(minutes=5)
        available = tuple(
            row
            for row in self.rows
            if datetime.fromtimestamp(int(row["time"]), tz=UTC)
            <= datetime.fromtimestamp(_server_epoch(last_open), tz=UTC)
        )
        return available[-count:]

    def symbol_info_tick(self, _symbol: str) -> SimpleNamespace:
        observed = self.clock.now() - timedelta(seconds=self.tick_lag_seconds)
        return SimpleNamespace(time=_server_epoch(observed))


def _engine(clock: _FakeClock) -> FundedNextRealtimeMarketData:
    return FundedNextRealtimeMarketData(
        now_fn=clock.now,
        sleep_fn=clock.sleep,
        poll_seconds=0.05,
    )


def test_boundary_snapshot_waits_for_exact_bar_but_never_beyond_two_seconds() -> None:
    anchor = datetime(2026, 9, 18, 20, 0, tzinfo=UTC)
    clock = _FakeClock(anchor - timedelta(seconds=1))
    api = _FakeApi(
        clock=clock,
        anchor=anchor,
        boundary_delay_seconds=0.70,
    )
    engine = _engine(clock)
    engine.warm(api, symbol="EURUSD", history_bars=2_000)

    clock.value = anchor + timedelta(milliseconds=100)
    result = engine.prime_anchor_group(
        api,
        anchor=anchor,
        symbols={"EURUSD": 2_000},
    )
    assert result == {"EURUSD": None}

    snapshot = engine.snapshot(
        api,
        symbol="EURUSD",
        anchor=anchor,
        history_bars=2_000,
    )
    assert snapshot.current_rate.opened_at == anchor
    assert snapshot.closed_rates[-1].opened_at == anchor - timedelta(minutes=5)
    assert 0 <= (snapshot.captured_at - anchor).total_seconds() <= 2
    assert snapshot.tick_age_seconds <= 2

    assert api.copy_counts[0] == 2_000
    assert all(count == 8 for count in api.copy_counts[1:])


def test_late_boundary_bar_is_fail_closed_and_never_accepted_later() -> None:
    anchor = datetime(2026, 9, 18, 20, 0, tzinfo=UTC)
    clock = _FakeClock(anchor - timedelta(seconds=1))
    api = _FakeApi(
        clock=clock,
        anchor=anchor,
        boundary_delay_seconds=2.50,
    )
    engine = _engine(clock)
    engine.warm(api, symbol="GBPUSD", history_bars=2_000)

    clock.value = anchor + timedelta(milliseconds=100)
    result = engine.prime_anchor_group(
        api,
        anchor=anchor,
        symbols={"GBPUSD": 2_000},
    )
    assert result["GBPUSD"] is not None
    assert "within 2.0s" in str(result["GBPUSD"])

    calls_after_failure = len(api.copy_counts)
    clock.advance(1)
    with pytest.raises(MarketDataSlaError, match="within 2.0s"):
        engine.snapshot(
            api,
            symbol="GBPUSD",
            anchor=anchor,
            history_bars=2_000,
        )
    assert len(api.copy_counts) == calls_after_failure


def test_stale_tick_fails_closed_even_when_boundary_bars_exist() -> None:
    anchor = datetime(2026, 9, 18, 20, 0, tzinfo=UTC)
    clock = _FakeClock(anchor - timedelta(seconds=1))
    api = _FakeApi(
        clock=clock,
        anchor=anchor,
        boundary_delay_seconds=0.0,
        tick_lag_seconds=3.0,
    )
    engine = _engine(clock)
    engine.warm(api, symbol="XAUUSD", history_bars=2_000)

    clock.value = anchor + timedelta(milliseconds=100)
    result = engine.prime_anchor_group(
        api,
        anchor=anchor,
        symbols={"XAUUSD": 2_000},
    )
    assert result["XAUUSD"] is not None


def test_sla_cannot_be_relaxed_above_two_seconds() -> None:
    assert MARKET_DATA_SLA_SECONDS == 2.0
    with pytest.raises(ValueError, match=r"within \(0, 2\]"):
        FundedNextRealtimeMarketData(sla_seconds=2.01)
