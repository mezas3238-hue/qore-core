"""ONE frozen FX28 risk-controlled BIS policy carry proxy test.

Pre-result prereg 9c51aa509040ebbd470a9c59d525d86760922c1b.
Unlocks previously Alpha2-embargoed original M5 2024-09..2026-09
ONLY AFTER prereg; NEVER broker NET, LIVE, or reproducible provider fills.
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
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import mean, stdev

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as new
from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as old
from qore.research.alpha2_fx28_bis_policy_carry import BIS_CCY_AREA, advance_month, previous_month
from qore.research.alpha2_fx28_carry_one_test import CCYS, FX28
from qore.research.alpha2_intermarket import Bar, _check_bar
from qore.research.alpha2_lab_h4_extract import source33_manifest, verify_source
from qore.research.alpha2_tsmom_daily_weekly import Day

IDENTITY = "QORE_ALPHA2_FX28_BIS_POLICY_CARRY_SINGLE_FINAL_VOL20_V1"
PREREG = "9c51aa509040ebbd470a9c59d525d86760922c1b"
HISTORY_START = date(2016, 9, 17)
DEV_END = date(2022, 1, 1)
RETAINED_HOLDOUT_START = date(2024, 9, 17)
HISTORY_END_EXCLUSIVE = date(2026, 9, 17)
GLOBAL_VOL_LOOKBACK = 20
GLOBAL_ANNUAL_VOL_TARGET = 0.10
B = 2000
SEED = 20261012
BIS_URL = "https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip"


def full_readonly_original_rows(source: Path, symbol: str) -> Iterator[Bar]:
    """Read exactly 2016-09-17..2026-09-16 original M5 AFTER external SHA audit."""
    schema = old.RAW_SCHEMA if symbol in old.SYMBOLS else new.NEW_RAW_SCHEMA
    identity = old.PRODUCER if symbol in old.SYMBOLS else new.NEW_CAPTURE_IDENTITY
    provider = old.SOURCE_SYMBOL_MAP.get(symbol, symbol)
    prior: datetime | None = None
    for year in range(2016, 2027):
        p = source / "RAW_M5_LEDGER" / f"{year}.jsonl"
        with p.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                opened = datetime.fromisoformat(row["opened_at"])
                if opened.tzinfo is None or opened.utcoffset() is None:
                    raise ValueError("POLICY_VOL20_NAIVE_SOURCE_TIMESTAMP")
                opened = opened.astimezone(UTC)
                if opened.date() >= HISTORY_END_EXCLUSIVE:
                    continue  # Never read post-2026-09-16 OHLC.
                if prior is not None and opened <= prior:
                    raise ValueError("POLICY_VOL20_ORIGINAL_TIMESTAMP_ORDER")
                prior = opened
                if (row.get("schema") != schema or row.get("identity") != identity
                    or row.get("canonical_symbol") != symbol
                    or row.get("provider_symbol") != provider):
                    raise ValueError("POLICY_VOL20_ORIGINAL_SCHEMA_OR_PROVIDER_DRIFT")
                names=("open_relative","high_relative","low_relative","close_relative")
                if any(type(row.get(k)) is not int for k in names):
                    raise ValueError("POLICY_VOL20_NATIVE_OHLC_NOT_INTEGER")
                yield Bar(
                    at=opened, open=row["open_relative"], high=row["high_relative"],
                    low=row["low_relative"], close=row["close_relative"],
                )


def original_native_daily(bars: Iterator[Bar]) -> tuple[list[Day],dict]:
    prev: datetime | None = None
    current: date | None = None
    op = last = None
    n = 0
    records: list[Day] = []
    dropped=0
    weekends=0
    bars_seen=0

    def flush() -> None:
        nonlocal dropped, weekends
        if current is None:
            return
        if current.weekday()>4:
            weekends+=1
        elif n<12:
            dropped+=1
        else:
            records.append(Day(current,op,last,n))

    for bar in bars:
        _check_bar(bar)
        t=bar.at
        if t.utcoffset().total_seconds()!=0 or (
            prev is not None and t<=prev
        ) or t.minute%5 or t.second or t.microsecond:
            raise ValueError("POLICY_VOL20_NOT_STRICT_UTC_NATIVE_M5")
        if t.date()>=HISTORY_END_EXCLUSIVE:
            raise ValueError("POLICY_VOL20_NEW_EMBARGO_FAIL")
        prev=t
        bars_seen+=1
        if t.date()!=current:
            flush()
            current=t.date()
            op=bar.open
            n=0
        last=bar.close
        n+=1
    flush()
    if len({r.utc_day for r in records})!=len(records):
        raise ValueError("POLICY_VOL20_DUPLICATE_DAILY")
    return records, {
        "original_native_m5_pre_20260917_rows":bars_seen,
        "eligible_m5_weekdays_min12":len(records),
        "sparse_days_censored":dropped,"weekend_days_censored":weekends,
        "last_day_in_source":records[-1].utc_day.isoformat() if records else None,
    }


def verified_extract(
    symbol: str, native: Path, signed33: Path, cache: Path,
    atlas_aggregate: Path | None,
) -> dict:
    if symbol not in FX28:
        raise ValueError("POLICY_VOL20_NOT_EXACT28")
    proof=verify_source(symbol,native,source33_manifest(signed33),atlas_aggregate)
    days,census=original_native_daily(full_readonly_original_rows(native,symbol))
    cache.mkdir(parents=True,exist_ok=True)
    outfile=cache/f"{symbol}.json"
    if outfile.exists():
        raise ValueError("POLICY_VOL20_ALREADY_WRITTEN_PRIVATE")
    outfile.write_text(json.dumps({
        "symbol":symbol,
        "original_signed33_proof":proof["native_original_source_sha_verified"],
        "cohort":proof["source_cohort"],
        "daily_census":census,
        "private_days":[[x.utc_day.isoformat(),x.open,x.close,x.native_m5_bars]
                        for x in days],
    },separators=(",",":"))+"\n",encoding="utf-8")
    (cache/(outfile.name+".sha256")).write_text(
        hashlib.sha256(outfile.read_bytes()).hexdigest()+"  "+outfile.name+"\n",
        encoding="utf-8",
    )
    return {"symbol":symbol,**census,"sha_original_verified":True,"orders":0}


def read_private_source(directory:Path)->tuple[dict[str,dict[date,Day]],dict]:
    files=sorted(directory.glob("*.json"))
    if len(files)!=28:
        raise ValueError("POLICY_VOL20_EXACT28_TEMP_SOURCE_REQUIRED")
    data={}
    census={}
    for f in files:
        check=f.with_name(f.name+".sha256")
        expected=hashlib.sha256(f.read_bytes()).hexdigest()+"  "+f.name
        if check.read_text(encoding="utf-8").strip()!=expected:
            raise ValueError("POLICY_VOL20_INTERMEDIATE_SHA_MISMATCH")
        j=json.loads(f.read_text(encoding="utf-8"))
        symbol=j["symbol"]
        if symbol not in FX28 or symbol in data or symbol!=f.stem:
            raise ValueError("POLICY_VOL20_PROVIDER_SYMBOL_OR_COUNT_INVALID")
        if j["original_signed33_proof"] is not True:
            raise ValueError("POLICY_VOL20_SOURCE_NOT_SHA_VERIFIED")
        days=[Day(date.fromisoformat(d),float(op),float(cl),int(n))
              for d,op,cl,n in j["private_days"]]
        if any(a.utc_day>=b.utc_day for a,b in zip(days,days[1:],strict=False)):
            raise ValueError("POLICY_VOL20_SOURCE_DAYS_NOT_SORTED")
        data[symbol]={r.utc_day:r for r in days}
        census[symbol]=j["daily_census"]
    if set(data)!=set(FX28):
        raise ValueError("POLICY_VOL20_ROSTER_MISSING")
    return data,census


def official_rate_history(biszip:Path)->tuple[dict[str,dict[str,float]],dict]:
    """BIS monthly series through 2026-08, without forward-rate substitution."""
    names={area:ccy for ccy,area in BIS_CCY_AREA.items()}
    rates={c:{} for c in CCYS}
    meta={c:{"sources":set(),"break_samples":set(),"compilations":set()}
          for c in CCYS}
    digest=hashlib.sha256(biszip.read_bytes()).hexdigest()
    with zipfile.ZipFile(biszip) as z:
        members=[n for n in z.namelist() if n.endswith(".csv")]
        if len(members)!=1:
            raise ValueError("POLICY_VOL20_BIS_FLAT_ARCHIVE_SCHEMA")
        with z.open(members[0]) as h:
            csvrows=csv.DictReader(io.TextIOWrapper(h,encoding="utf-8-sig",newline=""))
            required={"FREQ:Frequency","REF_AREA:Reference area",
                      "TIME_PERIOD:Time period or range","OBS_VALUE:Observation Value"}
            if not required.issubset(csvrows.fieldnames or []):
                raise ValueError("POLICY_VOL20_BIS_COLUMN_DRIFT")
            for row in csvrows:
                if not (row["FREQ:Frequency"] or "").startswith("M:"):
                    continue
                c=names.get((row["REF_AREA:Reference area"] or "").split(":")[0])
                if c is None:
                    continue
                period=(row["TIME_PERIOD:Time period or range"] or "").strip()
                if not "2016-08"<=period<="2026-08":
                    continue
                raw=(row["OBS_VALUE:Observation Value"] or "").strip()
                if not raw:
                    continue
                rate=float(raw)
                if not math.isfinite(rate) or not -20<=rate<=40 or period in rates[c]:
                    raise ValueError("POLICY_VOL20_BIS_DUPLICATE_OR_NAN_RATE")
                rates[c][period]=rate
                meta[c]["sources"].add((row.get("SOURCE_REF:Publication Source") or "")[:100])
                meta[c]["compilations"].add((row.get("COMPILATION:Compilation") or "")[:130])
                other=(row.get("SUPP_INFO_BREAKS:Supplemental information and breaks") or "").strip()
                if other:
                    meta[c]["break_samples"].add(other[:160])
    coverage={}
    for c in sorted(CCYS):
        series=sorted(rates[c])
        coverage[c]={
            "months":len(series),"first":series[0] if series else None,
            "last":series[-1] if series else None,
            "bis_area":BIS_CCY_AREA[c],"source":sorted(meta[c]["sources"]),
            "compilation":sorted(meta[c]["compilations"]),
            "break_examples":sorted(meta[c]["break_samples"])[:8],
        }
    return rates,{
        "official_dataset":"BIS:WS_CBPOL(1.0) monthly end of period",
        "official_source_zip_sha256":digest,"source_url":BIS_URL,
        "monthly_rates_not_published":True,
        "coverage":coverage,"authentic_vintages_not_verified":True,
    }


def realized_vol_pre_entry(
    all_days:dict[str,dict[date,Day]],common:list[date],position:int,
) ->float:
    """Each pair's 20 log returns from 21 common day CLOSES *strictly prior* to entry."""
    if position<GLOBAL_VOL_LOOKBACK+1:
        raise ValueError("POLICY_VOL20_PRIOR_21_SESSIONS_REQUIRED")
    variances=[]
    for s in FX28:
        returns=[
            math.log(all_days[s][common[j]].close/all_days[s][common[j-1]].close)
            for j in range(position-GLOBAL_VOL_LOOKBACK,position)
        ]
        if len(returns)!=20 or any(not math.isfinite(r) for r in returns):
            raise ValueError("POLICY_VOL20_PRIOR_20_RETURNS_INVALID")
        variances.append(stdev(returns)**2)
    vol=math.sqrt(mean(variances))*math.sqrt(252)
    if not math.isfinite(vol) or vol<=0:
        raise ValueError("POLICY_VOL20_ZERO_GLOBAL_VOL")
    return vol


def _bootstrap3(values:list[float],seed:int)->list[float]:
    if not values:
        raise ValueError("POLICY_VOL20_NO_CALENDAR")
    rng=random.Random(seed)
    n=len(values)
    results=[]
    for _ in range(B):
        drawn=[]
        while len(drawn)<n:
            start=rng.randrange(n)
            drawn.extend(values[(start+k)%n] for k in range(3))
        results.append(sum(drawn[:n])/n)
    results.sort()
    return [results[49],results[1949]]


def _sharpe(values:list[float])->float|None:
    if len(values)<12:
        return None
    v=stdev(values)
    return (mean(values)/v*math.sqrt(12)) if v>0 else None


def _skew(values:list[float])->float|None:
    n=len(values)
    if n<3:
        return None
    mu=mean(values)
    v=mean((x-mu)**2 for x in values)
    return mean((x-mu)**3 for x in values)/v**1.5 if v>0 else None


def _max_drawdown(values:list[float])->float:
    wealth=1.0
    high=1.0
    deepest=0.
    for bps in values:
        wealth*=1+bps/10000
        high=max(high,wealth)
        deepest=max(deepest,1-wealth/high)
    return deepest


def evaluate(rates:dict[str,dict[str,float]],
             original:dict[str,dict[date,Day]])->dict:
    if set(rates)!=set(CCYS) or set(original)!=set(FX28):
        raise ValueError("POLICY_VOL20_REQUIRE_28_FX_AND_8_COUNTRY_RATES")
    common=sorted(set.intersection(*(set(days) for days in original.values())))
    common=[d for d in common if HISTORY_START<=d<HISTORY_END_EXCLUSIVE]
    if len(common)<22:
        raise ValueError("POLICY_VOL20_TOO_FEW_COMMON_DAYS")
    index={d:i for i,d in enumerate(common)}
    combos=sorted({(d.year,d.month) for d in common})
    rows=[]
    censored=Counter()
    for y,m in combos:
        ym=f"{y:04d}-{m:02d}"
        py=previous_month(y,m)
        nexty,nextm=advance_month(y,m)
        entrances=[d for d in common if (d.year,d.month)==(y,m) and d.day>=16]
        exits=[d for d in common if (d.year,d.month)==(nexty,nextm) and d.day<16]
        if not entrances or not exits:
            censored["NO_COMMON_COMPLETE_MONTH"]+=1
            continue
        start=entrances[0]
        end=exits[-1]
        if start<DEV_END<=end or end>=HISTORY_END_EXCLUSIVE or (end-start).days<15:
            censored["ERA_BOUNDARY_OR_SHORT_HOLD_OR_CUTOFF"]+=1
            continue
        if any(
            py not in rates[c] or not isinstance(rates[c][py], (int, float))
            or not math.isfinite(rates[c][py])
            for c in CCYS
        ):
            censored["EIGHT_POLICY_PRIOR_EOM_MISSING"]+=1
            continue
        if index[start]<21:
            censored["PAST_20_GLOBAL_VOL_NOT_AVAILABLE"]+=1
            continue
        try:
            ann=realized_vol_pre_entry(original,common,index[start])
        except ValueError:
            censored["NONFINITE_GLOBAL_FX_VOL"]+=1
            continue
        scale=min(1.0,GLOBAL_ANNUAL_VOL_TARGET/ann)
        if not (0<scale<=1):
            raise ValueError("POLICY_VOL20_NOT_RISK_REDUCTION_ONLY")
        ordering=sorted(FX28,key=lambda s:(
            -(rates[s[:3]][py]-rates[s[3:]][py]),s
        ))
        long6=set(ordering[:6])
        short6=set(ordering[-6:])
        if len(long6)!=6 or len(short6)!=6 or long6&short6:
            raise ValueError("POLICY_VOL20_6X6_RANKING_FAILED")
        spot=accrued=0.
        currency={c:0. for c in CCYS}
        for s in sorted(long6|short6):
            w=(1/12) if s in long6 else (-1/12)
            spot+=w*10000*(original[s][end].close/original[s][start].open-1)
            accrued+=w*10000*((rates[s[:3]][py]-rates[s[3:]][py])/100)*(
                (end-start).days/365
            )
            currency[s[:3]]+=w
            currency[s[3:]]-=w
        pure=spot+accrued-4.
        risk=scale*pure
        rows.append({
            "month":ym,"signal_previous_eom":py,
            "entry_day_UTC_reference_not_fill":start.isoformat(),
            "exit_day_UTC_reference_not_fill":end.isoformat(),
            "era":"DEVELOPMENT" if start<DEV_END else "DIAGNOSTIC",
            "previously_embargoed_for_Alpha2":start>=RETAINED_HOLDOUT_START,
            "long6":sorted(long6),"short6":sorted(short6),
            "currency_exposure_by_base_and_quote":currency,
            "maximum_absolute_currency_exposure":max(map(abs,currency.values())),
            "prior_20d_global_28_pair_annual_fx_vol":ann,
            "pre_entry_notional_risk_scale":scale,
            "spot_gross_unscaled_bps":spot,
            "policy_accrual_HYPOTHETICAL_unscaled_bps":accrued,
            "unfiltered_assumed_cost_proxy_bps":pure,
            "scaled_assumed_cost_2bps_each_side_bps":4*scale,
            "filtered_spot_model_bps":spot*scale,
            "filtered_policy_HYPOTHETICAL_accrual_bps":accrued*scale,
            "filtered_gross_minus_assumed_cost_bps":risk,
            "paired_filtered_minus_pure_bps":risk-pure,
            "real_broker_NET_not_computed":True,
        })
    bymonth={r["month"]:r for r in rows}
    if len(rows)!=len(bymonth):
        raise ValueError("POLICY_VOL20_DOUBLE_DECISION_MONTH")
    segments={
        "DEVELOPMENT":((2016,9),(2022,1)),
        "DIAGNOSTIC":((2022,1),(2026,9)),
        "PREVIOUSLY_EMBARGOED_2024_2026":((2024,10),(2026,9)),
    }
    eras={}
    for k,(a,b) in enumerate(segments.items()):
        start,end=b
        y,m=start
        cal=[]
        while (y,m)<end:
            cal.append(f"{y:04d}-{m:02d}")
            y,m=advance_month(y,m)
        values=[bymonth[mon]["filtered_gross_minus_assumed_cost_bps"]
                if mon in bymonth else 0. for mon in cal]
        pure=[bymonth[mon]["unfiltered_assumed_cost_proxy_bps"]
              if mon in bymonth else 0. for mon in cal]
        difference=[x-y for x,y in zip(values,pure,strict=True)]
        n=sum(mon in bymonth for mon in cal)
        min_n=12 if k==2 else 24
        eros=[bymonth[mon] for mon in cal if mon in bymonth]
        eras[a]={
            "calendar_months_including_no_trade":len(cal),
            "executed_28_fx_months":n,
            "sample_gate_min_months":min_n,
            "sample_gate":n>=min_n,
            "mean_filtered_model_after_assumed_cost_bps":mean(values),
            "mean_unfiltered_model_after_assumed_cost_bps":mean(pure),
            "mean_paired_difference_filtered_minus_pure_bps":mean(difference),
            "CI95_filtered_3month_synchronized_block_bps":_bootstrap3(values,SEED+k*100),
            "CI95_unfiltered_3month_synchronized_block_bps":_bootstrap3(pure,SEED+k*100),
            "CI95_paired_3month_synchronized_block_bps":_bootstrap3(difference,SEED+k*100),
            "Sharpe_annualized_filtered_HYPOTHETICAL_model":_sharpe(values),
            "Sharpe_annualized_unfiltered_HYPOTHETICAL_model":_sharpe(pure),
            "model_filtered_skewness":_skew(values),
            "model_unfiltered_skewness":_skew(pure),
            "filtered_worst_month_bps":min(values),
            "unfiltered_worst_month_bps":min(pure),
            "filtered_max_drawdown_fraction_MODEL":_max_drawdown(values),
            "unfiltered_max_drawdown_fraction_MODEL":_max_drawdown(pure),
            "number_months_risk_reduced_exposure_below_one":sum(
                r["pre_entry_notional_risk_scale"]<1 for r in eros
            ),
            "mean_risk_scale_active_months":mean(
                r["pre_entry_notional_risk_scale"] for r in eros
            ) if eros else None,
            "max_currency_absolute_unfiltered_exposure":max(
                (r["maximum_absolute_currency_exposure"] for r in eros),default=None
            ),
        }
    diag=eras["DIAGNOSTIC"]
    held=eras["PREVIOUSLY_EMBARGOED_2024_2026"]
    dev=eras["DEVELOPMENT"]
    if not all(s["sample_gate"] for s in (dev,diag,held)):
        status="POLICY_VOL20_INCONCLUSIVE_MISSING_HOLDOUT"
    elif (diag["mean_filtered_model_after_assumed_cost_bps"]>0
          and diag["CI95_filtered_3month_synchronized_block_bps"][0]>0
          and diag["Sharpe_annualized_filtered_HYPOTHETICAL_model"] is not None
          and diag["Sharpe_annualized_filtered_HYPOTHETICAL_model"]>0.4
          and held["mean_filtered_model_after_assumed_cost_bps"]>0):
        status="POLICY_VOL20_EXPLORATORY_RISK_SCALE_PASS_NEEDS_INDEPENDENT_BROKER_NET_VINTAGE"
    else:
        status="POLICY_VOL20_FINAL_SCREEN_FAILED_CLOSE_LINE"
    return {
        "identity":IDENTITY,"prereg_ancestor":PREREG,
        "status":status,"closed_to_further_parameter_trials":True,
        "EUR_code_XM_BIS":True,"FX_currency_count":8,"FX_pair_count":28,
        "BIS_EOM_release_lag_assumed_not_proven_PIT":True,
        "broker_swap_or_forward_not_earned":True,
        "retained_2024_2026_source_not_globally_virgin_OOS":True,
        "M5_first_open_NOT_trade_fill":True,"original_28_joint_weekdays":len(common),
        "active_traded_months":len(rows),"censor_counts":dict(censored),
        "eras":eras,"month_contributions_hypothetical":rows,
        "real_broker_NET_PF_DD_not_computed":True,
        "UTC001_certified":False,"orders":0,
    }


def main()->None:
    p=argparse.ArgumentParser()
    c=p.add_subparsers(dest="action",required=True)
    ext=c.add_parser("extract")
    ext.add_argument("symbol",choices=FX28)
    ext.add_argument("source",type=Path)
    ext.add_argument("signed33",type=Path)
    ext.add_argument("cache",type=Path)
    ext.add_argument("--aggregate12",type=Path)
    fin=c.add_parser("finish")
    fin.add_argument("biszip",type=Path)
    fin.add_argument("cache",type=Path)
    fin.add_argument("out",type=Path)
    a=p.parse_args()
    if a.action=="extract":
        data=verified_extract(a.symbol,a.source,a.signed33,a.cache,a.aggregate12)
    else:
        rate,bisproof=official_rate_history(a.biszip)
        private,census=read_private_source(a.cache)
        data=evaluate(rate,private)
        data["bis_input_provenance_and_coverage"]=bisproof
        data["original28_source_census"]=census
        a.out.mkdir(parents=True,exist_ok=True)
        target=a.out/"FX28_policy_carry_LAST_VOL20_2016_2026_one_aggregate.json"
        target.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (a.out/"OUTPUT_SHA256SUMS.txt").write_text(
            hashlib.sha256(target.read_bytes()).hexdigest()+"  "+target.name+"\n",
            encoding="utf-8")
        data={"status":data["status"],"active_traded_months":data["active_traded_months"],
              "DIAG":data["eras"]["DIAGNOSTIC"]["mean_filtered_model_after_assumed_cost_bps"],
              "HOLDOUT":data["eras"]["PREVIOUSLY_EMBARGOED_2024_2026"]["mean_filtered_model_after_assumed_cost_bps"],
              "NET":"BLOCKED","orders":0}
    print(json.dumps(data,sort_keys=True))


if __name__=="__main__":
    main()
