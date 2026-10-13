"""Frozen FX28 original-M5 Asia-range to London expansion, one exploratory screen.

Prereg ancestor b0133535d6adb89724b827e9151c4ab7a109c154 BEFORE outcomes.
Europe/London local DST, original provider M5, 10min delayed entry,
static 1/28 notional each market to avoid hindsight portfolio sizing.
No certified BID/ASK, no broker NET, not a TTrades/ICT implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from qore.research.alpha2_fx28_carry_one_test import CCYS, FX28
from qore.research.alpha2_fx28_policy_vol20_final import full_readonly_original_rows
from qore.research.alpha2_intermarket import Bar, _check_bar
from qore.research.alpha2_lab_h4_extract import source33_manifest, verify_source

IDENTITY="QORE_ALPHA2_FX28_ASIA_RANGE_LONDON_BREAK_CONTINUE_FIXED_V1"
PREREG="b0133535d6adb89724b827e9151c4ab7a109c154"
LONDON=ZoneInfo("Europe/London")
FIRST_DAY=date(2016,9,17)
END_EXCL=date(2026,9,17)
SPLIT=date(2022,1,1)
RETAINED_EXPOSED=date(2024,9,17)
MARKET_NOTIONAL=1/28
COST_SIDE_BPS=2.0
STRESS_SIDE_BPS=5.0
B=2000
SEED=20261012

def _minutes(t:datetime)->int:
    local=t.astimezone(LONDON)
    return local.hour*60+local.minute


def _complete_session(
    local_day:date, asia:dict[int,Bar], active:dict[int,Bar],
)->dict:
    """Reference trade uses at most M5 CLOSE breakout and M5 OPEN t+10."""
    if (len(asia)!=84 or any(i*5 not in asia for i in range(84))
        or len(active)!=48
        or any(8*60+i*5 not in active for i in range(48))):
        return {"day":local_day.isoformat(),"status":"M5_SESSION_MISSING"}
    highest=max(x.high for x in asia.values())
    lowest=min(x.low for x in asia.values())
    if not (0<lowest<=highest):
        raise ValueError("LONDON_ASIA_RANGE_INVALID")
    for i in range(22):  # first bar at 08:00 -> last at 09:45, London local
        breakout=active[480+5*i]
        side=int(breakout.close>highest)-int(breakout.close<lowest)
        if side==0:
            continue
        # Signal known after breakout closes t+5, enter on t+10 (additional 5min).
        enter=active[480+5*(i+2)]
        exitbar=active[715]  # 11:55 M5 CLOSE at noon, no overnight carry.
        if enter.at <= breakout.at+timedelta(minutes=5):
            raise ValueError("LONDON_LOOKAHEAD_OR_SAME_BAR_FILL")
        signed=side*10000*(exitbar.close/enter.open-1)
        if not math.isfinite(signed):
            raise ValueError("LONDON_NONFINITE_EVENT_PNL")
        return {
            "day":local_day.isoformat(),"status":"TRADE",
            "direction":side,
            "breakout_local_hhmm":f"{8+i//12:02d}:{(i%12)*5:02d}",
            "entry_local_hhmm":f"{8+(i+2)//12:02d}:{((i+2)%12)*5:02d}",
            "reference_exit_local_hhmm":"12:00",
            "gross_signed_reference_bps":signed,
            "assumed_2bps_side_cost_event_bps":4.0,
            "assumed_5bps_side_stress_event_bps":10.0,
            "reference_minus_assumed_cost_bps":signed-4.,
            "reference_minus_assumed_stress_bps":signed-10.,
        }
    return {"day":local_day.isoformat(),"status":"NO_FIRST_CLOSE_BREAKOUT"}


def extract_symbol_rows(bars:Iterator[Bar], symbol:str)->tuple[list[dict],dict]:
    if symbol not in FX28:
        raise ValueError("LONDON_ONLY_FX28")
    outcomes=[]
    counts=Counter()
    last_timestamp=None
    current_day=None
    asia={}
    active={}
    source_rows=0

    def flush()->None:
        if current_day is None or not FIRST_DAY<=current_day<END_EXCL:
            return
        if current_day.weekday()>=5:
            return
        result=_complete_session(current_day,asia,active)
        outcomes.append(result)
        counts[result["status"]]+=1

    for bar in bars:
        _check_bar(bar)
        if (bar.at.tzinfo is None or bar.at.utcoffset().total_seconds()!=0
            or (last_timestamp is not None and bar.at<=last_timestamp)
            or bar.at.minute%5 or bar.at.second or bar.at.microsecond):
            raise ValueError("LONDON_NOT_NATIVE_STRICT_UTC_M5")
        last_timestamp=bar.at
        if bar.at.date()>=END_EXCL:
            raise ValueError("LONDON_ABSOLUTE_2026_SOURCE_CUTOFF")
        source_rows+=1
        lond=bar.at.astimezone(LONDON)
        d=lond.date()
        minute=lond.hour*60+lond.minute
        if d!=current_day:
            flush()
            current_day=d
            asia={}
            active={}
        # Exclude 07:00–07:55 entirely; no future signal known at 08:00.
        if 0<=minute<420:
            if minute in asia:
                raise ValueError("LONDON_DUPLICATE_ASIA_M5")
            asia[minute]=bar
        if 480<=minute<720:
            if minute in active:
                raise ValueError("LONDON_DUPLICATE_TRADING_M5")
            active[minute]=bar
    flush()
    if len({x["day"] for x in outcomes})!=len(outcomes):
        raise ValueError("LONDON_DUPLICATED_SESSION_DAY")
    return outcomes,{
        "symbol":symbol,"original_native_M5_rows_pre_cutoff":source_rows,
        "eligible_local_weekdays":len(outcomes),
        "source_days_status_counts":dict(counts),
        "distinct_london_dst_offsets_are_not_forcefixed":True,
        "original_raw_prices_not_uploaded":True,
    }


def extract_verified(symbol:str, source:Path, manifest:Path,
                     temp:Path, atlas:Path|None)->dict:
    proof=verify_source(symbol,source,source33_manifest(manifest),atlas)
    records,stats=extract_symbol_rows(full_readonly_original_rows(source,symbol),symbol)
    filename=temp/f"{symbol}.json"
    temp.mkdir(parents=True,exist_ok=True)
    if filename.exists():
        raise ValueError("LONDON_NO_OVERWRITE_UNVERIFIED")
    filename.write_text(json.dumps({
        "symbol":symbol,"original_signed33_SHA":proof["native_original_source_sha_verified"],
        "source_cohort":proof["source_cohort"],
        "census":stats,"private_session_events":records,
    },separators=(",",":"))+"\n",encoding="utf-8")
    (temp/(filename.name+".sha256")).write_text(
        hashlib.sha256(filename.read_bytes()).hexdigest()+"  "+filename.name+"\n",
        encoding="utf-8")
    return {"symbol":symbol,"SHA_verified":True,
            "original_M5_rows":stats["original_native_M5_rows_pre_cutoff"],
            "local_eligible_days":stats["eligible_local_weekdays"],
            "statuses":stats["source_days_status_counts"],"orders":0}


def _week_list(start:date,stop:date)->list[str]:
    """Each calendar week counted once, includes weeks where all 28 are cash."""
    out=[]
    prev=None
    d=start
    while d<stop:
        iso=d.isocalendar()
        wk=f"{iso.year:04d}-W{iso.week:02d}"
        if wk!=prev:
            out.append(wk)
            prev=wk
        d+=timedelta(days=1)
    return out


def _bootstrap4(data:list[float],seed:int)->list[float]:
    if not data:
        raise ValueError("LONDON_EMPTY_CALENDAR")
    rng=random.Random(seed)
    n=len(data)
    output=[]
    for _ in range(B):
        path=[]
        while len(path)<n:
            i=rng.randrange(n)
            path.extend(data[(i+j)%n] for j in range(4))
        output.append(sum(path[:n])/n)
    output.sort()
    return [output[49],output[1949]]


def _drawdown_week(returns:list[float])->float:
    equity=1.0
    max_equity=1.0
    worst=0.
    for val in returns:
        equity*=1+val/10000
        max_equity=max(max_equity,equity)
        worst=max(worst,1-equity/max_equity)
    return worst


def aggregate(extracted:Path)->dict:
    files=sorted(extracted.glob("*.json"))
    if len(files)!=28:
        raise ValueError("LONDON_ORIGINAL_M5_EXACT28_EPHEMERAL_REQUIRED")
    panel={}
    source_census={}
    for f in files:
        s=f.stem
        if s not in FX28 or s in panel:
            raise ValueError("LONDON_ORIGINAL_FX28_EXACT_ROSTER")
        expected=hashlib.sha256(f.read_bytes()).hexdigest()+"  "+f.name
        if f.with_name(f.name+".sha256").read_text().strip()!=expected:
            raise ValueError("LONDON_PRIVATE_SESSION_SHA_MISMATCH")
        j=json.loads(f.read_text())
        if j["symbol"]!=s or j["original_signed33_SHA"] is not True:
            raise ValueError("LONDON_ORIGINAL_SOURCE_NOT_VERIFIED")
        rows=j["private_session_events"]
        if len(rows)!=len({r["day"] for r in rows}):
            raise ValueError("LONDON_DUPLICATE_PRIVATE_DAY")
        panel[s]={date.fromisoformat(r["day"]):r for r in rows}
        source_census[s]=j["census"]
    if set(panel)!=set(FX28):
        raise ValueError("LONDON_SOURCE_ROSTER_INCOMPLETE")
    events=defaultdict(list)
    for sym,records in panel.items():
        for day,row in records.items():
            if row["status"]=="TRADE":
                events[day].append((sym,row))
    # Every position is allocated fixed 1/28 BEFORE knowing number of signals.
    daily={}
    for d,sigs in events.items():
        gross=sum(r["gross_signed_reference_bps"] for _,r in sigs)/28
        cost=4*len(sigs)/28
        stresscost=10*len(sigs)/28
        cur={c:0. for c in CCYS}
        for sym,r in sigs:
            side=r["direction"]
            cur[sym[:3]]+=side/28
            cur[sym[3:]]-=side/28
        daily[d]={
            "signals":len(sigs),
            "gross_bps":gross,
            "cost_assumed_portfolio_bps":cost,
            "model_cost_proxy_bps":gross-cost,
            "model_stress5bp_side_bps":gross-stresscost,
            "gross_notional_exposure":len(sigs)/28,
            "max_abs_currency_exposure":max(map(abs,cur.values())),
        }
    eraspec={
        "DEVELOPMENT":(FIRST_DAY,SPLIT),
        "DIAGNOSTIC":(SPLIT,END_EXCL),
        "PREVIOUSLY_EXPOSED_2024_2026":(RETAINED_EXPOSED,END_EXCL),
    }
    eras={}
    for idx,(era,(start,end)) in enumerate(eraspec.items()):
        weekkeys=_week_list(start,end)
        active_week=defaultdict(int)
        pnl=defaultdict(float)
        gross=defaultdict(float)
        stress=defaultdict(float)
        source_eligible=Counter()
        for symbol,records in panel.items():
            for day,row in records.items():
                if start<=day<end:
                    source_eligible[row["status"]]+=1
        selected=[(d,x) for d,x in daily.items() if start<=d<end]
        for d,item in selected:
            iso=d.isocalendar()
            wk=f"{iso.year:04d}-W{iso.week:02d}"
            if wk not in weekkeys:
                raise ValueError("LONDON_WEEK_OUTSIDE_CALENDAR")
            pnl[wk]+=item["model_cost_proxy_bps"]
            gross[wk]+=item["gross_bps"]
            stress[wk]+=item["model_stress5bp_side_bps"]
            active_week[wk]+=item["signals"]
        vector=[pnl[k] for k in weekkeys]
        before=[gross[k] for k in weekkeys]
        stressv=[stress[k] for k in weekkeys]
        n_active=sum(active_week[k]>0 for k in weekkeys)
        signal_count=sum(item["signals"] for _,item in selected)
        avg_active_n=(mean(item["signals"] for _,item in selected)
                      if selected else 0)
        sample_gate=n_active>=52
        eras[era]={
            "calendar_ISO_weeks_including_zero_cash":len(weekkeys),
            "weeks_with_at_least_one_complete_source_signal":n_active,
            "signal_sample_gate_52w":sample_gate,
            "daily_sessions_with_any_signal":len(selected),
            "symbol_trades":signal_count,
            "mean_signals_per_traded_day":avg_active_n,
            "mean_gross_reference_bps_per_calendar_week":mean(before),
            "mean_2bp_side_cost_proxy_bps_per_calendar_week":mean(vector),
            "mean_5bp_side_stress_proxy_bps_per_calendar_week":mean(stressv),
            "CI95_weekly_proxy_4week_synchronized_block_bps":_bootstrap4(vector,SEED+idx),
            "weekly_model_drawdown_fraction_NOT_real_NAV":_drawdown_week(vector),
            "model_worst_week_bps":min(vector),
            "highest_daily_currency_net_exposure":max(
                (i["max_abs_currency_exposure"] for _,i in selected),default=0),
            "source_symbol_day_eligibility_statuses":dict(source_eligible),
            "original_28_FX_weights_fixed_ex_ante":True,
        }
    if not all(
        v["signal_sample_gate_52w"]
        for k,v in eras.items() if k!="PREVIOUSLY_EXPOSED_2024_2026"
    ):
        status="SESSION_EXPANSION_UNDERPOWERED"
    elif all(eras[e]["mean_2bp_side_cost_proxy_bps_per_calendar_week"]>0
             and eras[e]["CI95_weekly_proxy_4week_synchronized_block_bps"][0]>0
             for e in ("DEVELOPMENT","DIAGNOSTIC")):
        status="SESSION_EXPANSION_EXPLORATORY_ONLY_NEEDS_FRESH_OOS_BROKER_NET"
    else:
        status="SESSION_EXPANSION_PREDECLARED_SCREEN_FAILED_STOP"
    return {
        "identity":IDENTITY,"prereg_ancestor":PREREG,
        "status":status,"closed_to_posthoc_tuning_on_exposed_data":True,
        "original28_SOURCES_SHA_before_M5":True,
        "source_census_without_raw_price":source_census,
        "conclusion_not_true_BROKER_NET":True,
        "2016_2026_already_exposed_in_Alpha2":True,
        "single_event_Asia_00_07_London_break08_0945_entry_t_plus_10_exit_noon":True,
        "FX28_count":len(panel),"CCY_count":len(CCYS),
        "cumulative_traded_days_over_eras_with_overlaps":len(daily),
        "eras":eras,"0_orders":True,"UTC001_certified":False,
    }


def main()->None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="action",required=True)
    x=sub.add_parser("extract")
    x.add_argument("symbol",choices=FX28)
    x.add_argument("original",type=Path)
    x.add_argument("source33",type=Path)
    x.add_argument("ephemeral",type=Path)
    x.add_argument("--aggregate12",type=Path)
    y=sub.add_parser("finish")
    y.add_argument("ephemeral",type=Path)
    y.add_argument("out",type=Path)
    a=p.parse_args()
    if a.action=="extract":
        data=extract_verified(a.symbol,a.original,a.source33,a.ephemeral,a.aggregate12)
    else:
        data=aggregate(a.ephemeral)
        a.out.mkdir(parents=True,exist_ok=True)
        dest=a.out/"alpha2-FX28-asia-london-session-expansion-2016-2026-one.json"
        dest.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        (a.out/"OUTPUT_SHA256SUMS.txt").write_text(
            hashlib.sha256(dest.read_bytes()).hexdigest()+"  "+dest.name+"\n",
            encoding="utf-8",
        )
        data={"status":data["status"],
              "DEV":data["eras"]["DEVELOPMENT"]["mean_2bp_side_cost_proxy_bps_per_calendar_week"],
              "DIAG":data["eras"]["DIAGNOSTIC"]["mean_2bp_side_cost_proxy_bps_per_calendar_week"],
              "FX28":data["FX28_count"],"orders":0,"broker_NET":"BLOCKED"}
    print(json.dumps(data,sort_keys=True))


if __name__=="__main__":
    main()
