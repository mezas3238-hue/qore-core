"""DCVC Audit02 P0: frozen decisions, MAX3 replacement, learning lockout.

A/B v0.1 are not rerun or retuned. Their source identities, causal
decisions, and economics must reproduce exactly before forensic joins.
Shadow economics uses hypothetical source-V49 M1 fills AFTER exit_at and is
strictly segregated from live-selected observations and v0.1 admission.
"""
from __future__ import annotations

import argparse
import heapq
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_ab_experiment_v1 import (
    DCVCState,
    read_jsonl,
    summarize,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_dcvc_causal_features_v1 import (
    DCVCPredecision,
)
from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
    _metrics,
    _portfolio_select,
)

IDENTITY="QORE_SCALPER_DCVC_AUDIT02_FROZEN_POLICY_SELECTION_FORENSICS_V1"
COST=Decimal("0.025")


def key(trade:V49EconomicTrade)->tuple[str,str,str,str,str,str]:
    return (
        trade.symbol,trade.session,trade.operating_date,
        trade.entry_at,trade.trigger_family,trade.h1_state_basis,
    )


def metric(rows:tuple[V49EconomicTrade,...])->dict[str,Any]:
    if not rows:
        return {"n":0,"pf_gross":None,"gross_R":None,"DD_R":None,
                "net_pf_assumed_0p025R":None,"net_expectancy_assumed_0p025R":None}
    gross=summarize(rows)
    stress=summarize(rows,COST)
    return {
        "n":len(rows),
        "wins":gross["wins"],
        "pf_gross":gross["profit_factor_after_assumed_cost"],
        "gross_R":gross["total_r_after_assumed_cost"],
        "DD_R":gross["max_dd_r"],
        "net_pf_assumed_0p025R":stress["profit_factor_after_assumed_cost"],
        "net_expectancy_assumed_0p025R":stress["net_expectancy_r"],
    }


def aggregate(source_root:Path,audit_root:Path,prior_root:Path,output:Path)->dict[str,Any]:
    def nine(pattern:str,where:Path)->tuple[Path,...]:
        paths=tuple(sorted(where.rglob(pattern)))
        if len(paths)!=9:
            raise ValueError(f"require exact nine previously published ledgers: {pattern}")
        return paths

    features=tuple(
        DCVCPredecision(**row)
        for p in nine("dcvc-predecision.jsonl",source_root)
        for row in read_jsonl(p)
    )
    labels=tuple(
        row for p in nine("dcvc-outcomes-after-settlement.jsonl",source_root)
        for row in read_jsonl(p)
    )
    witness=tuple(
        row for p in nine("dcvc-audit02-unknown-native-reasons.jsonl",audit_root)
        for row in read_jsonl(p)
    )
    decisions_files=tuple(prior_root.rglob("dcvc-decisions-outcome-blind.jsonl"))
    if len(decisions_files)!=1:
        raise ValueError("one immutable v0.1 decision ledger mandatory")
    decisions=tuple(read_jsonl(decisions_files[0]))
    if not all(len(x)==2876 for x in (features,labels,witness,decisions)):
        raise ValueError("original V49 2876 identities not fully reconciled")

    fmap={f.source_opportunity_id:f for f in features}
    lmap={x["source_opportunity_id"]:x for x in labels}
    wmap={x["source_opportunity_id"]:x for x in witness}
    dmap={x["source_opportunity_id"]:x for x in decisions}
    if any(len(x)!=2876 for x in (fmap,lmap,wmap,dmap)):
        raise ValueError("duplicated frozen identity")
    if not (set(fmap)==set(lmap)==set(wmap)==set(dmap)):
        raise ValueError("native witness, classifier and outcome ID sets differ")
    trades={
        sid:V49EconomicTrade(**{k:v for k,v in row.items()
                                if k!="source_opportunity_id"})
        for sid,row in lmap.items()
    }
    tkeys={key(t):sid for sid,t in trades.items()}
    if len(tkeys)!=2876:
        raise ValueError("economic keys not unique")
    baseline=tuple(t for _,t in _portfolio_select(tuple(trades.values())))
    baseline_ids={tkeys[key(t)] for t in baseline}
    if len(baseline)!=2020 or _metrics(baseline).wins!=1167:
        raise ValueError("immutable A baseline failed")
    if abs(Decimal(_metrics(baseline).max_drawdown_r)-Decimal("236.1342843563"))>Decimal("0.00001"):
        raise ValueError("immutable A drawdown changed")
    actual_B_ids={sid for sid,d in dmap.items() if d["selected"]}
    if len(actual_B_ids)!=266:
        raise ValueError("B actual version1 changed")
    if sum(f.regime=="UNKNOWN" for f in features)!=184:
        raise ValueError("UNKNOWN source population must be independently identical")
    if sum(fmap[sid].regime=="UNKNOWN" for sid in actual_B_ids)!=181:
        raise ValueError("UNKNOWN selected population must be independently identical")

    # A second chronologically sorted audit of the exact same V01 decisions:
    # no outcomes enter admit(), only settled SELECTED_B outcomes update state.
    state=DCVCState()
    shadow=DCVCState()
    pending_b:list[tuple[datetime,str,str,Decimal]]=[]
    pending_shadow:list[tuple[datetime,str,str,Decimal]]=[]
    capacity:Counter[tuple[str,str]]=Counter()
    ordered=tuple(sorted(features,key=lambda f:(
        f.decision_at,f.symbol,trades[f.source_opportunity_id].trigger_family,
        f.source_opportunity_id,
    )))
    pre_rows:list[dict[str,Any]]=[]
    econ_rows:list[dict[str,Any]]=[]
    reasons:Counter[str]=Counter()
    attempts:Counter[str]=Counter()
    chosen_by_reason:Counter[str]=Counter()
    posterior_rejections:Counter[str]=Counter()
    post_first_lockout:Counter[str]=Counter()
    shadow_late_counterfactual=0
    for f in ordered:
        sid=f.source_opportunity_id
        at=datetime.fromisoformat(f.decision_at)
        while pending_b and pending_b[0][0]<at:
            _,_,regime,result=heapq.heappop(pending_b)
            state.settle(regime,result)
        while pending_shadow and pending_shadow[0][0]<at:
            _,_,regime,result=heapq.heappop(pending_shadow)
            shadow.settle(regime,result)
            shadow_late_counterfactual+=1

        allowed,reason,posterior=state.admit(f)
        shadow_allowed,shadow_reason,shadow_posterior=shadow.admit(f)
        slot=(f.session,f.operating_date)
        has_capacity=capacity[slot]<3
        chosen=allowed and has_capacity
        original=dmap[sid]
        expected_reason=reason if not allowed else (
            "MAX3_CAPACITY" if not has_capacity else reason
        )
        if original["selected"]!=chosen or original["reason"]!=expected_reason:
            raise ValueError(f"v0.1 decision disagreement at {sid}")
        if int(original["settled_selected_b_before_decision"])!=state.total:
            raise ValueError("retrospective settling or same-timestamp leakage")
        recorded=original["expected_prior_r"]
        if recorded!=(str(posterior) if posterior is not None else None):
            raise ValueError("immutable v0.1 posterior diverges")
        if wmap[sid]["decision_at"]!=f.decision_at or wmap[sid]["regime"]!=f.regime:
            raise ValueError("native as-of diagnostic unpaired")
        if wmap[sid]["native_candles_after_decision_used"]!=0:
            raise ValueError("future native candle leak")
        if not allowed and reason=="FROZEN_POSTERIOR_EXPECTANCY":
            posterior_rejections[f.regime]+=1
            post_first_lockout[f.regime]+=1
        if chosen:
            capacity[slot]+=1
            heapq.heappush(pending_b,(
                datetime.fromisoformat(trades[sid].exit_at),sid,f.regime,
                Decimal(trades[sid].realized_gross_r),
            ))
        # HISTORICAL counterfactual fills are observed AFTER exit only in
        # a research-only shadow cohort. They NEVER feed V01 state/admit.
        heapq.heappush(pending_shadow,(
            datetime.fromisoformat(trades[sid].exit_at),sid,f.regime,
            Decimal(trades[sid].realized_gross_r),
        ))
        attempts[reason]+=1
        reasons[expected_reason]+=1
        if chosen:
            chosen_by_reason[reason]+=1
        cohort=(
            "A_AND_B" if sid in baseline_ids and chosen
            else "A_ONLY" if sid in baseline_ids
            else "B_ONLY" if chosen else "NEITHER"
        )
        pre_rows.append({
            "source_opportunity_id":sid,"symbol":f.symbol,
            "decision_at":f.decision_at,
            "operating_date":f.operating_date,
            "regime":f.regime,"diagnosis":wmap[sid]["diagnosis"],
            "v01_reason_before_capacity":reason,
            "v01_reason_recorded":expected_reason,
            "v01_prior_estimate_R":str(posterior) if posterior is not None else None,
            "v01_admitted_before_capacity":allowed,
            "max3_has_capacity":has_capacity,
            "A_original_selected":sid in baseline_ids,
            "B_v01_selected":chosen,
            "cohort":cohort,
            "selected_B_settled_available_before":state.total,
            "shadow_all_source_settled_before":shadow.total,
            "shadow_would_admit_counterfactual":shadow_allowed,
            "shadow_reason_counterfactual":shadow_reason,
            "shadow_estimate_R_counterfactual":(
                str(shadow_posterior) if shadow_posterior is not None else None
            ),
            "counterfactual_not_deployment_authority":True,
            "no_future_outcomes_in_admission":True,
        })
        econ_rows.append({
            "source_opportunity_id":sid,
            "symbol":f.symbol,
            "decision_at":f.decision_at,
            "historical_exit_at":trades[sid].exit_at,
            "realized_original_V49_gross_R":trades[sid].realized_gross_r,
            "cohort":cohort,
            "regime":f.regime,
            "v01_reason_before_capacity":reason,
            "hypothetical_if_not_executed_B":not chosen,
            "available_as_of_decision":False,
        })
    if len(pre_rows)!=2876 or sum(capacity.values())!=266:
        raise ValueError("B source/capacity totals drifted")
    def m(ids:set[str])->dict[str,Any]:
        return metric(tuple(trades[sid] for sid in ids))
    intersection=baseline_ids&actual_B_ids
    only_a=baseline_ids-actual_B_ids
    only_b=actual_B_ids-baseline_ids
    original_winners={
        sid for sid in baseline_ids if Decimal(trades[sid].realized_gross_r)>0
    }
    if len(intersection&original_winners)!=170:
        raise ValueError("frozen A winning overlap changed")
    cohort_metrics={
        "A_original":m(baseline_ids),
        "B_with_refill_v01":m(actual_B_ids),
        "A_intersect_B":m(intersection),
        "A_not_B":m(only_a),
        "B_replacements_not_in_A":m(only_b),
        "A_only_frozen_B_decision_mask_NO_REFILL":m(intersection),
    }
    # A-only mask uses a B-path classifier, not a separately trained A-policy.
    by_reason={}
    for reason in sorted(attempts):
        ids=[row["source_opportunity_id"] for row in pre_rows
             if row["v01_reason_before_capacity"]==reason]
        chosen_ids={sid for sid in ids if sid in actual_B_ids}
        by_reason[reason]={
            "opportunities":len(ids),
            "A_source_selected":sum(sid in baseline_ids for sid in ids),
            "B_selected":len(chosen_ids),
            "B_selected_metrics":m(chosen_ids),
            "B_refill_not_A":len(chosen_ids-baseline_ids),
        }
    unknown_reasons=Counter(
        row["diagnosis"] for row in pre_rows if row["regime"]=="UNKNOWN"
    )
    # Compact multi-dimensional pivot, with post-settlement outcomes only.
    pivots={}
    for field in ("symbol","regime","operating_month","v01_reason_before_capacity"):
        table={}
        tags={
            x["source_opportunity_id"]:(
                x["decision_at"][:7] if field=="operating_month" else x[field]
            )
            for x in pre_rows
        }
        for val in sorted(set(tags.values())):
            ids={sid for sid,tag in tags.items() if tag==val}
            table[val]={
                "opportunities":len(ids),
                "A_trades":len(ids&baseline_ids),
                "B_trades":len(ids&actual_B_ids),
                "B_replacements":len(ids&only_b),
                "B_metrics":m(ids&actual_B_ids),
            }
        pivots[field]=table
    result={
        "identity":IDENTITY,
        "source_ids_reconciled":len(features),
        "baseline_A":cohort_metrics["A_original"],
        "original_A_winners":len(original_winners),
        "original_A_winners_retained":len(intersection&original_winners),
        "original_A_winners_retained_share":str(
            Decimal(len(intersection&original_winners))/Decimal(len(original_winners))
        ),
        "B":cohort_metrics["B_with_refill_v01"],
        "cohort_decomposition":cohort_metrics,
        "A_intersection_B_ids":len(intersection),
        "B_replacements_outside_A":len(only_b),
        "A_original_displaced":len(only_a),
        "unknown_source_total":184,
        "unknown_B_accepted":181,
        "unknown_root_causes_asof":dict(sorted(unknown_reasons.items())),
        "v01_classifier_decisions_reconstructed_exact":True,
        "max3_all_v01_sessions_reconciled":True,
        "v01_attempted_reason_counts_before_capacity":dict(sorted(attempts.items())),
        "v01_recorded_reason_counts_after_capacity":dict(sorted(reasons.items())),
        "v01_selected_reason_counts":dict(sorted(chosen_by_reason.items())),
        "frozen_posterior_rejection_counts_by_regime":dict(sorted(posterior_rejections.items())),
        "shadow_hypothetical_full_source_prior_only_settlements":shadow_late_counterfactual,
        "shadow_uses_rejected_fills_for_admission":False,
        "by_reason":by_reason,
        "pivots":pivots,
        "broker_bid_ask_present":False,
        "master_frame_C_executed":False,
        "independent_OOS":False,
        "experiment_v01_changed":False,
        "certified":False,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"dcvc-audit02-aggregate.json").write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    for filename,rows in (
        ("dcvc-audit02-decision-observability-asof.jsonl",pre_rows),
        ("dcvc-audit02-OUTCOME_ONLY-historical-shadow.jsonl",econ_rows),
    ):
        (output/filename).write_text(
            "".join(json.dumps(x,sort_keys=True)+"\n" for x in rows),
            encoding="utf-8",
        )
    return result


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    parser.add_argument("native_witness",type=Path)
    parser.add_argument("original_v01_decisions",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    result=aggregate(
        args.source,args.native_witness,args.original_v01_decisions,args.output
    )
    summary={
        k:result[k] for k in (
            "source_ids_reconciled","A_intersection_B_ids",
            "B_replacements_outside_A","unknown_root_causes_asof",
            "v01_selected_reason_counts","frozen_posterior_rejection_counts_by_regime",
            "B",
        )
    }
    print("DCVC_AUDIT02",json.dumps(summary,sort_keys=True))


if __name__=="__main__":
    main()
