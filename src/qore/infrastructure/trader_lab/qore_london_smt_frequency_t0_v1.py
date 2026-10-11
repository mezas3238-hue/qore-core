"""LONDON SMT T0: paired 10M first-raid nonconfirmation frequency, not trading.

QORE fixed-timing operational proxy, NOT author-certified TTrades SMT.
Uses only strict provider-native M1 and a first-online simultaneous two-FX
clock; outcomes, profitability and RECLAIM/ACCEPTED are never accessed.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END, DEV_WINDOW_START,
)
from qore.infrastructure.trader_lab.qore_london_after_asia_raid_paths_v1 import at

ID = "QORE_LONDON_EURGBP_FIRST_ANCHOR_10M_NONCONFIRMATION_T0_V1"
SYMBOLS = ("EURUSD", "GBPUSD")
NY_DAYS = 261
WINDOW_M1 = 180
WINDOW_MATE = 10
SOURCE_LEDGER = "london-asia-postraid-*-daily-paths.jsonl"
STATUS_PROXY = "SMT_NONCONFIRMATION_10M"
STATUS_CONFIRM = "CONFIRMED_SAME_DIRECTION_WITHIN_10M"


def load_market(native: Path, frozen: Path, output: Path) -> dict[str, Any]:
    files = sorted(frozen.rglob(SOURCE_LEDGER))
    if len(files) != 1:
        raise ValueError("one frozen TTrades path ledger per symbol is mandatory")
    frozen_rows = [json.loads(l) for l in files[0].read_text().splitlines() if l.strip()]
    if len(frozen_rows) != NY_DAYS or len({x["ny_day"] for x in frozen_rows}) != NY_DAYS:
        raise ValueError("original first-raid source days drift")
    symbols = {x["symbol"] for x in frozen_rows}
    if len(symbols) != 1 or not symbols.issubset(set(SYMBOLS)):
        raise ValueError("source not exactly one London FX symbol")
    symbol = next(iter(symbols))
    m1: dict[datetime, Any] = {}
    for bar in iter_cibo_m1(native):
        if not DEV_WINDOW_START <= bar.opened_at < DEV_WINDOW_END:
            continue
        if bar.symbol != symbol or bar.opened_at in m1:
            raise ValueError("mixed or duplicate provider-native M1")
        m1[bar.opened_at] = bar
    if len(m1) < 300_000:
        raise ValueError("insufficient historical native M1")
    result=[]
    for old in frozen_rows:
        day=date.fromisoformat(old["ny_day"])
        asia_start=at(day-timedelta(days=1),20)
        asia_end=at(day,0)
        london_start=at(day,2)
        london_end=at(day,5)
        if asia_end-asia_start != timedelta(minutes=240) or london_end-london_start != timedelta(minutes=WINDOW_M1):
            raise ValueError("NY DST bucket invalid: stop, no assumption")
        asia=[m1.get(asia_start+timedelta(minutes=k)) for k in range(240)]
        found=sum(bar is not None for bar in asia)
        if old["asia_minutes_observed"] != found:
            raise ValueError(f"source Asia coverage changed {symbol}/{day}: {found} != {old['asia_minutes_observed']}")
        if found==240:
            high=max(x.high for x in asia if x is not None)
            low=min(x.low for x in asia if x is not None)
            if str(high)!=old["asia_high"] or str(low)!=old["asia_low"]:
                raise ValueError(f"source Asia extrema mismatch {symbol}/{day}")
            asia_high,asia_low = str(high),str(low)
        else:
            asia_high=asia_low=None
        london={}
        for k in range(WINDOW_M1):
            t=london_start+timedelta(minutes=k)
            b=m1.get(t)
            if b is not None:
                london[str(k)]=[str(b.high),str(b.low)]
        # The frozen original's first raid is an independent reconciliation
        # witness; it is NOT used to select or construct any SMT signal.
        if found==240 and old["raid_at"] is not None and old["status"] in (
            "CHECKPOINT_VALID","LONDON_CHECKPOINT_OUT_OF_WINDOW",
            "BOTH_ASIA_EXTREMES_AMBIGUOUS",
        ):
            computed=None
            for k in range(WINDOW_M1):
                row=london.get(str(k))
                if row is None:
                    break
                if Decimal(row[0])>Decimal(asia_high) or Decimal(row[1])<Decimal(asia_low):
                    computed=london_start+timedelta(minutes=k)
                    break
            if computed is None or computed.isoformat()!=old["raid_at"]:
                raise ValueError(f"first-raid source-time mismatch {symbol}/{day}")
        result.append({
            "symbol":symbol,"ny_day":old["ny_day"],"asia_M1_observed":found,
            "asia_high":asia_high,"asia_low":asia_low,
            "original_raid_status":old["status"],"original_raid_at":old["raid_at"],
            "london_M1_observed":len(london),"london":london,
        })
    output.mkdir(parents=True,exist_ok=True)
    (output/f"qore-london-SMT-T0-{symbol}-m1-evidence.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in result),encoding="utf-8"
    )
    stats={
        "identity":ID,"symbol":symbol,"ny_days":len(result),
        "asia_complete":sum(x["asia_M1_observed"]==240 for x in result),
        "source_native_m1":len(m1),
        "previous_raid_status_counts":dict(Counter(x["original_raid_status"] for x in result)),
    }
    (output/f"qore-london-SMT-T0-{symbol}-census.json").write_text(
        json.dumps(stats,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return stats


def scan_pair(day_rows:dict[str,Any])->dict[str,Any]:
    if set(day_rows)!=set(SYMBOLS):
        raise ValueError("both paired FX rows needed")
    eur=day_rows["EURUSD"]
    gbp=day_rows["GBPUSD"]
    if eur["ny_day"]!=gbp["ny_day"]:
        raise ValueError("pair date mismatch")
    day=date.fromisoformat(eur["ny_day"])
    start=at(day,2)
    row={
        "identity":ID,"ny_day":eur["ny_day"],"status":None,
        "leader_symbol":None,"mate_symbol":None,"leader_side":None,
        "anchor_opened_at":None,"available_at":None,
        "london_minute_index":None,"mate_first_confirmation_index":None,
        "mate_opposite_breach_in_window":None,
        "pair_asia_complete":all(day_rows[s]["asia_M1_observed"]==240 for s in SYMBOLS),
        "missing_symbol":None,"missing_minute_index":None,
        "same_m1_opposite_side":False,
    }
    if not row["pair_asia_complete"]:
        row["status"]="CENSORED_ASIA_PAIRED"
        return row
    extrema={
        s: (Decimal(day_rows[s]["asia_high"]),Decimal(day_rows[s]["asia_low"]))
        for s in SYMBOLS
    }
    def touches(sym:str,i:int)->set[str]|None:
        bar=day_rows[sym]["london"].get(str(i))
        if bar is None:
            return None
        hi,lo=extrema[sym]
        return (
            ({"HIGH"} if Decimal(bar[0])>hi else set()) |
            ({"LOW"} if Decimal(bar[1])<lo else set())
        )
    for i in range(WINDOW_M1):
        t_eur,t_gbp=touches("EURUSD",i),touches("GBPUSD",i)
        if t_eur is None or t_gbp is None:
            row.update(
                status="CENSORED_PRE_ANCHOR_PAIR_GAP",
                missing_symbol="EURUSD" if t_eur is None else "GBPUSD",
                missing_minute_index=i,
            )
            return row
        if not (t_eur or t_gbp):
            continue
        row["anchor_opened_at"]=(start+timedelta(minutes=i)).isoformat()
        row["london_minute_index"]=i
        if len(t_eur)>1 or len(t_gbp)>1:
            row["status"]="AMBIGUOUS_DUAL_EDGE_SAME_M1"
            return row
        if t_eur and t_gbp:
            row["status"]=(
                "SIMULTANEOUS_SAME_DIRECTION" if t_eur==t_gbp
                else "SIMULTANEOUS_OPPOSITE_DIRECTION"
            )
            return row
        lead="EURUSD" if t_eur else "GBPUSD"
        mate="GBPUSD" if lead=="EURUSD" else "EURUSD"
        side=next(iter(t_eur if t_eur else t_gbp))
        row.update(leader_symbol=lead,mate_symbol=mate,leader_side=side)
        if i+WINDOW_MATE>=WINDOW_M1:
            row["status"]="CENSORED_LONDON_10M_WINDOW"
            return row
        confirms=None
        opposite=False
        for step in range(1,WINDOW_MATE+1):
            for symbol in SYMBOLS:
                present=touches(symbol,i+step)
                if present is None:
                    row.update(
                        status="CENSORED_POST_ANCHOR_PAIR_GAP",
                        missing_symbol=symbol,missing_minute_index=i+step,
                    )
                    return row
                if symbol==mate:
                    if side in present and confirms is None:
                        confirms=i+step
                    if ("LOW" if side=="HIGH" else "HIGH") in present:
                        opposite=True
        row["mate_first_confirmation_index"]=confirms
        row["mate_opposite_breach_in_window"]=opposite
        row["available_at"]=(start+timedelta(minutes=i+WINDOW_MATE+1)).isoformat()
        row["status"]=STATUS_CONFIRM if confirms is not None else STATUS_PROXY
        return row
    row["status"]="NO_FIRST_RAID"
    return row


def wilson(k:int,n:int)->list[float]|None:
    if n<=0:
        return None
    z=1.959963984540054
    p=k/n
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    spread=(z/den)*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return [center-spread,center+spread]


def aggregate(folder:Path,output:Path)->dict[str,Any]:
    files=sorted(folder.rglob("qore-london-SMT-T0-*-m1-evidence.jsonl"))
    if len(files)!=2:
        raise ValueError(f"must have exactly 2 native FX evidence ledgers: {len(files)}")
    markets={}
    for file in files:
        lines=[json.loads(l) for l in file.read_text().splitlines() if l.strip()]
        symbols={x["symbol"] for x in lines}
        if len(symbols)!=1 or len(lines)!=NY_DAYS:
            raise ValueError("unexpected market source census")
        symbol=next(iter(symbols))
        if symbol in markets:
            raise ValueError("duplicate market")
        markets[symbol]={x["ny_day"]:x for x in lines}
    if set(markets)!=set(SYMBOLS):
        raise ValueError("missing FX market")
    dates=sorted(set(markets["EURUSD"])|set(markets["GBPUSD"]))
    if len(dates)!=NY_DAYS or set(markets["EURUSD"])!=set(markets["GBPUSD"]):
        raise ValueError("missing paired NY dates")
    if sum(x["asia_M1_observed"]==240 for x in markets["EURUSD"].values())!=237:
        raise ValueError("EURUSD frozen Asian complete source census mismatch")
    if sum(x["asia_M1_observed"]==240 for x in markets["GBPUSD"].values())!=241:
        raise ValueError("GBPUSD frozen Asian complete source census mismatch")
    rows=[scan_pair({s:markets[s][day] for s in SYMBOLS}) for day in dates]
    eligible=[r for r in rows if r["status"] in (STATUS_PROXY,STATUS_CONFIRM)]
    smt=[r for r in eligible if r["status"]==STATUS_PROXY]
    counts=Counter(r["status"] for r in rows)
    by_cell={}
    for sym in SYMBOLS:
        for side in ("HIGH","LOW"):
            subset=[r for r in eligible if r["leader_symbol"]==sym and r["leader_side"]==side]
            subset_smt=[r for r in subset if r["status"]==STATUS_PROXY]
            by_cell[f"{sym}|{side}"]={
                "eligible_lead_unique_10m":len(subset),
                "nonconfirmation_n":len(subset_smt),
                "confirmation_n":len(subset)-len(subset_smt),
                "nonconfirmation_rate":len(subset_smt)/len(subset) if subset else None,
                "nonconfirmation_wilson95":wilson(len(subset_smt),len(subset)),
            }
    by_hour={}
    for h in (2,3,4):
        subset=[r for r in eligible if datetime.fromisoformat(r["anchor_opened_at"]).astimezone(
            __import__("zoneinfo").ZoneInfo("America/New_York")).hour==h]
        by_hour[str(h)]={
            "eligible":len(subset),"nonconfirmation":sum(r["status"]==STATUS_PROXY for r in subset)
        }
    power_ok=all(x["nonconfirmation_n"]>=30 for x in by_cell.values())
    out={
        "identity":ID,"status":"DESCRIPTIVE_ONLY","canonical_author_TTrades_SMT_certified":False,
        "source_window":"Asia NY 20:00-00:00; London NY 02:00-05:00 DST",
        "m1_source":"provider-native frozen 2025-09-17 to 2026-09-17",
        "no_trader_economics_or_reclaim_conditional":True,
        "ny_days_all":len(rows),
        "paired_asia_complete":sum(r["pair_asia_complete"] for r in rows),
        "status_counts":dict(counts),
        "unique_eligible_leader_N":len(eligible),
        "smt_nonconfirmation_N":len(smt),
        "smt_nonconfirmation_rate":len(smt)/len(eligible) if eligible else None,
        "smt_nonconfirmation_wilson95":wilson(len(smt),len(eligible)),
        "by_leader_and_side":by_cell,
        "by_raid_hour_NY":by_hour,
        "mate_opposite_breach_within_window":sum(
            r["mate_opposite_breach_in_window"] is True for r in smt
        ),
        "predefined_min30_per_leader_side_power_gate":(
            "SAMPLE_COUNT_SUFFICIENT_TO_PLAN_FUTURE_TEST" if power_ok
            else "DESCRIPTIVE_ONLY_INADEQUATE_POWER"
        ),
        "data_reused_exploratory":True,
        "no_RECLAIM_ACCEPTED_dependence":True,
        "no_forward_outcomes_consulted":True,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"qore-london-SMT-T0-daily-paired-census.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in rows),encoding="utf-8"
    )
    (output/"qore-london-SMT-T0-two-market-prevalence.json").write_text(
        json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print("SMT_T0_FINAL",json.dumps(out,sort_keys=True))
    return out


def main()->None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    one=sub.add_parser("market")
    one.add_argument("native",type=Path)
    one.add_argument("frozen",type=Path)
    one.add_argument("output",type=Path)
    both=sub.add_parser("aggregate")
    both.add_argument("markets",type=Path)
    both.add_argument("output",type=Path)
    a=p.parse_args()
    if a.mode=="market":
        print("SMT_T0_MARKET",json.dumps(load_market(a.native,a.frozen,a.output),sort_keys=True))
    else:
        aggregate(a.markets,a.output)


if __name__=="__main__":
    main()
