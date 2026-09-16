"""Assemble the complete consumed VT-31 gap05 ledger after executable tick correction.

Coverage authority is the immutable gap05 fill-attrition evidence:
- 1,019 quality-pass setups total;
- 437 original fill-bar ambiguous roots;
- 339 previously-resolved parity-control roots;
- 4 original later-same-bar ambiguous roots;
- 239 original pending-no-fill setups (no trade).

Every one of the 780 roots that reached an M1 fill/ambiguity must end exactly as
terminal trade, no-trade, or censored. Only terminal trades enter economic
metrics. No fresh evidence is opened and no unresolved path is imputed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_QUALITY={"r5":367,"r6":366,"r8_fresh":286}
EXPECTED_ORIGINAL_NO_FILL={"r5":81,"r6":94,"r8_fresh":64}
EXPECTED_FILL_AMBIGUOUS={"r5":157,"r6":159,"r8_fresh":121}
EXPECTED_RESOLVED_PARITY={"r5":128,"r6":111,"r8_fresh":100}
EXPECTED_ORIGINAL_LATER={"r5":1,"r6":2,"r8_fresh":1}

TERMINAL_PENDING={
    "initial-stop-at-executable-fill",
    "initial-stop-in-fill-minute",
    "fixed-2r-target-at-executable-fill",
    "fixed-2r-target-in-fill-minute",
}


def _load(path: Path) -> dict[str,Any]:
    payload=json.loads(path.read_text())
    if payload.get("research_only") is not True:
        raise ValueError(f"research_only guard failed: {path}")
    if payload.get("opens_new_holdout") is True:
        raise ValueError(f"fresh holdout guard failed: {path}")
    return payload


def _meta(source: dict[str,Any]) -> dict[str,Any]:
    signal=source.get("signal_opened_at") or source.get("signal_at")
    if not isinstance(signal,str) or not signal:
        raise ValueError("root is missing signal timestamp")
    return {
        "partition":source["partition"],
        "market":source["market"],
        "ny_date":source["ny_date"],
        "side":source["side"],
        "signal_opened_at":signal,
    }


def _terminal(root_id: str, source: dict[str,Any], terminal_r: object, status: str, resolution_source: str) -> dict[str,Any]:
    if terminal_r is None:
        raise ValueError(f"terminal root {root_id} lacks terminal_r")
    row={"root_id":root_id,"classification":"terminal","terminal_r":str(terminal_r),"terminal_status":status,"resolution_source":resolution_source}
    row.update(_meta(source))
    return row


def _nonterminal(root_id: str, source: dict[str,Any], classification: str, status: str, resolution_source: str) -> dict[str,Any]:
    if classification not in {"no_trade","censored"}:
        raise ValueError(classification)
    row={"root_id":root_id,"classification":classification,"terminal_r":None,"terminal_status":status,"resolution_source":resolution_source}
    row.update(_meta(source))
    return row


def _followup_outcomes(
    root_sources: dict[str,dict[str,Any]],
    followup_manifest: dict[str,Any],
    pending_resolution: dict[str,Any],
    lifecycle: dict[str,Any],
    later_resolution: dict[str,Any],
    label: str,
) -> dict[str,dict[str,Any]]:
    windows=followup_manifest.get("windows")
    expired=followup_manifest.get("session_expired_no_fill",[])
    pending_rows=pending_resolution.get("results")
    life_rows=lifecycle.get("results")
    later_rows=later_resolution.get("results")
    if not all(isinstance(value,list) for value in (windows,expired,pending_rows,life_rows,later_rows)):
        raise ValueError(f"{label} follow-up inputs malformed")
    follow_by_id={row["window_id"]:row for row in windows if isinstance(row,dict)}
    pending_by_id={row["window_id"]:row for row in pending_rows if isinstance(row,dict)}
    life_by_follow={row["parent_window_id"]:row for row in life_rows if isinstance(row,dict)}
    later_by_window={row["window_id"]:row for row in later_rows if isinstance(row,dict)}
    if len(follow_by_id)!=len(windows) or len(pending_by_id)!=len(pending_rows):
        raise ValueError(f"{label} duplicate follow-up identities")
    if set(pending_by_id)!=set(follow_by_id):
        raise ValueError(f"{label} pending resolution identity mismatch")
    outcomes:dict[str,dict[str,Any]]={}
    for item in expired:
        if not isinstance(item,dict):
            raise ValueError(f"{label} expired row malformed")
        root_id=item.get("parent_window_id")
        if not isinstance(root_id,str) or root_id not in root_sources or root_id in outcomes:
            raise ValueError(f"{label} expired root mismatch")
        outcomes[root_id]=_nonterminal(root_id,root_sources[root_id],"no_trade","pending-entry-window-expired-no-fill",label)
    for follow_id,source_follow in follow_by_id.items():
        root_id=source_follow.get("parent_window_id")
        if not isinstance(root_id,str) or root_id not in root_sources or root_id in outcomes:
            raise ValueError(f"{label} root identity mismatch")
        row=pending_by_id[follow_id]
        status=str(row.get("status"))
        if status in TERMINAL_PENDING:
            outcomes[root_id]=_terminal(root_id,root_sources[root_id],row.get("terminal_r"),status,label+":pending-ticks")
            continue
        if status=="no-executable-fill-through-pending-cutoff":
            outcomes[root_id]=_nonterminal(root_id,root_sources[root_id],"no_trade",status,label+":pending-ticks")
            continue
        if status.startswith("unresolved-"):
            outcomes[root_id]=_nonterminal(root_id,root_sources[root_id],"censored",status,label+":pending-ticks")
            continue
        if status!="executable-fill-minute-clear":
            raise ValueError(f"{label} unknown pending status {status}")
        life=life_by_follow.get(follow_id)
        if life is None:
            raise ValueError(f"{label} clear fill lacks lifecycle row")
        life_status=str(life.get("status"))
        if life_status.startswith("terminal-"):
            outcomes[root_id]=_terminal(root_id,root_sources[root_id],life.get("terminal_r"),life_status,label+":frozen-m1-lifecycle")
            continue
        if life_status=="censored-later-same-bar-stop-target-ambiguity":
            ambiguity_id=life.get("ambiguity_window_id")
            if not isinstance(ambiguity_id,str) or ambiguity_id not in later_by_window:
                raise ValueError(f"{label} later ambiguity lacks tick resolution")
            later=later_by_window[ambiguity_id]
            later_status=str(later.get("status"))
            if later_status.startswith("terminal-"):
                outcomes[root_id]=_terminal(root_id,root_sources[root_id],later.get("terminal_r"),later_status,label+":later-open-position-ticks")
            else:
                outcomes[root_id]=_nonterminal(root_id,root_sources[root_id],"censored",later_status,label+":later-open-position-ticks")
            continue
        if life_status.startswith("censored-"):
            outcomes[root_id]=_nonterminal(root_id,root_sources[root_id],"censored",life_status,label+":frozen-m1-lifecycle")
            continue
        raise ValueError(f"{label} unknown lifecycle status {life_status}")
    expected_roots={row.get("parent_window_id") for row in windows if isinstance(row,dict)} | {row.get("parent_window_id") for row in expired if isinstance(row,dict)}
    if set(outcomes)!=expected_roots:
        raise ValueError(f"{label} follow-up root coverage mismatch")
    return outcomes


def build(args: argparse.Namespace) -> dict[str,Any]:
    attrition=_load(args.fill_attrition_summary)
    # Summary does not carry the standard governance keys in the old artifact;
    # the workflow separately verifies that immutable artifact. Accept its known schema.
    raise AssertionError("unreachable")


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--fill-attrition-summary",required=True,type=Path)
    parser.add_argument("--ambiguous-manifest",required=True,type=Path)
    parser.add_argument("--ambiguous-resolution",required=True,type=Path)
    parser.add_argument("--ambiguous-lifecycle",required=True,type=Path)
    parser.add_argument("--ambiguous-later-resolution",required=True,type=Path)
    parser.add_argument("--nofill-followup-manifest",required=True,type=Path)
    parser.add_argument("--nofill-pending-resolution",required=True,type=Path)
    parser.add_argument("--nofill-lifecycle",required=True,type=Path)
    parser.add_argument("--nofill-later-resolution",required=True,type=Path)
    parser.add_argument("--parity-manifest",required=True,type=Path)
    parser.add_argument("--parity-evaluation",required=True,type=Path)
    parser.add_argument("--parity-correction-dir",required=True,type=Path)
    parser.add_argument("--original-later-manifest",required=True,type=Path)
    parser.add_argument("--original-later-resolution",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()

    # The legacy fill-attrition summary predates the standard governance keys,
    # so validate its exact gap05 accounting structurally here.
    attrition=json.loads(args.fill_attrition_summary.read_text())
    for partition in EXPECTED_QUALITY:
        aggregate=attrition[partition]["gap05"]["aggregate"]
        assert aggregate.get("quality-pass",0)==EXPECTED_QUALITY[partition]
        assert aggregate.get("pending-no-fill-before-11",0)==EXPECTED_ORIGINAL_NO_FILL[partition]
        assert aggregate.get("fill-bar-path-ambiguous",0)==EXPECTED_FILL_AMBIGUOUS[partition]
        assert aggregate.get("later-same-bar-stop-target-ambiguous",0)==EXPECTED_ORIGINAL_LATER[partition]
        assert aggregate.get("resolved-protected-stop",0)+aggregate.get("resolved-fixed-2r-target",0)==EXPECTED_RESOLVED_PARITY[partition]

    ambiguous_manifest=_load(args.ambiguous_manifest)
    ambiguous_resolution=_load(args.ambiguous_resolution)
    ambiguous_lifecycle=_load(args.ambiguous_lifecycle)
    ambiguous_later=_load(args.ambiguous_later_resolution)
    nofill_manifest=_load(args.nofill_followup_manifest)
    nofill_pending=_load(args.nofill_pending_resolution)
    nofill_lifecycle=_load(args.nofill_lifecycle)
    nofill_later=_load(args.nofill_later_resolution)
    parity_manifest=_load(args.parity_manifest)
    parity_eval=_load(args.parity_evaluation)
    original_manifest=_load(args.original_later_manifest)
    original_resolution=_load(args.original_later_resolution)

    parity_dir=args.parity_correction_dir
    parity_followup=_load(parity_dir/"vt31-parity-no-fill-followup-manifest.json")
    parity_pending=_load(parity_dir/"vt31-parity-pending-limit-resolution.json")
    parity_lifecycle=_load(parity_dir/"vt31-pending-fill-lifecycle.json")
    parity_later=_load(parity_dir/"vt31-parity-later-open-position-resolution.json")

    ambiguous_sources={row["window_id"]:row for row in ambiguous_manifest["windows"]}
    parity_sources={row["window_id"]:row for row in parity_manifest["windows"]}
    original_sources={row["root_id"]:row for row in original_manifest["windows"]}
    if len(ambiguous_sources)!=437 or len(parity_sources)!=339 or len(original_sources)!=4:
        raise ValueError("root source cardinality mismatch")
    root_sets=(set(ambiguous_sources),set(parity_sources),set(original_sources))
    if root_sets[0]&root_sets[1] or root_sets[0]&root_sets[2] or root_sets[1]&root_sets[2]:
        raise ValueError("root identity collision across consumed classes")

    outcomes:dict[str,dict[str,Any]]={}

    # 437 fill-bar ambiguous roots.
    amb_res={row["window_id"]:row for row in ambiguous_resolution["results"]}
    amb_life={row["parent_window_id"]:row for row in ambiguous_lifecycle["results"]}
    amb_later={row["window_id"]:row for row in ambiguous_later["results"]}
    if set(amb_res)!=set(ambiguous_sources):
        raise ValueError("437 resolution/root mismatch")
    nofill_root_ids=set()
    for root_id,source in ambiguous_sources.items():
        row=amb_res[root_id]
        status=str(row.get("status"))
        if status in {"initial-stop-after-fill","fixed-2r-target-after-fill"}:
            outcomes[root_id]=_terminal(root_id,source,row.get("terminal_r"),status,"437:fill-minute-ticks")
        elif status=="unresolved-same-ms-cross-stream-order" or status.startswith("unresolved-"):
            outcomes[root_id]=_nonterminal(root_id,source,"censored",status,"437:fill-minute-ticks")
        elif status=="filled-clear-source-minute":
            life=amb_life.get(root_id)
            if life is None:
                raise ValueError("437 clear fill missing lifecycle")
            life_status=str(life.get("status"))
            if life_status.startswith("terminal-"):
                outcomes[root_id]=_terminal(root_id,source,life.get("terminal_r"),life_status,"437:frozen-m1-lifecycle")
            elif life_status=="censored-later-same-bar-stop-target-ambiguity":
                ambiguity_id=life.get("ambiguity_window_id")
                if not isinstance(ambiguity_id,str) or ambiguity_id not in amb_later:
                    raise ValueError("437 later ambiguity missing tick resolution")
                later=amb_later[ambiguity_id]
                later_status=str(later.get("status"))
                if later_status.startswith("terminal-"):
                    outcomes[root_id]=_terminal(root_id,source,later.get("terminal_r"),later_status,"437:later-open-position-ticks")
                else:
                    outcomes[root_id]=_nonterminal(root_id,source,"censored",later_status,"437:later-open-position-ticks")
            else:
                outcomes[root_id]=_nonterminal(root_id,source,"censored",life_status,"437:frozen-m1-lifecycle")
        elif status=="no-executable-fill-in-source-minute":
            nofill_root_ids.add(root_id)
        else:
            raise ValueError(f"unknown 437 status {status}")
    nofill_outcomes=_followup_outcomes(ambiguous_sources,nofill_manifest,nofill_pending,nofill_lifecycle,nofill_later,"437:no-fill-followup")
    if set(nofill_outcomes)!=nofill_root_ids:
        raise ValueError("437 no-fill follow-up root set mismatch")
    outcomes.update(nofill_outcomes)

    # 339 previously resolved parity controls, corrected by executable quote side.
    eval_rows={row["window_id"]:row for row in parity_eval["results"]}
    if set(eval_rows)!=set(parity_sources):
        raise ValueError("339 parity evaluation/root mismatch")
    parity_nofill_roots=set()
    for root_id,source in parity_sources.items():
        row=eval_rows[root_id]
        status=str(row.get("tick_status"))
        if status=="filled-clear-source-minute":
            outcomes[root_id]=_terminal(root_id,source,source["frozen_r_multiple"],str(source["frozen_exit_reason"]),"339:parity-preserved-frozen-m1")
        elif status=="initial-stop-after-fill":
            outcomes[root_id]=_terminal(root_id,source,"-1",status,"339:fill-minute-ticks")
        elif status=="no-executable-fill-in-source-minute":
            parity_nofill_roots.add(root_id)
        elif status.startswith("unresolved-"):
            outcomes[root_id]=_nonterminal(root_id,source,"censored",status,"339:fill-minute-ticks")
        else:
            raise ValueError(f"unknown 339 parity status {status}")
    parity_follow_outcomes=_followup_outcomes(parity_sources,parity_followup,parity_pending,parity_lifecycle,parity_later,"339:no-fill-followup")
    if set(parity_follow_outcomes)!=parity_nofill_roots:
        raise ValueError("339 no-fill correction root set mismatch")
    outcomes.update(parity_follow_outcomes)

    # Four original later same-bar ambiguities omitted from 437+339.
    original_by_window={row["window_id"]:row for row in original_manifest["windows"]}
    original_res={row["window_id"]:row for row in original_resolution["results"]}
    if set(original_by_window)!=set(original_res):
        raise ValueError("four original later ambiguity identity mismatch")
    for window_id,source_window in original_by_window.items():
        root_id=str(source_window["root_id"])
        row=original_res[window_id]
        status=str(row.get("status"))
        if status.startswith("terminal-"):
            outcomes[root_id]=_terminal(root_id,original_sources[root_id],row.get("terminal_r"),status,"4:original-later-open-position-ticks")
        else:
            outcomes[root_id]=_nonterminal(root_id,original_sources[root_id],"censored",status,"4:original-later-open-position-ticks")

    expected_root_count=437+339+4
    if len(outcomes)!=expected_root_count:
        raise ValueError(f"corrected root coverage mismatch {len(outcomes)} != {expected_root_count}")
    if set(outcomes)!=(set(ambiguous_sources)|set(parity_sources)|set(original_sources)):
        raise ValueError("corrected outcome root set mismatch")

    all_rows=sorted(outcomes.values(),key=lambda row:(row["signal_opened_at"],row["market"],row["root_id"]))
    trades=[row for row in all_rows if row["classification"]=="terminal"]
    no_trade=[row for row in all_rows if row["classification"]=="no_trade"]
    censored=[row for row in all_rows if row["classification"]=="censored"]
    if len(trades)+len(no_trade)+len(censored)!=expected_root_count:
        raise AssertionError("classification coverage failed")

    authority_quality=sum(EXPECTED_QUALITY.values())
    authority_original_nofill=sum(EXPECTED_ORIGINAL_NO_FILL.values())
    if expected_root_count+authority_original_nofill!=authority_quality:
        raise AssertionError("quality-pass accounting failed")
    class_counts=Counter(row["classification"] for row in all_rows)
    trade_partition=Counter(row["partition"] for row in trades)
    trade_market=Counter(row["market"] for row in trades)
    trade_side=Counter(row["side"] for row in trades)
    payload={
        "schema":"qore.vt31.tick_corrected_consumed_ledger.v1",
        "research_only":True,
        "opens_new_holdout":False,
        "candidate_status":"NO_R9_NOT_CERTIFIED",
        "authority":{
            "gap05_quality_pass_total":authority_quality,
            "quality_pass_by_partition":EXPECTED_QUALITY,
            "original_pending_no_fill_total":authority_original_nofill,
            "original_pending_no_fill_by_partition":EXPECTED_ORIGINAL_NO_FILL,
            "corrected_root_total":expected_root_count,
            "corrected_root_classes":dict(sorted(class_counts.items())),
            "accounting_identity":"quality_pass = corrected_roots + original_pending_no_fill",
        },
        "terminal_trade_count":len(trades),
        "terminal_trade_counts_by_partition":dict(sorted(trade_partition.items())),
        "terminal_trade_counts_by_market":dict(sorted(trade_market.items())),
        "terminal_trade_counts_by_side":dict(sorted(trade_side.items())),
        "trades":trades,
        "no_trade_roots":no_trade,
        "censored_roots":censored,
    }
    args.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"terminal_trade_count":len(trades),"no_trade_roots":len(no_trade),"censored_roots":len(censored),"trade_partition":dict(trade_partition),"trade_market":dict(trade_market),"trade_side":dict(trade_side)},sort_keys=True))


if __name__=="__main__":
    main()
