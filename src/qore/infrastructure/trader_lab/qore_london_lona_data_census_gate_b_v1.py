"""LON-A Gate B source-only native M1 -> D1/H4/M15 coverage inventory.

NO signal, CISD, fills or outcome fields. The legacy CIBO clone's neutral
read-only parser is reused only to inspect provenance; it is NOT a method.
All bars are provider-native M1, no interpolation or forward filling.
UTC-aligned H4 here is one *data-quality clock*, not author-hour certification.
Only the already-consumed London research window is audited: NOT VIRGIN OOS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Iterable

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    EXPECTED_IDENTITY,
    _bar_from_row,
)

IDENTITY = "QORE_LONDON_LONA_GATE_B_UTC_AGGREGATION_CENSUS_SOURCE_ONLY"
START = datetime(2025, 9, 17, tzinfo=UTC)
END = datetime(2026, 9, 17, tzinfo=UTC)
CLOCKS = (("M15_UTC", 15), ("H4_UTC", 240), ("D1_UTC", 1440))
ALLOWED_SYMBOLS = frozenset(("EURUSD", "GBPUSD"))
NY = ZoneInfo("America/New_York")
H4_NY_HYPOTHESES = {
    "H4_NY_22_02_06_HYPOTHESIS": (2, 6, 10, 14, 18, 22),
    "H4_NY_01_05_09_HYPOTHESIS": (1, 5, 9, 13, 17, 21),
}



def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for buf in iter(lambda: file.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def bucket_start(at: datetime, minutes: int) -> datetime:
    if at.tzinfo is None or at.utcoffset() != timedelta(0):
        raise ValueError("ONLY_EXPLICIT_UTC")
    return at - timedelta(minutes=at.hour * 60 % minutes + at.minute % minutes,
                          seconds=at.second, microseconds=at.microsecond)


def ny_h4_anchor(moment: datetime, hours: tuple[int, ...]) -> datetime:
    """Experimental NY wall-clock bin. Does not establish TTrades timezone."""
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise ValueError("UTC_REQUIRED")
    local = moment.astimezone(NY)
    candidates = tuple(h for h in hours if h <= local.hour)
    anchor_hour = candidates[-1] if candidates else hours[-1]
    anchor_date = local.date() if candidates else (local.date() - timedelta(days=1))
    return datetime.combine(anchor_date, time(anchor_hour), tzinfo=NY)


def ny_h4_expected_minutes(anchor: datetime) -> int:
    """NY wall-clock 4h may be 180/240/300 real minutes at DST boundaries."""
    finish = anchor + timedelta(hours=4)
    minutes = int((finish.astimezone(UTC) - anchor.astimezone(UTC)).total_seconds() // 60)
    if minutes not in (180, 240, 300):
        raise ValueError("UNEXPECTED_DST_H4_SPAN")
    return minutes


def summarize_coverage(observed: Iterable[datetime]) -> dict[str, object]:
    """Pure census across UTC bins; reports partials without inventing bars."""
    bins: dict[str, Counter[datetime]] = {key: Counter() for key, _ in CLOCKS}
    ny_counts: dict[str, Counter[datetime]] = {key: Counter() for key in H4_NY_HYPOTHESES}
    count = 0
    previous: datetime | None = None
    missing_minutes_inside_span = 0
    gap_events = 0
    largest_gap_minutes = 0
    first: datetime | None = None
    last: datetime | None = None
    for at in observed:
        if at.tzinfo is None or at.utcoffset() != timedelta(0):
            raise ValueError("UTC_REQUIRED")
        if at.second or at.microsecond:
            raise ValueError("M1_GRID_MISALIGNED")
        if previous is not None:
            dt = int((at - previous).total_seconds() / 60)
            if dt <= 0:
                raise ValueError("M1_NONMONOTONIC_OR_DUPLICATE")
            if dt > 1:
                gap_events += 1
                missing_minutes_inside_span += dt - 1
                largest_gap_minutes = max(largest_gap_minutes, dt - 1)
        if first is None:
            first = at
        last = at
        count += 1
        for key, minutes in CLOCKS:
            bins[key][bucket_start(at, minutes)] += 1
        for name, hours in H4_NY_HYPOTHESES.items():
            ny_counts[name][ny_h4_anchor(at, hours)] += 1
        previous = at
    groups: dict[str, object] = {}
    for key, minutes in CLOCKS:
        cc = bins[key]
        complete = sum(x == minutes for x in cc.values())
        partial = sum(x < minutes for x in cc.values())
        overfull = sum(x > minutes for x in cc.values())
        if overfull:
            raise ValueError("OVERCOVERED_AGGREGATE_BIN")
        groups[key] = {
            "clock_anchor": "UTC ONLY - NOT CERTIFIED AS TTRADES H4 CLOCK",
            "minutes_per_bar": minutes,
            "observed_buckets": len(cc),
            "complete_buckets": complete,
            "partial_buckets": partial,
            "min_retained_m1_in_nonempty_bin": min(cc.values()) if cc else None,
            "max_retained_m1_in_nonempty_bin": max(cc.values()) if cc else None,
            "complete_fraction_of_observed_nonempty_bins": round(
                complete / len(cc), 6
            ) if cc else None,
            "market_closed_or_empty_calendar_bins_not_assessed": True,
        }
    ny_results: dict[str, object] = {}
    for name, cc in ny_counts.items():
        spans = {k: ny_h4_expected_minutes(k) for k in cc}
        if any(n > spans[k] for k, n in cc.items()):
            raise ValueError("OVERCOVERED_NY_H4_BIN")
        completed = sum(n == spans[k] for k, n in cc.items())
        ny_results[name] = {
            "hypothesis_only": True,
            "observed_buckets": len(cc),
            "complete_buckets": completed,
            "partial_buckets": sum(n < spans[k] for k, n in cc.items()),
            "variable_duration_DST_handled": True,
            "observed_buckets_with_180_min_span": sum(span == 180 for span in spans.values()),
            "observed_buckets_with_300_min_span": sum(span == 300 for span in spans.values()),
            "complete_fraction_of_observed_nonempty_bins": round(completed / len(cc), 6) if cc else None,
            "not_an_author_clock_certification": True,
        }
    return {
        "ny_h4_hypothesis_bins": ny_results,
        "retained_m1_in_window": count,
        "first_observed_m1_utc": first.isoformat() if first else None,
        "last_observed_m1_utc": last.isoformat() if last else None,
        "discontinuity_events_including_weekends_and_holidays": gap_events,
        "missing_calendar_minutes_inside_span_including_closed_markets": missing_minutes_inside_span,
        "max_calendar_gap_minutes_including_closures": largest_gap_minutes,
        "utc_bins": groups,
        "market_closure_vs_feed_gap_unresolved": True,
    }


def census_source(root: Path, symbol: str) -> dict[str, object]:
    if symbol not in ALLOWED_SYMBOLS:
        raise ValueError("NON_LONDON_SYMBOL")
    manifest_path = root / "m1-clone-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("identity") != EXPECTED_IDENTITY
            or manifest.get("canonical_symbol") != symbol
            or manifest.get("provider_native_m1") is not True
            or manifest.get("synthetic_m1") is not False
            or manifest.get("interpolated_m1") is not False
            or manifest.get("contradictory_m1") != 0):
        raise ValueError("SOURCE_MANIFEST_PROVENANCE_FAILED")
    partition_by_year = {str(x["partition"]): x for x in manifest.get("partitions", [])}
    selected = ("2025", "2026")
    source_sha = {}
    for year in selected:
        part = partition_by_year.get(year)
        file = root / "RAW_M1_LEDGER" / f"{year}.jsonl"
        if part is None or not file.is_file():
            raise ValueError(f"YEARLY_PARTITION_MISSING:{year}")
        digest = sha256(file)
        if part.get("raw_sha256") != digest:
            raise ValueError(f"PARTITION_HASH_MISMATCH:{year}")
        source_sha[year] = digest

    def observed():
        for year in selected:
            file = root / "RAW_M1_LEDGER" / f"{year}.jsonl"
            with file.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    bar = _bar_from_row(raw)
                    if bar.symbol != symbol:
                        raise ValueError("MIXED_SYMBOL_IN_RAW_LEDGER")
                    if START <= bar.opened_at < END:
                        yield bar.opened_at

    counts = summarize_coverage(observed())
    if counts["retained_m1_in_window"] == 0:
        raise ValueError("NO_M1_DATA_FOR_AUDIT_WINDOW")
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "dataset_identity": manifest["identity"],
        "source_manifest_sha256": sha256(manifest_path),
        "verified_year_partition_sha256": source_sha,
        "window_start_utc": START.isoformat(),
        "window_end_exclusive_utc": END.isoformat(),
        "clock_policy": "UTC_BINNING_ONLY_AUTHOR_H4_CLOCK_UNDERDETERMINED",
        **counts,
        "existing_research_period_consumed": True,
        "fresh_holdout_eligible": False,
        "author_fidelity_certified": False,
        "native_h4_verified": False,
        "m15_and_d1_reconstructed_from_m1_only": True,
        "data_gate_b_certified": False,
        "economic_replay_authorized": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("symbol", choices=sorted(ALLOWED_SYMBOLS))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = census_source(args.source, args.symbol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("LONA_GATE_B_CENSUS_NO_REPLAY", json.dumps({
        "symbol": result["symbol"],
        "m1": result["retained_m1_in_window"],
        "utc_bins": result["utc_bins"],
        "ny_h4_hypothesis_bins": result["ny_h4_hypothesis_bins"],
        "data_gate_b_certified": result["data_gate_b_certified"],
        "fresh_holdout_eligible": result["fresh_holdout_eligible"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
