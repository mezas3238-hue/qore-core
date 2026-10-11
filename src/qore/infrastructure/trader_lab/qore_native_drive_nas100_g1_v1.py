"""QORE Native DRIVE NAS100 G1 — one prespecified, causal cTrader M1 gross test.

Only archived provider-native NAS100/USTEC 2016–2026 data; zero OAuth, no
orders, no executable fills, no unobserved order-flow assertions. All consumed DEV.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

IDENTITY = "QORE_NATIVE_DRIVE_NAS100_G1_NY_OPEN_CONTINUATION_V1"
PREREG_SHA = "9ebcf60628196a52cbd476e584d4f554b60af035"
SOURCE_RUN = 35548099334
SOURCE_ARTIFACT = 10618862813
SOURCE_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
SOURCE_IDENTITY = "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"
SOURCE_SCHEMA = "qore.capitalizer.cibo.raw_m1.v1"
START = datetime(2016, 9, 17, tzinfo=UTC)
END = datetime(2026, 9, 17, tzinfo=UTC)
NY = ZoneInfo("America/New_York")
NY_FIRST = 9 * 60 + 30
NY_FORMATION_END = 10 * 60
NY_ENTRY = 10 * 60 + 1
NY_EXIT = 11 * 60
EXPECTED_MINUTES = tuple(range(NY_FIRST, NY_EXIT + 1))
MAX_PRIOR_AGE_DAYS = 5
BOOTSTRAPS = 2000
SEED = 941211
MIN_COMMON_DAYS = 500
MIN_BY_SIGN = 150
MIN_WEEK_BLOCKS = 100


@dataclass(frozen=True, slots=True)
class Open:
    at_utc: datetime
    opening: int


@dataclass(frozen=True, slots=True)
class Day:
    ny_date: date
    formation_log: float
    forward_bps: float


@dataclass(frozen=True, slots=True)
class Paired:
    ny_date: str
    iso_week: str
    year: int
    formation_log: float
    drive_direction: int
    stale_direction: int
    prior_date: str
    prior_age_days: int
    forward_bps: float
    gross_drive_bps: float
    gross_stale_bps: float
    delta_bps: float


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_manifest(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = root / "m1-clone-manifest.json"
    witness = root / "MANIFEST_SHA256SUMS.txt"
    if not path.is_file() or not witness.is_file():
        raise ValueError("original CIBO 10Y M1 manifest and witness are required")
    parts = witness.read_text(encoding="utf-8").strip().split(maxsplit=1)
    if len(parts) != 2 or parts[1] != path.name or parts[0] != sha256_file(path):
        raise ValueError("M1 manifest SHA256 witness mismatch")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "identity": SOURCE_IDENTITY,
        "schema": "qore.capitalizer.cibo.m1_clone.v1",
        "canonical_symbol": "NAS100",
        "provider_symbol": "USTEC",
        "provider_native_m1": True,
        "synthetic_m1": False,
        "interpolated_m1": False,
        "read_only": True,
        "live_authorized": False,
        "production_authorized": False,
        "contradictory_m1": 0,
        "target_start": START.isoformat(),
        "target_end_exclusive": END.isoformat(),
    }
    for key, expected in required.items():
        if type(manifest.get(key)) is not type(expected) or manifest[key] != expected:
            raise ValueError("native CIBO M1 source contract mismatch: " + key)
    partitions = manifest.get("partitions")
    if not isinstance(partitions, list) or [
        p.get("partition") for p in partitions
    ] != [str(year) for year in range(2016, 2027)]:
        raise ValueError("source annual partitions drift")
    ident = manifest.get("provider_symbol_id")
    digits = manifest.get("digits")
    if (type(ident) is not int or ident <= 0
            or type(digits) is not int or not 1 <= digits <= 10
            or type(manifest.get("retained_m1")) is not int
            or manifest["retained_m1"] <= 0):
        raise ValueError("invalid provider native NAS100 identity/count")
    evidence = {
        "source_run_id": SOURCE_RUN, "source_artifact_id": SOURCE_ARTIFACT,
        "source_commit": SOURCE_SHA, "manifest_sha256": sha256_file(path),
        "provider_native_m1": True, "provider_symbol": "USTEC",
        "historical_window_start": START.isoformat(),
        "historical_window_end_exclusive": END.isoformat(),
        "reserved_pre2016_not_used": True,
    }
    return manifest, evidence


def read_native_nas100(root: Path) -> tuple[dict[date, dict[int, Open]], dict[str, Any]]:
    manifest, source = source_manifest(root)
    retained: dict[date, dict[int, Open]] = {}
    previous_utc: datetime | None = None
    annual_counts: dict[str, int] = {}
    total = 0
    for entry in manifest["partitions"]:
        year = entry["partition"]
        path = root / "RAW_M1_LEDGER" / f"{year}.jsonl"
        if not path.is_file() or sha256_file(path) != entry.get("raw_sha256"):
            raise ValueError("annual source M1 SHA mismatch: " + year)
        count = 0
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if (row.get("schema") != SOURCE_SCHEMA
                        or row.get("identity") != SOURCE_IDENTITY
                        or row.get("canonical_symbol") != "NAS100"
                        or row.get("provider_symbol") != "USTEC"
                        or row.get("provider_symbol_id") != manifest["provider_symbol_id"]
                        or row.get("digits") != manifest["digits"]):
                    raise ValueError("NAS100 native provider row identity mismatch")
                opened = datetime.fromisoformat(row["opened_at"])
                if opened.tzinfo is None or opened.utcoffset() is None:
                    raise ValueError("native M1 source timestamp must be timezone aware")
                opened = opened.astimezone(UTC)
                if (not START <= opened < END
                        or str(opened.year) != year
                        or opened.second or opened.microsecond
                        or (previous_utc is not None and opened <= previous_utc)
                        or row.get("utc_timestamp_in_minutes") != int(opened.timestamp() // 60)):
                    raise ValueError("native M1 missing chronology/time identity")
                previous_utc = opened
                values = [row.get(k) for k in (
                    "open_relative", "high_relative",
                    "low_relative", "close_relative",
                )]
                if (any(type(value) is not int for value in values)
                        or not (0 < values[2] <= min(values[0], values[3])
                                <= max(values[0], values[3]) <= values[1])):
                    raise ValueError("invalid original provider-native OHLC geometry")
                local = opened.astimezone(NY)
                slot = local.hour * 60 + local.minute
                if local.weekday() < 5 and NY_FIRST <= slot <= NY_EXIT:
                    slots = retained.setdefault(local.date(), {})
                    if slot in slots:
                        raise ValueError("duplicate opening in NY session")
                    slots[slot] = Open(opened, values[0])
                count += 1
        if count != entry["retained_m1"]:
            raise ValueError("annual count disagrees with immutable M1 manifest")
        annual_counts[year] = count
        total += count
    if total != manifest["retained_m1"]:
        raise ValueError("total native M1 bar count mismatch")
    source["all_annual_sha256_verified"] = True
    source["annual_native_m1_counts"] = annual_counts
    source["all_native_m1_count"] = total
    source["provider_digits"] = manifest["digits"]
    return retained, source


def ny_open(day: date, minute: int, slots: dict[int, Open]) -> int | None:
    point = slots.get(minute)
    if point is None:
        return None
    expected = datetime(day.year, day.month, day.day,
                        minute // 60, minute % 60,
                        tzinfo=NY).astimezone(UTC)
    if point.at_utc != expected:
        raise ValueError("native M1 timestamp does not match America/New_York DST")
    if point.opening <= 0:
        raise ValueError("provider-relative NAS100 open is nonpositive")
    return point.opening


def observations(sessions: dict[date, dict[int, Open]]) -> tuple[dict[date, Day], dict[str, int]]:
    valid: dict[date, Day] = {}
    reasons: Counter[str] = Counter()
    day = START.astimezone(NY).date()
    final = END.astimezone(NY).date()
    while day <= final:
        if day.weekday() < 5:
            slots = sessions.get(day, {})
            series = [ny_open(day, minute, slots) for minute in EXPECTED_MINUTES]
            if any(p is None for p in series):
                reasons["MISSING_NY_91_M1"] += 1
            else:
                entry_open = series[NY_ENTRY - NY_FIRST]
                exit_open = series[NY_EXIT - NY_FIRST]
                initial_open = series[0]
                formation_end_open = series[NY_FORMATION_END - NY_FIRST]
                assert all(isinstance(p, int) for p in (
                    initial_open, formation_end_open, entry_open, exit_open
                ))
                formation_log = math.log(formation_end_open / initial_open)
                if formation_log == 0:
                    reasons["ZERO_FORMATION_ABSTAIN"] += 1
                else:
                    y = 10000 * math.log(exit_open / entry_open)
                    valid[day] = Day(day, formation_log, y)
                    reasons["COMPLETE_NONZERO_NY"] += 1
        day += timedelta(days=1)
    return valid, dict(reasons)


def pair_prior_sign(observed: dict[date, Day]) -> tuple[list[Paired], dict[str, int]]:
    records: list[Paired] = []
    skips: Counter[str] = Counter()
    last_valid: Day | None = None
    for today in sorted(observed):
        record = observed[today]
        if last_valid is None:
            skips["NO_PREVIOUS_VALID_DAY"] += 1
        else:
            age = (today - last_valid.ny_date).days
            if not 0 < age <= MAX_PRIOR_AGE_DAYS:
                skips["PREVIOUS_VALID_DAY_STALE_OVER_5D"] += 1
            else:
                drive = 1 if record.formation_log > 0 else -1
                stale = 1 if last_valid.formation_log > 0 else -1
                iso = today.isocalendar()
                records.append(Paired(
                    ny_date=today.isoformat(),
                    iso_week=f"{iso.year}-W{iso.week:02d}",
                    year=today.year, formation_log=record.formation_log,
                    drive_direction=drive, stale_direction=stale,
                    prior_date=last_valid.ny_date.isoformat(),
                    prior_age_days=age,
                    forward_bps=record.forward_bps,
                    gross_drive_bps=drive * record.forward_bps,
                    gross_stale_bps=stale * record.forward_bps,
                    delta_bps=(drive - stale) * record.forward_bps,
                ))
                skips["MATCHED_CAUSAL_DAY_PAIR"] += 1
        # Prior observation becomes available after prior day's 11:00 NY,
        # still earlier than the next day's 10:01 NY decision.
        last_valid = record
    return records, dict(skips)


def percentile(items: list[float], p: float) -> float:
    ordered = sorted(items)
    i = (len(ordered) - 1) * p
    lo = int(i)
    weight = i - lo
    return ordered[lo] * (1 - weight) + ordered[min(lo + 1, len(ordered) - 1)] * weight


def bootstrap_iso_weeks(rows: list[Paired]) -> dict[str, Any]:
    by_week: dict[str, list[Paired]] = defaultdict(list)
    for row in rows:
        by_week[row.iso_week].append(row)
    blocks = list(by_week.values())
    if not blocks:
        return {"valid_draws": 0, "weeks": 0, "ci95_delta_bps": None}
    rng = random.Random(SEED)
    draws = []
    for _ in range(BOOTSTRAPS):
        selected = rng.choices(blocks, k=len(blocks))
        total = sum(sum(row.delta_bps for row in block) for block in selected)
        count = sum(len(block) for block in selected)
        draws.append(total / count)
    return {
        "weeks": len(blocks), "bootstraps_requested": BOOTSTRAPS,
        "valid_draws": len(draws), "seed": SEED,
        "paired_iso_week_block_resampling": True,
        "ci95_delta_bps": [percentile(draws, 0.025), percentile(draws, 0.975)],
    }


def analyze(source: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bars, evidence = read_native_nas100(source)
    episodes, census = observations(bars)
    rows, paired_census = pair_prior_sign(episodes)
    years = {}
    for year in range(2016, 2027):
        r = [v for v in rows if v.year == year]
        years[str(year)] = {"n": len(r), "gross_drive_mean_bps": (
            mean(v.gross_drive_bps for v in r) if r else None
        ), "delta_mean_bps": mean(v.delta_bps for v in r) if r else None}
    count_long = sum(row.drive_direction == 1 for row in rows)
    count_short = sum(row.drive_direction == -1 for row in rows)
    delta = mean(v.delta_bps for v in rows) if rows else None
    primary_gross = mean(v.gross_drive_bps for v in rows) if rows else None
    baseline_gross = mean(v.gross_stale_bps for v in rows) if rows else None
    weeks = len({v.iso_week for v in rows})
    sufficient = (
        len(rows) >= MIN_COMMON_DAYS
        and count_long >= MIN_BY_SIGN
        and count_short >= MIN_BY_SIGN
        and weeks >= MIN_WEEK_BLOCKS
    )
    bootstrap = bootstrap_iso_weeks(rows) if sufficient else {
        "ci95_delta_bps": None, "valid_draws": 0,
        "skip_reason": "FROZEN_MINIMUM_SAMPLE_GATE",
    }
    lower = bootstrap["ci95_delta_bps"][0] if bootstrap["ci95_delta_bps"] else None
    if not sufficient:
        verdict = "DEV_DRIVE_UNDERPOWERED"
    elif (delta is not None and lower is not None and delta > 0
          and lower > 0 and primary_gross is not None and primary_gross > 0):
        verdict = "DEV_DRIVE_GROSS_SIGNAL_ONLY"
    else:
        verdict = "DEV_DRIVE_GROSS_NO_SUPPORT"
    report = {
        "identity": IDENTITY,
        "source": evidence,
        "prereg_commit_sha": PREREG_SHA,
        "preregistered_before_drive_g1_outcome": True,
        "already_consumed_cibo_history_not_virgin_oos": True,
        "ny_clock_broker_rth_not_verified": True,
        "market": "NAS100",
        "provider_symbol": "USTEC",
        "only_one_configuration_no_parameter_search": True,
        "formation_local_NY": ["09:30", "10:00"],
        "entry_open_NY": "10:01",
        "exit_open_NY": "11:00",
        "calendar_fullday_91_m1_required": True,
        "stale_direction_uses_past_eligible_day_only": True,
        "placebo_age_max_calendar_days": MAX_PRIOR_AGE_DAYS,
        "census_ny_nominal": census,
        "paired_census": paired_census,
        "causally_complete_observed_days": len(episodes),
        "matched_days": len(rows),
        "long_direction_days": count_long,
        "short_direction_days": count_short,
        "bootstrap": bootstrap,
        "primary_delta_bps": delta,
        "gross_drive_bps": primary_gross,
        "gross_stale_placebo_bps": baseline_gross,
        "fixed_sample_gate_pass": sufficient,
        "by_year_descriptive_only": years,
        "directional_baseline_not_volatility_matched": True,
        "bid_ask_spread_slippage_unmeasured": True,
        "economic_tradability_unproved": True,
        "profit_factor_sharpe_sortino_dd_not_estimated": True,
        "not_an_executable_strategy": True,
        "no_orderflow_inference": True,
        "no_vps_no_mt5_no_live_no_trade": True,
        "verdict": verdict,
    }
    return report, [
        {
            "date_ny": v.ny_date, "week": v.iso_week, "year": v.year,
            "formation_log": v.formation_log,
            "drive_direction": v.drive_direction,
            "stale_direction": v.stale_direction,
            "prior_observed_date": v.prior_date,
            "prior_age_calendar_days": v.prior_age_days,
            "forward_bps": v.forward_bps,
            "gross_drive_bps": v.gross_drive_bps,
            "gross_stale_bps": v.gross_stale_bps,
            "delta_bps": v.delta_bps,
        } for v in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original_native_cibo_nas100_m1", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, records = analyze(args.original_native_cibo_nas100_m1)
    args.output.mkdir(parents=True, exist_ok=True)
    results = {
        "drive-g1-nas100-report.json": json.dumps(report, indent=2, sort_keys=True) + "\n",
        "drive-g1-nas100-day-pairs.jsonl": "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in records
        ),
    }
    for filename, content in results.items():
        (args.output / filename).write_text(content, encoding="utf-8")
        (args.output / (filename + ".sha256")).write_text(
            hashlib.sha256(content.encode()).hexdigest() + "  " + filename + "\n"
        )
    print(json.dumps({
        "verdict": report["verdict"], "matched_days": report["matched_days"],
        "gross_drive_bps": report["gross_drive_bps"],
        "gross_stale_bps": report["gross_stale_placebo_bps"],
        "delta_bps": report["primary_delta_bps"],
        "ci95": report["bootstrap"]["ci95_delta_bps"],
        "native_m1": True, "economic_execution_unproved": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
