"""QORE Native H4-GROSS-01: one preregistered EURUSD UTC 4h price phenomenon.

GROSS OHLC-only scientific test, NOT broker H4 candles, news safe or fills.
Freeze provenance and prereg before price outcomes. No live/MT5/trading imports.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, date
from pathlib import Path
from statistics import mean
from typing import Any

from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0

IDENTITY = "QORE_NATIVE_H4_GROSS01_EURUSD_12H_VS_4H_RESEARCH_V1"
PREREG_COMMIT = "a4424ba3027018bab54f03aff668894f63f47da9"
DEV_END = date(2022, 9, 17)
DIAGNOSTIC_END = date(2024, 9, 17)
START = date(2016, 9, 17)
WEEK_BOOTSTRAPS = 2000
BOOTSTRAP_SEED = 20261012
COST_GRID_BPS = (0, 1, 3, 5, 10, 20)
MIN_EVENTS = 300
MIN_WEEKS = 52
TARGET_HOUR_UTC = 16
REQUIRED_STARTS_UTC = (4, 8, 12, 16)
STATUS = "GROSS_PHENOMENON_ONLY_NEWS_UNFILTERED"
SOURCE_SYMBOL = "EURUSD"


def sign(value: int) -> int:
    return (value > 0) - (value < 0)


@dataclass(slots=True)
class Block:
    opened: datetime
    first_open: int
    last_close: int
    last_at: datetime
    bars: int = 1
    contiguous: bool = True

    def push(self, at: datetime, open_: int, close: int) -> None:
        if (at - self.last_at).total_seconds() != 300:
            self.contiguous = False
        self.last_close = close
        self.last_at = at
        self.bars += 1


def read_clock_blocks(source: Path) -> tuple[dict[date, dict[int, Block]], dict[str, int]]:
    """Read RAW EURUSD only up to 2024-09-17; no later OHLC even parsed."""
    days: dict[date, dict[int, Block]] = {}
    counters = {
        "eligible_utc_day_candidates": 0,
        "source_m5_rows_in_research_span": 0,
        "incomplete_required_h4_blocks": 0,
    }
    previous: datetime | None = None
    for year in range(2016, 2025):
        path = source / "RAW_M5_LEDGER" / f"{year}.jsonl"
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                raw = json.loads(line)
                at = datetime.fromisoformat(raw["opened_at"]).astimezone(UTC)
                if at.date() < START or at.date() >= DIAGNOSTIC_END:
                    continue  # NO OHLC access to quarantined data.
                if (previous is not None and at <= previous or at.minute % 5
                        or at.second or at.microsecond):
                    raise ValueError("EURUSD original M5 timestamp chronology malformed")
                previous = at
                counters["source_m5_rows_in_research_span"] += 1
                hour = (at.hour // 4) * 4
                if hour not in REQUIRED_STARTS_UTC:
                    continue
                if (raw.get("schema") != g0.RAW_SCHEMA
                        or raw.get("identity") != g0.PRODUCER
                        or raw.get("canonical_symbol") != SOURCE_SYMBOL
                        or raw.get("provider_symbol") != SOURCE_SYMBOL
                        or type(raw.get("open_relative")) is not int
                        or type(raw.get("close_relative")) is not int
                        or type(raw.get("high_relative")) is not int
                        or type(raw.get("low_relative")) is not int):
                    raise ValueError("original EURUSD M5 source/price invalid")
                lo = raw["low_relative"]
                hi = raw["high_relative"]
                op = raw["open_relative"]
                cl = raw["close_relative"]
                if lo <= 0 or lo > min(op, cl) or hi < max(op, cl) or op <= 0:
                    raise ValueError("original M5 OHLC not internally valid")
                d = at.date()
                row = days.setdefault(d, {})
                if hour in row:
                    row[hour].push(at, op, cl)
                else:
                    row[hour] = Block(at, op, cl, at)
    counters["eligible_utc_day_candidates"] = len(days)
    return days, counters


def evaluate_day(d: date, blocks: dict[int, Block]) -> dict[str, Any] | None:
    for h in REQUIRED_STARTS_UTC:
        if h not in blocks:
            return None
        b = blocks[h]
        expected = datetime(d.year, d.month, d.day, h, tzinfo=UTC)
        if (b.bars != 48 or not b.contiguous or b.opened != expected
                or b.last_at != expected.replace(hour=h + 3, minute=55)):
            return None
    first = blocks[4]
    last = blocks[12]
    target = blocks[16]
    s12 = sign(last.last_close - first.first_open)
    s4 = sign(last.last_close - last.first_open)
    if not s12 or not s4:
        return None
    if last.last_at.timestamp() + 300 != target.opened.timestamp():
        return None
    if target.first_open <= 0:
        raise ValueError("invalid target opening reference price")
    change_bps = 10000 * (target.last_close - target.first_open) / target.first_open
    iso = d.isocalendar()
    return {
        "date": d.isoformat(),
        "iso_week": f"{iso.year}-W{iso.week:02}",
        "signal_12h": s12,
        "control_4h": s4,
        "signed_gross_bps": s12 * change_bps,
        "control_gross_bps": s4 * change_bps,
        "paired_delta_bps": (s12 - s4) * change_bps,
        "reference_entry_price_relative": target.first_open,
        "reference_exit_price_relative": target.last_close,
        "observation_only_not_executable": True,
    }


def bootstrap_week_mean(
    rows: list[dict[str, Any]], field: str, seed: int = BOOTSTRAP_SEED,
) -> dict[str, float | int] | None:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[row["iso_week"]].append(row[field])
    if not groups:
        return None
    weeks = sorted(groups)
    weekly = [(sum(groups[k]), len(groups[k])) for k in weeks]
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(WEEK_BOOTSTRAPS):
        s = count = 0
        for _ in range(len(weeks)):
            total, n = weekly[rng.randrange(len(weeks))]
            s += total
            count += n
        samples.append(s / count)
    samples.sort()
    return {
        "low95": samples[int(0.025 * WEEK_BOOTSTRAPS)],
        "high95": samples[int(0.975 * WEEK_BOOTSTRAPS)],
        "bootstrap_count": WEEK_BOOTSTRAPS,
        "seed": seed,
        "cluster_units": len(weeks),
    }


def summarize(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    gross = [x["signed_gross_bps"] for x in rows]
    baseline = [x["control_gross_bps"] for x in rows]
    delta = [x["paired_delta_bps"] for x in rows]
    n = len(rows)
    weeks = len({x["iso_week"] for x in rows})
    ci_delta = bootstrap_week_mean(rows, "paired_delta_bps")
    ci_gross = bootstrap_week_mean(rows, "signed_gross_bps")
    g = mean(gross) if gross else None
    dev_testable = n >= MIN_EVENTS and weeks >= MIN_WEEKS
    supported = bool(
        dev_testable and ci_delta is not None and g is not None
        and mean(delta) > 0 and ci_delta["low95"] > 0 and g > 0
    )
    if not dev_testable:
        verdict = "INCONCLUSIVE_UNDERPOWERED_BY_PRESET_GATE"
    elif supported:
        verdict = "EXPLORATORY_GROSS_SUPPORT_NOT_NET"
    else:
        verdict = "NO_SUPPORT_FOR_FROZEN_GROSS_HYPOTHESIS"
    return {
        "window": name,
        "n_events_days": n,
        "n_iso_week_clusters": weeks,
        "mean_signed_gross_bps": g,
        "mean_baseline_gross_bps": mean(baseline) if baseline else None,
        "mean_paired_delta_bps": mean(delta) if delta else None,
        "delta_bootstrap_week_CI95": ci_delta,
        "gross_bootstrap_week_CI95": ci_gross,
        "break_even_total_rt_cost_bps": g,
        "hypothetical_cost_grid_not_broker_spread": [
            {"rt_cost_bps": cost,
             "mean_after_assumed_rt_cost_bps": None if g is None else g - cost}
            for cost in COST_GRID_BPS
        ],
        "positive_signed_gross_fraction": (
            sum(v > 0 for v in gross) / n if n else None
        ),
        "long_events": sum(x["signal_12h"] == 1 for x in rows),
        "short_events": sum(x["signal_12h"] == -1 for x in rows),
        "economic_net_certified": False,
        "verdict": verdict,
    }


def run(symbol_source: Path, original_aggregate: Path) -> dict[str, Any]:
    witness = g0.aggregate_index(original_aggregate)
    g0_audit = g0.audit_symbol(SOURCE_SYMBOL, symbol_source, witness[SOURCE_SYMBOL])
    if g0_audit["status"] != "G0_M5_SOURCE_INTEGRITY_PASS":
        raise ValueError("SHA-validated native EURUSD original source required")
    blocks, counters = read_clock_blocks(symbol_source)
    dev: list[dict[str, Any]] = []
    diag: list[dict[str, Any]] = []
    incomplete = 0
    for d, subset in sorted(blocks.items()):
        outcome = evaluate_day(d, subset)
        if outcome is None:
            incomplete += 1
        elif d < DEV_END:
            dev.append(outcome)
        else:
            diag.append(outcome)
    counters["incomplete_required_h4_blocks"] = incomplete
    dev_out = summarize(dev, "DEVELOPMENT_2016_09_17_TO_2022_09_17")
    diag_out = summarize(diag, "TEMPORAL_DIAGNOSTIC_2022_09_17_TO_2024_09_17")
    supported_both = (
        dev_out["verdict"] == "EXPLORATORY_GROSS_SUPPORT_NOT_NET"
        and diag_out["verdict"] == "EXPLORATORY_GROSS_SUPPORT_NOT_NET"
    )
    return {
        "identity": IDENTITY,
        "status": STATUS,
        "prereg_commit_before_outcomes": PREREG_COMMIT,
        "original_source_run": g0.SOURCE_RUN,
        "original_source_sha": g0.PRODUCER_SHA,
        "source_symbol": SOURCE_SYMBOL,
        "source_manifest_sha256": g0_audit["symbol_manifest_sha256"],
        "raw_11_annual_sha_verified": True,
        "original_eurusd_m5_bars": g0_audit["native_m5_bars"],
        "clock_utc_synthetic_h4_not_broker_h4": True,
        "all_23_universe_winners_examined": False,
        "utc_target_hours": [16, 20],
        "split_2022_09_17": DEV_END.isoformat(),
        "reserved_2024_09_17_onward_OHLC_not_accessed": True,
        "research_source_counts": counters,
        "development": dev_out,
        "temporal_diagnostic": diag_out,
        "directional_gross_support_in_both": supported_both,
        "net_certified": False,
        "news_calendar_known_asof_verified": False,
        "no_news_policy_operational_compliance_certified": False,
        "trading_strategy_stop_defined": False,
        "capital_or_live_authorized": False,
        "paper_authorized": False,
        "traders_certified": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("source_aggregate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = run(args.source, args.source_aggregate)
    args.output.mkdir(parents=True, exist_ok=True)
    file = args.output / "qore-native-h4-gross01-eurusd.json"
    file.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / (file.name + ".sha256")).write_text(
        g0.sha256(file) + f"  {file.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": STATUS,
        "prereg": PREREG_COMMIT,
        "dev": output["development"]["verdict"],
        "diagnostic": output["temporal_diagnostic"]["verdict"],
        "n_dev": output["development"]["n_events_days"],
        "n_diag": output["temporal_diagnostic"]["n_events_days"],
        "net_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
