"""Out-of-sample caveat aware paired moving-block bootstrap for DCVC A/B.

POST-EVENT statistics only. Never imported by causal features or selector.
Block lengths are five consecutive observed operating dates across ALL symbols,
so correlations and overlapping daily market shocks remain grouped.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_ab_experiment_v1 import (
    read_jsonl,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _portfolio_select,
)

IDENTITY = "QORE_SCALPER_DCVC_DAY_BLOCK_DEPENDENCE_AUDIT_V01"
COST = Decimal("0.025")
DRAWS = 500
BLOCK_DAYS = 5


def _pf_dd(values: tuple[Decimal, ...]) -> tuple[Decimal | None,Decimal,Decimal]:
    gains=sum((v for v in values if v>0),Decimal(0))
    losses=-sum((v for v in values if v<0),Decimal(0))
    peak=running=maxdd=Decimal(0)
    for value in values:
        running+=value
        peak=max(peak,running)
        maxdd=max(maxdd,peak-running)
    return gains/losses if losses>0 else None,maxdd,(
        sum(values,Decimal(0))/Decimal(len(values)) if values else Decimal(0)
    )


def _percentile(values:list[float],p:float)->float:
    if not values:
        raise ValueError("bootstrap contains no observations")
    ordered=sorted(values)
    return ordered[min(len(ordered)-1,int(p*(len(ordered)-1)))]


def analyze(market_root:Path,experiment_root:Path,output:Path)->dict[str,Any]:
    raw_paths=tuple(sorted(market_root.rglob("dcvc-outcomes-after-settlement.jsonl")))
    decisions_paths=tuple(sorted(experiment_root.rglob("dcvc-decisions-outcome-blind.jsonl")))
    if len(raw_paths)!=9 or len(decisions_paths)!=1:
        raise ValueError("requires exactly nine frozen source ledgers and ABC decisions")
    raw=tuple(row for path in raw_paths for row in read_jsonl(path))
    decisions=tuple(read_jsonl(decisions_paths[0]))
    if len(raw)!=2876 or len(decisions)!=2876:
        raise ValueError("source census changed")
    by_id={row["source_opportunity_id"]:row for row in raw}
    selected={row["source_opportunity_id"] for row in decisions if row["selected"]}
    if len(by_id)!=2876 or len({row["source_opportunity_id"] for row in decisions})!=2876:
        raise ValueError("duplicate or unmatched original IDs")
    all_trades={
        sid:V49EconomicTrade(**{k:v for k,v in row.items()
                                if k!="source_opportunity_id"})
        for sid,row in by_id.items()
    }
    baseline=tuple(t for _,t in _portfolio_select(tuple(all_trades.values())))
    if len(baseline)!=2020 or len(selected)==0:
        raise ValueError("missing frozen V49 control or DCVC intervention")
    b=tuple(all_trades[sid] for sid in selected)
    dates=sorted({t.operating_date for t in (*baseline,*b)})
    if len(dates)<20:
        raise ValueError("not enough observed days for dependence-aware blocks")
    a_days:dict[str,list[V49EconomicTrade]]=defaultdict(list)
    b_days:dict[str,list[V49EconomicTrade]]=defaultdict(list)
    for label,rows in ((a_days,baseline),(b_days,b)):
        for t in rows:
            label[t.operating_date].append(t)
    for group in (a_days,b_days):
        for date in group:
            group[date].sort(key=lambda x:(x.exit_at,x.entry_at,x.symbol))
    def sample(daylist:list[str],group:dict[str,list[V49EconomicTrade]])->tuple[Decimal,...]:
        return tuple(
            Decimal(row.realized_gross_r)-COST
            for date in daylist for row in group.get(date,())
        )
    actual_a=sample(dates,a_days)
    actual_b=sample(dates,b_days)
    pf_a,dd_a,exp_a=_pf_dd(actual_a)
    pf_b,dd_b,exp_b=_pf_dd(actual_b)
    rand=random.Random(20261010)
    diff_pf=[];diff_mean=[];diff_dd=[];delta_dd_equiv=[]
    for _ in range(DRAWS):
        sampled=[]
        while len(sampled)<len(dates):
            anchor=rand.randrange(max(1,len(dates)-BLOCK_DAYS+1))
            sampled.extend(dates[anchor:anchor+BLOCK_DAYS])
        sampled=sampled[:len(dates)]
        path_a=sample(sampled,a_days)
        path_b=sample(sampled,b_days)
        pfa,dda,mean_a=_pf_dd(path_a)
        pfb,ddb,mean_b=_pf_dd(path_b)
        if pfa is not None and pfb is not None:
            diff_pf.append(float(pfb-pfa))
        diff_mean.append(float(mean_b-mean_a))
        diff_dd.append(float(ddb-dda))
        scale=Decimal(len(path_b))/Decimal(len(path_a)) if path_a else Decimal(0)
        delta_dd_equiv.append(float(ddb-dda*scale))
    result={
        "identity":IDENTITY,
        "paired_original_baseline_n":len(baseline),"dcvc_selected_n":len(b),
        "distinct_observed_operating_dates":len(dates),
        "draws":DRAWS,"block_size_observed_days":BLOCK_DAYS,
        "assumed_cost_r":str(COST),
        "observed":{
            "A_PF":str(pf_a) if pf_a is not None else None,
            "B_PF":str(pf_b) if pf_b is not None else None,
            "A_DD_R":str(dd_a),"B_DD_R":str(dd_b),
            "A_expectancy_R":str(exp_a),"B_expectancy_R":str(exp_b),
        },
        "paired_B_minus_A_intervals_95pct":{
            "delta_PF":(_percentile(diff_pf,0.025),_percentile(diff_pf,0.975))
                if diff_pf else None,
            "delta_expectancy_R":(_percentile(diff_mean,0.025),
                                   _percentile(diff_mean,0.975)),
            "delta_DD_R":(_percentile(diff_dd,0.025),_percentile(diff_dd,0.975)),
            "DD_after_matching_A_risk_fraction_R":(
                _percentile(delta_dd_equiv,0.025),
                _percentile(delta_dd_equiv,0.975)
            ),
        },
        "block_dependence_respected":True,
        "bootstrap_used_in_causal_selection":False,
        "historical_pseudotest_already_consumed":True,
        "confirmatory_OOS":False,
        "broker_costs_physically_proven":False,
        "C_full_master_frame_executed":False,
        "certified":False,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"dcvc-conditional-edge-block-bootstrap.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("market_artifacts",type=Path)
    p.add_argument("experiment_artifacts",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    print(json.dumps(analyze(
        args.market_artifacts,args.experiment_artifacts,args.output
    ),sort_keys=True))


if __name__=="__main__":
    main()
