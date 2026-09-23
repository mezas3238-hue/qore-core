from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from qore.infrastructure.m5_boundary_cache import (
    M5BoundaryCache,
    await_boundary_snapshots,
)
from qore.infrastructure.market_boundary_actor import (
    MarketBoundaryJob,
    evaluate_market_boundaries,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    build_daily,
    build_h1,
    build_h4,
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
        self.copy_counts: dict[str, list[int]] = {symbol: [] for symbol in rows}

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
        rows[symbol].append(_row(anchor, str(Decimal("101") + Decimal(offset))))

    api = _Api(
        rows,
        {symbol: anchor + timedelta(milliseconds=100) for symbol in symbols},
    )
    caches = {symbol: M5BoundaryCache(symbol=symbol, error_prefix=symbol) for symbol in symbols}
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
        snapshot.observed_at <= anchor + timedelta(seconds=2) for snapshot in snapshots.values()
    )
    assert all(cache.preload_calls == 1 for cache in caches.values())
    assert all(cache.incremental_calls == 1 for cache in caches.values())
    for symbol in symbols:
        assert api.copy_counts[symbol] == [15000, 4]
        snapshot = snapshots[symbol]
        assert snapshot.new_bar_first_seen_at == anchor + timedelta(milliseconds=250)
        assert snapshot.market_state_updated_at == anchor + timedelta(milliseconds=250)
        assert snapshot.aggregate_finished_at == anchor + timedelta(milliseconds=250)
        assert snapshot.h1 == build_h1(snapshot.complete_bars)
        assert snapshot.h4 == build_h4(snapshot.complete_bars)
        assert snapshot.d1 == build_daily(snapshot.h4)


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
        "EURUSD": [_row(start + timedelta(minutes=5 * index), "1.100") for index in range(2000)]
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


def test_ready_market_is_delivered_once_without_waiting_for_delayed_sibling(
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
        symbol: [_row(start + timedelta(minutes=5 * index), "1.100") for index in range(2000)]
        for symbol in ("READY", "DELAYED")
    }

    class DelayedApi(_Api):
        def __init__(self) -> None:
            super().__init__(rows, {symbol: anchor for symbol in rows})
            self.delayed_reads = 0

        def copy_rates_from_pos(
            self,
            symbol: str,
            timeframe: int,
            start_pos: int,
            count: int,
        ) -> list[dict[str, object]]:
            if symbol == "DELAYED" and count == 4:
                self.copy_counts[symbol].append(count)
                self.delayed_reads += 1
                if self.delayed_reads == 1:
                    return self.rows[symbol][:-1][-count:]
            return super().copy_rates_from_pos(symbol, timeframe, start_pos, count)

    api = DelayedApi()
    caches = {symbol: M5BoundaryCache(symbol=symbol, error_prefix=symbol) for symbol in rows}
    for cache in caches.values():
        cache.preload(api, now=anchor - timedelta(seconds=10))
    for symbol in rows:
        rows[symbol].append(_row(anchor, "1.101"))

    delivered: list[str] = []
    snapshots = await_boundary_snapshots(
        api,
        caches=caches,
        anchor=anchor,
        now_fn=lambda: anchor + timedelta(milliseconds=100),
        sleep_fn=lambda _seconds: None,
        on_snapshot=lambda symbol, _snapshot: delivered.append(symbol),
    )

    assert set(snapshots) == {"READY", "DELAYED"}
    assert delivered == ["READY", "DELAYED"]
    assert caches["READY"].incremental_calls == 1
    assert caches["DELAYED"].incremental_calls == 2


def test_resident_aggregates_remain_bit_equivalent_across_updates_and_eviction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import m5_boundary_cache as live

    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    start = datetime(2025, 10, 25, 0, 0, tzinfo=UTC)
    initial = 2_000
    rows = {
        "EURUSD": [
            _row(
                start + timedelta(minutes=5 * index),
                str(Decimal("1.10000") + Decimal(index % 37) / Decimal("100000")),
            )
            for index in range(initial)
        ]
    }
    api = _Api(rows, {"EURUSD": start})
    cache = M5BoundaryCache(
        symbol="EURUSD",
        error_prefix="R38 EURUSD",
        max_bars=initial,
    )
    cache.preload(api, now=start + timedelta(minutes=5 * (initial - 1)))

    for offset in range(1, 401):
        opened = start + timedelta(minutes=5 * (initial - 1 + offset))
        rows["EURUSD"].append(
            _row(
                opened,
                str(Decimal("1.10100") + Decimal(offset % 43) / Decimal("100000")),
            )
        )
        cache.refresh_incremental(api, now=opened, count=4)
        anchor = opened
        complete, h1, h4, d1 = cache.prepared_context(anchor=anchor)
        assert h1 == build_h1(complete)
        assert h4 == build_h4(complete)
        assert d1 == build_daily(h4)


def test_all_turtle_live_adapters_consume_resident_frames_without_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import (
        m5_boundary_cache as cache_module,
    )
    from qore.infrastructure import (
        r34_xauusd_live as xauusd,
    )
    from qore.infrastructure import (
        r38_eurusd_live as eurusd,
    )
    from qore.infrastructure import (
        r38_gbpjpy_live as gbpjpy,
    )
    from qore.infrastructure import (
        r42_audjpy_live as audjpy,
    )
    from qore.infrastructure import (
        r43_gbpusd_live as gbpusd,
    )

    monkeypatch.setattr(
        cache_module,
        "normalise_fundednext_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    monkeypatch.setattr(
        xauusd,
        "_normalise_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    for module in (eurusd, gbpusd, gbpjpy, audjpy):
        monkeypatch.setattr(
            module,
            "normalise_fundednext_server_epoch",
            lambda raw: datetime.fromtimestamp(raw, tz=UTC),
        )
    anchor = datetime(2026, 9, 21, 13, 0, tzinfo=UTC)
    symbols = ("XAUUSD", "EURUSD", "GBPUSD", "GBPJPY", "AUDJPY")
    rows = {
        symbol: [
            _row(anchor - timedelta(minutes=5 * (2_000 - index)), "100.000")
            for index in range(2_000)
        ]
        + [_row(anchor, "100.001")]
        for symbol in symbols
    }
    api = _Api(rows, {symbol: anchor for symbol in symbols})
    snapshots = {}
    for symbol in symbols:
        cache = M5BoundaryCache(symbol=symbol, error_prefix=symbol)
        cache.preload(api, now=anchor - timedelta(seconds=10))
        cache.refresh_incremental(api, now=anchor, count=4)
        snapshots[symbol] = cache.boundary_snapshot(
            api,
            anchor=anchor,
            observed_at=anchor + timedelta(milliseconds=100),
        )

    builders = {
        "R34_XAUUSD": lambda snapshot=None: xauusd.build_live_signal(
            api,
            now=anchor,
            cognitive={},
            state=xauusd.R34LiveState(),
            boundary_snapshot=snapshot,
        ),
        "R38_EURUSD": lambda snapshot=None: eurusd.build_live_signal(
            api,
            now=anchor,
            cognitive={},
            state=eurusd.R38LiveState(),
            boundary_snapshot=snapshot,
        ),
        "R43_GBPUSD": lambda snapshot=None: gbpusd.build_live_signal(
            api,
            now=anchor,
            memory_bundle=((), "", {}),
            state=gbpusd.R43LiveState(),
            boundary_snapshot=snapshot,
        ),
        "R38_GBPJPY": lambda snapshot=None: gbpjpy.build_live_signal(
            api,
            now=anchor,
            memory_bundle={},
            state=gbpjpy.R38GbpJpyLiveState(),
            boundary_snapshot=snapshot,
        ),
        "R42_AUDJPY": lambda snapshot=None: audjpy.build_live_signal(
            api,
            now=anchor,
            memory_bundle={},
            state=audjpy.R42AudJpyLiveState(),
            boundary_snapshot=snapshot,
        ),
    }
    identity_symbols = {
        "R34_XAUUSD": "XAUUSD",
        "R38_EURUSD": "EURUSD",
        "R43_GBPUSD": "GBPUSD",
        "R38_GBPJPY": "GBPJPY",
        "R42_AUDJPY": "AUDJPY",
    }

    for identity, build in builders.items():
        symbol = identity_symbols[identity]
        assert build(snapshots[symbol]) == build()

    latency_samples: dict[str, list[int]] = {identity: [] for identity in builders}
    for _ in range(10):
        results = evaluate_market_boundaries(
            tuple(
                MarketBoundaryJob(
                    identity=identity,
                    symbol=identity_symbols[identity],
                    evaluate=lambda build=build, symbol=identity_symbols[identity]: build(
                        snapshots[symbol]
                    ),
                )
                for identity, build in builders.items()
            )
        )
        for result in results:
            assert result.error is None
            latency_samples[result.identity].append(result.strategy_latency_ms)

    for samples in latency_samples.values():
        ordered = sorted(samples)
        p50 = ordered[int((len(ordered) - 1) * 0.50)]
        p95 = ordered[int((len(ordered) - 1) * 0.95)]
        p99 = ordered[int((len(ordered) - 1) * 0.99)]
        assert 0 <= p50 <= p95 <= p99 <= max(ordered) < 2_000

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("full historical aggregate entered live hot path")

    for module in (xauusd, eurusd, gbpusd, gbpjpy, audjpy):
        monkeypatch.setattr(module, "build_h1", forbidden)
        monkeypatch.setattr(module, "build_h4", forbidden)
        monkeypatch.setattr(module, "_live_setup", lambda **_kwargs: None)

    assert xauusd.build_live_signal(
        api,
        now=anchor,
        cognitive={},
        state=xauusd.R34LiveState(),
        boundary_snapshot=snapshots["XAUUSD"],
    ) == (None, "no-r34-certified-signal")
    assert eurusd.build_live_signal(
        api,
        now=anchor,
        cognitive={},
        state=eurusd.R38LiveState(),
        boundary_snapshot=snapshots["EURUSD"],
    ) == (None, "no-r38-certified-signal")
    assert gbpusd.build_live_signal(
        api,
        now=anchor,
        memory_bundle=((), "", {}),
        state=gbpusd.R43LiveState(),
        boundary_snapshot=snapshots["GBPUSD"],
    ) == (None, "no-r43-certified-signal")
    assert gbpjpy.build_live_signal(
        api,
        now=anchor,
        memory_bundle={},
        state=gbpjpy.R38GbpJpyLiveState(),
        boundary_snapshot=snapshots["GBPJPY"],
    ) == (None, "no-gbpjpy-r38-certified-signal")
    assert audjpy.build_live_signal(
        api,
        now=anchor,
        memory_bundle={},
        state=audjpy.R42AudJpyLiveState(),
        boundary_snapshot=snapshots["AUDJPY"],
    ) == (None, "no-audjpy-r42-certified-signal")


def test_provider_late_market_does_not_discard_ready_sibling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from qore.infrastructure import m5_boundary_cache as live

    monkeypatch.setattr(
        live,
        "normalise_fundednext_server_epoch",
        lambda raw: datetime.fromtimestamp(raw, tz=UTC),
    )
    anchor = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)
    start = anchor - timedelta(minutes=5 * 2000)
    rows = {
        symbol: [_row(start + timedelta(minutes=5 * index), "1.100") for index in range(2000)]
        for symbol in ("READY", "PROVIDER_LATE")
    }
    api = _Api(
        rows,
        {
            "READY": anchor + timedelta(milliseconds=100),
            "PROVIDER_LATE": anchor - timedelta(milliseconds=100),
        },
    )
    caches = {
        symbol: M5BoundaryCache(symbol=symbol, error_prefix=symbol)
        for symbol in rows
    }
    for cache in caches.values():
        cache.preload(api, now=anchor - timedelta(seconds=10))
    rows["READY"].append(_row(anchor, "1.101"))

    delivered: list[str] = []
    snapshots = await_boundary_snapshots(
        api,
        caches=caches,
        anchor=anchor,
        now_fn=lambda: anchor + timedelta(seconds=1, milliseconds=1),
        sleep_fn=lambda _seconds: None,
        on_snapshot=lambda symbol, _snapshot: delivered.append(symbol),
    )

    assert set(snapshots) == {"READY"}
    assert delivered == ["READY"]
    assert snapshots["READY"].observed_at < anchor + timedelta(seconds=2)
