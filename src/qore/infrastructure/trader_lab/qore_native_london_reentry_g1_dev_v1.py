"""QORE Native London Reentry G1 DEV — causal fixed-rule OHLC proxy experiment.

The experiment reads immutable cTrader DEMO archives already held in GitHub,
parses only pre-VT08-cutoff M5/M15 observations, and never contacts cTrader.
No trader authorization, spread claim, live trading or unseen OOS inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from math import isfinite
from pathlib import Path
from statistics import mean
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.qore_native_existing_demo_fx_archive_inventory_v1 import (
    SOURCE_COMMIT,
    SOURCE_RUN_ID,
    build_inventory,
    metadata_prefix,
)

IDENTITY = "QORE_NATIVE_LONDON_REENTRY_G1_FIXED_DEV_V1"
PREREG = "docs/research/QORE_NATIVE_LONDON_REENTRY_G1_FROZEN_DEV_PREREG_2026-10-11.md"
SOURCE_SHA = {
    "EURJPY": "2a3afd8075b70fd7791ffbdefb15214e7174e7be7e0367cfa49037aa6b7af3e5",
    "USDCHF": "6afd148635907ba936a52c25817cacac7397de4da224a1b2581e75fa95e50edf",
}
SYMBOLS = ("EURJPY", "USDCHF")
START = date(2020, 9, 24)
END_EXCLUSIVE = date(2023, 9, 23)
RESERVED_CUTOFF = datetime(2023, 9, 24, 23, 45, tzinfo=UTC)
LONDON = ZoneInfo("Europe/London")
SEED = 941102
BOOTSTRAPS = 2000
MIN_TRADES_PER_CELL = 50
BARS_PATTERN = {
    period: re.compile(
        rb'\{"close":"([^"]+)","closed_at":"([^"]+)",'
        rb'"high":"([^"]+)","low":"([^"]+)","open":"([^"]+)",'
        rb'"opened_at":"([^"]+)","period":"' + period.encode() + rb'"\}'
    ) for period in ("M5", "M15")
}


@dataclass(frozen=True, slots=True)
class Bar:
    opened: datetime
    o: float
    h: float
    l: float
    c: float


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    london_date: str
    arm: str
    direction: str
    atr: float
    entry: float
    risk_distance: float
    exit_kind: str
    exit_price: float
    gross_r: float


def archive_validation(symbol: str, source: Path) -> None:
    original = build_inventory(symbol, source)
    if original["source_sha256"] != SOURCE_SHA[symbol]:
        raise ValueError("frozen 7Y source SHA256 mismatch")
    metadata = metadata_prefix(source)
    cutoff = datetime.fromisoformat(str(metadata.get("fresh_cutoff"))).astimezone(UTC)
    if cutoff != RESERVED_CUTOFF:
        raise ValueError("VT08 reserved cutoff changed")
    if not original["account_is_live"] is False:
        raise ValueError("source not verified DEMO")
    if original["environment"] != "demo":
        raise ValueError("source environment differs from DEMO")


def iter_pre_cutoff(source: Path, period: str) -> Iterator[Bar]:
    """Mmap an exact period; stop on first reserved timestamp without parsing it."""
    if period not in BARS_PATTERN:
        raise ValueError("only M5 and M15 native archive periods allowed")
    pattern = BARS_PATTERN[period]
    duration = timedelta(minutes=5 if period == "M5" else 15)
    with source.open("rb") as stream:
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as view:
            needle = ('"' + period + '":[').encode()
            at = view.find(needle)
            if at < 0:
                raise ValueError("missing native " + period)
            pos = at + len(needle)
            prev: datetime | None = None
            while view[pos:pos+1] == b"{":
                match = pattern.match(view, pos)
                if match is None:
                    raise ValueError("malformed native " + period)
                opened = datetime.fromisoformat(match.group(6).decode()).astimezone(UTC)
                if opened >= RESERVED_CUTOFF:
                    return
                closed = datetime.fromisoformat(match.group(2).decode()).astimezone(UTC)
                if closed - opened != duration:
                    raise ValueError("wrong native period duration")
                if opened.second or opened.microsecond or opened.minute % duration.seconds * 0 != 0:
                    # Minutes grid checked separately; the zero product is kept out of any parser side effects.
                    raise ValueError("misaligned sub-minute native timestamp")
                if opened.minute % (duration.seconds // 60) != 0:
                    raise ValueError("misaligned native M5/M15 grid")
                if prev is not None and opened <= prev:
                    raise ValueError("duplicated or non-monotone native bar")
                prev = opened
                c = float(match.group(1))
                h = float(match.group(3))
                l = float(match.group(4))
                o = float(match.group(5))
                if not all(isfinite(v) and v > 0 for v in (c, h, l, o)):
                    raise ValueError("nonpositive/nonfinite OHLC")
                if l > min(o, c) or h < max(o, c) or h < l:
                    raise ValueError("invalid OHLC extrema")
                yield Bar(opened=opened, o=o, h=h, l=l, c=c)
                pos = match.end()
                if view[pos:pos+1] == b",":
                    pos += 1
                elif view[pos:pos+1] == b"]":
                    return
                else:
                    raise ValueError("unexpected native JSON separator")


def london_utc(local_date: date, minute_of_day: int) -> datetime:
    if not 0 <= minute_of_day < 1440:
        raise ValueError("London minute outside day")
    local = datetime.combine(local_date, time(minute_of_day // 60, minute_of_day % 60))
    return local.replace(tzinfo=LONDON).astimezone(UTC)


def consecutive(
    bars: dict[datetime, Bar], start: datetime, count: int, minutes: int
) -> list[Bar] | None:
    delta = timedelta(minutes=minutes)
    found = [bars.get(start + i * delta) for i in range(count)]
    if any(item is None for item in found):
        return None
    return [item for item in found if item is not None]


def true_range_atr(m15: list[Bar]) -> float:
    if len(m15) != 15:
        raise ValueError("ATR needs 15 completed M15 bars")
    ranges = [
        max(b.h - b.l, abs(b.h - a.c), abs(b.l - a.c))
        for a, b in zip(m15, m15[1:])
    ]
    return mean(ranges)


def setup_direction(reference: list[Bar], event: list[Bar], atr: float) -> str | None:
    if len(reference) != 96 or len(event) != 12 or atr <= 0:
        return None
    hi = max(bar.h for bar in reference)
    lo = min(bar.l for bar in reference)
    upper = max(b.h for b in event) > hi + 0.10 * atr
    lower = min(b.l for b in event) < lo - 0.10 * atr
    if upper and lower:
        return None
    if not (lo <= event[-1].c <= hi):
        return None
    if upper:
        return "SHORT"
    if lower:
        return "LONG"
    return None


def execute_proxy(
    symbol: str, day: date, arm: str, direction: str, atr: float,
    period: list[Bar], time_exit: Bar
) -> Trade:
    if len(period) != 24 or atr <= 0:
        raise ValueError("a complete 120-minute M5 exit witness is required")
    entry = period[0].o
    risk = 1.5 * atr
    sign = 1 if direction == "LONG" else -1
    stop = entry - sign * risk
    target = entry + sign * risk
    exit_price = time_exit.o
    exit_kind = "TIME"
    gross_r = sign * (exit_price - entry) / risk
    for bar in period:
        stop_hit = bar.l <= stop if sign == 1 else bar.h >= stop
        target_hit = bar.h >= target if sign == 1 else bar.l <= target
        if stop_hit:
            exit_kind, exit_price, gross_r = "STOP_FIRST", stop, -1.0
            break
        if target_hit:
            exit_kind, exit_price, gross_r = "TARGET", target, 1.0
            break
    return Trade(symbol=symbol, london_date=day.isoformat(), arm=arm,
                 direction=direction, atr=atr, entry=entry, risk_distance=risk,
                 exit_kind=exit_kind, exit_price=exit_price, gross_r=gross_r)


def arm_decision(
    symbol: str, day: date, arm: str,
    m5: dict[datetime, Bar], m15: dict[datetime, Bar],
) -> tuple[Trade | None, str]:
    if arm not in ("LONDON", "PLACEBO"):
        raise ValueError("unregistered arm")
    start_hour = 8 if arm == "LONDON" else 6
    start = london_utc(day, start_hour * 60)
    reference_start = london_utc(day if arm == "LONDON" else day - timedelta(days=1),
                                 0 if arm == "LONDON" else 22 * 60)
    reference = consecutive(m5, reference_start, 96, 5)
    if reference is None:
        return None, "MISSING_REFERENCE"
    atr_window = consecutive(m15, start - timedelta(minutes=15 * 15), 15, 15)
    if atr_window is None:
        return None, "MISSING_ATR_M15"
    atr = true_range_atr(atr_window)
    if atr <= 0:
        return None, "INVALID_ATR"
    event = consecutive(m5, start, 12, 5)
    if event is None:
        return None, "MISSING_EVENT"
    direction = setup_direction(reference, event, atr)
    if direction is None:
        return None, "NO_UNIQUE_REENTRY"
    entry_at = start + timedelta(minutes=60)
    period = consecutive(m5, entry_at, 24, 5)
    exit_bar = m5.get(entry_at + timedelta(minutes=120))
    if period is None or exit_bar is None:
        return None, "MISSING_EXIT_WITNESS"
    return execute_proxy(symbol, day, arm, direction, atr, period, exit_bar), "TRADE"


def process_symbol(symbol: str, source: Path) -> tuple[list[Trade], dict[str, Any]]:
    archive_validation(symbol, source)
    # Both series stop on first timestamp >= RESERVED_CUTOFF, with no sealed price decode.
    m5 = {b.opened: b for b in iter_pre_cutoff(source, "M5")}
    m15 = {b.opened: b for b in iter_pre_cutoff(source, "M15")}
    trades: list[Trade] = []
    reasons: dict[str, Counter[str]] = {arm: Counter() for arm in ("LONDON", "PLACEBO")}
    cursor = START
    while cursor < END_EXCLUSIVE:
        if cursor.weekday() < 5:
            for arm in ("LONDON", "PLACEBO"):
                trade, reason = arm_decision(symbol, cursor, arm, m5, m15)
                reasons[arm][reason] += 1
                if trade is not None:
                    trades.append(trade)
        cursor += timedelta(days=1)
    return trades, {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_sha256": SOURCE_SHA[symbol],
        "source_run": SOURCE_RUN_ID,
        "source_commit": SOURCE_COMMIT,
        "native_m5_dev_bars": len(m5),
        "native_m15_dev_bars": len(m15),
        "period_start_london": START.isoformat(),
        "period_end_london_exclusive": END_EXCLUSIVE.isoformat(),
        "vt08_reserved_cutoff_utc": RESERVED_CUTOFF.isoformat(),
        "m1_m3_h4_opened": False,
        "sealed_outcomes_read": False,
        "ctrader_oauth_used": False,
        "reasons": {arm: dict(reasons[arm]) for arm in ("LONDON", "PLACEBO")},
    }


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean_r": None, "pf_gross": None, "max_dd_r": None}
    gains = sum(x for x in values if x > 0)
    losses = -sum(x for x in values if x < 0)
    equity = peak = dd = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return {
        "n": len(values), "mean_r": mean(values),
        "pf_gross": gains / losses if losses > 0 else None,
        "max_dd_r": dd,
        "cost_assumptions_mean_r": {str(x): mean(values) - x
                                   for x in (0.05, 0.10, 0.20, 0.30)},
        "pf_assumed_0_10R": (
            sum(max(x - 0.1, 0.0) for x in values)
            / -sum(min(x - 0.1, 0.0) for x in values)
            if sum(min(x - 0.1, 0.0) for x in values) < 0 else None),
    }


def _mean_equal_weight(
    records: list[Trade], arm: str,
) -> float | None:
    means = []
    for symbol in SYMBOLS:
        vals = [t.gross_r for t in records if t.symbol == symbol and t.arm == arm]
        if not vals:
            return None
        means.append(mean(vals))
    return mean(means)


def ci95(values: list[float]) -> list[float] | None:
    if len(values) < BOOTSTRAPS // 2:
        return None
    ordered = sorted(values)
    return [ordered[int((len(ordered) - 1) * p)] for p in (0.025, 0.975)]


def bootstrap_weekly(records: list[Trade]) -> dict[str, Any]:
    weeks: list[tuple[int, int]] = []
    cursor = START
    while cursor < END_EXCLUSIVE:
        iso = cursor.isocalendar()
        key = (iso.year, iso.week)
        if key not in weeks:
            weeks.append(key)
        cursor += timedelta(days=7)  # every study week has a Monday or is partial
    grouped: dict[tuple[int, int], dict[tuple[str, str], tuple[float, int]]] = defaultdict(dict)
    tmp: dict[tuple[int, int, str, str], list[float]] = defaultdict(list)
    for t in records:
        iso = date.fromisoformat(t.london_date).isocalendar()
        tmp[(iso.year, iso.week, t.symbol, t.arm)].append(t.gross_r)
    for (year, week, symbol, arm), v in tmp.items():
        grouped[(year, week)][(symbol, arm)] = (sum(v), len(v))
    rng = random.Random(SEED)
    draws_d: list[float] = []
    draws_l: list[float] = []
    for _ in range(BOOTSTRAPS):
        totals: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
        for wk in rng.choices(weeks, k=len(weeks)):
            for key, (value, count) in grouped.get(wk, {}).items():
                totals[key][0] += value
                totals[key][1] += count
        results: dict[str, float] = {}
        for arm in ("LONDON", "PLACEBO"):
            avgs: list[float] = []
            for symbol in SYMBOLS:
                total, count = totals[(symbol, arm)]
                if count == 0:
                    break
                avgs.append(total / count)
            if len(avgs) == len(SYMBOLS):
                results[arm] = mean(avgs)
        if len(results) == 2:
            draws_l.append(results["LONDON"])
            draws_d.append(results["LONDON"] - results["PLACEBO"])
    return {
        "weeks_resampled": len(weeks),
        "bootstrap_draws": BOOTSTRAPS,
        "valid_draws": len(draws_d),
        "seed": SEED,
        "ci95_difference_london_minus_placebo": ci95(draws_d),
        "ci95_mean_london": ci95(draws_l),
    }


def aggregate(records: list[Trade], manifests: list[dict[str, Any]]) -> dict[str, Any]:
    cells = {
        symbol: {arm: _summary([t.gross_r for t in records
                                if t.symbol == symbol and t.arm == arm])
                 for arm in ("LONDON", "PLACEBO")}
        for symbol in SYMBOLS
    }
    london_mean = _mean_equal_weight(records, "LONDON")
    placebo_mean = _mean_equal_weight(records, "PLACEBO")
    delta = None if london_mean is None or placebo_mean is None else london_mean - placebo_mean
    enough = all(cells[s][a]["n"] >= MIN_TRADES_PER_CELL
                 for s in SYMBOLS for a in ("LONDON", "PLACEBO"))
    inference = bootstrap_weekly(records) if enough else {
        "not_run": "frozen minimum sample requirement not met"}
    if not enough:
        verdict = "DEV_UNDERPOWERED"
    else:
        ci_d = inference["ci95_difference_london_minus_placebo"]
        ci_l = inference["ci95_mean_london"]
        passes = (ci_d is not None and ci_l is not None
                  and ci_d[0] > 0 and ci_l[0] > 0
                  and all(cells[s]["LONDON"]["mean_r"] > 0 for s in SYMBOLS))
        verdict = "DEV_GROSS_POTENTIAL" if passes else "DEV_NO_SUPPORT"
    return {
        "identity": IDENTITY,
        "prereg": PREREG,
        "research_only": True, "virgin_oos_claimed": False,
        "vt08_reserved_data_read": False, "broker_executable_pf_claimed": False,
        "no_execution_costs_available": True,
        "primary_delta_r": delta, "london_equal_weight_mean_r": london_mean,
        "placebo_equal_weight_mean_r": placebo_mean,
        "minimum_n_per_symbol_per_arm": MIN_TRADES_PER_CELL,
        "min_sample_met": enough, "verdict": verdict,
        "bootstrap": inference,
        "market_cells": cells, "source_manifests": manifests,
        "exit_counts": dict(Counter(f"{t.arm}:{t.exit_kind}" for t in records)),
        "year_counts": dict(Counter(f"{t.london_date[:4]}:{t.symbol}:{t.arm}"
                                     for t in records)),
        "trades_total": len(records),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("eurjpy", type=Path)
    parser.add_argument("usdchf", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    trades: list[Trade] = []
    manifests: list[dict[str, Any]] = []
    for symbol, root in zip(SYMBOLS, (args.eurjpy, args.usdchf)):
        records, manifest = process_symbol(symbol, root / "raw-7y-base.json")
        trades.extend(records)
        manifests.append(manifest)
    trades.sort(key=lambda t: (t.london_date, t.symbol, t.arm))
    report = aggregate(trades, manifests)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "g1-london-reentry-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n")
    # Keep full signal counts and economic losses: no cherry-picking and no rewrites.
    with (args.out / "g1-london-reentry-trades.jsonl").open("w") as f:
        for record in trades:
            f.write(json.dumps(asdict(record), sort_keys=True) + "\n")
    for filename in ("g1-london-reentry-report.json", "g1-london-reentry-trades.jsonl"):
        p = args.out / filename
        (args.out / (filename + ".sha256")).write_text(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + filename + "\n")
    print(json.dumps({
        "verdict": report["verdict"], "signals": report["trades_total"],
        "primary_delta_r": report["primary_delta_r"],
        "london_mean_r": report["london_equal_weight_mean_r"],
        "samples_sufficient": report["min_sample_met"],
        "no_live": True}, sort_keys=True))


if __name__ == "__main__":
    main()
