"""QORE Native G0C: credential-free, timestamp-only census of existing 7Y DEMO FX.

Uses archived GitHub Actions evidence. Refuses bars at/after VT08's reserved
fresh_cutoff. No market prices are decoded, no outcomes, trading, or OOS claim.
"""
from __future__ import annotations

import argparse
import csv
import json
import mmap
import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.qore_native_existing_demo_fx_archive_inventory_v1 import (
    SOURCE_COMMIT,
    SOURCE_RUN_ID,
    build_inventory,
    metadata_prefix,
)

IDENTITY = "QORE_NATIVE_G0C_EXISTING_7Y_FX_DEV_CLOCK_CENSUS_V1"
LONDON = ZoneInfo("Europe/London")
BAR_PERIOD = timedelta(minutes=5)
EXPECTED_SHA = {
    "EURJPY": "2a3afd8075b70fd7791ffbdefb15214e7174e7be7e0367cfa49037aa6b7af3e5",
    "USDCHF": "6afd148635907ba936a52c25817cacac7397de4da224a1b2581e75fa95e50edf",
}
WINDOWS = {
    "LONDON_OPEN_0800_0900": (8 * 60, 9 * 60),
    "LONDON_POST_0900_1100": (9 * 60, 11 * 60),
    "LONDON_FIX_1545_1615": (15 * 60 + 45, 16 * 60 + 15),
    "LONDON_POSTFIX_1605_1635": (16 * 60 + 5, 16 * 60 + 35),
}
# Only timestamp fields are captured. Price strings are skipped as opaque bytes.
M5_BAR = re.compile(
    rb'\{"close":"[^"]+","closed_at":"([^"]+)",'
    rb'"high":"[^"]+","low":"[^"]+","open":"[^"]+",'
    rb'"opened_at":"([^"]+)","period":"M5"\}'
)


def checked_source_metadata(symbol: str, path: Path) -> tuple[dict[str, Any], datetime]:
    inventory = build_inventory(symbol, path)
    if inventory["source_sha256"] != EXPECTED_SHA[symbol]:
        raise ValueError("immutable source SHA mismatch")
    raw = metadata_prefix(path)
    cutoff_text = raw.get("fresh_cutoff")
    if not isinstance(cutoff_text, str):
        raise ValueError("reserved fresh_cutoff missing")
    cutoff = datetime.fromisoformat(cutoff_text)
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("reserved cutoff timezone missing")
    cutoff = cutoff.astimezone(UTC)
    if cutoff > datetime(2023, 9, 24, 23, 45, tzinfo=UTC):
        raise ValueError("archive fresh_cutoff unexpectedly moved into sealed period")
    return inventory, cutoff


def iter_dev_timestamps(path: Path, cutoff: datetime):
    """Iterate timestamps only, stop on first sealed M5 before scanning onward."""
    previous: datetime | None = None
    with path.open("rb") as handle:
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as view:
            index = view.find(b'"M5":[')
            if index < 0:
                raise ValueError("M5 time series missing")
            position = index + len(b'"M5":[')
            while position < len(view) and view[position:position + 1] == b"{":
                match = M5_BAR.match(view, position)
                if match is None:
                    raise ValueError("unexpected M5 native archive schema")
                closed_at = datetime.fromisoformat(match.group(1).decode()).astimezone(UTC)
                opened_at = datetime.fromisoformat(match.group(2).decode()).astimezone(UTC)
                if opened_at >= cutoff:
                    return
                if closed_at - opened_at != BAR_PERIOD:
                    raise ValueError("M5 bar has wrong period")
                if opened_at.minute % 5 or opened_at.second or opened_at.microsecond:
                    raise ValueError("M5 timestamp not aligned to UTC five-minute grid")
                if previous is not None and opened_at <= previous:
                    raise ValueError("M5 duplicates/out-of-order timestamps")
                previous = opened_at
                yield opened_at
                position = match.end()
                if view[position:position + 1] == b",":
                    position += 1
                elif view[position:position + 1] == b"]":
                    return
                else:
                    raise ValueError("M5 archive sequence separator invalid")


def observation_slots(observed: list[datetime]) -> dict[date, dict[str, int]]:
    by_day: dict[date, dict[str, int]] = {}
    for opened in observed:
        local = opened.astimezone(LONDON)
        local_minutes = local.hour * 60 + local.minute
        for name, (start, end) in WINDOWS.items():
            if start <= local_minutes < end:
                day = local.date()
                series = by_day.setdefault(day, {})
                slot = (local_minutes - start) // 5
                series[name] = series.get(name, 0) | (1 << slot)
    return by_day


def census(symbol: str, root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = root / "raw-7y-base.json"
    inventory, cutoff = checked_source_metadata(symbol, path)
    observed = list(iter_dev_timestamps(path, cutoff))
    if not observed:
        raise ValueError("no M5 observations before sealed cutoff")
    by_day = observation_slots(observed)
    local_start = observed[0].astimezone(LONDON).date()
    local_end_exclusive = cutoff.astimezone(LONDON).date()
    rows: list[dict[str, Any]] = []
    totals = {key: Counter() for key in WINDOWS}
    day = local_start
    while day < local_end_exclusive:
        if day.weekday() < 5:
            actual = by_day.get(day, {})
            for name, (start, end) in WINDOWS.items():
                expected = (end - start) // 5
                mask = actual.get(name, 0)
                present = mask.bit_count()
                if present > expected:
                    raise ValueError("clock mask exceeds nominal window")
                full = int(present == expected)
                rows.append({
                    "symbol": symbol, "local_date": day.isoformat(),
                    "window": name, "present_m5": present,
                    "expected_m5": expected, "complete": full,
                    "present_mask_hex": hex(mask),
                })
                totals[name]["nominal_weekdays"] += 1
                totals[name]["actual_m5"] += present
                totals[name]["nominal_m5"] += expected
                totals[name]["complete_days"] += full
        day += timedelta(days=1)
    result = {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_run": SOURCE_RUN_ID,
        "source_sha": SOURCE_COMMIT,
        "source_file_sha256": inventory["source_sha256"],
        "demo_account_verified": inventory["account_is_live"] is False,
        "source_m5_total": inventory["coverage"]["M5"]["bar_count"],
        "m5_observed_dev": len(observed),
        "m5_first_dev_utc": observed[0].isoformat(),
        "m5_last_dev_utc": observed[-1].isoformat(),
        "reserved_cutoff_utc": cutoff.isoformat(),
        "observability_only": True,
        "prices_read": False,
        "new_capture": False,
        "ctrader_oauth_needed": False,
        "virgin_oos_claimed": False,
        "dev_previously_consumed": True,
        "sealed_vt08_post_cutoff_not_examined": True,
        "provider_session_certified": False,
        "windows": {name: dict(totals[name]) for name in WINDOWS},
        "per_day_rows": len(rows),
    }
    return result, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=tuple(EXPECTED_SHA))
    parser.add_argument("archive_root", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()
    result, rows = census(args.symbol, args.archive_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / f"{args.symbol}-g0c.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (args.out_dir / f"{args.symbol}-g0c-daily.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "symbol", "local_date", "window", "present_m5", "expected_m5",
            "complete", "present_mask_hex"])
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "symbol": args.symbol, "status": "EXISTING_DEMO_DEV_CLOCK_CENSUS_COMPLETE",
        "dev_m5": result["m5_observed_dev"], "source_m5": result["source_m5_total"],
        "sealed_cutoff": result["reserved_cutoff_utc"],
        "oauth_used": False}, sort_keys=True))


if __name__ == "__main__":
    main()
