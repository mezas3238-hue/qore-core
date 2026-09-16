"""Produce the definitive consumed VT-31 ledger by correcting exactly four roots.

The parent ledger is the immutable 780-root tick-corrected composition. A later
integrity audit found that exactly four `later-same-bar` roots had terminal exits
resolved by ticks but their initial M1 fill had not been checked against the
executable BID/ASK side. This module replaces only those four root outcomes from
the immutable initial-fill parity and its one-root pending finalization.

It cannot alter any other root and opens no fresh evidence.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path
from typing import Any

TERMINAL_PENDING={"initial-stop-at-executable-fill","initial-stop-in-fill-minute","fixed-2r-target-at-executable-fill","fixed-2r-target-in-fill-minute"}

def load(path: Path)->dict[str,Any]:
    p=json.loads(path.read_text())
    if p.get("research_only") is not True or p.get("opens_new_holdout") is not False: raise ValueError(f"governance guard {path}")
    return p

def terminal(source:dict[str,Any], r:object,status:str,resolution:str)->dict[str,Any]:
    return {"root_id":source["root_id"],"classification":"terminal","terminal_r":str(r),"terminal_status":status,"resolution_source":resolution,"partition":source["partition"],"market":source["market"],"ny_date":source["ny_date"],"side":source["side"],"signal_opened_at":source["signal_opened_at"]}

def nonterminal(source:dict[str,Any],klass:str,status:str,resolution:str)->dict[str,Any]:
    return {"root_id":source["root_id"],"classification":klass,"terminal_r":None,"terminal_status":status,"resolution_source":resolution,"partition":source["partition"],"market":source["market"],"ny_date":source["ny_date"],"side":source["side"],"signal_opened_at":source["signal_opened_at"]}

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("--parent-ledger",required=True,type=Path); ap.add_argument("--initial-manifest",required=True,type=Path); ap.add_argument("--initial-resolution",required=True,type=Path); ap.add_argument("--pending-manifest",required=True,type=Path); ap.add_argument("--pending-resolution",required=True,type=Path); ap.add_argument("--pending-lifecycle",required=True,type=Path); ap.add_argument("--pending-later-resolution",required=True,type=Path); ap.add_argument("--output",required=True,type=Path); a=ap.parse_args()
    parent=load(a.parent_ledger); im=load(a.initial_manifest); ir=load(a.initial_resolution); pm=load(a.pending_manifest); pr=load(a.pending_resolution); pl=load(a.pending_lifecycle); lr=load(a.pending_later_resolution)
    if parent.get("authority",{}).get("corrected_root_total")!=780: raise ValueError("parent must bind 780 corrected roots")
    sources={r["window_id"]:r for r in im.get("windows",[]) if isinstance(r,dict)}; results={r["window_id"]:r for r in ir.get("results",[]) if isinstance(r,dict)}
    if len(sources)!=4 or set(sources)!=set(results): raise ValueError("exact four initial parity roots required")
    root_sources={str(r["root_id"]):r for r in sources.values()}
    if len(root_sources)!=4: raise ValueError("four unique root ids required")
    parent_rows={r["root_id"]:r for r in parent["roots"]}
    if not set(root_sources)<=set(parent_rows): raise ValueError("four roots not contained in parent ledger")
    replacements:dict[str,dict[str,Any]]={}
    nofill=[]
    for wid,source in sources.items():
        root=str(source["root_id"]); status=str(results[wid].get("status"))
        if status=="initial-stop-after-fill": replacements[root]=terminal(source,"-1",status,"four-root:initial-fill-ticks")
        elif status=="fixed-2r-target-after-fill": replacements[root]=terminal(source,"2",status,"four-root:initial-fill-ticks")
        elif status=="filled-clear-source-minute":
            old=parent_rows[root]
            if old.get("classification")!="terminal": raise ValueError("clear initial fill does not have old later terminal")
            kept=dict(old); kept["resolution_source"]="four-root:initial-fill-confirmed+"+str(old.get("resolution_source")); replacements[root]=kept
        elif status=="no-executable-fill-in-source-minute": nofill.append((root,source))
        elif status.startswith("unresolved-"): replacements[root]=nonterminal(source,"censored",status,"four-root:initial-fill-ticks")
        else: raise ValueError(f"unknown four-root initial status {status}")
    if len(nofill)!=1: raise ValueError(f"expected exactly one pending root, got {len(nofill)}")
    root,source=nofill[0]
    pwin=pm.get("windows",[]); pres=pr.get("results",[])
    if len(pwin)!=1 or len(pres)!=1 or pwin[0].get("root_parent_window_id")!=root: raise ValueError("one-root pending finalization identity mismatch")
    pstatus=str(pres[0].get("status"))
    if pstatus in TERMINAL_PENDING: replacements[root]=terminal(source,pres[0].get("terminal_r"),pstatus,"four-root:pending-ticks")
    elif pstatus=="no-executable-fill-through-pending-cutoff": replacements[root]=nonterminal(source,"no_trade",pstatus,"four-root:pending-ticks")
    elif pstatus.startswith("unresolved-"): replacements[root]=nonterminal(source,"censored",pstatus,"four-root:pending-ticks")
    elif pstatus=="executable-fill-minute-clear":
        life=pl.get("results",[])
        if len(life)!=1: raise ValueError("clear pending fill requires one lifecycle row")
        ls=str(life[0].get("status"))
        if ls.startswith("terminal-"): replacements[root]=terminal(source,life[0].get("terminal_r"),ls,"four-root:pending-frozen-m1")
        elif ls=="censored-later-same-bar-stop-target-ambiguity":
            later=lr.get("results",[])
            if len(later)!=1: raise ValueError("later ambiguity requires one tick resolution")
            lstatus=str(later[0].get("status"))
            if lstatus.startswith("terminal-"): replacements[root]=terminal(source,later[0].get("terminal_r"),lstatus,"four-root:pending-later-ticks")
            else: replacements[root]=nonterminal(source,"censored",lstatus,"four-root:pending-later-ticks")
        else: replacements[root]=nonterminal(source,"censored",ls,"four-root:pending-frozen-m1")
    else: raise ValueError(f"unknown pending status {pstatus}")
    if len(replacements)!=4: raise AssertionError("exact four replacements required")
    final_roots=[]
    for old in parent["roots"]:
        final_roots.append(replacements.get(old["root_id"],old))
    if len(final_roots)!=780 or len({r["root_id"] for r in final_roots})!=780: raise AssertionError("root conservation failed")
    changed=[]
    for rid,new in replacements.items():
        old=parent_rows[rid]
        changed.append({"root_id":rid,"old_classification":old["classification"],"old_terminal_r":old.get("terminal_r"),"old_status":old.get("terminal_status"),"new_classification":new["classification"],"new_terminal_r":new.get("terminal_r"),"new_status":new.get("terminal_status")})
    trades=sorted([r for r in final_roots if r["classification"]=="terminal"],key=lambda r:(r["signal_opened_at"],r["market"],r["root_id"]))
    no_trade=sorted([r["root_id"] for r in final_roots if r["classification"]=="no_trade"])
    censored=sorted([r["root_id"] for r in final_roots if r["classification"]=="censored"])
    if len(trades)+len(no_trade)+len(censored)!=780: raise AssertionError("final classification conservation failed")
    payload=dict(parent); payload.update({"schema":"qore.vt31.tick_corrected.consumed_ledger.v2","candidate_status":"NO_R9_NOT_CERTIFIED","supersedes_parent_ledger":True,"four_root_initial_fill_parity_applied":True,"roots":final_roots,"trades":trades,"terminal_trade_count":len(trades),"no_trade_roots":no_trade,"censored_roots":censored,"four_root_correction":changed,"terminal_trade_counts_by_partition":dict(Counter(r["partition"] for r in trades)),"terminal_trade_counts_by_market":dict(Counter(r["market"] for r in trades)),"terminal_trade_counts_by_side":dict(Counter(r["side"] for r in trades))})
    payload["authority"]=dict(parent["authority"]); payload["authority"].update({"definitive_four_root_parity":True,"terminal_trade_count":len(trades),"no_trade_root_count":len(no_trade),"censored_root_count":len(censored)})
    a.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n"); print(json.dumps({"terminal":len(trades),"no_trade":len(no_trade),"censored":len(censored),"four_root_correction":changed},sort_keys=True))
if __name__=="__main__": main()
