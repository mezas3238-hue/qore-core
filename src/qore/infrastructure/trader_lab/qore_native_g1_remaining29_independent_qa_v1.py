"""Independent original 29-market source SHA and BID/ASK as-of QA (NO NET).

Input is the exact GitHub source artifact from the earlier code/clock freeze.
No provider download or trader signal generation. All positive source snapshots
are descriptive; zero/crossed/stale observations are quarantined, not free fills.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_native_g1_remaining29_bidask_census_v1 import (
    EXPECTED_WINDOWS,
    FROZEN_TARGETS,
    IDENTITY as SOURCE_IDENTITY,
    SOURCE_G0_SHA256,
)

IDENTITY = "QORE_NATIVE_G1_PRE_REAL29_NATIVE_SIDE_INDEPENDENT_QA_V1"
ORIGINAL_RUN = 38283737706
ORIGINAL_HEAD = "f8262bd7cdea1fbfb2287c3c1fe0dae3be2b0efc"
ORIGINAL_ARTIFACT_ID = 11762222336
ORIGINAL_ZIP_SHA256 = "be123f91e2069390e3bb44f9ce8b9398e3216b9ce483b7441f7f2aebb918f1c0"
MS_AGE_LIMIT = 5000
SCALE = Decimal(100000)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def check_register(folder: Path, filename: str, expected_count: int | None = None) -> dict[str, str]:
    register = folder / filename
    if not register.is_file():
        raise ValueError("SOURCE_SHA_REGISTER_MISSING")
    known: dict[str, str] = {}
    for line in register.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError("SOURCE_SHA_REGISTER_MALFORMED")
        digest, name = parts
        if (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)
                or name in known or Path(name).name != name or name == filename):
            raise ValueError("SOURCE_SHA_REGISTER_UNSAFE")
        known[name] = digest
    actual = {x.name for x in folder.iterdir() if x.is_file()} - {filename}
    if actual != set(known) or expected_count is not None and len(known) != expected_count:
        raise ValueError("SOURCE_FILE_SET_UNVERIFIED")
    for name, digest in known.items():
        if sha((folder / name).read_bytes()) != digest:
            raise ValueError("SOURCE_SHA_MISMATCH")
    return known


def _utc_ms(text: Any) -> int:
    if not isinstance(text, str) or not text.endswith("Z"):
        raise ValueError("SOURCE_UTC_TIMESTAMP_REQUIRED")
    at = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if at.tzinfo != UTC:
        raise ValueError("SOURCE_CLOCK_NOT_UTC")
    return int(at.timestamp() * 1000)


def audit_side(folder: Path, symbol: str, window: int, label: str, meta: dict,
               earliest: int, latest: int) -> tuple[list[tuple[int, int]], int]:
    expected_native = f"{symbol}-{window}-{label}-integer.jsonl"
    expected_decoded = f"{symbol}-{window}-{label}-decoded.jsonl"
    if (meta.get("native_int_file") != expected_native
            or meta.get("decoded_file") != expected_decoded):
        raise ValueError("SOURCE_SIDE_FILENAME_MISMATCH")
    native = (folder / expected_native).read_bytes()
    decoded = (folder / expected_decoded).read_bytes()
    if sha(native) != meta.get("native_int_sha256") or sha(decoded) != meta.get("decoded_sha256"):
        raise ValueError("SOURCE_SIDE_SHA_CONFLICT")
    nrows = [json.loads(x) for x in native.splitlines()]
    drows = [json.loads(x) for x in decoded.splitlines()]
    if (not nrows or len(nrows) != len(drows)
            or meta.get("native_tick_count") != len(nrows)):
        raise ValueError("SOURCE_NATIVE_SIDE_COUNT_MISMATCH")
    requests = meta.get("historical_provider_requests")
    if type(requests) is not int or not 1 <= requests <= 64:
        raise ValueError("SOURCE_HASMORE_PAGINATION_NOT_ATTESTED")
    events: list[tuple[int, int]] = []
    repeated = 0
    for index, (n, d) in enumerate(zip(nrows, drows, strict=True)):
        t, price = n.get("epoch_ms"), n.get("integer_price_1e5")
        if (type(t) is not int or type(price) is not int or price <= 0
                or not earliest <= t < latest):
            raise ValueError("SOURCE_NATIVE_PRICE_OR_INTERVAL_INVALID")
        if _utc_ms(d.get("event_time_utc")) != t or d.get("native_sequence") != index:
            raise ValueError("SOURCE_DECODER_CLOCK_OR_SEQUENCE_MISMATCH")
        if Decimal(str(d.get("price"))) != Decimal(price) / SCALE:
            raise ValueError("SOURCE_DECODER_DECIMAL_MISMATCH")
        if events and events[-1][0] > t:
            raise ValueError("SOURCE_SIDE_CHRONOLOGY_INVALID")
        if events and events[-1][0] == t:
            repeated += 1
            if events[-1][1] != price:
                raise ValueError("SOURCE_SAME_MILLISECOND_PRICE_ORDER_AMBIGUOUS")
        events.append((t, price))
    return events, repeated


def source_asof(bids: list[tuple[int, int]], asks: list[tuple[int, int]]) -> dict[str, Any]:
    if not bids or not asks:
        raise ValueError("SOURCE_BOTH_SIDES_REQUIRED")
    union = sorted({x[0] for x in bids} | {x[0] for x in asks})
    i = j = 0
    b: tuple[int, int] | None = None
    a: tuple[int, int] | None = None
    counters: Counter[str] = Counter()
    positives: list[Decimal] = []
    for moment in union:
        while i < len(bids) and bids[i][0] <= moment:
            b = bids[i]
            i += 1
        while j < len(asks) and asks[j][0] <= moment:
            a = asks[j]
            j += 1
        if b is None or a is None:
            counters["missing_side"] += 1
        elif moment - b[0] > MS_AGE_LIMIT or moment - a[0] > MS_AGE_LIMIT:
            counters["stale_side"] += 1
        elif a[1] < b[1]:
            counters["crossed_spread"] += 1
        elif a[1] == b[1]:
            counters["zero_spread"] += 1
        else:
            counters["positive_spread"] += 1
            positives.append(Decimal(20000) * Decimal(a[1] - b[1]) / Decimal(a[1] + b[1]))
    keys = ("missing_side", "stale_side", "crossed_spread", "zero_spread", "positive_spread")
    quality = {key: counters[key] for key in keys}
    if sum(quality.values()) != len(union):
        raise ValueError("SOURCE_ASOF_QUALITY_NOT_EXHAUSTIVE")
    positives.sort()
    def pct(p: int) -> float | None:
        if not positives:
            return None
        k = max(0, math.ceil(len(positives) * p / 100) - 1)
        return round(float(positives[k]), 6)
    return {
        "source_distinct_asof_instants": len(union),
        "quality_counts": quality,
        "positive_spread_median_bps": pct(50),
        "positive_spread_p95_bps": pct(95),
        "historical_order_cost_measured": False,
    }


def audit(root: Path) -> dict[str, Any]:
    top = check_register(root, "G1_CENSUS_SHA256SUMS.txt", 1)
    if set(top) != {"G1-29-SOURCE-CENSUS-NOT-NET.json"}:
        raise ValueError("SOURCE_CENSUS_TOP_MANIFEST_MISSING")
    census = json.loads((root / "G1-29-SOURCE-CENSUS-NOT-NET.json").read_bytes())
    if (
        census.get("identity") != SOURCE_IDENTITY
        or census.get("g0_source_sha256") != SOURCE_G0_SHA256
        or census.get("status") != "G1_ALL_29_THREE_WINDOWS_SOURCE_PASS_NOT_NET"
        or census.get("source_markets_requested") != list(FROZEN_TARGETS)
        or census.get("attempted") != 29 or census.get("complete") != 29
        or census.get("historical_NET_authorized") is not False
        or census.get("certified_traders") != 0
        or census.get("token_refresh_attempts") != 0
        or census.get("trade_orders_sent") != 0
    ):
        raise ValueError("SOURCE_CENSUS_PARENT_SCIENTIFIC_STATE_MISMATCH")
    dirs = {p.name for p in root.iterdir() if p.is_dir()}
    if dirs != set(FROZEN_TARGETS):
        raise ValueError("SOURCE_29_SUBFOLDERS_NOT_EXACT")
    out = []
    aggregate: Counter[str] = Counter()
    total_bid = total_ask = 0
    for symbol in FROZEN_TARGETS:
        folder = root / symbol
        known = check_register(folder, "SOURCE_SHA256SUMS.txt", 13)
        if "SOURCE-MANIFEST-NOT-NET.json" not in known:
            raise ValueError("SOURCE_MARKET_MANIFEST_SHA_MISSING")
        data = json.loads((folder / "SOURCE-MANIFEST-NOT-NET.json").read_bytes())
        if (
            data.get("identity") != SOURCE_IDENTITY
            or data.get("canonical_symbol") != symbol
            or data.get("provider_symbol") != symbol
            or type(data.get("provider_symbol_id")) is not int
            or data["provider_symbol_id"] <= 0
            or data.get("provider") != "ICMARKETS_CTRADER_DEMO"
            or data.get("account_type") != "DEMO"
            or data.get("source_g0_sha256") != SOURCE_G0_SHA256
            or data.get("state") != "THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
            or data.get("complete_windows") != 3
            or data.get("source_captured_both_sides") is not True
            or data.get("frozen_windows") != [list(x) for x in EXPECTED_WINDOWS]
            or data.get("historical_NET_authorized") is not False
            or data.get("certified_traders") != 0
            or data.get("historical_10Y_BIDASK_coverage_verified") is not False
            or data.get("source_native_protobuf_bytes_archived") is not False
        ):
            raise ValueError("SOURCE_MARKET_PROVENANCE_INVALID")
        records = data.get("windows")
        if not isinstance(records, list) or len(records) != 3:
            raise ValueError("SOURCE_WINDOW_COUNT_INVALID")
        summaries = []
        for n, (win, times) in enumerate(zip(records, EXPECTED_WINDOWS, strict=True), 1):
            if win.get("utc_range") != list(times) or win.get("both_sides_nonempty") is not True:
                raise ValueError("SOURCE_WINDOW_PREREG_MISMATCH")
            start = int(datetime.fromisoformat(times[0]).timestamp() * 1000)
            stop = int(datetime.fromisoformat(times[1]).timestamp() * 1000)
            sides = win["by_side"]
            bid, bd = audit_side(folder, symbol, n, "BID", sides["BID"], start, stop)
            ask, ad = audit_side(folder, symbol, n, "ASK", sides["ASK"], start, stop)
            quality = source_asof(bid, ask)
            aggregate.update(quality["quality_counts"])
            total_bid += len(bid)
            total_ask += len(ask)
            quality.update({
                "window_index": n, "bid_source_ticks": len(bid),
                "ask_source_ticks": len(ask),
                "bid_identical_same_ms_ties": bd, "ask_identical_same_ms_ties": ad,
            })
            summaries.append(quality)
        out.append({
            "canonical_symbol": symbol, "provider_symbol_id_confirmed": True,
            "source_side_files_sha256_verified": 13,
            "bid_ticks": sum(x["bid_source_ticks"] for x in summaries),
            "ask_ticks": sum(x["ask_source_ticks"] for x in summaries),
            "source_quality_windows": summaries,
        })
    return {
        "identity": IDENTITY, "status": "REAL_29_SOURCE_SHA_ASOF_PASS_NO_NET",
        "source_workflow_run": ORIGINAL_RUN, "source_artifact_id": ORIGINAL_ARTIFACT_ID,
        "source_code_sha": ORIGINAL_HEAD,
        "source_artifact_zip_sha256_expected": ORIGINAL_ZIP_SHA256,
        "original_zip_bytes_not_reverified_by_this_extracted_file_auditor": True,
        "source_market_manifests_verified": len(out),
        "source_market_files_sha_verified": sum(x["source_side_files_sha256_verified"] for x in out),
        "new_bid_ticks": total_bid, "new_ask_ticks": total_ask,
        "new_native_ticks": total_bid + total_ask,
        "asof_source_quality_totals": {k: aggregate[k] for k in (
            "missing_side", "stale_side", "crossed_spread", "zero_spread", "positive_spread"
        )},
        "markets": out,
        "nas100_ustec_contract_equivalence_verified": False,
        "market33_ten_year_historical_bidask_coverage": False,
        "broker_native_protobuf_independently_archived": False,
        "historical_NET_authorized": False,
        "profit_factor_sharpe_sortino_drawdown_measured": False,
        "certified_traders": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_source_folder", type=Path)
    p.add_argument("output_folder", type=Path)
    args = p.parse_args()
    result = audit(args.original_source_folder)
    args.output_folder.mkdir(parents=True, exist_ok=True)
    doc = args.output_folder / "source-29-independent-QA-NOT-NET.json"
    doc.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_folder / "SHA256SUMS.txt").write_text(
        sha(doc.read_bytes()) + "  " + doc.name + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"],
        "markets": result["source_market_manifests_verified"],
        "ticks": result["new_native_ticks"],
        "source_quality": result["asof_source_quality_totals"],
        "NET": False, "certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
