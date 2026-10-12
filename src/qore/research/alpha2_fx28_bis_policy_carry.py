"""One predeclared 28-FX BIS official policy-rate differential proxy test.

Preregistered e669a1d; monthly PREVIOUS EOM rate, trade starting >=16th,
28 verified native M5 source symbols, no M5 source/official rates uploaded.
Reference spot plus HYPOTHETICAL policy accrual is NOT broker NET nor a forward.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import zipfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, stdev

from qore.research.alpha2_fx28_carry_one_test import FX28, CCYS
from qore.research.alpha2_tsmom_daily_weekly import Day

IDENTITY="QORE_ALPHA2_FX28_BIS_POLICY_PREVMONTH_LAG15_6X6_V1"
PREREG="e669a1d2100f94a0c17e3773b177a3ead3661e16"
BIS_URL="https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip"
BIS_CCY_AREA={"AUD":"AU","CAD":"CA","CHF":"CH","EUR":"XM",
              "GBP":"GB","JPY":"JP","NZD":"NZ","USD":"US"}
BEGIN=date(2016,9,17)
DEV_END=date(2022,1,1)
EMBARGO=date(2024,9,17)
B=2000
SEED=20261012


def previous_month(year:int,month:int)->str:
    return f"{year-1 if month==1 else year:04d}-{12 if month==1 else month-1:02d}"


def advance_month(year:int,month:int)->tuple[int,int]:
    return (year+1,1) if month==12 else (year,month+1)


def bis_policy_rates(zip_path:Path)->tuple[dict[str,dict[str,float]],dict]:
    """Validate eight exact BIS monthly areas, no currency-rate fallback."""
    zhash=hashlib.sha256(zip_path.read_bytes()).hexdigest()
    out={ccy:{} for ccy in CCYS}
    info={ccy:{"area":area,"observations":0,"source_refs":set(),
               "compilation_descriptors":set(),"break_annotations":set()}
          for ccy,area in BIS_CCY_AREA.items()}
    inverse={code:ccy for ccy,code in BIS_CCY_AREA.items()}
    with zipfile.ZipFile(zip_path) as z:
        csvfiles=[n for n in z.namelist() if n.endswith(".csv")]
        if len(csvfiles)!=1:
            raise ValueError("POLICY_BIS_EXPECT_ONE_OFFICIAL_FLAT_CSV")
        with z.open(csvfiles[0]) as raw:
            reader=csv.DictReader(io.TextIOWrapper(raw,encoding="utf-8-sig",newline=""))
            keys=set(reader.fieldnames or [])
            columns={"FREQ:Frequency","REF_AREA:Reference area",
                     "TIME_PERIOD:Time period or range","OBS_VALUE:Observation Value",
                     "SOURCE_REF:Publication Source","COMPILATION:Compilation"}
            if not columns<=keys:
                raise ValueError("POLICY_BIS_CSV_SCHEMA_DRIFT")
            for row in reader:
                if not (row["FREQ:Frequency"] or "").startswith("M:"):
                    continue
                area=(row["REF_AREA:Reference area"] or "").split(":")[0].strip()
                ccy=inverse.get(area)
                if ccy is None:
                    continue
                period=(row["TIME_PERIOD:Time period or range"] or "").strip()
                if not ("2016-08" <= period <= "2024-08"):
                    continue
                value=(row["OBS_VALUE:Observation Value"] or "").strip()
                if not value:
                    continue
                try:
                    p=float(value)
                except ValueError as e:
                    raise ValueError("POLICY_BIS_RATE_VALUE_NONFLOAT") from e
                if not math.isfinite(p) or p < -20 or p > 40:
                    raise ValueError("POLICY_BIS_RATE_IMPLAUSIBLE")
                if period in out[ccy]:
                    raise ValueError("POLICY_BIS_DUPLICATE_8_CURRENCY_MONTH")
                out[ccy][period]=p
                meta=info[ccy]
                meta["observations"]+=1
                meta["source_refs"].add((row["SOURCE_REF:Publication Source"] or "")[:110])
                meta["compilation_descriptors"].add(
                    (row["COMPILATION:Compilation"] or "")[:130])
                annotation=(row.get("SUPP_INFO_BREAKS:Supplemental information and breaks") or "").strip()
                if annotation:
                    meta["break_annotations"].add(annotation[:160])
    cover={}
    for ccy in sorted(info):
        m=info[ccy]
        months=sorted(out[ccy])
        cover[ccy]={"bis_iso_area":m["area"],"n_months":len(months),
                    "first":months[0] if months else None,
                    "last":months[-1] if months else None,
                    "publication_sources":sorted(m["source_refs"]),
                    "compilation_descriptors":sorted(m["compilation_descriptors"]),
                    "break_annotation_samples":sorted(m["break_annotations"])[:10]}
    return out,{"source":"BIS:WS_CBPOL(1.0) flat monthly EOP",
                "source_zip_sha256":zhash,"source_url":BIS_URL,
                "rates_raw_not_published":True,
                "coverage":cover}


def original28_day_files(root:Path)->tuple[dict[str,dict[date,Day]],dict]:
    files=sorted(root.glob("*.json"))
    if len(files)!=28:
        raise ValueError("POLICY_NEEDS_EXACT28_PRIVATE_SHA_VERIFIED_DAILY_SOURCES")
    all_days={}
    audit={}
    for f in files:
        name=f.stem
        if name not in FX28 or name in all_days:
            raise ValueError("POLICY_PRIVATE_SOURCE_ROSTER_INVALID")
        expected=f.with_name(f.name+".sha256")
        if expected.read_text(encoding="utf-8").strip()!=(
            hashlib.sha256(f.read_bytes()).hexdigest()+"  "+f.name
        ):
            raise ValueError("POLICY_PRIVATE_DAILY_SOURCE_SHA_DRIFT")
        row=json.loads(f.read_text(encoding="utf-8"))
        if row.get("original_signed33_proof") is not True or row.get("symbol")!=name:
            raise ValueError("POLICY_SOURCE_NOT_ORIGINAL_SHA_VERIFIED")
        days=[Day(date.fromisoformat(d),float(op),float(cl),int(n))
              for d,op,cl,n in row["private_days"]]
        if any(a.utc_day>=b.utc_day for a,b in zip(days,days[1:],strict=False)):
            raise ValueError("POLICY_NONSTRICT_SOURCE_DAYS")
        all_days[name]={d.utc_day:d for d in days}
        audit[name]={"eligible_days":len(days),"source_cohort":row.get("cohort")}
    if set(all_days)!=set(FX28):
        raise ValueError("POLICY_PRIVATE_SOURCE_NOT_EXACT28")
    return all_days,audit


def _bootstrap3(series:list[float],rng_seed:int)->list[float]:
    rng=random.Random(rng_seed)
    n=len(series)
    if n<1:
        raise ValueError("POLICY_BOOTSTRAP_EMPTY")
    results=[]
    for _ in range(B):
        draws=[]
        while len(draws)<n:
            start=rng.randrange(n)
            draws.extend(series[(start+j)%n] for j in range(3))
        results.append(sum(draws[:n])/n)
    results.sort()
    return [results[49],results[1949]]


def _sharp12(series:list[float])->float|None:
    if len(series)<12:
        return None
    sig=stdev(series)
    return (mean(series)/sig*math.sqrt(12)) if sig>0 else None


def evaluate(rate:dict[str,dict[str,float]],
             original:dict[str,dict[date,Day]])->dict:
    if set(original)!=set(FX28) or set(rate)!=set(CCYS):
        raise ValueError("POLICY_EXACT28_8CCY_REQUIRED")
    common=sorted(set.intersection(*(set(x) for x in original.values())))
    if not common:
        raise ValueError("POLICY_NO_SHARED_28_FX_DAYS")
    valid_dates=[d for d in common if BEGIN<=d<EMBARGO]
    months=sorted({(d.year,d.month) for d in valid_dates})
    candidates=[]
    censor=Counter()
    for year,month in months:
        key=f"{year:04d}-{month:02d}"
        prev=previous_month(year,month)
        y2,m2=advance_month(year,month)
        current=[d for d in valid_dates
                 if d.year==year and d.month==month and d.day>=16]
        following=[d for d in valid_dates
                   if (d.year,d.month)==(y2,m2) and d.day<16]
        if not current or not following:
            censor["NO_UNBROKEN_COMPLETE_MONTH_ENTRY_EXIT"]+=1
            continue
        start=current[0]
        end=following[-1]
        if (start<DEV_END<=end or end>=EMBARGO or
            start<BEGIN or (end-start).days<15):
            censor["ERA_OR_SHORT_HOLD_OR_EMBARGO"]+=1
            continue
        if any(prev not in rate[c] for c in CCYS):
            censor["MISSING_PREVIOUS_MONTH_POLICY_RATE_ONE_OF_EIGHT"]+=1
            continue
        ranked=sorted(FX28,key=lambda s:(-(rate[s[:3]][prev]-rate[s[3:]][prev]),s))
        longs=set(ranked[:6])
        shorts=set(ranked[-6:])
        if len(longs)!=6 or len(shorts)!=6 or longs&shorts:
            raise ValueError("POLICY_6X6_LONG_SHORT_TIE_BUG")
        spot=0.0
        accrual=0.0
        weights={c:0.0 for c in CCYS}
        days=(end-start).days
        for s in (*sorted(longs),*sorted(shorts)):
            weight=(1/12 if s in longs else -1/12)
            pol_diff=rate[s[:3]][prev]-rate[s[3:]][prev]  # percentage points, not forward discount
            spot+=weight*10000*(original[s][end].close/original[s][start].open-1.0)
            accrual+=weight*10000*(pol_diff/100)*days/365
            weights[s[:3]]+=weight
            weights[s[3:]]-=weight
        cost=4.0
        row={"calendar_month":key,
             "factor_month_previous_EOM":prev,
             "entry_reference_utc_day":start.isoformat(),
             "exit_reference_utc_day":end.isoformat(),
             "held_calendar_days":days,
             "era":"DEVELOPMENT" if start<DEV_END else "DIAGNOSTIC",
             "long6":sorted(longs),"short6":sorted(shorts),
             "currency_net_exposures":weights,
             "max_absolute_currency_exposure":max(map(abs,weights.values())),
             "spot_reference_bps":spot,
             "hypothetical_policy_accrual_bps":accrual,
             "model_gross_proxy_bps":spot+accrual,
             "assumed_2bps_each_side_portfolio_bps":cost,
             "model_gross_minus_assumed_cost_bps":spot+accrual-cost,
             "NOT_EXECUTABLE_NOT_NET":True}
        candidates.append(row)
    if len({x["calendar_month"] for x in candidates})!=len(candidates):
        raise ValueError("POLICY_DUPLICATE_RANKING_CALENDAR_MONTH")
    eras={}
    for i,era in enumerate(("DEVELOPMENT","DIAGNOSTIC")):
        # full calendar from Sep2016 through Dec2021 and Jan2022 through Aug2024
        begin=(2016,9) if not i else (2022,1)
        stop=(2022,1) if not i else (2024,9)
        cal=[]
        y,m=begin
        while (y,m)<stop:
            cal.append(f"{y:04d}-{m:02d}")
            y,m=advance_month(y,m)
        seen={x["calendar_month"]:x for x in candidates if x["era"]==era}
        data=[seen[k]["model_gross_minus_assumed_cost_bps"] if k in seen else 0.0 for k in cal]
        gross=[seen[k]["model_gross_proxy_bps"] if k in seen else 0.0 for k in cal]
        spot=[seen[k]["spot_reference_bps"] if k in seen else 0.0 for k in cal]
        acc=[seen[k]["hypothetical_policy_accrual_bps"] if k in seen else 0.0 for k in cal]
        n=len(seen)
        eras[era]={
            "calendar_months_including_zero_missing":len(cal),
            "active_complete_fx28_months":n,
            "min_sample_predeclared":24 if not i else 12,
            "sample_gate":n>=(24 if not i else 12),
            "mean_month_spot_reference_bps":mean(spot),
            "mean_month_HYPOTHETICAL_rate_accrual_bps":mean(acc),
            "mean_month_gross_model_bps":mean(gross),
            "mean_month_gross_minus_2bp_side_assumed_cost_bps":mean(data),
            "CI95_3month_circular_block_model_cost_proxy_bps":_bootstrap3(data,SEED+i),
            "annualized_model_Sharpe_NOT_BROKER_NET":_sharp12(data),
            "not_virgin_OOS":True,
        }
    enough=all(x["sample_gate"] for x in eras.values())
    good=all(x["mean_month_gross_minus_2bp_side_assumed_cost_bps"]>0 and
             x["CI95_3month_circular_block_model_cost_proxy_bps"][0]>0
             for x in eras.values())
    state=("POLICY28_NOT_IDENTIFIABLE_MISSING_RATES_OR_PRICE" if not candidates else
           "POLICY28_UNDERPOWERED" if not enough else
           "POLICY28_EXPLORATORY_MODEL_PASS_REQUIRES_FRESH_OOS_AND_EXECUTION" if good else
           "POLICY28_PREDECLARED_MODEL_SCREEN_FAILED_STOP")
    return {"identity":IDENTITY,"prereg_ancestor":PREREG,"status":state,
            "source_factor_BIS_monthly_EOP_with_15day_publag_not_true_vintage":True,
            "carry_forward_price_not_observed":True,
            "policy_accrual_is_hypothetical_NOT_realized_swap":True,
            "source_day_M5_OPEN_is_not_guaranteed_fill":True,
            "28_fx_exact_roster":sorted(FX28),
            "shared_all28_eligible_UTC_days":len(valid_dates),
            "candidate_months":len(candidates),
            "censored_candidate_month_counts":dict(censor),
            "eras":eras,"weekly_monthly":candidates,
            "original_period_previously_exposed_NOT_OOS":True,
            "UTC001_certified":False,"account_NET_computed":False,"orders":0}


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("bis_policy_zip",type=Path)
    p.add_argument("private_exact28_daily",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    rates,bis_proof=bis_policy_rates(a.bis_policy_zip)
    sources,census=original28_day_files(a.private_exact28_daily)
    outcome=evaluate(rates,sources)
    outcome["bis_rate_source_proof"]=bis_proof
    outcome["original28_SHA_verified_daily_census"]=census
    a.out.mkdir(parents=True,exist_ok=True)
    filename=a.out/"alpha2-FX28-policy-rate-carry-monthly-one-model-cost-proxy.json"
    filename.write_text(json.dumps(outcome,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (a.out/"OUTPUT_SHA256SUMS.txt").write_text(
        hashlib.sha256(filename.read_bytes()).hexdigest()+"  "+filename.name+"\n",
        encoding="utf-8")
    print(json.dumps({"status":outcome["status"],
                      "months":outcome["candidate_months"],
                      "DEV":outcome["eras"]["DEVELOPMENT"]["mean_month_gross_minus_2bp_side_assumed_cost_bps"],
                      "DIAG":outcome["eras"]["DIAGNOSTIC"]["mean_month_gross_minus_2bp_side_assumed_cost_bps"],
                      "orders":0,"broker_NET":"BLOCKED"},sort_keys=True))

if __name__=="__main__":
    main()
