from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from threading import Lock

from qore.infrastructure.ctrader_demo_full_api import CTraderDemoFullApi


def _bare_api(*, started_at: datetime) -> CTraderDemoFullApi:
    api = CTraderDemoFullApi.__new__(CTraderDemoFullApi)
    api._spot_lock = Lock()
    api._resident_bars = {}
    api._resident_started_at = started_at
    api._history = {
        ("XAUUSD", 300): [
            {
                "utc_time": int(
                    datetime(2026, 9, 24, 11, 55, tzinfo=UTC).timestamp()
                ),
                "time": 0,
                "open": 99.0,
                "high": 101.0,
                "low": 98.0,
                "close": 100.0,
                "tick_volume": 10,
                "spread": 0,
                "real_volume": 0,
            }
        ]
    }
    api._canonical = lambda symbol: symbol  # type: ignore[method-assign]
    api.copy_rates_from_pos = lambda *args, **kwargs: (_ for _ in ()).throw(  # type: ignore[method-assign]
        AssertionError("resident hot path must not call historical transport")
    )
    return api


def test_resident_hotpath_builds_complete_m5_ohlc_without_network() -> None:
    api = _bare_api(
        started_at=datetime(2026, 9, 24, 11, 59, 30, tzinfo=UTC)
    )
    with api._spot_lock:
        api._update_resident_bars_locked(
            canonical="XAUUSD",
            observed=datetime(2026, 9, 24, 12, 0, 1, tzinfo=UTC),
            bid=Decimal("100"),
        )
        api._update_resident_bars_locked(
            canonical="XAUUSD",
            observed=datetime(2026, 9, 24, 12, 4, 59, tzinfo=UTC),
            bid=Decimal("105"),
        )
        api._update_resident_bars_locked(
            canonical="XAUUSD",
            observed=datetime(2026, 9, 24, 12, 5, 1, tzinfo=UTC),
            bid=Decimal("102"),
        )

    rows = api.copy_rates_from_pos_resident("XAUUSD", 300, 0, 3)
    assert rows is not None
    assert [row["utc_time"] for row in rows] == [
        int(datetime(2026, 9, 24, 11, 55, tzinfo=UTC).timestamp()),
        int(datetime(2026, 9, 24, 12, 0, tzinfo=UTC).timestamp()),
        int(datetime(2026, 9, 24, 12, 5, tzinfo=UTC).timestamp()),
    ]
    closed = rows[1]
    assert closed["open"] == 100.0
    assert closed["high"] == 105.0
    assert closed["low"] == 100.0
    assert closed["close"] == 105.0


def test_resident_hotpath_excludes_bar_started_before_runtime() -> None:
    api = _bare_api(
        started_at=datetime(2026, 9, 24, 12, 2, tzinfo=UTC)
    )
    with api._spot_lock:
        api._update_resident_bars_locked(
            canonical="XAUUSD",
            observed=datetime(2026, 9, 24, 12, 2, 1, tzinfo=UTC),
            bid=Decimal("100"),
        )
        api._update_resident_bars_locked(
            canonical="XAUUSD",
            observed=datetime(2026, 9, 24, 12, 5, 1, tzinfo=UTC),
            bid=Decimal("102"),
        )

    rows = api.copy_rates_from_pos_resident("XAUUSD", 300, 0, 2)
    assert rows is not None
    assert [row["utc_time"] for row in rows] == [
        int(datetime(2026, 9, 24, 11, 55, tzinfo=UTC).timestamp()),
        int(datetime(2026, 9, 24, 12, 5, tzinfo=UTC).timestamp()),
    ]
