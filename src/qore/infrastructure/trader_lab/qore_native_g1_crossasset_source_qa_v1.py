"""Independent post-capture source QA for original IC Markets XAGUSD/US500 ticks.

Research only: 2 markets, 3 fixed windows, 1e5 native integer price and
as-of BID/ASK chronology. No historical fill, spread-at-trade or NET claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "QORE_NATIVE_G1_CROSSASSET_INDEPENDENT_SHA_ASOF_QA_V1"
SOURCE_RUN = 38282585181
SOURCE_HEAD = "626909b960525dbf3ca0c7ab0a554b56d03c0170"
SOURCE_G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
SYMBOL_ARTIFACT = {
    "XAGUSD": {
        "provider": "XAGUSD", "id": 11761892358,
        "zip_sha256": "aaa32406dd4e2a5cc826da47e088f645f3963b88735d4ced4d7f366e5f00843e",
    },
    "SP500": {
        "provider": "US500", "id": 11761419260,
        "zip_sha256": "a1fa1a7c22062f2b20970c5a8540634f3fc3ab0a165f136dce97aa3cbe26f5f5",
    },
}
WINDOWS = (
    ("2020-09-15T13:00:00+00:00", "2020-09-15T13:10:00+00:00"),
    ("2023-09-19T13:00:00+00:00", "2023-09-19T13:10:00+00:00"),
    ("2026-09-15T13:00:00+00:00", "2026-09-15T13:10:00+00:00"),
)
SOURCE_MANIFEST = "SOURCE-CROSSASSET-NOT-NET.json"
MAX_SIDE_AGE_MS = 5000
SCALE = Decimal(100000)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _verified_files(folder: Path) -> dict[str, str]:
    signed = folder / "OUTPUT_SHA256SUMS.txt"
    if not signed.is_file():
        raise ValueError("SOURCE_SHA_REGISTER_MISSING")
    lines = signed.read_text(encoding="utf-8").splitlines()
    if len(lines) != 13:
        raise ValueError("SOURCE_FILE_COUNT_NOT_13")
    expected: dict[str, str] = {}
    for line in lines:
        pieces = line.split(maxsplit=1)
        if len(pieces) != 2:
            raise ValueError("SOURCE_SHA_ENTRY_MALFORMED")
        digest, name = pieces
        if (
            len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
            or name in expected or Path(name).name != name or name == signed.name
        ):
            raise ValueError("SOURCE_SHA_IDENTITY_UNSAFE")
        expected[name] = digest
    actual = {p.name for p in folder.iterdir() if p.is_file()} - {signed.name}
    if actual != set(expected):
        raise ValueError("SOURCE_FILES_NOT_EXACT_WITNESS")
    for name, digest in expected.items():
        if sha((folder / name).read_bytes()) != digest:
            raise ValueError("SOURCE_ORIGINAL_SHA_MISMATCH")
    return expected


def _utc_ms(text: Any) -> int:
    if not isinstance(text, str) or not text.endswith("Z"):
        raise ValueError("SOURCE_TIMESTAMP_MISSING_UTC")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("SOURCE_TIMESTAMP_INVALID") from exc
    if dt.tzinfo != UTC:
        raise ValueError("SOURCE_TIMESTAMP_NOT_UTC")
    return int(dt.timestamp() * 1000)


def _side(
    folder: Path, meta: dict, canonical: str, window: int, side: str,
    start: int, end: int,
) -> tuple[list[tuple[int, int]], int]:
    prefix = f"{canonical.lower()}-{window}-{side}"
    native_name = prefix + "-integer.jsonl"
    decoded_name = prefix + "-decoded.jsonl"
    if (meta.get("native_int_file") != native_name
            or meta.get("decoded_file") != decoded_name):
        raise ValueError("SOURCE_SIDE_FILE_IDENTITY_DRIFT")
    native = (folder / native_name).read_bytes()
    decoded = (folder / decoded_name).read_bytes()
    if sha(native) != meta.get("native_int_sha256") or sha(decoded) != meta.get("decoded_sha256"):
        raise ValueError("SOURCE_SIDE_MANIFEST_SHA_CONFLICT")
    a = [json.loads(x) for x in native.splitlines()]
    b = [json.loads(x) for x in decoded.splitlines()]
    if not a or len(a) != len(b) or len(a) != meta.get("native_tick_count"):
        raise ValueError("SOURCE_SIDE_COUNT_MISMATCH_OR_EMPTY")
    requests = meta.get("historical_provider_requests")
    if type(requests) is not int or not 1 <= requests <= 64:
        raise ValueError("SOURCE_SIDE_PAGINATION_INVALID")
    last: tuple[int, int] | None = None
    repeats = 0
    rows: list[tuple[int, int]] = []
    for i, (left, right) in enumerate(zip(a, b, strict=True)):
        t, price = left.get("epoch_ms"), left.get("integer_price_1e5")
        if type(t) is not int or type(price) is not int or price <= 0 or not start <= t < end:
            raise ValueError("SOURCE_NATIVE_TICK_OUTSIDE_OR_INVALID")
        if right.get("native_sequence") != i or _utc_ms(right.get("event_time_utc")) != t:
            raise ValueError("SOURCE_DECODER_TIMESTAMP_SEQUENCE_MISMATCH")
        if Decimal(str(right.get("price"))) != Decimal(price) / SCALE:
            raise ValueError("SOURCE_DECODER_NATIVE_PRICE_MISMATCH")
        if last is not None and t < last[0]:
            raise ValueError("SOURCE_NATIVE_SIDE_OUT_OF_ORDER")
        if last is not None and t == last[0]:
            repeats += 1
            if price != last[1]:
                # With 1ms timestamps, sorting tied prices changes event order.
                # Better to block reconstruction than synthesize causality.
                raise ValueError("SOURCE_SAME_MS_CONFLICTING_PRICE_AMBIGUOUS")
        last = (t, price)
        rows.append(last)
    return rows, repeats


def asof_quality(bid: list[tuple[int, int]], ask: list[tuple[int, int]]) -> dict[str, Any]:
    if not bid or not ask:
        raise ValueError("SOURCE_MISSING_BID_OR_ASK")
    times = sorted({t for t, _ in bid} | {t for t, _ in ask})
    i = j = 0
    b: tuple[int, int] | None = None
    a: tuple[int, int] | None = None
    counts = {"missing_side": 0, "stale_side": 0, "crossed_spread": 0,
              "zero_spread": 0, "positive_spread": 0}
    positive: list[Decimal] = []
    for current in times:
        while i < len(bid) and bid[i][0] <= current:
            b = bid[i]
            i += 1
        while j < len(ask) and ask[j][0] <= current:
            a = ask[j]
            j += 1
        if b is None or a is None:
            counts["missing_side"] += 1
        elif current - b[0] > MAX_SIDE_AGE_MS or current - a[0] > MAX_SIDE_AGE_MS:
            counts["stale_side"] += 1
        elif a[1] < b[1]:
            counts["crossed_spread"] += 1
        elif a[1] == b[1]:
            counts["zero_spread"] += 1
        else:
            counts["positive_spread"] += 1
            positive.append(Decimal(20000) * Decimal(a[1] - b[1]) / Decimal(a[1] + b[1]))
    if sum(counts.values()) != len(times):
        raise ValueError("SOURCE_ASOF_QUALITY_PARTITION_NOT_EXHAUSTIVE")
    positive.sort()
    def pct(fraction: int) -> float | None:
        if not positive:
            return None
        index = max(0, math.ceil(fraction * len(positive) / 100) - 1)
        return round(float(positive[index]), 6)
    return {
        "source_distinct_asof_instants": len(times),
        "quality_counts": counts,
        "positive_spread_p50_bps": pct(50),
        "positive_spread_p95_bps": pct(95),
        "positive_spread_max_bps": pct(100),
        "spread_at_strategy_entry_exit_verified": False,
        "NET_economics_measured": False,
    }


def audit_symbol(folder: Path, canonical: str) -> dict[str, Any]:
    if canonical not in SYMBOL_ARTIFACT:
        raise ValueError("SOURCE_CANONICAL_SYMBOL_OUT_OF_SCOPE")
    witness = _verified_files(folder)
    manifest = json.loads((folder / SOURCE_MANIFEST).read_bytes())
    expected = SYMBOL_ARTIFACT[canonical]
    if (
        manifest.get("identity") != "QORE_NATIVE_G1_CROSSASSET_ICMARKETS_BIDASK_SOURCE_V1"
        or manifest.get("canonical_symbol") != canonical
        or manifest.get("provider_symbol") != expected["provider"]
        or manifest.get("expected_provider_symbol") != expected["provider"]
        or type(manifest.get("provider_symbol_id")) is not int
        or manifest["provider_symbol_id"] <= 0
        or manifest.get("provider") != "ICMARKETS_CTRADER_DEMO"
        or manifest.get("account_type") != "DEMO"
        or manifest.get("g0_source_sha256") != SOURCE_G0_SHA
        or manifest.get("m1_native_source_run") != 38262534602
        or manifest.get("source_result") != "THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
        or manifest.get("windows_frozen_utc") != [list(x) for x in WINDOWS]
        or manifest.get("complete_windows") != 3
        or manifest.get("NET_economics_authorized") is not False
        or manifest.get("33_market_history_proven") is not False
        or manifest.get("historical_contract_equivalence_to_G0_proven") is not False
        or manifest.get("native_protobuf_bytes_archived") is not False
        or manifest.get("trade_orders_sent") != 0
        or manifest.get("token_refresh_attempts") != 0
        or manifest.get("certified_traders") != 0
    ):
        raise ValueError("SOURCE_MANIFEST_BROKER_OR_SCIENTIFIC_SCOPE_INVALID")
    windows = manifest.get("windows")
    if not isinstance(windows, list) or len(windows) != 3:
        raise ValueError("SOURCE_WINDOW_COUNT_NOT_3")
    out = []
    for index, (window, times) in enumerate(zip(windows, WINDOWS, strict=True), 1):
        if window.get("utc_range") != list(times) or window.get("both_sides_nonempty") is not True:
            raise ValueError("SOURCE_WINDOW_PREREG_DRIFT")
        start = int(datetime.fromisoformat(times[0]).timestamp() * 1000)
        end = int(datetime.fromisoformat(times[1]).timestamp() * 1000)
        sides = window["by_side"]
        bid, repeated_bids = _side(folder, sides["BID"], canonical, index, "BID", start, end)
        ask, repeated_asks = _side(folder, sides["ASK"], canonical, index, "ASK", start, end)
        q = asof_quality(bid, ask)
        q.update({
            "frozen_window_utc": list(times),
            "native_bid_ticks": len(bid), "native_ask_ticks": len(ask),
            "same_ms_identical_bid": repeated_bids,
            "same_ms_identical_ask": repeated_asks,
        })
        out.append(q)
    return {
        "identity": IDENTITY,
        "status": "SOURCE_SHA_AND_ASOF_VALIDATED_NOT_NET",
        "canonical_symbol": canonical, "provider_symbol": expected["provider"],
        "source_run": SOURCE_RUN, "source_sha": SOURCE_HEAD,
        "original_artifact_id": expected["id"],
        "original_artifact_zip_sha256_expected": expected["zip_sha256"],
        "original_zip_bytes_not_reloaded_in_this_job": True,
        "source_files_sha256_verified": len(witness),
        "original_manifest_sha256": witness[SOURCE_MANIFEST],
        "bid_ticks": sum(x["native_bid_ticks"] for x in out),
        "ask_ticks": sum(x["native_ask_ticks"] for x in out),
        "total_native_ticks": sum(x["native_bid_ticks"] + x["native_ask_ticks"] for x in out),
        "windows": out,
        "historical_33_market_bidask_coverage_proven": False,
        "original_provider_protobuf_bytes_independently_redecoded": False,
        "historical_execution_cost_verified": False,
        "historical_NET_authorized": False, "certified_traders": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("canonical", choices=sorted(SYMBOL_ARTIFACT))
    p.add_argument("source_dir", type=Path)
    p.add_argument("result_dir", type=Path)
    args = p.parse_args()
    report = audit_symbol(args.source_dir, args.canonical)
    args.result_dir.mkdir(parents=True, exist_ok=True)
    output = args.result_dir / f"{args.canonical}-asof-integrity-NOT-NET.json"
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.result_dir / "SHA256SUMS.txt").write_text(sha(output.read_bytes()) + "  " + output.name + "\n")
    print(json.dumps({
        "market": args.canonical, "status": report["status"],
        "bid": report["bid_ticks"], "ask": report["ask_ticks"],
        "quality": [w["quality_counts"] for w in report["windows"]],
        "historical_NET_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
