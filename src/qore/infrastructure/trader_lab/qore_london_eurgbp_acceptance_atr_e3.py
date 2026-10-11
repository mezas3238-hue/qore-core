"""E3: volatility-normalized London Asia acceptance using frozen +60m outcomes.

Descriptive only. Never alters original 458 paths, no stops/TP, BID/ASK,
broker simulation, claims of author fidelity, or production signals.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar as M1, iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END, DEV_WINDOW_START,
)
from qore.infrastructure.trader_lab.qore_london_after_asia_raid_paths_v1 import at

ID = "QORE_LONDON_E3_ATR14_M15_ASIA_ACCEPTANCE_V1"
SYMBOLS = ("EURUSD", "GBPUSD")
ORIG_STATES = ("RECLAIM_INSIDE", "ACCEPTED_OUTSIDE")
E3_STATES = ("RECLAIM_INSIDE", "ACCEPTED_ATR_0P5")
ALL_E3 = (*E3_STATES, "OUTSIDE_WEAK", "OPPOSITE_OUTSIDE")
THRESHOLD = Decimal("0.50")
BOOTSTRAPS = 2000
BLOCK_DAYS = 5
SEED = 77520261013


def atr14_m15_asia(
    bars: dict[datetime, M1], day: date,
) -> tuple[Decimal, int] | None:
    """16 closed M15 in preceding Asia; 14 last TR with predecessor."""
    start = at(day - timedelta(days=1), 20)
    m1s: list[M1] = []
    for minute in range(240):
        timestamp = start + timedelta(minutes=minute)
        b = bars.get(timestamp)
        if b is None or b.opened_at != timestamp or b.closed_at != timestamp+timedelta(minutes=1):
            return None
        m1s.append(b)
    m15s = []
    for k in range(16):
        group = m1s[k*15:(k+1)*15]
        m15s.append((
            max(b.high for b in group),
            min(b.low for b in group),
            group[-1].close,
        ))
    tr_values = [
        max(
            m15s[k][0] - m15s[k][1],
            abs(m15s[k][0]-m15s[k-1][2]),
            abs(m15s[k][1]-m15s[k-1][2]),
        ) for k in range(2, 16)
    ]
    assert len(tr_values) == 14
    atr = sum(tr_values, Decimal(0)) / Decimal(14)
    if atr <= 0:
        return None
    # Availability: final M15 close at 00:00 NY, before first raid >=02:00.
    return atr, len(m1s)


def classify_acceptance(
    close: Decimal, asia_low: Decimal, asia_high: Decimal,
    side: str, atr: Decimal,
) -> tuple[str, Decimal]:
    if asia_high <= asia_low or atr <= 0 or side not in ("HIGH", "LOW"):
        raise ValueError("invalid E3 geometry/ATR")
    signed = (
        (close-asia_high)/atr if side == "HIGH" else (asia_low-close)/atr
    )
    opposite = (close < asia_low) if side == "HIGH" else (close > asia_high)
    if opposite:
        return "OPPOSITE_OUTSIDE", signed
    if asia_low <= close <= asia_high:
        return "RECLAIM_INSIDE", signed
    if signed >= THRESHOLD:
        return "ACCEPTED_ATR_0P5", signed
    return "OUTSIDE_WEAK", signed


def source_files(root: Path, name: str) -> list[Path]:
    return sorted(root.rglob(name))


def one_market(native: Path, frozen: Path, h4e2: Path, output: Path) -> dict[str, Any]:
    original_files = source_files(frozen, "london-asia-postraid-*-daily-paths.jsonl")
    joined_files = source_files(h4e2, "issue775-E2-*-frozen-joined-h4.jsonl")
    if len(original_files) != 1 or len(joined_files) != 1:
        raise ValueError("one frozen and one E2 source ledger per market required")
    orig = [json.loads(line) for line in original_files[0].read_text().splitlines()
            if line.strip()]
    joined = [json.loads(line) for line in joined_files[0].read_text().splitlines()
              if line.strip()]
    if len(orig) != 261 or len(joined) != 261:
        raise ValueError("original NY-day census changed")
    s = {r["symbol"] for r in orig}
    if len(s) != 1 or s not in ({"EURUSD"}, {"GBPUSD"}):
        raise ValueError("unexpected symbol")
    symbol = next(iter(s))
    if {r["symbol"] for r in joined} != {symbol}:
        raise ValueError("E2 H4 source symbol mismatch")
    by_day = {r["ny_day"]: r for r in joined}
    if len(by_day) != 261 or len({r["ny_day"] for r in orig}) != 261:
        raise ValueError("duplicate days in sources")
    expected = {
        "EURUSD": {"valid":227, "RECLAIM_INSIDE":(94,38), "ACCEPTED_OUTSIDE":(115,40)},
        "GBPUSD": {"valid":231, "RECLAIM_INSIDE":(92,22), "ACCEPTED_OUTSIDE":(123,50)},
    }[symbol]
    valid = [r for r in orig if r["status"] == "CHECKPOINT_VALID"]
    if len(valid) != expected["valid"]:
        raise ValueError("frozen valid count mismatch")
    for st in ORIG_STATES:
        selected = [r for r in valid if r["checkpoint_state"] == st]
        if (len(selected), sum(r["terminal_60"]=="REVERSAL" for r in selected)) != expected[st]:
            raise ValueError("original return labels or classification modified")
    prices: dict[datetime, M1] = {}
    for bar in iter_cibo_m1(native):
        if not (DEV_WINDOW_START <= bar.opened_at < DEV_WINDOW_END):
            continue
        if bar.symbol != symbol or bar.opened_at in prices:
            raise ValueError("source symbol mismatch or duplicate M1")
        prices[bar.opened_at] = bar
    if len(prices) < 300_000:
        raise ValueError("insufficient native source")
    output_rows = []
    for record in orig:
        old = by_day[record["ny_day"]]
        for field in ("symbol", "ny_day", "raid_at", "checkpoint_at",
                      "checkpoint_state", "terminal_60"):
            src = record[field] if field != "checkpoint_state" else record["checkpoint_state"]
            prev = old[field]
            if prev != src:
                raise ValueError(f"source/E2 identity mismatch {field}: {record['ny_day']}")
        item = {
            "identity":ID,"symbol":symbol,"ny_day":record["ny_day"],
            "status":record["status"],"original_state":record["checkpoint_state"],
            "terminal_60":record["terminal_60"],
            "H4_E2_status":old["h4_prior"]["status"],
            "E3_state":None,"atr14_m15_pips":None,
            "asia_range_pips":None,"signed_extension_atr":None,
            "checkpoint_at":record["checkpoint_at"],
            "raid_at":record["raid_at"],
            "atr_source_M1":0,
        }
        if record["status"] == "CHECKPOINT_VALID":
            ny_day=date.fromisoformat(record["ny_day"])
            raid=datetime.fromisoformat(record["raid_at"])
            cp=datetime.fromisoformat(record["checkpoint_at"])
            if cp-raid != timedelta(minutes=11):
                raise ValueError("checkpoint clock must preserve 11 M1")
            source=atr14_m15_asia(prices,ny_day)
            if source is None:
                item["E3_state"]="ATR_UNKNOWN_ASIA_COVERAGE"
            else:
                atr, n_m1=source
                if at(ny_day,0)>raid:
                    raise AssertionError("using future Asia")
                b=prices.get(cp-timedelta(minutes=1))
                if b is None or b.closed_at!=cp:
                    item["E3_state"]="CHECKPOINT_M1_UNAVAILABLE"
                else:
                    high=Decimal(record["asia_high"])
                    low=Decimal(record["asia_low"])
                    state, extension=classify_acceptance(b.close,low,high,
                                                         record["raid_side"],atr)
                    item.update(E3_state=state,
                                atr14_m15_pips=float(atr/Decimal(".0001")),
                                asia_range_pips=float((high-low)/Decimal(".0001")),
                                signed_extension_atr=float(extension),
                                atr_source_M1=n_m1)
                    # Orthogonality: old spatial reclaim must be preserved exactly.
                    if (record["checkpoint_state"] == "RECLAIM_INSIDE") != (state == "RECLAIM_INSIDE"):
                        raise AssertionError("E3 must not redefine reclaim")
        output_rows.append(item)
    output.mkdir(parents=True,exist_ok=True)
    (output/f"qore-london-E3-{symbol}-joined-states.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in output_rows),
        encoding="utf-8",
    )
    info = {
        "identity":ID,"symbol":symbol,"ny_days":len(orig),
        "original_checkpoints_valid":len(valid),
        "E3_counts":dict(Counter(r["E3_state"] for r in output_rows
                                if r["status"] == "CHECKPOINT_VALID")),
        "M1_native_total":len(prices),"original_outcomes_unchanged":True,
    }
    (output/f"qore-london-E3-{symbol}-source-census.json").write_text(
        json.dumps(info,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return info


def four_cells(rows:list[dict[str,Any]],st_key:str,states:tuple[str,str])->dict[str,Any]|None:
    cells:dict[str,Any]={}
    diffs:dict[str,float]={}
    for symbol in SYMBOLS:
        rates:list[float]=[]
        for state in states:
            cohort=[r for r in rows if r["symbol"]==symbol
                    and r["status"]=="CHECKPOINT_VALID"
                    and r[st_key]==state
                    and r["terminal_60"]!="CENSORED"]
            rev=sum(r["terminal_60"]=="REVERSAL" for r in cohort)
            con=sum(r["terminal_60"]=="CONTINUATION" for r in cohort)
            key=f"{symbol}|{state}"
            cells[key]={"N":len(cohort),"reversal":rev,"continuation":con,
                        "neutral":len(cohort)-rev-con,
                        "reversal_rate":rev/len(cohort) if cohort else None}
            if not cohort:
                return None
            rates.append(rev/len(cohort))
        diffs[symbol]=rates[0]-rates[1]
    return {
        "cells":cells,"within_symbol_differences":diffs,
        "interaction_EUR_minus_GBP":diffs["EURUSD"]-diffs["GBPUSD"],
    }


def block_bootstrap(rows:list[dict[str,Any]],by_key:str,states:tuple[str,str],
                    dates:list[str],reps:int=BOOTSTRAPS)->dict[str,Any]:
    by_day:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for row in rows:
        by_day[row["ny_day"]].append(row)
    rng=random.Random(SEED)
    values=[]
    for _ in range(reps):
        draws=[]
        day_count=0
        while day_count < len(dates):
            start=rng.randrange(len(dates))
            for j in range(min(BLOCK_DAYS,len(dates)-day_count)):
                draws.extend(by_day[dates[(start+j)%len(dates)]])
                day_count+=1
        c=four_cells(draws,by_key,states)
        if c is not None:
            values.append(c["interaction_EUR_minus_GBP"])
    values.sort()
    def q(p:float)->float|None:
        if not values:
            return None
        x=(len(values)-1)*p
        lo=int(x)
        return values[lo]*(1-(x-lo))+values[min(lo+1,len(values)-1)]*(x-lo)
    return {
        "n_requested":reps,"valid":len(values),
        "seed":SEED,"paired_NY_block_dates":BLOCK_DAYS,
        "CI95":[q(.025),q(.975)],
        "share_nonpositive":sum(x<=0 for x in values)/len(values) if values else None,
        "exploratory_historic_data":True,
    }


def report(root:Path,output:Path)->dict[str,Any]:
    files=source_files(root,"qore-london-E3-*-joined-states.jsonl")
    if len(files)!=2:
        raise ValueError("exact two London market ledgers")
    rows=[json.loads(line) for p in files for line in p.read_text().splitlines() if line.strip()]
    if len(rows)!=522 or {r["symbol"] for r in rows}!=set(SYMBOLS):
        raise ValueError("must preserve 522 frozen source NY days")
    if len({(r["symbol"],r["ny_day"]) for r in rows})!=522:
        raise ValueError("duplicate source NY days")
    if sum(r["status"]=="CHECKPOINT_VALID" for r in rows)!=458:
        raise ValueError("458 frozen checkpoints modified")
    dates=sorted({r["ny_day"] for r in rows})
    h4_groups={
        "H4_E2_KNOWN":lambda r:r["H4_E2_status"] in
            ("H4_ALIGNED_WITH_RAID","H4_OPPOSED_TO_RAID"),
        "H4_E2_UNKNOWN":lambda r:r["H4_E2_status"] not in
            ("H4_ALIGNED_WITH_RAID","H4_OPPOSED_TO_RAID"),
    }
    original=four_cells(rows,"original_state",ORIG_STATES)
    e3=four_cells(rows,"E3_state",E3_STATES)
    if original is None or e3 is None:
        raise ValueError("both comparison cohorts need nonempty paired cells")
    coverage={}
    for key,cond in h4_groups.items():
        selected=[r for r in rows if cond(r)]
        c=four_cells(selected,"original_state",ORIG_STATES)
        coverage[key]={
            "original":c,"valid_source_cases":sum(r["status"]=="CHECKPOINT_VALID" for r in selected),
            "bootstrap":block_bootstrap(selected,"original_state",ORIG_STATES,dates),
        }
    transitions={
        s:{
            a:dict(Counter(r["E3_state"] for r in rows
                if r["symbol"]==s and r["original_state"]==a and r["status"]=="CHECKPOINT_VALID"))
            for a in ("RECLAIM_INSIDE","ACCEPTED_OUTSIDE","OUTSIDE_UNCONFIRMED","OPPOSITE_OUTSIDE")
        } for s in SYMBOLS
    }
    by_e3={
        s:{
            state:{
                "N":len(sub:=[r for r in rows if r["symbol"]==s and r["E3_state"]==state]),
                "reversal":sum(r["terminal_60"]=="REVERSAL" for r in sub),
                "continuation":sum(r["terminal_60"]=="CONTINUATION" for r in sub),
                "neutral":sum(r["terminal_60"]=="NEUTRAL" for r in sub),
                "median_ATR_M15_pips":median(x["atr14_m15_pips"] for x in sub) if sub else None,
                "median_AsiaRange_pips":median(x["asia_range_pips"] for x in sub) if sub else None,
                "median_signed_extension_ATR":median(x["signed_extension_atr"] for x in sub) if sub else None,
            }
            for state in ALL_E3
        } for s in SYMBOLS
    }
    result={
        "identity":ID,"status":"EXPLORATORY_NONCONFIRMATORY",
        "original_hist_458_unchanged":True,
        "original_pair_interaction":original,
        "E3_ATR_normalized_interaction":e3,
        "E3_ATR_0p50_bootstrap":block_bootstrap(rows,"E3_state",E3_STATES,dates),
        "E3_by_state":by_e3,
        "original_to_E3_transitions":transitions,
        "original_contrast_by_H4_E2_missingness":coverage,
        "commentary":"Missing E2-H4 coverage is not broken London raid M1 or a causal H4 effect",
        "ATR14_M15_definition":"last 14 M15 true ranges from exact 240 native Asia M1",
        "no_trades_PF_SMT_or_cisd_author":True,
        "OOS_certification":False,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"qore-london-E3-atr-normalized-acceptance-results.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print("QORE_LONDON_E3_RESULT",json.dumps(result,sort_keys=True))
    return result


def main()->None:
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)
    m=sub.add_parser("market")
    m.add_argument("native",type=Path)
    m.add_argument("frozen",type=Path)
    m.add_argument("H4_E2",type=Path)
    m.add_argument("output",type=Path)
    a=sub.add_parser("aggregate")
    a.add_argument("markets",type=Path)
    a.add_argument("output",type=Path)
    v=p.parse_args()
    if v.mode=="market":
        print("QORE_LONDON_E3_MARKET",json.dumps(one_market(v.native,v.frozen,v.H4_E2,v.output),sort_keys=True))
    else:
        report(v.markets,v.output)


if __name__=="__main__":
    main()
