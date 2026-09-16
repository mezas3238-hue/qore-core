"""Render consumed-only VT-31 causal diagnostics without selecting a candidate.

The report is descriptive. It may surface hypotheses but it must not choose
thresholds, optimize a rule, or open fresh evidence.
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

GROUP_ORDER=(
    "protected_swing_like_at_signal",
    "entry_family",
    "prior_day_alignment",
    "signal_minute_bucket",
    "risk_to_reference_bucket",
    "raid_body_bucket",
    "confirmation_body_bucket",
    "raid_to_extreme_latency",
    "opposing_liquidity_r_bucket",
    "market",
    "side",
)

def D(v: object)->Decimal:
    return Decimal(str(v))

def compact(m: dict[str,Any])->dict[str,Any]:
    return {"n":m["n"],"mean_stressed_r":m["mean_stressed_r"],"pf_stressed":m["profit_factor_stressed"],"total_stressed_r":m["total_stressed_r"],"wins":m["wins"],"losses":m["losses"]}

def row_metrics(rows:list[dict[str,Any]])->dict[str,Any]:
    vals=[D(r["terminal_r"])-Decimal("0.10") for r in rows]
    wins=[v for v in vals if v>0]; losses=[v for v in vals if v<0]
    total=sum(vals,Decimal(0)); n=len(vals)
    pf=sum(wins,Decimal(0))/abs(sum(losses,Decimal(0))) if losses else None
    return {"n":n,"wins":len(wins),"losses":len(losses),"total_stressed_r":format(total,"f"),"mean_stressed_r":format(total/Decimal(n),"f") if n else None,"pf_stressed":format(pf,"f") if pf is not None else None}

def group_rows(rows:list[dict[str,Any]],field:str)->dict[str,Any]:
    g:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for r in rows: g[str(r.get(field))].append(r)
    return {k:row_metrics(v) for k,v in sorted(g.items())}

def cross(rows:list[dict[str,Any]],a:str,b:str)->dict[str,Any]:
    g:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for r in rows: g[f"{r.get(a)} | {r.get(b)}"].append(r)
    return {k:row_metrics(v) for k,v in sorted(g.items())}

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("--forensics",required=True,type=Path); ap.add_argument("--economics",required=True,type=Path); ap.add_argument("--output",required=True,type=Path); a=ap.parse_args()
    f=json.loads(a.forensics.read_text()); e=json.loads(a.economics.read_text())
    if f.get("research_only") is not True or f.get("selection_prohibited") is not True: raise ValueError("forensics governance guard")
    if e.get("research_only") is not True or e.get("opens_new_holdout") is not False: raise ValueError("economics governance guard")
    groups=f["diagnostic_groups"]; rows=f["rows"]
    report_groups={name:{k:compact(v) for k,v in groups[name].items()} for name in GROUP_ORDER}
    ps=groups["protected_swing_like_at_signal"]; ps_contrast=None
    if "True" in ps and "False" in ps:
        ps_contrast={"true":compact(ps["True"]),"false":compact(ps["False"]),"mean_difference_true_minus_false":format(D(ps["True"]["mean_stressed_r"])-D(ps["False"]["mean_stressed_r"]),"f")}
    prior=groups["prior_day_alignment"]; prior_contrast=None
    if "True" in prior and "False" in prior:
        prior_contrast={"aligned":compact(prior["True"]),"opposed":compact(prior["False"]),"mean_difference_aligned_minus_opposed":format(D(prior["True"]["mean_stressed_r"])-D(prior["False"]["mean_stressed_r"]),"f")}
    streaks=f["top_losing_streaks"]
    streak_summary=[{k:s[k] for k in ("length","start","end","markets","sides","entry_families","protected_swing_like","mean_risk_to_reference","mean_confirmation_body_fraction","mean_raid_body_fraction","mean_opposing_liquidity_r")} for s in streaks[:10]]
    payload={
        "schema":"qore.vt31.definitive_deep_forensics_report.v2","research_only":True,"opens_new_holdout":False,"candidate_status":"NO_R9_NOT_CERTIFIED","selection_prohibited":True,
        "definitive_gate_pass":e["consumed_economic_gate_pass"],"definitive_0_10":e["results"]["0.10"],
        "source_target_structure":f["source_target_structure"],"max_global_losing_streak":f["max_losing_streak"],"top_losing_streaks":streak_summary,
        "protected_swing_like_contrast":ps_contrast,"prior_day_alignment_contrast":prior_contrast,"groups":report_groups,
        "terminal_status":group_rows(rows,"terminal_status"),"resolution_source":group_rows(rows,"resolution_source"),"partition":group_rows(rows,"partition"),
        "entry_family_x_terminal_status":cross(rows,"entry_family","terminal_status"),"market_x_terminal_status":cross(rows,"market","terminal_status"),"side_x_terminal_status":cross(rows,"side","terminal_status"),
        "interpretation_constraints":["group contrasts are descriptive diagnostics, not candidate-selection rules","post-entry terminal_r was used only as label","no threshold may be promoted without a finite predeclared family and leakage-free walk-forward"],
    }
    a.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"terminal_status":payload["terminal_status"],"resolution_source":payload["resolution_source"],"partition":payload["partition"],"source_target_structure":payload["source_target_structure"],"protected_swing_like_contrast":ps_contrast,"prior_day_alignment_contrast":prior_contrast,"groups":report_groups,"top_losing_streaks":streak_summary[:5]},sort_keys=True))
if __name__=="__main__": main()
