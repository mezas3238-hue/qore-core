"""Strict exported real-M5 interface and causal offline SMT census tests.

All fixtures are synthetic for parser validation. Passing them is NOT a backtest.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.index_smt_census import (
    CSV_FIELDS,
    SMTExportError,
    census_smt_candidates,
    load_ctrader_m5_export,
)
from qore.infrastructure.trader_lab.index_smt_research import SYMBOLS, Symbol

END = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
M5 = timedelta(minutes=5)
BROKER_SYMBOLS: dict[Symbol, str] = {
    "SPX500": "US500",
    "NDX100": "USTEC",
    "US30": "US30",
}


def rows(
    symbol: Symbol,
    *,
    server: str = "IC-DEMO-TEST",
    end: datetime = END,
) -> list[dict[str, str]]:
    answer = []
    base = {"SPX500": 100, "NDX100": 200, "US30": 300}[symbol]
    for index in range(27):
        opened_at = end - timedelta(minutes=135) + M5 * index
        high = base + (4 if symbol == "SPX500" and index == 24 else 2)
        answer.append({
            "origin": "CTRADER_IC_DEMO",
            "broker": "IC MARKETS",
            "environment": "DEMO",
            "server": server,
            "canonical_symbol": symbol,
            "broker_symbol": BROKER_SYMBOLS[symbol],
            "open_time_utc": opened_at.isoformat(),
            "open": str(base),
            "high": str(high),
            "low": str(base - 2),
            "close": str(base),
            "closed": "true",
        })
    return answer


def save(path: Path, dataset: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(dataset)


def export(
    tmp_path: Path,
    symbol: Symbol,
    data: list[dict[str, str]] | None = None,
):
    path = tmp_path / f"{symbol}.csv"
    save(path, rows(symbol) if data is None else data)
    return load_ctrader_m5_export(
        path, symbol=symbol, broker_symbol=BROKER_SYMBOLS[symbol]
    )


def test_three_real_export_shaped_inputs_make_one_closed_smt_candidate(
    tmp_path: Path,
) -> None:
    inputs = {sym: export(tmp_path, sym) for sym in SYMBOLS}
    result = census_smt_candidates(inputs)
    assert result["research_only"] is True
    assert result["authorized_to_trade"] is False
    assert result["authorized_to_emit_alerts"] is False
    assert result["economic_edge_certified"] is False
    assert result["data_source_authenticity_verified"] is False
    assert result["complete_windows"] == 1
    assert result["candidate_count"] == 2
    assert result["candidate_counts_by_pair_side"] == {
        "SPX500/NDX100:BEARISH": 1,
        "SPX500/US30:BEARISH": 1,
    }
    assert result["candidates"][0]["confirmed_at_utc"] == END.isoformat()
    for sym in SYMBOLS:
        assert result["exports"][sym]["raw_m5_count"] == 27
        assert result["exports"][sym]["complete_m15_count"] == 9
        assert result["exports"][sym]["incomplete_m15_buckets"] == 0


def test_broken_m5_bucket_is_not_filled_or_synthetically_repaired(
    tmp_path: Path,
) -> None:
    invalid = rows("NDX100")
    invalid.pop(-2)
    inputs = {
        sym: export(tmp_path, sym, invalid if sym == "NDX100" else None)
        for sym in SYMBOLS
    }
    result = census_smt_candidates(inputs)
    assert result["complete_windows"] == 0
    assert result["candidate_count"] == 0
    assert result["windows_missing_instrument"] == 1
    assert result["exports"]["NDX100"]["incomplete_m15_buckets"] == 1


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ({"origin": "TRADINGVIEW_IC"}, "provenance"),
        ({"broker": "OTHER BROKER"}, "provenance"),
        ({"environment": "LIVE"}, "provenance"),
        ({"canonical_symbol": "US30"}, "provenance"),
        ({"broker_symbol": "NDX100"}, "provenance"),
        ({"closed": "false"}, "closure"),
        ({"open_time_utc": "2026-11-05T15:01:00+00:00"}, "five-minute"),
        ({"open_time_utc": "2026-11-05T14:00:00"}, "UTC"),
        ({"low": "105"}, "OHLC"),
        ({"high": "nan"}, "finite"),
    ],
)
def test_bad_provenance_and_ohlc_fail_closed(
    tmp_path: Path, mutation: dict[str, str], error: str
) -> None:
    data = rows("SPX500")
    data[0].update(mutation)
    with pytest.raises(SMTExportError, match=error):
        export(tmp_path, "SPX500", data)


def test_duplicate_timestamp_and_server_switch_are_rejected(tmp_path: Path) -> None:
    data = rows("SPX500")
    data[1]["open_time_utc"] = data[0]["open_time_utc"]
    with pytest.raises(SMTExportError, match="chronological"):
        export(tmp_path, "SPX500", data)
    other = rows("SPX500")
    other[10]["server"] = "OTHER-SERVER"
    with pytest.raises(SMTExportError, match="servers"):
        export(tmp_path, "SPX500", other)


def test_cross_index_feed_identity_rejected(tmp_path: Path) -> None:
    datasets = {
        sym: export(
            tmp_path, sym,
            rows(sym, server="WRONG-IC-SERVER" if sym == "US30" else "IC-DEMO-TEST"),
        )
        for sym in SYMBOLS
    }
    with pytest.raises(SMTExportError, match="source/server"):
        census_smt_candidates(datasets)


def test_sweep_not_seen_before_its_completed_candle(tmp_path: Path) -> None:
    truncated = {sym: rows(sym)[:-3] for sym in SYMBOLS}
    exports = {sym: export(tmp_path, sym, truncated[sym]) for sym in SYMBOLS}
    result = census_smt_candidates(exports)
    assert result["candidate_count"] == 0


def test_explicit_broker_symbols_required(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    save(path, rows("SPX500"))
    with pytest.raises(SMTExportError, match="mapping"):
        load_ctrader_m5_export(path, symbol="SPX500", broker_symbol="")


def test_dst_calendar_is_evaluated_in_new_york_not_fixed_utc(
    tmp_path: Path,
) -> None:
    july_end = datetime(2026, 7, 7, 14, 0, tzinfo=UTC)
    exports = {}
    for sym in SYMBOLS:
        exports[sym] = export(tmp_path, sym, rows(sym, end=july_end))
    report = census_smt_candidates(exports)
    assert report["complete_windows"] == 1
    assert report["candidate_count"] == 2


def test_iso_utc_and_digest_replay_is_deterministic(tmp_path: Path) -> None:
    inputs = {sym: export(tmp_path, sym) for sym in SYMBOLS}
    assert census_smt_candidates(inputs) == census_smt_candidates(inputs)
    assert len(inputs["SPX500"].sha256) == 64
