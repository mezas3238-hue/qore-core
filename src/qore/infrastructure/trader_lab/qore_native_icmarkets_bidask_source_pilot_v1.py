"""QORE Native research-only native BID/ASK feasibility on IC Markets DEMO.

Freeze: NZDUSD three ten-minute UTC windows, no PnL, orders, token refresh,
midpoint interpolation or 33-market source equivalence assumptions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from importlib import import_module
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import sleep
from typing import Any, Callable

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiConnectionError,
    CTraderOpenApiProtocolError,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import probe_catalog
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m1_capture_v1 import _credentials
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m5_capture_v1 import (
    _ReadOnlyIcMarketsHistoryClient,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_ICMARKETS_G1_PRE_NZDUSD_NATIVE_TICKS_V1"
SYMBOL = "NZDUSD"  # selected by pilot source availability, NEVER by PnL
FROZEN_WINDOWS = (
    ("2020-09-15T13:00:00+00:00", "2020-09-15T13:10:00+00:00"),
    ("2023-09-19T13:00:00+00:00", "2023-09-19T13:10:00+00:00"),
    ("2026-09-15T13:00:00+00:00", "2026-09-15T13:10:00+00:00"),
)
SIDES = {"BID": 1, "ASK": 2}
MAX_QUERIES_PER_SIDE = 64
MAX_WINDOW_MS = 604800000
SOURCE_M1_PILOT_RUN = 38262534602
SOURCE_G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"


class SourceBlock(ValueError):
    pass


class ReadOnlyTickPilot(_ReadOnlyIcMarketsHistoryClient):
    _HISTORY_ONLY_REQUEST_NAMES = _ReadOnlyIcMarketsHistoryClient._HISTORY_ONLY_REQUEST_NAMES | frozenset({
        "ProtoOAGetTickDataReq",
    })

    def __init__(self, *, credentials, request_timeout_seconds: float):
        super().__init__(credentials=credentials, request_timeout_seconds=request_timeout_seconds)
        # The historical M5/M1 base binding omitted tick messages by design.
        # Admit only documented official read-only tick Req/Res to THIS instance.
        sdk = import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
        for name in ("ProtoOAGetTickDataReq", "ProtoOAGetTickDataRes"):
            native = getattr(sdk, name, None)
            if not isinstance(native, type):
                raise SourceBlock("NATIVE_TICK_SDK_PROTO_UNAVAILABLE")
            self._bindings.messages[name] = native


def window_milliseconds(window: tuple[str, str]) -> tuple[int, int]:
    left, right = (datetime.fromisoformat(x) for x in window)
    if left.tzinfo != UTC or right.tzinfo != UTC:
        raise SourceBlock("SOURCE_WINDOW_NOT_UTC")
    a, b = int(left.timestamp() * 1000), int(right.timestamp() * 1000)
    if b <= a or b - a > MAX_WINDOW_MS:
        raise SourceBlock("SOURCE_WINDOW_BAD_RANGE")
    return a, b


def decode_native(raw: tuple[object, ...], begin: int, finish: int) -> list[tuple[int, int]]:
    """cTrader first ms is absolute; following ms are backwards deltas."""
    result: list[tuple[int, int]] = []
    previous: int | None = None
    for row in raw:
        millis, integer_price = getattr(row, "timestamp", None), getattr(row, "tick", None)
        if type(millis) is not int or type(integer_price) is not int or integer_price <= 0:
            raise SourceBlock("BAD_PROVIDER_TICK")
        if previous is None:
            now = millis
        else:
            if millis < 0:
                raise SourceBlock("NEGATIVE_TICK_DELTA")
            now = previous - millis
        if now < begin or now > finish or (previous is not None and now > previous):
            raise SourceBlock("TICK_TIME_OUTSIDE_QUERY")
        result.append((now, integer_price))
        previous = now
    return result


def complete_side(
    fetch: Callable[[int, int], dict[str, Any]], begin: int, finish: int,
) -> tuple[list[tuple[int, int]], int]:
    """Fail closed on hasMore and unpageable millisecond, retain every native tick."""
    if begin < 0 or finish < begin or finish - begin + 1 > MAX_WINDOW_MS:
        raise SourceBlock("QUERY_RANGE_INVALID")
    pending = [(begin, finish)]
    ticks: list[tuple[int, int]] = []
    queries = 0
    while pending:
        a, b = pending.pop()
        queries += 1
        if queries > MAX_QUERIES_PER_SIDE:
            raise SourceBlock("QUERY_BUDGET_EXCEEDED")
        payload = fetch(a, b)
        if type(payload.get("has_more")) is not bool:
            raise SourceBlock("MISSING_HASMORE")
        decoded = decode_native(tuple(payload.get("tick_data", ())), a, b)
        if payload["has_more"]:
            if a == b:
                raise SourceBlock("UNPAGEABLE_SAME_MS")
            middle = (a + b) // 2
            pending.extend(((middle + 1, b), (a, middle)))
        else:
            ticks.extend(decoded)
    ticks.sort(key=lambda x: (x[0], x[1]))
    return ticks, queries


def _native_fetch(
    client: ReadOnlyTickPilot, symid: int, side: int, begin: int, finish: int, sequence: int,
) -> dict[str, Any]:
    sleep(0.30)
    result = client.request(
        "ProtoOAGetTickDataReq",
        {"ctidTraderAccountId": client.account_id, "symbolId": symid,
         "type": side, "fromTimestamp": begin, "toTimestamp": finish},
        client_msg_id=f"qore-native-quote-{sequence}",
        timeout_seconds=35.0,
    )
    if isinstance(result, Failure):
        # Do not disclose untrusted provider text or credentials in an artifact.
        code = re.search(r"cTrader request rejected: ([A-Z][A-Z0-9_]{0,63})", str(result.error))
        if code:
            raise SourceBlock("NATIVE_TICK_PROVIDER_" + code.group(1))
        if isinstance(result.error, CTraderOpenApiConnectionError):
            raise SourceBlock("NATIVE_TICK_PROVIDER_TRANSPORT_FAILURE")
        if isinstance(result.error, CTraderOpenApiProtocolError):
            if "invalid cTrader request field" in str(result.error):
                raise SourceBlock("NATIVE_TICK_PROTOCOL_REQUEST_FIELD_INVALID")
            if "response could not be decoded" in str(result.error):
                raise SourceBlock("NATIVE_TICK_PROTOCOL_RESPONSE_UNDECODABLE")
            allowed_submessages = {
                "HISTORY_ONLY_MESSAGE_NOT_ALLOWED": "NATIVE_TICK_BLOCKED_ADAPTER_REQUEST_WHITELIST",
                "cTrader request message is not admitted by this runtime": "NATIVE_TICK_SDK_MESSAGE_NOT_ADMITTED",
                "cTrader request rejected:": "NATIVE_TICK_SERVER_ERROR_UNCLASSIFIED",
            }
            for signal, reason in allowed_submessages.items():
                if signal in str(result.error):
                    raise SourceBlock(reason)
            raise SourceBlock("NATIVE_TICK_PROVIDER_PROTOCOL_FAILURE")
        raise SourceBlock("NATIVE_TICK_PROVIDER_QUERY_FAILED")
    response = result.value
    if getattr(response, "ctidTraderAccountId", None) != client.account_id:
        raise SourceBlock("RESPONSE_ACCOUNT_CHANGED")
    return {"has_more": getattr(response, "hasMore", None),
            "tick_data": getattr(response, "tickData", ())}


def capture(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "identity": IDENTITY, "symbol": SYMBOL, "provider": "ICMARKETS_CTRADER_DEMO",
        "source_m1_provenance_run": SOURCE_M1_PILOT_RUN,
        "source_g0_sha256": SOURCE_G0_SHA, "windows_frozen_utc": FROZEN_WINDOWS,
        "status": "SOURCE_AUTH_OR_QUOTE_BLOCKED",
        "complete_bid_ask_windows": 0, "windows": [],
        "trading_orders_submitted": 0, "token_refresh_attempts": 0,
        "original_side_protobuf_attested_independently": False,
        "historical_33_market_coverage_verified": False,
        "historical_NET_authorized": False, "traders_certified": 0,
    }
    client: ReadOnlyTickPilot | None = None
    try:
        catalog = probe_catalog()
        if catalog.get("status") != "ICMARKETS_DEMO_CATALOG_VERIFIED":
            raise SourceBlock("DEMO_BROKER_PREFLIGHT_FAILED")
        symbols = catalog["catalog"]["catalog_exact_matches"]
        symbol = symbols.get(SYMBOL)
        if not isinstance(symbol, dict) or symbol.get("broker_symbol") != SYMBOL or symbol.get("enabled") is not True:
            raise SourceBlock("EXACT_NATIVE_SYMBOL_NOT_ENABLED")
        symid = symbol.get("symbol_id")
        account = catalog.get("_ephemeral_account_id")
        if type(symid) is not int or symid <= 0 or type(account) is not int or account <= 0:
            raise SourceBlock("INVALID_ACCOUNT_OR_SYMBOL_ID")
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(account)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
        client = ReadOnlyTickPilot(credentials=_credentials(), request_timeout_seconds=35.0)
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure) or client.account_id != account:
            raise SourceBlock("SOURCE_DEMO_ACCOUNT_AUTH_FAILED")
        result["verified_provider_symbol"] = SYMBOL
        result["provider_symbol_id"] = symid
        for index, window in enumerate(FROZEN_WINDOWS, 1):
            start, end = window_milliseconds(window)
            by_side: dict[str, dict[str, Any]] = {}
            for quote_side, side_code in SIDES.items():
                counter = [0]
                def one(a: int, b: int) -> dict[str, Any]:
                    counter[0] += 1
                    return _native_fetch(client, symid, side_code, a, b, index * 100 + side_code * 20 + counter[0])
                ticks, reqs = complete_side(one, start, end - 1)
                native_file = outdir / f"nzdusd-{index}-{quote_side}-integer.jsonl"
                decoded_file = outdir / f"nzdusd-{index}-{quote_side}-decoded.jsonl"
                native_rows = (json.dumps({"epoch_ms": at, "integer_price_1e5": price},
                                          sort_keys=True) for at, price in ticks)
                decoded_rows = (json.dumps({
                    "event_time_utc": datetime.fromtimestamp(at / 1000, tz=UTC)
                    .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                    "native_sequence": n,
                    "price": format(Decimal(price) / Decimal(100000), "f")},
                    sort_keys=True) for n, (at, price) in enumerate(ticks))
                native_file.write_text("\n".join(native_rows) + "\n", encoding="utf-8")
                decoded_file.write_text("\n".join(decoded_rows) + "\n", encoding="utf-8")
                by_side[quote_side] = {
                    "native_tick_count": len(ticks), "historical_provider_requests": reqs,
                    "native_int_file": native_file.name,
                    "native_int_sha256": hashlib.sha256(native_file.read_bytes()).hexdigest(),
                    "decoded_file": decoded_file.name,
                    "decoded_sha256": hashlib.sha256(decoded_file.read_bytes()).hexdigest(),
                }
            complete = all(by_side[side]["native_tick_count"] > 0 for side in SIDES)
            result["windows"].append({"utc_range": window, "by_side": by_side,
                                      "both_sides_nonempty": complete})
        result["complete_bid_ask_windows"] = sum(w["both_sides_nonempty"] for w in result["windows"])
        result["status"] = (
            "THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
            if result["complete_bid_ask_windows"] == 3
            else "PARTIAL_NATIVE_HISTORY_NOT_NET"
        )
    except (SourceBlock, OSError, TypeError, KeyError, RuntimeError, ValueError) as exc:
        reason = str(exc) if type(exc) is SourceBlock else ""
        result["safe_blocker"] = reason if reason.startswith((
            "DEMO_", "EXACT_", "INVALID_", "SOURCE_", "NATIVE_", "RESPONSE_", "QUERY_",
            "MISSING_", "UNPAGEABLE_", "BAD_", "NEGATIVE_", "TICK_"
        )) else "UNCLASSIFIED_AUTH_OR_PROVIDER_BLOCKER"
    finally:
        if client is not None:
            client.close()
        manifest = outdir / "native-quote-source-PILOT-NOT-NET.json"
        manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        files = sorted(p for p in outdir.iterdir() if p.is_file() and p.name != "OUTPUT_SHA256SUMS.txt")
        (outdir / "OUTPUT_SHA256SUMS.txt").write_text(
            "".join(hashlib.sha256(f.read_bytes()).hexdigest() + f"  {f.name}\n" for f in files),
            encoding="utf-8",
        )
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    result = capture(p.parse_args().output)
    print(json.dumps({"status": result["status"],
                      "complete": result["complete_bid_ask_windows"],
                      "blocker": result.get("safe_blocker"),
                      "NET": False}, sort_keys=True))
    if result["status"] != "THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
