"""TTrades-inspired London Asian range raid paths, descriptive source-only replay.

No entry orders, no stops, no bid/ask, no profits and no trader certification.
CISD/MSS are explicitly QORE causal proxies, never passed off as author truth.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import mean, median
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar as M1,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END, DEV_WINDOW_START,
)

ID = "QORE_LONDON_TTRADES_INSPIRED_FIRST_RAID_PATH_V1"
NY = ZoneInfo("America/New_York")
SYMBOLS = {"EURUSD", "GBPUSD"}
SEED = 77520261011
HORIZONS = (30, 60, 120)
THRESHOLD = Decimal("0.25")


def at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), NY).astimezone(UTC)


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def base_row(symbol: str, day: date, status: str, count: int = 0) -> dict[str, Any]:
    return {
        "identity": ID, "symbol": symbol, "ny_day": day.isoformat(),
        "status": status, "asia_minutes_observed": count,
        "asia_high": None, "asia_low": None, "asia_range": None,
        "raid_at": None, "raid_side": None, "checkpoint_at": None,
        "checkpoint_state": None, "cisd_proxy_at": None,
        "structure_proxy_at": None, "structure_swing_at": None,
        "retest_held": None, "reclaim_before_checkpoint": None,
        "raid_depth_asia_units": None, "cisd_structure_order": None,
        "terminal_60": None, "first_touch_60": None,
        "delta_30_asia": None, "delta_60_asia": None, "delta_120_asia": None,
        "mfe_60_asia": None, "mae_60_asia": None,
        "outcome_60_coverage": 0, "author_rule_certified": False,
    }


def final_first_touch(rows: list[M1], price: Decimal, side: int,
                      rg: Decimal) -> str:
    upper = price + Decimal(side) * THRESHOLD * rg
    lower = price - Decimal(side) * THRESHOLD * rg
    for b in rows:
        # Directional high/low as positive/negative toward the breached side.
        directional_high = b.high if side > 0 else b.low
        directional_low = b.low if side > 0 else b.high
        up = directional_high >= upper if side > 0 else directional_high <= upper
        dn = directional_low <= lower if side > 0 else directional_low >= lower
        if up and dn:
            return "BOTH_SAME_M1_UNRESOLVED"
        if up:
            return "CONTINUATION_FIRST"
        if dn:
            return "REVERSAL_FIRST"
    return "NEITHER"


def recent_pivot(bars: dict[datetime, M1], raid_at: datetime,
                 direction: int) -> tuple[Decimal, datetime] | None:
    # 60 minutes PRE raid only; right neighbor closed before raid.
    sample = [bars.get(raid_at-timedelta(minutes=k)) for k in range(60, 0, -1)]
    if any(x is None for x in sample):
        return None
    candidates: list[tuple[Decimal, datetime]] = []
    for j in range(1, len(sample)-1):
        left, middle, right = sample[j-1], sample[j], sample[j+1]
        assert left is not None and middle is not None and right is not None
        if direction > 0:
            good = middle.low < left.low and middle.low < right.low
            value = middle.low
        else:
            good = middle.high > left.high and middle.high > right.high
            value = middle.high
        if good and right.closed_at <= raid_at:
            candidates.append((value, right.closed_at))
    return candidates[-1] if candidates else None


def cisd_proxy(checkpoint: list[M1], pre_bars: dict[datetime, M1],
               direction: int) -> datetime | None:
    # Candle sequence must preexist the confirming close. Candidate may be
    # the first raid candle if a prior up/down streak is already visible.
    for candidate in checkpoint:
        cursor = candidate.opened_at
        consecutive: list[M1] = []
        for _ in range(10):
            previous = pre_bars.get(cursor - timedelta(minutes=1))
            if previous is None:
                break
            prior_same = previous.close > previous.open if direction > 0 else previous.close < previous.open
            if not prior_same:
                break
            consecutive.insert(0, previous)
            cursor = previous.opened_at
        if not consecutive:
            continue
        opening = consecutive[0].open
        is_confirmed = (
            candidate.close < opening if direction > 0 else candidate.close > opening
        )
        if is_confirmed:
            return candidate.closed_at
    return None


def inspect_day(symbol: str, day: date, bars: dict[datetime, M1]) -> dict[str, Any]:
    if symbol not in SYMBOLS:
        raise ValueError("out of scope")
    if day.weekday() >= 5:
        raise ValueError("weekend")
    a_begin = at(day-timedelta(days=1), 20)
    a_end = at(day, 0)
    # Verify NY DST does not collapse/extend the intended Asia range.
    if a_end-a_begin != timedelta(minutes=240):
        return base_row(symbol, day, "ASIA_DST_WINDOW_UNSUPPORTED")
    asia = [bars.get(a_begin+timedelta(minutes=k)) for k in range(240)]
    observed = sum(b is not None for b in asia)
    row = base_row(symbol, day, "ASIA_INCOMPLETE", observed)
    if observed != 240:
        return row
    assert all(b is not None for b in asia)
    high = max(b.high for b in asia if b is not None)
    low = min(b.low for b in asia if b is not None)
    rg = high-low
    row.update(asia_high=str(high), asia_low=str(low), asia_range=str(rg))
    if rg <= 0:
        row["status"] = "ASIA_ZERO_RANGE"
        return row
    l2 = at(day, 2)
    l5 = at(day, 5)
    if l5-l2 != timedelta(minutes=180):
        row["status"] = "LONDON_DST_WINDOW_UNSUPPORTED"
        return row
    raid: datetime | None = None
    side = 0
    for k in range(180):
        instant = l2+timedelta(minutes=k)
        b = bars.get(instant)
        if b is None:
            row["status"] = "PRE_RAID_GAP"
            return row
        up, down = b.high > high, b.low < low
        if up and down:
            row.update(status="BOTH_ASIA_EXTREMES_AMBIGUOUS", raid_at=iso(instant))
            return row
        if up or down:
            raid = instant
            side = 1 if up else -1
            break
    if raid is None:
        row["status"] = "NO_RAID"
        return row
    row.update(raid_at=iso(raid), raid_side="HIGH" if side > 0 else "LOW")
    cp_at=raid+timedelta(minutes=11)
    if cp_at>l5:
        row["status"]="LONDON_CHECKPOINT_OUT_OF_WINDOW"
        return row
    checkpoint=[bars.get(raid+timedelta(minutes=k)) for k in range(11)]
    if any(x is None for x in checkpoint):
        row["status"]="CHECKPOINT_GAP"
        return row
    assert all(x is not None for x in checkpoint)
    cp = [x for x in checkpoint if x is not None]
    row.update(status="CHECKPOINT_VALID", checkpoint_at=iso(cp_at))
    last=cp[-1].close
    opposite_outside = last < low if side>0 else last>high
    within = low<=last<=high
    last3 = cp[-3:]
    accepted = all(b.close>high for b in last3) if side>0 else all(b.close<low for b in last3)
    state = (
        "OPPOSITE_OUTSIDE" if opposite_outside else
        "RECLAIM_INSIDE" if within else
        "ACCEPTED_OUTSIDE" if accepted else
        "OUTSIDE_UNCONFIRMED"
    )
    depth = max((b.high-high for b in cp),default=Decimal(0)) if side>0 else max((low-b.low for b in cp),default=Decimal(0))
    retest = any(
        (b.low<=high and b.close>high) if side>0 else
        (b.high>=low and b.close<low)
        for b in cp[1:]
    )
    rec_before = any(low<=b.close<=high for b in cp)
    row.update(checkpoint_state=state,retest_held=retest,
               reclaim_before_checkpoint=rec_before,raid_depth_asia_units=float(depth/rg))
    cisd=cisd_proxy(cp,bars,side)
    pivot=recent_pivot(bars,raid,side)
    structural:datetime|None=None
    if pivot:
        pivot_price,pivot_avail=pivot
        for b in cp:
            if b.closed_at < pivot_avail:
                continue
            if (side>0 and b.close<pivot_price) or (side<0 and b.close>pivot_price):
                structural=b.closed_at
                break
        row["structure_swing_at"]=iso(pivot_avail)
    row["cisd_proxy_at"]=iso(cisd)
    row["structure_proxy_at"]=iso(structural)
    row["cisd_structure_order"]=(
        "BOTH_SAME_M1" if cisd and structural and cisd==structural else
        "CISD_BEFORE_STRUCTURE" if cisd and structural and cisd<structural else
        "STRUCTURE_BEFORE_CISD" if cisd and structural else
        "CISD_ONLY" if cisd else
        "STRUCTURE_ONLY" if structural else "NEITHER"
    )
    for horizon in HORIZONS:
        future=[bars.get(cp_at+timedelta(minutes=k)) for k in range(horizon)]
        if any(x is None for x in future):
            continue
        seq=[x for x in future if x is not None]
        signed=(seq[-1].close-last)*Decimal(side)/rg
        row[f"delta_{horizon}_asia"]=float(signed)
        if horizon==60:
            row["outcome_60_coverage"]=60
            row["terminal_60"]=(
                "CONTINUATION" if signed>=THRESHOLD else
                "REVERSAL" if signed<=-THRESHOLD else
                "NEUTRAL"
            )
            row["first_touch_60"]=final_first_touch(seq,last,side,rg)
            fav=max(((x.high-last)*Decimal(side)/rg if side>0 else
                     (last-x.low)/rg for x in seq),default=Decimal(0))
            adv=min(((x.low-last)/rg if side>0 else
                     (last-x.high)/rg for x in seq),default=Decimal(0))
            row["mfe_60_asia"]=float(fav)
            row["mae_60_asia"]=float(adv)
    if row["terminal_60"] is None:
        row["terminal_60"]="CENSORED"
        row["first_touch_60"]="CENSORED_GAP"
    return row


def analyse_market(native: Path, output: Path) -> dict[str, Any]:
    by_day:dict[date,dict[datetime,M1]]=defaultdict(dict)
    symbol:str|None=None
    n=0
    for b in iter_cibo_m1(native):
        if not (DEV_WINDOW_START<=b.opened_at<DEV_WINDOW_END):
            continue
        if symbol is not None and b.symbol!=symbol:
            raise ValueError("mixed symbols")
        symbol=b.symbol
        if symbol not in SYMBOLS:
            raise ValueError("unexpected market")
        # Asia for NY day d comes from d-1 evening; index both possibilities.
        ny_day=b.opened_at.astimezone(NY).date()
        by_day[ny_day][b.opened_at]=b
        if (b.opened_at.astimezone(NY).hour>=20):
            nxt=ny_day+timedelta(days=1)
            if nxt.weekday()<5:
                by_day[nxt][b.opened_at]=b
        n+=1
    if symbol is None:
        raise ValueError("empty native M1")
    days=sorted(day for day in by_day if day.weekday()<5
                and at(day,5)>DEV_WINDOW_START
                and at(day,0)<DEV_WINDOW_END)
    result=[inspect_day(symbol,day,by_day[day]) for day in days]
    output.mkdir(parents=True,exist_ok=True)
    filename=f"london-asia-postraid-{symbol}-daily-paths.jsonl"
    (output/filename).write_text("".join(json.dumps(v,sort_keys=True)+"\n" for v in result))
    count=Counter(v["status"] for v in result)
    info={"identity":ID,"symbol":symbol,"n_source_M1":n,"ny_days":len(days),
          "status_counts":dict(count),
          "first_raid":sum(v["raid_at"] is not None for v in result),
          "checkpoint_valid":count["CHECKPOINT_VALID"],
          "return_paths_not_trades":True,"source_author_exact":False}
    (output/f"london-asia-postraid-{symbol}-census.json").write_text(json.dumps(info,indent=2,sort_keys=True))
    return info


def wilson(k:int,n:int)->list[float]|None:
    if n==0:
        return None
    z=1.959963984540054
    p=k/n
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=(z/(1+z*z/n))*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return [center-half,center+half]


def summaries(rows:list[dict[str,Any]])->dict[str,Any]:
    states=["OPPOSITE_OUTSIDE","RECLAIM_INSIDE","ACCEPTED_OUTSIDE","OUTSIDE_UNCONFIRMED"]
    outcomes=["CONTINUATION","REVERSAL","NEUTRAL","CENSORED"]
    def cell(group:list[dict[str,Any]])->dict[str,Any]:
        known=[v for v in group if v["terminal_60"]!="CENSORED"]
        counts=Counter(v["terminal_60"] for v in group)
        returns=[v["delta_60_asia"] for v in known if v["delta_60_asia"] is not None]
        return {
            "N":len(group),"N_60_known":len(known),"N_censored":len(group)-len(known),
            "outcomes":{k:counts[k] for k in outcomes},
            "continuation_rate_known":len([v for v in known if v["terminal_60"]=="CONTINUATION"])/len(known) if known else None,
            "reversal_rate_known":len([v for v in known if v["terminal_60"]=="REVERSAL"])/len(known) if known else None,
            "reversal_wilson95":wilson(counts["REVERSAL"],len(known)),
            "median_delta60_asia":median(returns) if returns else None,
            "mean_delta60_asia":mean(returns) if returns else None,
            "first_touch_counts":dict(Counter(v["first_touch_60"] for v in group)),
        }
    valid=[v for v in rows if v["status"]=="CHECKPOINT_VALID"]
    return {
        "date_rows_total":len(rows),
        "status_counts":dict(Counter(v["status"] for v in rows)),
        "raid_side":dict(Counter(v["raid_side"] for v in valid)),
        "checkpoint_valid":len(valid),
        "overall":cell(valid),
        "by_state":{k:cell([v for v in valid if v["checkpoint_state"]==k]) for k in states},
        "by_cisd_proxy":{k:cell([v for v in valid if bool(v["cisd_proxy_at"])==k]) for k in (True,False)},
        "by_structure_proxy":{k:cell([v for v in valid if bool(v["structure_proxy_at"])==k]) for k in (True,False)},
        "by_cisd_structure_order":{
            k:cell([v for v in valid if v["cisd_structure_order"]==k])
            for k in ["CISD_BEFORE_STRUCTURE","STRUCTURE_BEFORE_CISD",
                      "BOTH_SAME_M1","CISD_ONLY","STRUCTURE_ONLY","NEITHER"]
        },
        "by_retest":{k:cell([v for v in valid if v["retest_held"]==k]) for k in (True,False)},
        "by_local_raid_hour":{
            str(h):cell([v for v in valid if datetime.fromisoformat(v["raid_at"]).astimezone(NY).hour==h])
            for h in (2,3,4)
        },
        "horizons":{
            str(h):{
                "N":sum(v[f"delta_{h}_asia"] is not None for v in valid),
                "mean":mean([v[f"delta_{h}_asia"] for v in valid if v[f"delta_{h}_asia"] is not None]) if any(v[f"delta_{h}_asia"] is not None for v in valid) else None,
                "median":median([v[f"delta_{h}_asia"] for v in valid if v[f"delta_{h}_asia"] is not None]) if any(v[f"delta_{h}_asia"] is not None for v in valid) else None,
            }
            for h in HORIZONS
        }
    }


def bootstrap_delta(valid:list[dict[str,Any]],simulations:int=2000)->dict[str,Any]:
    eligible=[v for v in valid if v["terminal_60"]!="CENSORED" and v["checkpoint_state"] in ("RECLAIM_INSIDE","ACCEPTED_OUTSIDE")]
    rs=[v for v in eligible if v["checkpoint_state"]=="RECLAIM_INSIDE"]
    bs=[v for v in eligible if v["checkpoint_state"]=="ACCEPTED_OUTSIDE"]
    if not rs or not bs:
        return {"difference":None,"CI95":None,"reason":"INSUFFICIENT_TWO_STATES"}
    def delta(seq:list[dict[str,Any]])->float|None:
        a=[int(v["terminal_60"]=="REVERSAL") for v in seq if v["checkpoint_state"]=="RECLAIM_INSIDE"]
        b=[int(v["terminal_60"]=="REVERSAL") for v in seq if v["checkpoint_state"]=="ACCEPTED_OUTSIDE"]
        return mean(a)-mean(b) if a and b else None
    rng=random.Random(SEED)
    draws:list[float]=[]
    for _ in range(simulations):
        sample=[eligible[rng.randrange(len(eligible))] for _ in eligible]
        z=delta(sample)
        if z is not None:
            draws.append(z)
    return {"difference":delta(eligible),"CI95":[sorted(draws)[int(.025*(len(draws)-1))],sorted(draws)[int(.975*(len(draws)-1))]] if draws else None,
            "replications_valid":len(draws),"reason":"EXPLORATORY_WITHIN_DATE_ONE_RAID"}


def aggregate(market_root:Path,output:Path)->dict[str,Any]:
    paths=sorted(market_root.rglob("london-asia-postraid-*-daily-paths.jsonl"))
    if len(paths)!=2:
        raise ValueError(f"require 2 native market paths, got {len(paths)}")
    rows=[json.loads(line) for path in paths for line in path.read_text().splitlines() if line.strip()]
    if {x["symbol"] for x in rows}!=SYMBOLS:
        raise ValueError("require exact two symbols")
    if len({(x["symbol"],x["ny_day"]) for x in rows})!=len(rows):
        raise ValueError("duplicate London day")
    reports:dict[str,Any]={}
    for symbol in sorted(SYMBOLS):
        chunk=[x for x in rows if x["symbol"]==symbol]
        info=summaries(chunk)
        info["checkpoint_state_reversal_minus_acceptance_reversal_probability_bootstrap"]=bootstrap_delta(
            [x for x in chunk if x["status"]=="CHECKPOINT_VALID"]
        )
        reports[symbol]=info
    overall=summaries(rows)
    data={
        "identity":ID,"source":"provider-native M1, run35548099334",
        "author_clock_interpretation":"America/New_York with DST; author writes EST",
        "source_asia":"20:00 prior NY day to 00:00 day NY","source_london":"02:00 to 05:00 NY",
        "checkpoint":"first raid M1 + 11 exact M1 closes",
        "analysis_exploratory_2025_2026_consumed":True,
        "no_trades_or_PF":True,"no_broker_quotes_required":True,
        "cisd_and_structure_are_QORE_proxies_not_exact_author":True,
        "markets":reports,"both_markets_descriptive":overall,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"london-ttrades-inspired-postraid-two-market-results.json").write_text(json.dumps(data,indent=2,sort_keys=True))
    print("LONDON_POSTRAID_RESULT",json.dumps(data,sort_keys=True))
    return data


def main()->None:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="mode",required=True)
    a=sub.add_parser("market")
    a.add_argument("native",type=Path)
    a.add_argument("output",type=Path)
    b=sub.add_parser("aggregate")
    b.add_argument("markets",type=Path)
    b.add_argument("output",type=Path)
    z=parser.parse_args()
    if z.mode=="market":
        print("LONDON_POSTRAID_MARKET",json.dumps(analyse_market(z.native,z.output),sort_keys=True))
    else:
        aggregate(z.markets,z.output)


if __name__=="__main__":
    main()
