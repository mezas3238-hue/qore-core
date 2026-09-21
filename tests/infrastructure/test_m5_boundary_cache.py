from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from qore.infrastructure.m5_boundary_cache import (
    M5BoundaryCache,
    await_boundary_snapshots,
)


def _row(at: datetime, price: str) -> dict[str, object]:
    value = Decimal(price)
    return {
        "time": int(at.timestamp()),
        "open": float(value),
        "high": float(value + Decimal("0.010")),
        "low": float(value - Decimal("0.010")),
        "close": float(value),
    }


class _Api:
    TIMEFRAME_M5 = 5

    def __init__(
        self,
        rows: dict[str, list[dict[str, object]]],
        ticks: dict[str, datetime],
    ) -> None:
        self.rows = rows
        self.ticks = ticks
        self.copy_counts: dict[str, list[int]] = {
            symbol: [] for symbol in rows
        }

    def copy_rates_from_pos(
        self,
        symbol: str,
        _timeframe: int,
        _start: int,
        count: int,
    ) -> list[dict[str, object]]:
        self.copy_counts[symbol].append(count)
        return self.rows[symbol][-count:]

    def symbol_info(self, _symbol: str) -> SimpleNamespace:
        return SimpleNamespace(digits=3)

    def symbol_info_tick(self, symbol: str) -> SimpleNamespace:
        tick = self.ticks[symbol]
        return SimpleNamespace(
            time=int(tick.timestamp()),
            time_msc=int(tick.timestamp() * 1000),
        )


def test_shared_m5_cache_preloads_once_and_reads_only_recent_at_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import m5_boundary_cache as live

    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    anchor = datetime(2026, 9, 21, 9, 0, tzinfo=UTC)
    symbols = ("XAUUSD", "EURUSD", "GBPUSD", "GBPJPY", "AUDJPY")
    rows: dict[str, list[dict[str, object]]] = {}
    for offset, symbol in enumerate(symbols):
        start = anchor - timedelta(minutes=5 * 2000)
        rows[symbol] = [
            _row(
                start + timedelta(minutes=5 * index),
                str(Decimal("100") + Decimal(offset)),
            )
            for index in range(2000)
        ]
        rows[symbol].append(
            _row(anchor, str(Decimal("101") + Decimal(offset)))
        )

    api = _Api(
        rows,
        {symbol: anchor + timedelta(milliseconds=100) for symbol in symbols},
    )
    caches = {
        symbol: M5BoundaryCache(symbol=symbol, error_prefix=symbol)
        for symbol in symbols
    }
    for cache in caches.values():
        cache.preload(api, now=anchor - timedelta(seconds=10))

    snapshots = await_boundary_snapshots(
        api,
        caches=caches,
        anchor=anchor,
        now_fn=lambda: anchor + timedelta(milliseconds=250),
        sleep_fn=lambda _seconds: None,
    )

    assert set(snapshots) == set(symbols)
    assert all(
        snapshot.observed_at <= anchor + timedelta(seconds=2)
        for snapshot in snapshots.values()
    )
    assert all(cache.preload_calls == 1 for cache in caches.values())
    assert all(cache.incremental_calls == 1 for cache in caches.values())
    for symbol in symbols:
        assert api.copy_counts[symbol] == [15000, 4]


def test_shared_m5_boundary_fails_closed_after_two_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import m5_boundary_cache as live

    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    anchor = datetime(2026, 9, 21, 9, 0, tzinfo=UTC)
    start = anchor - timedelta(minutes=5 * 2000)
    rows = {
        "EURUSD": [
            _row(start + timedelta(minutes=5 * index), "1.100")
            for index in range(2000)
        ]
        + [_row(anchor, "1.101")]
    }
    api = _Api(rows, {"EURUSD": anchor})
    cache = M5BoundaryCache(symbol="EURUSD", error_prefix="R38 EURUSD")
    cache.preload(api, now=anchor - timedelta(seconds=10))

    with pytest.raises(TimeoutError, match="hard 2s SLA expired"):
        await_boundary_snapshots(
            api,
            caches={"EURUSD": cache},
            anchor=anchor,
            now_fn=lambda: anchor + timedelta(seconds=2, milliseconds=1),
            sleep_fn=lambda _seconds: None,
        )
