#!/usr/bin/env python3
"""Streaming UK/DST M1 evidence-coverage probe for VT31_LONDON.

Counts actual closed M1 bars by Europe/London civil clock on the exact Owner 3Y
NAS100 evidence. Candidate clock windows are coverage probes, NOT strategy
implementation or parameter choices. Does not touch cognition or signals.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SCHEMA = "qore.vt31.nas100.owner_3y_london_coverage_fast_probe.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
START = datetime(2023, 10, 1, tzinfo=UTC)
END = datetime(2026, 10, 1, tzinfo=UTC)
LONDON = ZoneInfo("Europe/London")
COMPLETE_HOUR = (1 << 60) - 1
# Diagnostic only; final contract is NOT set by this audit.
PAIRS = ((6, 7), (7, 8), (8, 9), (9, 10))


def _dt(raw: str) -> datetime:
    result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("unaware M1 timestamp")
    return result.astimezone(UTC)


def _offset_type(day: date) -> str:
    clock = datetime(day.year, day.month, day.day, 12, tzinfo=LONDON)
    hours = clock.utcoffset()
    if hours == timedelta(hours=1):
        return "BST_UTC_PLUS_1"
    if hours == timedelta(0):
        return "GMT_UTC_PLUS_0"
    raise ValueError("unknown UK DST offset")


def count_bars(
    bars: object,
) -> dict[str, object]:
    daily_masks: dict[str, dict[int, int]] = defaultdict(dict)
    total = 0
    prev_open: datetime | None = None
    first_open: datetime | None = None
    last_close: datetime | None = None
    gap_count = 0
    uk_dst_day_counts: Counter[str] = Counter()
    for bar in bars:
        if not isinstance(bar, dict):
            raise ValueError("M1 record must be object")
        opened = _dt(str(bar["opened_at"]))
        closed = _dt(str(bar["closed_at"]))
        if closed - opened != timedelta(minutes=1):
            raise ValueError("non-M1 record")
        if not START <= opened < END or closed > END:
            raise ValueError("M1 bar outside frozen 3Y boundaries")
        if opened.second or opened.microsecond:
            raise ValueError("non-minute-aligned open")
        if prev_open is not None:
            if opened <= prev_open:
                raise ValueError("out-of-order or duplicate M1 record")
            if opened - prev_open > timedelta(minutes=1):
                gap_count += 1
        prev_open = opened
        if first_open is None:
            first_open = opened
        last_close = closed
        local = opened.astimezone(LONDON)
        day = local.date().isoformat()
        hour = local.hour
        minute_bit = 1 << local.minute
        existing = daily_masks[day].get(hour, 0)
        if existing & minute_bit:
            raise ValueError("duplicate UK-local minute; DST folded minute needs identity")
        daily_masks[day][hour] = existing | minute_bit
        total += 1

    # DST fall-back hour 01:00 repeats in local time. We deliberately fail-closed
    # instead of declaring a complete/unique hour from ambiguous evidence.
    if total == 0:
        raise ValueError("empty 3Y M1 evidence")
    by_hour: dict[str, dict[str, int]] = {}
    for hour in range(24):
        masks = [hours[hour] for hours in daily_masks.values() if hour in hours]
        by_hour[f"{hour:02d}"] = {
            "days_with_any_bars": len(masks),
            "days_with_all_60_minutes": sum(mask == COMPLETE_HOUR for mask in masks),
            "days_with_incomplete_hour": sum(mask != COMPLETE_HOUR for mask in masks),
        }
    probes: dict[str, dict[str, object]] = {}
    for ref_hour, exec_hour in PAIRS:
        eligible_days = [
            day for day, hours in daily_masks.items()
            if hours.get(ref_hour) == COMPLETE_HOUR
            and hours.get(exec_hour) == COMPLETE_HOUR
        ]
        by_year = Counter(day[:4] for day in eligible_days)
        by_dst = Counter(_offset_type(date.fromisoformat(day))
                         for day in eligible_days)
        probes[f"{ref_hour:02d}:00-{ref_hour + 1:02d}:00_REF__"
               f"{exec_hour:02d}:00-{exec_hour + 1:02d}:00_EXEC"] = {
            "full_reference_plus_execution_days": len(eligible_days),
            "by_year": dict(sorted(by_year.items())),
            "by_uk_clock_offset": dict(sorted(by_dst.items())),
            "first_5_days": sorted(eligible_days)[:5],
            "last_5_days": sorted(eligible_days)[-5:],
        }
    for day in daily_masks:
        uk_dst_day_counts[_offset_type(date.fromisoformat(day))] += 1

    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "frozen_window_utc": {
            "start_inclusive": START.isoformat(),
            "end_exclusive": END.isoformat(),
        },
        "market": "NAS100",
        "session_model_id": "VT31_LONDON",
        "timezone": "Europe/London",
        "m1_bar_count": total,
        "distinct_london_dates_with_bars": len(daily_masks),
        "first_m1_open_utc": first_open.isoformat() if first_open else None,
        "last_m1_close_utc": last_close.isoformat() if last_close else None,
        "utc_m1_gap_boundaries": gap_count,
        "observed_day_counts_by_uk_offset": dict(sorted(uk_dst_day_counts.items())),
        "complete_hours_by_london_wall_clock": by_hour,
        "diagnostic_candidate_window_coverage_only": probes,
        "missing_hours_not_backfilled": True,
        "governance": {
            "read_only_coverage_measurement": True,
            "candidate_clock_windows_are_diagnostic_only": True,
            "london_reference_window_frozen": False,
            "london_execution_window_frozen": False,
            "london_trader_implemented": False,
            "london_certified": False,
            "ny_metrics_used_for_london_certification": False,
            "fresh_holdout_opened": False,
            "trade_or_policy_modified": False,
            "live_authorized": False,
        },
    }


def evidence_bars(path: Path) -> object:
    import ijson

    # Streaming avoids parsing an entire multi-year M1 payload into RAM.
    # The frozen artifact identity/hashes are checked by the workflow.
    with path.open("rb") as stream:
        for item in ijson.items(stream, "periods.M1.item"):
            yield item


def evidence_identity(path: Path) -> None:
    import ijson

    expected = {
        "base_id": BASE_ID,
        "base_start_at": START.isoformat(),
        "base_end_exclusive": END.isoformat(),
        "market": "NAS100",
    }
    for key, value in expected.items():
        with path.open("rb") as stream:
            actual = next(ijson.items(stream, key), None)
        if actual != value:
            raise ValueError(f"frozen evidence {key} mismatch: {actual!r}")


def self_test() -> None:
    # UK switches clocks on 2026-03-29 and 2026-10-25. A fixed UTC shift
    # would fail these assertions, even though local 07:00 remains unambiguous.
    assert _offset_type(date(2026, 3, 28)) == "GMT_UTC_PLUS_0"
    assert _offset_type(date(2026, 3, 30)) == "BST_UTC_PLUS_1"
    assert _offset_type(date(2026, 10, 24)) == "BST_UTC_PLUS_1"
    assert _offset_type(date(2026, 10, 26)) == "GMT_UTC_PLUS_0"
    def sample(start: datetime, n: int = 120) -> object:
        for i in range(n):
            op = start + timedelta(minutes=i)
            yield {"opened_at": op.isoformat(),
                   "closed_at": (op + timedelta(minutes=1)).isoformat()}
    day = datetime(2025, 5, 1, 6, tzinfo=UTC)  # BST => 07:00 London.
    result = count_bars(sample(day))
    pairs = result["diagnostic_candidate_window_coverage_only"]
    assert pairs["07:00-08:00_REF__08:00-09:00_EXEC"][
        "full_reference_plus_execution_days"
    ] == 1
    assert pairs["06:00-07:00_REF__07:00-08:00_EXEC"][
        "full_reference_plus_execution_days"
    ] == 0
    assert result["m1_bar_count"] == 120


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print(json.dumps({"self_test": "PASS", "schema": SCHEMA}))
        return
    if not args.evidence or not args.output:
        parser.error("--evidence and --output are required")
    evidence_identity(args.evidence)
    result = count_bars(evidence_bars(args.evidence))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "m1_bar_count": result["m1_bar_count"],
        "days": result["distinct_london_dates_with_bars"],
        "candidate_window_coverage": (
            result["diagnostic_candidate_window_coverage_only"]
        ),
        "uk_dst": result["observed_day_counts_by_uk_offset"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
