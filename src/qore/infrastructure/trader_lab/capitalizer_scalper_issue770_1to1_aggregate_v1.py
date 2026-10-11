"""Issue770: original V49 A=2020 consolidation and symmetric entry tests.

Statistical outcomes are POST-EVENT ONLY. Placebo holds each timestamp, symbol,
price, absolute 1R bracket and max3. Random direction is not randomized timing,
so the result cannot certify timing skill or author fidelity.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_scalper_issue770_1to1_market_v1 import (
    CENSORED,
    IDENTITY,
    RESOLVED,
    rows,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
)

AGG_IDENTITY="QORE_SCALPER_ISSUE770_NINE_MARKET_1TO1_ENTRY_QUALITY_AUDIT_V1"
COSTS=(Decimal("0"),Decimal("0.025"),Decimal("0.05"),Decimal("0.10"))
PLACEBO_N=2000
BOOT_N=1000
BLOCK_DAYS=5


def _source_trade_key(t:V49EconomicTrade)->tuple[str,str,str,str,str,str]:
    return (
        t.symbol,t.session,t.operating_date,
        t.entry_at,t.trigger_family,t.h1_state_basis,
    )


def cohort_metrics(
    selected:tuple[dict[str,Any],...],
    scenario:str,
    cost:Decimal,
    *,
    target_first:bool=False,
)->dict[str,Any]:
    stats=Counter(x[scenario]["status"] for x in selected)
    resolved=tuple(
        x for x in selected if x[scenario]["status"] in RESOLVED
    )
    outcomes=sorted(
        resolved,key=lambda x:(
            x[scenario]["exit_at"],x["entry_at"],x["symbol"],
        ),
    )
    realized=[
        Decimal(
            x[scenario]["target_first_sensitivity_R"] if target_first
            else x[scenario]["R"]
        )-cost for x in outcomes
    ]
    gains=sum((v for v in realized if v>0),Decimal(0))
    losses=-sum((v for v in realized if v<0),Decimal(0))
    equity=peak=maxdd=Decimal(0)
    curve=[]
    for row,val in zip(outcomes,realized,strict=True):
        equity+=val
        peak=max(peak,equity)
        maxdd=max(maxdd,peak-equity)
        curve.append({
            "source_opportunity_id":row["source_opportunity_id"],
            "entry_at":row["entry_at"],
            "exit_at":row[scenario]["exit_at"],
            "equity_r":str(equity),"drawdown_r":str(peak-equity),
            "realized_after_assumed_cost_R":str(val),
        })
    n=len(realized)
    hits=sum(row[scenario]["status"]=="TARGET" for row in resolved)
    censored=len(selected)-n
    if any(x[scenario]["status"] not in RESOLVED|CENSORED for x in selected):
        raise ValueError("invalid exit/censor in scenario")
    return {
        "source_intents":len(selected),"resolved":n,
        "censored":censored,
        "status_counts":dict(sorted(stats.items())),
        "target_hit_total":hits,"stop_hit_total":stats["STOP"],
        "same_bar_dual_hit_stop_first":sum(
            bool(x[scenario]["both_touched"]) for x in resolved
        ),
        "target_rate_resolved":str(Decimal(hits)/Decimal(n)) if n else None,
        "target_rate_all_lower_bound":str(
            Decimal(hits)/Decimal(len(selected))
        ) if selected else None,
        "target_rate_all_upper_bound_if_censored_target":str(
            Decimal(hits+censored)/Decimal(len(selected))
        ) if selected else None,
        "wins_after_cost":sum(v>0 for v in realized),
        "losses_after_cost":sum(v<0 for v in realized),
        "flats_after_cost":sum(v==0 for v in realized),
        "gross_profit_after_cost_R":str(gains),
        "gross_loss_after_cost_R":str(losses),
        "total_result_after_cost_R":str(equity),
        "expectancy_per_resolved_R":str(equity/Decimal(n)) if n else None,
        "profit_factor_after_cost":str(gains/losses) if losses>0 else None,
        "max_drawdown_resolved_exits_R":str(maxdd) if n else None,
        "max_drawdown_on_actual_deployable_capital":None,
        "cost_per_resolved_trade_assumed_R":str(cost),
        "median_hold_M1_candles_resolved":sorted(
            x[scenario]["m1_bars_held"] for x in resolved
        )[n//2] if n else None,
        "target_first_sensitivity":target_first,
        "capital_overlaps_not_executable_all_at_once":True,
        "_equity_curve":curve,
    }


def stripped(x:dict[str,Any])->dict[str,Any]:
    return {k:v for k,v in x.items() if k!="_equity_curve"}


def _float_perf(rows_selected:tuple[dict[str,Any],...],scenario:str)->float|None:
    metric=cohort_metrics(rows_selected,scenario,Decimal("0.025"))
    raw=metric["expectancy_per_resolved_R"]
    return float(raw) if isinstance(raw,str) else None


def quantile(values:list[float],p:float)->float:
    if not values:
        raise ValueError("empty bootstrap/placebo statistic")
    v=sorted(values)
    return v[min(len(v)-1,round((len(v)-1)*p))]


def paired_placebo(
    original:tuple[dict[str,Any],...],
    scenario:str,
)->dict[str,Any]:
    """"Opposite exact same-time barrier" and random sign, not time placebo."""
    reverse_name=(
        "reverse_direction_same_time_pure" if scenario=="pure_1to1"
        else "reverse_direction_same_time_session_capped"
    )
    observed=cohort_metrics(original,scenario,Decimal("0.025"))
    mirror=tuple(
        {**row,scenario:row[reverse_name]} for row in original
    )
    flipped=cohort_metrics(mirror,scenario,Decimal("0.025"))
    if observed["source_intents"]!=2020 or flipped["source_intents"]!=2020:
        raise ValueError("paired mirror altered 2020 entry instants")
    rng=random.Random(20261011)
    means=[]
    pfs=[]
    dds=[]
    censor=[]
    for _ in range(PLACEBO_N):
        sample=tuple({
            **row,
            scenario:row[reverse_name] if rng.getrandbits(1) else row[scenario],
        } for row in original)
        metric=cohort_metrics(sample,scenario,Decimal("0.025"))
        x=metric["expectancy_per_resolved_R"]
        pf=metric["profit_factor_after_cost"]
        dd=metric["max_drawdown_resolved_exits_R"]
        if not isinstance(x,str) or not isinstance(pf,str) or not isinstance(dd,str):
            raise ValueError("paired placebo cannot calculate performance")
        means.append(float(x))
        pfs.append(float(pf))
        dds.append(float(dd))
        censor.append(int(metric["censored"]))
    value=observed["expectancy_per_resolved_R"]
    if not isinstance(value,str):
        return {
            "status":"NO_RESOLVED_TRADES",
            "replications":PLACEBO_N,"nonconfirmatory":True,
        }
    score=float(value)
    return {
        "replications":PLACEBO_N,
        "paired_timestamp_symbol_stop_distance_and_sample_n":True,
        "randomized_direction_only_not_randomized_entry_time":True,
        "original_direction_assumed_cost_0p025R":stripped(observed),
        "mirror_direction_assumed_cost_0p025R":stripped(flipped),
        "null_expectancy_mean_R":sum(means)/len(means),
        "null_expectancy_2p5_50_97p5_R":(
            quantile(means,0.025),quantile(means,0.5),quantile(means,0.975)
        ),
        "one_sided_expectancy_random_flip_p":(
            (sum(v>=score for v in means)+1)/(PLACEBO_N+1)
        ),
        "null_pf_2p5_50_97p5":(
            quantile(pfs,0.025),quantile(pfs,0.5),quantile(pfs,0.975)
        ),
        "null_drawdown_R_2p5_50_97p5":(
            quantile(dds,0.025),quantile(dds,0.5),quantile(dds,0.975)
        ),
        "random_flip_censored_range":(min(censor),max(censor)),
        "historical_period_previously_consulted":True,
        "independent_OOS":False,
        "time_placebo_completed":False,
    }


def block_bootstrap(
    selected:tuple[dict[str,Any],...],scenario:str,
)->dict[str,Any]:
    by_date:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for row in selected:
        by_date[row["operating_date"]].append(row)
    dates=sorted(by_date)
    if len(dates)<BLOCK_DAYS:
        raise ValueError("too few days for a five-operating-day paired resample")
    rng=random.Random(20267011)
    values=[]
    for _ in range(BOOT_N):
        sampled_dates=[]
        while len(sampled_dates)<len(dates):
            i=rng.randrange(0,len(dates)-BLOCK_DAYS+1)
            sampled_dates.extend(dates[i:i+BLOCK_DAYS])
        synthetic=tuple(
            row for day in sampled_dates[:len(dates)] for row in by_date[day]
        )
        x=_float_perf(synthetic,scenario)
        if x is not None:
            values.append(x)
    return {
        "replications":BOOT_N,"block_size_observed_operating_days":BLOCK_DAYS,
        "distinct_operating_dates":len(dates),
        "expectancy_R_cost_0p025_interval_95pct":(
            quantile(values,0.025),quantile(values,0.975)
        ),
        "simultaneous_markets_kept_within_day":True,
        "reused_historical_days_not_OOS":True,
        "no_censored_returns_imputed":True,
    }


def market_counts(selected:tuple[dict[str,Any],...],scenario:str)->dict[str,Any]:
    return {
        symbol:stripped(cohort_metrics(
            tuple(row for row in selected if row["symbol"]==symbol),
            scenario,Decimal("0.025")
        ))
        for symbol in sorted({x["symbol"] for x in selected})
    }


def main_aggregate(input_root:Path,output:Path)->dict[str,Any]:
    market_reports=tuple(sorted(input_root.rglob("scalper-issue770-market.json")))
    market_ledger=tuple(sorted(input_root.rglob(
        "scalper-issue770-all-original-ids-two-scenarios.jsonl"
    )))
    if len(market_reports)!=9 or len(market_ledger)!=9:
        raise ValueError("requires all nine native frozen market jobs")
    manifests=tuple(json.loads(p.read_text(encoding="utf-8")) for p in market_reports)
    if (len({p["symbol"] for p in manifests})!=9
            or any(p["identity"]!=IDENTITY for p in manifests)):
        raise ValueError("duplicate or different native input markets")
    all_rows=tuple(x for p in market_ledger for x in rows(p))
    if len(all_rows)!=2876 or len({x["source_opportunity_id"] for x in all_rows})!=2876:
        raise ValueError("2876 original source identities required")
    if any(not x["original_v49_reconstructed_unchanged"] for x in all_rows):
        raise ValueError("baseline V49 original drifted")
    by_trade={_source_trade_key(V49EconomicTrade(**x["original_v49"])):x for x in all_rows}
    if len(by_trade)!=2876:
        raise ValueError("duplicated source economic identity")
    original=tuple(V49EconomicTrade(**x["original_v49"]) for x in all_rows)
    original_selected=tuple(t for _,t in _portfolio_select(original))
    selected=tuple(by_trade[_source_trade_key(t)] for t in original_selected)
    baseline=_metrics(original_selected)
    if (len(selected)!=2020 or baseline.wins!=1167
        or abs(Decimal(baseline.total_r)-Decimal("-233.2693270763665099166092077"))
            >Decimal("0.000000001")
        or abs(Decimal(baseline.max_drawdown_r)-Decimal("236.1342843563"))
            >Decimal("0.000001")
        or abs(Decimal(baseline.profit_factor or "0")-
               Decimal("0.6644630742216"))>Decimal("0.0000001")):
        raise ValueError("V49 original 2020 1167 economics and DD not reproduced")
    source_exit=Counter(x.exit_reason for x in original_selected)
    source_flat=sum(Decimal(x.realized_gross_r)==0 for x in original_selected)
    source_dual=sum(x.same_bar_stop_target_ambiguity for x in original_selected)
    output.mkdir(parents=True,exist_ok=True)
    with (output/"scalper-issue770-original-A-2020-two-1to1-scenarios.jsonl").open(
        "w",encoding="utf-8"
    ) as f:
        for row in selected:
            f.write(json.dumps(row,sort_keys=True)+"\n")
    result:dict[str,Any]={
        "identity":AGG_IDENTITY,"source_ids_conserved":len(all_rows),
        "original_A_2020":len(selected),"nine_markets":len(manifests),
        "baseline_reconstructed_exact":True,
        "original_exit_counts":dict(sorted(source_exit.items())),
        "original_flat_count":source_flat,
        "original_same_bar_stop_target_ambiguity":source_dual,
        "baseline_A_gross_metrics":asdict(baseline),
        "origin_win_average_R":str(
            Decimal(baseline.gross_profit_r)/Decimal(baseline.wins)
        ),
        "origin_loss_average_R_if_only_losses":str(
            Decimal(baseline.gross_loss_r)/Decimal(baseline.losses)
        ),
        "number_native_post_entry_bars_provider_per_symbol":{
            x["symbol"]:x["native_M1_bars_since_development"] for x in manifests
        },
        "provider_m1_last_close_per_symbol":{
            x["symbol"]:x["native_m1_last_close"] for x in manifests
        },
        "censoring_observable_not_dropped":True,
        "new_parent_H1_M15_universe_generated":False,
        "underlying_M15_stop_author_certified":False,
        "historical_OOS_independent":False,
        "physical_bid_ask_costs":False,
        "production_VPS_touched":False,"certified":False,
    }
    for scenario in ("pure_1to1","session_capped_1to1"):
        data={
            str(cost):stripped(cohort_metrics(selected,scenario,cost))
            for cost in COSTS
        }
        name=scenario.upper()
        result[name]={
            "cost_stress":data,
            "target_first_sensitivity_assumed_cost_0p025R":stripped(
                cohort_metrics(selected,scenario,Decimal("0.025"),target_first=True)
            ),
            "by_market_cost_0p025R":market_counts(selected,scenario),
            "direction_mirror_and_2000_random_flips":paired_placebo(
                selected,scenario
            ),
            "1000x5day_block_bootstrap":block_bootstrap(selected,scenario),
            "overlapping_positions_not_risk_sized":True,
            "censoring_means_no_2020_unconditional_WR":True,
        }
        for cost in COSTS:
            curve=cohort_metrics(selected,scenario,cost)["_equity_curve"]
            path=output/f"scalper-issue770-{scenario}-equity-cost{str(cost).replace('.','p')}.jsonl"
            path.write_text(
                "".join(json.dumps(x,sort_keys=True)+"\n" for x in curve),
                encoding="utf-8",
            )
    (output/"scalper-issue770-scientific-nine-market.json").write_text(
        json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    print("SCALPER_ISSUE770",json.dumps({
        "sources":result["source_ids_conserved"],
        "selected":result["original_A_2020"],
        "original_exit_counts":result["original_exit_counts"],
        "flat":result["original_flat_count"],
        "pure":result["PURE_1TO1"]["cost_stress"]["0.025"],
        "session":result["SESSION_CAPPED_1TO1"]["cost_stress"]["0.025"],
        "pure_sign_flip_p":result["PURE_1TO1"][
            "direction_mirror_and_2000_random_flips"
        ]["one_sided_expectancy_random_flip_p"],
        "session_sign_flip_p":result["SESSION_CAPPED_1TO1"][
            "direction_mirror_and_2000_random_flips"
        ]["one_sided_expectancy_random_flip_p"],
    },sort_keys=True))
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("nine_market_root",type=Path)
    p.add_argument("report_output",type=Path)
    args=p.parse_args()
    main_aggregate(args.nine_market_root,args.report_output)


if __name__=="__main__":
    main()
