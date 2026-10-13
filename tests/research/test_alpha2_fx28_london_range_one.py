"""Entirely synthetic source; historical QORE OHLC is never used in unit tests."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from qore.research.alpha2_fx28_carry_one_test import FX28
from qore.research.alpha2_fx28_london_range_one import (
    LONDON,
    _complete_session,
    _week_list,
    aggregate,
    extract_symbol_rows,
)
from qore.research.alpha2_intermarket import Bar


def synthetic_london_day(d:date, direction=1):
    local=datetime(d.year,d.month,d.day,0,0,tzinfo=LONDON)
    bars=[]
    # Exact 84 pre-London reference bars at 00:00-06:55.
    for i in range(84):
        t=(local+timedelta(minutes=5*i)).astimezone(UTC)
        bars.append(Bar(t,100.0,100.5,99.5,100.0))
    # London 08:00 breakout is completed at08:05. Entry must be 08:10.
    for i in range(48):
        t=(local+timedelta(hours=8,minutes=5*i)).astimezone(UTC)
        if i==0:
            closes=100.9 if direction==1 else 99.1
            bars.append(Bar(t,100.0,max(101.0,closes),min(99.,closes),closes))
        elif i==2:
            bars.append(Bar(t,100.0,100.2,99.8,100.0))
        elif i==47:
            bars.append(Bar(t,101.5,101.6,101.4,101.5))
        else:
            bars.append(Bar(t,100.0,100.2,99.8,100.0))
    return sorted(bars,key=lambda b:b.at)


@pytest.mark.parametrize("ymd", [(2026,1,12),(2026,7,13)])
def test_local_london_dst_open_and_10min_causal_delay(ymd):
    source=synthetic_london_day(date(*ymd))
    cases,meta=extract_symbol_rows(iter(source),"AUDJPY")
    assert len(cases)==1
    result=cases[0]
    assert result["status"]=="TRADE"
    assert result["direction"]==1
    assert result["breakout_local_hhmm"]=="08:00"
    assert result["entry_local_hhmm"]=="08:10"
    assert result["reference_exit_local_hhmm"]=="12:00"
    assert result["gross_signed_reference_bps"]==pytest.approx(150.)
    assert result["reference_minus_assumed_cost_bps"]==pytest.approx(146.)
    assert result["reference_minus_assumed_stress_bps"]==pytest.approx(140.)
    assert meta["source_days_status_counts"]["TRADE"]==1
    # 08:00 London local maps to different UTC starts in Jan vs July, not fixed UTC.
    start=[b for b in source if b.at.astimezone(LONDON).hour==8
           and b.at.astimezone(LONDON).minute==0][0]
    assert start.at.hour==(8 if ymd[1]==1 else 7)


def test_missing_one_asia_or_london_M5_day_censors_all_not_filled():
    d=date(2026,1,12)
    for hm in ((2,15),(11,55)):
        source=synthetic_london_day(d)
        drop=[b for b in source if (b.at.astimezone(LONDON).hour,
                                    b.at.astimezone(LONDON).minute)==hm][0]
        source.remove(drop)
        out,_=extract_symbol_rows(iter(source),"EURGBP")
        assert out[0]["status"]=="M5_SESSION_MISSING"


def test_price_move_on_breakout_or_intervening_bar_cannot_be_marked_as_entry():
    src=synthetic_london_day(date(2026,1,12))
    fixed,_=extract_symbol_rows(iter(src),"GBPJPY")
    for j,b in enumerate(src):
        loc=b.at.astimezone(LONDON)
        if (loc.hour,loc.minute)==(8,5):
            # An intermediate bar may have arbitrary OHLC but price at 08:10 is unchanged.
            src[j]=Bar(b.at,open=130,high=141,low=91,close=111)
    same,_=extract_symbol_rows(iter(src),"GBPJPY")
    assert same[0]["gross_signed_reference_bps"]==fixed[0]["gross_signed_reference_bps"]


def test_neutral_asia_range_no_first_close_break_has_no_trade():
    source=synthetic_london_day(date(2026,1,12))
    new=[]
    for b in source:
        lon=b.at.astimezone(LONDON)
        if lon.hour==8 and lon.minute==0:
            new.append(Bar(b.at,100,100.2,99.8,100))
        else:
            new.append(b)
    out,_=extract_symbol_rows(iter(new),"AUDJPY")
    assert out[0]["status"]=="NO_FIRST_CLOSE_BREAKOUT"


def test_weekly_portfolio_notional_fixed_1_div_28_and_cost_not_trade_count(tmp_path:Path):
    d1="2020-01-13"
    d2="2023-01-16"
    for s in FX28:
        # Exact roster but only one pair signals, others no breakout.
        entries=[
            {"day":d1,"status":"TRADE","direction":1,"gross_signed_reference_bps":100}
            if s=="AUDJPY" else {"day":d1,"status":"NO_FIRST_CLOSE_BREAKOUT"},
            {"day":d2,"status":"TRADE","direction":-1,"gross_signed_reference_bps":-100}
            if s=="EURCHF" else {"day":d2,"status":"NO_FIRST_CLOSE_BREAKOUT"},
        ]
        f=tmp_path/f"{s}.json"
        f.write_text(json.dumps({"symbol":s,"original_signed33_SHA":True,
            "source_cohort":"SYNTHETIC_TEST_ONLY",
            "census":{"source_days_status_counts":{}},
            "private_session_events":entries})+"\n")
        (tmp_path/(f.name+".sha256")).write_text(
            hashlib.sha256(f.read_bytes()).hexdigest()+"  "+f.name+"\n")
    result=aggregate(tmp_path)
    assert result["FX28_count"]==28
    assert result["status"]=="SESSION_EXPANSION_UNDERPOWERED"
    # One 100 bp active signal is 1/28 notional and costs just 4/28 bp/week.
    dev=result["eras"]["DEVELOPMENT"]
    assert dev["weeks_with_at_least_one_complete_source_signal"]==1
    assert dev["symbol_trades"]==1
    n=dev["calendar_ISO_weeks_including_zero_cash"]
    assert dev["mean_2bp_side_cost_proxy_bps_per_calendar_week"]==pytest.approx(
        96/28/n
    )
    assert dev["mean_5bp_side_stress_proxy_bps_per_calendar_week"]==pytest.approx(
        90/28/n
    )
    assert dev["highest_daily_currency_net_exposure"]==pytest.approx(1/28)
    assert result["UTC001_certified"] is False
    assert result["conclusion_not_true_BROKER_NET"] is True


def test_native_source_2026_cutoff_is_not_legacy_2024_cutoff():
    d=date(2026,1,12)
    a,_=extract_symbol_rows(iter(synthetic_london_day(d)),"AUDJPY")
    assert a[0]["status"]=="TRADE"
    bad=Bar(datetime(2026,9,17,0,0,tzinfo=UTC),100,101,99,100)
    with pytest.raises(ValueError,match="2026_SOURCE_CUTOFF"):
        extract_symbol_rows(iter([bad]),"AUDJPY")


def test_iso_week_calendar_no_trade_weeks_explicit():
    weeks=_week_list(date(2024,10,1),date(2024,11,1))
    assert weeks[0]=="2024-W40"
    assert weeks[-1]=="2024-W44"
    assert len(weeks)==5
