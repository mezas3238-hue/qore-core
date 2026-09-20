"""Sequence-regeneration root-cause forensics for VT31_NAS100.

Diagnostic only. No risk multiplier, filter, target, stop, entry, lifecycle,
rearm or Silver Bullet rule is changed.

Question:
After two or more already-closed losing trades, why does a new Order Block
authorization remain structurally weak? This lab tests whether the weakness is
explained by lack of causal market-state regeneration between the previous
closed trade and the current authorization.

Only information known before the current trade outcome is used:
- prior closed outcomes / prior loss streak;
- prior trade causal state;
- current decision-time causal state;
- elapsed time between prior signal and current signal.

Current terminal PnL is attached only after grouping for research metrics.
Calendar/fold identity is never a runtime feature. H4/H1 are excluded.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA="qore.vt31.nas100.sequence_regeneration_root_cause_forensics.v1"
MIN_STABLE_SAMPLE=5

STATE_FIELDS=(
    "entry_family",
    "side",
    "reference_volatility_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
)

MARKET_RESET_FIELDS=(
    "reference_volatility_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
)


def _d(value: object)->Decimal:
    return Decimal(str(value))


def _dt(value: object)->datetime:
    return datetime.fromisoformat(str(value).replace("Z","+00:00"))


def _change_bucket(value:int)->str:
    if value <= 1:
        return "0_1"
    if value <= 3:
        return "2_3"
    if value <= 5:
        return "4_5"
    return "6_7"


def _elapsed_bucket(hours:Decimal)->str:
    if hours <= Decimal("24"):
        return "le_24h"
    if hours <= Decimal("72"):
        return "24_72h"
    if hours <= Decimal("168"):
        return "3_7d"
    return "gt_7d"


def _metrics(rows:list[dict[str,object]])->dict[str,object]:
    return residual._metrics(rows)


def _state_metrics(rows:list[dict[str,object]])->dict[str,object]:
    losses=[r for r in rows if _d(r["capital_weighted_net_r"]) < 0]
    return {
        "sample":len(rows),
        "metrics":_metrics(rows),
        "loss_rate":(
            "0" if not rows
            else format(Decimal(len(losses))/Decimal(len(rows)),"f")
        ),
        "loss_path_counts":dict(sorted(
            {
                key:sum(1 for r in losses if str(r.get("loss_path_class"))==key)
                for key in {str(r.get("loss_path_class")) for r in losses}
            }.items()
        )),
    }


def _annotate(rows:list[dict[str,object]])->list[dict[str,object]]:
    ordered=sorted(rows,key=lambda r:cast(str,r["signal_at"]))
    out:list[dict[str,object]]=[]
    streak=0
    history:list[dict[str,object]]=[]
    for row in ordered:
        u=dict(row)
        u["pre_loss_streak"]=streak
        u["pre_loss_ge_2"]=streak>=2
        u["pre_loss_ge_3"]=streak>=3

        if history:
            prev=history[-1]
            changes=0
            for field in STATE_FIELDS:
                same=prev.get(field)==u.get(field)
                u[f"prev_{field}_relation"]="same" if same else "changed"
            for field in MARKET_RESET_FIELDS:
                if prev.get(field)!=u.get(field):
                    changes += 1
            u["market_state_change_count"]=changes
            u["market_state_change_bucket"]=_change_bucket(changes)
            elapsed=Decimal(str((_dt(u["signal_at"])-_dt(prev["signal_at"])).total_seconds()))/Decimal("3600")
            u["elapsed_since_prev_trade_hours"]=format(elapsed,"f")
            u["elapsed_since_prev_trade_bucket"]=_elapsed_bucket(elapsed)
            u["previous_loss_path_class"]=prev.get("loss_path_class")
            u["previous_entry_family"]=prev.get("entry_family")
            u["previous_side"]=prev.get("side")
        else:
            for field in STATE_FIELDS:
                u[f"prev_{field}_relation"]="none"
            u["market_state_change_count"]=0
            u["market_state_change_bucket"]="none"
            u["elapsed_since_prev_trade_hours"]=None
            u["elapsed_since_prev_trade_bucket"]="none"
            u["previous_loss_path_class"]=None
            u["previous_entry_family"]=None
            u["previous_side"]=None

        if len(history)>=2:
            last2=history[-2:]
            u["prior2_family_pattern"]=">".join(str(x.get("entry_family")) for x in last2)
            u["prior2_side_pattern"]=">".join(str(x.get("side")) for x in last2)
            u["prior2_loss_path_pattern"]=">".join(str(x.get("loss_path_class")) for x in last2)
        else:
            u["prior2_family_pattern"]="insufficient"
            u["prior2_side_pattern"]="insufficient"
            u["prior2_loss_path_pattern"]="insufficient"

        out.append(u)
        history.append(u)
        if _d(row["capital_weighted_net_r"]) < 0:
            streak += 1
        else:
            streak=0
    return out


def _groups(rows:list[dict[str,object]], field:str)->dict[str,object]:
    grouped:dict[str,list[dict[str,object]]]=defaultdict(list)
    for row in rows:
        grouped[str(row.get(field))].append(row)
    return {k:_state_metrics(v) for k,v in sorted(grouped.items())}


def replay(path:Path, *, partition:str)->dict[str,object]:
    rows,evidence,diagnostics,stats=alt._current_rows(path)
    a=_annotate(rows)
    post2=[r for r in a if bool(r["pre_loss_ge_2"])]
    post2_ob=[r for r in post2 if r.get("entry_family")=="order-block"]
    post3_ob=[r for r in a if bool(r["pre_loss_ge_3"]) and r.get("entry_family")=="order-block"]

    fields=(
        "market_state_change_bucket",
        "elapsed_since_prev_trade_bucket",
        "prev_side_relation",
        "prev_entry_family_relation",
        "prev_reference_volatility_state_relation",
        "prev_prior_day_state_relation",
        "prev_premarket_state_relation",
        "prev_cash_open_state_relation",
        "prev_last_structure_event_family_relation",
        "prev_current_path_bucket_relation",
        "prev_risk_ref_bucket_relation",
        "prev_reclaim_age_bucket_relation",
        "prev_confirmation_latency_bucket_relation",
        "previous_entry_family",
        "previous_side",
        "previous_loss_path_class",
        "prior2_family_pattern",
        "prior2_side_pattern",
        "prior2_loss_path_pattern",
        "tier",
        "side",
        "reference_volatility_state",
        "premarket_state",
        "cash_open_state",
        "last_structure_event_family",
        "current_path_bucket",
        "risk_ref_bucket",
        "reclaim_age_bucket",
        "confirmation_latency_bucket",
    )

    return {
        "schema":SCHEMA,
        "partition":partition,
        "trade_count":len(a),
        "overall_metrics":_metrics(a),
        "post_loss_ge2":{
            "sample":len(post2),
            "metrics":_metrics(post2),
        },
        "post_loss_ge2_order_block":{
            "sample":len(post2_ob),
            "metrics":_metrics(post2_ob),
            "dimensions":{f:_groups(post2_ob,f) for f in fields},
        },
        "post_loss_ge3_order_block":{
            "sample":len(post3_ob),
            "metrics":_metrics(post3_ob),
        },
        "source_stats":stats,
        "diagnostics":diagnostics,
        "evidence":evidence,
        "governance":{
            "consumed_evidence_only":True,
            "diagnostic_only":True,
            "prior_outcomes_closed_before_current_decision":True,
            "current_terminal_pnl_used_for_group_definition":False,
            "market_state_transition_uses_decision_time_features_only":True,
            "h4_h1_excluded":True,
            "calendar_date_runtime_forbidden":True,
            "fold_identity_runtime_forbidden":True,
            "trade_policy_changed":False,
            "risk_policy_changed":False,
            "silver_bullet_changed":False,
            "opens_new_holdout":False,
            "policy_promoted":False,
            "candidate_certified":False,
            "live_authorized":False,
            "production_authorized":False,
        },
    }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("evidence",type=Path)
    p.add_argument("--partition",required=True)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    payload=replay(a.evidence,partition=a.partition)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "partition":payload["partition"],
        "post_loss_ge2":payload["post_loss_ge2"],
        "post_loss_ge2_order_block":{
            "sample":payload["post_loss_ge2_order_block"]["sample"],
            "metrics":payload["post_loss_ge2_order_block"]["metrics"],
        },
        "post_loss_ge3_order_block":payload["post_loss_ge3_order_block"],
    },sort_keys=True))


if __name__=="__main__":
    main()
