"""Source-only exact 20 and complete nine-market causality census. No PnL read."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_direction_source_forensic_v1 import (  # noqa: E501
    load_sources,
    sample_hash,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_v49_v50_g_waterfall_v1 import (
    source_id,
)

IDENTITY="QORE_SCALPER_ISSUE772_OUTCOME_BLIND_2020_2876_DIRECTION_AUDIT_V1"
FAMILIES=("LIQUIDITY_SWEEP_CISD","FVG_RETRACE_CISD")


def max3(sources:tuple[V49Opportunity,...])->set[str]:
    grouped:dict[tuple[str,str],list[V49Opportunity]]=defaultdict(list)
    for row in sources:
        grouped[row.session,row.operating_date].append(row)
    selected:set[str]=set()
    for group in grouped.values():
        for row in sorted(group,key=lambda x:(
            x.m1_trigger_confirmed_at,x.symbol,x.m1_trigger_family
        ))[:3]:
            selected.add(source_id(row))
    return selected


def sample20(chosen:tuple[dict[str,Any],...])->tuple[dict[str,Any],...]:
    if len(chosen)!=2020:
        raise ValueError("original source-only A MAX3 must have 2020")
    selected:list[dict[str,Any]]=[]
    seen:set[str]=set()
    for family in FAMILIES:
        for inherited in (False,True):
            group=sorted(
                (row for row in chosen
                 if row["trigger_family"]==family
                 and row["h1_state_inherited"]==inherited),
                key=lambda x:x["selection_rank_sha256"]
            )
            for row in group[:5]:
                selected.append(row)
                seen.add(row["source_opportunity_id"])
    for row in sorted(chosen,key=lambda x:x["selection_rank_sha256"]):
        if len(selected)==20:
            break
        if row["source_opportunity_id"] not in seen:
            selected.append(row)
            seen.add(row["source_opportunity_id"])
    if len(selected)!=20 or len(seen)!=20:
        raise ValueError("deterministic exactly 20 unique source IDs")
    if any(sample_hash(x["source_opportunity_id"])!=x["selection_rank_sha256"]
           for x in selected):
        raise ValueError("source-ID selection hash mismatch")
    return tuple(selected)


def mk_trace(rank:int,row:dict[str,Any])->str:
    def series(tag:str,data:list[dict[str,Any]])->str:
        header=(
            "### "+tag+" completed at/as-of decision\n\n"
            "| Opened | Available after close | Open | High | Low | Close |\n"
            "|---|---|---:|---:|---:|---:|\n"
        )
        return header+"".join(
            f"| {a['opened_at']} | {a['closed_at']} | {a['open']} | "
            f"{a['high']} | {a['low']} | {a['close']} |\n"
            for a in data
        )+"\n"
    info=[
        f"# Trace {rank:02d} — {row['symbol']} {row['session']} {row['operating_date']}",
        "Source-only forensic witness. No PnL, no strategy optimization, no certification.",
        f"Source ID: {row['source_opportunity_id']}",
        f"SHA256 deterministic selection: {row['selection_rank_sha256']}",
        f"V49 direction: {row['m1_direction']} / H1 {row['h1_direction']}",
        f"M1 trigger family: {row['trigger_family']}",
        f"H1 basis: {row['h1_state_basis']}",
        f"H1 inherited: {row['h1_state_inherited']}"
        f";state active-from original: {row['original_state_from']}",
        f"H1 true original event as recoverable from ORIGINAL V48 observer"
        f":{row['original_source_origin_at']}",
        f"H1 event recovery status: {row['original_source_origin_status']}",
        f"H1 original event age in minutes: {row['h1_source_age_minutes']}",
        f"4-bar completed H1 slope: {row['h1_trend4_completed_native']}"
        f" / agreement {row['h1_trend4_agreement']}, descriptive NOT TTrades",
        f"M15 setup confirmed source at: {row['m15_setup_confirmed_at']}",
        f"M15 timestamp matches closed native aggregated candle"
        f":{row['m15_confirmed_in_closed_native']}",
        f"M15→M1 delay: {row['m15_setup_to_entry_minutes']} minutes",
        f"Entry at: {row['decision_at']} close price {row['entry_price']}"
        f";native exact match: {row['entry_matches_native_m1_close']}",
        f"M15 protected swing stop: {row['m15_swing_stop_price']}",
        f"H1 target source witness: {row['structural_h1_target_price']}",
        f"M15 pivot-right candle causal witness"
        f":{row['swing_right_candle_and_earliest_availability']}",
        f"M1 sweep/opposing series/first CISD: {row['m1_sweep_series_CISD_first_online']}",
        f"Source timestamp/price violations: {row['causal_timestamp_failures']}",
        f"Native provider slice SHA256: {row['feed_sha256_native_research_slice']}",
        "Source H1 active-until is retrospective metadata; do NOT use for as-of decision.",
        "Candle series are truncated to bars closed no later than the decision.",
        "Full independent Candle2/Candle3 POI and M15-right/M1 CISD first-online: UNRESOLVED.",
        "Author-exact TTrades semantics: UNRESOLVED. No trading authority.",
        "",
        series("H1",row["h1_last_5_closed_candles"]),
        series("M15",row["m15_recent_candles"]),
        series("M1",row["m1_recent_closed_candles"]),
    ]
    return "\n\n".join(info)+"\n"


def aggregate(root:Path,output:Path)->dict[str,Any]:
    source_files=tuple(sorted(root.rglob(
        "capitalizer-*-v49-hf-capacity-opportunities.jsonl"
    )))
    witness_files=tuple(sorted(root.rglob(
        "scalper-issue772-all-source-causal-witnesses.jsonl"
    )))
    market_files=tuple(sorted(root.rglob(
        "scalper-issue772-market-causal-census.json"
    )))
    if len(source_files)!=9 or len(witness_files)!=9 or len(market_files)!=9:
        raise ValueError("nine market source, witness and market reports required")
    source=tuple(x for f in source_files for x in load_sources(f.parent))
    rows=tuple(
        json.loads(line) for f in witness_files
        for line in f.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    markets=tuple(json.loads(f.read_text(encoding="utf-8")) for f in market_files)
    ids={source_id(x) for x in source}
    witnesses={x["source_opportunity_id"]:x for x in rows}
    if (
        len(source)!=2876 or len(ids)!=2876 or len(rows)!=2876
        or len(witnesses)!=2876 or ids!=set(witnesses)
        or len({m["symbol"] for m in markets})!=9
        or sum(m["original_source_n"] for m in markets)!=2876
    ):
        raise ValueError("source identities and nine market reports not identical")
    a_ids=max3(source)
    if len(a_ids)!=2020:
        raise ValueError("A source-only first MAX3 no longer has 2020")
    selected=tuple(row for row in rows
                   if row["source_opportunity_id"] in a_ids)
    chosen=sample20(selected)
    output.mkdir(parents=True,exist_ok=True)
    tracedir=output/"20_outcome_blind_asof_traces"
    tracedir.mkdir(exist_ok=True)
    manifest=[]
    for n,row in enumerate(chosen,1):
        name=f"TRACE_{n:02d}_{row['symbol']}_{row['source_opportunity_id'][:16]}"
        (tracedir/(name+".json")).write_text(
            json.dumps(row,sort_keys=True,indent=2)+"\n",encoding="utf-8"
        )
        (tracedir/(name+".md")).write_text(
            mk_trace(n,row),encoding="utf-8"
        )
        manifest.append({
            "rank":n,"source_id":row["source_opportunity_id"],
            "hash_sha256":row["selection_rank_sha256"],
            "symbol":row["symbol"],"session":row["session"],
            "family":row["trigger_family"],
            "inherited":row["h1_state_inherited"],
            "markdown_path":f"20_outcome_blind_asof_traces/{name}.md",
            "json_path":f"20_outcome_blind_asof_traces/{name}.json",
            "future_outcomes_used":False,
        })
    (output/"scalper-issue772-20-source-IDs-manifest.json").write_text(
        json.dumps({
            "sample20":manifest,
            "rule":"5 min SHA256 per family x inherited/fresh, fill residual global hash",
            "historical_outcomes_or_1to1_used":False,
        },indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    full=Counter()
    a=Counter()
    market_dir:dict[str,Counter[str]]=defaultdict(Counter)
    session_dir:dict[str,Counter[str]]=defaultdict(Counter)
    lag=[]
    ages=[]
    errors:dict[str,list[str]]=defaultdict(list)
    for row in rows:
        sid=row["source_opportunity_id"]
        in_a=sid in a_ids
        groups=[full,a] if in_a else [full]
        for count in groups:
            count["N"]+=1
            count["INHERITED" if row["h1_state_inherited"] else "FRESH"]+=1
            count["SOURCE_ORIGIN_RESOLVED" if row["original_source_origin_at"]
                  else "SOURCE_ORIGIN_UNKNOWN"]+=1
            count["H1_4BAR_"+row["h1_trend4_agreement"]]+=1
            count["SOURCE_TIMESTAMP_PASS" if row["causal_timestamp_pass"]
                  else "SOURCE_TIMESTAMP_FAIL"]+=1
            count["TRIGGER_"+row["trigger_family"]]+=1
            for reason in row["causal_timestamp_failures"]:
                count["FAULT_"+reason]+=1
        if in_a:
            market_dir[row["symbol"]][row["h1_trend4_agreement"]]+=1
            session_dir[row["session"]][row["h1_trend4_agreement"]]+=1
            lag.append(float(row["m15_setup_to_entry_minutes"]))
            if row["h1_source_age_minutes"] is not None:
                ages.append(float(row["h1_source_age_minutes"]))
            for reason in row["causal_timestamp_failures"]:
                errors[reason].append(sid)
    def desc(v:list[float])->dict[str,Any]:
        z=sorted(v)
        return {
            "n":len(z),"min":z[0] if z else None,
            "median":z[len(z)//2] if z else None,
            "p95":z[round(0.95*(len(z)-1))] if z else None,
            "max":z[-1] if z else None,
        }
    (output/"scalper-issue772-A2020-source-causal-witnesses.jsonl").write_text(
        "".join(json.dumps(x,sort_keys=True)+"\n" for x in selected),
        encoding="utf-8"
    )
    report={
        "identity":IDENTITY,"all_source":len(rows),"original_A":len(selected),
        "source_only_NO_economics":True,
        "manifest20":manifest,
        "full_2876_census":dict(sorted(full.items())),
        "A_2020_census":dict(sorted(a.items())),
        "A_m15_confirmed_to_m1_entry_minutes":desc(lag),
        "A_recovered_origin_H1_age_minutes_observed_only":desc(ages),
        "A_H1_4bar_price_slope_agreement_by_market":{
            k:dict(sorted(c.items())) for k,c in sorted(market_dir.items())
        },
        "A_H1_4bar_price_slope_agreement_by_session":{
            k:dict(sorted(c.items())) for k,c in sorted(session_dir.items())
        },
        "A_source_timestamp_fault_id_details":{
            k:sorted(v) for k,v in sorted(errors.items())
        },
        "native_feed_sha256_by_market":{
            m["symbol"]:m["native_feed_sha256"] for m in markets
        },
        "author_validated_signal_semantics":False,
        "independent_full_first_online_reconstructed":False,
        "original_V48_bias_event_recovery_used_only_as_comparator":True,
        "unresolved_M15_right_and_CISD_first_online_A":2020,
        "V49_or_VPS_modified":False,"certified":False,
    }
    (output/"scalper-issue772-source-causal-nine-market-report.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    print("ISSUE772_SOURCE_GATE_A_B",json.dumps({
        "n":report["all_source"],"A":report["original_A"],
        "sample20":len(manifest),"full":report["full_2876_census"],
        "a":report["A_2020_census"],
        "lag":report["A_m15_confirmed_to_m1_entry_minutes"],
        "age":report["A_recovered_origin_H1_age_minutes_observed_only"],
        "first_online_independent_complete":False,
    },sort_keys=True))
    return report


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("frozen_nine_markets",type=Path)
    p.add_argument("output",type=Path)
    x=p.parse_args()
    aggregate(x.frozen_nine_markets,x.output)


if __name__=="__main__":
    main()
