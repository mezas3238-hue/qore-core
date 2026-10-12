"""Second, independent decoder of original cTrader ProtoOATickData field bytes.

No provider requests, no credentials, no trade ledgers. This auditor refuses
to accept producer-normalised JSONL absent original byte-for-byte wire parity,
full hasMore leaf coverage, source SHA and frozen dates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATickData
from qore.infrastructure.trader_lab.qore_native_g1_proto_wire_5market_pilot_v1 import (
    IDENTITY as SOURCE_IDENTITY,
    TARGETS, WINDOWS, PARENT_G0_SHA,
)

IDENTITY = "QORE_NATIVE_G1_FIVE_MARKET_ORIGINAL_PROTO_WIRE_SECOND_AUDIT_V1"
SOURCE_MANIFEST = "G1_PROTO_WIRE_PILOT_NOT_NET.json"
MAX_AGE_MS = 5000


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_register(folder: Path, register: str, expected_count: int) -> dict[str, str]:
    witness = folder / register
    if not witness.is_file():
        raise ValueError("SOURCE_SHA_REGISTER_MISSING")
    files: dict[str, str] = {}
    for line in witness.read_text(encoding="utf-8").splitlines():
        args = line.split(maxsplit=1)
        if len(args) != 2:
            raise ValueError("SOURCE_SHA_ENTRY_INVALID")
        hexdigest, name = args
        if (len(hexdigest) != 64 or any(c not in "0123456789abcdef" for c in hexdigest)
                or name in files or Path(name).name != name or name == register):
            raise ValueError("SOURCE_SHA_ENTRY_UNSAFE")
        files[name] = hexdigest
    actual = {p.name for p in folder.iterdir() if p.is_file()} - {register}
    if actual != set(files) or len(files) != expected_count:
        raise ValueError("SOURCE_SHA_FILE_SET_INCOMPLETE")
    for name, expected in files.items():
        if digest((folder/name).read_bytes()) != expected:
            raise ValueError("SOURCE_SHA_BYTES_TAMPERED")
    return files


def decode_batch_fields(blob: bytes, start_ms: int, stop_ms: int) -> list[tuple[int, int]]:
    """Separate decoder, using original field protobuf, not source's decode_native."""
    parsed = []
    cursor = 0
    while cursor < len(blob):
        if cursor + 4 > len(blob):
            raise ValueError("SOURCE_PROTO_FRAME_HEADER_TRUNCATED")
        length = struct.unpack_from(">I", blob, cursor)[0]
        cursor += 4
        if length == 0 or length > 1000 or cursor + length > len(blob):
            raise ValueError("SOURCE_PROTO_FRAME_LENGTH_INVALID")
        native = ProtoOATickData()
        try:
            native.ParseFromString(blob[cursor:cursor + length])
        except Exception as exc:
            raise ValueError("SOURCE_PROTO_FRAME_CANNOT_PARSE") from exc
        cursor += length
        if not native.IsInitialized():
            raise ValueError("SOURCE_PROTO_TICK_FIELDS_NOT_INITIALIZED")
        t, price = int(native.timestamp), int(native.tick)
        if not parsed:
            absolute_ms = t
            absolute_price = price
        else:
            if t > 0:
                raise ValueError("SOURCE_PROTO_TIME_DELTA_NOT_NEWEST_FIRST")
            absolute_ms = parsed[-1][0] + t
            absolute_price = parsed[-1][1] + price
        if (absolute_price <= 0 or not start_ms <= absolute_ms <= stop_ms
                or parsed and parsed[-1][0] < absolute_ms):
            raise ValueError("SOURCE_PROTO_NATIVE_CUMULATIVE_PRICE_TIME_INVALID")
        parsed.append((absolute_ms, absolute_price))
    if cursor != len(blob):
        raise ValueError("SOURCE_PROTO_FRAME_TRAILING_BYTES")
    return parsed


def verify_side(folder: Path, symbol: str, idx: int, side: str, data: dict,
                first: int, last: int) -> list[tuple[int, int]]:
    prefix = f"{symbol}-{idx}-{side}"
    required = {
        "native_file": prefix + "-integer.jsonl",
        "decimal_file": prefix + "-decimal.jsonl",
        "wire_file": prefix + "-tick-fields.pbframes",
    }
    for key, name in required.items():
        if data.get(key) != name:
            raise ValueError("SOURCE_PROTO_SIDE_FILENAME_DRIFT")
    native = (folder/required["native_file"]).read_bytes()
    decimal = (folder/required["decimal_file"]).read_bytes()
    original_wire = (folder/required["wire_file"]).read_bytes()
    if (digest(native) != data.get("native_sha256")
            or digest(decimal) != data.get("decimal_sha256")
            or digest(original_wire) != data.get("wire_sha256")
            or data.get("wire_tick_fields_only_account_wrapper_excluded") is not True):
        raise ValueError("SOURCE_PROTO_SIDE_INTEGRITY_OR_SAFETY_INVALID")
    pages = data.get("wire_pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("SOURCE_PROTO_PAGES_MISSING")
    if len(pages) != data.get("total_provider_requests") or len(pages) > 64:
        raise ValueError("SOURCE_PROTO_PAGE_COUNT_INVALID")
    expected_ranges = [(first, last-1)]
    used: list[tuple[int, int]] = []
    offset = 0
    for page in pages:
        if not expected_ranges:
            raise ValueError("SOURCE_PROTO_EXTRA_PAGE")
        a, b = expected_ranges.pop()
        if (page.get("from_ms") != a or page.get("to_ms") != b
                or type(page.get("has_more")) is not bool
                or page.get("accepted_leaf") is not (not page["has_more"])):
            raise ValueError("SOURCE_PROTO_PAGE_RANGE_OR_HASMORE_INVALID")
        size = page.get("wire_length")
        if (type(size) is not int or size < 0 or page.get("wire_offset") != offset
                or offset + size > len(original_wire)):
            raise ValueError("SOURCE_PROTO_PAGE_BYTE_BOUNDARY_INVALID")
        portion = original_wire[offset:offset+size]
        offset += size
        if digest(portion) != page.get("wire_section_sha256"):
            raise ValueError("SOURCE_PROTO_PAGE_SHA_MISMATCH")
        rows = decode_batch_fields(portion, a, b)
        if len(rows) != page.get("tick_count"):
            raise ValueError("SOURCE_PROTO_PAGE_TICK_COUNT_MISMATCH")
        if page["has_more"]:
            if a == b:
                raise ValueError("SOURCE_PROTO_UNPAGEABLE_MILLISECOND")
            middle = (a+b)//2
            expected_ranges.extend(((middle+1, b), (a, middle)))
        else:
            used.extend(rows)
    if offset != len(original_wire) or expected_ranges:
        raise ValueError("SOURCE_PROTO_UNCOVERED_PAGES_OR_EXTRA_BYTES")
    used.sort(key=lambda t: (t[0], t[1]))
    originals = [json.loads(x) for x in native.splitlines()]
    decimals = [json.loads(x) for x in decimal.splitlines()]
    if not used or len(used) != data.get("count") or len(originals) != len(used) or len(decimals) != len(used):
        raise ValueError("SOURCE_PROTO_ACCEPTED_TICK_COUNT_MISMATCH")
    for seq, ((millis, price), left, right) in enumerate(zip(used, originals, decimals, strict=True)):
        if (left != {"epoch_ms": millis, "integer_price_1e5": price}
                or right.get("native_sequence") != seq):
            raise ValueError("SOURCE_PROTO_NATIVE_INTEGER_OR_SEQUENCE_MISMATCH")
        stamp = datetime.fromtimestamp(millis/1000, tz=UTC)
        exp = stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if right.get("event_time_utc") != exp or Decimal(str(right.get("price"))) != Decimal(price)/Decimal(100000):
            raise ValueError("SOURCE_PROTO_DECIMAL_OR_CLOCK_MISMATCH")
        if seq and used[seq-1][0] == millis and used[seq-1][1] != price:
            raise ValueError("SOURCE_PROTO_INTRA_MS_PRICE_ORDER_AMBIGUOUS")
    return used


def asof_quality(bid: list[tuple[int, int]], ask: list[tuple[int, int]]) -> dict[str, int]:
    if not bid or not ask:
        raise ValueError("SOURCE_PROTO_NO_BID_ASK_PAIR")
    instants = sorted({t for t, _ in bid} | {t for t, _ in ask})
    i = j = 0
    b: tuple[int, int] | None = None
    a: tuple[int, int] | None = None
    counts: Counter[str] = Counter()
    for t in instants:
        while i < len(bid) and bid[i][0] <= t:
            b = bid[i]
            i += 1
        while j < len(ask) and ask[j][0] <= t:
            a = ask[j]
            j += 1
        if b is None or a is None:
            counts["missing_side"] += 1
        elif t-b[0] > MAX_AGE_MS or t-a[0] > MAX_AGE_MS:
            counts["stale_side"] += 1
        elif a[1] < b[1]:
            counts["crossed_spread"] += 1
        elif a[1] == b[1]:
            counts["zero_spread"] += 1
            if b[0] == t and a[0] == t:
                counts["zero_same_millisecond"] += 1
        else:
            counts["positive_spread"] += 1
    if sum(counts[k] for k in (
            "missing_side", "stale_side", "crossed_spread",
            "zero_spread", "positive_spread")) != len(instants):
        raise ValueError("SOURCE_PROTO_ASOF_STATE_PARTITION_INVALID")
    return {key: counts[key] for key in (
        "missing_side", "stale_side", "crossed_spread", "zero_spread",
        "positive_spread", "zero_same_millisecond")}


def audit(root: Path) -> dict[str, Any]:
    top = verify_register(root, "TOP_LEVEL_SHA256SUMS.txt", 1)
    if set(top) != {SOURCE_MANIFEST}:
        raise ValueError("SOURCE_PROTO_TOP_MANIFEST_MISSING")
    manifest = json.loads((root/SOURCE_MANIFEST).read_bytes())
    if (manifest.get("identity") != SOURCE_IDENTITY
            or manifest.get("broker") != "ICMARKETS_CTRADER_DEMO"
            or manifest.get("g0_source_sha256") != PARENT_G0_SHA
            or manifest.get("frozen_windows_utc") != [list(x) for x in WINDOWS]
            or manifest.get("frozen_targets") != TARGETS
            or manifest.get("state") != "G1_FIVE_MARKETS_2_WINDOWS_PROTO_WIRE_CAPTURED_NO_NET"
            or manifest.get("markets_completed") != 5
            or manifest.get("original_request_response_wrapper_account_fields_archived") is not False
            or manifest.get("native_tick_field_protobuf_archived") is not True
            or manifest.get("trades_submitted") != 0
            or manifest.get("oauth_refresh_count") != 0
            or manifest.get("net_economics_authorized") is not False
            or manifest.get("certified_traders") != 0):
        raise ValueError("SOURCE_PROTO_PREREG_OR_AUTH_SAFETY_FAILED")
    if {p.name for p in root.iterdir() if p.is_dir()} != set(TARGETS):
        raise ValueError("SOURCE_PROTO_MARKET_FOLDER_DRIFT")
    reports = []
    total: Counter[str] = Counter()
    for canonical, provider in TARGETS.items():
        folder = root/canonical
        verify_register(folder, "FILE_SHA256SUMS.txt", 13)
        m = json.loads((folder/"SOURCE_MARKET_MANIFEST_NOT_NET.json").read_bytes())
        if (m.get("canonical_symbol") != canonical or m.get("provider_symbol") != provider
                or m.get("native_protobuf_source_state") != "TWO_WINDOWS_ALL_SIDES_WIRE_AVAILABLE_NOT_NET"
                or m.get("complete_windows") != 2
                or type(m.get("source_symbol_id")) is not int or m["source_symbol_id"] <= 0):
            raise ValueError("SOURCE_PROTO_MARKET_SOURCE_STATUS_INVALID")
        windows = m.get("windows")
        if not isinstance(windows, list) or len(windows) != 2:
            raise ValueError("SOURCE_PROTO_WINDOW_SET_INVALID")
        amounts: Counter[str] = Counter()
        for w, freeze in zip(windows, WINDOWS, strict=True):
            if w.get("frozen") != list(freeze) or w.get("both_sides_nonempty") is not True:
                raise ValueError("SOURCE_PROTO_WINDOW_FREEZE_INVALID")
            first, last = (int(datetime.fromisoformat(x).timestamp()*1000) for x in freeze)
            b = verify_side(folder, canonical, windows.index(w)+1, "BID",
                            w["by_side"]["BID"], first, last)
            a = verify_side(folder, canonical, windows.index(w)+1, "ASK",
                            w["by_side"]["ASK"], first, last)
            amounts["bid_ticks"] += len(b)
            amounts["ask_ticks"] += len(a)
            amounts.update(asof_quality(b,a))
        total.update(amounts)
        reports.append({"canonical_symbol": canonical, "provider_symbol": provider,
                        "source_witnesses_sha_verified": 13,
                        "counts": dict(amounts),
                        "no_trade_cost_economics": True})
    return {
        "identity": IDENTITY,
        "status": "SOURCE_WIRE_INDEPENDENT_CUMULATIVE_DELTA_PARITY_PASS_NO_NET",
        "source_markets": 5, "source_windows_per_market": 2,
        "source_field_wire_protobuf_redecoded_independently": True,
        "original_provider_response_wrapper_not_archived": True,
        "source_ticks_total": total["bid_ticks"] + total["ask_ticks"],
        "source_quality_totals": dict(total),
        "original_33_market_broker_contract_equivalent": False,
        "NET_authorized": False, "traders_certified": 0,
        "per_market": reports,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_source", type=Path)
    p.add_argument("output_dir", type=Path)
    args = p.parse_args()
    result = audit(args.original_source)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir/"G1_SOURCE_PROTO_WIRE_INDEPENDENT_QA_NOT_NET.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (args.output_dir/"SHA256SUMS.txt").write_text(
        digest(path.read_bytes()) + "  " + path.name + "\n"
    )
    print(json.dumps({
        "state": result["status"], "ticks": result["source_ticks_total"],
        "quality": result["source_quality_totals"],
        "NET": False, "certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
