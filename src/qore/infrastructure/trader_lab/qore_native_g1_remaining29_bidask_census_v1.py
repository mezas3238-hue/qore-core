"""QORE Native G1-PRE: bounded 29-market two-sided tick SOURCE census only.

Original IC Markets DEMO single read-only authenticated session, 3 predeclared
10-minute UTC windows per remaining exact-symbol market. No strategies/NET.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

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
from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import universe
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_G1_PRE_REMAINING29_CTRADER_BIDASK_SOURCE_V1"
FROZEN_TARGETS = tuple(s for s in universe() if s not in {"NZDUSD", "XAGUSD", "SP500", "NAS100"})
EXPECTED_WINDOWS = (
    ("2020-09-15T13:00:00+00:00", "2020-09-15T13:10:00+00:00"),
    ("2023-09-19T13:00:00+00:00", "2023-09-19T13:10:00+00:00"),
    ("2026-09-15T13:00:00+00:00", "2026-09-15T13:10:00+00:00"),
)
SOURCE_M1_PROOF_RUN = 38262534602
SOURCE_G0_SHA256 = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
EXCLUSIONS = {"NZDUSD": "ALREADY_SOURCE_PROVEN", "XAGUSD": "ALREADY_SOURCE_PROVEN",
              "SP500": "ALREADY_SOURCE_PROVEN_PROVIDER_US500",
              "NAS100": "PROVIDER_ALIAS_NOT_EXACT_VERIFIED"}
MAX_SOURCE_TICKS_PER_SIDE = 100_000
SCALE = Decimal(100000)

if len(FROZEN_TARGETS) != 29 or len(set(FROZEN_TARGETS)) != 29 or FROZEN_WINDOWS != EXPECTED_WINDOWS:
    raise RuntimeError("G1_PREREG_29_MARKET_OR_CLOCK_DRIFT")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_symbols(catalog: dict[str, Any]) -> tuple[int, dict[str, int]]:
    """Require exact source broker/account, no alias guessing after PnL."""
    if catalog.get("status") != "ICMARKETS_DEMO_CATALOG_VERIFIED":
        raise SourceBlock("BROKER_CATALOG_SOURCE_BLOCKED")
    account = catalog.get("_ephemeral_account_id")
    if type(account) is not int or account <= 0 or catalog.get("account_is_live") is not False:
        raise SourceBlock("SOURCE_DEMO_ACCOUNT_UNVERIFIED")
    matched: dict[str, int] = {}
    candidates = catalog.get("catalog", {}).get("catalog_exact_matches", {})
    for name in FROZEN_TARGETS:
        item = candidates.get(name)
        if not isinstance(item, dict):
            continue
        if (item.get("broker_symbol") == name and item.get("enabled") is True
                and type(item.get("symbol_id")) is int and item["symbol_id"] > 0):
            matched[name] = item["symbol_id"]
    return account, matched


def _write_side(
    output: Path, name: str, index: int, side: str,
    rows: list[tuple[int, int]], requests: int,
) -> dict[str, Any]:
    if name not in FROZEN_TARGETS or side not in SIDES or not 1 <= index <= 3:
        raise SourceBlock("SOURCE_WRITER_SCOPE_INVALID")
    if len(rows) > MAX_SOURCE_TICKS_PER_SIDE:
        raise SourceBlock("SOURCE_SIDE_TICK_BUDGET_EXCEEDED")
    previous: int | None = None
    for at, px in rows:
        if type(at) is not int or type(px) is not int or px <= 0:
            raise SourceBlock("SOURCE_TICK_INTEGER_INVALID")
        if previous is not None and at < previous:
            raise SourceBlock("SOURCE_TICK_CHRONOLOGY_INVALID")
        previous = at
    source = output / f"{name}-{index}-{side}-integer.jsonl"
    decoded = output / f"{name}-{index}-{side}-decoded.jsonl"
    source.write_text("".join(
        json.dumps({"epoch_ms": at, "integer_price_1e5": px}, sort_keys=True) + "\n"
        for at, px in rows
    ), encoding="utf-8")
    decoded.write_text("".join(
        json.dumps({
            "event_time_utc": datetime.fromtimestamp(at / 1000, tz=UTC)
            .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "native_sequence": sequence,
            "price": format(Decimal(px) / SCALE, "f"),
        }, sort_keys=True) + "\n"
        for sequence, (at, px) in enumerate(rows)
    ), encoding="utf-8")
    return {
        "native_tick_count": len(rows), "historical_provider_requests": requests,
        "native_int_file": source.name, "native_int_sha256": _sha(source),
        "decoded_file": decoded.name, "decoded_sha256": _sha(decoded),
    }


def _one_market(
    client: ReadOnlyTickPilot, name: str, symbol_id: int, output: Path,
) -> dict[str, Any]:
    """Failure of one market does not suppress later preregistered sources."""
    folder = output / name
    folder.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "identity": IDENTITY, "canonical_symbol": name, "provider_symbol": name,
        "provider_symbol_id": symbol_id,
        "provider": "ICMARKETS_CTRADER_DEMO", "account_type": "DEMO",
        "source_g0_sha256": SOURCE_G0_SHA256,
        "frozen_windows": EXPECTED_WINDOWS,
        "state": "SOURCE_NOT_VERIFIED", "complete_windows": 0,
        "source_captured_both_sides": False, "windows": [],
        "source_native_protobuf_bytes_archived": False,
        "historical_10Y_BIDASK_coverage_verified": False,
        "historical_NET_authorized": False, "certified_traders": 0,
        "trade_orders_sent": 0, "token_refresh_attempts": 0,
    }
    try:
        for win_index, frozen in enumerate(EXPECTED_WINDOWS, 1):
            begin, end = window_milliseconds(frozen)
            rows: dict[str, Any] = {}
            for side, typ in SIDES.items():
                seq = [0]

                def request(left: int, right: int) -> dict:
                    seq[0] += 1
                    return _native_fetch(
                        client, symbol_id, typ, left, right,
                        win_index * 10000 + typ * 1000 + seq[0],
                    )

                ticks, req_count = complete_side(request, begin, end - 1)
                rows[side] = _write_side(folder, name, win_index, side, ticks, req_count)
            valid = all(rows[side]["native_tick_count"] > 0 for side in SIDES)
            result["windows"].append({"utc_range": frozen, "by_side": rows,
                                      "both_sides_nonempty": valid})
        result["complete_windows"] = sum(w["both_sides_nonempty"] for w in result["windows"])
        result["source_captured_both_sides"] = result["complete_windows"] == 3
        result["state"] = (
            "THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
            if result["source_captured_both_sides"]
            else "PARTIAL_SOURCE_SIDE_EMPTY_NOT_NET"
        )
    except (SourceBlock, ValueError, RuntimeError, OSError, TypeError, KeyError) as exc:
        text = str(exc) if type(exc) is SourceBlock else ""
        # Only allow upstream static machine-readable error codes.
        result["sanitized_blocker"] = text if re.fullmatch(r"[A-Z][A-Z0-9_]{4,90}", text) else "SOURCE_REQUEST_FAILED_SAFE"
        result["state"] = "SOURCE_BLOCKED_NO_NET"
    finally:
        manifest = folder / "SOURCE-MANIFEST-NOT-NET.json"
        manifest.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        files = sorted(x for x in folder.iterdir() if x.is_file() and x.name != "SOURCE_SHA256SUMS.txt")
        (folder / "SOURCE_SHA256SUMS.txt").write_text(
            "".join(_sha(x) + "  " + x.name + "\n" for x in files), encoding="utf-8"
        )
    return result


def census(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "identity": IDENTITY, "source_only": True, "g0_source_sha256": SOURCE_G0_SHA256,
        "source_m1_catalog_provenance_run": SOURCE_M1_PROOF_RUN,
        "source_markets_requested": list(FROZEN_TARGETS),
        "original_three_sources_not_duplicated": sorted(EXCLUSIONS)[:],
        "alias_unresolved": "NAS100",
        "status": "SOURCE_CENSUS_NOT_STARTED", "attempted": 0, "complete": 0,
        "results": [], "source_only_not_33_complete_historical_history": True,
        "historical_NET_authorized": False, "certified_traders": 0,
        "trade_orders_sent": 0, "token_refresh_attempts": 0,
    }
    client: ReadOnlyTickPilot | None = None
    try:
        account, symbols = _source_symbols(probe_catalog())
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(account)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
        client = ReadOnlyTickPilot(credentials=_credentials(), request_timeout_seconds=35.0)
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure) or client.account_id != account:
            raise SourceBlock("SOURCE_DEMO_ACCOUNT_AUTH_FAILED")
        for symbol in FROZEN_TARGETS:
            symid = symbols.get(symbol)
            if symid is None:
                row = {"canonical_symbol": symbol, "state": "SOURCE_EXACT_CATALOG_UNAVAILABLE",
                       "sanitized_blocker": "EXACT_PROVIDER_SYMBOL_UNAVAILABLE", "complete_windows": 0}
            else:
                row = _one_market(client, symbol, symid, outdir)
            result["results"].append({
                "canonical_symbol": symbol, "state": row["state"],
                "complete_windows": row["complete_windows"],
                "source_manifest": f"{symbol}/SOURCE-MANIFEST-NOT-NET.json" if symid else None,
                "sanitized_blocker": row.get("sanitized_blocker"),
            })
            result["attempted"] += 1
        result["complete"] = sum(x["complete_windows"] == 3 for x in result["results"])
        result["status"] = (
            "G1_ALL_29_THREE_WINDOWS_SOURCE_PASS_NOT_NET"
            if result["complete"] == 29
            else "G1_PARTIAL_29_SOURCE_CENSUS_NOT_NET"
        )
    except (SourceBlock, ValueError, RuntimeError, TypeError, OSError) as exc:
        code = str(exc) if type(exc) is SourceBlock else ""
        result["source_blocker"] = code if re.fullmatch(r"[A-Z][A-Z0-9_]{4,90}", code) else "SOURCE_PRECONDITION_BLOCKED"
        result["status"] = "G1_ALL_29_SOURCE_PRECONDITION_BLOCKED_NOT_NET"
    finally:
        if client is not None:
            client.close()
        summary = outdir / "G1-29-SOURCE-CENSUS-NOT-NET.json"
        summary.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        (outdir / "G1_CENSUS_SHA256SUMS.txt").write_text(
            _sha(summary) + "  " + summary.name + "\n", encoding="utf-8"
        )
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    args = p.parse_args()
    report = census(args.output)
    print(json.dumps({
        "status": report["status"], "attempted": report["attempted"],
        "complete_markets": report["complete"],
        "blocked": [x["canonical_symbol"] for x in report["results"] if x["complete_windows"] != 3],
        "historical_NET_authorized": False, "certified_traders": 0,
    }, sort_keys=True))
    if report["status"] != "G1_ALL_29_THREE_WINDOWS_SOURCE_PASS_NOT_NET":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
