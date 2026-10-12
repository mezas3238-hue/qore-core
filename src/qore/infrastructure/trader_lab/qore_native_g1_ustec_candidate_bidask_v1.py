"""Read-only USTEC (NAS100 *unverified* alias) historical BID/ASK source pilot.

NEVER establishes contract equivalence to archived original NAS100 CIBO M5.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    CANONICAL_ALIAS_HINTS,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_G1_USTEC_UNVERIFIED_NAS100_ALIAS_SOURCE_TICKS_V1"
ALIAS_IDENTITY_SOURCE_RUN = 38284304699
ALIAS_IDENTITY_ARTIFACT = 11762018327
ALIAS_IDENTITY_ZIP_SHA256 = "7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e"
USTEC_PINNED_SYMBOL_ID = 10014
WINDOWS = (
    ("2020-09-15T13:00:00+00:00", "2020-09-15T13:10:00+00:00"),
    ("2023-09-19T13:00:00+00:00", "2023-09-19T13:10:00+00:00"),
    ("2026-09-15T13:00:00+00:00", "2026-09-15T13:10:00+00:00"),
)
if CANONICAL_ALIAS_HINTS.get("NAS100") != "USTEC" or WINDOWS != FROZEN_WINDOWS:
    raise RuntimeError("G1_USTEC_SOURCE_PREREG_FROZEN_WITNESS_FAILED")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_candidate(entries: tuple[object, ...]) -> int:
    """An exact enabled USTEC with ID10014; no NAS100 or other alias guessing."""
    matches = [
        x for x in entries
        if getattr(x, "symbolName", None) == "USTEC"
        and getattr(x, "enabled", None) is True
    ]
    if len(matches) != 1:
        raise SourceBlock("USTEC_BROKER_EXACT_CANDIDATE_UNAVAILABLE_OR_AMBIGUOUS")
    value = getattr(matches[0], "symbolId", None)
    if type(value) is not int or value != USTEC_PINNED_SYMBOL_ID:
        raise SourceBlock("USTEC_SYMBOL_ID_CHANGED_FROM_PREFLIGHT")
    return value


def _write_side(output: Path, win: int, side: str, ticks: list[tuple[int, int]], requests: int) -> dict:
    if win not in (1, 2, 3) or side not in SIDES:
        raise SourceBlock("USTEC_SIDE_OUTPUT_OUT_OF_SCOPE")
    target = output / f"USTEC-{win}-{side}-integer.jsonl"
    normalized = output / f"USTEC-{win}-{side}-decoded.jsonl"
    target.write_text("".join(
        json.dumps({"epoch_ms": t, "integer_price_1e5": px}, sort_keys=True) + "\n"
        for t, px in ticks
    ), encoding="utf-8")
    normalized.write_text("".join(
        json.dumps({
            "event_time_utc": datetime.fromtimestamp(t / 1000, tz=UTC)
            .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "native_sequence": n,
            "price": format(Decimal(px) / Decimal(100000), "f"),
        }, sort_keys=True) + "\n"
        for n, (t, px) in enumerate(ticks)
    ), encoding="utf-8")
    return {
        "count": len(ticks), "requests": requests,
        "integer_file": target.name, "integer_sha256": _sha(target),
        "decoded_file": normalized.name, "decoded_sha256": _sha(normalized),
    }


def capture(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "identity": IDENTITY, "canonical_alias_candidate": "NAS100",
        "actual_provider_symbol": "USTEC",
        "provider": "ICMARKETS_CTRADER_DEMO",
        "source_alias_preflight_run": ALIAS_IDENTITY_SOURCE_RUN,
        "source_alias_preflight_artifact": ALIAS_IDENTITY_ARTIFACT,
        "source_alias_preflight_zip_expected": ALIAS_IDENTITY_ZIP_SHA256,
        "provider_symbol_id_pinned": USTEC_PINNED_SYMBOL_ID,
        "windows_frozen_utc": WINDOWS,
        "source_state": "USTEC_SOURCE_NOT_VERIFIED",
        "complete_windows": 0, "windows": [],
        "nas100_original_CIBO_contract_equivalence_verified": False,
        "provider_raw_protobuf_bytes_archived": False,
        "continuous_10Y_historical_BIDASK_proven": False,
        "historical_NET_authorized": False,
        "order_submission_count": 0,
        "oauth_refresh_count": 0, "certified_traders": 0,
    }
    client: ReadOnlyTickPilot | None = None
    try:
        account = probe_catalog()
        if account.get("status") != "ICMARKETS_DEMO_CATALOG_VERIFIED" or account.get("account_is_live") is not False:
            raise SourceBlock("SOURCE_CTRADER_BROKER_DEMO_NOT_VERIFIED")
        acct_id = account.get("_ephemeral_account_id")
        if type(acct_id) is not int or acct_id <= 0:
            raise SourceBlock("SOURCE_CTRADER_ACCOUNT_UNVERIFIED")
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(acct_id)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
        client = ReadOnlyTickPilot(credentials=_credentials(), request_timeout_seconds=35.0)
        session = client.connect_and_authenticate()
        if isinstance(session, Failure) or client.account_id != acct_id:
            raise SourceBlock("SOURCE_CTRADER_ACCOUNT_AUTH_FAILED")
        symbols = client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": acct_id, "includeArchivedSymbols": False},
            client_msg_id="qore-native-g1-ustec-verify-provider-id-before-ticks",
            timeout_seconds=35.0,
        )
        if isinstance(symbols, Failure):
            raise SourceBlock("USTEC_CATALOG_REQUEST_FAILED")
        symid = exact_candidate(tuple(getattr(symbols.value, "symbol", ())))
        result["current_symbol_id_exact_match"] = True
        for idx, w in enumerate(WINDOWS, 1):
            begin, stop = window_milliseconds(w)
            sides: dict[str, dict] = {}
            for side, typ in SIDES.items():
                counter = [0]

                def fetch(first: int, last: int) -> dict:
                    counter[0] += 1
                    return _native_fetch(
                        client, symid, typ, first, last, idx * 1000 + typ * 100 + counter[0],
                    )

                ticks, requests = complete_side(fetch, begin, stop - 1)
                sides[side] = _write_side(output, idx, side, ticks, requests)
            result["windows"].append({
                "utc_range": w, "by_side": sides,
                "both_nonempty": all(sides[s]["count"] > 0 for s in SIDES),
            })
        result["complete_windows"] = sum(x["both_nonempty"] for x in result["windows"])
        result["source_state"] = (
            "USTEC_SOURCE_THREE_WINDOWS_AVAILABLE_ALIAS_UNVERIFIED_NOT_NET"
            if result["complete_windows"] == 3 else
            "USTEC_SOURCE_PARTIAL_ALIAS_UNVERIFIED_NOT_NET"
        )
    except (SourceBlock, RuntimeError, ValueError, TypeError, KeyError, OSError) as exc:
        allowed = {
            "SOURCE_CTRADER_BROKER_DEMO_NOT_VERIFIED", "SOURCE_CTRADER_ACCOUNT_UNVERIFIED",
            "SOURCE_CTRADER_ACCOUNT_AUTH_FAILED", "USTEC_CATALOG_REQUEST_FAILED",
            "USTEC_BROKER_EXACT_CANDIDATE_UNAVAILABLE_OR_AMBIGUOUS",
            "USTEC_SYMBOL_ID_CHANGED_FROM_PREFLIGHT",
            "NATIVE_TICK_PROVIDER_QUERY_FAILED", "NATIVE_TICK_PROVIDER_TRANSPORT_FAILURE",
            "NATIVE_TICK_PROVIDER_PROTOCOL_FAILURE", "TICK_TIME_OUTSIDE_QUERY",
            "MISSING_HASMORE", "UNPAGEABLE_SAME_MS", "QUERY_BUDGET_EXCEEDED",
        }
        result["source_blocker"] = str(exc) if type(exc) is SourceBlock and str(exc) in allowed else "USTEC_SOURCE_UNAVAILABLE_SAFE"
        result["source_state"] = "USTEC_SOURCE_BLOCKED_NO_NET"
    finally:
        if client is not None:
            client.close()
        mf = output / "USTEC-CANDIDATE-SOURCE-NOT-NET.json"
        mf.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        files = sorted(p for p in output.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
        (output / "SHA256SUMS.txt").write_text(
            "".join(_sha(p) + "  " + p.name + "\n" for p in files), encoding="utf-8"
        )
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    args = p.parse_args()
    result = capture(args.output)
    print(json.dumps({
        "source_state": result["source_state"],
        "source_complete_windows": result["complete_windows"],
        "original_NAS100_contract_equivalence": False, "NET": False,
        "safe_blocker": result.get("source_blocker"),
    }, sort_keys=True))
    if result["source_state"] != "USTEC_SOURCE_THREE_WINDOWS_AVAILABLE_ALIAS_UNVERIFIED_NOT_NET":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
