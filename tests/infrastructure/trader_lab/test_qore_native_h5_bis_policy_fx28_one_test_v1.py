"""Synthetic unit regression for H5 eight official policy rate FX28 one-shot.

No live rates, no GitHub artifacts, no real market data in these fixtures.
"""
from __future__ import annotations

import datetime as dt
import math
import unittest
from collections import defaultdict
from datetime import date,timedelta

from qore.infrastructure.trader_lab import qore_native_h5_bis_policy_fx28_one_test_v1 as h


def mocked_monthly():
    rs={}
    months=[]
    d=date(2016,1,1)
    while d<=date(2024,8,1):
        months.append(d)
        d=date(d.year+1,1,1) if d.month==12 else date(d.year,d.month+1,1)
    for c,code in h.CURRENCY_BIS.items():
        base={"AUD":4.,"CAD":2.,"CHF":-2.,"EUR":-1.,"GBP":3.,
              "JPY":-3.,"NZD":5.,"USD":1.}[c]
        rs[c]={m:base+0.02*i for i,m in enumerate(months)}
    return rs


def mocked_bars(n=500,start=date(2020,1,1)):
    days=[]
    d=start
    while len(days)<n:
        if d.weekday()<5:days.append(d)
        d+=timedelta(days=1)
    r={}
    for i,s in enumerate(h.FX28):
        r[s]=[]
        for j,day in enumerate(days):
            price=int(100000 + j*(i-14)*0.50 + 20*math.sin(j/11+i))
            r[s].append({
                "date":day, "entry_open":price,"close":price,
                "entry_ts":dt.datetime.combine(day,dt.time(0,10),tzinfo=dt.UTC),
                "last_ts":dt.datetime.combine(day,dt.time(23,55),tzinfo=dt.UTC),
            })
    return r


def xml_sample(ccy="USD",delete_month=None,wrong_ccy=None):
    code=h.CURRENCY_BIS[ccy]
    d=date(2016,1,1)
    obs=[]
    while d<=date(2024,8,1):
        if d!=delete_month:
            obs.append(f'<Obs TIME_PERIOD="{d:%Y-%m}" OBS_VALUE="1.5"/>')
        d=date(d.year+1,1,1) if d.month==12 else date(d.year,d.month+1,1)
    return (f'<StructureSpecificData><DataSet><Series REF_AREA="{wrong_ccy or code}" FREQ="M">'+
            "".join(obs)+"</Series></DataSet></StructureSpecificData>").encode()


class PolicyRateH5(unittest.TestCase):
    def test_universe_rates_and_frozen_cost(self):
        h.check_universe()
        self.assertEqual(len(h.FX28),28)
        self.assertEqual(len(h.CURRENCY_BIS),8)
        self.assertEqual(h.SIDE_COST,.0002)
        self.assertEqual(h.LONGS,6)
        self.assertEqual(h.SHORTS,6)
        self.assertEqual(h.LAG_MONTHS,2)

    def test_bis_8_country_source_url_only_allowed(self):
        self.assertIn("WS_CBPOL/M.CH",h.bis_url("CHF"))
        self.assertIn("WS_CBPOL/M.XM",h.bis_url("EUR"))
        with self.assertRaisesRegex(ValueError,"UNRECOGNIZED"):
            h.bis_url("USDJPY")

    def test_bis_structure_specific_xml_parses_104(self):
        z=h.parse_policy_rates(xml_sample(),"USD")
        self.assertEqual(len(z),104)
        self.assertEqual(z[date(2024,8,1)],1.5)

    def test_policy_source_reject_wrong_country(self):
        with self.assertRaisesRegex(ValueError,"WRONG_COUNTRY"):
            h.parse_policy_rates(xml_sample(wrong_ccy="JP"),"USD")

    def test_missing_month_in_range_reject_at_rebalance(self):
        rates=mocked_monthly()
        del rates["CHF"][date(2022,2,1)]
        with self.assertRaisesRegex(ValueError,"RATE_MISSING_FAIL_CLOSED_CHF"):
            h.policy_basket(rates,date(2022,4,1))

    def test_basket_neutral_and_top6_carry(self):
        p,diff=h.policy_basket(mocked_monthly(),date(2022,4,1))
        self.assertEqual(sum(x>0 for x in p.values()),6)
        self.assertEqual(sum(x<0 for x in p.values()),6)
        self.assertAlmostEqual(sum(p.values()),0.)
        self.assertAlmostEqual(sum(abs(x) for x in p.values()),1.)
        lows=max(diff[s] for s,v in p.items() if v<0)
        highs=min(diff[s] for s,v in p.items() if v>0)
        self.assertGreaterEqual(highs,lows)

    def test_month_minus_two_no_current_information(self):
        self.assertEqual(h.month_minus(date(2023,1,5),2),date(2022,11,1))
        self.assertEqual(h.month_minus(date(2024,9,16),2),date(2024,7,1))
        a=mocked_monthly()
        p1=h.policy_basket(a,date(2022,4,1))[0]
        for c in a:
            a[c][date(2022,4,1)]=100
            a[c][date(2022,3,1)]=100
        p2=h.policy_basket(a,date(2022,4,1))[0]
        self.assertEqual(p1,p2)

    def test_no_live_economics_after_embargo(self):
        bars=mocked_bars(500,start=date(2023,1,2))
        with self.assertRaisesRegex(ValueError,"HOLDOUT_FORBIDDEN"):
            h.calendar_and_maps(bars)

    def test_common28_and_spot_theory_separate(self):
        data=mocked_bars(1850,start=date(2017,1,2))
        days,_,c=h.calendar_and_maps(data)
        self.assertEqual(c["fx_count"],28)
        self.assertEqual(len(days),1850)
        results=h.score(data,mocked_monthly())
        self.assertEqual(results["num_fx_pairs"],28)
        self.assertTrue(results["B_component_is_idealized_yield_not_executable"])
        self.assertFalse(results["broker_NET_certified"])
        self.assertFalse(results["economic_holdout_2024_09_17_onward_read"])
        self.assertEqual(results["certified_traders"],0)
        dev=results["performance"]["DEV"]
        self.assertGreater(dev["rebalance_decisions"],12)
        self.assertAlmostEqual(dev["assumed_2bp_cost_bp_capital_sum_not_compounded"],
                               dev["turnover_abs_weight_sides"]*2.)
        self.assertNotEqual(
            dev["SPOT_ONLY_AFTER_2BP_ASSUMED_COST"]["annualized_return_252"],
            dev["SPOT_PLUS_IDEALIZED_POLICY_ACCRUAL_NOT_BROKER_NET"]["annualized_return_252"])

    def test_reject_missing_one_pair(self):
        data=mocked_bars(500)
        del data["EURUSD"]
        with self.assertRaisesRegex(ValueError,"EXACT_FX28"):
            h.calendar_and_maps(data)


if __name__=="__main__":
    unittest.main()
