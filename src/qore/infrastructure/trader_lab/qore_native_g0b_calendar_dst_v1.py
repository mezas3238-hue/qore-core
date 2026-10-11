"""QORE Native G0B: nominal session observability from G0 bitmaps, no prices/returns.

Never conflates candidate clocks with certified provider trading hours.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SOURCE_RUN = 38166675573
SOURCE_SHA = "fb22970798a2bd93f097f1327ce9c864eec0bb9c"
START = date(2025, 9, 17)
END_EXCLUSIVE = date(2026, 9, 17)
UNIVERSE = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "AUDJPY",
            "GBPJPY", "XAUUSD", "USDCAD", "NAS100")
PAIRS = (("EURUSD", "GBPUSD"), ("AUDUSD", "GBPUSD"), ("AUDJPY", "GBPJPY"))
WINDOWS: dict[str, dict[str, Any]] = {
    "DRIVE_NY_AM": {
        "timezone": "America/New_York", "start": (9, 30), "end": (11, 0),
        "symbols": ("NAS100", "XAUUSD", "EURUSD", "GBPUSD"), "pairs": (),
    },
    "RESET_LDN_FIX_CONTEXT": {
        "timezone": "Europe/London", "start": (15, 45), "end": (16, 15),
        "symbols": ("EURUSD", "GBPUSD", "USDJPY"), "pairs": (),
    },
    "RELATIVE_LDN_AM": {
        "timezone": "Europe/London", "start": (8, 0), "end": (12, 0),
        "symbols": (), "pairs": PAIRS,
    },
    "RELATIVE_NY_AM": {
        "timezone": "America/New_York", "start": (9, 0), "end": (11, 0),
        "symbols": (), "pairs": PAIRS,
    },
}
MASK_LIMIT = (1 << 1440) - 1


def utc_candidate_minutes(local_day: date, definition: dict[str, Any]) -> list[datetime]:
    """Use IANA local civil time; no manual DST offsets or weekend substitutions."""
    if local_day.weekday() >= 5:
        return []
    tz = ZoneInfo(definition["timezone"])
    h0, m0 = definition["start"]
    h1, m1 = definition["end"]
    start = datetime.combine(local_day, time(h0, m0), tz)
    end = datetime.combine(local_day, time(h1, m1), tz)
    if end <= start:
        raise ValueError("window must end later on same local day")
    n = int((end - start).total_seconds() / 60)
    return [(start + timedelta(minutes=i)).astimezone(UTC) for i in range(n)]


def mask_contains(masks: dict[str, int], minute: datetime) -> bool:
    if minute.tzinfo is None or minute.utcoffset() != timedelta(0):
        raise ValueError("minute must be UTC aware")
    return bool(masks.get(minute.date().isoformat(), 0)
                & (1 << (minute.hour * 60 + minute.minute)))


def load_bitmaps(root: Path) -> tuple[dict[str, dict[str, int]], dict[str, str]]:
    paths = sorted(root.rglob("qore-native-G0-*-minute-bitmaps.json"))
    if len(paths) != len(UNIVERSE):
        raise ValueError(f"expected exactly nine G0 minute bitmaps, found {len(paths)}")
    out: dict[str, dict[str, int]] = {}
    digests: dict[str, str] = {}
    for path in paths:
        raw = path.read_bytes()
        payload = json.loads(raw)
        symbol = payload.get("symbol")
        if symbol not in UNIVERSE or symbol in out:
            raise ValueError(f"unknown or duplicate symbol: {symbol}")
        if payload.get("identity") != "QORE_NATIVE_G0_NINE_MARKET_M1_SOURCE_AUDIT_V1":
            raise ValueError(f"unexpected bitmap identity for {symbol}")
        days = payload.get("days")
        minutes_by_day = payload.get("minutes_by_day")
        if not isinstance(days, dict) or not isinstance(minutes_by_day, dict):
            raise ValueError("missing day bitmaps or count witness")
        if set(days) != set(minutes_by_day):
            raise ValueError(f"day count keys differ for {symbol}")
        parsed: dict[str, int] = {}
        for iso_day, hexbits in days.items():
            d = date.fromisoformat(iso_day)
            if not START <= d < END_EXCLUSIVE:
                raise ValueError(f"day outside frozen sample: {iso_day}")
            if not isinstance(hexbits, str) or len(hexbits) != 360:
                raise ValueError(f"malformed 1440-bit hex mask: {symbol} {iso_day}")
            number = int(hexbits, 16)
            if number < 0 or number > MASK_LIMIT:
                raise ValueError("bitmask exceeds 1440 minutes")
            if type(minutes_by_day[iso_day]) is not int or (
                number.bit_count() != minutes_by_day[iso_day]
            ):
                raise ValueError(f"bit count witness disagreement: {symbol} {iso_day}")
            parsed[iso_day] = number
        out[symbol] = parsed
        digests[symbol] = hashlib.sha256(raw).hexdigest()
    return out, digests


def days_in_scope() -> list[date]:
    return [START + timedelta(days=i)
            for i in range((END_EXCLUSIVE - START).days)
            if (START + timedelta(days=i)).weekday() < 5]


def bucket_stats(minutes: list[datetime], masks: dict[str, int], width: int) -> dict[str, int]:
    """Count only fully contained UTC 15m/60m buckets; no reconstructed bars."""
    scheduled = set(minutes)
    buckets: set[datetime] = set()
    for m in minutes:
        first_minute = (m.hour * 60 + m.minute) // width * width
        base = m.replace(hour=0, minute=0) + timedelta(minutes=first_minute)
        buckets.add(base)
    contained = 0
    full = 0
    for base in buckets:
        block = [base + timedelta(minutes=i) for i in range(width)]
        if all(t in scheduled for t in block):
            contained += 1
            if all(mask_contains(masks, t) for t in block):
                full += 1
    return {"fully_contained_buckets": contained, "complete_buckets": full,
            "incomplete_buckets": contained - full}


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected = sum(row["expected_minutes"] for row in rows)
    observed = sum(row["observed_minutes"] for row in rows)
    full = sum(row["observed_minutes"] == row["expected_minutes"] for row in rows)
    mostly = sum(row["expected_minutes"] * 0.95 <= row["observed_minutes"] <
                 row["expected_minutes"] for row in rows)
    return {
        "nominal_weekdays": len(rows), "nominal_expected_minutes": expected,
        "observed_minutes": observed, "missing_minutes_unattributed": expected - observed,
        "observed_fraction": round(observed / expected, 8) if expected else None,
        "fully_observed_days": full, "partly_observed_ge95pct_days": mostly,
        "partly_observed_lt95pct_days": len(rows) - full - mostly,
        "provider_calendar_verified": False, "broker_contract_verified": False,
        "execution_costs_verified": False, "OOS_unseen": False,
        "status": "SOURCE_PARTIAL_PROVIDER_UNVERIFIED",
    }


def audit(root: Path, output: Path) -> dict[str, Any]:
    masks, digests = load_bitmaps(root)
    result: dict[str, Any] = {
        "identity": "QORE_NATIVE_G0B_NOMINAL_CLOCK_AVAILABILITY_V1",
        "G0_source_run": SOURCE_RUN, "G0_run_commit": SOURCE_SHA,
        "G0_bitmap_sha256": digests, "G0B_source_integrity": "VALIDATED_BITMASK_COUNTS",
        "scope_start_UTC_day": START.isoformat(),
        "scope_end_UTC_day_exclusive": END_EXCLUSIVE.isoformat(),
        "all_sessions_are_candidate_nominal_clocks_not_provider_certified": True,
        "weekend_local_days_excluded": True, "holidays_excluded": False,
        "provider_broker_calendar_verified": False, "costs_observed": False,
        "future_returns_or_PnL_measured": False, "live_authorized": False,
        "windows": {},
    }
    records: list[dict[str, Any]] = []
    weekdays = days_in_scope()
    for name, spec in WINDOWS.items():
        win: dict[str, Any] = {
            "timezone": spec["timezone"],
            "local_start": "%02d:%02d" % spec["start"],
            "local_end_exclusive": "%02d:%02d" % spec["end"],
            "symbols": {}, "pairs": {},
        }
        for symbol in spec["symbols"]:
            symbol_rows = []
            bucket_total: dict[int, dict[str, int]] = {
                width: defaultdict(int) for width in (15, 60)
            }
            for day in weekdays:
                minutes = utc_candidate_minutes(day, spec)
                count = sum(mask_contains(masks[symbol], m) for m in minutes)
                row = {"window": name, "kind": "single", "instrument": symbol,
                       "local_day": day.isoformat(), "expected_minutes": len(minutes),
                       "observed_minutes": count, "missing_unattributed": len(minutes)-count}
                records.append(row)
                symbol_rows.append(row)
                for width in (15, 60):
                    for key, value in bucket_stats(minutes, masks[symbol], width).items():
                        bucket_total[width][key] += value
            win["symbols"][symbol] = {
                **summary(symbol_rows),
                "bucket_m15": dict(bucket_total[15]),
                "bucket_h1": dict(bucket_total[60]),
            }
        for a, b in spec["pairs"]:
            pair_rows = []
            a_missing = 0
            b_missing = 0
            both_missing = 0
            for day in weekdays:
                minutes = utc_candidate_minutes(day, spec)
                common = 0
                for minute in minutes:
                    has_a = mask_contains(masks[a], minute)
                    has_b = mask_contains(masks[b], minute)
                    common += has_a and has_b
                    a_missing += (not has_a) and has_b
                    b_missing += has_a and (not has_b)
                    both_missing += (not has_a) and (not has_b)
                row = {"window": name, "kind": "pair", "instrument": a+"|"+b,
                       "local_day": day.isoformat(), "expected_minutes": len(minutes),
                       "observed_minutes": common,
                       "missing_unattributed": len(minutes)-common}
                records.append(row)
                pair_rows.append(row)
            win["pairs"][a+"|"+b] = {
                **summary(pair_rows),
                "only_leg_A_missing_minutes": a_missing,
                "only_leg_B_missing_minutes": b_missing,
                "both_legs_missing_minutes": both_missing,
                "never_forward_filled": True,
            }
        result["windows"][name] = win
    output.mkdir(parents=True, exist_ok=True)
    (output/"qore-native-G0B-calendar-observability.json").write_text(
        json.dumps(result, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    with (output/"qore-native-G0B-per-day-window-census.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "window", "kind", "instrument", "local_day",
            "expected_minutes", "observed_minutes", "missing_unattributed"])
        writer.writeheader()
        writer.writerows(records)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bitmaps", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = audit(args.bitmaps, args.output)
    print(json.dumps({
        "identity": result["identity"],
        "number_windows": len(result["windows"]),
        "broker_calendar_verified": result["provider_broker_calendar_verified"],
        "future_returns_measured": result["future_returns_or_PnL_measured"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
