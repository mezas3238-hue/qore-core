"""QORE Native RESET fixing G1 — causally frozen, read-only EURUSD M5 research.

Not an execution strategy, trading signal, WMR fixing print or untouched OOS.
Consumes exactly CIBO's existing EURUSD cTrader DEMO 10Y artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

IDENTITY = "QORE_NATIVE_RESET_FIX_G1_CIBO_M5_V1"
SOURCE_RUN_ID = 35166210458
SOURCE_ARTIFACT_ID = 10475354631
SOURCE_SHA = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
SOURCE_IDENTITY = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
SYMBOL = "EURUSD"
START_UTC = datetime(2016, 9, 17, tzinfo=UTC)
END_UTC = datetime(2026, 9, 17, tzinfo=UTC)
EXPECTED_BARS = 745458
LONDON = ZoneInfo("Europe/London")
SEED = 941102
N_BOOTSTRAP = 2000
LOOKBACK = 120
HIGH_QUANTILE = 0.75
MIN_DAYS = 300
MIN_PER_CELL = 50
# (forming-open local minutes, entry at 05 after event, exit +25, delayed entry +5)
CLOCK = {
    "FIX": (15 * 60 + 30, 16 * 60 + 5, 16 * 60 + 30, 16 * 60 + 10),
    "PLACEBO": (13 * 60 + 30, 14 * 60 + 5, 14 * 60 + 30, 14 * 60 + 10),
}
REQUIRED_LOCAL_MINUTES = {
    m for start, ent, end, delay in CLOCK.values()
    for m in (*range(start, start + 25, 5), ent, end, delay)
}


@dataclass(frozen=True, slots=True)
class Bar:
    opened_utc: datetime
    opening: float
    closing: float


@dataclass(frozen=True, slots=True)
class Event:
    day: str
    week: str
    year: int
    fixing_class: str
    placebo_class: str
    fixing_pressure_bps: float
    placebo_pressure_bps: float
    fixing_reversal_bps: float
    placebo_reversal_bps: float
    fixing_delay_bps: float
    placebo_delay_bps: float
    month_end: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha_expectations(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in text.splitlines():
        tokens = row.split(maxsplit=1)
        if len(tokens) != 2 or len(tokens[0]) != 64:
            raise ValueError("invalid SHA256 manifest line")
        result[tokens[1].strip()] = tokens[0]
    return result


def read_existing_cibo_atlas(root: Path) -> tuple[dict[date, dict[int, Bar]], dict[str, Any]]:
    """Verify all annual raw digests while retaining ONLY the designated London event windows."""
    manifest_file = root / "symbol-consumption-manifest.json"
    if not manifest_file.is_file():
        raise ValueError("EURUSD source manifest missing")
    sha = _sha_expectations((root / "MANIFEST_SHA256SUMS.txt").read_text())
    if sha.get("symbol-consumption-manifest.json") != sha256_file(manifest_file):
        raise ValueError("symbol manifest SHA256 mismatch")
    manifest = json.loads(manifest_file.read_text())
    if (manifest.get("identity") != SOURCE_IDENTITY
            or manifest.get("canonical_symbol") != SYMBOL
            or manifest.get("provider_symbol") != SYMBOL
            or manifest.get("retained_bars") != EXPECTED_BARS
            or manifest.get("research_evidence_consumed") is not True
            or manifest.get("read_only") is not True
            or manifest.get("live_authorized") is not False
            or manifest.get("production_authorized") is not False
            or manifest.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD"):
        raise ValueError("CIBO Atlas frozen EURUSD manifest contract failed")
    digits = manifest.get("digits")
    if type(digits) is not int or digits != 5:
        raise ValueError("EURUSD native quote precision contract changed")
    previous: datetime | None = None
    total = 0
    counts: dict[str, int] = {}
    retained: dict[date, dict[int, Bar]] = defaultdict(dict)
    for year in range(2016, 2027):
        name = str(year)
        source = root / "RAW_M5_LEDGER" / (name + ".jsonl")
        sha_file = root / "PARTITION_MANIFEST" / (name + ".sha256")
        partition_file = root / "PARTITION_MANIFEST" / (name + ".json")
        if not all(p.is_file() for p in (source, sha_file, partition_file)):
            raise ValueError("annual raw or integrity witness missing " + name)
        expected = _sha_expectations(sha_file.read_text())
        if expected.get("RAW_M5_LEDGER/" + name + ".jsonl") != sha256_file(source):
            raise ValueError("annual RAW_M5_LEDGER SHA mismatch " + name)
        if expected.get("PARTITION_MANIFEST/" + name + ".json") != sha256_file(partition_file):
            raise ValueError("annual manifest SHA mismatch " + name)
        annual = json.loads(partition_file.read_text())
        if annual.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD":
            raise ValueError("annual source status not clean")
        seen = 0
        with source.open("rt", encoding="utf-8") as rows:
            for raw in rows:
                row = json.loads(raw)
                moment = datetime.fromisoformat(row["opened_at"]).astimezone(UTC)
                if (not START_UTC <= moment < END_UTC or moment.second
                        or moment.microsecond or moment.minute % 5
                        or (previous is not None and moment <= previous)):
                    raise ValueError("out-of-window, unaligned or non-monotone native M5")
                previous = moment
                if (row.get("canonical_symbol") != SYMBOL
                        or row.get("identity") != SOURCE_IDENTITY
                        or row.get("digits") != digits
                        or type(row.get("open_relative")) is not int
                        or type(row.get("close_relative")) is not int
                        or type(row.get("high_relative")) is not int
                        or type(row.get("low_relative")) is not int):
                    raise ValueError("unexpected provider-relative bar identity")
                o, c = row["open_relative"], row["close_relative"]
                lo, hi = row["low_relative"], row["high_relative"]
                if not (0 < lo <= min(o, c) <= max(o, c) <= hi):
                    raise ValueError("OHLC extreme violation")
                # A missing session bar is never invented.
                local = moment.astimezone(LONDON)
                minute = local.hour * 60 + local.minute
                if minute in REQUIRED_LOCAL_MINUTES:
                    day = local.date()
                    if day.weekday() < 5:
                        if minute in retained[day]:
                            raise ValueError("duplicate London M5 event slot")
                        retained[day][minute] = Bar(moment, o / 10**digits, c / 10**digits)
                seen += 1
        if seen != annual.get("retained_bars"):
            raise ValueError("annual retained bar count changed " + name)
        counts[name] = seen
        total += seen
    if total != EXPECTED_BARS:
        raise ValueError("total EURUSD native M5 count changed")
    return dict(retained), {
        "source_run_id": SOURCE_RUN_ID, "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_sha": SOURCE_SHA, "cibo_manifest_sha256": sha256_file(manifest_file),
        "raw_annual_m5_sha256_verified": True, "raw_m5_total": total,
        "raw_m5_by_year": counts, "digits": digits, "read_only": True,
        "research_evidence_consumed": True, "provider_calendar_verified": False,
        "original_raw_ohlc_modified": False,
    }


def quantile75(prior: deque[float]) -> float:
    if len(prior) != LOOKBACK:
        raise ValueError("p75 requires exactly 120 previous complete formations")
    items = sorted(prior)
    position = (len(items) - 1) * HIGH_QUANTILE
    i = int(position)
    alpha = position - i
    return items[i] * (1 - alpha) + items[min(i + 1, len(items) - 1)] * alpha


def local_minute_bar(day: date, local_minutes: int, day_bars: dict[int, Bar]) -> Bar | None:
    value = day_bars.get(local_minutes)
    if value is None:
        return None
    # Check each event uses an M5 open at the intended Europe/London timestamp (including DST).
    target = datetime(day.year, day.month, day.day,
                      local_minutes // 60, local_minutes % 60, tzinfo=LONDON)
    if value.opened_utc != target.astimezone(UTC):
        raise ValueError("London event timestamp not source-matched")
    return value


def formation(day: date, bars: dict[int, Bar], arm: str) -> float | None:
    start = CLOCK[arm][0]
    seq = [local_minute_bar(day, start + n * 5, bars) for n in range(5)]
    if any(x is None for x in seq):
        return None
    assert seq[0] is not None and seq[-1] is not None
    a, b = seq[0].opening, seq[-1].closing
    if a <= 0 or b <= 0:
        raise ValueError("nonpositive fixed-window EURUSD OHLC")
    return 10000 * math.log(b / a)


def reversal(day: date, bars: dict[int, Bar], arm: str, pressure: float,
             delayed: bool = False) -> float | None:
    _, entry, exit_, late = CLOCK[arm]
    first = local_minute_bar(day, late if delayed else entry, bars)
    last = local_minute_bar(day, exit_, bars)
    if first is None or last is None:
        return None
    if pressure == 0:
        return None
    return -math.copysign(1.0, pressure) * 10000 * math.log(last.opening / first.opening)


def month_end_flag(day: date) -> bool:
    # Last weekday of each calendar month; proxy ONLY, not confirmed WMR rebalancing.
    candidate = day + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.month != day.month


def build_events(source: dict[date, dict[int, Bar]]) -> tuple[list[Event], dict[str, Any]]:
    history: dict[str, deque[float]] = {arm: deque(maxlen=LOOKBACK) for arm in CLOCK}
    reasons: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    form_counts: Counter[str] = Counter()
    records: list[Event] = []
    day = START_UTC.date()
    end = END_UTC.date()
    while day < end:
        if day.weekday() < 5:
            b = source.get(day, {})
            pressure = {arm: formation(day, b, arm) for arm in CLOCK}
            if any(v is None for v in pressure.values()):
                reasons["INCOMPLETE_FORMATION"] += 1
            for arm, value in pressure.items():
                if value is not None:
                    form_counts[arm] += 1
            if any(v is None for v in pressure.values()):
                pass
            elif any(len(history[arm]) < LOOKBACK for arm in CLOCK):
                reasons["INSUFFICIENT_HISTORY"] += 1
            elif any(pressure[arm] == 0 for arm in CLOCK):
                reasons["ZERO_PRESSURE"] += 1
            else:
                assert all(pressure[arm] is not None for arm in CLOCK)
                revs: dict[str, float | None] = {}
                delays: dict[str, float | None] = {}
                for arm in CLOCK:
                    revs[arm] = reversal(day, b, arm, float(pressure[arm]))
                    delays[arm] = reversal(day, b, arm, float(pressure[arm]), delayed=True)
                if any(x is None for x in revs.values()) or any(x is None for x in delays.values()):
                    reasons["MISSING_ENTRY_OR_EXIT"] += 1
                else:
                    assert all(v is not None for v in revs.values())
                    assert all(v is not None for v in delays.values())
                    iso = day.isocalendar()
                    classes = {
                        arm: ("HIGH" if abs(float(pressure[arm])) >= quantile75(history[arm])
                              else "LOW") for arm in CLOCK
                    }
                    records.append(Event(
                        day.isoformat(), f"{iso.year}-W{iso.week:02d}", day.year,
                        classes["FIX"], classes["PLACEBO"],
                        float(pressure["FIX"]), float(pressure["PLACEBO"]),
                        float(revs["FIX"]), float(revs["PLACEBO"]),
                        float(delays["FIX"]), float(delays["PLACEBO"]),
                        month_end_flag(day)))
                    reasons["USABLE"] += 1
                    year_counts[str(day.year)] += 1
            # This update happens AFTER all current-day classifications.
            for arm, value in pressure.items():
                if value is not None:
                    history[arm].append(abs(float(value)))
        day += timedelta(days=1)
    return records, {
        "nominal_weekdays": sum(reasons.values()), "reasons": dict(reasons),
        "complete_formations_by_arm": dict(form_counts), "usable_by_year": dict(year_counts),
        "lookback_complete_formations": LOOKBACK, "quantile": HIGH_QUANTILE,
        "classification_has_no_current_or_future_formations": True,
        "joint_day_arm_censor": True, "calendar_is_weekday_proxy": True,
    }


def stratified_means(events: list[Event], *, delayed: bool = False) -> tuple[dict[str, Any], float | None]:
    cells: dict[str, Any] = {}
    for arm, name in (("FIX", "fixing"), ("PLACEBO", "placebo")):
        for level in ("HIGH", "LOW"):
            key = f"{arm}_{level}"
            values = [getattr(e, name + ("_delay_bps" if delayed else "_reversal_bps"))
                      for e in events if getattr(e, name + "_class") == level]
            cells[key] = {"n": len(values), "mean_reversal_bps": mean(values) if values else None}
    if any(cells[k]["n"] == 0 for k in cells):
        return cells, None
    d = (
        cells["FIX_HIGH"]["mean_reversal_bps"]
        - cells["FIX_LOW"]["mean_reversal_bps"]
        - cells["PLACEBO_HIGH"]["mean_reversal_bps"]
        + cells["PLACEBO_LOW"]["mean_reversal_bps"]
    )
    return cells, d


def linear_percentile(data: list[float], percentile: float) -> float:
    ordered = sorted(data)
    position = (len(ordered) - 1) * percentile
    lo = int(position)
    frac = position - lo
    return ordered[lo] * (1 - frac) + ordered[min(lo + 1, len(ordered) - 1)] * frac


def bootstrap_weekly(events: list[Event]) -> dict[str, Any]:
    weeks: dict[str, list[Event]] = defaultdict(list)
    for item in events:
        weeks[item.week].append(item)
    groups = list(weeks.values())
    if not groups:
        return {"ci95_d_bps": None, "valid_draws": 0, "weeks": 0}
    rng = random.Random(SEED)
    distributions: list[float] = []
    for _ in range(N_BOOTSTRAP):
        selection = [event for group in rng.choices(groups, k=len(groups)) for event in group]
        _, d = stratified_means(selection)
        if d is not None:
            distributions.append(d)
    ci = ([linear_percentile(distributions, 0.025),
           linear_percentile(distributions, 0.975)]
          if len(distributions) == N_BOOTSTRAP else None)
    return {
        "ci95_d_bps": ci, "valid_draws": len(distributions),
        "bootstraps_requested": N_BOOTSTRAP, "seed": SEED,
        "weeks": len(groups), "ISO_week_block_joint_resampling": True,
    }


def run(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bars, source = read_existing_cibo_atlas(root)
    events, missing = build_events(bars)
    cells, d = stratified_means(events)
    delay_cells, delay_d = stratified_means(events, delayed=True)
    enough = len(events) >= MIN_DAYS and all(c["n"] >= MIN_PER_CELL for c in cells.values())
    bootstrap = bootstrap_weekly(events) if enough else {
        "ci95_d_bps": None, "skip_reason": "MIN_SAMPLE_GATE",
        "valid_draws": 0,
    }
    lower = bootstrap["ci95_d_bps"][0] if bootstrap["ci95_d_bps"] else None
    if not enough:
        verdict = "DEV_UNDERPOWERED"
    elif d is not None and d > 0 and lower is not None and lower > 0:
        verdict = "DEV_GROSS_POTENTIAL"
    else:
        verdict = "DEV_GROSS_NO_SUPPORT"
    year_slices = {}
    for year in sorted({e.year for e in events}):
        sub = [e for e in events if e.year == year]
        _, diff = stratified_means(sub)
        year_slices[str(year)] = {"common_days": len(sub), "difference_in_differences_bps": diff}
    endmonth = [e for e in events if e.month_end]
    _, endmonth_d = stratified_means(endmonth)
    payload = {
        "identity": IDENTITY, "source": source, "prereg_identity": "QORE_NATIVE_RESET_FIX_G1",
        "primary_symbol": SYMBOL, "results_are_dev_consumed_not_oos": True,
        "event_is_16_00_europe_london": True, "uses_native_m5": True,
        "entry_open_16_05_exit_open_16_30_no_fill_claim": True,
        "fixing_benchmark_print_not_observed": True,
        "broker_bidask_costs_not_observed": True,
        "pnl_pf_sharpe_sortino_not_estimated": True,
        "no_live_no_vps_no_trade": True, "common_days": len(events),
        "sample_gate_pass": enough, "cells": cells,
        "primary_d_bps": d, "bootstrap": bootstrap, "verdict": verdict,
        "delay_1_m5_secondary_bps": delay_d, "delay_cells": delay_cells,
        "last_weekday_monthend_days": len(endmonth),
        "monthend_secondary_d_bps": endmonth_d,
        "year_secondary": year_slices, "quality": missing,
    }
    return payload, [e.__dict__ if hasattr(e, "__dict__") else {
        f: getattr(e, f) for f in e.__dataclass_fields__
    } for e in events]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    report, events = run(args.source)
    args.out.mkdir(parents=True, exist_ok=True)
    outputs = {
        "reset-g1-report.json": json.dumps(report, sort_keys=True, indent=2) + "\n",
        "reset-g1-common-days.jsonl": "".join(json.dumps(item, sort_keys=True) + "\n"
                                           for item in events),
    }
    for filename, content in outputs.items():
        dest = args.out / filename
        dest.write_text(content, encoding="utf-8")
        (args.out / (filename + ".sha256")).write_text(
            hashlib.sha256(content.encode()).hexdigest() + "  " + filename + "\n")
    print(json.dumps({"status": report["verdict"], "n": report["common_days"],
                      "d_bps": report["primary_d_bps"],
                      "ci95_d_bps": report["bootstrap"]["ci95_d_bps"],
                      "source_artifact": SOURCE_ARTIFACT_ID,
                      "no_oauth": True}, sort_keys=True))


if __name__ == "__main__":
    main()
