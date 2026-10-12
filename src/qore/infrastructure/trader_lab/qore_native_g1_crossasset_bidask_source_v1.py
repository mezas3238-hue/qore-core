"""G1 source-only cross-asset BID/ASK cTrader DEMO feasibility pilot.

XAGUSD metal and canonical SP500 -> provider US500 index. Source windows
frozen BEFORE collection; only historical side-ticks, no orders or economics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.qore_native_icmarkets_bidask_source_pilot_v1 import (
    FROZEN_WINDOWS,
    SIDES,
    ReadOnlyTickPilot,
    SourceBlock,
    _native_fetch,
    complete_side,
    window_milliseconds,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import probe_catalog
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m1_capture_v1 import _credentials
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_G1_CROSSASSET_ICMARKETS_BIDASK_SOURCE_V1"
TARGETS = {"XAGUSD": "XAGUSD", "SP500": "US500"}
FROZEN_UTC_WINDOWS = (
    ("2020-09-15T13:00:00+00:00", "2020-09-15T13:10:00+00:00"),
    ("2023-09-19T13:00:00+00:00", "2023-09-19T13:10:00+00:00"),
    ("2026-09-15T13:00:00+00:00", "2026-09-15T13:10:00+00:00"),
)
PARENT_G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
PARENT_NATIVE_M1_RUN = 38262534602
MAX_SIDE_ROWS = 100_000
SCALE = Decimal(100_000)
SOURCE_ONLY = True

if FROZEN_UTC_WINDOWS != FROZEN_WINDOWS:
    raise RuntimeError("FROZEN_SOURCE_WINDOWS_NOT_IDENTICAL_TO_NZDUSD_PREREG")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract_proof(catalog: dict, canonical: str) -> tuple[int, int]:
    """Exact source identity, not numerical alias or historical broker contract proof."""
    if canonical not in TARGETS:
        raise SourceBlock("INVALID_UNIVERSE_OUT_OF_SCOPE")
    if catalog.get("status") != "ICMARKETS_DEMO_CATALOG_VERIFIED":
        raise SourceBlock("SOURCE_DEMO_CATALOG_NOT_VERIFIED")
    acct = catalog.get("_ephemeral_account_id")
    if type(acct) is not int or acct <= 0 or catalog.get("account_is_live") is not False:
        raise SourceBlock("SOURCE_DEMO_ACCOUNT_NOT_VERIFIED")
    item = catalog["catalog"]["catalog_exact_matches"].get(TARGETS[canonical])
    if not isinstance(item, dict) or item.get("broker_symbol") != TARGETS[canonical]:
        raise SourceBlock("EXACT_PROVIDER_ALIAS_NOT_VERIFIED")
    if item.get("enabled") is not True or type(item.get("symbol_id")) is not int or item["symbol_id"] <= 0:
        raise SourceBlock("EXACT_PROVIDER_SYMBOL_NOT_ENABLED")
    return acct, item["symbol_id"]


def write_side(
    folder: Path, canonical: str, window_index: int, side: str, ticks: list[tuple[int, int]], requests: int,
) -> dict[str, object]:
    """Persist decoded integer witness and separately normalized decimal source."""
    if canonical not in TARGETS or side not in SIDES or not (1 <= window_index <= 3):
        raise SourceBlock("INVALID_WRITER_SCOPE")
    if len(ticks) > MAX_SIDE_ROWS:
        raise SourceBlock("SOURCE_SIDE_CAP_EXCEEDED")
    previous: int | None = None
    for at, price in ticks:
        if type(at) is not int or type(price) is not int or price <= 0:
            raise SourceBlock("BAD_SOURCE_INTEGER_TICK")
        if previous is not None and at < previous:
            raise SourceBlock("BAD_SOURCE_TICK_CLOCK_ORDER")
        previous = at
    name = canonical.lower()
    native = folder / f"{name}-{window_index}-{side}-integer.jsonl"
    decoded = folder / f"{name}-{window_index}-{side}-decoded.jsonl"
    native.write_text("".join(
        json.dumps({"epoch_ms": at, "integer_price_1e5": price}, sort_keys=True) + "\n"
        for at, price in ticks
    ), encoding="utf-8")
    decoded.write_text("".join(
        json.dumps({
            "event_time_utc": datetime.fromtimestamp(at / 1000, tz=UTC)
            .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "native_sequence": index,
            "price": format(Decimal(price) / SCALE, "f"),
        }, sort_keys=True) + "\n"
        for index, (at, price) in enumerate(ticks)
    ), encoding="utf-8")
    return {
        "native_tick_count": len(ticks), "historical_provider_requests": requests,
        "native_int_file": native.name, "native_int_sha256": _sha(native),
        "decoded_file": decoded.name, "decoded_sha256": _sha(decoded),
    }


def capture(canonical: str, destination: Path) -> dict[str, object]:
    if canonical not in TARGETS:
        raise SourceBlock("INVALID_UNIVERSE_OUT_OF_SCOPE")
    destination.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "identity": IDENTITY, "canonical_symbol": canonical,
        "expected_provider_symbol": TARGETS[canonical],
        "account_type": "DEMO",
        "provider": "ICMARKETS_CTRADER_DEMO",
        "g0_source_sha256": PARENT_G0_SHA,
        "m1_native_source_run": PARENT_NATIVE_M1_RUN,
        "windows_frozen_utc": FROZEN_UTC_WINDOWS,
        "source_result": "SOURCE_BLOCKED",
        "complete_windows": 0, "windows": [],
        "native_protobuf_bytes_archived": False,
        "historical_contract_equivalence_to_G0_proven": False,
        "33_market_history_proven": False,
        "NET_economics_authorized": False, "certified_traders": 0,
        "trade_orders_sent": 0, "token_refresh_attempts": 0,
    }
    client: ReadOnlyTickPilot | None = None
    try:
        account, symbol_id = contract_proof(probe_catalog(), canonical)
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(account)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
        client = ReadOnlyTickPilot(credentials=_credentials(), request_timeout_seconds=35.0)
        auth = client.connect_and_authenticate()
        if isinstance(auth, Failure) or client.account_id != account:
            raise SourceBlock("SOURCE_DEMO_ACCOUNT_REAUTH_BLOCKED")
        manifest["provider_symbol"] = TARGETS[canonical]
        manifest["provider_symbol_id"] = symbol_id
        for index, frozen in enumerate(FROZEN_UTC_WINDOWS, 1):
            begin, end = window_milliseconds(frozen)
            sides: dict[str, object] = {}
            for name, quote_type in SIDES.items():
                counter = [0]

                def request(a: int, b: int) -> dict:
                    counter[0] += 1
                    return _native_fetch(
                        client, symbol_id, quote_type, a, b, index * 1000 + quote_type * 100 + counter[0],
                    )

                ticks, requests = complete_side(request, begin, end - 1)
                sides[name] = write_side(destination, canonical, index, name, ticks, requests)
            complete = all(sides[s]["native_tick_count"] > 0 for s in SIDES)
            manifest["windows"].append({
                "utc_range": frozen, "by_side": sides, "both_sides_nonempty": complete,
            })
        manifest["complete_windows"] = sum(
            int(w["both_sides_nonempty"]) for w in manifest["windows"]
        )
        manifest["source_result"] = (
            "THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
            if manifest["complete_windows"] == 3 else "PARTIAL_QUOTE_SIDE_COVERAGE_NOT_NET"
        )
    except (SourceBlock, ValueError, RuntimeError, TypeError, KeyError, OSError) as exc:
        # Closed set of static safe diagnostics, never raw tokens/account/provider strings.
        safe_codes = {
            "INVALID_UNIVERSE_OUT_OF_SCOPE", "SOURCE_DEMO_CATALOG_NOT_VERIFIED",
            "SOURCE_DEMO_ACCOUNT_NOT_VERIFIED", "EXACT_PROVIDER_ALIAS_NOT_VERIFIED",
            "EXACT_PROVIDER_SYMBOL_NOT_ENABLED", "SOURCE_DEMO_ACCOUNT_REAUTH_BLOCKED",
            "SOURCE_SIDE_CAP_EXCEEDED", "BAD_SOURCE_TICK_CLOCK_ORDER",
            "BAD_SOURCE_INTEGER_TICK", "NATIVE_TICK_PROVIDER_TRANSPORT_FAILURE",
            "NATIVE_TICK_PROVIDER_QUERY_FAILED", "NATIVE_TICK_PROVIDER_PROTOCOL_FAILURE",
            "NATIVE_TICK_PROTOCOL_REQUEST_FIELD_INVALID", "NATIVE_TICK_PROTOCOL_RESPONSE_UNDECODABLE",
            "TICK_TIME_OUTSIDE_QUERY", "MISSING_HASMORE", "UNPAGEABLE_SAME_MS",
            "QUERY_BUDGET_EXCEEDED", "BAD_PROVIDER_TICK",
        }
        manifest["source_result"] = "SOURCE_BLOCKED"
        manifest["sanitized_blocker"] = str(exc) if type(exc) is SourceBlock and str(exc) in safe_codes else "OTHER_SOURCE_BLOCKER"
    finally:
        if client is not None:
            client.close()
        report = destination / "SOURCE-CROSSASSET-NOT-NET.json"
        report.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        files = sorted(x for x in destination.iterdir() if x.is_file() and x.name != "OUTPUT_SHA256SUMS.txt")
        (destination / "OUTPUT_SHA256SUMS.txt").write_text(
            "".join(_sha(x) + "  " + x.name + "\n" for x in files), encoding="utf-8"
        )
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("canonical", choices=sorted(TARGETS))
    p.add_argument("output", type=Path)
    args = p.parse_args()
    result = capture(args.canonical, args.output)
    print(json.dumps({
        "symbol": args.canonical,
        "source_result": result["source_result"],
        "complete_windows": result["complete_windows"],
        "sanitized_blocker": result.get("sanitized_blocker"),
        "historical_NET_authorized": False, "traders_certified": 0,
    }, sort_keys=True))
    if result["source_result"] != "THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
