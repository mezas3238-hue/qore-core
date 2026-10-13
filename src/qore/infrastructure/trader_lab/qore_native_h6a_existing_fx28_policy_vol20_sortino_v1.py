"""H6a ONE frozen 2016–2024 FX policy carry global-vol-20D experiment.

PROVENANCE: single prereg commit 8a2b9605e562a243fc2f79b48367d946f062ae13.
Research-only: existing H5 source ingestion and BIS rate m-2, no post-2024-09-16.
All "interest" returns are counterfactual policy-rate accrual, not broker NET.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_h5_bis_policy_fx28_one_test_v1 as h5
from qore.infrastructure.trader_lab import qore_native_d1_tsmom20_single_edge_v1 as src

IDENTITY="QORE_NATIVE_H6A_EXISTING_WINDOW_28FX_BIS_POLICY_VOL20_SORTINO_ONE_TEST_V1"
MAJORS=("AUDUSD","EURUSD","GBPUSD","NZDUSD","USDCAD","USDCHF","USDJPY")
WINDOW=20
ANNUAL_TARGET=.10
LEVERAGE_CAP=2.
FEE_PER_NOTIONAL_SIDE=.0002
BOOTSTRAP_REPS=10000
BOOTSTRAP_SEED=20261012


def vol_target_multiplier(calendar:list[date],maps:dict[str,dict],index:int):
    """Exactly 20 previous log close-to-close returns from common-session days."""
    if index<WINDOW+1:raise ValueError("H6A_INSUFFICIENT_COMPLETED_VOL20_RETURNS")
    vols=[]
    for s in MAJORS:
        if s not in maps:raise ValueError("H6A_MAJORS_NOT_IN_MARKET_PANEL")
        returns=[]
        for j in range(index-WINDOW,index):
            p0=maps[s][calendar[j-1]]["close"]
            p1=maps[s][calendar[j]]["close"]
            if p0<=0 or p1<=0 or not math.isfinite(p0+p1):
                raise ValueError("H6A_BAD_CLOSED_PRICE")
            returns.append(math.log(p1/p0))
        if len(returns)!=20:
            raise ValueError("H6A_NOT_EXACT_20")
        v=statistics.stdev(returns)*math.sqrt(252)
        if not math.isfinite(v):raise ValueError("H6A_BAD_VOL")
        vols.append(v)
    rms=math.sqrt(sum(x*x for x in vols)/len(vols))
    if rms<=0 or not math.isfinite(rms):raise ValueError("H6A_ZERO_OR_BAD_GLOBAL_VOL")
    mult=min(LEVERAGE_CAP,ANNUAL_TARGET/rms)
    if not 0<mult<=LEVERAGE_CAP:raise ValueError("H6A_BAD_MULTIPLIER")
    return mult,rms


def monthly_compounded(day_to_return:dict[date,float]):
    bucket=defaultdict(list)
    for d,r in sorted(day_to_return.items()):
        if not math.isfinite(r) or r<=-1:
            raise ValueError("H6A_BAD_DAILY_RETURN_LEVERED")
        bucket[(d.year,d.month)].append(r)
    records=[]
    for (yr,month),values in sorted(bucket.items()):
        total=1.
        for r in values:total*=1+r
        records.append({"month":f"{yr}-{month:02d}","return":total-1.,
                        "trading_days":len(values)})
    return records


def _sortino(data:list[float]):
    if not data:return None
    down=math.sqrt(sum(min(0.,x)**2 for x in data)/len(data))
    if down<=1.e-15:return None
    return math.sqrt(12)*statistics.mean(data)/down


def bootstrap_mean_sortino(data:list[float],block:int=6,reps:int=BOOTSTRAP_REPS,
                           seed:int=BOOTSTRAP_SEED):
    """Circular moving-block bootstrap retains within-block serial structure."""
    if not data or block<=0 or reps<=0:
        raise ValueError("H6A_BOOTSTRAP_INVALID_SPEC")
    n=len(data)
    rng=random.Random(seed)
    means=[]
    sortinos=[]
    for _ in range(reps):
        selected=[]
        while len(selected)<n:
            k=rng.randrange(n)
            selected.extend(data[(k+i)%n] for i in range(block))
        selected=selected[:n]
        means.append(sum(selected)/n)
        so=_sortino(selected)
        if so is not None and math.isfinite(so):sortinos.append(so)
    means.sort()
    sortinos.sort()
    def quantile(vals,q):
        if not vals:return None
        p=q*(len(vals)-1)
        a=int(math.floor(p)); b=int(math.ceil(p))
        return vals[a]*(b-p)+vals[b]*(p-a) if b>a else vals[a]
    return {
        "bootstrap_type":"CIRCULAR_MOVING_BLOCK_MONTHLY",
        "block_months":block,
        "repetitions":reps,
        "seed":seed,
        "monthly_mean_95pct_CI":[quantile(means,.025),quantile(means,.975)],
        "sortino_95pct_CI":[quantile(sortinos,.025),quantile(sortinos,.975)],
        "undefined_sortino_bootstrap_draws":reps-len(sortinos),
    }


def risk_metrics(months:list[dict],seed:int=BOOTSTRAP_SEED):
    data=[m["return"] for m in months]
    n=len(data)
    if n<20:raise ValueError("H6A_TOO_FEW_MONTHLY_RETURNS")
    mu=statistics.mean(data)
    std=statistics.stdev(data)
    sharpe=math.sqrt(12)*mu/std if std>0 else None
    sortino=_sortino(data)
    equity=1.
    peak=1.
    maxdd=0.
    for r in data:
        equity*=1+r
        peak=max(peak,equity)
        maxdd=min(maxdd,equity/peak-1)
    CAGR=(equity**(12/n)-1) if equity>0 else None
    calmar=CAGR/abs(maxdd) if CAGR is not None and maxdd<0 else None
    central=[x-mu for x in data]
    m2=sum(x*x for x in central)/n
    m3=sum(x**3 for x in central)/n
    m4=sum(x**4 for x in central)/n
    skew=m3/(m2**1.5) if m2>1e-25 else None
    kurt=m4/(m2*m2)-3 if m2>1e-25 else None
    # Pezier-White stylized adjustment on monthly Sharpe (report NOT gating).
    monthly_sr=mu/std if std>0 else None
    adjusted=(monthly_sr*(1+skew*monthly_sr/6
               -(kurt*monthly_sr*monthly_sr)/24)*math.sqrt(12)
              if monthly_sr is not None and skew is not None else None)
    k=max(1,math.ceil(.05*n))
    monthly_tail=sorted(data)
    return {
        "complete_or_partial_months_included":n,
        "mean_monthly_return":mu,
        "CAGR_monthly_compounded":CAGR,
        "annualized_Sharpe_monthly_rf0":sharpe,
        "annualized_Sortino_monthly_MAR0":sortino,
        "Pezier_White_style_adjusted_Sharpe_exploratory":adjusted,
        "Calmar_CAGR_div_maxDD":calmar,
        "max_drawdown_month_end":maxdd,
        "worst_month":min(data),
        "expected_shortfall_worst_5pct_months":sum(monthly_tail[:k])/k,
        "ES5pct_tail_month_count":k,
        "sample_skewness_moment":skew,
        "sample_excess_kurtosis_moment":kurt,
        "negative_months":sum(x<0 for x in data),
        "last_partial_month_possible":months[-1]["month"]=="2024-09",
        "bootstrap_6_month_blocks":bootstrap_mean_sortino(data,6,seed=seed),
        "bootstrap_12_month_blocks_sensitivity_only":bootstrap_mean_sortino(data,12,seed=seed),
    }


def evaluate(dailies:dict,rates:dict[str,dict[date,float]]):
    calendar,maps,coverage=h5.calendar_and_maps(dailies)
    if len(calendar)<21:raise ValueError("H6A_NO_LOOKBACK")
    # Prevent hiding missing source months behind selected days.
    for c in h5.CURRENCY_BIS:
        if c not in rates:raise ValueError("H6A_POLICY_CURRENCY_MISSING_"+c)
    result={}
    for era,start,end in (
        ("DEV",src.DEV_START,src.VALIDATION_START),
        ("DIAG",src.VALIDATION_START,src.EMBARGO),
    ):
        dates=[x for x in calendar if start<=x<end]
        if len(dates)<100:raise ValueError("H6A_TOO_FEW_SOURCE_DAYS")
        pos={s:0. for s in h5.FX28}
        diff={s:0. for s in h5.FX28}
        last_date=None
        last_month=None
        spot_daily={}
        ideal_daily={}
        rebalances=0; turnover=0.; fees=0.
        max_gross=0.; max_currency_exposure=0.
        multipliers=[]; first_decisions=[]
        for d in dates:
            pnl=0.; policy_interest=0.
            if last_date is not None:
                elapsed=(d-last_date).days
                if elapsed>src.MAX_GAP_DAYS:raise ValueError("H6A_EXCESSIVE_MARK_GAP")
                for s,p in pos.items():
                    move=maps[s][d]["entry_open"]/maps[s][last_date]["entry_open"]-1.
                    if not math.isfinite(move) or abs(move)>.45:
                        raise ValueError("H6A_BAD_M5_MARK")
                    pnl+=p*move
                    policy_interest+=p*(diff[s]/100.)*elapsed/365.
            last_date=d
            fee=0.
            ym=(d.year,d.month)
            if ym!=last_month and d>=h5.FIRST_RATE_COMPLETE_DECISION_MONTH:
                idx=calendar.index(d)
                multiplier,annual_vol=vol_target_multiplier(calendar,maps,idx)
                base,diffs=h5.policy_basket(rates,d)
                target={s:base[s]*multiplier for s in h5.FX28}
                delta=sum(abs(target[s]-pos[s]) for s in h5.FX28)
                fee+=FEE_PER_NOTIONAL_SIDE*delta
                turnover+=delta
                pos=target
                diff=diffs
                last_month=ym
                rebalances+=1
                multipliers.append(multiplier)
                max_gross=max(max_gross,sum(abs(x) for x in pos.values()))
                exposure=defaultdict(float)
                for s,w in pos.items():
                    exposure[s[:3]]+=w
                    exposure[s[3:]]-=w
                max_currency_exposure=max(
                    max_currency_exposure,max(abs(v) for v in exposure.values()))
                if len(first_decisions)<3:
                    first_decisions.append({
                        "day":d.isoformat(),"policy_month":h5.month_minus(d,2).isoformat(),
                        "global_rms_vol20_annualized":annual_vol,
                        "leverage_multiplier":multiplier,
                        "long_pairs":sorted(s for s in pos if pos[s]>0),
                        "short_pairs":sorted(s for s in pos if pos[s]<0),
                    })
            if d==dates[-1]:
                change=sum(abs(w) for w in pos.values())
                fee+=FEE_PER_NOTIONAL_SIDE*change
                turnover+=change
                pos={s:0. for s in h5.FX28}
            fees+=fee
            spot_daily[d]=pnl-fee
            ideal_daily[d]=pnl+policy_interest-fee
        A=monthly_compounded(spot_daily)
        B=monthly_compounded(ideal_daily)
        if [m["month"] for m in A]!=[m["month"] for m in B]:
            raise ValueError("H6A_MONTHLY_STREAM_MISMATCH")
        result[era]={
            "spot_only_assumed_2bp":risk_metrics(A),
            "spot_plus_ideal_policy_accrual_not_broker_NET":risk_metrics(B),
            "monthly_observation_month_labels":[x["month"] for x in A],
            "monthly_days_counts":[x["trading_days"] for x in A],
            "source_common_days":len(dates),
            "monthly_rebalance_events":rebalances,
            "turnover_abs_nominal_weight_sides":turnover,
            "assumed_2bp_cost_bps_nav_uncompounded":fees*1e4,
            "leverage_multiplier_min":min(multipliers),
            "leverage_multiplier_max":max(multipliers),
            "max_gross_nominal_exposure":max_gross,
            "max_single_currency_net_exposure_nominal":max_currency_exposure,
            "first_3_decisions_nonselective_witness":first_decisions,
        }
    diag=result["DIAG"]["spot_plus_ideal_policy_accrual_not_broker_NET"]
    s=diag["annualized_Sortino_monthly_MAR0"]
    lower=diag["bootstrap_6_month_blocks"]["monthly_mean_95pct_CI"][0]
    promising=(s is not None and s>.5 and lower>0)
    return {
        "identity":IDENTITY,
        "status":"PROMISING_IDEALIZED_ONLY_NOT_CERTIFIED" if promising
                 else "NO_PROMOTION_EXPLORATORY",
        "performance":result,
        "FX28_original_G0_source_calendar":coverage,
        "policy_rate_source":"BIS_WS_CBPOL_8_CURRENCIES_M_MINUS_2",
        "volatility_formula":"RMS(seven_USD_majors_20_log_close_returns×sqrt252)",
        "target_vol_rms_seven_majors":ANNUAL_TARGET,
        "gross_multiplier_cap":LEVERAGE_CAP,
        "weight_monthly_frozen_until_next_rebalance":True,
        "2_bps_cost_per_notional_side":True,
        "sortino_only_monthly_not_daily":True,
        "DIAG_IS_ALREADY_EXPOSED_ADAPTIVE_EXPLORATORY":True,
        "bootstrap_is_not_independent_confirmation":True,
        "source_broker_swaps_actual_forward_discount_verified":False,
        "ideal_policy_yield_is_not_broker_excess_return":True,
        "M5_common_day_calendar_retrospective_selection_risk":True,
        "holdout_2024_09_17_onward_opened":False,
        "production_untouched":True,
        "certified_traders":0,
    }


def run(workdir:Path,output:Path):
    repo=os.getenv("GITHUB_REPOSITORY","mezas3238-hue/qore-core")
    token=os.getenv("GH_TOKEN")
    if not token:raise ValueError("H6A_GITHUB_READONLY_TOKEN_REQUIRED")
    rates={}
    rate_witness=[]
    for c in sorted(h5.CURRENCY_BIS):
        raw,meta=h5.fetch_policy(c)
        rates[c]=h5.parse_policy_rates(raw,c)
        rate_witness.append(meta)
        print("H6A_BIS_EIGHT_POLICY_RATE_SOURCE_PASS",c,len(rates[c]),flush=True)
    workdir.mkdir(parents=True,exist_ok=True)
    reg=src.get_artifact_register(repo,token)
    original_witness=[]
    dailies={}
    for s in h5.FX28:
        item=reg[s]
        archive=workdir/(s+".zip")
        try:
            subprocess.run([
                "curl","--fail","--silent","--show-error","--location",
                "--retry","2","-H",f"Authorization: Bearer {token}",
                "-H","Accept: application/vnd.github+json",
                f"https://api.github.com/repos/{repo}/actions/artifacts/{item['artifact_id']}/zip",
                "--output",str(archive)],check=True)
            bars,witness=src.daily_from_zip(archive,s)
            dailies[s]=bars
            witness["original_run"]=item["original_run"]
            original_witness.append(witness)
            print("H6A_FX28_G0_SHA_PASS",s,len(bars),flush=True)
        finally:
            archive.unlink(missing_ok=True)
    if len(original_witness)!=28 or len(rate_witness)!=8 or not all(
        x.get("source_sha_verified_11_annual_partitions") is True for x in original_witness
    ):
        raise ValueError("H6A_SOURCE_CUSTODY_NOT_28_OR_RATES8")
    result=evaluate(dailies,rates)
    result["original_28_source_hash_witnesses"]=original_witness
    result["BIS_8_monthly_rate_hash_witnesses"]=rate_witness
    output.mkdir(parents=True,exist_ok=True)
    file=output/"H6A_FX28_BIS8_VOL20_SORTINO_CRASH_EXPLORATORY_RESULT.json"
    file.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    (output/"SHA256SUMS.txt").write_text(
        hashlib.sha256(file.read_bytes()).hexdigest()+"  "+file.name+"\n")
    compact={}
    for era in ("DEV","DIAG"):
        a=result["performance"][era]
        compact[era]={
            "spot":a["spot_only_assumed_2bp"],
            "ideal":a["spot_plus_ideal_policy_accrual_not_broker_NET"],
            "rebalances":a["monthly_rebalance_events"],
            "cost_bp":a["assumed_2bp_cost_bps_nav_uncompounded"],
        }
    print("H6A_COMPLETE_SINGLE_ECONOMIC_RESULT",json.dumps({
        "verdict":result["status"],"metrics":compact,
        "fx":len(original_witness),"policy":len(rate_witness),
        "holdout_open":False,"broker_NET":False,"certified":0,
    },sort_keys=True),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("tmp",type=Path)
    parser.add_argument("out",type=Path)
    args=parser.parse_args()
    run(args.tmp,args.out)


if __name__=="__main__":main()
