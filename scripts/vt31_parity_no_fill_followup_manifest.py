"""Freeze consumed follow-up windows for the 65 parity controls without executable fill.

The source is the immutable 339-row previously-resolved control manifest plus the
immutable BID/ASK parity evaluation. Only rows classified
`no-executable-fill-in-source-minute` are carried forward. The original LIMIT
remains eligible through 11:00 New York exactly as in the frozen simulator.
No fresh evidence, setup discovery, or threshold change occurs here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
EXPECTED_SOURCE_ROWS = 339
EXPECTED_NO_FILL = 65


def _canonical_id(row: dict[str, Any]) -> str:
    material=json.dumps(row,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(material.encode()).hexdigest()[:24]


def build(source_manifest_path: Path, evaluation_path: Path, output_path: Path) -> dict[str, Any]:
    source=json.loads(source_manifest_path.read_text())
    evaluation=json.loads(evaluation_path.read_text())
    for name,payload in (("source",source),("evaluation",evaluation)):
        if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False:
            raise ValueError(f"{name} governance guard failed")
    source_rows=source.get("windows")
    eval_rows=evaluation.get("results")
    if not isinstance(source_rows,list) or len(source_rows)!=EXPECTED_SOURCE_ROWS:
        raise ValueError("parity source manifest cardinality changed")
    if not isinstance(eval_rows,list) or len(eval_rows)!=EXPECTED_SOURCE_ROWS:
        raise ValueError("parity evaluation cardinality changed")
    by_id={row["window_id"]:row for row in source_rows if isinstance(row,dict)}
    if len(by_id)!=EXPECTED_SOURCE_ROWS:
        raise ValueError("parity source identities malformed")
    selected=[row for row in eval_rows if isinstance(row,dict) and row.get("status")=="no-executable-fill-in-source-minute"]
    if len(selected)!=EXPECTED_NO_FILL:
        raise ValueError(f"parity no-fill count changed: {len(selected)}")

    windows=[]
    expired=[]
    for resolved in selected:
        parent_id=resolved.get("window_id")
        if not isinstance(parent_id,str) or parent_id not in by_id:
            raise ValueError("parity evaluation/source identity mismatch")
        original=by_id[parent_id]
        close_ms=original.get("tick_window_close_ms")
        open_ms=original.get("tick_window_open_ms")
        if type(close_ms) is not int or type(open_ms) is not int:
            raise ValueError("parity source tick boundaries malformed")
        local_day=datetime.fromtimestamp(open_ms/1000,tz=UTC).astimezone(NY).date()
        cutoff=datetime.combine(local_day,time(11,0),tzinfo=NY).astimezone(UTC)
        follow_open=close_ms+1
        follow_close=int(cutoff.timestamp()*1000)-1
        if follow_open>follow_close:
            expired.append({
                "parent_window_id":parent_id,
                "partition":original["partition"],
                "market":original["market"],
                "ny_date":original["ny_date"],
                "side":original["side"],
                "status":"pending-entry-window-expired-no-fill",
            })
            continue
        row={
            "parent_window_id":parent_id,
            "partition":original["partition"],
            "market":original["market"],
            "provider":original["provider"],
            "ny_date":original["ny_date"],
            "side":original["side"],
            "entry":original["entry"],
            "initial_stop":original["initial_stop"],
            "fixed_2r_target":original["fixed_2r_target"],
            "tick_window_open_ms":follow_open,
            "tick_window_close_ms":follow_close,
            "followup_reason":"parity-m1-touch-not-executable-pending-limit-through-11-ny",
        }
        row["window_id"]=_canonical_id(row)
        windows.append(row)
    windows.sort(key=lambda row:(row["market"],row["tick_window_open_ms"],row["window_id"]))
    if len(windows)+len(expired)!=EXPECTED_NO_FILL:
        raise AssertionError("parity follow-up lost source rows")
    if len({row["window_id"] for row in windows})!=len(windows):
        raise AssertionError("parity follow-up ids duplicated")
    payload={
        "schema":"qore.vt31.consumed_parity_no_fill_followup_manifest.v1",
        "research_only":True,
        "opens_new_holdout":False,
        "candidate_status":"NO_R9_NOT_CERTIFIED",
        "source_resolution_status":"no-executable-fill-in-source-minute",
        "source_resolution_count":EXPECTED_NO_FILL,
        "pending_entry_cutoff":"11:00:00 America/New_York",
        "windows":windows,
        "session_expired_no_fill":expired,
    }
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"))
    payload["sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    output_path.write_text(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n")
    return payload


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-manifest",required=True,type=Path)
    parser.add_argument("--evaluation",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    payload=build(args.source_manifest,args.evaluation,args.output)
    print(json.dumps({"followup_windows":len(payload["windows"]),"session_expired_no_fill":len(payload["session_expired_no_fill"])},sort_keys=True))


if __name__=="__main__":
    main()
