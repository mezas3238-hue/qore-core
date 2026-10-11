"""DCVC Gate1/2 frozen-policy, consumption-aware, source-anchored scientific audit.

A/B v0.1 is READ ONLY. Null selection never accesses outcomes until after
random IDs are drawn; Gate2 replays v0.1 State using B-selected and settled
trade histories, not paper-shadow or rejected-trade outcomes.
All physical broker-cost and true OOS claims are explicitly disabled.
"""
from __future__ import annotations

import argparse
import heapq
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_ab_experiment_v1 import (
    DCVCState,
    read_jsonl,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_causal_features_v1 import (
    DCVCPredecision,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
)

IDENTITY="QORE_SCALPER_DCVC_GATE1_GATE2_FROZEN_POLICY_EXPLORATORY_V1"
N_GLOBAL=2000
N_STRATIFIED=1000
N_POWER=1000
ASSUMED_COST_R=0.025
SHIFTS=(0.05,0.10,0.20,0.30)
TARGET_N=266
SOURCE_N=2876
MAX_PER_SLOT=3


@dataclass(frozen=True,slots=True)
class Data:
    features:dict[str,DCVCPredecision]
    trades:dict[str,V49EconomicTrade]
    decisions:dict[str,dict[str,Any]]
    a_ids:frozenset[str]
    b_ids:frozenset[str]


def source_data(source_root:Path,original_root:Path)->Data:
    feature_paths=tuple(sorted(source_root.rglob("dcvc-predecision.jsonl")))
    outcome_paths=tuple(sorted(source_root.rglob("dcvc-outcomes-after-settlement.jsonl")))
    decisions_paths=tuple(original_root.rglob("dcvc-decisions-outcome-blind.jsonl"))
    if len(feature_paths)!=9 or len(outcome_paths)!=9 or len(decisions_paths)!=1:
        raise ValueError("requires exactly 9 native ledgers and frozen V01 decisions")
    records=tuple(row for p in feature_paths for row in read_jsonl(p))
    outcomes=tuple(row for p in outcome_paths for row in read_jsonl(p))
    decisions=tuple(read_jsonl(decisions_paths[0]))
    if any(len(v)!=SOURCE_N for v in (records,outcomes,decisions)):
        raise ValueError("2876 frozen opportunities expected in ALL ledgers")
    features={x["source_opportunity_id"]:DCVCPredecision(**x) for x in records}
    raw_outcomes={x["source_opportunity_id"]:x for x in outcomes}
    decision_map={x["source_opportunity_id"]:x for x in decisions}
    if (any(len(v)!=SOURCE_N for v in (features,raw_outcomes,decision_map))
            or set(features)!=set(raw_outcomes) or set(features)!=set(decision_map)):
        raise ValueError("duplicates or unpaired historical source IDs")
    trades={
        sid:V49EconomicTrade(**{k:v for k,v in item.items()
                                if k!="source_opportunity_id"})
        for sid,item in raw_outcomes.items()
    }
    original=tuple(x for _,x in _portfolio_select(tuple(trades.values())))
    key=lambda x:(x.symbol,x.session,x.operating_date,
                  x.entry_at,x.trigger_family,x.h1_state_basis)
    ids={key(trade):sid for sid,trade in trades.items()}
    if len(ids)!=SOURCE_N:
        raise ValueError("nonunique frozen economic key")
    a_ids=frozenset(ids[key(t)] for t in original)
    b_ids=frozenset(sid for sid,d in decision_map.items() if d["selected"])
    base=_metrics(original)
    bstats=_metrics(tuple(trades[sid] for sid in b_ids))
    if (
        len(a_ids)!=2020 or base.wins!=1167
        or abs(Decimal(base.max_drawdown_r)-Decimal("236.1342843563"))
        >Decimal("0.00001")
        or abs(Decimal(base.profit_factor or "0")-Decimal("0.6644630742"))
        >Decimal("0.000001")
        or len(b_ids)!=TARGET_N
        or abs(Decimal(bstats.max_drawdown_r)-Decimal("19.93243852075"))
        >Decimal("0.00001")
        or abs(Decimal(bstats.profit_factor or "0")-Decimal("0.8518247147"))
        >Decimal("0.000001")
        or sum(f.regime=="UNKNOWN" for f in features.values())!=184
        or sum(features[sid].regime=="UNKNOWN" for sid in b_ids)!=181
    ):
        raise ValueError("source A/B policy baseline not reproduced exactly")
    return Data(features,trades,decision_map,a_ids,b_ids)


def slot(data:Data,sid:str)->tuple[str,str]:
    f=data.features[sid]
    return f.session,f.operating_date


def _valid_sample(data:Data,ids:list[str],n:int)->tuple[str,...]:
    capacity:Counter[tuple[str,str]]=Counter()
    selection:list[str]=[]
    for sid in ids:
        key=slot(data,sid)
        if capacity[key]>=MAX_PER_SLOT:
            continue
        selection.append(sid)
        capacity[key]+=1
        if len(selection)==n:
            break
    if len(selection)!=n:
        raise ValueError("randomization cannot satisfy MAX3 and n")
    return tuple(selection)


def global_sample(data:Data,seed:int)->tuple[str,...]:
    """Offline equal-N unconditional permutation, NOT an online algorithm."""
    rng=random.Random(seed)
    ids=sorted(data.features)
    rng.shuffle(ids)
    return _valid_sample(data,ids,TARGET_N)


def original_a_sample(data:Data,seed:int)->tuple[str,...]:
    rng=random.Random(seed)
    ids=sorted(data.a_ids)
    rng.shuffle(ids)
    return _valid_sample(data,ids,TARGET_N)


def strata_sample(data:Data,seed:int)->tuple[str,...]:
    """Sensitivity only: B symbol/session counts were discovered posthoc."""
    quota=Counter(
        (data.features[sid].symbol,data.features[sid].session)
        for sid in data.b_ids
    )
    pool:dict[tuple[str,str],list[str]]=defaultdict(list)
    for sid,f in data.features.items():
        pool[(f.symbol,f.session)].append(sid)
    rng=random.Random(seed)
    # Independent randomizations with backtracking if global MAX3 prevents
    # filling an exact posthoc symbol/session quota.
    for _ in range(12):
        capacity:Counter[tuple[str,str]]=Counter()
        kept:list[str]=[]
        shuffled={k:rng.sample(v,len(v)) for k,v in pool.items()}
        # Least flexible strata are reserved before the dense ones.
        keys=sorted(quota,key=lambda k:(len(pool[k])/quota[k],k))
        ok=True
        for k in keys:
            n=0
            for sid in shuffled[k]:
                cap=slot(data,sid)
                if capacity[cap]>=MAX_PER_SLOT:
                    continue
                kept.append(sid)
                capacity[cap]+=1
                n+=1
                if n==quota[k]:
                    break
            if n!=quota[k]:
                ok=False
                break
        if ok and len(kept)==TARGET_N:
            return tuple(kept)
    raise ValueError("matched marginal null infeasible after 12 retries")


def outcome(data:Data,ids:tuple[str,...]|frozenset[str],
            cost:float=ASSUMED_COST_R)->dict[str,float|int|None]:
    selected=sorted(
        (data.trades[sid] for sid in ids),
        key=lambda t:(t.exit_at,t.entry_at,t.symbol),
    )
    values=[float(x.realized_gross_r)-cost for x in selected]
    gain=sum(v for v in values if v>0)
    loss=-sum(v for v in values if v<0)
    running=peak=dd=0.0
    for value in values:
        running+=value
        peak=max(peak,running)
        dd=max(dd,peak-running)
    return {
        "n":len(values),
        "PF":gain/loss if loss>0 else None,
        "expectancy_R":sum(values)/len(values) if values else None,
        "max_drawdown_R":dd,
        "gross_gain_after_cost_R":gain,
        "gross_loss_after_cost_R":loss,
        "result_after_cost_R":sum(values),
        "wins":sum(x>0 for x in values),
    }


def percentile(values:list[float],q:float)->float:
    ordered=sorted(values)
    if not ordered:
        raise ValueError("empty randomization")
    ix=min(len(ordered)-1,max(0,round(q*(len(ordered)-1))))
    return ordered[ix]


def holm_one_sided(p:dict[str,float])->dict[str,float]:
    ordered=sorted(p,key=p.__getitem__)
    prior=0.0
    corrected={}
    for i,key in enumerate(ordered):
        prior=max(prior,min(1.0,p[key]*(len(p)-i)))
        corrected[key]=prior
    return corrected


def null_distribution(
    data:Data,method:str,count:int,seed_base:int,
)->dict[str,Any]:
    fn={
        "GLOBAL_2876_MAX3":global_sample,
        "A_FIRST3_2020_MAX3":original_a_sample,
        "B_SYMBOL_SESSION_MARGIN_POSTHOC":strata_sample,
    }[method]
    observations=[]
    for seed in range(seed_base,seed_base+count):
        ids=fn(data,seed)
        if len(set(ids))!=TARGET_N:
            raise ValueError("duplicate or incomplete random sample")
        observations.append(outcome(data,ids))
    expected=outcome(data,data.b_ids)
    metrics=("expectancy_R","PF","max_drawdown_R")
    raw_p={}
    metrics_out={}
    for metric in metrics:
        x=expected[metric]
        if not isinstance(x,float):
            raise ValueError("B result not available")
        distribution=[row[metric] for row in observations]
        if any(not isinstance(v,float) for v in distribution):
            raise ValueError("placebo needs finite losses and all metrics")
        series=[float(v) for v in distribution]
        tail_count=sum(
            v>=x if metric!="max_drawdown_R" else v<=x for v in series
        )
        p=(tail_count+1)/(count+1)
        raw_p[metric]=p
        metrics_out[metric]={
            "B_observed":x,
            "placebo_p025":percentile(series,0.025),
            "placebo_median":percentile(series,0.5),
            "placebo_p975":percentile(series,0.975),
            "placebo_mean":sum(series)/len(series),
            "one_sided_empirical_p":p,
            "tails_as_good_as_B":tail_count,
        }
    return {
        "method":method,"replications":count,
        "same_total_B_exposure_trades":TARGET_N,
        "max3_enforced_on_each_replication":True,
        "selection_uses_outcomes":False,
        "conditioning_B_counts_per_day":False,
        "conditioning_B_marginal_counts":method=="B_SYMBOL_SESSION_MARGIN_POSTHOC",
        "executable_causal_policy":False,
        "confirmatory_test":False,
        "metrics_assumed_cost_0p025R":metrics_out,
        "holm_adjusted_three_endpoints":holm_one_sided(raw_p),
        "null_distribution":observations,
    }


def power_diagnostic(data:Data,global_null:dict[str,Any])->dict[str,Any]:
    threshold=float(
        global_null["metrics_assumed_cost_0p025R"]["expectancy_R"]["placebo_p975"]
    )
    # One-sided 5% threshold must be p95, not upper 97.5%.
    values=[float(x["expectancy_R"]) for x in global_null["null_distribution"]]
    threshold=percentile(values,0.95)
    scenario_counts={str(x):0 for x in SHIFTS}
    for seed in range(20263000,20263000+N_POWER):
        ids=global_sample(data,seed)
        r=float(outcome(data,ids)["expectancy_R"])
        for shift in SHIFTS:
            if r+shift>threshold:
                scenario_counts[str(shift)]+=1
    powers={key:count/N_POWER for key,count in scenario_counts.items()}
    reached=next((float(k) for k,power in powers.items() if power>=0.8),None)
    return {
        "simulation_count":N_POWER,"null_one_sided_alpha":0.05,
        "null_expectancy_threshold_R_assumed_cost_0p025R":threshold,
        "hypothetical_uniform_shift_R_per_trade":list(SHIFTS),
        "rejection_power_if_shift_hypothetically_exists":powers,
        "smallest_grid_shift_at_least_80pct_power_R":reached,
        "power_80pct_not_attainable_below_max_grid":reached is None,
        "not_actual_DCVC_effect":True,
        "nonconfirmatory_reused_historical_outcomes":True,
        "calendar_correlation_not_modeled_by_randomization":True,
    }


def anatomy(data:Data)->dict[str,Any]:
    state=DCVCState()
    waiting:list[tuple[datetime,str,str,Decimal]]=[]
    capacity:Counter[tuple[str,str]]=Counter()
    reasons:Counter[str]=Counter()
    selected_reasons:Counter[str]=Counter()
    after_reason:Counter[str]=Counter()
    regime_selected:Counter[str]=Counter()
    details=[]
    ordered=sorted(data.features.values(),key=lambda f:(
        f.decision_at,f.symbol,
        data.trades[f.source_opportunity_id].trigger_family,
        f.source_opportunity_id,
    ))
    for f in ordered:
        now=datetime.fromisoformat(f.decision_at)
        while waiting and waiting[0][0]<now:
            _,_,bucket,pnl=heapq.heappop(waiting)
            state.settle(bucket,pnl)
        admitted,reason,estimate=state.admit(f)
        sid=f.source_opportunity_id
        key=slot(data,sid)
        selected=admitted and capacity[key]<MAX_PER_SLOT
        effective=reason if not admitted else "MAX3_CAPACITY" if not selected else reason
        original=data.decisions[sid]
        if (
            selected!=original["selected"] or effective!=original["reason"]
            or state.total!=original["settled_selected_b_before_decision"]
            or (str(estimate) if estimate is not None else None)
            !=original["expected_prior_r"]
        ):
            raise ValueError(f"V01 causal-policy replay mismatch {sid}")
        if selected:
            capacity[key]+=1
            t=data.trades[sid]
            heapq.heappush(waiting,(
                datetime.fromisoformat(t.exit_at),sid,f.regime,
                Decimal(t.realized_gross_r),
            ))
            selected_reasons[reason]+=1
            regime_selected[f.regime]+=1
        reasons[reason]+=1
        after_reason[effective]+=1
        positive=estimate is not None and estimate>Decimal("0.025")
        if selected and reason=="FROZEN_POSTERIOR_EXPECTANCY" and not positive:
            raise ValueError("selected using nonpositive posterior")
        details.append({
            "source_opportunity_id":sid,
            "symbol":f.symbol,"session":f.session,
            "month":f.decision_at[:7],"decision_at":f.decision_at,
            "regime":f.regime,
            "decision_reason_before_capacity":reason,
            "decision_reason_after_capacity":effective,
            "admitted_pre_capacity":admitted,
            "selected_original_v01":selected,
            "estimated_R_available":estimate is not None,
            "positive_estimate_0p025R_at_decision":positive,
            "v01_trades_settled_prior_to_decision":state.total,
            "A_original_member":sid in data.a_ids,
            "NOT_a_future_outcome_ledger":True,
        })
    if len(details)!=SOURCE_N or sum(capacity.values())!=TARGET_N:
        raise ValueError("v0.1 gate2 population drifted")
    cross:dict[str,dict[str,Any]]={}
    # Exclusive effective reason × actual regime × symbol × month.
    for d in details:
        key="|".join((
            d["decision_reason_after_capacity"],d["regime"],d["symbol"],d["month"]
        ))
        if key not in cross:
            cross[key]={"opportunities":0,"A_trades":0,"B_trades":0}
        cross[key]["opportunities"]+=1
        cross[key]["A_trades"]+=int(d["A_original_member"])
        cross[key]["B_trades"]+=int(d["selected_original_v01"])
    b_ids=data.b_ids
    a_ids=data.a_ids
    summaries={}
    for reason in sorted(reasons):
        ids=frozenset(d["source_opportunity_id"] for d in details
                      if d["selected_original_v01"]
                      and d["decision_reason_before_capacity"]==reason)
        summaries[reason]={
            "selected_count":len(ids),
            "selected_winners_original_V49":sum(
                float(data.trades[sid].realized_gross_r)>0 for sid in ids
            ),
            "source_A_selected_overlap":len(ids&a_ids),
            "metrics_assumed_cost_0p025R":outcome(data,ids),
            "metrics_bruto":outcome(data,ids,0.0),
        }
    intersection=a_ids&b_ids
    displaced=a_ids-b_ids
    replacements=b_ids-a_ids
    return {
        "source_n":SOURCE_N,"selected_original_B":len(b_ids),
        "selected_fallback_UNKNOWN":regime_selected["UNKNOWN"],
        "selected_classified":len(b_ids)-regime_selected["UNKNOWN"],
        "attempts_by_pre_capacity_reason":dict(sorted(reasons.items())),
        "effective_reason_all_opportunities":dict(sorted(after_reason.items())),
        "selected_by_reason":dict(sorted(selected_reasons.items())),
        "selected_positive_posterior_only":selected_reasons["FROZEN_POSTERIOR_EXPECTANCY"],
        "selected_not_proven_by_posterior":TARGET_N-selected_reasons["FROZEN_POSTERIOR_EXPECTANCY"],
        "selected_reason_metrics":summaries,
        "cross_reason_regime_symbol_month":cross,
        "A_intersection_B":len(intersection),
        "A_displaced":len(displaced),
        "B_replacements_not_A":len(replacements),
        "cohort_metrics_assumed_cost_0p025R":{
            "A_AND_B":outcome(data,intersection),
            "A_ONLY_NO_REFILL":outcome(data,intersection),
            "A_NOT_B":outcome(data,displaced),
            "B_NOT_A_REFILL":outcome(data,replacements),
        },
        "C_master_frame_invoked":False,
        "ab_v01_modified":False,
        "decision_trace":details,
    }


def run(source:Path,original:Path,output:Path)->dict[str,Any]:
    data=source_data(source,original)
    gate2=anatomy(data)
    global_null=null_distribution(data,"GLOBAL_2876_MAX3",N_GLOBAL,20261011)
    original_a_null=null_distribution(
        data,"A_FIRST3_2020_MAX3",N_GLOBAL,20301011
    )
    margins=null_distribution(
        data,"B_SYMBOL_SESSION_MARGIN_POSTHOC",N_STRATIFIED,20401011
    )
    power=power_diagnostic(data,global_null)
    a_metric=outcome(data,data.a_ids)
    b_metric=outcome(data,data.b_ids)
    a_gross=outcome(data,data.a_ids,0.0)
    b_gross=outcome(data,data.b_ids,0.0)
    if abs(float(a_gross["max_drawdown_R"])-236.1342843563)>0.0001:
        raise ValueError("drawdown baseline changed")
    if abs(float(b_gross["max_drawdown_R"])-19.93243852075)>0.0001:
        raise ValueError("DCVC baseline changed")
    result={
        "identity":IDENTITY,"source_ids_reconciled":SOURCE_N,
        "original_A_trades":len(data.a_ids),
        "frozen_B_trades":len(data.b_ids),
        "A_original_assumed_cost_0p025R":a_metric,
        "B_DCVC_assumed_cost_0p025R":b_metric,
        "A_original_gross":a_gross,"B_DCVC_gross":b_gross,
        "GATE1_primary_no_posthoc_daily_B_counts":global_null,
        "GATE1_A_first3_population_sensitivity":original_a_null,
        "GATE1_posthoc_B_symbol_session_marginal_sensitivity":margins,
        "GATE1_power_diagnostic":power,
        "GATE2_anatomy":{
            k:v for k,v in gate2.items() if k!="decision_trace"
        },
        "exposure_A_B_count_fraction":len(data.b_ids)/len(data.a_ids),
        "exposure_normalized_A_DD_assumed_cost_0p025R_heuristic":(
            float(a_metric["max_drawdown_R"])*len(data.b_ids)/len(data.a_ids)
        ),
        "prior_500x5day_bootstrap_exposure_adjusted_DD_includes_zero":True,
        "is_source_anchored_V49_not_online_regenerated":True,
        "synchronized_physical_bid_ask":False,
        "independent_OOS":False,
        "master_frame_C_executed":False,
        "trade_or_production_authority":False,
        "DCVC_v01_parameters_changed":False,
        "certified":False,
    }
    output.mkdir(parents=True,exist_ok=True)
    decisions=gate2["decision_trace"]
    (output/"dcvc-gate2-exclusive-reasons-asof.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in decisions),
        encoding="utf-8",
    )
    # Dedicated large null result kept separated from readable summary.
    for tag,name in (
        ("GATE1_primary_no_posthoc_daily_B_counts","global_2000"),
        ("GATE1_A_first3_population_sensitivity","original_A_2000"),
        ("GATE1_posthoc_B_symbol_session_marginal_sensitivity","strat_1000"),
    ):
        trials=result[tag].pop("null_distribution")
        (output/f"dcvc-gate1-{name}-null-metrics.jsonl").write_text(
            "".join(json.dumps(x,sort_keys=True)+"\n" for x in trials),
            encoding="utf-8",
        )
    (output/"dcvc-gate1-gate2-scientific-results.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8",
    )
    print("DCVC_GATE1_2",json.dumps({
        "original_A_trades":result["original_A_trades"],
        "frozen_B_trades":result["frozen_B_trades"],
        "gate1_global":result["GATE1_primary_no_posthoc_daily_B_counts"][
            "metrics_assumed_cost_0p025R"
        ],
        "power":power,
        "selected_reasons":gate2["selected_by_reason"],
        "A_intersection_B":gate2["A_intersection_B"],
        "B_replacements_not_A":gate2["B_replacements_not_A"],
        "certified":False,
    },sort_keys=True))
    return result


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("source_nine_markets",type=Path)
    parser.add_argument("original_decisions",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    run(args.source_nine_markets,args.original_decisions,args.output)


if __name__=="__main__":
    main()
