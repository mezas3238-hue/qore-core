"""VT31 G5 source-only IC Markets DEMO USTEC BID/ASK on ICT Silver Bullet hours.

Pre-registered development-only pilot. Never equates USTEC to NAS100 contract,
never emits a fill or a trading decision, never fetches fresh holdout.
Reuses the QORE Native read-only 2026-10-12 independently audited decoder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.qore_native_g1_ustec_candidate_bidask_v1 import (
    USTEC_PINNED_SYMBOL_ID,
    exact_candidate,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_bidask_source_pilot_v1 import (
    SIDES,
    ReadOnlyTickPilot,
    SourceBlock,
    _native_fetch,
    complete_side,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    probe_catalog,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m1_capture_v1 import (
    _credentials,
)
from qore.kernel.result import Failure

IDENTITY = "VT31_G5_REAL_USTEC_SILVER_BULLET_SOURCE_DEV_PILOT_V1"
NY = ZoneInfo("America/New_York")
DAYS_NY = ("2024-06-12", "2025-01-15")
HOURS_NY = (("LONDON", 3), ("NY_AM", 10), ("NY_PM", 14))
MAX_REQUESTS_ALL = 300
EXPECTED_OFFSETS = {"2024-06-12": -4, "2025-01-15": -5}


def frozen_windows() -> tuple[dict[str, str], ...]:
    """Single unambiguous DST-aware inclusive start, exclusive end."""
    rows = []
    for raw_day in DAYS_NY:
        day = date.fromisoformat(raw_day)
        for session, h in HOURS_NY:
            start = datetime.combine(day, time(h), NY)
            end = datetime.combine(day, time(h + 1), NY)
            if int(start.utcoffset().total_seconds() / 3600) != EXPECTED_OFFSETS[raw_day]:
                raise SourceBlock("NY_DST_EXPECTATION_MISMATCH")
            rows.append({
                "day_ny": raw_day,
                "session": session,
                "start_ny": start.isoformat(),
                "end_ny": end.isoformat(),
                "start_utc": start.astimezone(UTC).isoformat(),
                "end_utc": end.astimezone(UTC).isoformat(),
            })
    return tuple(rows)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _side_rows(
    out: Path, number: int, side: str,
    ticks: list[tuple[int, int]], queries: int,
) -> dict[str, str | int]:
    native = out / f"ustec-sb-{number:02d}-{side}-integer.jsonl"
    normalized = out / f"ustec-sb-{number:02d}-{side}-decoded.jsonl"
    with native.open("w", encoding="utf-8") as a, normalized.open("w", encoding="utf-8") as b:
        for seq, (ts, value) in enumerate(ticks):
            a.write(json.dumps({"epoch_ms": ts, "integer_price_1e5": value}, sort_keys=True) + "\n")
            b.write(json.dumps({
                "epoch_ms": ts,
                "native_sequence": seq,
                "decimal_price": format(value / 100000, ".5f"),
            }, sort_keys=True) + "\n")
    return {
        "tick_count": len(ticks),
        "requests": queries,
        "integer_file": native.name,
        "integer_sha256": _sha(native),
        "decoded_file": normalized.name,
        "decoded_sha256": _sha(normalized),
    }


def capture(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    windows = frozen_windows()
    record: dict = {
        "schema": IDENTITY,
        "status": "SOURCE_ONLY_NOT_STARTED",
        "provider": "ICMARKETS_CTRADER_DEMO",
        "provider_symbol": "USTEC",
        "provider_symbol_id": USTEC_PINNED_SYMBOL_ID,
        "strategy_symbol": "NAS100",
        "strategy_contract_equivalent": False,
        "source_prereg_days_ny": list(DAYS_NY),
        "source_prereg_sessions_ny": [s for s, _ in HOURS_NY],
        "windows_planned": windows,
        "windows_complete": 0,
        "windows_attempted": [],
        "total_provider_requests": 0,
        "orders_submitted": 0,
        "oauth_refresh_attempts": 0,
        "trades_replayed": 0,
        "fresh_holdout_accessed": False,
        "net_pnl_certified": False,
        "live_authorized": False,
    }
    client = None
    try:
        account = probe_catalog()
        if account.get("status") != "ICMARKETS_DEMO_CATALOG_VERIFIED" or account.get("account_is_live") is not False:
            raise SourceBlock("ICMARKETS_DEMO_ACCOUNT_NOT_VERIFIED")
        account_id = account.get("_ephemeral_account_id")
        if type(account_id) is not int or account_id <= 0:
            raise SourceBlock("DEMO_ACCOUNT_ID_UNAVAILABLE")
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(account_id)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
        client = ReadOnlyTickPilot(credentials=_credentials(), request_timeout_seconds=35.0)
        auth = client.connect_and_authenticate()
        if isinstance(auth, Failure) or client.account_id != account_id:
            raise SourceBlock("ICMARKETS_DEMO_AUTH_BLOCKED")
        listed = client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
            client_msg_id="vt31-source-ustec-catalog-exact",
            timeout_seconds=35.0,
        )
        if isinstance(listed, Failure):
            raise SourceBlock("USTEC_EXACT_CATALOG_FAILED")
        sid = exact_candidate(tuple(getattr(listed.value, "symbol", ())))
        for index, w in enumerate(windows, 1):
            a = int(datetime.fromisoformat(w["start_utc"]).timestamp() * 1000)
            b = int(datetime.fromisoformat(w["end_utc"]).timestamp() * 1000)
            if b - a != 3600000:
                raise SourceBlock("UTC_SOURCE_HOUR_LENGTH_MISMATCH")
            by_side: dict = {}
            for side, side_type in SIDES.items():
                def fetch(first: int, last: int) -> dict:
                    if record["total_provider_requests"] >= MAX_REQUESTS_ALL:
                        raise SourceBlock("VT31_G5_TOTAL_QUERY_BUDGET_EXHAUSTED")
                    record["total_provider_requests"] += 1
                    return _native_fetch(
                        client, sid, side_type, first, last,
                        index * 1000 + side_type * 100 + record["total_provider_requests"],
                    )
                values, requests = complete_side(fetch, a, b - 1)
                by_side[side] = _side_rows(out, index, side, values, requests)
            complete = all(by_side[s]["tick_count"] > 0 for s in SIDES)
            record["windows_attempted"].append({**w, "by_side": by_side, "both_sides_nonempty": complete})
            record["windows_complete"] += int(complete)
        record["status"] = (
            "REAL_USTEC_BIDASK_6_SILVER_BULLET_HOURS_AVAILABLE_NOT_NET"
            if record["windows_complete"] == len(windows)
            else "REAL_USTEC_PARTIAL_SILVER_BULLET_HOURS_NOT_NET"
        )
    except (SourceBlock, RuntimeError, ValueError, TypeError, KeyError, OSError) as exc:
        safe = str(exc)
        if type(exc) is not SourceBlock or not safe.isupper() or len(safe) > 96:
            safe = "USTEC_PROVIDER_OR_ACCOUNT_BLOCKED_SAFE"
        record["status"] = "SOURCE_PARTIAL_OR_BLOCKED_NOT_NET"
        record["safe_blocker"] = safe
    finally:
        if client is not None:
            client.close()
        mf = out / "VT31-G5-USTEC-SB-BIDASK-NOT-NET.json"
        mf.write_text(json.dumps(record, sort_keys=True, indent=2, default=list) + "\n", encoding="utf-8")
        lines = []
        for item in sorted(out.iterdir()):
            if item.is_file() and item.name != "SHA256SUMS.txt":
                lines.append(f"{_sha(item)}  {item.name}")
        (out / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    result = capture(parser.parse_args().output)
    print(json.dumps({
        "status": result["status"],
        "windows_complete": result["windows_complete"],
        "requests": result["total_provider_requests"],
        "safe_blocker": result.get("safe_blocker"),
        "broker_contract_homologated": False,
        "NET": False,
    }, sort_keys=True))
    if result["windows_complete"] != len(frozen_windows()):
        raise SystemExit(4)


if __name__ == "__main__":
    main()
