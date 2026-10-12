"""W2/W3 frozen -> G2 EURCHF historical BID/ASK read-only source pilot.

No orders; no refresh; no LIVE login. Only 60 seconds in consumed 2023.
Historical ticks retrieved in 2026 do not prove decision-time availability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_market_atlas_10y_m5_consumer_v1 as original
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    probe_catalog,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m5_capture_v1 import (
    _ReadOnlyIcMarketsHistoryClient,
)
from qore.kernel.result import Failure

SYMBOL = "EURCHF"
START = datetime(2023, 6, 12, 12, 0, tzinfo=UTC)
END = START + timedelta(minutes=1)
START_MS = int(START.timestamp() * 1000)
END_MS = int(END.timestamp() * 1000)
PRICE_SCALE = 100000
MAX_DURATION_MS = 604800000
IDENTITY = "QORE_ALPHA2_G2_EURCHF_CTRADER_DEMO_HIST_TICKS_READONLY_V1"
BLOCKED = "HISTORICAL_DEMO_BIDASK_SOURCE_BLOCKED_NO_NET"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(2**20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_newest_first(
    tick_rows: list[tuple[int, int]],
    *,
    start_ms: int = START_MS, end_ms: int = END_MS,
) -> list[dict[str, int]]:
    """Official cTrader: first timestamp absolute-ms; rest backward deltas."""
    if (end_ms <= start_ms or end_ms-start_ms > MAX_DURATION_MS
            or not tick_rows):
        raise ValueError("BAD_WINDOW_OR_NO_HISTORIC_TICKS")
    previous: int | None = None
    previous_price: int | None = None
    chronological: list[dict[str, int]] = []
    for index, (stamp, signed_price) in enumerate(tick_rows):
        if type(stamp) is not int or type(signed_price) is not int:
            raise ValueError("BAD_CTRADER_TICK_TYPE_OR_PRICE")
        if index == 0:
            absolute, price = stamp, signed_price
        else:
            # cTrader returns newest first: timestamp and tick price are both
            # SIGNED deltas from previous reconstructed native record.
            if stamp > 0 or previous is None or previous_price is None:
                raise ValueError("BAD_CTRADER_SIGNED_DELTA")
            absolute = previous + stamp
            price = previous_price + signed_price
        if price <= 0:
            raise ValueError("BAD_CTRADER_TICK_TYPE_OR_PRICE")
        if not start_ms <= absolute < end_ms:
            raise ValueError("HISTORICAL_TICK_OUTSIDE_PRESET_WINDOW")
        if previous is not None and absolute > previous:
            raise ValueError("REVERSE_CHRONOLOGY_INCONSISTENT")
        previous, previous_price = absolute, price
        chronological.append({"provider_tick_at_ms": absolute,
                              "raw_tick_price_1e5": price})
    chronological.reverse()
    return chronological


def classify_pilot(
    *,
    bid_rows: list[tuple[int, int]], ask_rows: list[tuple[int, int]],
    bid_has_more: bool, ask_has_more: bool, broker_verified: bool,
) -> dict[str, Any]:
    if (not broker_verified or type(bid_has_more) is not bool
            or type(ask_has_more) is not bool):
        raise ValueError("BROKER_OR_PAGINATION_PROOF_MISSING")
    if bid_has_more or ask_has_more:
        raise ValueError("HISTORIC_TICKS_TRUNCATED_HAS_MORE")
    bids = decode_newest_first(bid_rows)
    asks = decode_newest_first(ask_rows)
    return {
        "bid": bids, "ask": asks,
        "bid_count": len(bids), "ask_count": len(asks),
        "bid_first_ms": bids[0]["provider_tick_at_ms"],
        "bid_last_ms": bids[-1]["provider_tick_at_ms"],
        "ask_first_ms": asks[0]["provider_tick_at_ms"],
        "ask_last_ms": asks[-1]["provider_tick_at_ms"],
    }


def _sdk_response_ticks(
    value: object, *, expected_account: int,
) -> tuple[list[tuple[int, int]], bool]:
    if getattr(value, "ctidTraderAccountId", None) != expected_account:
        raise ValueError("HISTORICAL_TICK_ACCOUNT_SCOPE_MISMATCH")
    is_init = getattr(value, "IsInitialized", None)
    if callable(is_init) and is_init() is not True:
        raise ValueError("SDK_TICK_RESPONSE_MISSING_REQUIRED_FIELDS")
    more = getattr(value, "hasMore", None)
    if type(more) is not bool:
        raise ValueError("SDK_PAGINATION_FLAG_NOT_BOOL")
    values = []
    for row in getattr(value, "tickData", ()):
        ts = getattr(row, "timestamp", None)
        p = getattr(row, "tick", None)
        if type(ts) is not int or type(p) is not int:
            raise ValueError("SDK_TICK_PAYLOAD_INVALID")
        values.append((ts,p))
    return values,more


def authenticated_probe() -> dict[str, Any]:
    proof = probe_catalog()
    if (proof.get("status") != "ICMARKETS_DEMO_CATALOG_VERIFIED"
            or proof.get("account_is_live") is not False
            or proof.get("token_refreshed") is not False
            or proof.get("broker_identity_verified_from_account") is not True):
        raise ValueError("EXACT_DEMO_BROKER_NOT_VERIFIED")
    catalog = proof["catalog"]
    row = catalog["catalog_exact_matches"].get(SYMBOL)
    if (SYMBOL not in catalog["available_exact"] or row is None
            or row.get("broker_symbol") != SYMBOL or row.get("enabled") is not True
            or type(row.get("symbol_id")) is not int or row["symbol_id"] <= 0):
        raise ValueError("EXACT_DEMO_EURCHF_SYMBOL_NOT_VERIFIED")
    account = proof["_ephemeral_account_id"]
    if type(account) is not int or account <= 0:
        raise ValueError("EPHEMERAL_DEMO_ACCOUNT_NOT_AUTHENTICATED")
    return {"account_id": account, "symbol_id":row["symbol_id"],
            "broker_label":proof["broker_label"]}


def request_historical_ticks() -> dict[str, Any]:
    proof = authenticated_probe()
    # Scoped to THIS isolated GitHub job; never persist or print account id.
    os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(proof["account_id"])
    os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
    client = _ReadOnlyIcMarketsHistoryClient(credentials=original._credentials(),
                                           request_timeout_seconds=25.0)
    try:
        proto = import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        for name in ("ProtoOAGetTickDataReq", "ProtoOAGetTickDataRes"):
            klass = getattr(proto, name, None)
            if not isinstance(klass, type):
                raise ValueError("SDK_HIST_TICKS_READONLY_MESSAGE_UNAVAILABLE")
            client._bindings.messages[name] = klass
        result = client.connect_and_authenticate()
        if isinstance(result, Failure):
            raise ValueError("EXACT_DEMO_SOURCE_REAUTH_BLOCKED")
        captured = {}
        for direction, typ in (("BID", 1), ("ASK", 2)):
            if END_MS - START_MS > MAX_DURATION_MS:
                raise ValueError("BIDASK_WINDOW_EXCEEDS_CTRADER_LIMIT")
            returned = client.request(
                "ProtoOAGetTickDataReq",
                {"ctidTraderAccountId":proof["account_id"],
                 "symbolId":proof["symbol_id"],
                 "type":typ,
                 "fromTimestamp":START_MS,
                 "toTimestamp":END_MS-1},
                client_msg_id="qore-alpha2-g2-"+direction.lower()+"-source",
                timeout_seconds=30.0,
            )
            if isinstance(returned, Failure):
                raise ValueError("CTRADER_HISTORICAL_"+direction+"_REQUEST_FAILED")
            if not isinstance(returned.value,
                              client._bindings.messages["ProtoOAGetTickDataRes"]):
                raise ValueError("HISTORICAL_"+direction+"_RESPONSE_NOT_RECOGNIZED")
            captured[direction] = _sdk_response_ticks(
                returned.value,expected_account=proof["account_id"]
            )
        verified = classify_pilot(
            bid_rows=captured["BID"][0], ask_rows=captured["ASK"][0],
            bid_has_more=captured["BID"][1],ask_has_more=captured["ASK"][1],
            broker_verified=True,
        )
        return verified
    finally:
        client.close()


def write_pilot(output: Path) -> dict[str, Any]:
    if not (START < END <= datetime(2024,9,17,tzinfo=UTC)
            and END-START <= timedelta(minutes=1)):
        raise ValueError("FROZEN_G2_EXPLORATORY_WINDOW_CHANGED")
    output.mkdir(parents=True,exist_ok=True)
    result: dict[str, Any] = {
        "identity":IDENTITY, "status":BLOCKED,
        "symbol":SYMBOL,
        "window_start_utc":START.isoformat(),
        "window_end_exclusive_utc":END.isoformat(),
        "broker_demo_identity_verified":False,
        "broker_account_id_or_access_token_persisted":False,
        "historical_quote_available_at_decision_verified":False,
        "downloaded_quote_timestamp_is_NOT_asof_availability":True,
        "has_more_pages_or_truncation_permitted":False,
        "orders_sent":0, "token_refreshed":False,
        "costs_commission_swap_slippage_macro_verified":False,
        "net_certified":False,"utc001_certified":False,
    }
    try:
        stats = request_historical_ticks()
        filenames = {}
        for typ in ("bid","ask"):
            path = output / f"eur-chf-one-minute-raw-{typ}.jsonl"
            with path.open("w",encoding="utf-8") as file:
                for point in stats[typ]:
                    file.write(json.dumps(point,sort_keys=True,separators=(",",":"))+"\n")
            filenames[typ] = {"name":path.name,"sha256":_sha(path),
                              "count":len(stats[typ]),
                              "earliest_ms":stats[f"{typ}_first_ms"],
                              "latest_ms":stats[f"{typ}_last_ms"]}
        result.update({
            "status":"TICK_HISTORY_ONE_MINUTE_READONLY_SOURCE_PRESENT",
            "broker_demo_identity_verified":True,
            "read_only_bidask":filenames,
            "historical_quote_available_at_decision_verified":False,
            "data_retrieved_at_utc":datetime.now(UTC).isoformat(),
        })
    except (ValueError,OSError,RuntimeError,ImportError,TypeError) as exc:
        whitelisted={
            "EXACT_DEMO_BROKER_NOT_VERIFIED",
            "EXACT_DEMO_EURCHF_SYMBOL_NOT_VERIFIED",
            "EPHEMERAL_DEMO_ACCOUNT_NOT_AUTHENTICATED",
            "SDK_HIST_TICKS_READONLY_MESSAGE_UNAVAILABLE",
            "EXACT_DEMO_SOURCE_REAUTH_BLOCKED",
            "CTRADER_HISTORICAL_BID_REQUEST_FAILED",
            "CTRADER_HISTORICAL_ASK_REQUEST_FAILED",
            "HISTORICAL_BID_RESPONSE_NOT_RECOGNIZED",
            "HISTORICAL_ASK_RESPONSE_NOT_RECOGNIZED",
            "HISTORIC_TICKS_TRUNCATED_HAS_MORE",
            "BAD_WINDOW_OR_NO_HISTORIC_TICKS",
            "HISTORICAL_TICK_OUTSIDE_PRESET_WINDOW",
            "HISTORICAL_TICK_ACCOUNT_SCOPE_MISMATCH",
            "SDK_TICK_RESPONSE_MISSING_REQUIRED_FIELDS",
            "SDK_PAGINATION_FLAG_NOT_BOOL",
            "SDK_TICK_PAYLOAD_INVALID",
        }
        code = str(exc) if type(exc) is ValueError else ""
        result["safe_blocker"] = (
            code if code in whitelisted else "AUTH_OR_SOURCE_UNAVAILABLE_SAFE_BLOCK"
        )
    manifest = output/"alpha2-g2-eurchf-historical-bidask-source-manifest.json"
    manifest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (output/"SOURCE_SHA256SUMS.txt").write_text(
        "".join(_sha(f)+"  "+f.name+"\n" for f in sorted(output.glob("*.json*"))),
        encoding="utf-8",
    )
    return result


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    args=p.parse_args()
    result=write_pilot(args.output)
    print("ALPHA2_G2_READONLY_SOURCE",result["status"],
          result.get("safe_blocker","NO_BLOCKER"))
    if result["status"] != "TICK_HISTORY_ONE_MINUTE_READONLY_SOURCE_PRESENT":
        raise SystemExit(3)


if __name__=="__main__":
    main()
