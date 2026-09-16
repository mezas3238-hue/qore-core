"""Freeze the exact pending LIMIT follow-up from the four-root initial-fill parity.

Consumed evidence only. Exactly one of the four original later-ambiguity roots
was classified no-executable-fill-in-source-minute. This module extends only
that already-selected pending LIMIT through the frozen 11:00 NY cutoff.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

NY=ZoneInfo("America/New_York"); UTC=ZoneInfo("UTC")

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--manifest",required=True,type=Path); p.add_argument("--resolution",required=True,type=Path); p.add_argument("--output",required=True,type=Path); a=p.parse_args()
    manifest=json.loads(a.manifest.read_text()); resolution=json.loads(a.resolution.read_text())
    for name,payload in (("manifest",manifest),("resolution",resolution)):
        if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False: raise ValueError(f"{name} governance guard")
    sources=manifest.get("windows"); results=resolution.get("results")
    if not isinstance(sources,list) or len(sources)!=4 or not isinstance(results,list) or len(results)!=4: raise ValueError("four-root parity cardinality changed")
    by_id={r["window_id"]:r for r in sources if isinstance(r,dict)}
    selected=[r for r in results if isinstance(r,dict) and r.get("status")=="no-executable-fill-in-source-minute"]
    if len(selected)!=1: raise ValueError(f"expected one no-fill root, got {len(selected)}")
    resolved=selected[0]; parent=str(resolved["window_id"]); original=by_id[parent]
    source_close=int(original["tick_window_close_ms"]); opened=datetime.fromtimestamp(int(original["tick_window_open_ms"])/1000,tz=UTC); local_day=opened.astimezone(NY).date(); cutoff=datetime.combine(local_day,time(11,0),tzinfo=NY).astimezone(UTC)
    row={"parent_window_id":parent,"root_parent_window_id":original.get("root_id"),"partition":original["partition"],"market":original["market"],"provider":original["provider"],"ny_date":original["ny_date"],"side":original["side"],"entry":original["entry"],"initial_stop":original["initial_stop"],"fixed_2r_target":original["fixed_2r_target"],"tick_window_open_ms":source_close+1,"tick_window_close_ms":int(cutoff.timestamp()*1000)-1,"followup_reason":"four-root-initial-parity-no-executable-fill-pending-limit-through-11-ny"}
    if row["tick_window_open_ms"]>row["tick_window_close_ms"]: raise ValueError("pending window already expired unexpectedly")
    row["window_id"]=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:24]
    payload={"schema":"qore.vt31.original_later.pending_followup.v1","research_only":True,"opens_new_holdout":False,"candidate_status":"NO_R9_NOT_CERTIFIED","source_resolution_count":1,"pending_entry_cutoff":"11:00 America/New_York","windows":[row],"session_expired_no_fill":[]}
    material=json.dumps(payload,sort_keys=True,separators=(",",":")); payload["sha256"]=hashlib.sha256(material.encode()).hexdigest(); a.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n"); print(json.dumps({"parent":parent,"root":row["root_parent_window_id"],"partition":row["partition"],"market":row["market"],"ny_date":row["ny_date"]},sort_keys=True))
if __name__=="__main__": main()
