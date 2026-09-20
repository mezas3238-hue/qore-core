from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_cibo_10y_m1_clone_v1 import (
    IDENTITY as CLONE_IDENTITY,
    PERIOD_M1,
    TARGET_END_EXCLUSIVE,
    TARGET_START,
    TARGET_SYMBOLS,
    _year_partitions,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_native_m1_entry_replay_v1 import (
    IDENTITY,
    _find_entry,
    _lifecycle,
)


def _bar(
    index: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 5, 7, 0, tzinfo=UTC) + timedelta(minutes=index)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def _long_pattern() -> tuple[CapitalizerM1Bar, ...]:
    return (
        _bar(0, open_="100", high="101", low="99.5", close="100.5"),
        _bar(1, open_="100.5", high="101", low="100", close="100.8"),
        _bar(2, open_="100.8", high="103", low="100.5", close="102"),
        _bar(3, open_="101.8", high="102", low="101.5", close="101.9"),
        _bar(4, open_="101.9", high="102", low="101", close="101.2"),
        _bar(5, open_="101.2", high="104.5", low="101.1", close="104"),
        _bar(6, open_="104", high="104.2", low="102.5", close="103.5"),
        _bar(7, open_="103.5", high="103.6", low="101.8", close="102.4"),
        _bar(8, open_="102.4", high="106.5", low="102.2", close="106"),
    )


def test_native_m1_entry_requires_mss_fvg_ob_then_retest() -> None:
    bars = _long_pattern()
    setup, entry_index, entry_price, reason = _find_entry(
        bars,
        signal_at=bars[4].opened_at,
        side=CapitalizerSide.LONG,
        target=Decimal("106"),
    )

    assert reason == "M1_ENTRY_CONFIRMED"
    assert setup is not None
    assert entry_index == 7
    assert entry_price == Decimal("102")
    assert setup.mss_level == Decimal("103")
    assert setup.fvg_low == Decimal("102")
    assert setup.fvg_high == Decimal("102.5")
    assert setup.order_block_low == Decimal("101")
    assert setup.order_block_high == Decimal("102")
    assert setup.protected_swing == Decimal("101")


def test_missing_m1_order_block_is_fail_closed() -> None:
    bars = list(_long_pattern())
    original = bars[4]
    bars[4] = CapitalizerM1Bar(
        symbol=original.symbol,
        opened_at=original.opened_at,
        closed_at=original.closed_at,
        open=Decimal("101.2"),
        high=Decimal("102"),
        low=Decimal("101"),
        close=Decimal("101.9"),
        volume=None,
        digits=5,
    )
    setup, entry_index, entry_price, reason = _find_entry(
        tuple(bars),
        signal_at=bars[4].opened_at,
        side=CapitalizerSide.LONG,
        target=Decimal("106"),
    )

    assert setup is None
    assert entry_index is None
    assert entry_price is None
    assert reason == "M1_ORDER_BLOCK_NOT_CONFIRMED"


def test_native_m1_lifecycle_uses_structural_ob_extreme_stop() -> None:
    bars = _long_pattern()
    setup, entry_index, entry_price, _ = _find_entry(
        bars,
        signal_at=bars[4].opened_at,
        side=CapitalizerSide.LONG,
        target=Decimal("106"),
    )
    assert setup is not None and entry_index is not None and entry_price is not None

    realized, reason, held, ambiguous, exit_at = _lifecycle(
        bars,
        entry_index=entry_index,
        side=CapitalizerSide.LONG,
        entry_price=entry_price,
        stop_price=setup.protected_swing,
        target_price=Decimal("106"),
    )

    assert realized == Decimal("4")
    assert reason == "TARGET"
    assert held == 2
    assert ambiguous is False
    assert exit_at == bars[8].closed_at


def test_cibo_m1_clone_contract_is_exact_ten_year_native_scope() -> None:
    assert CLONE_IDENTITY == "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"
    assert PERIOD_M1 == 1
    assert TARGET_START == datetime(2016, 9, 17, 0, 0, tzinfo=UTC)
    assert TARGET_END_EXCLUSIVE == datetime(2026, 9, 17, 0, 0, tzinfo=UTC)
    assert set(TARGET_SYMBOLS) == {
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "USDCAD",
        "USDJPY",
        "NAS100",
        "XAUUSD",
    }
    partitions = _year_partitions()
    assert partitions[0][1] == TARGET_START
    assert partitions[-1][2] == TARGET_END_EXCLUSIVE


def test_m1_reader_preserves_native_one_minute_chronology(tmp_path: Path) -> None:
    root = tmp_path
    raw = root / "RAW_M1_LEDGER"
    raw.mkdir()
    rows = []
    for index in range(2):
        bar = _bar(index, open_="100", high="101", low="99", close="100.5")
        low = 9_900_000
        rows.append(
            {
                "schema": "qore.capitalizer.cibo.raw_m1.v1",
                "identity": "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1",
                "canonical_symbol": "EURUSD",
                "provider_symbol": "EURUSD",
                "provider_symbol_id": 1,
                "digits": 5,
                "opened_at": bar.opened_at.isoformat(),
                "utc_timestamp_in_minutes": int(bar.opened_at.timestamp() // 60),
                "low_relative": low,
                "delta_open": 100_000,
                "delta_high": 200_000,
                "delta_close": 150_000,
                "volume": None,
                "open_relative": low + 100_000,
                "high_relative": low + 200_000,
                "close_relative": low + 150_000,
            }
        )
    (raw / "2026.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    loaded = tuple(iter_cibo_m1(root))
    assert len(loaded) == 2
    assert loaded[1].opened_at - loaded[0].opened_at == timedelta(minutes=1)
    assert loaded[0].closed_at - loaded[0].opened_at == timedelta(minutes=1)
    assert IDENTITY == "QORE_CAPITALIZER_NATIVE_M1_ENTRY_REPLAY_V1"
