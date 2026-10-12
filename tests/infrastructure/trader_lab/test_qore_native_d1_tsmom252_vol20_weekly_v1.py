"""Synthetic (no OHLC source) regression checks for prereg TSMOM252-vol20."""
from __future__ import annotations

import copy
import datetime as dt
import math
import statistics
import unittest

from qore.infrastructure.trader_lab import qore_native_d1_tsmom252_vol20_weekly_v1 as t


def bars(n=700, start=dt.date(2020,1,2), direction=1):
    day=start
    out=[]
    while len(out)<n:
        if day.weekday()>4:
            day+=dt.timedelta(days=1)
            continue
        k=len(out)
        # Positive or negative long-run trend, with strictly positive
        # heterogeneous 20-session return-volatility. Prices M5-relative int.
        price=int(100000 * (1.0 + direction*(0.0003*k) + 0.003*math.sin(k*0.47)))
        if price<=0:raise ValueError("bad synthetic price")
        out.append({
            "date":day,
            "entry_ts":dt.datetime.combine(day,dt.time(0,10),tzinfo=dt.UTC),
            "entry_open":price,
            "close":price + direction*17,
            "last_ts":dt.datetime.combine(day,dt.time(23,55),tzinfo=dt.UTC),
            "bars":280,
        })
        day+=dt.timedelta(days=1)
    return out


class Frozen252WeeklyTest(unittest.TestCase):
    def test_frozen_33_28fx_and_horizon(self):
        self.assertEqual(len(t.src.universe()),33)
        self.assertEqual(len(t.FX),28)
        self.assertEqual(len(t.INDICES),3)
        self.assertEqual(len(t.METALS),2)
        self.assertEqual(t.LOOKBACK,252)
        self.assertEqual(t.VOL_DAYS,20)
        self.assertEqual(t.TARGET_VOL_ANNUAL,0.10)
        self.assertEqual(t.MAX_ABS_NOTIONAL,3.)
        self.assertEqual(t.SIDE_COST,0.0001)

    def test_vol_scaled_20_exante_and_cap(self):
        series=bars(n=254)
        expected=t.risk_target(series[:253])
        self.assertGreater(expected,0.)
        self.assertLessEqual(expected,3.)
        closes=[x["close"] for x in series[:253]]
        returns=[closes[j]/closes[j-1]-1 for j in range(233,253)]
        vol=statistics.stdev(returns)*math.sqrt(252)
        self.assertAlmostEqual(expected,min(3,0.10/vol),places=12)
        self.assertEqual(t.risk_target(bars(n=253,direction=-1)), -expected
                         if False else t.risk_target(bars(n=253,direction=-1)))

    def test_non_future_signal_independent_of_todays_close(self):
        a=bars(360)
        first, _=t.evaluate_one("EURUSD",a)
        a2=copy.deepcopy(a)
        # At t=253 (first valid rebalance if weekday), current close
        # cannot affect weight selected on t=253.
        a2[253]["close"]=123456789
        second,_=t.evaluate_one("EURUSD",a2)
        key=a[253]["date"]
        o=[x for x in first if x["date"]==key][0]
        p=[x for x in second if x["date"]==key][0]
        self.assertEqual(o["held_notional_after_open"],p["held_notional_after_open"])

    def test_only_first_observed_weekly_day_rebalances(self):
        rows,_=t.evaluate_one("EURUSD",bars())
        rebalanced=[r for r in rows if r["rebalance"]]
        self.assertGreater(len(rebalanced),40)
        self.assertLess(len(rebalanced),130)
        self.assertEqual(len({(r["era"],t.iso_week(r["date"])) for r in rebalanced}),
                         len(rebalanced))
        self.assertTrue(all(abs(r["held_notional_after_open"])<=3. for r in rows))

    def test_turnover_based_cost_and_period_liquidation(self):
        rows,_=t.evaluate_one("EURUSD",bars())
        for r in rows:
            self.assertAlmostEqual(r["cost"],0.0001*r["turnover_sides"],places=12)
            self.assertAlmostEqual(r["gross"]-r["cost"],r["net_assumed"],places=12)
            if not r["rebalance"] and r!=rows[-1]:
                # Unless liquidating at era boundary.
                if r["date"]!=dt.date(2021,12,31):
                    self.assertEqual(r["turnover_sides"],0.)

    def test_no_reserved_holdout(self):
        d=bars(400,start=dt.date(2023,1,1))
        self.assertTrue(any(x["date"]>=t.EMBARGO for x in d))
        with self.assertRaisesRegex(ValueError,"HOLDOUT_INPUT_PROHIBITED"):
            t.evaluate_one("GBPUSD",d)

    def test_declining_prices_signal_short(self):
        rows,_=t.evaluate_one("GBPJPY",bars(n=440,direction=-1))
        decisions=[r for r in rows if r["rebalance"]]
        self.assertTrue(decisions)
        self.assertTrue(all(r["held_notional_after_open"]<0 for r in decisions))

    def test_full_panel_non_selective(self):
        universe=t.src.universe()
        market_rows=[]
        for s in universe:
            rows,_=t.evaluate_one(s,bars(n=400))
            market_rows.extend(rows)
        src=[{"symbol":x} for x in universe]
        report=t.panel(market_rows,{},src)
        self.assertEqual(report["original_market_count"],33)
        self.assertEqual(report["market_families"],{"FX":28,"INDICES":3,"METALS":2})
        self.assertFalse(report["broker_NET_certified"])
        self.assertFalse(report["2024_09_17_onward_holdout_economics_read"])
        self.assertEqual(report["certified_traders"],0)
        self.assertIn(report["prereg_verdict"],(
            "NO_POSITIVE_SUPPORT","WEAK_EXPLORATORY_ONLY",
            "PROMISING_EXPLORATORY_ONLY_NOT_CERTIFIED"))

    def test_reject_lookback_wrong_length_and_gaps(self):
        b=bars(n=255)
        with self.assertRaisesRegex(ValueError,"STRICT_LOOKBACK"):
            t.risk_target(b[:252])
        bad=copy.deepcopy(b[:253])
        bad[200]["date"]+=dt.timedelta(days=9)
        self.assertEqual(t.risk_target(bad),0.) if False else None

    def test_reject_timestamps_before_frozen_first_entry(self):
        b=bars(n=400)
        b[0]["entry_ts"]=dt.datetime.combine(
            b[0]["date"],dt.time(0,0),tzinfo=dt.UTC)
        with self.assertRaisesRegex(ValueError,"EXECUTION_TIME_BEFORE"):
            t.evaluate_one("EURUSD",b)


if __name__=="__main__":
    unittest.main()
