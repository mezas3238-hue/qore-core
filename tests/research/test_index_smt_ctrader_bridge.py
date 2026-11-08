"""Provider-native M5 read-result -> SMT CSV roundtrip (synthetic contract QA)."""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest

from qore.infrastructure.ctrader_demo_market_data import (
    CTraderTrendbar,
    CTraderTrendbarPeriod,
    CTraderTrendbarReadResult,
)
from qore.infrastructure.trader_lab.index_smt_census import (
    SMTExportError,
    load_ctrader_m5_export,
)
from qore.infrastructure.trader_lab.index_smt_ctrader_bridge import (
    encode_sanitized_ctrader_m5,
)
from qore.infrastructure.trader_lab.index_smt_research import Symbol


def at() -> datetime:
    return datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


def source(
    *, symbol: str = "SPX500", has_more: bool = False,
    minutes: tuple[int, ...] = (0, 5, 10, 15, 20, 25),
) -> CTraderTrendbarReadResult:
    first_minute = int((at() - timedelta(minutes=30)).timestamp() // 60)
    return CTraderTrendbarReadResult(
        instrument=symbol,
        symbol_id=123,
        digits=2,
        period=CTraderTrendbarPeriod.M5,
        trendbars=tuple(
            CTraderTrendbar(
                low_relative=10000000,  # 100.00
                delta_open=100000,       # 101.00
                delta_high=200000,       # 102.00
                delta_close=150000,      # 101.50
                utc_timestamp_in_minutes=first_minute + minute,
            ) for minute in minutes
        ),
        has_more=has_more,
    )


def encode(
    result: CTraderTrendbarReadResult,
    *,
    symbol: Symbol = "SPX500",
    observed: datetime | None = None,
    expected_id: int = 123,
) -> str:
    return encode_sanitized_ctrader_m5(
        result,
        canonical_symbol=symbol,
        runtime_instrument="SPX500",
        broker_symbol="US500",
        broker_symbol_id=expected_id,
        broker_digits=2,
        server="IC-DEMO-SYNTHETIC",
        observed_at=observed or at(),
    )


def test_native_roundtrip_reconstructs_true_ohlc_and_m15(
    tmp_path: Path,
) -> None:
    payload = encode(source())
    rows = list(csv.DictReader(StringIO(payload)))
    assert len(rows) == 6
    assert rows[0]["open"] == "101.00"
    assert rows[0]["high"] == "102.00"
    assert rows[0]["low"] == "100.00"
    assert rows[0]["close"] == "101.50"
    assert rows[0]["origin"] == "CTRADER_IC_DEMO"
    path = tmp_path / "SPX500.csv"
    path.write_text(payload, encoding="utf-8")
    report = load_ctrader_m5_export(path, symbol="SPX500", broker_symbol="US500")
    assert report.raw_m5_count == 6
    assert len(report.complete_m15) == 2
    assert report.complete_m15[-1].closed_at == at()
    assert report.complete_m15[-1].high == 102
    assert report.complete_m15[-1].close == 101.5


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("wrong_id", "mapping"),
        ("wrong_clock", "observation clock"),
        ("future_bar", "not-yet-closed"),
        ("duplicate", "unordered"),
        ("reversed", "unordered"),
        ("has_more", "truncated"),
        ("missing", "no M5"),
    ],
)
def test_fail_closed_on_provider_errors(case: str, expected: str) -> None:
    provider = source()
    expected_id = 123
    observed: datetime | None = None
    if case == "wrong_id":
        expected_id = 124
    elif case == "wrong_clock":
        observed = datetime(2026, 11, 5, 15, 0)
    elif case == "future_bar":
        observed = at() - timedelta(minutes=2)
    elif case == "duplicate":
        provider = source(minutes=(0, 5, 10, 10, 20, 25))
    elif case == "reversed":
        provider = source(minutes=(0, 5, 10, 25, 20, 15))
    elif case == "has_more":
        provider = source(has_more=True)
    elif case == "missing":
        provider = source(minutes=())
    with pytest.raises(SMTExportError, match=expected):
        encode(provider, observed=observed, expected_id=expected_id)


def test_missing_m5_stays_missing_after_provider_roundtrip(
    tmp_path: Path,
) -> None:
    provider = source(minutes=(0, 5, 10, 15, 25))
    path = tmp_path / "part.csv"
    path.write_text(encode(provider), encoding="utf-8")
    report = load_ctrader_m5_export(path, symbol="SPX500", broker_symbol="US500")
    assert report.raw_m5_count == 5
    assert len(report.complete_m15) == 1
    assert report.incomplete_m15_buckets == 1


def test_mapping_is_explicit_not_inferred() -> None:
    with pytest.raises(SMTExportError, match="mapping"):
        encode_sanitized_ctrader_m5(
            source(), canonical_symbol="SPX500",
            runtime_instrument="NDX100", broker_symbol="US500",
            broker_symbol_id=123, broker_digits=2,
            server="IC-DEMO-SYNTHETIC", observed_at=at(),
        )


def test_same_byte_result_for_same_provider_response() -> None:
    assert encode(source()) == encode(source())
