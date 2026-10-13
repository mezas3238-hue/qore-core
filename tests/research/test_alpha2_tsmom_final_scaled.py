"""Synthetic-only source-free risk-scaled time series momentum and stop tests."""
from datetime import date, timedelta

import pytest

from qore.research.alpha2_tsmom_daily_weekly import Day
from qore.research.alpha2_tsmom_final_scaled import _risk_weight, replay


def days(n=315):
    when=date(2020,1,1)
    result=[]
    for i in range(n):
        while when.weekday()>4:
            when+=timedelta(days=1)
        c=100 + i*.02 + (0.23 if i%3==0 else -.18)
        result.append(Day(when,c-.09,c,36))
        when+=timedelta(days=1)
    return result


def test_risk_scaling_only_uses_prior_20_and_252_closes():
    d=days()
    w, v, cap=_risk_weight(d,260)
    assert w>0 and v>0 and abs(w)<=3 and type(cap) is bool
    item=d[260]
    d[260]=Day(item.utc_day,1,99999999,36)
    assert _risk_weight(d,260)==(w,v,cap)


def test_one_bp_per_side_is_scaled_by_absolute_exposure():
    x=replay("EURUSD",days())
    assert x["count_events"]>1
    for e in x["events"]:
        w=e["signed_risk_scaled_exposure"]
        assert e["assumed_1bp_each_side_cost_bps"]==pytest.approx(2*abs(w))
        assert e["gross_minus_assumed_cost_proxy_bps"]==pytest.approx(
            e["gross_risk_scaled_reference_bps"]-2*abs(w)
        )
        assert e["broker_NET_NOT_VERIFIED"]
    assert len({e["iso_week"] for e in x["events"]})==x["count_events"]


def test_zero_vol_or_signal_yields_cash_no_division_by_zero():
    d=days()
    for j in range(239,260):
        a=d[j]
        d[j]=Day(a.utc_day,100,100,36)
    assert _risk_weight(d,260)[0]==0


def test_censor_at_2022_era_and_zero_aliases():
    d=days(n=500)
    x=replay("EURUSD",d)
    assert all(
        not (date.fromisoformat(e["decision_reference_utc_day"]) < date(2022,9,17)
             <= date.fromisoformat(e["last_native_reference_exit_day"]))
        for e in x["events"]
    )
    with pytest.raises(ValueError,match="SYMBOL_OR_DAILY_ORDER"):
        replay("US500",d)
    with pytest.raises(ValueError,match="WARMUP_INCOMPLETE"):
        _risk_weight(d,22)


def test_missing_five_sessions_does_not_synthesize_exit():
    d=days(n=255)
    x=replay("AUDUSD",d)
    assert x["count_events"]==0
    assert x["censored_or_abstained"]["INSUFFICIENT_FIVE_SESSIONS"]>=1
