"""QORE Native G0 existing twelve original cTrader DEMO M5 archives.

Only identity, SHA and UTC timestamp availability; never use bar prices, price
directions, returns, conditional patterns, P&L, trade setup or execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IDENTITY = "QORE_NATIVE_EXISTING12_10Y_M5_SOURCE_G0_V1"
PRODUCER = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
PRODUCER_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
SOURCE_RUN = 35166210458
AGGREGATE_ARTIFACT = 10476615509
AGGREGATE_INDEX_SHA256 = "47f5763d7ea2c10dd32fa40a84d7480c8124f1a512b623c1299ef2ba7b8c51c2"
SOURCE_SYMBOL_MAP = {
    "AUDJPY": "AUDJPY", "AUDUSD": "AUDUSD", "EURUSD": "EURUSD",
    "GBPJPY": "GBPJPY", "GBPUSD": "GBPUSD", "NAS100": "USTEC",
    "SP500": "US500", "US30": "US30", "USDCAD": "USDCAD",
    "USDJPY": "USDJPY", "XAGUSD": "XAGUSD", "XAUUSD": "XAUUSD",
}
SYMBOLS = tuple(SOURCE_SYMBOL_MAP)
YEARS = tuple(range(2016, 2027))
FIRST = datetime(2016, 9, 17, tzinfo=UTC)
LAST_EXCLUSIVE = datetime(2026, 9, 17, tzinfo=UTC)
RAW_SCHEMA = "qore.cibo_market_atlas.raw_m5.v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for buf in iter(lambda: file.read(2 * 1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def digest_ledger(path: Path) -> dict[str, str]:
    """Only file SHA ledger; reject duplicate paths or untrusted traversals."""
    digest: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 2 or len(parts[0]) != 64:
            raise ValueError("noncanonical SHA256 witness")
        hash_, name = parts
        if (name.startswith("/") or "\\" in name or name.startswith("../")
                or "/../" in name or name in digest
                or any(char not in "0123456789abcdef" for char in hash_)):
            raise ValueError("duplicate/unsafe SHA256 path")
        digest[name] = hash_
    return digest


def verified_file(root: Path, witness: dict[str, str], name: str) -> Path:
    path = root / name
    if name not in witness or not path.is_file() or sha256(path) != witness[name]:
        raise ValueError("original provider SHA256 invalid/missing: " + name)
    return path


def aggregate_index(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "ten-year-consumption-index.json"
    ledger = digest_ledger(root / "SHA256SUMS.txt")
    verified_file(root, ledger, path.name)
    if sha256(path) != AGGREGATE_INDEX_SHA256:
        raise ValueError("frozen original producer aggregate SHA drift")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "identity": PRODUCER,
        "symbol_count": len(SYMBOLS),
        "total_retained_bars": 8726985,
        "target_start": FIRST.isoformat(),
        "target_end_exclusive": LAST_EXCLUSIVE.isoformat(),
        "transport": "STRICT_FROM_TO_WINDOWED_V1",
        "research_evidence_consumed": True,
        "demo_eligible": False, "live_authorized": False,
        "production_authorized": False, "real_capital_authorized": False,
    }
    for name, expected in required.items():
        if type(data.get(name)) is not type(expected) or data[name] != expected:
            raise ValueError("original aggregate identity/total drift: " + name)
    items = data["symbols"]
    by = {item["canonical_symbol"]: item for item in items}
    if len(items) != len(SYMBOLS) or set(by) != set(SYMBOLS):
        raise ValueError("original fixed 12 market inventory mismatch")
    if any(by[s]["provider_symbol"] != SOURCE_SYMBOL_MAP[s] for s in SYMBOLS):
        raise ValueError("original provider alias map drift")
    if sum(row["retained_bars"] for row in items) != 8726985:
        raise ValueError("original per-market bar total mismatch")
    return by


def audit_timestamp_bucket(
    minute: int,
    previous: int | None,
    h4_bitmap: dict[int, int],
    day_bitmap: dict[int, int],
) -> None:
    """UTC M5 slots only; not a reconstruction of broker H4/D1 candles."""
    if (minute % 5 or previous is not None and minute <= previous):
        raise ValueError("original M5 timestamp non-monotonic/unaligned")
    index_h4 = minute // 240
    offset_h4 = (minute % 240) // 5
    index_day = minute // 1440
    offset_day = (minute % 1440) // 5
    mask_h4 = 1 << offset_h4
    mask_day = 1 << offset_day
    if h4_bitmap.get(index_h4, 0) & mask_h4:
        raise ValueError("duplicate M5 timestamp in UTC H4")
    if day_bitmap.get(index_day, 0) & mask_day:
        raise ValueError("duplicate M5 timestamp in UTC D1")
    h4_bitmap[index_h4] = h4_bitmap.get(index_h4, 0) | mask_h4
    day_bitmap[index_day] = day_bitmap.get(index_day, 0) | mask_day


def audit_symbol(symbol: str, source: Path, aggregate_row: dict[str, Any]) -> dict[str, Any]:
    if symbol not in SOURCE_SYMBOL_MAP:
        raise ValueError("symbol is not in original frozen 12")
    if not source.is_dir():
        raise ValueError("missing producer archive")
    root_ledger = digest_ledger(source / "SYMBOL_SHA256SUMS.txt")
    manifest = verified_file(source, root_ledger, "symbol-consumption-manifest.json")
    verified_file(source, root_ledger, "MANIFEST_SHA256SUMS.txt")
    sha = sha256(manifest)
    m = json.loads(manifest.read_text(encoding="utf-8"))
    if m != aggregate_row:
        raise ValueError("original source symbol manifest does not equal frozen aggregate row")
    if sha256(verified_file(source, root_ledger, "git-sha.txt")) != root_ledger["git-sha.txt"]:
        raise ValueError("producer sha witness mismatch")
    if (source / "git-sha.txt").read_text().strip() != PRODUCER_SHA:
        raise ValueError("archive producer commit differs")
    if (m["identity"] != PRODUCER or m["canonical_symbol"] != symbol
        or m["provider_symbol"] != SOURCE_SYMBOL_MAP[symbol]
        or m["raw_integrity_status"] != "CLEAN_PROVIDER_PAYLOAD"
        or not m["read_only"] or m["live_authorized"]
        or m["production_authorized"] or m["real_capital_authorized"]
        or m["target_start"] != FIRST.isoformat()
        or m["target_end_exclusive"] != LAST_EXCLUSIVE.isoformat()):
        raise ValueError("provider source identity/permissions mismatch")
    if [p.get("partition") for p in m["partitions"]] != [str(y) for y in YEARS]:
        raise ValueError("source annual partition list is not 2016–2026")

    partition_hashes = digest_ledger(source / "MANIFEST_SHA256SUMS.txt")
    if partition_hashes.get(manifest.name) != sha:
        raise ValueError("year-partition manifest master SHA mismatch")
    first_seen: str | None = None
    latest_seen: str | None = None
    all_bars = 0
    prev: int | None = None
    h4_bitmap: dict[int, int] = {}
    day_bitmap: dict[int, int] = {}
    annual: list[dict[str, Any]] = []
    provider_id = m["provider_symbol_id"]
    digits = m["digits"]
    for p in m["partitions"]:
        year = str(p["partition"])
        part_name = f"PARTITION_MANIFEST/{year}.json"
        verified_file(source, partition_hashes, part_name)
        yearly = json.loads((source / part_name).read_text(encoding="utf-8"))
        if yearly != p or yearly["raw_integrity_status"] != "CLEAN_PROVIDER_PAYLOAD":
            raise ValueError("producer partition checksum/data quality discrepancy")
        if any(yearly[k] != 0 for k in (
            "contradictory_bars", "timestamp_alignment_errors", "out_of_window_bars"
        )):
            raise ValueError("source historical quality flag not clean")
        sha_path = f"PARTITION_MANIFEST/{year}.sha256"
        verified_file(source, partition_hashes, sha_path)
        raw_witness = digest_ledger(source / sha_path)
        expected_names = {
            f"RAW_M5_LEDGER/{year}.jsonl", f"DATA_QUALITY_LEDGER/{year}.jsonl"
        }
        if set(raw_witness) != expected_names:
            raise ValueError("missing annual raw/quality SHA")
        raw = verified_file(source, raw_witness, f"RAW_M5_LEDGER/{year}.jsonl")
        verified_file(source, raw_witness, f"DATA_QUALITY_LEDGER/{year}.jsonl")
        n = 0
        year_start: str | None = None
        year_end: str | None = None
        with raw.open("r", encoding="utf-8") as file:
            for line in file:
                # JSON parsed solely for original identity/time fields.
                # OHLC/volume never referenced to derive economics/volatility.
                row = json.loads(line)
                if (row.get("schema") != RAW_SCHEMA or
                    row.get("identity") != PRODUCER or
                    row.get("canonical_symbol") != symbol or
                    row.get("provider_symbol") != SOURCE_SYMBOL_MAP[symbol] or
                    row.get("provider_symbol_id") != provider_id or
                    row.get("digits") != digits):
                    raise ValueError("native M5 row identity drift")
                instant = datetime.fromisoformat(row["opened_at"])
                if instant.tzinfo is None or instant.utcoffset() is None:
                    raise ValueError("native M5 timestamp must include UTC")
                at = instant.astimezone(UTC)
                minute = int(at.timestamp() // 60)
                if (at.year != int(year) or not FIRST <= at < LAST_EXCLUSIVE
                    or at.second != 0 or at.microsecond != 0 or
                    row["utc_timestamp_in_minutes"] != minute):
                    raise ValueError("M5 timestamp outside frozen original scope")
                audit_timestamp_bucket(minute, prev, h4_bitmap, day_bitmap)
                prev = minute
                year_start = year_start or at.isoformat()
                year_end = at.isoformat()
                n += 1
        if n != p["retained_bars"] or year_start != p["first_observed_m5"] or year_end != p["last_observed_m5"]:
            raise ValueError("native M5 bar recount, year boundaries or manifest mismatch")
        first_seen = first_seen or year_start
        latest_seen = year_end
        all_bars += n
        annual.append({
            "year": int(year),
            "native_m5_bars": n,
            "original_sha256": raw_witness[f"RAW_M5_LEDGER/{year}.jsonl"],
            "first_utc": year_start, "last_utc": year_end,
            "raw_quality_gaps_unclassified": p["unresolved_gap_runs"],
            "raw_calendar_slots_unclassified": p["unresolved_calendar_slots"],
        })

    if (all_bars != m["retained_bars"] or
        first_seen != m["earliest_observed_m5"] or
        latest_seen != m["latest_observed_m5"]):
        raise ValueError("source total bar count/first/last does not reconcile")
    def completeness(bitmap: dict[int, int], full_bits: int) -> dict[str, int]:
        full = sum(bits.bit_count() == full_bits for bits in bitmap.values())
        return {
            "observed_active_utc_blocks": len(bitmap),
            "complete_utc_blocks": full,
            "partial_utc_blocks": len(bitmap) - full,
            "slots_per_complete_utc_block": full_bits,
        }
    h4 = completeness(h4_bitmap, 48)
    d1 = completeness(day_bitmap, 288)
    if all_bars < 10 * 365 * 24:  # generous source existence gate, not session completeness
        raise ValueError("insufficient retained original bars even for source inventory")
    return {
        "identity": IDENTITY, "status": "G0_M5_SOURCE_INTEGRITY_PASS",
        "source_run": SOURCE_RUN, "producer_sha": PRODUCER_SHA,
        "source_symbol": symbol, "provider_symbol": SOURCE_SYMBOL_MAP[symbol],
        "symbol_manifest_sha256": sha,
        "all_11_years_raw_and_quality_sha256_verified": True,
        "native_m5_bars": all_bars, "first_utc": first_seen, "last_utc": latest_seen,
        "calendar_session_knowledge": "UNVERIFIED_BROKER_SESSION_CALENDAR",
        "h4_calendar_utc_presence_only": h4,
        "d1_calendar_utc_presence_only": d1,
        "yearly": annual,
        "historical_spreads_bidask_verified": False,
        "price_values_or_economic_outcomes_accessed": False,
        "returns_or_volatility_calculated": False,
        "broker_h4_d1_candles_certified": False,
        "G1_authorized": False,
        "no_live_vps_mt5_cibo_shared_changes": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", choices=SYMBOLS)
    ap.add_argument("original_artifact_root", type=Path)
    ap.add_argument("aggregate_original_artifact_root", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    expected = aggregate_index(args.aggregate_original_artifact_root)
    result = audit_symbol(args.symbol, args.original_artifact_root, expected[args.symbol])
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f"native-existing12-m5-{args.symbol}-g0.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / f"{target.name}.sha256").write_text(
        sha256(target) + f"  {target.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"], "symbol": result["source_symbol"],
        "native_m5": result["native_m5_bars"],
        "complete_H4_UTC": result["h4_calendar_utc_presence_only"]["complete_utc_blocks"],
        "complete_D1_UTC": result["d1_calendar_utc_presence_only"]["complete_utc_blocks"],
        "no_outcomes": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
