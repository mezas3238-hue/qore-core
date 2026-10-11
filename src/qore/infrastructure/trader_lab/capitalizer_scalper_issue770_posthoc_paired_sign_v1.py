"""Issue770 POSTHOC direction-sign anomaly, day-cluster paired dependence audit.

The outcome anomaly was seen BEFORE this audit. Never call this preregistered,
independent OOS, source-author proof, broker pricing or inverted LIVE edge.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_scalper_issue770_1to1_market_v1 import (
    RESOLVED,
    rows,
)

IDENTITY="QORE_SCALPER_ISSUE770_POSTHOC_PAIRED_SIGN_SHOCK_AUDIT_V1"
REPS=2000
BLOCK=5


def quantile(a:list[float],p:float)->float:
    if not a:
        raise ValueError("empty paired comparison")
    ordered=sorted(a)
    return ordered[min(len(ordered)-1,round(p*(len(ordered)-1)))]


def comparative(
    selected:tuple[dict[str,Any],...],scenario:str,reverse:str,
)->dict[str,Any]:
    by_date:dict[str,list[float]]=defaultdict(list)
    by_market:dict[str,list[float]]=defaultdict(list)
    by_quarter:dict[str,list[float]]=defaultdict(list)
    original_only=reverse_only=both_censored=0
    counts:Counter[str]=Counter()
    paired_rows=[]
    for item in selected:
        p=item[scenario]
        q=item[reverse]
        first=p["status"] in RESOLVED
        other=q["status"] in RESOLVED
        if first and other:
            change=float(q["R"])-float(p["R"])
            day=item["operating_date"]
            by_date[day].append(change)
            by_market[item["symbol"]].append(change)
            quarter=day[:4]+"Q"+str((int(day[5:7])-1)//3+1)
            by_quarter[quarter].append(change)
            paired_rows.append({
                "source_opportunity_id":item["source_opportunity_id"],
                "date":day,"symbol":item["symbol"],
                "opposite_minus_source_gross_R":change,
                "source_exit_at":p["exit_at"],
                "opposite_exit_at":q["exit_at"],
                "asof_policy":False,
                "historical_counterfactual_only":True,
            })
        elif first:
            original_only+=1
        elif other:
            reverse_only+=1
        else:
            both_censored+=1
        counts[p["status"]+"|"+q["status"]]+=1
    if len(paired_rows)+original_only+reverse_only+both_censored!=len(selected):
        raise ValueError("unpaired frozen source identity")
    dates=sorted(by_date)
    if len(dates)<BLOCK:
        raise ValueError("requires five or more observed operating dates")
    deltas=[v for vals in by_date.values() for v in vals]
    observed=sum(deltas)/len(deltas)
    rng=random.Random(20261011)
    bootstrap=[]
    for _ in range(REPS):
        days:list[str]=[]
        while len(days)<len(dates):
            i=rng.randrange(len(dates)-BLOCK+1)
            days.extend(dates[i:i+BLOCK])
        vals=[v for date in days[:len(dates)] for v in by_date[date]]
        bootstrap.append(sum(vals)/len(vals))
    # A day-cluster exchangeable sign test: conditional on exact entry times,
    # swap ALL trades for a given operating day together. Not randomized entry.
    signs=random.Random(20261111)
    clustered_sign=[]
    for _ in range(REPS):
        val:list[float]=[]
        for date in dates:
            sign=-1 if signs.getrandbits(1) else 1
            val.extend(sign*x for x in by_date[date])
        clustered_sign.append(sum(val)/len(val))
    p_mirror_positive=(
        1+sum(x>=observed for x in clustered_sign)
    )/(REPS+1)
    return {
        "scenario":scenario,"n_original_intents":len(selected),
        "paired_resolved_count":len(paired_rows),
        "original_resolved_only":original_only,
        "reverse_resolved_only":reverse_only,
        "both_censored":both_censored,
        "identical_censor_identity":original_only==0 and reverse_only==0,
        "mean_opposite_minus_original_gross_R":observed,
        "day_block_95pct_bootstrap_delta_R":[
            quantile(bootstrap,0.025),quantile(bootstrap,0.975)
        ],
        "days_observed":len(dates),
        "day_cluster_random_sign_swap_p_mirror_superiority":p_mirror_positive,
        "same_day_sign_swap_null_2p5_97p5_R":[
            quantile(clustered_sign,0.025),
            quantile(clustered_sign,0.975),
        ],
        "by_market":{
            k:{"n":len(v),"mean_delta_R":sum(v)/len(v)}
            for k,v in sorted(by_market.items())
        },
        "by_quarter":{
            k:{"n":len(v),"mean_delta_R":sum(v)/len(v)}
            for k,v in sorted(by_quarter.items())
        },
        "paired_resolution_statuses":dict(sorted(counts.items())),
        "posthoc_followup_NOT_preregistered":True,
        "broker_physical_costs_proven":False,
        "real_reverse_stop_TTrades_validated":False,
        "real_entry_time_random_placebo_executed":False,
        "independent_holdout":False,
        "sign_reversal_trade_authority":False,
        "not_certified":True,
        "_post_event_rows":paired_rows,
    }


def run(input_root:Path,output:Path)->dict[str,Any]:
    files=tuple(input_root.rglob(
        "scalper-issue770-original-A-2020-two-1to1-scenarios.jsonl"
    ))
    summaries=tuple(input_root.rglob(
        "scalper-issue770-scientific-nine-market.json"
    ))
    if len(files)!=1 or len(summaries)!=1:
        raise ValueError("exact original 2020 artifact and summary required")
    items=tuple(rows(files[0]))
    original=json.loads(summaries[0].read_text(encoding="utf-8"))
    if (
        len(items)!=2020 or len({x["source_opportunity_id"] for x in items})!=2020
        or original["source_ids_conserved"]!=2876
        or original["original_A_2020"]!=2020
        or not original["baseline_reconstructed_exact"]
    ):
        raise ValueError("original 2876/2020 source identity changed")
    out:dict[str,Any]={
        "identity":IDENTITY,"source_intents":2020,
        "primary_1to1_replay_changed":False,
        "run_is_posthoc":True,
        "confirmatory_pvalue":False,
        "certified":False,
    }
    output.mkdir(parents=True,exist_ok=True)
    for scenario,mirror in (
        ("pure_1to1","reverse_direction_same_time_pure"),
        ("session_capped_1to1","reverse_direction_same_time_session_capped"),
    ):
        result=comparative(items,scenario,mirror)
        trace=result.pop("_post_event_rows")
        (output/f"scalper-issue770-posthoc-paired-{scenario}.jsonl").write_text(
            "".join(json.dumps(v,sort_keys=True)+"\n" for v in trace),
            encoding="utf-8",
        )
        out[scenario]=result
    (output/"scalper-issue770-posthoc-cluster-paired.json").write_text(
        json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8",
    )
    print("ISSUE770_POSTHOC_SIGN",json.dumps({
        k:{
            "paired":out[k]["paired_resolved_count"],
            "censored":out[k]["both_censored"],
            "mean_delta":out[k]["mean_opposite_minus_original_gross_R"],
            "CI95":out[k]["day_block_95pct_bootstrap_delta_R"],
            "day_cluster_p":out[k][
                "day_cluster_random_sign_swap_p_mirror_superiority"
            ],
        }
        for k in ("pure_1to1","session_capped_1to1")
    },sort_keys=True))
    return out


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("original_repo_artifact",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    run(args.original_repo_artifact,args.output)


if __name__=="__main__":
    main()
