"""SMT T0: clocks, cross-symbol causality, censorship, exactly one daily leader."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from qore.infrastructure.trader_lab.qore_london_after_asia_raid_paths_v1 import at
from qore.infrastructure.trader_lab.qore_london_smt_frequency_t0_v1 import (
    STATUS_CONFIRM, STATUS_PROXY, scan_pair, wilson,
)


def sample() -> dict:
    rows={}
    for symbol in ("EURUSD","GBPUSD"):
        rows[symbol]={
            "symbol":symbol,
            "ny_day":"2026-07-15",
            "asia_M1_observed":240,
            "asia_high":"1.10000",
            "asia_low":"1.09000",
            "london":{str(i):["1.09900","1.09100"] for i in range(180)},
        }
    rows["EURUSD"]["london"]["0"]=["1.10100","1.09100"]
    return rows


def test_no_confirmation_asof_11_m1_and_future_unchanged() -> None:
    orig=sample()
    x=scan_pair(orig)
    assert x["status"]==STATUS_PROXY
    assert x["leader_symbol"]=="EURUSD"
    assert x["leader_side"]=="HIGH"
    assert x["mate_first_confirmation_index"] is None
    assert x["anchor_opened_at"]=="2026-07-15T06:00:00+00:00"
    assert x["available_at"]=="2026-07-15T06:11:00+00:00"
    # All price changes after signal available_at have no causal impact.
    orig["GBPUSD"]["london"]["11"]=["1.20000","1.09100"]
    assert scan_pair(orig)==x


def test_mate_confirmation_within_ten_minutes_not_SMT() -> None:
    x=sample()
    x["GBPUSD"]["london"]["10"]=["1.10200","1.09100"]
    result=scan_pair(x)
    assert result["status"]==STATUS_CONFIRM
    assert result["mate_first_confirmation_index"]==10


def test_both_pairs_same_minute_not_counted_as_smt() -> None:
    x=sample()
    x["GBPUSD"]["london"]["0"]=["1.10050","1.09100"]
    assert scan_pair(x)["status"]=="SIMULTANEOUS_SAME_DIRECTION"
    x["GBPUSD"]["london"]["0"]=["1.09900","1.08900"]
    assert scan_pair(x)["status"]=="SIMULTANEOUS_OPPOSITE_DIRECTION"


def test_dual_high_low_in_one_m1_censored() -> None:
    x=sample()
    x["EURUSD"]["london"]["0"]=["1.10100","1.08900"]
    assert scan_pair(x)["status"]=="AMBIGUOUS_DUAL_EDGE_SAME_M1"


def test_mate_opposite_break_remains_nonconfirmation() -> None:
    x=sample()
    x["GBPUSD"]["london"]["7"]=["1.09900","1.08900"]
    r=scan_pair(x)
    assert r["status"]==STATUS_PROXY
    assert r["mate_opposite_breach_in_window"] is True


def test_missing_one_early_minute_does_not_invent_first_raid() -> None:
    x=sample()
    del x["GBPUSD"]["london"]["0"]
    r=scan_pair(x)
    assert r["status"]=="CENSORED_PRE_ANCHOR_PAIR_GAP"
    assert r["missing_symbol"]=="GBPUSD"


def test_missing_followup_or_too_late_to_observe_ten_minutes() -> None:
    x=sample()
    del x["GBPUSD"]["london"]["6"]
    assert scan_pair(x)["status"]=="CENSORED_POST_ANCHOR_PAIR_GAP"
    x=sample()
    x["EURUSD"]["london"]["0"]=["1.09900","1.09100"]
    x["EURUSD"]["london"]["175"]=["1.10100","1.09100"]
    assert scan_pair(x)["status"]=="CENSORED_LONDON_10M_WINDOW"


def test_ny_summer_and_winter_civil_time_and_no_asia() -> None:
    assert at(date(2026,7,15),2).hour==6
    assert at(date(2026,2,11),2).hour==7
    x=sample()
    x["GBPUSD"]["asia_M1_observed"]=239
    assert scan_pair(x)["status"]=="CENSORED_ASIA_PAIRED"


def test_wilson_is_descriptive_no_rate_when_zero_denominator() -> None:
    assert wilson(0,0) is None
    assert wilson(5,10)[0] < .5 < wilson(5,10)[1]
