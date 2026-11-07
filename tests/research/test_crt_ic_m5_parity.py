"""Pure offline tests: no network, trading, credentials or market signals."""
import csv
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.crt_feed_parity.compare_ic_m5 import (
    HEADER,
    SCHEMA,
    CandleParityError,
    compare,
    read_closed_m5_csv,
)

BASE = datetime(2026, 11, 5, 0, 0, tzinfo=UTC)


def make_rows(
    origin: str, *, n: int = 600, shift_min: int = 0,
    price_offset: float = 0.0, symbol: str = "EURUSD",
    server: str = "feed-1",
) -> list[dict[str, str]]:
    rows = []
    for i in range(n):
        at = BASE + timedelta(minutes=5 * i + shift_min)
        low = 1.10 + (i % 3) / 10000.0 + price_offset
        rows.append({
            "origin": origin,
            "tv_symbol": "IC:" + symbol,
            "broker": "IC MARKETS",
            "server": server,
            "open_time_utc": at.isoformat(),
            "open": format(low + .0001, ".5f"),
            "high": format(low + .0002, ".5f"),
            "low": format(low, ".5f"),
            "close": format(low + .0001, ".5f"),
            "closed": "true",
        })
    return rows


def write(path: Path, rows: list[dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


class CandleParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tvfile = Path(self.tmp.name) / "tv.csv"
        self.ctfile = Path(self.tmp.name) / "ctrader.csv"

    def load(
        self,
        tv_rows: list[dict[str, str]] | None = None,
        ct_rows: list[dict[str, str]] | None = None,
    ) -> dict[str, object]:
        write(self.tvfile, make_rows("TRADINGVIEW_IC") if tv_rows is None else tv_rows)
        write(self.ctfile, make_rows("CTRADER_IC_DEMO") if ct_rows is None else ct_rows)
        a, ta = read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")
        b, cb = read_closed_m5_csv(self.ctfile, source="CTRADER_IC_DEMO", symbol="EURUSD")
        return compare(a, b, symbol="EURUSD", tv_server=ta, ctrader_server=cb)

    def test_exact_600_is_only_sample_match_not_signal_certification(self) -> None:
        report = self.load()
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["status"], "SAMPLE_MATCH_ONLY")
        self.assertEqual(report["identical_ohlc"], 600)
        self.assertEqual(report["different_ohlc"], 0)
        self.assertFalse(report["crt_mss_fvg_parity_checked"])
        self.assertFalse(report["authorized_to_emit_v34_12x_alerts"])

    def test_one_price_change_blocks_equivalence(self) -> None:
        ct = make_rows("CTRADER_IC_DEMO", price_offset=.00001)
        r = self.load(ct_rows=ct)
        self.assertEqual(r["status"], "DIVERGENT")
        self.assertEqual(r["different_ohlc"], 600)
        self.assertTrue(r["different_ohlc_examples"])

    def test_one_minute_native_phase_shift_is_not_silently_aligned(self) -> None:
        r = self.load(ct_rows=make_rows("CTRADER_IC_DEMO", shift_min=1))
        self.assertEqual(r["status"], "INSUFFICIENT")
        self.assertEqual(r["common_open_timestamps"], 0)
        self.assertEqual(r["tv_phase_minutes"], [0])
        self.assertEqual(r["ctrader_phase_minutes"], [1])

    def test_25_or_300_bars_are_insufficient_for_default_600(self) -> None:
        r = self.load(ct_rows=make_rows("CTRADER_IC_DEMO", n=300))
        self.assertEqual(r["status"], "INSUFFICIENT")
        self.assertEqual(r["common_open_timestamps"], 300)
        self.assertEqual(r["only_tradingview_times"], 300)

    def test_missing_bar_rejected_even_with_600_common(self) -> None:
        r = self.load(tv_rows=make_rows("TRADINGVIEW_IC", n=601),
                      ct_rows=make_rows("CTRADER_IC_DEMO", n=600))
        self.assertEqual(r["status"], "DIVERGENT")
        self.assertEqual(r["only_tradingview_times"], 1)

    def test_different_server_within_same_export_rejected(self) -> None:
        rows = make_rows("TRADINGVIEW_IC")
        rows[-1]["server"] = "other-server"
        write(self.tvfile, rows)
        with self.assertRaisesRegex(CandleParityError, "mix servers"):
            read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")

    def test_wrong_source_and_symbol_rejected(self) -> None:
        write(self.tvfile, make_rows("CTRADER_IC_DEMO"))
        with self.assertRaisesRegex(CandleParityError, "wrong data origin"):
            read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")
        write(self.tvfile, make_rows("TRADINGVIEW_IC", symbol="USDCAD"))
        with self.assertRaisesRegex(CandleParityError, "source ticker mismatch"):
            read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")

    def test_unclosed_and_naive_dates_rejected(self) -> None:
        rows = make_rows("TRADINGVIEW_IC")
        rows[0]["closed"] = "false"
        write(self.tvfile, rows)
        with self.assertRaisesRegex(CandleParityError, "unclosed"):
            read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")
        rows[0]["closed"] = "true"
        rows[0]["open_time_utc"] = "2026-11-05T00:00:00"
        write(self.tvfile, rows)
        with self.assertRaisesRegex(CandleParityError, "UTC offset"):
            read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")

    def test_duplicate_timestamp_and_impossible_ohlc_rejected(self) -> None:
        rows = make_rows("TRADINGVIEW_IC")
        rows[1]["open_time_utc"] = rows[0]["open_time_utc"]
        write(self.tvfile, rows)
        with self.assertRaisesRegex(CandleParityError, "duplicate"):
            read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")
        rows = make_rows("TRADINGVIEW_IC")
        rows[0]["low"] = "1.50000"
        write(self.tvfile, rows)
        with self.assertRaisesRegex(CandleParityError, "impossible OHLC"):
            read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")

    def test_wrong_broker_rejected(self) -> None:
        rows = make_rows("TRADINGVIEW_IC")
        rows[0]["broker"] = "OTHER"
        write(self.tvfile, rows)
        with self.assertRaisesRegex(CandleParityError, "broker mismatch"):
            read_closed_m5_csv(self.tvfile, source="TRADINGVIEW_IC", symbol="EURUSD")


if __name__ == "__main__":
    unittest.main()
