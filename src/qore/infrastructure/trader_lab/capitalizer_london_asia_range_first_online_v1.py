"""Issue775 London Asia-range sweep/reclaim versus break/hold.

Independent provider-native M1 event study. NO V49, DCVC, TTrades, production,
future-derived signal selection, synthetic candles, or certified brokerage PnL.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    DEV_WINDOW_END,
    DEV_WINDOW_START,
)

ID = "QORE_ISSUE775_LONDON_ASIA_FIRST_ONLINE_V1"
LONDON = ZoneInfo("Europe/London")
SYMBOLS = ("EURUSD", "GBPUSD")
PATTERNS = ("L1_SWEEP_RECLAIM", "L2_BREAK_HOLD")
COSTS = (Decimal("0"), Decimal("0.025"), Decimal("0.05"))
SIMULATIONS = 2000
SEED = 77520261011


@dataclass(frozen=True, slots=True)
class Event:
    symbol: str
    london_day: str
    asia_observed_m1: int
    asia_coverage: str
    asia_high: str | None
    asia_low: str | None
    first_breach_at: str | None
    breach_side: str | None
    reason: str
    pattern: str | None
    confirmed_at: str | None
    entry_at: str | None
    direction: str | None
    entry: str | None
    stop: str | None
    target: str | None
    risk: str | None
    exit_at: str | None
    exit_reason: str | None
    gross_r: str | None
    opposite_gross_r: str | None
    dual_touch_stop_first: bool
    future_used_to_select_event: bool = False


def london_start(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=LONDON).astimezone(UTC)


def asof_event(
    symbol: str, day: date, bars: tuple[CapitalizerM1Bar, ...],
) -> Event:
    """Scan only finished bars for triggers; returns outcome separately in replay."""
    if symbol not in SYMBOLS:
        raise ValueError("unexpected symbol")
    by_open = {bar.opened_at: bar for bar in bars}
    if len(by_open) != len(bars):
        raise ValueError("duplicate native M1")
    a0, l8 = london_start(day, 0), london_start(day, 8)
    a = [by_open.get(a0 + timedelta(minutes=i)) for i in range(480)]
    n = sum(x is not None for x in a)
    strict = n == 480
    coverage = "ASIA_COMPLETE" if strict else (
        "ASIA_95_INFORMATIONAL" if n >= 456 else "ASIA_INCOMPLETE"
    )
    hi = max(b.high for b in a if b is not None) if n else None
    lo = min(b.low for b in a if b is not None) if n else None

    def result(
        reason: str,
        *, first: datetime | None = None,
        side: str | None = None,
        pattern: str | None = None,
        confirmed: datetime | None = None,
        entry_bar: CapitalizerM1Bar | None = None,
        direction: str | None = None,
        stop: Decimal | None = None,
    ) -> Event:
        entry_price = entry_bar.open if entry_bar is not None else None
        risk = (
            abs(entry_price - stop)
            if entry_price is not None and stop is not None
            else None
        )
        target = None
        if risk is not None and direction is not None:
            target = (
                entry_price + risk if direction == "LONG" else entry_price - risk
            )
        return Event(
            symbol=symbol, london_day=day.isoformat(),
            asia_observed_m1=n, asia_coverage=coverage,
            asia_high=str(hi) if hi is not None else None,
            asia_low=str(lo) if lo is not None else None,
            first_breach_at=first.isoformat() if first else None,
            breach_side=side, reason=reason, pattern=pattern,
            confirmed_at=confirmed.isoformat() if confirmed else None,
            entry_at=entry_bar.opened_at.isoformat() if entry_bar else None,
            direction=direction, entry=str(entry_price) if entry_price is not None else None,
            stop=str(stop) if stop is not None else None,
            target=str(target) if target is not None else None,
            risk=str(risk) if risk is not None else None,
            exit_at=None, exit_reason=None, gross_r=None,
            opposite_gross_r=None, dual_touch_stop_first=False,
        )

    if not strict or hi is None or lo is None:
        return result("ASIA_COVERAGE_INVALID")
    if hi <= lo:
        return result("ASIA_RANGE_ZERO")

    first: datetime | None = None
    side: str | None = None
    for i in range(180):
        at = l8 + timedelta(minutes=i)
        bar = by_open.get(at)
        if bar is None:
            return result("LONDON_PRE_BREACH_GAP")
        touched_high = bar.high > hi
        touched_low = bar.low < lo
        if touched_high and touched_low:
            return result("AMBIGUOUS_BOTH_EXTREMES", first=at)
        if touched_high or touched_low:
            first, side = at, ("HIGH" if touched_high else "LOW")
            break
    if first is None or side is None:
        return result("NO_FIRST_BREACH")

    extreme: Decimal | None = None
    last_outside = False
    for j in range(5):
        at = first + timedelta(minutes=j)
        b = by_open.get(at)
        if b is None:
            return result("FOLLOWUP_GAP", first=first, side=side)
        if (side == "HIGH" and b.low < lo) or (side == "LOW" and b.high > hi):
            return result("OPPOSITE_EXTREME_DURING_CONFIRMATION", first=first, side=side)
        extreme = (
            max(extreme, b.high) if extreme is not None and side == "HIGH"
            else min(extreme, b.low) if extreme is not None
            else (b.high if side == "HIGH" else b.low)
        )
        inside = lo <= b.close <= hi
        outside = b.close > hi if side == "HIGH" else b.close < lo
        pattern: str | None = None
        direction: str | None = None
        stop: Decimal | None = None
        if inside:
            pattern = PATTERNS[0]
            direction = "SHORT" if side == "HIGH" else "LONG"
            stop = extreme
        elif outside and last_outside:
            pattern = PATTERNS[1]
            direction = "LONG" if side == "HIGH" else "SHORT"
            stop = hi if side == "HIGH" else lo
        last_outside = outside
        if pattern is None or direction is None or stop is None:
            continue
        nxt = by_open.get(b.closed_at)
        if nxt is None or nxt.opened_at.astimezone(LONDON).hour >= 11:
            return result("ENTRY_GAP_OR_LATE", first=first, side=side,
                          pattern=pattern, confirmed=b.closed_at)
        entry = nxt.open
        valid = (
            (direction == "LONG" and stop < entry)
            or (direction == "SHORT" and stop > entry)
        )
        if not valid:
            return result("INVALID_RISK", first=first, side=side,
                          pattern=pattern, confirmed=b.closed_at,
                          entry_bar=nxt, direction=direction, stop=stop)
        return result("SIGNAL_CONFIRMED", first=first, side=side,
                      pattern=pattern, confirmed=b.closed_at,
                      entry_bar=nxt, direction=direction, stop=stop)
    return result("UNCONFIRMED_BREACH", first=first, side=side)


def exit_path(
    bars: dict[datetime, CapitalizerM1Bar],
    at: datetime, stop: Decimal, target: Decimal,
    direction: str, day: date,
) -> tuple[datetime | None, str, Decimal | None, bool]:
    """Conservative barrier adjudication + same-day 16:00 London exit."""
    close_at = london_start(day, 16)
    entry = bars.get(at)
    if entry is None:
        return None, "RIGHT_CENSORED_ENTRY", None, False
    price = entry.open
    risk = abs(price - stop)
    if risk <= 0:
        return None, "INVALID_RISK", None, False
    clock = at
    while clock < close_at:
        b = bars.get(clock)
        if b is None:
            return clock, "RIGHT_CENSORED_GAP", None, False
        stop_hit = b.low <= stop if direction == "LONG" else b.high >= stop
        target_hit = b.high >= target if direction == "LONG" else b.low <= target
        if stop_hit:
            return b.closed_at, "STOP_FIRST", Decimal(-1), target_hit
        if target_hit:
            return b.closed_at, "TARGET", Decimal(1), False
        if b.closed_at == close_at:
            pnl = (
                b.close - price if direction == "LONG" else price - b.close
            ) / risk
            return close_at, "TIME_CAP_16_LONDON", pnl, False
        clock = b.closed_at
    return clock, "RIGHT_CENSORED_FEED_END", None, False


def analyse_market(root: Path, output: Path) -> dict[str, Any]:
    by_day: dict[date, list[CapitalizerM1Bar]] = defaultdict(list)
    observed: str | None = None
    count = 0
    for b in iter_cibo_m1(root):
        if not (DEV_WINDOW_START <= b.opened_at < DEV_WINDOW_END):
            continue
        if b.symbol not in SYMBOLS:
            raise ValueError("only EURUSD / GBPUSD")
        if observed is not None and b.symbol != observed:
            raise ValueError("multiple symbols in native artifact")
        observed = b.symbol
        ld = b.opened_at.astimezone(LONDON).date()
        if ld.weekday() < 5:
            by_day[ld].append(b)
        count += 1
    if observed is None or not by_day:
        raise ValueError("no research-window native M1")
    events: list[Event] = []
    for day, day_bars in sorted(by_day.items()):
        rows = tuple(day_bars)
        rec = asof_event(observed, day, rows)
        if rec.reason == "SIGNAL_CONFIRMED":
            assert rec.entry_at is not None and rec.stop is not None
            assert rec.risk is not None and rec.direction is not None
            entry_at = datetime.fromisoformat(rec.entry_at)
            price = Decimal(rec.entry)
            risk = Decimal(rec.risk)
            stop = Decimal(rec.stop)
            target = Decimal(rec.target)
            calendar = {b.opened_at: b for b in rows}
            exit_at, reason, gross, ambig = exit_path(
                calendar, entry_at, stop, target, rec.direction, day
            )
            reverse_side = "SHORT" if rec.direction == "LONG" else "LONG"
            reverse_stop = (
                price + risk if reverse_side == "SHORT" else price - risk
            )
            reverse_target = (
                price - risk if reverse_side == "SHORT" else price + risk
            )
            alt_at, alt_reason, alt_r, _ = exit_path(
                calendar, entry_at, reverse_stop, reverse_target, reverse_side, day
            )
            if (exit_at is None) != (alt_at is None):
                raise ValueError("mirror has inconsistent censoring")
            if (gross is None) != (alt_r is None):
                raise ValueError("mirror has inconsistent outcome resolution")
            z = asdict(rec)
            z.update(
                exit_at=exit_at.isoformat() if exit_at else None,
                exit_reason=reason,
                gross_r=str(gross) if gross is not None else None,
                opposite_gross_r=str(alt_r) if alt_r is not None else None,
                dual_touch_stop_first=ambig,
            )
            events.append(Event(**z))
        else:
            events.append(rec)
    output.mkdir(parents=True, exist_ok=True)
    (output / f"issue775-london-{observed}-daily-events.jsonl").write_text(
        "".join(json.dumps(asdict(x), sort_keys=True) + "\n" for x in events),
        encoding="utf-8",
    )
    cnt = Counter(x.reason for x in events)
    result = {
        "identity": ID, "symbol": observed, "native_m1": count,
        "london_days_with_any_M1": len(events), "reason_counts": dict(cnt),
        "eligible_complete_asia_days": sum(x.asia_coverage == "ASIA_COMPLETE" for x in events),
        "asia_95_informational_days": sum(x.asia_coverage == "ASIA_95_INFORMATIONAL" for x in events),
        "signals_by_pattern": dict(Counter(
            x.pattern for x in events if x.reason == "SIGNAL_CONFIRMED"
        )),
        "outcomes_used_to_select": False,
        "legacy_V49_used": False,
        "not_certified": True,
    }
    (output / f"issue775-london-{observed}-report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def percentile(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    i = (len(s) - 1) * p
    low = int(i)
    return s[low] * (1 - (i - low)) + s[min(low + 1, len(s) - 1)] * (i - low)


def metrics(rows: list[Event], cost: Decimal) -> dict[str, Any]:
    v = [Decimal(x.gross_r) - cost for x in rows if x.gross_r is not None]
    if not v:
        return {"N": len(rows), "resolved": 0,
                "censored": len(rows), "PF": None, "E_R": None,
                "WR": None, "sum_R": None}
    plus = sum((x for x in v if x > 0), Decimal(0))
    minus = -sum((x for x in v if x < 0), Decimal(0))
    return {
        "N": len(rows), "resolved": len(v), "censored": len(rows) - len(v),
        "PF": str(plus / minus) if minus else None,
        "E_R": str(sum(v, Decimal(0)) / len(v)),
        "WR": str(Decimal(sum(x > 0 for x in v)) / len(v)),
        "sum_R": str(sum(v, Decimal(0))),
    }


def permutation_sign_p(
    rows: list[Event], sims: int = SIMULATIONS, seed: int = SEED,
) -> float | None:
    events = [x for x in rows if x.gross_r is not None]
    if not events:
        return None
    days: dict[str, list[Event]] = defaultdict(list)
    for x in events:
        days[x.london_day].append(x)
    dates = sorted(days)
    observed = sum(float(Decimal(x.gross_r) - COSTS[1]) for x in events) / len(events)
    rng = random.Random(seed)
    exceed = 0
    for _ in range(sims):
        simulated: list[float] = []
        for day in dates:
            flip = rng.choice((False, True))
            for x in days[day]:
                d = x.opposite_gross_r if flip else x.gross_r
                assert d is not None
                simulated.append(float(Decimal(d) - COSTS[1]))
        if sum(simulated) / len(simulated) >= observed:
            exceed += 1
    return (1 + exceed) / (sims + 1)


def bootstrap_ci(rows: list[Event], sims: int = SIMULATIONS) -> list[float] | None:
    events = [x for x in rows if x.gross_r is not None]
    if len(events) < 2:
        return None
    days: dict[str, list[float]] = defaultdict(list)
    for event in events:
        days[event.london_day].append(float(Decimal(event.gross_r) - COSTS[1]))
    keys = sorted(days)
    rng = random.Random(SEED)
    avgs: list[float] = []
    for _ in range(sims):
        sample = [r for _ in keys for r in days[rng.choice(keys)]]
        avgs.append(sum(sample) / len(sample))
    return [percentile(avgs, .025), percentile(avgs, .975)]


def bh_fdr(pvalues: dict[str, float | None]) -> dict[str, float | None]:
    ok = sorted(((v, k) for k, v in pvalues.items() if v is not None))
    k = len(ok)
    qvals: dict[str, float | None] = {key: None for key in pvalues}
    smallest = 1.0
    for rank in range(k, 0, -1):
        v, name = ok[rank - 1]
        smallest = min(smallest, v * k / rank)
        qvals[name] = smallest
    return qvals


def combine(root: Path, output: Path) -> dict[str, Any]:
    files = sorted(root.rglob("issue775-london-*-daily-events.jsonl"))
    if len(files) != 2:
        raise ValueError("exactly two London pair event files")
    all_events: list[Event] = []
    for p in files:
        all_events.extend(
            Event(**json.loads(line))
            for line in p.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    if {x.symbol for x in all_events} != set(SYMBOLS):
        raise ValueError("exact EURUSD GBPUSD coverage required")
    pairs = [(symbol, pattern) for symbol in SYMBOLS for pattern in PATTERNS]
    reports: dict[str, Any] = {}
    p: dict[str, float | None] = {}
    for sym, pat in pairs:
        key = f"{sym}:{pat}"
        trade_rows = [x for x in all_events
                      if x.symbol == sym and x.pattern == pat and x.entry_at is not None]
        reports[key] = {
            "gross": metrics(trade_rows, COSTS[0]),
            "cost_0p025R_hypothetical": metrics(trade_rows, COSTS[1]),
            "cost_0p05R_hypothetical": metrics(trade_rows, COSTS[2]),
            "bootstrap_date_ci95_E_R_at_0p025": bootstrap_ci(trade_rows),
            "dual_touch_n": sum(x.dual_touch_stop_first for x in trade_rows),
            "median_stop_distance": (
                str(sorted(Decimal(x.risk) for x in trade_rows)[len(trade_rows)//2])
                if trade_rows else None
            ),
        }
        p[key] = permutation_sign_p(trade_rows)
        reports[key]["exploratory_random_sign_p_one_sided"] = p[key]
    q = bh_fdr(p)
    for k in reports:
        reports[k]["BH_London_q"] = q[k]
        reports[k]["FDR_q_le_0p10"] = bool(q[k] is not None and q[k] <= .10)
    days = {
        sym: {
            "total": sum(x.symbol == sym for x in all_events),
            "complete": sum(
                x.symbol == sym and x.asia_coverage == "ASIA_COMPLETE"
                for x in all_events
            ),
            "reason_counts": dict(Counter(
                x.reason for x in all_events if x.symbol == sym
            )),
        }
        for sym in SYMBOLS
    }
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "identity": ID, "research_window_start": DEV_WINDOW_START.isoformat(),
        "research_window_end": DEV_WINDOW_END.isoformat(),
        "sessions": ["LONDON"], "symbols": list(SYMBOLS),
        "pairs_pattern_cells": reports,
        "days_by_symbol": days,
        "fdr_method": "BH among 4 fixed London pair-pattern hypotheses q=0.10",
        "calendar_dst": "Europe/London (IANA)",
        "true_broker_bid_ask": False, "fees_are_hypothetical_R": True,
        "historical_dataset_already_consumed": True,
        "outcome_based_event_selection": False,
        "trader_certified": False, "production_changed": False,
    }
    (output / "issue775-london-two-pairs-first-online-results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("market")
    m.add_argument("native", type=Path)
    m.add_argument("output", type=Path)
    a = sub.add_parser("aggregate")
    a.add_argument("market_root", type=Path)
    a.add_argument("output", type=Path)
    x = p.parse_args()
    if x.mode == "market":
        print("ISSUE775_LONDON_MARKET", json.dumps(analyse_market(x.native, x.output), sort_keys=True))
    else:
        z = combine(x.market_root, x.output)
        print("ISSUE775_LONDON_RESULT", json.dumps(z, sort_keys=True))


if __name__ == "__main__":
    main()
