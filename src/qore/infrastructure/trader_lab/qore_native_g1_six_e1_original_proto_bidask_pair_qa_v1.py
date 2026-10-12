"""Independent original native Protobuf audit of 6 historical E1 research clock pairs.

Genuine frozen 7-method E1 research opportunities, NOT real trades or fills.
Source current IC Markets DEMO NOT homologated to original CIBO G0 contracts.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    qore_native_g1_causal_quote_checkpoint_pair_gate_v1 as gate,
    qore_native_g1_e1_original_opportunity_quote_coverage_v1 as e1,
    qore_native_g1_proto_wire_second_decoder_qa_v1 as proto,
    qore_native_g1_six_e1_original_event_pair_quote_source_v1 as source,
)

IDENTITY = "QORE_NATIVE_G1_ORIGINAL_E1_SIX_PAIR_NATIVE_PROTO_SOURCE_SECOND_QA_V1"
SOURCE_RUN = 38293565282
SOURCE_ARTIFACT = 11767003876
SOURCE_HEAD = "7b7cd8339a4a1d135f531db90fd3931213708de4"
SOURCE_ZIP_SHA256 = "01075ecd534de104caf4fb8702aebef86468b611aafb5fcec366722ac12eea9b"
EXPECTED_ORIGINAL_E1_ROWS = 6


def _witness_original_side(
    folder: Path, canonical: str, day: str, clock: str, side: str, meta: dict,
) -> list[tuple[int, int]]:
    prefix = f"{canonical}-{day}-{clock}-{side}"
    expected = {
        "wire_file":prefix+"-proto-fields.pbframes",
        "int_file":prefix+"-integer.jsonl",
        "decimal_file":prefix+"-decimal.jsonl",
    }
    if any(meta.get(key) != name for key,name in expected.items()):
        raise ValueError("E1_PAIR_SOURCE_EXPECTED_PROTO_FILE_IDENTITY_DRIFT")
    raw={}
    for key,name in expected.items():
        raw[key]=(folder/name).read_bytes()
    if any(proto.digest(raw[key]) != meta.get(key.replace("_file","_sha256")
             .replace("wire_sha256","wire_sha256")
             .replace("int_sha256","int_sha256")
             .replace("decimal_sha256","decimal_sha256"))
           for key in expected):
        raise ValueError("E1_PAIR_SOURCE_SHA_BYTE_DRIFT")
    first,last=source.source_period(day,clock)
    if (meta.get("start_utc_ms_inclusive") != first
            or meta.get("end_utc_ms_exclusive") != last
            or meta.get("wire_field_protobuf_account_wrapper_archived") is not False):
        raise ValueError("E1_PAIR_SOURCE_CLOCK_OR_SECRET_BOUNDARY_DRIFT")
    pages=meta.get("pages")
    count=meta.get("provider_requests")
    if (not isinstance(pages,list) or not pages or type(count) is not int
            or len(pages) != count or count > 64):
        raise ValueError("E1_PAIR_SOURCE_HASMORE_PAGE_COUNT_INVALID")
    expected_ranges=[(first,last-1)]
    offset=0
    events=[]
    wire=raw["wire_file"]
    for page in pages:
        if not expected_ranges:
            raise ValueError("E1_PAIR_SOURCE_EXTRA_PAGE")
        a,b=expected_ranges.pop()
        if (page.get("from_ms") != a or page.get("to_ms") != b
                or type(page.get("has_more")) is not bool
                or page.get("accepted_leaf") is not (not page["has_more"])):
            raise ValueError("E1_PAIR_SOURCE_PAGE_HASMORE_BOUNDARY_INVALID")
        length=page.get("wire_length")
        if (type(length) is not int or length<0
                or page.get("wire_offset") != offset or offset+length>len(wire)):
            raise ValueError("E1_PAIR_SOURCE_PAGE_WIRE_FRAME_BOUNDARY_INVALID")
        payload=wire[offset:offset+length]
        offset+=length
        if proto.digest(payload)!=page.get("wire_section_sha256"):
            raise ValueError("E1_PAIR_SOURCE_PAGE_SECTION_SHA_INVALID")
        decoded=proto.decode_batch_fields(payload,a,b)
        if len(decoded)!=page.get("tick_count"):
            raise ValueError("E1_PAIR_SOURCE_PAGE_NATIVE_PROTODATA_COUNT_DRIFT")
        if page["has_more"]:
            if a == b:
                raise ValueError("E1_PAIR_SOURCE_SAME_MS_UNPAGEABLE")
            middle=(a+b)//2
            expected_ranges.extend(((middle+1,b),(a,middle)))
        else:
            events.extend(decoded)
    if offset != len(wire) or expected_ranges:
        raise ValueError("E1_PAIR_SOURCE_INCOMPLETE_OR_EXTRA_ORIGINAL_FIELDS")
    events.sort(key=lambda x:(x[0],x[1]))
    ints=[json.loads(x) for x in raw["int_file"].splitlines()]
    norm=[json.loads(x) for x in raw["decimal_file"].splitlines()]
    if not events or len(events)!=meta.get("native_tick_count") or len(ints)!=len(events) or len(norm)!=len(events):
        raise ValueError("E1_PAIR_SOURCE_ORIGINAL_NATIVE_COUNT_MISMATCH")
    for n,((t,price),orig,dec) in enumerate(zip(events,ints,norm,strict=True)):
        if orig!={"epoch_ms":t,"integer_price_1e5":price}:
            raise ValueError("E1_PAIR_SOURCE_ORIGINAL_PROTO_INTEGER_MISMATCH")
        stamp=datetime.fromtimestamp(t/1000,tz=UTC).isoformat(timespec="milliseconds").replace("+00:00","Z")
        if (dec.get("event_time_utc") != stamp or dec.get("native_sequence") != n
                or Decimal(str(dec.get("price"))) != Decimal(price)/Decimal(100000)):
            raise ValueError("E1_PAIR_SOURCE_ORIGINAL_PROTO_DECIMAL_CLOCK_MISMATCH")
        if n and t==events[n-1][0] and price!=events[n-1][1]:
            raise ValueError("E1_PAIR_SOURCE_INTRA_MS_PRICE_ORDER_AMBIGUOUS")
    return events


def analyze(signed_E1: Path, original_native: Path) -> dict[str, Any]:
    top=proto.verify_register(original_native,"SOURCE_SHA256SUMS.txt",1)
    if set(top)!={"SOURCE_SIX_E1_EVENT_CLOCK_PAIR_MANIFEST_NOT_NET.json"}:
        raise ValueError("E1_PAIR_ORIGINAL_BROKER_SOURCE_MANIFEST_NOT_ATTESTED")
    source_manifest=json.loads(
        (original_native/"SOURCE_SIX_E1_EVENT_CLOCK_PAIR_MANIFEST_NOT_NET.json").read_bytes()
    )
    if (source_manifest.get("identity")!=source.IDENTITY
            or source_manifest.get("g0_sha")!=e1.G0_SOURCE_SHA
            or source_manifest.get("e1_source_run")!=e1.E1_SOURCE_RUN
            or source_manifest.get("e1_source_code_sha")!=e1.E1_CODE_SHA
            or source_manifest.get("broker")!="ICMARKETS_CTRADER_DEMO"
            or source_manifest.get("frozen_events") != [list(e) for e in source.EVENTS]
            or source_manifest.get("window_clocks") != {k:list(v) for k,v in source.CLOCKS.items()}
            or source_manifest.get("state")!="SIX_E1_EVENT_CLOCK_PAIRS_NATIVE_BIDASK_PRESENT_NO_NET"
            or source_manifest.get("fully_acquired_event_rows")!=6
            or source_manifest.get("original_CIBO_12_vs_current_broker_contract_homologated") is not False
            or source_manifest.get("historical_Net_authorized") is not False
            or source_manifest.get("certified_traders") !=0
            or source_manifest.get("trade_orders_sent")!=0
            or source_manifest.get("oauth_refresh_attempts")!=0):
        raise ValueError("E1_PAIR_SOURCE_ORIGINAL_SCIENTIFIC_CONTRACT_INVALID")
    folders={p.name for p in original_native.iterdir() if p.is_dir()}
    wanted={f"{sym}-{day}" for sym,_,day,_ in source.EVENTS}
    if folders!=wanted:
        raise ValueError("E1_PAIR_SOURCE_EXACT_SIX_FOLDERS_MISSING")
    proven={}
    for sym in sorted({x[0] for x in source.EVENTS}):
        source_events, evidence_sha=e1._verify_signed_e1(signed_E1/sym,sym)
        proven[sym]=(source_events,evidence_sha)
    aggregate=Counter()
    rows=[]
    for sym,provider,day,method in source.EVENTS:
        matches=[
            record for record in proven[sym][0]
            if record["method_id"]==method
            and record["research_entry_clock_utc"].startswith(day)
        ]
        if len(matches)!=1:
            raise ValueError("E1_PAIR_NOT_ONE_ACTUAL_SIGNED_E1_RESEARCH_OPPORTUNITY")
        genuine=matches[0]
        entry=datetime.fromisoformat(genuine["research_entry_clock_utc"]).astimezone(UTC)
        theoretical=datetime.fromisoformat(
            genuine["theoretical_m5_target_close_clock_utc"]
        ).astimezone(UTC)
        if (entry.hour!=13 or entry.minute!=0
                or theoretical!=entry+timedelta(hours=2)
                or theoretical.hour!=15 or theoretical.minute!=0):
            raise ValueError("E1_PAIR_SIGNED_METHOD_RESEARCH_CLOCK_WRONG")
        folder=original_native/f"{sym}-{day}"
        proto.verify_register(folder,"SHA256SUMS.txt",13)
        record=json.loads((folder/"E1_EVENT_SOURCE_MANIFEST_NOT_NET.json").read_bytes())
        if (record.get("canonical")!=sym or record.get("provider")!=provider
                or record.get("day")!=day or record.get("method")!=method
                or record.get("state")!="BOTH_E1_RESEARCH_CLOCK_SOURCE_WINDOWS_PRESENT_NO_NET"
                or record.get("both_windows_complete") is not True
                or type(record.get("provider_symbol_id")) is not int
                or record["provider_symbol_id"]<=0):
            raise ValueError("E1_PAIR_SOURCE_BROKER_SYMBOL_OR_METHOD_INVALID")
        by_clock={}
        for label,at in (("entry",entry),("theoretical_close",theoretical)):
            part=record["clocks"][label]
            if part.get("both_native_sides_nonempty") is not True:
                raise ValueError("E1_PAIR_SOURCE_BOTH_SIDES_NOT_PROVEN")
            bid=_witness_original_side(
                folder,sym,day,label,"BID",part["sides"]["BID"]
            )
            ask=_witness_original_side(
                folder,sym,day,label,"ASK",part["sides"]["ASK"]
            )
            # exact, no interpolation, no known future tick, zero/stale/crossed rejected
            quality=gate.decision_quality(int(at.timestamp()*1000),bid,ask)
            by_clock[label]={
                "source_quality":quality,
                "native_bid_ticks":len(bid),
                "native_ask_ticks":len(ask),
                "original_fields_independently_redecoded":True,
            }
            aggregate[f"{label}_{quality}"]+=1
            aggregate["source_tick_events_verified"]+=len(bid)+len(ask)
        eligible=all(
            by_clock[point]["source_quality"]=="OK_POSITIVE_BIDASK"
            for point in source.CLOCKS
        )
        aggregate["source_eligible_both_clocks"]+=int(eligible)
        rows.append({
            "canonical_symbol":sym,"current_provider_symbol":provider,
            "original_E1_method":method,
            "utc_event_date":day,
            "original_E1_opportunity_sha256":genuine["opportunity_sha256"],
            "research_entry_timestamp_utc":entry.isoformat(),
            "theoretical_M5_horizon_end_utc":theoretical.isoformat(),
            "current_broker_G0_contract_equivalent":False,
            "source_eligible_both_clocks_NO_NET":eligible,
            "clocks":by_clock,
            "outcomes_signs_or_pnl_exported":False,
            "real_broker_entry_or_exit_fills_measured":False,
        })
    if len(rows)!=EXPECTED_ORIGINAL_E1_ROWS or len({r["original_E1_opportunity_sha256"] for r in rows})!=6:
        raise ValueError("E1_PAIR_SIGNED_ORIGINAL_SIX_OPPORTUNITY_COUNT_INVALID")
    return {
        "identity":IDENTITY,"status":"G1_SIX_ORIGINAL_E1_RESEARCH_EVENT_SOURCE_PROTO_PAIR_QA_PASS_NO_NET",
        "source_original_run":SOURCE_RUN,"source_original_artifact_id":SOURCE_ARTIFACT,
        "source_original_head_sha":SOURCE_HEAD,"source_original_zip_sha256":SOURCE_ZIP_SHA256,
        "original_E1_source_run":e1.E1_SOURCE_RUN,"original_E1_code_sha":e1.E1_CODE_SHA,
        "signed_E1_archive_SHA_provenance":{s:val[1] for s,val in proven.items()},
        "source_original_proto_tick_fields_independently_redecoded":True,
        "original_E1_research_opportunities":EXPECTED_ORIGINAL_E1_ROWS,
        "source_eligible_both_clocks":aggregate["source_eligible_both_clocks"],
        "source_blocked_pairs":6-aggregate["source_eligible_both_clocks"],
        "source_tick_events_verified":aggregate["source_tick_events_verified"],
        "quality_counts":dict(sorted(aggregate.items())),
        "real_broker_contract_equivalence_proven":False,
        "real_order_fills_commissions_slippage_swaps_known":False,
        "historical_NET_authorized":False,"certified_traders":0,
        "event_results":rows,
    }


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("original_E1_signed_dir",type=Path)
    parser.add_argument("native_BIDASK_six_source",type=Path)
    parser.add_argument("report_only_folder",type=Path)
    args=parser.parse_args()
    report=analyze(args.original_E1_signed_dir,args.native_BIDASK_six_source)
    args.report_only_folder.mkdir(parents=True,exist_ok=True)
    path=args.report_only_folder/"G1_E1_SIX_REAL_RESEARCH_CLOCK_SOURCE_PROTO_ASOF_QA_NOT_NET.json"
    path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    (args.report_only_folder/"SHA256SUMS.txt").write_text(
        proto.digest(path.read_bytes())+"  "+path.name+"\n"
    )
    print(json.dumps({
        "status":report["status"],"events":report["original_E1_research_opportunities"],
        "source_eligible_both_clocks":report["source_eligible_both_clocks"],
        "source_blocked":report["source_blocked_pairs"],
        "source_tick_events_verified":report["source_tick_events_verified"],
        "quality_counts":report["quality_counts"],"NET":False,"certified":0,
    },sort_keys=True))


if __name__ == "__main__":
    main()
