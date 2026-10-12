"""Pure synthetic tests for prereg cross-sectional H3, no real outcomes."""
from __future__ import annotations

import copy
import datetime as dt
import math
import unittest

from qore.infrastructure.trader_lab import qore_native_d1_xsrev5_33_h3_one_test_v1 as h


def fake33(n=900,start=dt.date(2020,1,2)):
    out={s:[] for s in h.freeze_universe()}
    dtday=start
    days=[]
    while len(days)<n:
        if dtday.weekday()<5:
            days.append(dtday)
        dtday+=dt.timedelta(days=1)
    for i,s in enumerate(h.freeze_universe()):
        for k,d in enumerate(days):
            price=1_000_000 + 4 * (i-16)*k + (k%3)*11
            out[s].append({
                "date":d,
                "entry_ts":dt.datetime.combine(d,dt.time(0,10),tzinfo=dt.UTC),
                "last_ts":dt.datetime.combine(d,dt.time(23,55),tzinfo=dt.UTC),
                "entry_open":price,
                "close":price+4*(i-16),
                "bars":280,
            })
    return out


class CrossReversalFrozen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=fake33()
        cls.common,cls.maps,cls.stats=h.make_common_calendar(cls.data)

    def test_original_frozen_33_and_subgroups(self):
        self.assertEqual(len(h.freeze_universe()),33)
        self.assertEqual({k:len(x) for k,x in h.FAMILIES.items()},
                         {"FX_28":28,"INDICES_3":3,"METALS_2":2})
        self.assertEqual(h.FORMATION,5)
        self.assertEqual(h.HOLD,5)
        self.assertEqual(h.LEG_COUNT,6)
        self.assertEqual(h.SIDE_COST,0.0001)
        self.assertEqual(h.EMBARGO.isoformat(),"2024-09-17")

    def test_calendar_common_all_markets(self):
        self.assertEqual(len(self.common),900)
        self.assertEqual(self.stats["union_dates_excluded_in_complete_case"],0)

    def test_5_completed_sessions_direction_and_6x6_neutral(self):
        b=h.basket(self.common,self.maps,20)
        self.assertEqual(len([x for x in b.values() if x>0]),6)
        self.assertEqual(len([x for x in b.values() if x<0]),6)
        self.assertAlmostEqual(sum(abs(x) for x in b.values()),1.)
        self.assertAlmostEqual(sum(b.values()),0.)
        symbols=h.freeze_universe()
        self.assertTrue(all(b[s]>0 for s in symbols[:6]))
        self.assertTrue(all(b[s]<0 for s in symbols[-6:]))

    def test_no_lookahead_from_current_close_or_future_close(self):
        before=h.basket(self.common,self.maps,30)
        changed=copy.deepcopy(self.maps)
        for s in h.freeze_universe():
            changed[s][self.common[30]]["close"] *= 99
            changed[s][self.common[31]]["close"] *= 123
        after=h.basket(self.common,changed,30)
        self.assertEqual(before,after)

    def test_lookback_requires_six_completed_session_closes(self):
        with self.assertRaisesRegex(ValueError,"INSUFFICIENT_FINISHED"):
            h.basket(self.common,self.maps,5)

    def test_cost_turnover_and_5day_nonoverlap(self):
        report=h.evaluate(self.data)
        dev=report["performance"]["DEV"]
        diag=report["performance"]["DIAG"]
        self.assertGreater(dev["portfolio_rebalance_events"],20)
        self.assertGreater(diag["portfolio_rebalance_events"],10)
        self.assertLess(dev["portfolio_rebalance_events"],120)
        self.assertAlmostEqual(dev["assumed_cost_total_capital_fraction_uncompounded"],
                               0.0001*dev["gross_notional_turnover_sides"])
        self.assertAlmostEqual(diag["assumed_cost_total_capital_fraction_uncompounded"],
                               0.0001*diag["gross_notional_turnover_sides"])
        self.assertEqual(report["quintile_floor_assets_long_and_short"],6)
        self.assertFalse(report["broker_NET_certified"])
        self.assertEqual(report["certified_traders"],0)

    def test_no_missing_market_allowed(self):
        data=dict(self.data)
        del data["EURUSD"]
        with self.assertRaisesRegex(ValueError,"MISSING_SOURCE_MARKET"):
            h.make_common_calendar(data)

    def test_common_intersection_no_future_bar_imputation(self):
        data={k:list(v) for k,v in self.data.items()}
        data["EURUSD"]=data["EURUSD"][10:]
        common,_,stats=h.make_common_calendar(data)
        self.assertEqual(len(common),890)
        self.assertEqual(stats["union_dates_excluded_in_complete_case"],10)

    def test_early_entry_rejected(self):
        data={k:list(v) for k,v in self.data.items()}
        data["EURUSD"]=list(data["EURUSD"])
        data["EURUSD"][0]=dict(data["EURUSD"][0])
        d=data["EURUSD"][0]["date"]
        data["EURUSD"][0]["entry_ts"]=dt.datetime.combine(
            d,dt.time(0,0),tzinfo=dt.UTC)
        with self.assertRaisesRegex(ValueError,"INVALID_UTC_EXECUTION"):
            h.make_common_calendar(data)

    def test_embargo_rejected_without_price_read(self):
        data={k:list(v) for k,v in self.data.items()}
        data["EURUSD"]=list(data["EURUSD"])
        changed=dict(data["EURUSD"][-1])
        changed["date"]=h.EMBARGO
        data["EURUSD"].append(changed)
        with self.assertRaisesRegex(ValueError,"HOLDOUT_DAILY_SOURCE_BLOCKED"):
            h.make_common_calendar(data)

    def test_wrong_causal_previous_close(self):
        maps=copy.deepcopy(self.maps)
        earlier=self.common[19]
        maps["EURUSD"][earlier]["last_ts"]+=dt.timedelta(minutes=30)
        with self.assertRaisesRegex(ValueError,"LAST_BAR_NOT_CAUSALLY_COMPLETE"):
            h.basket(self.common,maps,20)

    def test_performance_has_mandatory_metrics_each_era(self):
        report=h.evaluate(self.data)
        self.assertEqual(set(report["performance"]),{"DEV","DIAG"})
        for era in ("DEV","DIAG"):
            x=report["performance"][era]
            for k in ("annualized_sharpe_252_rf0",
                      "annualized_return_252","max_drawdown",
                      "portfolio_rebalance_events",
                      "gross_notional_turnover_sides",
                      "correlation_SP500_CFD_PROXY_NOT_SPX"):
                self.assertIn(k,x)
            self.assertTrue(math.isfinite(x["annualized_return_252"]))
        self.assertTrue(report["research_adaptively_chosen_after_H1_H2"])
        self.assertFalse(report["2024_09_17_onward_economic_holdout_read"])


if __name__=="__main__":
    unittest.main()
