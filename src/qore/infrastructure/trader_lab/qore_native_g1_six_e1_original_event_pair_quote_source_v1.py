"""Original E1 method EXISTENCE-selected native BID/ASK source at both clocks.

Six frozen *theoretical research opportunities*, NOT orders, fills, PnL or NET.
Saves provider ProtoOATickData field bytes, not account response wrapper.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_native_icmarkets_bidask_source_pilot_v1 import (
    SIDES, ReadOnlyTickPilot, SourceBlock, complete_side,
)
from qore.infrastructure.trader_lab.qore_native_g1_proto_wire_5market_pilot_v1 import (
    _history_response, _safe_failure, _source_auth,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import probe_catalog
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m1_capture_v1 import _credentials
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_G1_E1_6_ORIGINAL_OPPORTUNITIES_BOTH_SOURCE_CLOCKS_V1"
EVENTS = (
    ("SP500", "US500", "2021-03-16", "SWEEP_RECLAIM"),
    ("SP500", "US500", "2023-03-21", "SWEEP_RECLAIM"),
    ("GBPUSD", "GBPUSD", "2021-03-16", "RANGE_BREAK_CONT"),
    ("USDJPY", "USDJPY", "2021-03-16", "RANGE_BREAK_CONT"),
    ("USDJPY", "USDJPY", "2023-03-21", "SWEEP_RECLAIM"),
    ("XAGUSD", "XAGUSD", "2023-03-21", "SWEEP_RECLAIM"),
)
CLOCKS = {"entry": (12, 55), "theoretical_close": (14, 55)}
MAX_WIRE_SIDE_BYTES = 10_000_000
MAX_TICK_SIDE_EVENTS = 100_000
E1_ORIGINAL_SOURCE_RUN = 38257207836
E1_ORIGINAL_CODE_SHA = "dfe78f115957a40f4188c30e78bd7f88c2ce6c42"
G0_SOURCE_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_period(day: str, clock: str) -> tuple[int, int]:
    if clock not in CLOCKS or day not in ("2021-03-16", "2023-03-21"):
        raise SourceBlock("SOURCE_E1_FROZEN_CLOCK_OR_DATE_MISMATCH")
    hour, minute = CLOCKS[clock]
    begin = datetime.fromisoformat(day).replace(tzinfo=UTC) + timedelta(hours=hour, minutes=minute)
    a = int(begin.timestamp() * 1000)
    return a, a + 600_000


def _write_side(
    client: ReadOnlyTickPilot, provider_id: int, canonical: str, day: str,
    clock: str, side: str, folder: Path,
) -> dict[str, Any]:
    if (canonical not in {x[0] for x in EVENTS} or side not in SIDES or clock not in CLOCKS):
        raise SourceBlock("SOURCE_E1_SIDE_OUT_OF_FROZEN_SCOPE")
    start, stop = source_period(day, clock)
    frames = bytearray()
    pages: list[dict[str, Any]] = []
    count = [0]

    def request(a: int, b: int) -> dict:
        count[0] += 1
        response = _history_response(client, provider_id, SIDES[side], a, b, count[0])
        wire = bytearray()
        for native in response["tick_data"]:
            if not hasattr(native, "SerializeToString"):
                raise SourceBlock("SOURCE_E1_ORIGINAL_TICK_PROTO_FIELD_MISSING")
            serialized = native.SerializeToString(deterministic=True)
            if not 0 < len(serialized) <= 1000:
                raise SourceBlock("SOURCE_E1_PROTO_FIELD_LENGTH_INVALID")
            wire.extend(struct.pack(">I", len(serialized)))
            wire.extend(serialized)
        offset = len(frames)
        if len(frames) + len(wire) > MAX_WIRE_SIDE_BYTES:
            raise SourceBlock("SOURCE_E1_PROVIDER_PROTO_FIELD_BUDGET_EXCEEDED")
        frames.extend(wire)
        pages.append({
            "from_ms": a, "to_ms": b, "has_more": response["has_more"],
            "accepted_leaf": not response["has_more"],
            "tick_count": len(response["tick_data"]),
            "wire_offset": offset, "wire_length": len(wire),
            "wire_section_sha256": sha(wire),
        })
        return response

    ticks, requests = complete_side(request, start, stop - 1)
    if len(ticks) > MAX_TICK_SIDE_EVENTS:
        raise SourceBlock("SOURCE_E1_SIDE_EVENTS_BUDGET_EXCEEDED")
    prefix = f"{canonical}-{day}-{clock}-{side}"
    wire_file = folder / (prefix+"-proto-fields.pbframes")
    int_file = folder / (prefix+"-integer.jsonl")
    decimal_file = folder / (prefix+"-decimal.jsonl")
    wire_file.write_bytes(frames)
    int_file.write_text("".join(
        json.dumps({"epoch_ms": t,"integer_price_1e5":px},sort_keys=True)+"\n"
        for t,px in ticks
    ),encoding="utf-8")
    decimal_file.write_text("".join(
        json.dumps({
            "event_time_utc":datetime.fromtimestamp(t/1000,tz=UTC)
            .isoformat(timespec="milliseconds").replace("+00:00","Z"),
            "native_sequence":n,
            "price":format(Decimal(px)/Decimal(100000),"f"),
        },sort_keys=True)+"\n"
        for n,(t,px) in enumerate(ticks)
    ),encoding="utf-8")
    return {
        "start_utc_ms_inclusive":start, "end_utc_ms_exclusive":stop,
        "provider_requests":requests, "native_tick_count":len(ticks),
        "wire_field_protobuf_account_wrapper_archived":False,
        "pages":pages,
        "wire_file":wire_file.name, "wire_sha256":sha(wire_file.read_bytes()),
        "int_file":int_file.name, "int_sha256":sha(int_file.read_bytes()),
        "decimal_file":decimal_file.name, "decimal_sha256":sha(decimal_file.read_bytes()),
    }


def capture(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True,exist_ok=True)
    report: dict[str, Any] = {
        "identity":IDENTITY, "source_only":True,
        "e1_source_run":E1_ORIGINAL_SOURCE_RUN,
        "e1_source_code_sha":E1_ORIGINAL_CODE_SHA, "g0_sha":G0_SOURCE_SHA,
        "broker":"ICMARKETS_CTRADER_DEMO",
        "frozen_events": [list(x) for x in EVENTS],
        "window_clocks":CLOCKS,
        "state":"SOURCE_PRECONDITION_BLOCKED",
        "fully_acquired_event_rows":0,
        "event_rows":[],
        "original_CIBO_12_vs_current_broker_contract_homologated":False,
        "historical_Net_authorized":False,
        "certified_traders":0,
        "trade_orders_sent":0,
        "oauth_refresh_attempts":0,
    }
    client: ReadOnlyTickPilot | None = None
    try:
        broker, catalog = _source_auth(probe_catalog())
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(broker)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID",None)
        client = ReadOnlyTickPilot(credentials=_credentials(),request_timeout_seconds=35.0)
        authed = client.connect_and_authenticate()
        if isinstance(authed, Failure) or client.account_id != broker:
            raise SourceBlock("SOURCE_E1_DEMO_ACCOUNT_AUTH_FAILED")
        for canonical,provider,day,method in EVENTS:
            row = {
                "canonical":canonical,"provider":provider,"day":day,"method":method,
                "state":"SOURCE_PROVIDER_SYMBOL_UNVERIFIED","both_windows_complete":False,
                "clocks":{},
            }
            symid = catalog.get(canonical)
            if type(symid) is int and symid > 0:
                row["provider_symbol_id"] = symid
                folder = outdir / f"{canonical}-{day}"
                folder.mkdir(parents=True,exist_ok=True)
                try:
                    for clock in CLOCKS:
                        sides = {}
                        for side in SIDES:
                            sides[side] = _write_side(
                                client,symid,canonical,day,clock,side,folder,
                            )
                        row["clocks"][clock] = {
                            "sides":sides,
                            "both_native_sides_nonempty":all(
                                sides[name]["native_tick_count"] > 0 for name in SIDES
                            ),
                        }
                    row["both_windows_complete"] = all(
                        row["clocks"][clock]["both_native_sides_nonempty"] for clock in CLOCKS
                    )
                    row["state"] = (
                        "BOTH_E1_RESEARCH_CLOCK_SOURCE_WINDOWS_PRESENT_NO_NET"
                        if row["both_windows_complete"]
                        else "E1_SOURCE_SIDE_EMPTY_NO_NET"
                    )
                except (SourceBlock,RuntimeError,ValueError,TypeError,OSError,KeyError) as error:
                    row["safe_blocker"] = _safe_failure(error)
                    row["state"] = "E1_SOURCE_PROVIDER_BLOCKED_NO_NET"
                finally:
                    manifest = folder / "E1_EVENT_SOURCE_MANIFEST_NOT_NET.json"
                    manifest.write_text(json.dumps(row,indent=2,sort_keys=True)+"\n")
                    files = sorted(p for p in folder.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
                    (folder/"SHA256SUMS.txt").write_text(
                        "".join(sha(p.read_bytes())+"  "+p.name+"\n" for p in files)
                    )
            report["event_rows"].append({
                "canonical":canonical,"day":day,"method":method,
                "state":row["state"],
                "both_windows_complete":row["both_windows_complete"],
                "safe_blocker":row.get("safe_blocker"),
            })
        report["fully_acquired_event_rows"] = sum(
            r["both_windows_complete"] for r in report["event_rows"]
        )
        report["state"] = (
            "SIX_E1_EVENT_CLOCK_PAIRS_NATIVE_BIDASK_PRESENT_NO_NET"
            if report["fully_acquired_event_rows"] == 6
            else "SIX_E1_EVENT_CLOCK_PAIRS_SOURCE_PARTIAL_NO_NET"
        )
    except (SourceBlock,RuntimeError,ValueError,TypeError,OSError) as err:
        report["safe_blocker"] = _safe_failure(err)
    finally:
        if client is not None:
            client.close()
        manifest=outdir/"SOURCE_SIX_E1_EVENT_CLOCK_PAIR_MANIFEST_NOT_NET.json"
        manifest.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        (outdir/"SOURCE_SHA256SUMS.txt").write_text(
            sha(manifest.read_bytes())+"  "+manifest.name+"\n")
    return report


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    result=capture(args.output)
    print(json.dumps({
        "state":result["state"],
        "source_complete_event_rows":result["fully_acquired_event_rows"],
        "safe_blocker":result.get("safe_blocker"),
        "historical_NET":False,"certified":0,
    },sort_keys=True))
    if result["state"]!="SIX_E1_EVENT_CLOCK_PAIRS_NATIVE_BIDASK_PRESENT_NO_NET":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
