"""XSREV5: exactly 33 same-day source available instruments, 5d contrarian.

Pre-registered f9248d42, no data publication, contract, price fill or NET claim.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from statistics import mean

from qore.research.alpha2_intermarket import MARKETS, sha256_file
from qore.research.alpha2_lab_h4_extract import (
    source33_manifest,
    source_rows_before_embargo,
    verify_source,
)
from qore.research.alpha2_tsmom_daily_weekly import DEV_END, EMBARGO, Day, daily_from_native
from qore.research.alpha2_tsmom_daily_weekly_panel import era_weeks
from qore.research.alpha2_tsmom_final_scaled_panel import _bootstrap

IDENTITY = "QORE_ALPHA2_XSREV5_ALL33_FIFTH_COMMON_SESSION_GROSS_COST_V1"
PREREG = "f9248d42a6cbced3d6e962b24e47c709cb91161c"
LONG_COUNT = 7
SHORT_COUNT = 7
PAST_CLOSE_RETURN = 5
EXIT_COMMON_SESSIONS = 5
COST_PER_SIDE = 1.0


def prep_day_source(
    symbol: str, native: Path, signed33: Path,
    private: Path, aggregate: Path | None,
) -> dict:
    """Source SHA verify then write ephemeral date/price JSON, NOT uploadable."""
    if symbol not in MARKETS:
        raise ValueError("XSREV5_UNLISTED_CANONICAL")
    manifest = source33_manifest(signed33)
    evidence = verify_source(symbol, native, manifest, aggregate)
    days, census = daily_from_native(source_rows_before_embargo(native, symbol))
    private.mkdir(parents=True, exist_ok=True)
    f = private / f"{symbol}.json"
    if f.exists():
        raise ValueError("XSREV5_PRIVATE_DAY_FILE_ALREADY_CREATED")
    payload = {
        "symbol": symbol,
        "cohort": evidence["source_cohort"],
        "original_signed33_proof": True,
        "daily_source_census": census,
        "private_days": [[r.utc_day.isoformat(),r.open,r.close,r.native_m5_bars]
                         for r in days],
    }
    f.write_text(json.dumps(payload, separators=(",",":"))+"\n", encoding="utf-8")
    (private / f"{symbol}.json.sha256").write_text(
        sha256_file(f)+"  "+f.name+"\n", encoding="utf-8"
    )
    return {"symbol":symbol,"daily":len(days),"SHA_audited":True,"NET":"BLOCKED"}


def _validate_days(all33: dict[str,list[Day]]) -> list[date]:
    if set(all33) != set(MARKETS) or len(MARKETS)!=33:
        raise ValueError("XSREV5_NEEDS_EACH_OF_33_ORIGINAL_MARKETS")
    sets = []
    for days in all33.values():
        if any(a.utc_day >= b.utc_day for a,b in zip(days,days[1:],strict=False)):
            raise ValueError("XSREV5_DAILY_ORDER_INVALID")
        if not days:
            raise ValueError("XSREV5_ORIGINAL_MARKET_HAS_NO_DAYS")
        sets.append({r.utc_day for r in days})
    dates = sorted(set.intersection(*sets))
    if any(day>=EMBARGO for day in dates):
        raise ValueError("XSREV5_AFTER_EMBARGO_DENIED")
    return dates


def replay(all33: dict[str,list[Day]]) -> dict:
    """Cross-sectional ranks use only previous 5 COMMON daily close returns."""
    dates = _validate_days(all33)
    look = {s:{d.utc_day:d for d in day} for s,day in all33.items()}
    attempted=set()
    last_exit:date|None=None
    events=[]
    reject={}
    for i in range(PAST_CLOSE_RETURN+1,len(dates)):
        current=dates[i]
        iso=current.isocalendar()
        wk=f"{iso.year}-W{iso.week:02d}"
        if wk in attempted or last_exit is not None and current<=last_exit:
            continue
        attempted.add(wk)
        if i + EXIT_COMMON_SESSIONS > len(dates):
            reject["NOT_ENOUGH_FUTURE_COMMON_DAYS"]=reject.get(
                "NOT_ENOUGH_FUTURE_COMMON_DAYS",0)+1
            continue
        exit_date=dates[i+EXIT_COMMON_SESSIONS-1]
        if current<DEV_END<=exit_date or exit_date>=EMBARGO:
            reject["ERA_OR_EMBARGO_CENSORED"]=reject.get("ERA_OR_EMBARGO_CENSORED",0)+1
            continue
        # Tie-breaking deterministic lexicographic canonical symbol.
        ranked = sorted(
            ((look[s][dates[i-1]].close/look[s][dates[i-6]].close-1,s)
             for s in MARKETS),
            key=lambda x:(x[0],x[1]),
        )
        bottom=tuple(s for _,s in ranked[:LONG_COUNT])
        top=tuple(s for _,s in ranked[-SHORT_COUNT:])
        if len(set(bottom)|set(top)) != LONG_COUNT+SHORT_COUNT:
            raise ValueError("XSREV5_TIED_OVERLAPPING_LEGS")
        gross=0.0
        by_symbol={}
        for s in (*bottom,*top):
            weight=(1/14 if s in bottom else -1/14)
            a=look[s][current]
            b=look[s][exit_date]
            r=10000*weight*(b.close/a.open-1)
            if not math.isfinite(r):
                raise ValueError("XSREV5_GROSS_PRICE_NONFINITE")
            gross+=r
            by_symbol[s]=r
        cost=2*COST_PER_SIDE
        events.append({
            "iso_week":wk,
            "era":"DEVELOPMENT" if current<DEV_END else "DIAGNOSTIC",
            "reference_entry_day":current.isoformat(),
            "reference_fifth_common_exit_day":exit_date.isoformat(),
            "bottom7_long":list(bottom),
            "top7_short":list(top),
            "gross_reference_bps":gross,
            "assumed_1bp_each_side_total_bps":cost,
            "gross_minus_assumed_cost_proxy_bps":gross-cost,
            "gross_by_selected_symbol_reference_bps":by_symbol,
            "33_exact_common_day_before_entry":True,
            "broker_NET_not_proven":True,
        })
        last_exit=exit_date
    if len({(r["era"],r["iso_week"]) for r in events})!=len(events):
        raise ValueError("XSREV5_DUPLICATE_WEEKS")
    return {"events":events,"count_events":len(events),
            "all33_common_eligible_days":len(dates),
            "first_common_day":dates[0].isoformat() if dates else None,
            "last_common_day":dates[-1].isoformat() if dates else None,
            "censored_or_skipped_weekly":reject}


def panel(result:dict, market_days:dict[str,int]) -> dict:
    if set(market_days)!=set(MARKETS):
        raise ValueError("XSREV5_MARKET_CENSUS_UNVERIFIED")
    eras={}
    for ei,era in enumerate(("DEVELOPMENT","DIAGNOSTIC")):
        observed=[e for e in result["events"] if e["era"]==era]
        calendar=era_weeks(era)
        grouped={}
        for e in observed:
            k=e["iso_week"]
            if k not in calendar or k in grouped:
                raise ValueError("XSREV5_EVENT_WRONG_ERA_WEEK")
            grouped[k]=e
        returns=[grouped[w]["gross_minus_assumed_cost_proxy_bps"] if w in grouped else 0.
                 for w in calendar]
        gross=[grouped[w]["gross_reference_bps"] if w in grouped else 0.
               for w in calendar]
        ci=_bootstrap(returns,20261012+ei)
        n=len(observed)
        sufficient=n >= (52 if ei==0 else 26)
        eras[era]={
            "full_calendar_weeks_including_flat":len(calendar),
            "active_common_calendar_weeks":n,
            "gate_min_active_weeks":52 if ei==0 else 26,
            "sample_gate":sufficient,
            "weekly_gross_reference_mean_bps":mean(gross),
            "weekly_gross_minus_assumed_cost_proxy_bps":mean(returns),
            "CI95_fourweek_assumed_cost_proxy_bps":ci,
            "gross_mean_bps_per_trade":mean(e["gross_reference_bps"] for e in observed)
            if observed else None,
            "real_broker_NET_computed":False,
        }
    enough=all(x["sample_gate"] for x in eras.values())
    good=all(x["weekly_gross_minus_assumed_cost_proxy_bps"]>0
             and x["CI95_fourweek_assumed_cost_proxy_bps"][0]>0
             for x in eras.values())
    status=("INCONCLUSIVE_UNDERPOWERED" if not enough else
            "XSREV5_EXPLORATORY_SIGNAL_REQUIRES_TRUE_OOS" if good else
            "XSREV5_GROSS_MINUS_ASSUMED_COST_FAIL")
    # Do not publish daily OHLC source, only derived ranks, PnL reference.
    return {
        "identity":IDENTITY,"prereg_ancestor":PREREG,"status":status,
        "all33_exact_original_sources":33,
        "all33_common_eligible_days":result["all33_common_eligible_days"],
        "market_daily_source_coverage_count":market_days,
        "original_selected_weeks":result["count_events"],
        "censored_or_skipped_weeks":result["censored_or_skipped_weekly"],
        "erabreakdown":eras,
        "weekly_selected_ranks_gross_without_source_price":result["events"],
        "fixed_quintile7_each_side":True,
        "COST_HYPOTHESIS_ONLY_NOT_REAL_BROKER_NET":True,
        "2016_2024_previously_exposed_exploratory":True,
        "UTC001_certified":False,"orders":0,
        "raw_market_daily_OHLC_published":False,
    }


def finish(private:Path, output:Path)->dict:
    files=sorted(private.glob("*.json"))
    if len(files)!=33:
        raise ValueError("XSREV5_INTERNAL_WORKER_FILES_NOT33")
    markets={}
    coverage={}
    for f in files:
        if (private/(f.name+".sha256")).read_text(encoding="utf-8").strip()!=(
            sha256_file(f)+"  "+f.name
        ):
            raise ValueError("XSREV5_INTERMEDIATE_PRICE_SHA_INVALID")
        obj=json.loads(f.read_text(encoding="utf-8"))
        sym=obj["symbol"]
        if sym not in MARKETS or sym in markets or not obj["original_signed33_proof"]:
            raise ValueError("XSREV5_ORIGINAL_SOURCE_COHORT_INVALID")
        days=[Day(date.fromisoformat(a),float(b),float(c),int(n))
              for a,b,c,n in obj["private_days"]]
        markets[sym]=days
        coverage[sym]=len(days)
    outcome=panel(replay(markets),coverage)
    output.mkdir(parents=True,exist_ok=True)
    path=output/"alpha2-xsrev5-33-one-gross-minus-assumed-cost.json"
    path.write_text(json.dumps(outcome,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (output/"OUTPUT_SHA256SUMS.txt").write_text(
        sha256_file(path)+"  "+path.name+"\n",encoding="utf-8"
    )
    return outcome


def main()->None:
    p=argparse.ArgumentParser()
    commands=p.add_subparsers(dest="action",required=True)
    one=commands.add_parser("extract")
    one.add_argument("symbol",choices=MARKETS)
    one.add_argument("native",type=Path)
    one.add_argument("signed33",type=Path)
    one.add_argument("private",type=Path)
    one.add_argument("--aggregate12",type=Path)
    fin=commands.add_parser("finish")
    fin.add_argument("private",type=Path)
    fin.add_argument("output",type=Path)
    a=p.parse_args()
    if a.action=="extract":
        result=prep_day_source(a.symbol,a.native,a.signed33,a.private,a.aggregate12)
    else:
        result=finish(a.private,a.output)
        result={"status":result["status"],
                "common_days":result["all33_common_eligible_days"],
                "weeks":result["original_selected_weeks"],
                "NET":"BLOCKED"}
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
