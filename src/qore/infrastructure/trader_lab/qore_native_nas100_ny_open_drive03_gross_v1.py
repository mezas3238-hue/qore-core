"""QORE Native OPEN-DRIVE-03: frozen NAS100 US cash-open direction, GROSS only.

Research-only observational paired study: 09:30-10:00 NY drive sign vs
09:00-09:30 NY CFD premarket sign for 10:00-12:00 NY reference returns.
No BID/ASK execution, no news-as-of filter, no LIVE or broker session assertion.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0

IDENTITY = "QORE_NATIVE_NAS100_NY_OPEN_DRIVE03_V1"
PREREG_COMMIT = "4b26a2da961da6f778028835efaa7ea899ebda9d"
SYMBOL = "NAS100"
PROVIDER_SYMBOL = "USTEC"
NEW_YORK = ZoneInfo("America/New_York")
START_UTC = datetime(2016, 9, 17, tzinfo=UTC)
DEV_END_UTC = datetime(2022, 9, 17, tzinfo=UTC)
EMBARGO_UTC = datetime(2024, 9, 17, tzinfo=UTC)
SOURCE_END_UTC = datetime(2026, 9, 17, tzinfo=UTC)
BOOTS = 2000
SEED = 20261012
MIN_DAYS = 300
MIN_ISO_WEEKS = 52
ROUNDTRIP_COST_BPS = (0, 1, 3, 5, 10, 20)
STATUS = "RESEARCH_GROSS_NEWS_UNFILTERED_NO_OPERATIONS"
BLOCK_HOURS = {"PRE": (9, 0, 6), "DRIVE": (9, 30, 6), "TARGET": (10, 0, 24)}


def sign(value: int) -> int:
    return (value > 0) - (value < 0)


@dataclass(slots=True)
class ClockBlock:
    first_local: datetime
    last_local: datetime
    first_open: int
    last_close: int
    count: int = 1
    contiguous: bool = True

    def add(self, at: datetime, close: int) -> None:
        if (at.astimezone(UTC) - self.last_local.astimezone(UTC)) != timedelta(minutes=5):
            self.contiguous = False
        self.last_local = at
        self.last_close = close
        self.count += 1


def required_slot(at: datetime) -> str | None:
    """Known-in-advance NY local clock, DST handled by ZoneInfo."""
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("naive timestamp")
    ny = at.astimezone(NEW_YORK)
    if ny.weekday() >= 5:
        return None
    minute = ny.hour * 60 + ny.minute
    if 9 * 60 <= minute < 9 * 60 + 30:
        return "PRE"
    if 9 * 60 + 30 <= minute < 10 * 60:
        return "DRIVE"
    if 10 * 60 <= minute < 12 * 60:
        return "TARGET"
    return None


def source_blocks(root: Path) -> tuple[dict[date, dict[str, ClockBlock]], dict[str, int]]:
    """Ignore OHLC of all rows on/after 2024-09-17 UTC."""
    days: dict[date, dict[str, ClockBlock]] = {}
    seen_before: datetime | None = None
    counts = {"original_m5_timestamps_before_embargo": 0,
              "eligible_ny_day_candidates_with_any_required_slot": 0,
              "individual_required_slot_bars": 0}
    for year in range(2016, 2025):
        raw = root / "RAW_M5_LEDGER" / f"{year}.jsonl"
        with raw.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                timestamp = datetime.fromisoformat(row["opened_at"])
                if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                    raise ValueError("source M5 naive opened_at")
                at = timestamp.astimezone(UTC)
                if not START_UTC <= at < EMBARGO_UTC:
                    continue  # Price fields never referenced for embargo rows.
                if (seen_before is not None and at <= seen_before
                        or at.second or at.microsecond or at.minute % 5):
                    raise ValueError("original M5 chronology invalid")
                seen_before = at
                counts["original_m5_timestamps_before_embargo"] += 1
                slot = required_slot(at)
                if slot is None:
                    continue
                if (row.get("identity") != g0.PRODUCER
                        or row.get("schema") != g0.RAW_SCHEMA
                        or row.get("canonical_symbol") != SYMBOL
                        or row.get("provider_symbol") != PROVIDER_SYMBOL
                        or type(row.get("open_relative")) is not int
                        or type(row.get("close_relative")) is not int
                        or type(row.get("low_relative")) is not int
                        or type(row.get("high_relative")) is not int):
                    raise ValueError("NAS100 source identity and raw OHLC integers required")
                op, cl = row["open_relative"], row["close_relative"]
                lo, hi = row["low_relative"], row["high_relative"]
                if lo <= 0 or lo > min(op, cl) or hi < max(op, cl):
                    raise ValueError("source OHLC internal boundaries invalid")
                ny = at.astimezone(NEW_YORK)
                blocks = days.setdefault(ny.date(), {})
                if slot in blocks:
                    blocks[slot].add(ny, cl)
                else:
                    blocks[slot] = ClockBlock(ny, ny, op, cl)
                counts["individual_required_slot_bars"] += 1
    counts["eligible_ny_day_candidates_with_any_required_slot"] = len(days)
    return days, counts


def evaluate_ny_day(day: date, blocks: dict[str, ClockBlock]) -> dict[str, Any] | None:
    """Read only 9:00–10:00 closed bars for both directions."""
    for name, (hour, minute, expected_count) in BLOCK_HOURS.items():
        block = blocks.get(name)
        if block is None:
            return None
        first_expected = datetime(day.year, day.month, day.day, hour, minute,
                                  tzinfo=NEW_YORK)
        last_expected = first_expected + timedelta(minutes=(expected_count - 1) * 5)
        if (block.count != expected_count or not block.contiguous
                or block.first_local.astimezone(UTC) != first_expected.astimezone(UTC)
                or block.last_local.astimezone(UTC) != last_expected.astimezone(UTC)):
            return None
    pre, drive, target = blocks["PRE"], blocks["DRIVE"], blocks["TARGET"]
    if (drive.first_local.astimezone(UTC) - pre.last_local.astimezone(UTC)
            != timedelta(minutes=5)
            or target.first_local.astimezone(UTC) - drive.last_local.astimezone(UTC)
            != timedelta(minutes=5)):
        return None
    s_open = sign(drive.last_close - drive.first_open)
    s_pre = sign(pre.last_close - pre.first_open)
    if not s_open or not s_pre:
        return None
    if target.first_open <= 0:
        raise ValueError("invalid 10:00 reference entry")
    return_bps = 10000 * (target.last_close - target.first_open) / target.first_open
    week = day.isocalendar()
    return {
        "ny_date": day.isoformat(),
        "ny_iso_week": f"{week.year}-W{week.week:02d}",
        "open_drive_sign": s_open,
        "pre_open_baseline_sign": s_pre,
        "strategy_gross_bps": s_open * return_bps,
        "baseline_gross_bps": s_pre * return_bps,
        "paired_delta_bps": (s_open - s_pre) * return_bps,
        "price_reference_only_not_executable": True,
    }


def weekly_bootstrap(data: list[dict[str, Any]], field: str) -> dict[str, float | int] | None:
    weeks: dict[str, list[float]] = defaultdict(list)
    for item in data:
        weeks[item["ny_iso_week"]].append(item[field])
    if not weeks:
        return None
    groups = [(sum(weeks[k]), len(weeks[k])) for k in sorted(weeks)]
    rng = random.Random(SEED)
    result: list[float] = []
    for _ in range(BOOTS):
        total = count = 0
        for _ in range(len(groups)):
            s, n = groups[rng.randrange(len(groups))]
            total += s
            count += n
        result.append(total / count)
    result.sort()
    return {
        "lower_98_333pct": result[int(BOOTS / 120)],
        "upper_98_333pct": result[int(BOOTS * 119 / 120)],
        "week_clusters": len(groups),
        "bootstrap_draws": BOOTS,
        "seed": SEED,
    }


def summarize(events: list[dict[str, Any]], name: str) -> dict[str, Any]:
    n = len(events)
    weeks = len({r["ny_iso_week"] for r in events})
    v = [r["strategy_gross_bps"] for r in events]
    b = [r["baseline_gross_bps"] for r in events]
    diff = [r["paired_delta_bps"] for r in events]
    ci_delta = weekly_bootstrap(events, "paired_delta_bps")
    ci_gross = weekly_bootstrap(events, "strategy_gross_bps")
    gross = mean(v) if n else None
    paired = mean(diff) if n else None
    adequate = n >= MIN_DAYS and weeks >= MIN_ISO_WEEKS
    accepted = bool(
        adequate and ci_delta is not None and gross is not None and paired is not None
        and paired > 0 and ci_delta["lower_98_333pct"] > 0 and gross > 0
    )
    state = (
        "INCONCLUSIVE_UNDERPOWERED_BY_PRESET_GATE" if not adequate
        else "EXPLORATORY_GROSS_SUPPORT_NOT_NET" if accepted
        else "NO_SUPPORT_FOR_FROZEN_NY_OPEN_DRIVE"
    )
    return {
        "period": name,
        "n_paired_days": n,
        "n_NY_iso_week_clusters": weeks,
        "gross_strategy_mean_bps": gross,
        "gross_baseline_mean_bps": mean(b) if b else None,
        "paired_mean_delta_bps": paired,
        "weekly_bootstrap_delta_CI98_333pct": ci_delta,
        "weekly_bootstrap_gross_CI98_333pct": ci_gross,
        "long_days": sum(x["open_drive_sign"] == 1 for x in events),
        "short_days": sum(x["open_drive_sign"] == -1 for x in events),
        "positive_gross_fraction": sum(x > 0 for x in v) / n if n else None,
        "mean_roundtrip_break_even_bps": gross,
        "hypothetical_total_RT_cost_not_actual_broker": [
            {"assumed_RT_cost_bps": cost,
             "gross_minus_assumed_cost_bps": (gross - cost) if gross is not None else None}
            for cost in ROUNDTRIP_COST_BPS
        ],
        "net_economics_certified": False,
        "verdict": state,
    }


def run(root: Path, aggregate: Path) -> dict[str, Any]:
    expected = g0.aggregate_index(aggregate)
    attestation = g0.audit_symbol(SYMBOL, root, expected[SYMBOL])
    if attestation["status"] != "G0_M5_SOURCE_INTEGRITY_PASS":
        raise ValueError("frozen source SHA evidence invalid")
    days, availability = source_blocks(root)
    dev: list[dict[str, Any]] = []
    diag: list[dict[str, Any]] = []
    skipped = 0
    for day, three in sorted(days.items()):
        signal = evaluate_ny_day(day, three)
        if signal is None:
            skipped += 1
            continue
        sample_time = datetime(day.year, day.month, day.day, 10, tzinfo=NEW_YORK).astimezone(UTC)
        if sample_time < DEV_END_UTC:
            dev.append(signal)
        elif sample_time < EMBARGO_UTC:
            diag.append(signal)
        else:
            raise ValueError("attempted embargo outcome")
    d = summarize(dev, "DEVELOPMENT_2016_09_17_2022_09_17")
    t = summarize(diag, "TEMPORAL_DIAGNOSTIC_2022_09_17_2024_09_17")
    availability["incomplete_or_zero_signal_days"] = skipped
    return {
        "identity": IDENTITY, "status": STATUS,
        "prereg_committed_before_any_outcome": PREREG_COMMIT,
        "fixed_symbol": SYMBOL, "original_provider_alias": PROVIDER_SYMBOL,
        "original_source_run": g0.SOURCE_RUN,
        "original_source_sha": g0.PRODUCER_SHA,
        "original_m5_bars_sha_verified": attestation["native_m5_bars"],
        "manifest_sha256": attestation["symbol_manifest_sha256"],
        "all_11_annual_raw_and_quality_SHA_verified": True,
        "clock": "America/New_York DST 09:00-12:00 RESEARCH blocks, NOT BROKER SESSIONS",
        "dev_end_utc": DEV_END_UTC.isoformat(),
        "embargo_from_utc": EMBARGO_UTC.isoformat(),
        "later_OHLC_not_accessed": True,
        "source_census": availability,
        "development": d,
        "temporal_diagnostic": t,
        "both_windows_gross_support": (
            d["verdict"] == "EXPLORATORY_GROSS_SUPPORT_NOT_NET"
            and t["verdict"] == "EXPLORATORY_GROSS_SUPPORT_NOT_NET"
        ),
        "three_attempts_accounted_for": ["EURUSD_H4_GROSS01_NO_SUPPORT",
                                         "XAUUSD_H4_GROSS02_NO_SUPPORT",
                                         "NAS100_NY_OPEN_DRIVE03_THIS_TRIAL"],
        "news_asof_calendar_verified": False,
        "broker_H4_D1_sessions_certified": False,
        "broker_executable_bidask_verified": False,
        "strategy_stop_or_fills_defined": False,
        "net_certified": False, "live_or_paper_authorized": False,
        "traders_certified": 0, "production_untouched": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("original_aggregate", type=Path)
    ap.add_argument("output", type=Path)
    a = ap.parse_args()
    result = run(a.source, a.original_aggregate)
    a.output.mkdir(parents=True, exist_ok=True)
    path = a.output / "qore-native-nas100-ny-open-drive03-gross.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.with_name(path.name + ".sha256").write_text(
        g0.sha256(path) + f"  {path.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": STATUS,
        "pre_outcome_sha": PREREG_COMMIT,
        "dev_verdict": result["development"]["verdict"],
        "diag_verdict": result["temporal_diagnostic"]["verdict"],
        "n_dev": result["development"]["n_paired_days"],
        "n_diag": result["temporal_diagnostic"]["n_paired_days"],
        "live": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
