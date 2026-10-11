"""One prespecified, post-G1 exploratory cTrader-native EURUSD M1 RESET sensitivity.

Read-only, consumed DEV evidence. G1 pressure and quantiles remain unchanged.
No bid/ask is needed for gross directional falsification; no net-PnL claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_reset_fix_g1_v1 as g1

IDENTITY = "QORE_NATIVE_RESET_FIX_G2_CTRADER_M1_EXPLORATORY_V1"
M1_RUN = 35548099334
M1_ARTIFACT = 10618547852
M1_HEAD_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
M1_IDENTITY = "QORE_CAPITALIZER_CIBO_10Y_NATIVE_M1_CLONE_V1"
M1_SCHEMA = "qore.capitalizer.cibo.raw_m1.v1"
M1_WINDOWS = {
    "FIX": (16 * 60 + 3, 16 * 60 + 15),
    "PLACEBO": (14 * 60 + 3, 14 * 60 + 15),
}
NEEDED_LOCAL_MINUTES = {minute for clock in M1_WINDOWS.values() for minute in clock}
PREREG_SHA = "3d96c55b06d376b26fc9e501be9fe9d2539f59b4"


@dataclass(frozen=True, slots=True)
class M1Open:
    timestamp_utc: datetime
    open_price: float


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for buffer in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(buffer)
    return h.hexdigest()


def manifest_m1(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    file = root / "m1-clone-manifest.json"
    checksum_file = root / "MANIFEST_SHA256SUMS.txt"
    if not file.is_file() or not checksum_file.is_file():
        raise ValueError("CIBO 10Y native M1 manifest/witness missing")
    expected = checksum_file.read_text().strip().split(maxsplit=1)
    if len(expected) != 2 or expected[1] != file.name or expected[0] != sha256(file):
        raise ValueError("CIBO M1 manifest sha256 mismatch")
    data = json.loads(file.read_text())
    if (data.get("identity") != M1_IDENTITY
            or data.get("schema") != "qore.capitalizer.cibo.m1_clone.v1"
            or data.get("canonical_symbol") != "EURUSD"
            or data.get("provider_symbol") != "EURUSD"
            or data.get("target_start") != g1.START_UTC.isoformat()
            or data.get("target_end_exclusive") != g1.END_UTC.isoformat()
            or data.get("digits") != 5
            or data.get("provider_native_m1") is not True
            or data.get("synthetic_m1") is not False
            or data.get("interpolated_m1") is not False
            or data.get("read_only") is not True
            or data.get("live_authorized") is not False
            or data.get("production_authorized") is not False
            or data.get("contradictory_m1") != 0):
        raise ValueError("CIBO provider-native M1 immutable contract changed")
    partitions = data.get("partitions")
    if not isinstance(partitions, list) or [row["partition"] for row in partitions] != [
        str(year) for year in range(2016, 2027)
    ]:
        raise ValueError("M1 annual partition inventory changed")
    if type(data.get("retained_m1")) is not int or data["retained_m1"] <= 0:
        raise ValueError("invalid total native M1 count")
    return data, {"m1_manifest_sha256": sha256(file), "source_artifact": M1_ARTIFACT,
                  "source_run": M1_RUN, "source_sha": M1_HEAD_SHA,
                  "provider_native": True, "consumed_development_only": True}


def read_native_m1(root: Path) -> tuple[dict[date, dict[int, M1Open]], dict[str, Any]]:
    """Read all original native M1 ledgers, validate SHA/count, retain only 4 open slots."""
    manifest, evidence = manifest_m1(root)
    retained: dict[date, dict[int, M1Open]] = {}
    previous: datetime | None = None
    seen_total = 0
    annual_counts: dict[str, int] = {}
    active_symbol_id: int | None = None
    for entry in manifest["partitions"]:
        year = entry["partition"]
        raw = root / "RAW_M1_LEDGER" / (year + ".jsonl")
        if not raw.is_file() or sha256(raw) != entry.get("raw_sha256"):
            raise ValueError("CIBO native raw M1 SHA256 mismatch: " + year)
        count = 0
        with raw.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if (row.get("schema") != M1_SCHEMA
                        or row.get("identity") != M1_IDENTITY
                        or row.get("canonical_symbol") != "EURUSD"
                        or row.get("provider_symbol") != "EURUSD"
                        or row.get("digits") != 5
                        or type(row.get("provider_symbol_id")) is not int):
                    raise ValueError("unexpected CIBO native M1 row identity")
                symbol_id = row["provider_symbol_id"]
                if symbol_id <= 0 or (active_symbol_id is not None
                                       and symbol_id != active_symbol_id):
                    raise ValueError("native M1 provider symbol identity changed")
                active_symbol_id = symbol_id
                when = datetime.fromisoformat(row["opened_at"])
                if when.tzinfo is None or when.utcoffset() is None:
                    raise ValueError("M1 provider timestamp has no timezone")
                when = when.astimezone(UTC)
                if (not g1.START_UTC <= when < g1.END_UTC
                        or str(when.year) != year
                        or when.second or when.microsecond
                        or (previous is not None and when <= previous)
                        or row.get("utc_timestamp_in_minutes") != int(when.timestamp() / 60)):
                    raise ValueError("unaligned, out of window or nonmonotone native M1")
                previous = when
                opening = row.get("open_relative")
                high = row.get("high_relative")
                low = row.get("low_relative")
                close = row.get("close_relative")
                if (any(type(x) is not int for x in (opening, high, low, close))
                        or not (0 < low <= min(opening, close) <= max(opening, close) <= high)):
                    raise ValueError("invalid original provider OHLC M1")
                local = when.astimezone(g1.LONDON)
                minutes = local.hour * 60 + local.minute
                if local.weekday() < 5 and minutes in NEEDED_LOCAL_MINUTES:
                    day = local.date()
                    daily = retained.setdefault(day, {})
                    if minutes in daily:
                        raise ValueError("duplicated EURUSD native M1 timestamp at event")
                    daily[minutes] = M1Open(when, opening / 100000)
                count += 1
        if count != entry.get("retained_m1"):
            raise ValueError("CIBO native M1 annual bar count mismatch")
        annual_counts[year] = count
        seen_total += count
    if seen_total != manifest["retained_m1"]:
        raise ValueError("CIBO 10Y native M1 total bar count mismatch")
    evidence.update({"native_m1_count": seen_total, "annual_native_m1": annual_counts,
                     "original_ohlc_modified": False, "reserved_pre2016_ohlc_read": False})
    return retained, evidence


def native_open(day: date, local_minute: int,
                bars: dict[int, M1Open]) -> float | None:
    record = bars.get(local_minute)
    if record is None:
        return None
    expected = datetime(day.year, day.month, day.day,
                        local_minute // 60, local_minute % 60,
                        tzinfo=g1.LONDON).astimezone(UTC)
    if record.timestamp_utc != expected:
        raise ValueError("M1 timestamp does not match DST-adjusted local clock")
    if record.open_price <= 0:
        raise ValueError("nonpositive M1 price")
    return record.open_price


def reversals(event: g1.Event, readings: dict[int, M1Open]) -> tuple[float, float] | None:
    day = date.fromisoformat(event.day)
    for arm in ("FIX", "PLACEBO"):
        for minute in M1_WINDOWS[arm]:
            if native_open(day, minute, readings) is None:
                return None
    new = []
    for arm, pressure in (
        ("FIX", event.fixing_pressure_bps),
        ("PLACEBO", event.placebo_pressure_bps),
    ):
        start, finish = M1_WINDOWS[arm]
        entry = native_open(day, start, readings)
        exit_ = native_open(day, finish, readings)
        assert entry is not None and exit_ is not None
        if pressure == 0:
            raise ValueError("G1 nonzero pressure cohort unexpectedly contains zero")
        new.append(-math.copysign(1, pressure) * 10000 * math.log(exit_ / entry))
    return new[0], new[1]


def run(root_m5: Path, root_m1: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observed_g1, m5_source = g1.read_existing_cibo_atlas(root_m5)
    g1_events, g1_quality = g1.build_events(observed_g1)
    observed_m1, m1_source = read_native_m1(root_m1)
    selected: list[g1.Event] = []
    reasons: Counter[str] = Counter()
    dates: list[dict[str, Any]] = []
    for prior in g1_events:
        values = reversals(prior, observed_m1.get(date.fromisoformat(prior.day), {}))
        if values is None:
            reasons["MISSING_M1_ENTRY_OR_EXIT_JOINT_PAIR"] += 1
            continue
        fixed, placebo = values
        event = replace(
            prior, fixing_reversal_bps=fixed, placebo_reversal_bps=placebo
        )
        selected.append(event)
        reasons["USABLE_MATCHED_G1_M1"] += 1
        dates.append({
            "date_london": event.day, "week": event.week,
            "fixing_class": event.fixing_class, "placebo_class": event.placebo_class,
            "fixing_pressure_bps_g1": event.fixing_pressure_bps,
            "placebo_pressure_bps_g1": event.placebo_pressure_bps,
            "fixing_tail_reversal_bps_m1": fixed,
            "placebo_tail_reversal_bps_m1": placebo,
        })
    cells, d = g1.stratified_means(selected)
    enough = len(selected) >= g1.MIN_DAYS and all(
        cell["n"] >= g1.MIN_PER_CELL for cell in cells.values()
    )
    bootstrap = (g1.bootstrap_weekly(selected) if enough else {
        "ci95_d_bps": None, "skip_reason": "PREDECLARED_SAMPLE_GATE",
        "valid_draws": 0,
    })
    bounds = bootstrap["ci95_d_bps"]
    if not enough:
        verdict = "DEV_M1_UNDERPOWERED"
    elif (d is not None and d > 0 and bounds is not None and bounds[0] > 0
          and cells["FIX_HIGH"]["mean_reversal_bps"] > 0):
        verdict = "DEV_M1_GROSS_SIGNAL_FOR_COST_AUDIT"
    else:
        verdict = "DEV_M1_GROSS_NO_SUPPORT"
    report = {
        "identity": IDENTITY, "prereg_sha": PREREG_SHA,
        "post_g1_exploratory_not_confirmatory": True,
        "g1_rules_changed": False, "original_g1_verdict": "DEV_GROSS_NO_SUPPORT",
        "costs_not_observed": True, "bidask_not_required_for_gross_signal": True,
        "profit_factor_sharpe_sortino_pnl_not_estimated": True,
        "source_from_archived_cibo_gh_actions_only": True,
        "ctrader_oauth_called": False, "tick_data_used": False,
        "reserved_2014_2016_raw_not_opened": True,
        "no_vps_no_live_no_trader_certification": True,
        "g1_m5_source": m5_source, "native_m1_source": m1_source,
        "g1_cohort_days": len(g1_events),
        "m1_matched_days": len(selected),
        "joint_rejection_reasons": dict(reasons),
        "g1_quality": g1_quality,
        "primary_windows_local_europe_london": M1_WINDOWS,
        "four_cells": cells, "primary_d_bps": d, "bootstrap": bootstrap,
        "sample_gate_pass": enough, "verdict": verdict,
        "rule": "FIX_16:03_TO_16:15_v_PLACEBO_14:03_TO_14:15_SAME_G1_PRESSURE_P75_120",
    }
    return report, dates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_m5", type=Path)
    parser.add_argument("source_m1", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    report, dates = run(args.source_m5, args.source_m1)
    args.out.mkdir(parents=True, exist_ok=True)
    outputs = {
        "g2-m1-report.json": json.dumps(report, sort_keys=True, indent=2) + "\n",
        "g2-m1-joint-days.jsonl": "".join(json.dumps(row, sort_keys=True) + "\n"
                                            for row in dates),
    }
    for filename, content in outputs.items():
        file = args.out / filename
        file.write_text(content, encoding="utf-8")
        (args.out / (filename + ".sha256")).write_text(
            hashlib.sha256(content.encode()).hexdigest() + "  " + filename + "\n"
        )
    print(json.dumps({"status": report["verdict"],
                      "matched_days": report["m1_matched_days"],
                      "effect_bps": report["primary_d_bps"],
                      "ci95_bps": report["bootstrap"]["ci95_d_bps"],
                      "no_oauth": True, "post_g1_exploratory": True}, sort_keys=True))


if __name__ == "__main__":
    main()
