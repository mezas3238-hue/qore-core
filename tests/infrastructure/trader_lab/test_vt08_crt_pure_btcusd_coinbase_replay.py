from datetime import UTC, datetime

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_btcusd_coinbase_replay import (
    _coverage,
    _parse_coinbase_row,
)


def test_coinbase_row_maps_documented_ohlc_order() -> None:
    row = [1726876800, "62000.10", "62500.20", "62100.30", "62400.40", "12.5"]
    bar = _parse_coinbase_row(row)
    assert bar.opened_at == datetime.fromtimestamp(1726876800, tz=UTC)
    assert bar.low_price == 6200010000000
    assert bar.high_price == 6250020000000
    assert bar.open_price == 6210030000000
    assert bar.close_price == 6240040000000


def test_coinbase_row_rejects_invalid_ohlc() -> None:
    with pytest.raises(ValueError, match="OHLC ordering"):
        _parse_coinbase_row([1726876800, "62500", "62000", "62100", "62400", "1"])


def test_coverage_is_fail_closed_on_missing_m5() -> None:
    start = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    rows = (
        _parse_coinbase_row([1767225600, "1", "2", "1", "2", "1"]),
        _parse_coinbase_row([1767226200, "1", "2", "1", "2", "1"]),
    )
    report = _coverage(rows, start, datetime(2026, 1, 1, 0, 15, tzinfo=UTC))
    assert report["expected_bars"] == 3
    assert report["observed_bars"] == 2
    assert report["missing_bars"] == 1
    assert report["complete"] is False
