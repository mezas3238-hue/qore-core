"""Single 45-second NZDUSD read-only cTrader DEMO *prospective* spot source.

Collector first-seen times are assigned only AFTER asynchronous event dequeue.
No historical timestamp may be substituted for receive time. NO ORDER METHODS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from time import monotonic

from qore.infrastructure.trader_lab import cibo_market_atlas_10y_m5_consumer_v1 as original
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    probe_catalog,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m5_capture_v1 import (
    _ReadOnlyIcMarketsHistoryClient,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_ALPHA2_G2_ICMARKETS_DEMO_NZDUSD_FORWARD_RECEIPT_V1"
SYMBOL = "NZDUSD"
DURATION_SECONDS = 45
MAX_SIDE_AGE = timedelta(seconds=5)
MAX_ROWS = 15000
SUCCESS = "FORWARD_RECEIVED_NZDUSD_DEMO_SPOT_SOURCE_PRESENT"
BLOCKED = "FORWARD_DEMO_SPOT_SOURCE_BLOCKED_NO_NET"


class SourceBlockedError(ValueError):
    pass


class ReadOnlySpotClient(_ReadOnlyIcMarketsHistoryClient):
    _HISTORY_ONLY_REQUEST_NAMES = (
        _ReadOnlyIcMarketsHistoryClient._HISTORY_ONLY_REQUEST_NAMES
        | frozenset({"ProtoOASubscribeSpotsReq"})
    )

    def __init__(self, *, credentials):
        super().__init__(credentials=credentials, request_timeout_seconds=25.0)
        proto = import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        for name in ("ProtoOASubscribeSpotsReq", "ProtoOASubscribeSpotsRes",
                     "ProtoOASpotEvent"):
            klass = getattr(proto, name, None)
            if not isinstance(klass, type):
                raise SourceBlockedError("SPOT_DEMO_SDK_READONLY_MESSAGE_MISSING")
            self._bindings.messages[name] = klass


def _optional_present_integer(event: object, field: str) -> int | None:
    check = getattr(event, "HasField", None)
    if callable(check):
        try:
            if check(field) is False:
                return None
        except (TypeError, ValueError):
            raise SourceBlockedError("SPOT_FIELD_PRESENCE_UNVERIFIED") from None
    value = getattr(event, field, None)
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise SourceBlockedError("SPOT_FIELD_INTEGER_INVALID")
    if value == 0:
        return None
    return value


def normalize_spot_event(
    event: object, *, expected_symid: int, received_at: datetime,
    sequence: int,
) -> dict:
    if type(expected_symid) is not int or expected_symid <= 0:
        raise SourceBlockedError("BROKER_SYMBOL_SCOPE_INVALID")
    if getattr(event, "symbolId", None) != expected_symid:
        raise SourceBlockedError("BROKER_SPOT_SYMBOL_ID_CHANGED")
    if (type(received_at) is not datetime or received_at.tzinfo is None
            or received_at.utcoffset() != timedelta(0)):
        raise SourceBlockedError("SPOT_FIRST_SEEN_CLOCK_NOT_UTC")
    bid = _optional_present_integer(event, "bid")
    ask = _optional_present_integer(event, "ask")
    event_at_ms = _optional_present_integer(event, "timestamp")
    if event_at_ms is not None:
        try:
            event_at = datetime.fromtimestamp(event_at_ms / 1000, tz=UTC)
        except (OSError, OverflowError, ValueError):
            raise SourceBlockedError("SPOT_PROVIDER_EVENT_CLOCK_INVALID") from None
        if event_at > received_at:
            raise SourceBlockedError("SPOT_EVENT_IN_FUTURE_RELATIVE_TO_RECEIPT")
    if bid is None and ask is None:
        raise SourceBlockedError("SPOT_SIDE_VALUES_ABSENT")
    return {
        "sequence":sequence,
        "source_symbol":SYMBOL,
        "first_observed_by_runner_utc":received_at.isoformat(),
        "provider_event_at_ms":event_at_ms,
        "native_bid_1e5":bid, "native_ask_1e5":ask,
        "event_is_NOT_fill":True,
    }


def classify_received_pair(
    *, bid: int | None, ask: int | None,
    bid_seen: datetime | None, ask_seen: datetime | None,
    now: datetime,
) -> str:
    if (bid is None or ask is None or bid_seen is None or ask_seen is None
            or now - bid_seen > MAX_SIDE_AGE or now - ask_seen > MAX_SIDE_AGE):
        return "MISSING_OR_STALE_BIDASK"
    if bid <= 0 or ask <= 0:
        raise SourceBlockedError("INVALID_DEMO_BIDASK_PRICE")
    if ask < bid:
        return "CROSSED_QUOTE_QUARANTINED"
    if ask == bid:
        return "ZERO_QUOTE_QUARANTINED"
    return "POSITIVE_SPREAD_OBSERVATION_NO_FILL"


def _preflight_exact_demo_symbol() -> tuple[int, int]:
    proof=probe_catalog()
    if (proof.get("status")!="ICMARKETS_DEMO_CATALOG_VERIFIED"
            or proof.get("account_is_live") is not False
            or proof.get("broker_identity_verified_from_account") is not True
            or proof.get("token_refreshed") is not False):
        raise SourceBlockedError("EXACT_ICMARKETS_DEMO_SOURCE_NOT_VERIFIED")
    row=proof.get("catalog",{}).get("catalog_exact_matches",{}).get(SYMBOL)
    if (row is None or SYMBOL not in proof["catalog"]["available_exact"]
            or row.get("broker_symbol")!=SYMBOL
            or row.get("enabled") is not True
            or type(row.get("symbol_id")) is not int
            or row["symbol_id"]<=0):
        raise SourceBlockedError("DEMO_NZDUSD_EXACT_SYMBOL_NOT_ENABLED")
    account=proof.get("_ephemeral_account_id")
    if type(account) is not int or account <= 0:
        raise SourceBlockedError("DEMO_EPHEMERAL_ACCOUNT_NOT_VERIFIED")
    return account,row["symbol_id"]


def _capture(output: Path) -> dict:
    account,symid=_preflight_exact_demo_symbol()
    os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"]=str(account)
    os.environ.pop("QORE_CTRADER_ACCOUNT_ID",None)
    client=ReadOnlySpotClient(credentials=original._credentials())
    rows=[]
    last_bid=last_ask=None
    bid_seen=ask_seen=None
    last_received=None
    classes={}
    try:
        ready=client.connect_and_authenticate()
        if isinstance(ready,Failure) or client.account_id!=account:
            raise SourceBlockedError("DEMO_SOURCE_SESSION_NOT_AUTHENTICATED")
        subscribed=client.request(
            "ProtoOASubscribeSpotsReq",
            {"ctidTraderAccountId":account,"symbolId":[symid],
             "subscribeToSpotTimestamp":True},
            client_msg_id="alpha2-g2-demoonly-nzdusd-subscribe",
            timeout_seconds=30.0,
        )
        if (isinstance(subscribed,Failure)
                or not isinstance(subscribed.value,
                                  client._bindings.messages["ProtoOASubscribeSpotsRes"])):
            raise SourceBlockedError("DEMO_SUBSCRIBE_SPOTS_REQUEST_BLOCKED")
        started=monotonic()
        while monotonic()-started<DURATION_SECONDS:
            remaining=DURATION_SECONDS-(monotonic()-started)
            event=client.wait_for_event(
                "ProtoOASpotEvent",
                timeout_seconds=min(2.0,max(0.01,remaining)),
                predicate=lambda row: getattr(row,"symbolId",None)==symid,
            )
            if isinstance(event,Failure):
                continue
            received_at=datetime.now(UTC)  # after event dequeue: conservative first-seen
            if last_received is not None and received_at < last_received:
                raise SourceBlockedError("FIRST_SEEN_LOCAL_CLOCK_REVERSED")
            last_received=received_at
            raw=normalize_spot_event(
                event.value,expected_symid=symid,received_at=received_at,
                sequence=len(rows),
            )
            if raw["native_bid_1e5"] is not None:
                last_bid=raw["native_bid_1e5"]
                bid_seen=received_at
            if raw["native_ask_1e5"] is not None:
                last_ask=raw["native_ask_1e5"]
                ask_seen=received_at
            state=classify_received_pair(
                bid=last_bid,ask=last_ask,bid_seen=bid_seen,
                ask_seen=ask_seen,now=received_at,
            )
            raw["current_side_freshness_class"]=state
            classes[state]=classes.get(state,0)+1
            rows.append(raw)
            if len(rows)>MAX_ROWS:
                raise SourceBlockedError("DEMO_SPOT_EVENT_RATE_BUDGET_EXCEEDED")
    finally:
        client.close()
    if not rows or not any(r["native_bid_1e5"] is not None for r in rows) or not any(
        r["native_ask_1e5"] is not None for r in rows
    ):
        raise SourceBlockedError("DEMO_NO_BOTH_SIDES_OBSERVED")
    destination=output/"nzdusd-demo-forward-first-seen-spot-events.jsonl"
    with destination.open("w",encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
    return {
        "source_observation_state":SUCCESS,
        "native_provider_symbol_id":symid,
        "received_events":len(rows),
        "both_sides_seen_nonzero":True,
        "observed_classifications":classes,
        "first_collector_utc":rows[0]["first_observed_by_runner_utc"],
        "last_collector_utc":rows[-1]["first_observed_by_runner_utc"],
        "original_spot_events_sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
    }


def execute(output: Path) -> dict:
    output.mkdir(parents=True,exist_ok=True)
    result={
        "identity":IDENTITY,
        "status":BLOCKED,
        "duration_seconds_fixed":DURATION_SECONDS,
        "account_type":"DEMO", "broker":"ICMARKETS_CTRADER",
        "symbol":SYMBOL,
        "broker_account_or_token_persisted":False,
        "orders_sent":0,"token_refresh_attempts":0,
        "historical_2026_price_holdout_unsealed":False,
        "historical_available_at_proven":False,
        "actual_execution_fill_proven":False,
        "NET_certified":False,
    }
    try:
        result.update(_capture(output))
        result["status"]=SUCCESS
    except Exception as exc:  # sanitized, never emit untrusted provider/token errors
        codes={
            "EXACT_ICMARKETS_DEMO_SOURCE_NOT_VERIFIED",
            "DEMO_NZDUSD_EXACT_SYMBOL_NOT_ENABLED",
            "DEMO_EPHEMERAL_ACCOUNT_NOT_VERIFIED",
            "DEMO_SOURCE_SESSION_NOT_AUTHENTICATED",
            "DEMO_SUBSCRIBE_SPOTS_REQUEST_BLOCKED",
            "DEMO_NO_BOTH_SIDES_OBSERVED",
            "SPOT_DEMO_SDK_READONLY_MESSAGE_MISSING",
            "SPOT_FIELD_PRESENCE_UNVERIFIED",
            "SPOT_FIELD_INTEGER_INVALID",
            "SPOT_PROVIDER_EVENT_CLOCK_INVALID",
            "SPOT_EVENT_IN_FUTURE_RELATIVE_TO_RECEIPT",
            "SPOT_SIDE_VALUES_ABSENT",
            "BROKER_SPOT_SYMBOL_ID_CHANGED",
            "FIRST_SEEN_LOCAL_CLOCK_REVERSED",
            "DEMO_SPOT_EVENT_RATE_BUDGET_EXCEEDED",
        }
        msg=str(exc) if type(exc) is SourceBlockedError else ""
        result["safe_blocker"]=msg if msg in codes else "PROSPECTIVE_SOURCE_UNAVAILABLE_SAFE"
    report=output/"alpha2-g2-nzdusd-prospective-demo-source-manifest.json"
    report.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    ledgers=[]
    for name in sorted(output.glob("*.json*")):
        ledgers.append(hashlib.sha256(name.read_bytes()).hexdigest()+"  "+name.name)
    (output/"SOURCE_SHA256SUMS.txt").write_text("\n".join(ledgers)+"\n",encoding="utf-8")
    return result


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    a=p.parse_args()
    d=execute(a.output)
    print(json.dumps({"status":d["status"],
                      "safe_blocker":d.get("safe_blocker"),
                      "received_events":d.get("received_events",0),
                      "no_order":True, "NET":"BLOCKED"},sort_keys=True))
    if d["status"]!=SUCCESS:
        raise SystemExit(4)


if __name__=="__main__":
    main()
