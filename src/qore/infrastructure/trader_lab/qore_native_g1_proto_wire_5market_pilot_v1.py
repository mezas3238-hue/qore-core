"""QORE Native source-only raw ProtoOATickData witness / two-window FX controls.

Research only, no trading requests. Persist provider tick-field Protobuf bytes
without ctidTraderAccountId or tokens, including hasMore-discarded pages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import sleep
from typing import Any

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiConnectionError, CTraderOpenApiProtocolError,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_bidask_source_pilot_v1 import (
    SIDES, ReadOnlyTickPilot, SourceBlock, complete_side, window_milliseconds,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import probe_catalog
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m1_capture_v1 import _credentials
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_G1_NATIVE_PROTO_WIRE_FIDELITY_V1"
TARGETS = {"EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY",
           "XAGUSD": "XAGUSD", "SP500": "US500"}
WINDOWS = (
    ("2021-03-16T13:00:00+00:00", "2021-03-16T13:30:00+00:00"),
    ("2023-03-21T13:00:00+00:00", "2023-03-21T13:30:00+00:00"),
)
PARENT_SOURCE_RUN = 38283737706
PARENT_G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
MAX_PER_SIDE = 100000
MAX_WIRE_BYTES_PER_MARKET = 30_000_000
MAX_SAFE_BLOCKER_LEN = 96


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _source_auth(catalog: dict[str, Any]) -> tuple[int, dict[str, int]]:
    if catalog.get("status") != "ICMARKETS_DEMO_CATALOG_VERIFIED":
        raise SourceBlock("ICMARKETS_DEMO_BROKER_NOT_VERIFIED")
    account = catalog.get("_ephemeral_account_id")
    if type(account) is not int or account <= 0 or catalog.get("account_is_live") is not False:
        raise SourceBlock("ICMARKETS_DEMO_ACCOUNT_NOT_VERIFIED")
    available = catalog.get("catalog", {}).get("catalog_exact_matches", {})
    symbols = {}
    for canonical, provider in TARGETS.items():
        item = available.get(provider)
        if (isinstance(item, dict) and item.get("broker_symbol") == provider
                and item.get("enabled") is True and type(item.get("symbol_id")) is int
                and item["symbol_id"] > 0):
            symbols[canonical] = item["symbol_id"]
    return account, symbols


def _safe_failure(exc: Exception) -> str:
    if isinstance(exc, SourceBlock):
        value = str(exc)
        if len(value) <= MAX_SAFE_BLOCKER_LEN and re.fullmatch(r"[A-Z][A-Z0-9_]+", value):
            return value
    return "SOURCE_PROVIDER_OR_PROTOCOL_BLOCKED"


def _history_response(client: ReadOnlyTickPilot, symbol_id: int,
                      side_type: int, first: int, last: int, sequence: int) -> dict:
    sleep(0.30)
    answer = client.request(
        "ProtoOAGetTickDataReq", {
            "ctidTraderAccountId": client.account_id,
            "symbolId": symbol_id, "type": side_type,
            "fromTimestamp": first, "toTimestamp": last,
        }, client_msg_id=f"qore-g1-original-tick-field-{sequence}",
        timeout_seconds=35.0,
    )
    if isinstance(answer, Failure):
        error = answer.error
        if isinstance(error, CTraderOpenApiConnectionError):
            raise SourceBlock("CTRADER_SOURCE_TRANSPORT_FAILURE")
        if isinstance(error, CTraderOpenApiProtocolError):
            code = re.search(r"cTrader request rejected: ([A-Z][A-Z0-9_]{0,63})", str(error))
            if code:
                raise SourceBlock("CTRADER_SOURCE_REJECTED_" + code.group(1))
            raise SourceBlock("CTRADER_SOURCE_PROTOCOL_FAILURE")
        raise SourceBlock("CTRADER_SOURCE_REQUEST_FAILURE")
    payload = answer.value
    if getattr(payload, "ctidTraderAccountId", None) != client.account_id:
        raise SourceBlock("CTRADER_SOURCE_ACCOUNT_MISMATCH")
    flag = getattr(payload, "hasMore", None)
    if type(flag) is not bool:
        raise SourceBlock("CTRADER_SOURCE_HASMORE_NOT_EXPLICIT")
    return {"has_more": flag, "tick_data": tuple(getattr(payload, "tickData", ()))}


def _store_side(
    client: ReadOnlyTickPilot, symbol_id: int, symbol: str,
    idx: int, side: str, outdir: Path,
) -> dict[str, Any]:
    start, end = window_milliseconds(WINDOWS[idx - 1])
    pages: list[dict[str, Any]] = []
    original_wire = bytearray()
    requests = [0]

    def fetch(a: int, b: int) -> dict:
        requests[0] += 1
        response = _history_response(
            client, symbol_id, SIDES[side], a, b, idx * 100_000 + SIDES[side] * 10_000 + requests[0],
        )
        raw_ticks = response["tick_data"]
        section = bytearray()
        for row in raw_ticks:
            if not hasattr(row, "SerializeToString"):
                raise SourceBlock("CTRADER_SOURCE_NATIVE_PROTO_MESSAGE_MISSING")
            # Serialize only tick fields; the response wrapper contains the account.
            blob = row.SerializeToString(deterministic=True)
            if len(blob) == 0 or len(blob) > 1_000:
                raise SourceBlock("CTRADER_SOURCE_PROTO_TICK_SIZE_INVALID")
            section.extend(struct.pack(">I", len(blob)))
            section.extend(blob)
        offset = len(original_wire)
        if offset + len(section) > MAX_WIRE_BYTES_PER_MARKET:
            raise SourceBlock("CTRADER_SOURCE_WIRE_BUDGET_EXCEEDED")
        original_wire.extend(section)
        pages.append({
            "from_ms": a, "to_ms": b, "has_more": response["has_more"],
            "accepted_leaf": response["has_more"] is False,
            "tick_count": len(raw_ticks),
            "wire_offset": offset, "wire_length": len(section),
            "wire_section_sha256": _sha(section),
            "no_account_wrapper_archived": True,
        })
        return response

    ticks, calls = complete_side(fetch, start, end - 1)
    if len(ticks) > MAX_PER_SIDE:
        raise SourceBlock("CTRADER_SOURCE_SIDE_TICK_BUDGET_EXCEEDED")
    prefix = f"{symbol}-{idx}-{side}"
    native = outdir / f"{prefix}-integer.jsonl"
    decimal = outdir / f"{prefix}-decimal.jsonl"
    wire = outdir / f"{prefix}-tick-fields.pbframes"
    native.write_text("".join(
        json.dumps({"epoch_ms": t, "integer_price_1e5": price}, sort_keys=True) + "\n"
        for t, price in ticks
    ), encoding="utf-8")
    decimal.write_text("".join(
        json.dumps({
            "event_time_utc": datetime.fromtimestamp(t/1000, tz=UTC)
            .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "native_sequence": n, "price": format(Decimal(price)/Decimal(100000), "f"),
        }, sort_keys=True) + "\n"
        for n, (t, price) in enumerate(ticks)
    ), encoding="utf-8")
    wire.write_bytes(original_wire)
    return {
        "count": len(ticks),
        "total_provider_requests": calls,
        "wire_tick_fields_only_account_wrapper_excluded": True,
        "native_file": native.name, "native_sha256": _sha(native.read_bytes()),
        "decimal_file": decimal.name, "decimal_sha256": _sha(decimal.read_bytes()),
        "wire_file": wire.name, "wire_sha256": _sha(wire.read_bytes()),
        "wire_pages": pages,
    }


def capture(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    doc: dict[str, Any] = {
        "identity": IDENTITY, "source_only": True,
        "broker": "ICMARKETS_CTRADER_DEMO", "g0_source_sha256": PARENT_G0_SHA,
        "parent_29_source_run": PARENT_SOURCE_RUN,
        "frozen_windows_utc": WINDOWS,
        "frozen_targets": TARGETS,
        "state": "SOURCE_PRECONDITION_BLOCKED",
        "markets_completed": 0, "markets": [],
        "original_request_response_wrapper_account_fields_archived": False,
        "native_tick_field_protobuf_archived": False,
        "trades_submitted": 0, "oauth_refresh_count": 0,
        "net_economics_authorized": False, "certified_traders": 0,
    }
    client: ReadOnlyTickPilot | None = None
    try:
        account, available = _source_auth(probe_catalog())
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(account)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
        client = ReadOnlyTickPilot(credentials=_credentials(), request_timeout_seconds=35.0)
        authenticated = client.connect_and_authenticate()
        if isinstance(authenticated, Failure) or client.account_id != account:
            raise SourceBlock("CTRADER_DEMO_REAUTH_FAILURE")
        for canonical, provider in TARGETS.items():
            market = {
                "canonical_symbol": canonical, "provider_symbol": provider,
                "native_protobuf_source_state": "BROKER_EXACT_SYMBOL_UNAVAILABLE",
                "complete_windows": 0, "windows": [],
            }
            symbol_id = available.get(canonical)
            if symbol_id:
                market["source_symbol_id"] = symbol_id
                folder = outdir / canonical
                folder.mkdir(parents=True, exist_ok=True)
                try:
                    for idx, w in enumerate(WINDOWS, 1):
                        sides = {}
                        for name in SIDES:
                            sides[name] = _store_side(client, symbol_id, canonical, idx, name, folder)
                        both = all(sides[s]["count"] > 0 for s in SIDES)
                        market["windows"].append({"frozen": w, "by_side": sides, "both_sides_nonempty": both})
                    market["complete_windows"] = sum(w["both_sides_nonempty"] for w in market["windows"])
                    market["native_protobuf_source_state"] = (
                        "TWO_WINDOWS_ALL_SIDES_WIRE_AVAILABLE_NOT_NET"
                        if market["complete_windows"] == 2 else "PARTIAL_NATIVE_SIDE_ZERO_NOT_NET"
                    )
                except (SourceBlock, RuntimeError, ValueError, OSError, TypeError) as exc:
                    market["safe_blocker"] = _safe_failure(exc)
                    market["native_protobuf_source_state"] = "SOURCE_PROVIDER_BLOCKED_NOT_NET"
                finally:
                    filename = folder / "SOURCE_MARKET_MANIFEST_NOT_NET.json"
                    filename.write_text(json.dumps(market, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    files = sorted(x for x in folder.iterdir() if x.is_file() and x.name != "FILE_SHA256SUMS.txt")
                    (folder / "FILE_SHA256SUMS.txt").write_text(
                        "".join(_sha(p.read_bytes()) + "  " + p.name + "\n" for p in files)
                    )
            doc["markets"].append({
                "canonical_symbol": canonical, "provider_symbol": provider,
                "state": market["native_protobuf_source_state"],
                "complete_windows": market["complete_windows"],
                "safe_blocker": market.get("safe_blocker"),
            })
        doc["markets_completed"] = sum(m["complete_windows"] == 2 for m in doc["markets"])
        doc["native_tick_field_protobuf_archived"] = doc["markets_completed"] > 0
        doc["state"] = (
            "G1_FIVE_MARKETS_2_WINDOWS_PROTO_WIRE_CAPTURED_NO_NET"
            if doc["markets_completed"] == 5 else "G1_FIVE_MARKETS_PARTIAL_PROTO_WIRE_SOURCE_NO_NET"
        )
    except (SourceBlock, RuntimeError, ValueError, OSError, TypeError) as exc:
        doc["safe_blocker"] = _safe_failure(exc)
    finally:
        if client is not None:
            client.close()
        report = outdir / "G1_PROTO_WIRE_PILOT_NOT_NET.json"
        report.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (outdir / "TOP_LEVEL_SHA256SUMS.txt").write_text(_sha(report.read_bytes()) + "  " + report.name + "\n")
    return doc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    args = p.parse_args()
    doc = capture(args.output)
    print(json.dumps({
        "state": doc["state"], "markets_completed": doc["markets_completed"],
        "markets": doc["markets"], "safe_blocker": doc.get("safe_blocker"),
        "historical_NET": False, "certified_traders": 0,
    }, sort_keys=True))
    if doc["state"] != "G1_FIVE_MARKETS_2_WINDOWS_PROTO_WIRE_CAPTURED_NO_NET":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
