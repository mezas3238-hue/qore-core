"""Independent G2 29 exact cTrader DEMO live-firstseen quote source SHA audit.

Original source is immutable GitHub Actions artifact, no source API calls.
Independent quality reconstructs both quote sides and global receipt order.
Never emit raw source quote prices or authorize broker orders / net metrics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.research.alpha2_g2_29_real_bidask_reuse import SOURCE_29

SOURCE_HEAD = "33068c720fedb3d358a2f73e7323508abd8365f6"
ORIGINAL_RUN = 38298399112
SOURCE_ID = "QORE_ALPHA2_G2_29_EXACT_DEMO_SPOT_60SEC_FIRSTRECEIPT_V1"
SOURCE_PASS = "G2_29_EXACT_DEMO_FORWARD_FIRSTRECEIPT_SOURCE_PRESENT_NOT_EXECUTION"
STATUS = "G2_29_DEMO_FIRSTRECEIPT_ORIGINAL_SHA_AND_SIDE_QA_PASS_NOT_NET"
MANIFEST = "alpha2-g2-29-exact-demo-spot-forward-source-manifest.json"
ORIGINAL_SHA = "ORIGINAL_SHA256SUMS.txt"
COMPLETE_SHA = "COMPLETE_SHA256SUMS.txt"
CODE_HEAD = "exact-code-head-sha.txt"
FIELDS = {
    "source_symbol", "global_sequence", "symbol_sequence",
    "first_observed_by_runner_utc","provider_event_at_ms",
    "native_bid_1e5","native_ask_1e5",
    "trade_fill_verified","source_quote_quality",
}
QUALITY = {
    "MISSING_OR_STALE_SIDE",
    "CROSSED_SPREAD_NO_FILL",
    "ZERO_SPREAD_NO_FILL",
    "POSITIVE_SPREAD_SOURCE_ONLY",
}
MAX_AGE = timedelta(seconds=5)


def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def _ledger(path: Path, required: set[str]) -> dict[str,str]:
    witness={}
    for line in path.read_text(encoding="utf-8").splitlines():
        pair=line.strip().split()
        if (len(pair)!=2 or pair[1] in witness or "/" in pair[1]
                or ".." in pair[1]):
            raise ValueError("29_ORIGINAL_SOURCE_SHA_LEDGER_INVALID")
        witness[pair[1]]=pair[0]
    if set(witness)!=required:
        raise ValueError("29_ORIGINAL_SOURCE_SHA_FILE_SCOPE_CHANGED")
    return witness


def _utc(value: Any) -> datetime:
    if type(value) is not str:
        raise ValueError("COLLECTOR_FIRST_SEEN_CLOCK_NOT_A_STRING")
    try:
        parsed=datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("COLLECTOR_FIRST_SEEN_CLOCK_MALFORMED") from None
    if parsed.tzinfo is None or parsed.utcoffset()!=timedelta(0):
        raise ValueError("COLLECTOR_FIRST_SEEN_NOT_UTC")
    return parsed


def _quality_reconstruct(entries: list[dict]) -> dict:
    if not entries:
        raise ValueError("29_SOURCE_ZERO_COLLECTOR_EVENTS")
    last_bid={sym:None for sym in SOURCE_29}
    last_ask={sym:None for sym in SOURCE_29}
    last_bid_time={sym:None for sym in SOURCE_29}
    last_ask_time={sym:None for sym in SOURCE_29}
    per_market={
        s:{"bid_updates":0,"ask_updates":0,"event_count":0,
           "state_counts":Counter(),"first_observed_utc":None,"last_observed_utc":None}
        for s in sorted(SOURCE_29)
    }
    first=None
    prev=None
    source_timestamp_count=0
    for sequence,row in enumerate(entries):
        if not isinstance(row,dict) or set(row)!=FIELDS:
            raise ValueError("29_SOURCE_EVENT_SCHEMA_INVALID")
        name=row["source_symbol"]
        if (name not in SOURCE_29
                or type(row["global_sequence"]) is not int
                or row["global_sequence"]!=sequence
                or type(row["symbol_sequence"]) is not int
                or row["symbol_sequence"]!=per_market[name]["event_count"]
                or row["trade_fill_verified"] is not False):
            raise ValueError("29_SOURCE_SYMBOL_OR_RECEIPT_SEQUENCE_INVALID")
        now=_utc(row["first_observed_by_runner_utc"])
        if prev is not None and now < prev:
            raise ValueError("29_SOURCE_RECEIPT_CLOCK_REVERSED")
        first=now if first is None else first
        prev=now
        publisher=row["provider_event_at_ms"]
        if publisher is not None:
            if type(publisher) is not int or publisher<=0:
                raise ValueError("29_SOURCE_PROVIDER_CLOCK_TYPE_INVALID")
            try:
                provider_at=datetime.fromtimestamp(publisher/1000,tz=UTC)
            except (OSError,OverflowError,ValueError):
                raise ValueError("29_SOURCE_PROVIDER_CLOCK_OUT_OF_RANGE") from None
            if provider_at > now:
                raise ValueError("29_SOURCE_PROVIDER_EVENT_NOT_YET_RECEIVED")
            source_timestamp_count+=1
        bid=row["native_bid_1e5"]
        ask=row["native_ask_1e5"]
        for side,value in (("BID",bid),("ASK",ask)):
            if value is not None and (type(value) is not int or value<=0):
                raise ValueError(f"29_SOURCE_NATIVE_{side}_INVALID")
        if bid is None and ask is None:
            raise ValueError("29_SOURCE_EVENT_WITHOUT_BID_OR_ASK")
        stats=per_market[name]
        if bid is not None:
            stats["bid_updates"]+=1
            last_bid[name]=bid
            last_bid_time[name]=now
        if ask is not None:
            stats["ask_updates"]+=1
            last_ask[name]=ask
            last_ask_time[name]=now
        if (last_bid[name] is None or last_ask[name] is None
                or last_bid_time[name] is None or last_ask_time[name] is None
                or now-last_bid_time[name]>MAX_AGE
                or now-last_ask_time[name]>MAX_AGE):
            state="MISSING_OR_STALE_SIDE"
        elif last_bid_time[name]>now or last_ask_time[name]>now:
            raise ValueError("29_SOURCE_SIDE_RECEIPT_FROM_FUTURE")
        elif last_ask[name]<last_bid[name]:
            state="CROSSED_SPREAD_NO_FILL"
        elif last_ask[name]==last_bid[name]:
            state="ZERO_SPREAD_NO_FILL"
        else:
            state="POSITIVE_SPREAD_SOURCE_ONLY"
        if state != row["source_quote_quality"] or state not in QUALITY:
            raise ValueError("29_SOURCE_SIDE_QUALITY_RECONSTRUCTION_DIFFERENT")
        stats["state_counts"][state]+=1
        stats["event_count"]+=1
        stats["first_observed_utc"]=stats["first_observed_utc"] or now.isoformat()
        stats["last_observed_utc"]=now.isoformat()
    if first is None or prev is None or prev-first>timedelta(seconds=65):
        raise ValueError("29_SOURCE_SESSION_BUDGET_CHANGED")
    for record in per_market.values():
        record["state_counts"]=dict(record["state_counts"])
    return {
        "all_event_count":len(entries),
        "publisher_timestamp_events":source_timestamp_count,
        "first_dequeued_utc":first.isoformat(),
        "last_dequeued_utc":prev.isoformat(),
        "source_receive_duration_seconds":(prev-first).total_seconds(),
        "markets_bid_and_ask":sum(
            z["bid_updates"]>0 and z["ask_updates"]>0 for z in per_market.values()
        ),
        "by_market":per_market,
    }


def inspect_original(root: Path) -> dict:
    quote_files={f"firstrecv-{s}-spot-events.jsonl" for s in SOURCE_29}
    original_set=quote_files|{MANIFEST}
    total_set=original_set|{CODE_HEAD}
    expected_files=total_set|{ORIGINAL_SHA,COMPLETE_SHA}
    if {p.name for p in root.iterdir() if p.is_file()}!=expected_files:
        raise ValueError("29_FORWARD_ARTIFACT_EXACT_FILE_SCOPE_CHANGED")
    source_ledger=_ledger(root/ORIGINAL_SHA,original_set)
    complete_ledger=_ledger(root/COMPLETE_SHA,total_set)
    for filename,h in source_ledger.items():
        if complete_ledger[filename]!=h:
            raise ValueError("29_FORWARD_TWO_ORIGINAL_SHA_LEDGERS_CONTRADICT")
    for filename,h in complete_ledger.items():
        if _sha(root/filename)!=h:
            raise ValueError("29_FORWARD_SOURCE_SHA256_TAMPERED")
    if (root/CODE_HEAD).read_text(encoding="utf-8").strip()!=SOURCE_HEAD:
        raise ValueError("29_FORWARD_ORIGINAL_GITHUB_CODE_HEAD_CHANGED")
    manifest=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    if (manifest.get("identity")!=SOURCE_ID
            or manifest.get("status")!=SOURCE_PASS
            or manifest.get("target_market_count")!=29
            or manifest.get("requested_duration_seconds")!=60
            or manifest.get("provider")!="ICMARKETS_CTRADER_DEMO"
            or manifest.get("excluded_four_unverified_or_separate")!=[
                "NAS100","NZDUSD","SP500","XAGUSD"]
            or manifest.get("all_exact_symbols_verified") is not True
            or manifest.get("provider_symbol_ids_broker_verified") is not True
            or manifest.get("symbols_with_received_bid_and_ask")!=29
            or manifest.get("account_id_or_oauth_persisted") is not False
            or manifest.get("broker_orders_sent")!=0
            or manifest.get("refresh_token_attempts")!=0
            or manifest.get("G2_NET_CERTIFIED") is not False
            or manifest.get("UTC001_certified") is not False
            or manifest.get("historical_reserve_tick_values_unread") is not True
            or set(manifest.get("by_market",{}))!=SOURCE_29
            or set(manifest.get("by_market_source_witness",{}))!=SOURCE_29):
        raise ValueError("29_FORWARD_ROOT_IDENTITY_OR_NO_TRADING_STATUS_INVALID")
    all_events=[]
    for sym in sorted(SOURCE_29):
        name=f"firstrecv-{sym}-spot-events.jsonl"
        item=manifest["by_market_source_witness"][sym]
        if (item.get("original_file")!=name
                or item.get("sha256")!=source_ledger[name]
                or item.get("source_bytes")!=(root/name).stat().st_size):
            raise ValueError("29_FORWARD_PER_SYMBOL_SHA_IN_SOURCE_MANIFEST_INVALID")
        sym_events=[]
        for line in (root/name).read_text(encoding="utf-8").splitlines():
            try:
                sym_events.append(json.loads(line))
            except json.JSONDecodeError:
                raise ValueError("29_FORWARD_ORIGINAL_EVENT_JSON_MALFORMED") from None
        if any(v.get("source_symbol")!=sym for v in sym_events):
            raise ValueError("29_FORWARD_SYMBOL_WRONG_FILE")
        all_events.extend(sym_events)
    all_events.sort(key=lambda x:x.get("global_sequence",-1))
    stats=_quality_reconstruct(all_events)
    if (stats["all_event_count"]!=manifest.get("received_event_count")
            or stats["first_dequeued_utc"]!=manifest.get("session_first_dequeued_utc")
            or stats["last_dequeued_utc"]!=manifest.get("session_last_dequeued_utc")
            or stats["markets_bid_and_ask"]!=29):
        raise ValueError("29_FORWARD_ROOT_EVENT_SUMMARY_NOT_RECONCILED")
    for sym,row in stats["by_market"].items():
        original=manifest["by_market"][sym]
        for key in (
            "event_count","bid_updates","ask_updates",
            "first_observed_utc","last_observed_utc","state_counts",
        ):
            if row[key]!=original.get(key):
                raise ValueError("29_FORWARD_SYMBOL_QUALITY_OR_CLOCK_DISCREPANCY")
    aggregate=Counter()
    for row in stats["by_market"].values():
        aggregate.update(row["state_counts"])
    if sum(aggregate.values())!=stats["all_event_count"]:
        raise ValueError("29_FORWARD_ALL_EVENTS_NOT_CLASSIFIED")
    return {
        "identity":"QORE_ALPHA2_G2_29_DEMO_PROSPECTIVE_FIRSTRECEIPT_INDEPENDENT_QA",
        "status":STATUS,
        "original_source_run":ORIGINAL_RUN,
        "original_code_head":SOURCE_HEAD,
        "original_source_manifest_sha256":source_ledger[MANIFEST],
        "market_count":29,
        "event_count":stats["all_event_count"],
        "provider_timestamp_events":stats["publisher_timestamp_events"],
        "markets_with_two_sides":stats["markets_bid_and_ask"],
        "first_dequeued_utc":stats["first_dequeued_utc"],
        "last_dequeued_utc":stats["last_dequeued_utc"],
        "duration_seconds_observed":stats["source_receive_duration_seconds"],
        "quality_class_counts":dict(sorted(aggregate.items())),
        "per_market_quality_including_zero":stats["by_market"],
        "original_market_sha256":{
            name:source_ledger[name] for name in sorted(quote_files)
        },
        "raw_prices_republished":False,
        "source_is_app_dequeue_not_broker_fill":True,
        "full_33_provider_contracts_homologated":False,
        "continuous_historical_bidask_path_covered":False,
        "UTC001_certified":False,
        "broker_actual_NET_certified":False,
        "orders":0,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("original",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    d=inspect_original(a.original)
    a.out.mkdir(parents=True,exist_ok=True)
    target=a.out/"alpha2-g2-29-independent-forward-demospot-QA.json"
    target.write_text(json.dumps(d,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":d["status"],
        "markets":d["market_count"],
        "events":d["event_count"],
        "bidask_two_sided":d["markets_with_two_sides"],
        "quality":d["quality_class_counts"],
        "broker_net_certified":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
