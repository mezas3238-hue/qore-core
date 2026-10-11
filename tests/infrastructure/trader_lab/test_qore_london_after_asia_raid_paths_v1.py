"""Synthetic, outcome-blind causal tests of London TTrades-inspired paths."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.qore_london_after_asia_raid_paths_v1 import (
    at, bootstrap_delta, final_first_touch, inspect_day, summaries, wilson,
)

DAY = date(2026, 7, 15)


def b(t, o="1.1000", high="1.1002", low="1.0998", c="1.1000"):
    return CapitalizerM1Bar(
        symbol="EURUSD",opened_at=t,closed_at=t+timedelta(minutes=1),
        open=Decimal(o),high=Decimal(high),low=Decimal(low),
        close=Decimal(c),volume=1,digits=5,
    )


def standard_400():
    start=at(DAY-timedelta(days=1),20)
    xs={start+timedelta(minutes=i):b(start+timedelta(minutes=i)) for i in range(240)}
    london=at(DAY,2)
    for i in range(180+140):
        z=london+timedelta(minutes=i)
        xs[z]=b(z)
    return xs


def test_raid_checkpoint_and_reclaim_with_future_never_used_to_select():
    bars=standard_400()
    raid=at(DAY,2)
    bars[raid]=b(raid,high="1.1007",c="1.1000")
    first=inspect_day("EURUSD",DAY,bars)
    assert first["status"]=="CHECKPOINT_VALID"
    assert first["raid_side"]=="HIGH"
    assert first["checkpoint_state"]=="RECLAIM_INSIDE"
    assert first["checkpoint_at"]==(raid+timedelta(minutes=11)).isoformat()
    assert first["terminal_60"]=="NEUTRAL"
    modified=dict(bars)
    later=raid+timedelta(minutes=12)
    modified[later]=b(later,high="1.1200",low="1.0980",c="1.1100")
    second=inspect_day("EURUSD",DAY,modified)
    for key in ("raid_at","checkpoint_at","checkpoint_state","cisd_proxy_at",
                "structure_proxy_at","raid_depth_asia_units","retest_held"):
        assert first[key]==second[key]


def test_accepted_outside_requires_three_close_m1():
    bars=standard_400()
    raid=at(DAY,2)
    for i in range(11):
        z=raid+timedelta(minutes=i)
        bars[z]=b(z,o="1.10030",high="1.10080",low="1.10010",c="1.10040")
    r=inspect_day("EURUSD",DAY,bars)
    assert r["checkpoint_state"]=="ACCEPTED_OUTSIDE"
    assert r["raid_depth_asia_units"]>0
    assert not r["reclaim_before_checkpoint"]


def test_strict_asia_and_gap_censor_after_checkpoint():
    bars=standard_400()
    raid=at(DAY,2)
    bars[raid]=b(raid,high="1.1007")
    del bars[at(DAY-timedelta(days=1),20)]
    assert inspect_day("EURUSD",DAY,bars)["status"]=="ASIA_INCOMPLETE"
    bars=standard_400()
    bars[raid]=b(raid,high="1.1007")
    del bars[raid+timedelta(minutes=12)]
    r=inspect_day("EURUSD",DAY,bars)
    assert r["status"]=="CHECKPOINT_VALID"
    assert r["terminal_60"]=="CENSORED"
    assert r["first_touch_60"]=="CENSORED_GAP"
    assert r["checkpoint_state"]=="RECLAIM_INSIDE"


def test_no_raid_and_both_same_m1():
    xs=standard_400()
    assert inspect_day("EURUSD",DAY,xs)["status"]=="NO_RAID"
    t=at(DAY,2)
    xs[t]=b(t,high="1.1008",low="1.0990")
    assert inspect_day("EURUSD",DAY,xs)["status"]=="BOTH_ASIA_EXTREMES_AMBIGUOUS"


def test_directional_first_touch_does_not_impose_stop_first():
    t=at(DAY,2)
    both=b(t,high="1.1009",low="1.0990")
    assert final_first_touch([both],Decimal("1.1000"),1,Decimal(".0020")) == "BOTH_SAME_M1_UNRESOLVED"
    assert final_first_touch([both],Decimal("1.1000"),-1,Decimal(".0020")) == "BOTH_SAME_M1_UNRESOLVED"


def test_wilson_and_empty_diff():
    assert wilson(0,0) is None
    assert wilson(2,4)[0] < .5 < wilson(2,4)[1]
    assert bootstrap_delta([])["reason"]=="INSUFFICIENT_TWO_STATES"
    assert summaries([])["checkpoint_valid"]==0


def test_clock_ny_dst_without_using_fixed_utc_offset():
    winter=date(2026,2,11)
    summer=date(2026,7,15)
    assert at(winter,2).hour == 7
    assert at(summer,2).hour == 6
