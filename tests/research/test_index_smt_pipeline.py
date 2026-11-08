"""Full isolated native cTrader M5 -> M15 -> SMT pipeline, synthetic fixtures only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.ctrader_demo_market_data import (
    CTraderTrendbar,
    CTraderTrendbarPeriod,
    CTraderTrendbarReadResult,
)
from qore.infrastructure.trader_lab.index_smt_census import (
    census_smt_candidates,
    load_ctrader_m5_export,
)
from qore.infrastructure.trader_lab.index_smt_ctrader_bridge import (
    encode_sanitized_ctrader_m5,
)
from qore.infrastructure.trader_lab.index_smt_research import SYMBOLS, Symbol

END = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
SYMBOL_META: dict[Symbol, tuple[str, int, int]] = {
    "SPX500": ("US500", 101, 100),
    "NDX100": ("USTEC", 202, 200),
    "US30": ("US30", 303, 300),
}


def response(symbol: Symbol, *, shift_minutes: int = 0) -> CTraderTrendbarReadResult:
    _, symbol_id, base = SYMBOL_META[symbol]
    begin = END - timedelta(minutes=135 - shift_minutes)
    first = int(begin.timestamp() / 60)
    bars = []
    for index in range(27):
        # For SPX500 only: the 25th source M5 creates a late high sweep
        # but closes back inside the previous eight M15 highs.
        high_price = 4 if (symbol == "SPX500" and index == 24) else 2
        bars.append(CTraderTrendbar(
            low_relative=(base - 2) * 100000,
            delta_open=2 * 100000,
            delta_high=(high_price + 2) * 100000,
            delta_close=2 * 100000,
            utc_timestamp_in_minutes=first + index * 5,
        ))
    return CTraderTrendbarReadResult(
        instrument=symbol,
        symbol_id=symbol_id,
        digits=2,
        period=CTraderTrendbarPeriod.M5,
        trendbars=tuple(bars),
    )


def run_pipeline(tmp_path: Path, *, shift_ndx: bool = False) -> dict[str, object]:
    exported = {}
    for sym in SYMBOLS:
        name, symbol_id, _ = SYMBOL_META[sym]
        source = response(sym, shift_minutes=15 if shift_ndx and sym == "NDX100" else 0)
        payload = encode_sanitized_ctrader_m5(
            source,
            canonical_symbol=sym,
            runtime_instrument=sym,
            broker_symbol=name,
            broker_symbol_id=symbol_id,
            broker_digits=2,
            server="IC-DEMO-SYNTHETIC",
            observed_at=END + (timedelta(minutes=15) if shift_ndx else timedelta(0)),
        )
        path = tmp_path / f"{sym}.csv"
        path.write_text(payload, encoding="utf-8")
        exported[sym] = load_ctrader_m5_export(
            path, symbol=sym, broker_symbol=name,
        )
    return census_smt_candidates(exported)


def test_end_to_end_native_m5_to_smt_census_without_any_mocked_event(
    tmp_path: Path,
) -> None:
    report = run_pipeline(tmp_path)
    assert report["complete_windows"] == 1
    assert report["candidate_count"] == 2
    assert report["candidate_counts_by_pair_side"] == {
        "SPX500/NDX100:BEARISH": 1,
        "SPX500/US30:BEARISH": 1,
    }
    assert report["authorized_to_emit_alerts"] is False
    assert report["authorized_to_trade"] is False
    assert report["crt_mss_certified"] is False
    assert report["economic_edge_certified"] is False
    assert report["data_source_authenticity_verified"] is False


def test_end_to_end_misaligned_source_is_not_converted_to_signal(
    tmp_path: Path,
) -> None:
    report = run_pipeline(tmp_path, shift_ndx=True)
    assert report["complete_windows"] == 0
    assert report["candidate_count"] == 0
    missing_instrument = report["windows_missing_instrument"]
    missing_prior_m15 = report["windows_missing_prior_m15"]
    assert isinstance(missing_instrument, int)
    assert isinstance(missing_prior_m15, int)
    assert missing_instrument > 0 or missing_prior_m15 > 0
