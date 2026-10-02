"""Shared Perception Intelligence V6 on VT31 NAS100.

This laboratory deliberately stops using historical analog outcomes as the
primary eyes of Shared. It reconstructs an immutable as-of-signal market
snapshot from M1 evidence and asks whether current-state perception itself can
separate adverse from favorable opportunities.

R8 = discovery of perception-state statistics.
R6 = calibration/freeze.
R5 = untouched evaluation.

No journey management, capital weighting, current-trade outcome feature,
post-signal candle, Shared order authority, or R5 retune.
"""
# ruff: noqa: E501,E701,E702,E741,E701,E702,E741
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_integrated_shared_intelligence_v1 as integrated

SCHEMA = "qore.core_stack_v3.vt31.perception_intelligence.v6"
IDENTITY = "VT31_NAS100_SHARED_PERCEPTION_INTELLIGENCE_V6"


@dataclass(frozen=True, slots=True)
class Policy:
    shrinkage: int
    threshold: Decimal
    minimum_groups: int
    profile: str

    def payload(self) -> dict[str, object]:
        return {
            "shrinkage": self.shrinkage,
            "threshold": format(self.threshold, "f"),
            "minimum_groups": self.minimum_groups,
            "profile": self.profile,
        }


POLICIES = tuple(
    Policy(shrinkage, threshold, groups, profile)
    for shrinkage in (8, 16, 32)
    for threshold in (
        Decimal("-0.15"),
        Decimal("-0.10"),
        Decimal("-0.05"),
        Decimal("0"),
        Decimal("0.05"),
    )
    for groups in (3, 5, 7)
    for profile in ("STATE", "STATE_PLUS_GEOMETRY")
)


def _bucket(value: Decimal, cuts: tuple[Decimal, ...]) -> str:
    for i, cut in enumerate(cuts):
        if value < cut:
            return f"b{i}"
    return f"b{len(cuts)}"


def _prefix(day_bars: tuple[object, ...], signal_at: object) -> list[object]:
    signal = v3._dt(signal_at)
    bars = [
        bar for bar in day_bars
        if cast(object, bar).closed_at <= signal
    ]
    if not bars:
        raise AssertionError("empty as-of prefix")
    if any(cast(object, bar).closed_at > signal for bar in bars):
        raise AssertionError("future bar leaked into perception")
    return bars


def _window_state(bars: list[object], n: int) -> dict[str, Decimal]:
    recent = bars[-n:]
    if len(recent) < 3:
        return {
            "efficiency": Decimal(0),
            "overlap": Decimal(1),
            "body_fraction": Decimal(0),
            "range_ratio": Decimal(1),
            "wick_fraction": Decimal(0),
        }
    vals = [integrated._bar_values(bar) for bar in recent]
    closes = [x[3] for x in vals]
    travel = sum(
        (abs(b-a) for a,b in zip(closes, closes[1:], strict=False)),
        Decimal(0),
    )
    net = abs(closes[-1]-closes[0])
    efficiency = Decimal(0) if travel == 0 else net/travel
    overlaps: list[Decimal] = []
    bodies: list[Decimal] = []
    wicks: list[Decimal] = []
    ranges: list[Decimal] = []
    for o,h,l,c in vals:
        r=max(h-l, Decimal("0.0000001"))
        ranges.append(r)
        body=abs(c-o)
        bodies.append(body/r)
        wicks.append((r-body)/r)
    for left,right in zip(vals, vals[1:], strict=False):
        _,lh,ll,_=left
        _,rh,rl,_=right
        ov=max(Decimal(0), min(lh,rh)-max(ll,rl))
        den=min(lh-ll,rh-rl)
        overlaps.append(Decimal(0) if den<=0 else min(Decimal(1),ov/den))
    short=sum(ranges[-min(5,len(ranges)):],Decimal(0))/Decimal(min(5,len(ranges)))
    long=sum(ranges,Decimal(0))/Decimal(len(ranges))
    return {
        "efficiency": efficiency,
        "overlap": sum(overlaps,Decimal(0))/Decimal(len(overlaps)),
        "body_fraction": sum(bodies,Decimal(0))/Decimal(len(bodies)),
        "range_ratio": Decimal(1) if long==0 else short/long,
        "wick_fraction": sum(wicks,Decimal(0))/Decimal(len(wicks)),
    }


def _perceive(
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
) -> dict[str, object]:
    bars=_prefix(day_bars,row["signal_at"])
    s5=_window_state(bars,5)
    s15=_window_state(bars,15)
    s30=_window_state(bars,30)
    last=integrated._bar_values(bars[-1])
    prev=integrated._bar_values(bars[-2])
    o,h,l,c=last
    po,ph,pl,pc=prev
    side=str(row["side"])
    sign=Decimal(1) if side=="long" else Decimal(-1)
    risk=cast(object,setup).initial_risk
    entry=cast(object,setup).entry_price
    ref=cast(object,setup).source_setup.reference
    ref_width=max(ref.high-ref.low,Decimal("0.0000001"))
    body_signed=sign*(c-o)/risk
    close_from_entry=sign*(c-entry)/risk
    displacement=abs(c-o)/max(h-l,Decimal("0.0000001"))
    range_expansion=(h-l)/max(ph-pl,Decimal("0.0000001"))
    location=(c-ref.low)/ref_width
    direction="WITH_SIDE" if sign*(c-pc)>0 else "AGAINST_SIDE"
    if s15["efficiency"]>=Decimal("0.55") and s15["overlap"]<=Decimal("0.45"):
        regime="DIRECTIONAL"
    elif s15["overlap"]>=Decimal("0.65") and s15["efficiency"]<=Decimal("0.35"):
        regime="RANGE"
    elif s5["range_ratio"]>=Decimal("1.35") and s5["body_fraction"]>=Decimal("0.55"):
        regime="EXPANSION"
    elif s5["range_ratio"]<=Decimal("0.75"):
        regime="COMPRESSION"
    else:
        regime="TRANSITION"
    if s5["range_ratio"]>s30["range_ratio"]*Decimal("1.25"):
        vol_transition="VOL_EXPANDING"
    elif s5["range_ratio"]<s30["range_ratio"]*Decimal("0.80"):
        vol_transition="VOL_CONTRACTING"
    else:
        vol_transition="VOL_STABLE"
    return {
        "perception_regime":regime,
        "vol_transition":vol_transition,
        "last_direction":direction,
        "eff5":_bucket(s5["efficiency"],(Decimal(".25"),Decimal(".5"),Decimal(".75"))),
        "eff15":_bucket(s15["efficiency"],(Decimal(".25"),Decimal(".5"),Decimal(".75"))),
        "overlap5":_bucket(s5["overlap"],(Decimal(".35"),Decimal(".55"),Decimal(".75"))),
        "overlap15":_bucket(s15["overlap"],(Decimal(".35"),Decimal(".55"),Decimal(".75"))),
        "range_ratio5":_bucket(s5["range_ratio"],(Decimal(".75"),Decimal("1"),Decimal("1.35"),Decimal("1.75"))),
        "body5":_bucket(s5["body_fraction"],(Decimal(".35"),Decimal(".5"),Decimal(".65"))),
        "wick5":_bucket(s5["wick_fraction"],(Decimal(".35"),Decimal(".5"),Decimal(".65"))),
        "last_displacement":_bucket(displacement,(Decimal(".35"),Decimal(".55"),Decimal(".75"))),
        "last_range_expansion":_bucket(range_expansion,(Decimal(".75"),Decimal("1"),Decimal("1.5"),Decimal("2"))),
        "signed_body_r":_bucket(body_signed,(Decimal("-.5"),Decimal("-.1"),Decimal(".1"),Decimal(".5"))),
        "close_from_entry_r":_bucket(close_from_entry,(Decimal("-.5"),Decimal("0"),Decimal(".5"),Decimal("1"))),
        "reference_location":_bucket(location,(Decimal(".2"),Decimal(".4"),Decimal(".6"),Decimal(".8"))),
        "side":side,
        "entry_family":str(row.get("entry_family","unknown")),
        "decision_minute_bucket":str(row.get("decision_minute_bucket","unknown")),
        "candidate_combo":str(row.get("candidate_combo","unknown")),
    }


STATE_FIELDS=(
    "perception_regime","vol_transition","last_direction","eff5","eff15",
    "overlap5","overlap15","range_ratio5","body5","wick5",
    "last_displacement","last_range_expansion","signed_body_r",
    "close_from_entry_r","reference_location",
)
GEOMETRY_FIELDS=("side","entry_family","decision_minute_bucket","candidate_combo")
INTERACTIONS=(
    ("perception_regime","vol_transition"),
    ("perception_regime","last_direction"),
    ("vol_transition","range_ratio5"),
    ("eff5","overlap5"),
    ("eff15","overlap15"),
    ("last_direction","signed_body_r"),
    ("last_displacement","last_range_expansion"),
    ("perception_regime","reference_location"),
    ("perception_regime","side"),
    ("vol_transition","side"),
)


def _decorate(
    rows:list[dict[str,object]],
    paths:dict[str,tuple[object,tuple[object,...]]],
)->list[dict[str,object]]:
    out=[]
    for source in rows:
        row=dict(source)
        signal=str(row["signal_at"])
        setup,bars=paths[signal]
        row.update(_perceive(row,setup,bars))
        out.append(row)
    return out


def _metrics(rows:list[dict[str,object]])->dict[str,object]:
    values=[v3._d(r["net_r_after_friction"]) for r in rows]
    gains=sum((x for x in values if x>0),Decimal(0))
    losses=-sum((x for x in values if x<0),Decimal(0))
    total=sum(values,Decimal(0))
    equity=peak=dd=Decimal(0); streak=max_streak=0
    for x in values:
        equity+=x; peak=max(peak,equity); dd=max(dd,peak-equity)
        if x<0: streak+=1; max_streak=max(max_streak,streak)
        else: streak=0
    return {
        "sample":len(values),"wins":sum(x>0 for x in values),"losses":sum(x<0 for x in values),
        "profit_factor":None if losses==0 else format(gains/losses,"f"),
        "total_r":format(total,"f"),
        "mean_r":"0" if not values else format(total/Decimal(len(values)),"f"),
        "max_drawdown_r":format(dd,"f"),"max_losing_streak":max_streak,
    }


def _posterior(history,current,fields,global_mean,shrinkage):
    key=tuple(str(current.get(f)) for f in fields)
    selected=[r for r in history if tuple(str(r.get(f)) for f in fields)==key]
    if len(selected)<4:return None
    total=sum((v3._d(r["net_r_after_friction"]) for r in selected),Decimal(0))
    n=Decimal(len(selected)); a=Decimal(shrinkage)
    return (total+a*global_mean)/(n+a),len(selected)


def _score(history,current,policy):
    fields=STATE_FIELDS if policy.profile=="STATE" else STATE_FIELDS+GEOMETRY_FIELDS
    global_mean=sum((v3._d(r["net_r_after_friction"]) for r in history),Decimal(0))/Decimal(len(history))
    estimates=[]
    for f in fields:
        x=_posterior(history,current,(f,),global_mean,policy.shrinkage)
        if x is not None: estimates.append((x[0],Decimal(x[1]).sqrt()))
    for pair in INTERACTIONS:
        if all(f in fields for f in pair):
            x=_posterior(history,current,pair,global_mean,policy.shrinkage)
            if x is not None: estimates.append((x[0],Decimal(x[1]).sqrt()*Decimal("1.5")))
    if len(estimates)<policy.minimum_groups:return None,len(estimates)
    w=sum((x[1] for x in estimates),Decimal(0))
    return sum((x[0]*x[1] for x in estimates),Decimal(0))/w,len(estimates)


def _apply(history,rows,policy):
    kept=[]; abstained=[]
    for source in rows:
        score,groups=_score(history,source,policy)
        row=dict(source); row["perception_score_r"]=None if score is None else format(score,"f"); row["perception_groups"]=groups
        if score is not None and score<policy.threshold: abstained.append(row)
        else: kept.append(row)
    baseline=_metrics(rows); shared=_metrics(kept)
    losses=sum(v3._d(r["net_r_after_friction"])<0 for r in rows)
    wins=sum(v3._d(r["net_r_after_friction"])>0 for r in rows)
    avoided=sum(v3._d(r["net_r_after_friction"])<0 for r in abstained)
    sacrificed=sum(v3._d(r["net_r_after_friction"])>0 for r in abstained)
    gross=sum((v3._d(r["net_r_after_friction"]) for r in rows if v3._d(r["net_r_after_friction"])>0),Decimal(0))
    sacr=sum((v3._d(r["net_r_after_friction"]) for r in abstained if v3._d(r["net_r_after_friction"])>0),Decimal(0))
    return {
        "baseline":baseline,"shared":shared,"input":len(rows),"kept":len(kept),"abstained":len(abstained),
        "losses_avoided":avoided,"winners_sacrificed":sacrificed,
        "loss_rejection_recall":"0" if not losses else format(Decimal(avoided)/Decimal(losses),"f"),
        "winner_count_retention":"0" if not wins else format(Decimal(wins-sacrificed)/Decimal(wins),"f"),
        "winner_r_retention":"1" if gross==0 else format((gross-sacr)/gross,"f"),
        "density_retained":"0" if not rows else format(Decimal(len(kept))/Decimal(len(rows)),"f"),
    }


def _gates(result):
    b=result["baseline"]; s=result["shared"]
    if b["profit_factor"] is None or s["profit_factor"] is None:return {"valid":False}
    return {
        "pf_plus_25pct":v3._d(s["profit_factor"])>=v3._d(b["profit_factor"])*Decimal("1.25"),
        "dd_minus_30pct":v3._d(s["max_drawdown_r"])<=v3._d(b["max_drawdown_r"])*Decimal(".70"),
        "loss_recall_at_least_25pct":v3._d(result["loss_rejection_recall"])>=Decimal(".25"),
        "winner_count_retention_at_least_80pct":v3._d(result["winner_count_retention"])>=Decimal(".80"),
        "winner_r_retention_at_least_90pct":v3._d(result["winner_r_retention"])>=Decimal(".90"),
        "density_at_least_55pct":v3._d(result["density_retained"])>=Decimal(".55"),
    }


def _score_policy(result):
    g=_gates(result)
    if not all(g.values()):return None
    b=result["baseline"];s=result["shared"]
    return (v3._d(s["profit_factor"])/v3._d(b["profit_factor"]))*(
        v3._d(b["max_drawdown_r"])/max(v3._d(s["max_drawdown_r"]),Decimal(".000001"))
    )*(Decimal(1)+v3._d(result["loss_rejection_recall"]))*v3._d(result["winner_r_retention"])


def run(r8_json,r6_json,r5_json,r8_evidence,r6_evidence,r5_evidence):
    r8=v3._load_trades(r8_json);r6=v3._load_trades(r6_json);r5=v3._load_trades(r5_json)
    all_rows=r8+r6+r5
    if len(all_rows)!=822 or sum(v3._d(r["net_r_after_friction"])<0 for r in all_rows)!=711 or sum(v3._d(r["net_r_after_friction"])>0 for r in all_rows)!=111:
        raise AssertionError("challenge set drift")
    p8=integrated._reconstruct_partition(r8_evidence);p6=integrated._reconstruct_partition(r6_evidence);p5=integrated._reconstruct_partition(r5_evidence)
    d8=_decorate(r8,p8);d6=_decorate(r6,p6);d5=_decorate(r5,p5)
    frontier=[];best=None
    for policy in POLICIES:
        cal=_apply(d8,d6,policy);score=_score_policy(cal)
        frontier.append({"policy":policy.payload(),"calibration":cal,"gates":_gates(cal),"selection_score":None if score is None else format(score,"f")})
        if score is not None and (best is None or score>best[0]):best=(score,policy)
    if best is None:
        return {"schema":SCHEMA,"identity":IDENTITY,"economic_status":"FALSIFIED_IN_CALIBRATION","challenge_set":{"trades":822,"losses":711,"wins":111},"frozen_policy":None,"evaluation":None,"gates":None,"passes_shared_perception":False,"frontier":frontier,"governance":{"asof_market_perception_primary":True,"historical_analog_similarity_used":False,"post_signal_bar_used":False,"current_outcome_feature_used":False,"journey_management_used":False,"capital_weighting_used":False,"r5_retuned":False,"live_authorized":False,"merge_authorized":False}}
    frozen=best[1]
    ev=_apply(d8+d6,d5,frozen);g=_gates(ev);passed=all(g.values())
    return {"schema":SCHEMA,"identity":IDENTITY,"economic_status":"PASSED_PERCEPTION_EVALUATION" if passed else "FALSIFIED_ON_R5","challenge_set":{"trades":822,"losses":711,"wins":111},"frozen_policy":frozen.payload(),"evaluation":ev,"gates":g,"passes_shared_perception":passed,"frontier":frontier,"governance":{"asof_market_perception_primary":True,"historical_analog_similarity_used":False,"post_signal_bar_used":False,"current_outcome_feature_used":False,"journey_management_used":False,"capital_weighting_used":False,"r5_retuned":False,"live_authorized":False,"merge_authorized":False}}


def main():
    p=argparse.ArgumentParser()
    for name in ("r8-json","r6-json","r5-json","r8-evidence","r6-evidence","r5-evidence"):p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    payload=run(a.r8_json,a.r6_json,a.r5_json,a.r8_evidence,a.r6_evidence,a.r5_evidence)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"economic_status":payload["economic_status"],"passes_shared_perception":payload["passes_shared_perception"],"frozen_policy":payload["frozen_policy"],"evaluation":payload["evaluation"],"gates":payload["gates"]},sort_keys=True))


if __name__=="__main__":main()
