"""Synthetic tests only; no market PnL or reserved-holdout data."""
import datetime as dt
import hashlib
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_d1_tsmom20_single_edge_v1 as t


def synthetic_sessions(n=85, start=dt.date(2021, 6, 1), rising=True):
    days = []
    day = start
    while len(days) < n:
        if day.weekday() >= 5:
            day += dt.timedelta(days=1)
            continue
        idx = len(days)
        price = 100000 + (150 * idx if rising else -100 * idx)
        days.append({
            "date": day,
            "entry_ts": dt.datetime.combine(day, dt.time(0, 10), tzinfo=dt.UTC),
            "entry_open": price,
            "close": price + (100 if rising else -80),
            "last_ts": dt.datetime.combine(day, dt.time(23, 55), tzinfo=dt.UTC),
            "bars": 280,
        })
        day += dt.timedelta(days=1)
    return days


class FrozenDailyMomentumTest(unittest.TestCase):
    def test_universe_and_original_source_roster_frozen(self):
        self.assertEqual(len(t.universe()), 33)
        self.assertEqual(len(t.ORIGINAL12), 12)
        self.assertEqual(len(set(t.source_name(s) for s in t.universe())), 33)
        self.assertEqual(t.SIGNAL_DAYS, 20)
        self.assertEqual(t.BPS_PER_SIDE, 1)
        self.assertEqual(t.EMBARGO.isoformat(), "2024-09-17")

    def test_entry_after_prior_m5_close_plus_latency(self):
        bars = synthetic_sessions()
        rows, benchmark = t.market_experiment("EURUSD", bars)
        self.assertTrue(rows)
        self.assertTrue(benchmark)
        self.assertTrue(all(x["position"] == 1 for x in rows))
        self.assertTrue(all(x["mark_date"] > bars[0]["date"] for x in rows))
        self.assertEqual(sum(x["turnover_sides"] for x in rows), 2)
        self.assertAlmostEqual(rows[0]["strategy_daily_net_assumed"],
                               rows[0]["raw_daily_underlying"] - t.SIDE_COST)

    def test_exclude_if_signal_bar_not_yet_available(self):
        bars = synthetic_sessions()
        # Force same-day open to precede the earlier day's hypothetical last close.
        for i in range(len(bars)):
            bars[i]["entry_ts"] = dt.datetime.combine(
                bars[i]["date"], dt.time(0, 0), tzinfo=dt.UTC)
        with self.assertRaisesRegex(ValueError, "NO_TRADING_ROWS"):
            t.market_experiment("EURUSD", bars)

    def test_cost_roundtrip_side_not_2bps_every_single_day(self):
        bars = synthetic_sessions()
        rows, _ = t.market_experiment("EURUSD", bars)
        self.assertGreater(len(rows), 10)
        self.assertEqual(rows[1]["turnover_sides"], 0)
        self.assertAlmostEqual(rows[1]["strategy_daily_net_assumed"],
                               rows[1]["raw_daily_underlying"])
        self.assertEqual(rows[-1]["turnover_sides"], 1)

    def test_negative_trend_short_and_no_post_embargo(self):
        bars = synthetic_sessions(start=dt.date(2022, 5, 2), rising=False)
        rows, _ = t.market_experiment("EURUSD", bars)
        self.assertTrue(rows)
        self.assertTrue(all(x["position"] == -1 for x in rows))
        self.assertTrue(all(x["era"] == "DIAG" for x in rows))
        self.assertTrue(all(x["mark_date"] < t.EMBARGO for x in rows))

    def test_single_panel_cash_when_other_markets_missing(self):
        bars = synthetic_sessions()
        rows, bm = t.market_experiment("EURUSD", bars)
        source = [{"symbol":s} for s in t.universe()]
        report = t.aggregate(rows, bm, source)
        self.assertEqual(report["frozen_markets"], 33)
        self.assertEqual(report["performance"]["DIAG"]["market_day_positions"], 0)
        self.assertFalse(report["holdout_outcomes_calculated"])
        self.assertFalse(report["performance_is_real_broker_NET"])
        d = rows[0]["mark_date"]
        self.assertGreater(report["performance"]["DEV"]["active_mark_dates"], 0)

    def test_performance_drawdown_and_sharpe(self):
        v = t.performance([0.02, -0.10, 0.05, -0.01] * 80)
        self.assertLess(v["max_drawdown"], 0.)
        self.assertTrue(math.isfinite(v["annualized_sharpe_252_rf0"]))

    def test_no_unsafe_or_duplicate_sha_witness(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            t.parse_checksum("a"*64 + "  RAW/year.jsonl\n" + "b"*64 + "  RAW/year.jsonl")
        with self.assertRaisesRegex(ValueError, "UNSAFE"):
            t.parse_checksum("a"*64 + "  ../passwords")

    def test_open_proxy_is_not_spx(self):
        self.assertEqual(t.correlation([1.]*60, [1.]*60), None)
        self.assertIsNone(t.correlation([1.]*2, [1.]*2))

    def test_no_cross_period_open_open_return(self):
        bars = synthetic_sessions(n=85, start=dt.date(2021, 11, 15))
        rows, _ = t.market_experiment("EURUSD", bars)
        self.assertTrue(rows)
        for item in rows:
            self.assertIn(item["era"], ("DEV", "DIAG"))
            self.assertLess(item["mark_date"], t.EMBARGO)


if __name__ == "__main__":
    unittest.main()
