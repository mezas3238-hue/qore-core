"""G2 29 exact-symbol cTrader DEMO 60sec BID/ASK first-receipt source pilot.

One read-only spot subscription on the same broker-confirmed account. No
orders, no OAuth refresh, no VPS, no strategy, no actual broker NET.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any

from qore.research.alpha2_g2_29_real_bidask_reuse import SOURCE_29
from qore.research.alpha2_g2_nzdusd_forward_spot_receipt import (
    SourceBlockedError,
    _optional_present_integer,
    _read_only_spot_client,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_ALPHA2_G2_29_EXACT_DEMO_SPOT_60SEC_FIRSTRECEIPT_V1"
WINDOW_SECONDS = 60
SIDE_MAX_AGE = timedelta(seconds=5)
MAX_EVENTS = 120000
SUCCESS = "G2_29_EXACT_DEMO_FORWARD_FIRSTRECEIPT_SOURCE_PRESENT_NOT_EXECUTION"
PARTIAL = "PARTIAL_29_FORWARD_SOURCE_BLOCKED_NOT_NET"


def classify(
    *, bid: int | None, ask: int | None,
    bid_at: datetime | None, ask_at: datetime | None,
    now: datetime,
) -> str:
    if (bid is None or ask is None or bid_at is None or ask_at is None
            or now - bid_at > SIDE_MAX_AGE or now - ask_at > SIDE_MAX_AGE):
        return "MISSING_OR_STALE_SIDE"
    if now < bid_at or now < ask_at:
        raise SourceBlockedError("FORWARD_SOURCE_SIDE_FROM_FUTURE")
    if bid <= 0 or ask <= 0:
        raise SourceBlockedError("FORWARD_SOURCE_NONPOSITIVE_PRICE")
    if ask < bid:
        return "CROSSED_SPREAD_NO_FILL"
    if ask == bid:
        return "ZERO_SPREAD_NO_FILL"
    return "POSITIVE_SPREAD_SOURCE_ONLY"


def _catalog_exact29() -> tuple[int, dict[str, int]]:
    from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
        probe_catalog,
    )

    proof = probe_catalog()
    if (proof.get("status")!="ICMARKETS_DEMO_CATALOG_VERIFIED"
            or proof.get("account_is_live") is not False
            or proof.get("broker_identity_verified_from_account") is not True
            or proof.get("token_refreshed") is not False):
        raise SourceBlockedError("BROKER_VERIFIED_DEMO_ONLY_SOURCE_UNAVAILABLE")
    account=proof.get("_ephemeral_account_id")
    if type(account) is not int or account<=0:
        raise SourceBlockedError("ORIGINAL_DEMO_ACCOUNT_NOT_VERIFIED")
    catalog=proof.get("catalog",{}).get("catalog_exact_matches",{})
    enabled=proof.get("catalog",{}).get("available_exact",())
    bysymbol={}
    for sym in sorted(SOURCE_29):
        row=catalog.get(sym)
        if (not isinstance(row,dict) or sym not in enabled
                or row.get("broker_symbol")!=sym
                or row.get("enabled") is not True
                or type(row.get("symbol_id")) is not int
                or row["symbol_id"]<=0):
            raise SourceBlockedError("29_EXACT_SYMBOLS_NOT_ALL_DEMO_ENABLED")
        bysymbol[sym]=row["symbol_id"]
    if len(bysymbol)!=29 or len(set(bysymbol.values()))!=29:
        raise SourceBlockedError("ORIGINAL_29_SYMBOL_ALIAS_OR_ID_DUPLICATE")
    return account,bysymbol


def _normalize(
    event: object, *, symbol: str, received_at: datetime, sequence: int,
    local_sequence: int,
) -> dict:
    if symbol not in SOURCE_29:
        raise SourceBlockedError("SPOT_EVENT_SYMBOL_OUTSIDE_FROZEN29")
    raw_bid = _optional_present_integer(event,"bid")
    raw_ask = _optional_present_integer(event,"ask")
    event_ms = _optional_present_integer(event,"timestamp")
    if raw_bid is None and raw_ask is None:
        raise SourceBlockedError("SPOT_MESSAGE_BOTH_PRICE_SIDES_MISSING")
    if event_ms is not None:
        try:
            source_at = datetime.fromtimestamp(event_ms/1000,tz=UTC)
        except (ValueError,OverflowError,OSError):
            raise SourceBlockedError("SPOT_PROVIDER_TIMESTAMP_INVALID") from None
        if source_at > received_at:
            raise SourceBlockedError("SPOT_PROVIDER_TIMESTAMP_AFTER_RECEIPT")
    return {
        "source_symbol":symbol,
        "global_sequence":sequence,
        "symbol_sequence":local_sequence,
        "first_observed_by_runner_utc":received_at.isoformat(),
        "provider_event_at_ms":event_ms,
        "native_bid_1e5":raw_bid,
        "native_ask_1e5":raw_ask,
        "trade_fill_verified":False,
    }


def _collect(output: Path) -> dict:
    account, symbols=_catalog_exact29()
    os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"]=str(account)
    os.environ.pop("QORE_CTRADER_ACCOUNT_ID",None)
    from qore.infrastructure.trader_lab import cibo_market_atlas_10y_m5_consumer_v1 as original

    client=_read_only_spot_client(original._credentials())
    stats={
        symbol:{
            "event_count":0,"bid_updates":0,"ask_updates":0,
            "first_observed_utc":None,"last_observed_utc":None,
            "state_counts":{},
        } for symbol in sorted(SOURCE_29)
    }
    last_bid={sym:None for sym in SOURCE_29}
    last_ask={sym:None for sym in SOURCE_29}
    bid_seen={sym:None for sym in SOURCE_29}
    ask_seen={sym:None for sym in SOURCE_29}
    first_global=None
    last_global=None
    count=0
    try:
        conn=client.connect_and_authenticate()
        if isinstance(conn,Failure) or client.account_id!=account:
            raise SourceBlockedError("DEMO_SOURCE_AUTHENTICATED_ACCOUNT_DIFFERENT")
        subscribed=client.request(
            "ProtoOASubscribeSpotsReq",
            {"ctidTraderAccountId":account,
             "symbolId":[symbols[name] for name in sorted(SOURCE_29)],
             "subscribeToSpotTimestamp":True},
            client_msg_id="alpha2-g2-29exact-demoonly-firstreceipt",
            timeout_seconds=30.0,
        )
        if (isinstance(subscribed,Failure)
                or not isinstance(subscribed.value,
                                  client._bindings.messages["ProtoOASubscribeSpotsRes"])):
            raise SourceBlockedError("DEMO_29_SPOT_SUBSCRIBE_NOT_ACKNOWLEDGED")
        id_to_symbol={id_:name for name,id_ in symbols.items()}
        with ExitStack() as stack:
            streams={
                sym:stack.enter_context(
                    (output/f"firstrecv-{sym}-spot-events.jsonl")
                    .open("w",encoding="utf-8")
                ) for sym in sorted(SOURCE_29)
            }
            started=monotonic()
            while monotonic()-started<WINDOW_SECONDS:
                remaining=WINDOW_SECONDS-(monotonic()-started)
                result=client.wait_for_event(
                    "ProtoOASpotEvent",
                    timeout_seconds=min(2.0,max(0.01,remaining)),
                )
                if isinstance(result,Failure):
                    continue
                now=datetime.now(UTC)
                if last_global is not None and now<last_global:
                    raise SourceBlockedError("FORWARD_COLLECTION_CLOCK_REVERSED")
                name=id_to_symbol.get(getattr(result.value,"symbolId",None))
                if name is None:
                    raise SourceBlockedError("DEMO_SPOT_PROVIDER_ID_UNRECOGNIZED")
                info=stats[name]
                raw=_normalize(
                    result.value,symbol=name,received_at=now,
                    sequence=count,local_sequence=info["event_count"],
                )
                if raw["native_bid_1e5"] is not None:
                    last_bid[name]=raw["native_bid_1e5"]
                    bid_seen[name]=now
                    info["bid_updates"]+=1
                if raw["native_ask_1e5"] is not None:
                    last_ask[name]=raw["native_ask_1e5"]
                    ask_seen[name]=now
                    info["ask_updates"]+=1
                state=classify(
                    bid=last_bid[name],ask=last_ask[name],
                    bid_at=bid_seen[name],ask_at=ask_seen[name],now=now,
                )
                raw["source_quote_quality"]=state
                info["state_counts"][state]=info["state_counts"].get(state,0)+1
                info["first_observed_utc"]=info["first_observed_utc"] or now.isoformat()
                info["last_observed_utc"]=now.isoformat()
                streams[name].write(json.dumps(raw,sort_keys=True,separators=(",",":"))+"\n")
                info["event_count"]+=1
                count+=1
                first_global=first_global or now
                last_global=now
                if count>MAX_EVENTS:
                    raise SourceBlockedError("DEMO_29_SOURCE_CAPTURE_BOUNDED_EVENTS_EXCEEDED")
    finally:
        client.close()
    observed_two_sided=sum(
        info["bid_updates"]>0 and info["ask_updates"]>0
        for info in stats.values()
    )
    return {
        "status":SUCCESS if observed_two_sided==29 else PARTIAL,
        "all_exact_symbols_verified":True,
        "provider_symbol_ids_broker_verified":True,
        "received_event_count":count,
        "symbols_with_received_bid_and_ask":observed_two_sided,
        "session_first_dequeued_utc":first_global.isoformat() if first_global else None,
        "session_last_dequeued_utc":last_global.isoformat() if last_global else None,
        "by_market":stats,
    }


def execute(output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=True)
    result: dict[str,Any]={
        "identity":IDENTITY,"status":PARTIAL,
        "target_market_count":29,
        "requested_duration_seconds":WINDOW_SECONDS,
        "provider":"ICMARKETS_CTRADER_DEMO",
        "excluded_four_unverified_or_separate":["NAS100","NZDUSD","SP500","XAGUSD"],
        "account_id_or_oauth_persisted":False,
        "refresh_token_attempts":0,"broker_orders_sent":0,
        "native_quote_source_not_execution":True,
        "historical_reserve_tick_values_unread":True,
        "G2_NET_CERTIFIED":False,"UTC001_certified":False,
    }
    try:
        result.update(_collect(output))
    except Exception as exc:  # exclude any untrusted error text from output
        allowed={
            "BROKER_VERIFIED_DEMO_ONLY_SOURCE_UNAVAILABLE",
            "ORIGINAL_DEMO_ACCOUNT_NOT_VERIFIED",
            "29_EXACT_SYMBOLS_NOT_ALL_DEMO_ENABLED",
            "ORIGINAL_29_SYMBOL_ALIAS_OR_ID_DUPLICATE",
            "DEMO_SOURCE_AUTHENTICATED_ACCOUNT_DIFFERENT",
            "DEMO_29_SPOT_SUBSCRIBE_NOT_ACKNOWLEDGED",
            "SPOT_EVENT_SYMBOL_OUTSIDE_FROZEN29",
            "DEMO_SPOT_PROVIDER_ID_UNRECOGNIZED",
            "FORWARD_COLLECTION_CLOCK_REVERSED",
            "DEMO_29_SOURCE_CAPTURE_BOUNDED_EVENTS_EXCEEDED",
            "SPOT_MESSAGE_BOTH_PRICE_SIDES_MISSING",
            "SPOT_PROVIDER_TIMESTAMP_AFTER_RECEIPT",
        }
        raw=str(exc) if type(exc) is SourceBlockedError else ""
        result["safe_blocker"]=raw if raw in allowed else "BROKER_DEMO_OR_PROTOCOL_SOURCE_BLOCKED"
    manifests={}
    for symbol in sorted(SOURCE_29):
        path=output/f"firstrecv-{symbol}-spot-events.jsonl"
        if path.exists():
            manifests[symbol]={
                "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "source_bytes":path.stat().st_size,
                "original_file":path.name,
            }
    result["by_market_source_witness"]=manifests
    doc=output/"alpha2-g2-29-exact-demo-spot-forward-source-manifest.json"
    doc.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    rows=[]
    for file in sorted(output.glob("*.json*")):
        rows.append(hashlib.sha256(file.read_bytes()).hexdigest()+"  "+file.name)
    (output/"ORIGINAL_SHA256SUMS.txt").write_text("\n".join(rows)+"\n",encoding="utf-8")
    return result


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("out",type=Path)
    args=p.parse_args()
    d=execute(args.out)
    print(json.dumps({
        "status":d["status"],
        "events":d.get("received_event_count",0),
        "markets_two_sided":d.get("symbols_with_received_bid_and_ask",0),
        "safe_blocker":d.get("safe_blocker"),
        "net_certified":False,"orders":0,
    },sort_keys=True))
    if d["status"]!=SUCCESS:
        raise SystemExit(4)


if __name__=="__main__":
    main()
