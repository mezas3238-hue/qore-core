"""H6a synthetic scientific contracts; never check economic real data in tests."""
from __future__ import annotations

import math
import random
import statistics
import unittest
from datetime import UTC,date,datetime,time,timedelta
from unittest.mock import patch

from qore.infrastructure.trader_lab import qore_native_h6a_existing_fx28_policy_vol20_sortino_v1 as h
from qore.infrastructure.trader_lab import qore_native_h5_bis_policy_fx28_one_test_v1 as h5


def dailies(n=2050,start=date(2016,9,19)):
    result={s:[] for s in h5.FX28}
    d=start
    t=0
    while t<n:
        if d.weekday()<5 and d<date(2024,9,17):
            for i,s in enumerate(h5.FX28):
                # Synthetic relative price gradients and mild oscillating volatility.
                price=1.3+0.00001*(i-14)*t+0.006*math.sin(t/11+i)
                result[s].append({
                    "date":d,
                    "entry_open":price,
                    "close":price+0.0003*math.sin(t/7+i),
                    "entry_ts":datetime.combine(d,time(0,10),tzinfo=UTC),
                    "last_ts":datetime.combine(d,time(23,55),tzinfo=UTC),
                })
            t+=1
        d+=timedelta(days=1)
        if d>date(2024,9,16):break
    return result


def synthetic_rates():
    rates={c:{} for c in h5.CURRENCY_BIS}
    d=date(2016,1,1)
    i=0
    while d<=date(2024,8,1):
        for k,c in enumerate(h5.CURRENCY_BIS):
            rates[c][d]=.15*(k-3)+.001*i
        d=date(d.year+1,1,1) if d.month==12 else date(d.year,d.month+1,1)
        i+=1
    return rates


class H6A(unittest.TestCase):
    def test_frozen_rules(self):
        self.assertEqual(h.WINDOW,20)
        self.assertEqual(h.ANNUAL_TARGET,.10)
        self.assertEqual(h.LEVERAGE_CAP,2.)
        self.assertEqual(h.FEE_PER_NOTIONAL_SIDE,.0002)
        self.assertEqual(h.BOOTSTRAP_REPS,10000)
        self.assertEqual(h.BOOTSTRAP_SEED,20261012)
        self.assertEqual(len(h.MAJORS),7)
        self.assertEqual(set(h.MAJORS)&set(h5.FX28),set(h.MAJORS))

    def test_no_current_or_future_close_for_vol(self):
        d=dailies(65)
        cal,maps,_=h5.calendar_and_maps if False else (None,None,None)
        # Local tiny future-history subset with no calendar eligibility check.
        dates=[x["date"] for x in d[h.MAJORS[0]]]
        maps={s:{x["date"]:x for x in d[s]} for s in d}
        a=h.vol_target_multiplier(dates,maps,34)
        for s in h.MAJORS:
            maps[s][dates[34]]["close"]*=2
            maps[s][dates[35]]["close"]*=2
        b=h.vol_target_multiplier(dates,maps,34)
        self.assertEqual(a,b)

    def test_past_20_day_close_can_change_vol(self):
        d=dailies(65)
        dates=[x["date"] for x in d[h.MAJORS[0]]]
        maps={s:{x["date"]:x for x in d[s]} for s in d}
        a=h.vol_target_multiplier(dates,maps,34)
        maps["EURUSD"][dates[33]]["close"]*=1.1
        b=h.vol_target_multiplier(dates,maps,34)
        self.assertNotEqual(a,b)

    def test_lookback_20_requires_21_closed_sessions(self):
        d=dailies(35)
        dates=[x["date"] for x in d[h.MAJORS[0]]]
        maps={s:{x["date"]:x for x in d[s]} for s in d}
        with self.assertRaisesRegex(ValueError,"INSUFFICIENT_COMPLETED_VOL20"):
            h.vol_target_multiplier(dates,maps,20)
        self.assertGreater(h.vol_target_multiplier(dates,maps,21)[0],0.)

    def test_vol_global_caps_leverage_even_when_very_low_vol(self):
        d=dailies(45)
        dates=[x["date"] for x in d[h.MAJORS[0]]]
        maps={s:{x["date"]:x for x in d[s]} for s in d}
        # extremely low-vol monotonic log slope across all seven majors
        for s in h.MAJORS:
            for i,x in enumerate(dates):
                maps[s][x]["close"]=1.1*math.exp(i*0.00001 + 0.00000001*math.sin(i))
        mult,vol=h.vol_target_multiplier(dates,maps,34)
        self.assertEqual(mult,2.)
        self.assertGreater(vol,0.)

    def test_compound_daily_into_monthly(self):
        r=h.monthly_compounded({
            date(2023,1,2):0.10,date(2023,1,3):-0.10,
            date(2023,2,1):.03,
        })
        self.assertEqual(len(r),2)
        self.assertAlmostEqual(r[0]["return"],-.01)
        self.assertAlmostEqual(r[1]["return"],.03)

    def test_negative_skew_not_misinterpreted_as_carry_edge(self):
        m=[{"month":f"2020-{(i%12)+1:02d}","return":(.006 if i%14 else -.07)}
           for i in range(36)]
        risk=h.risk_metrics(m,seed=33)
        self.assertLess(risk["sample_skewness_moment"],0)
        self.assertLess(risk["expected_shortfall_worst_5pct_months"],0)
        self.assertLess(risk["max_drawdown_month_end"],0)
        self.assertEqual(risk["ES5pct_tail_month_count"],2)
        self.assertEqual(risk["bootstrap_6_month_blocks"]["repetitions"],10000)
        self.assertEqual(risk["bootstrap_12_month_blocks_sensitivity_only"]["block_months"],12)

    def test_bootstrap_not_independent_month_assumption(self):
        data=[.01,.006,-.05,.012,.005,-.03,.009,.002,.003]*4
        a=h.bootstrap_mean_sortino(data,block=6,reps=120,seed=23)
        b=h.bootstrap_mean_sortino(data,block=6,reps=120,seed=23)
        self.assertEqual(a,b)
        self.assertEqual(a["block_months"],6)
        self.assertEqual(len(a["monthly_mean_95pct_CI"]),2)

    def test_economic_synthetic_28_complete_and_carry_separated(self):
        bars=dailies(2050)
        old=h.bootstrap_mean_sortino
        def quick(arr,block=6,reps=h.BOOTSTRAP_REPS,seed=h.BOOTSTRAP_SEED):
            return old(arr,block=block,reps=70,seed=seed)
        with patch.object(h,"bootstrap_mean_sortino",side_effect=quick):
            out=h.evaluate(bars,synthetic_rates())
        self.assertEqual(out["status"] in (
            "PROMISING_IDEALIZED_ONLY_NOT_CERTIFIED","NO_PROMOTION_EXPLORATORY"),True)
        self.assertTrue(out["DIAG_IS_ALREADY_EXPOSED_ADAPTIVE_EXPLORATORY"])
        self.assertFalse(out["holdout_2024_09_17_onward_opened"])
        self.assertFalse(out["source_broker_swaps_actual_forward_discount_verified"])
        self.assertEqual(out["certified_traders"],0)
        self.assertEqual(out["performance"]["DEV"]["monthly_rebalance_events"]>0,True)
        self.assertGreater(out["performance"]["DIAG"]["monthly_rebalance_events"],10)
        self.assertGreater(out["performance"]["DIAG"]["assumed_2bp_cost_bps_nav_uncompounded"],0)
        self.assertNotEqual(
            out["performance"]["DIAG"]["spot_only_assumed_2bp"]["CAGR_monthly_compounded"],
            out["performance"]["DIAG"]["spot_plus_ideal_policy_accrual_not_broker_NET"]["CAGR_monthly_compounded"])

    def test_embargo_guard_existing_calendar(self):
        data=dailies(100)
        sample=data["AUDUSD"][10].copy()
        sample["date"]=date(2024,9,17)
        sample["entry_ts"]=datetime.combine(sample["date"],time(0,10),tzinfo=UTC)
        data["AUDUSD"].append(sample)
        with self.assertRaisesRegex(ValueError,"HOLDOUT_FORBIDDEN"):
            h.evaluate(data,synthetic_rates())


if __name__=="__main__":unittest.main()
