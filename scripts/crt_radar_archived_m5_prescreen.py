#!/usr/bin/env python3
"""Read-only, single-symbol CRT calibration prescreen over existing cTrader M5 archives.

Never prints/saves raw prices, source rows, account credentials, or trade advice.
Never treats older already-consumed research archives as untouched holdout.
Only uses original source paths in the ephemeral GitHub Actions runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
M5_SECONDS = 300
C1_HOURS = {"forex": frozenset((1, 5, 21)), "index": frozenset((2, 6, 22))}
CAL_START = datetime(2026, 8, 1, tzinfo=UTC)
CAL_END = datetime(2026, 9, 17, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class M5:
    opened_at: datetime
    open: int
    high: int
    low: int
    close: int


@dataclass(frozen=True, slots=True)
class H4:
    opened_at: datetime
    closed_at: datetime
    ny_hour: int
    c1_allowed: bool
    open: int
    high: int
    low: int
    close: int


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for data in iter(lambda: source.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def native_to_bar(row: dict[str, object], symbol: str, provider_id: int) -> M5:
    if row.get("canonical_symbol") != symbol or row.get("provider_symbol") != symbol:
        raise ValueError("SYMBOL_PROVENANCE_MISMATCH")
    if type(row.get("provider_symbol_id")) is not int or row["provider_symbol_id"] != provider_id:
        raise ValueError("PROVIDER_ID_MISMATCH")
    keys = ("utc_timestamp_in_minutes", "low_relative", "delta_open", "delta_high",
            "delta_close", "open_relative", "high_relative", "close_relative")
    if any(type(row.get(key)) is not int for key in keys):
        raise ValueError("INVALID_NATIVE_INTEGER_FIELDS")
    minute = int(row["utc_timestamp_in_minutes"])
    if minute % 5 != 0 or minute <= 0:
        raise ValueError("M5_TIMESTAMP_UNALIGNED")
    instant = datetime.fromtimestamp(minute * 60, UTC)
    opened = datetime.fromisoformat(str(row.get("opened_at", ""))).astimezone(UTC)
    if opened != instant:
        raise ValueError("M5_ISO_TIMESTAMP_MISMATCH")
    low = int(row["low_relative"])
    op = int(row["open_relative"])
    high = int(row["high_relative"])
    close = int(row["close_relative"])
    if (low <= 0 or min(int(row["delta_open"]), int(row["delta_high"]),
         int(row["delta_close"])) < 0 or
        op != low + int(row["delta_open"]) or
        high != low + int(row["delta_high"]) or
        close != low + int(row["delta_close"]) or
        high < max(op, close)):
        raise ValueError("NATIVE_RELATIVE_OHLC_BROKEN")
    return M5(instant, op, high, low, close)


def frozen_bucket(bar: M5, family: str) -> tuple[str, int]:
    ny = bar.opened_at.astimezone(NY)
    origin = 2 if family == "index" else 1
    hr = (origin + 4 * (((ny.hour - origin) % 24) // 4)) % 24
    date = ny.date() - timedelta(days=1) if ny.hour < origin else ny.date()
    return (f"{date.isoformat()}T{hr:02d}", hr)


def completed_h4(bars: list[M5], family: str) -> H4 | None:
    if len(bars) != 48:
        return None
    first, last = bars[0], bars[-1]
    hour = frozen_bucket(first, family)[1]
    first_local = first.opened_at.astimezone(NY)
    last_local = (last.opened_at + timedelta(minutes=5)).astimezone(NY)
    if (first_local.hour != hour or first_local.minute != 0 or
        last_local.hour != (hour + 4) % 24 or last_local.minute != 0):
        return None
    if any(bars[i].opened_at - bars[i - 1].opened_at != timedelta(minutes=5)
           for i in range(1, len(bars))):
        return None
    return H4(first.opened_at, last.opened_at + timedelta(minutes=5),
              hour, hour in C1_HOURS[family],
              first.open, max(b.high for b in bars),
              min(b.low for b in bars), last.close)


def _verify_2026_partition(root: Path) -> tuple[Path, dict[str, object]]:
    manifests = list(root.rglob("symbol-consumption-manifest.json"))
    if len(manifests) != 1:
        raise ValueError("UNIQUE_SOURCE_MANIFEST_REQUIRED")
    m_path = manifests[0]
    m = json.loads(m_path.read_text(encoding="utf-8"))
    if m.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD":
        raise ValueError("SOURCE_INTEGRITY_NOT_CLEAN")
    source_root = m_path.parent
    raw_files = list(source_root.rglob("RAW_M5_LEDGER/2026.jsonl"))
    if len(raw_files) != 1:
        raise ValueError("2026_RAW_LEDGER_PARTITION_MISSING_OR_DUPLICATED")
    raw_path = raw_files[0]
    expected_path = source_root / "PARTITION_MANIFEST" / "2026.sha256"
    if not expected_path.is_file():
        raise ValueError("ORIGINAL_PARTITION_HASH_MANIFEST_MISSING")
    hashes: dict[str, str] = {}
    for line in expected_path.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2 or len(fields[0]) != 64:
            raise ValueError("ORIGINAL_HASH_LINE_INVALID")
        hashes[fields[1].lstrip("*").strip()] = fields[0].lower()
    rel = "RAW_M5_LEDGER/2026.jsonl"
    if rel not in hashes or sha256(raw_path) != hashes[rel]:
        raise ValueError("ORIGINAL_2026_M5_SHA256_MISMATCH")
    return raw_path, m


def inspect(source_root: Path, symbol: str, family: str, cohort: str) -> dict[str, object]:
    if family not in C1_HOURS or cohort not in (
        "ATLAS_DEMO_BROKER_UNVERIFIED", "ICMARKETS_DEMO_CONFIRMED"
    ):
        raise ValueError("UNSUPPORTED_SOURCE_FAMILY_OR_COHORT")
    raw_path, manifest = _verify_2026_partition(source_root)
    if manifest.get("canonical_symbol") != symbol or manifest.get("provider_symbol") != symbol:
        raise ValueError("MANIFEST_SYMBOL_DOES_NOT_MATCH_JOB")
    provider_id = manifest.get("provider_symbol_id")
    if type(provider_id) is not int or provider_id <= 0:
        raise ValueError("UNVERIFIED_PROVIDER_SYMBOL_ID")
    accepted = 0
    total = 0
    skipped = 0
    last_time: datetime | None = None
    current_key: str | None = None
    current: list[M5] = []
    valid_h4: H4 | None = None
    prev_candidate: tuple[H4, int] | None = None
    eligible_c1 = 0
    structural_2c = 0
    structural_3c = 0
    partial_h4 = 0
    internal_m5 = 0

    def consume_bucket(group: list[M5]) -> None:
        nonlocal valid_h4, prev_candidate, eligible_c1, structural_2c
        nonlocal structural_3c, partial_h4, internal_m5
        if not group:
            return
        h4 = completed_h4(group, family)
        if h4 is None:
            partial_h4 += 1
            if any(group[i].opened_at - group[i - 1].opened_at != timedelta(minutes=5)
                   for i in range(1, len(group))):
                internal_m5 += 1
            prev_candidate = None
            valid_h4 = None
            return
        if h4.c1_allowed:
            eligible_c1 += 1
        if valid_h4 is not None and h4.opened_at == valid_h4.closed_at:
            high_sweep = h4.high > valid_h4.high
            low_sweep = h4.low < valid_h4.low
            if (valid_h4.c1_allowed and high_sweep != low_sweep and
                valid_h4.low <= h4.close <= valid_h4.high):
                structural_2c += 1
                prev_candidate = (h4, 1 if low_sweep else -1)
            elif prev_candidate is not None:
                c2, direction = prev_candidate
                if (c2.closed_at == h4.opened_at and
                    (h4.close >= c2.low if direction == 1 else h4.close <= c2.high)):
                    structural_3c += 1
                prev_candidate = None
        else:
            prev_candidate = None
        valid_h4 = h4

    with raw_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            b = native_to_bar(row, symbol, provider_id)
            total += 1
            if last_time is not None and b.opened_at <= last_time:
                raise ValueError("SOURCE_M5_NONMONOTONIC_OR_DUPLICATE")
            last_time = b.opened_at
            if b.opened_at < CAL_START or b.opened_at >= CAL_END:
                skipped += 1
                continue
            accepted += 1
            key, _ = frozen_bucket(b, family)
            if current_key != key:
                consume_bucket(current)
                current = []
                current_key = key
            current.append(b)
    consume_bucket(current)
    if accepted < 100:
        raise ValueError("INSUFFICIENT_CALIBRATION_M5")
    return {
        "symbol": symbol,
        "cohort": cohort,
        "mode": "PREVIOUSLY_CONSUMED_CALIBRATION_ONLY",
        "original_partition_sha256": "VERIFIED",
        "original_m5_rows_examined": total,
        "calibration_m5_rows": accepted,
        "calibration_h4_complete": eligible_c1,
        "rejected_h4_blocks": partial_h4,
        "internal_m5_blocks": internal_m5,
        "crt2c_structural_occurrences": structural_2c,
        "crt3c_followups_diagnostic": structural_3c,
        "holdout_untouched": False,
        "full_pine_parity_verified": False,
        "mss_m15_verified": False,
        "orders_enabled": False,
        "live_alerts_enabled": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--family", required=True, choices=tuple(C1_HOURS))
    parser.add_argument("--cohort", required=True)
    args = parser.parse_args()
    report = inspect(args.root, args.symbol, args.family, args.cohort)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
