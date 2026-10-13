#!/usr/bin/env python3
"""VT31 Gate1: JOINT COG+OPS selected FVG vs earliest RAW M1 FVG in same hour.

Already-explored development. Timing/side may differ; NOT a COG-only ablation,
NOT order PnL/CE fill, NOT proof of causal predictive lift.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any
from zoneinfo import ZoneInfo

from scripts.vt31_edge_directional_15m_preregistered_3y_v1 import (
    _digest,
    _market_source,
    prepare,
    stamp,
)

NY = ZoneInfo("America/New_York")
SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
PREREG = "c7822542fd6d2d734cc511db25466d4d6bb604c4"
EXPECTED = {"VT31_LONDON": 774, "VT31_NY_AM": 771, "VT31_NY_PM": 741}
HOURS = {3: "VT31_LONDON", 10: "VT31_NY_AM", 14: "VT31_NY_PM"}
HORIZON = 15
BOOT = 2000
SEED = 13102026


def key_for(t: datetime) -> tuple[str, str] | None:
    local = t.astimezone(NY)
    session = HOURS.get(local.hour)
    if session is None:
        return None
    return local.date().isoformat(), session


def raw_first_for_complete_hour(
    bars: list[dict[str, Any]], key: tuple[str, str],
) -> dict[str, Any] | None:
    if len(bars) != 60:
        raise ValueError("raw-first requires fully observed source hour")
    starts = [stamp(b["opened_at"]) for b in bars]
    if any(
        starts[i] != starts[0] + timedelta(minutes=i)
        for i in range(60)
    ):
        raise ValueError("raw first not contiguous M1")
    for j in range(2, 59):
        first, third = bars[j-2], bars[j]
        bullish = float(third["low"]) > float(first["high"])
        bearish = float(third["high"]) < float(first["low"])
        if not (bullish or bearish):
            continue
        formed = stamp(third["closed_at"])
        return {
            "day": key[0],
            "session": key[1],
            "formed": formed,
            "side_sign": 1 if bullish else -1,
            "week": f"{formed.astimezone(NY).isocalendar().year}-W"
                    f"{formed.astimezone(NY).isocalendar().week:02d}",
        }
    return None


def census_raw(path: Path) -> tuple[
    dict[tuple[str, str], dict[str, Any]], set[tuple[str, str]], int
]:
    events = {}
    complete = set()
    counts: Counter[str] = Counter()
    last_open = None
    active = None
    buffered: list[dict[str, Any]] = []
    total = 0

    def flush() -> None:
        nonlocal buffered, active
        if active is None:
            return
        local_hour = {v: k for k, v in HOURS.items()}[active[1]]
        if len(buffered) == 60:
            first = stamp(buffered[0]["opened_at"]).astimezone(NY)
            correct = (
                first.hour == local_hour and first.minute == 0
                and all(
                    stamp(b["opened_at"]) ==
                    stamp(buffered[0]["opened_at"]) + timedelta(minutes=i)
                    for i, b in enumerate(buffered)
                )
            )
            if correct:
                complete.add(active)
                counts[active[1]] += 1
                event = raw_first_for_complete_hour(buffered, active)
                if event is not None:
                    events[active] = event
        active, buffered = None, []

    for item in _market_source(path):
        now = stamp(item["opened_at"])
        if last_open is not None and now <= last_open:
            raise ValueError("nonchronological frozen market")
        if stamp(item["closed_at"]) - now != timedelta(minutes=1):
            raise ValueError("non-M1 market")
        last_open = now
        total += 1
        key = key_for(now)
        if key != active:
            flush()
        if key is not None:
            active = key
            buffered.append(item)
    flush()
    if total != 1059784 or dict(counts) != EXPECTED:
        raise ValueError("frozen 3Y raw M1 or complete hour composition drift")
    if len(complete) != 2286:
        raise ValueError("unexpected complete ICT windows")
    return events, complete, total


def gross(
    event: dict[str, Any], opens: dict[datetime, float],
) -> float | None:
    t = event["formed"]
    if any(t + timedelta(minutes=i) not in opens for i in range(16)):
        return None
    return (opens[t + timedelta(minutes=HORIZON)] - opens[t]) * event["side_sign"]


def get_opens(path: Path, required: set[datetime]) -> dict[datetime, float]:
    out = {}
    n = 0
    for row in _market_source(path):
        n += 1
        at = stamp(row["opened_at"])
        if at in required:
            x = float(row["open"])
            if not 1000 < x < 1000000:
                raise ValueError("bad price open")
            out[at] = x
    if n != 1059784:
        raise ValueError("frozen M1 count drift in second read")
    return out


def quantile(values: list[float], fraction: float) -> float:
    xs = sorted(values)
    i = (len(xs)-1) * fraction
    n = int(i)
    return xs[n] + (xs[min(n+1, len(xs)-1)]-xs[n])*(i-n)


def blocks(
    observations: list[tuple[str, float]],
) -> dict[str, Any]:
    if not observations:
        return {"n": 0, "mean": None, "week_boot_ci95": None}
    by_week: dict[str, list[float]] = defaultdict(list)
    for week, value in observations:
        by_week[week].append(value)
    clusters = [(sum(v), len(v)) for v in by_week.values()]
    rng = random.Random(SEED)
    bootstrap = []
    for _ in range(BOOT):
        picked = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        bootstrap.append(
            sum(val for val, _ in picked) / sum(num for _, num in picked)
        )
    return {
        "n": len(observations),
        "mean": round(mean([v for _, v in observations]), 6),
        "weeks": len(clusters),
        "week_boot_ci95": [
            round(quantile(bootstrap, .025), 6),
            round(quantile(bootstrap, .975), 6),
        ],
        "already_used_development_NOT_confirmation": True,
    }


def adjudicate(
    ledger: dict[str, Any],
    raw: dict[tuple[str, str], dict[str, Any]],
    complete: set[tuple[str, str]],
    opens: dict[datetime, float],
) -> dict[str, Any]:
    selected, _ = prepare(ledger)
    sel: dict[tuple[str, str], dict[str, Any]] = {}
    for ev in selected:
        key = (ev["formed"].astimezone(NY).date().isoformat(), ev["session"])
        if key in sel or key not in complete:
            raise ValueError("duplicate approved window or absent source")
        ev = dict(ev)
        ev["week"] = ev["ny_iso_week"]
        sel[key] = ev
        if key not in raw:
            raise ValueError("approved source cannot lack raw FVG")
    raw_stats = []
    raw_yes = []
    raw_no = []
    app_stats = []
    paired = []
    same_side = 0
    same_timestamp = 0
    lags = []
    by_session: dict[str, list[tuple[str, float]]] = defaultdict(list)
    per_year: dict[str, list[tuple[str, float]]] = defaultdict(list)
    missing = Counter()
    for key in sorted(complete):
        r = raw.get(key)
        ev = sel.get(key)
        if r is not None:
            g = gross(r, opens)
            if g is not None:
                raw_stats.append((r["week"], g))
                (raw_yes if ev is not None else raw_no).append((r["week"], g))
            else:
                missing["raw"] += 1
        if ev is not None:
            approved = gross(ev, opens)
            if approved is None:
                missing["selected"] += 1
            else:
                app_stats.append((ev["week"], approved))
            if r is None:
                raise ValueError("matched raw absent")
            control = gross(r, opens)
            if control is not None and approved is not None:
                delta = approved - control
                paired.append((ev["week"], delta))
                by_session[ev["session"]].append((ev["week"], delta))
                per_year[str(ev["formed"].astimezone(NY).year)].append(
                    (ev["week"], delta)
                )
                same_side += int(ev["side_sign"] == r["side_sign"])
                same_timestamp += int(ev["formed"] == r["formed"])
                lags.append((ev["formed"] - r["formed"]).total_seconds()/60)
    if not paired or len(app_stats) != len(selected):
        raise ValueError("missing matched sample or forward coverage")
    if len(sel) != 2140:
        raise ValueError("approved denominator changed")
    delta_stats = blocks(paired)
    return {
        "schema": "qore.vt31.Gate1.raw_first_vs_COG_OPS_selected.v1",
        "market_M1_SHA256": SHA,
        "pre_registration_commit": PREREG,
        "complete_ict_windows": len(complete),
        "first_raw_FVG_windows": len(raw),
        "no_raw_first_fvg_windows": len(complete)-len(raw),
        "COG_plus_OPS_selected_windows": len(sel),
        "nonselected_complete_windows": len(complete)-len(sel),
        "missing_forward_15m": dict(missing),
        "raw_first_all": blocks(raw_stats),
        "raw_first_when_later_COG_OPS_selected_POSTHOC": blocks(raw_yes),
        "raw_first_when_no_COG_OPS_selection_POSTHOC": blocks(raw_no),
        "COG_OPS_original_approved_15m": blocks(app_stats),
        "paired_approved_minus_first_raw_first_window": delta_stats,
        "paired_by_session": {k: blocks(v) for k, v in sorted(by_session.items())},
        "paired_by_year": {k: blocks(v) for k, v in sorted(per_year.items())},
        "same_direction_n": same_side,
        "exactly_same_formation_timestamp_n": same_timestamp,
        "different_formation_timestamp_n": len(paired)-same_timestamp,
        "time_lag_approved_minus_raw_minutes": {
            "min": min(lags), "max": max(lags),
            "median": median(lags), "mean": round(mean(lags), 4),
        },
        "NO_COG_ONLY_ABLATION": True,
        "COMBINED_COG_OPS_selection_NOT_only_cognition": True,
        "different_clock_and_direction_are_confounders": True,
        "raw_FVG_first_is_causal_matched_hour_not_matched_second": True,
        "15m_gross_not_executable_PnL": True,
        "broker_fills_bid_ask_oms": 0,
        "economic_profit_factor_drawdown": None,
        "fresh_holdout_opened": False,
        "LIVE_or_VPS_authority": False,
        "decision": (
            "EXPLORATORY_JOINT_SELECTION_DIFFERENCE_POSITIVE_NOT_EDGE"
            if delta_stats["mean"] > 0 and delta_stats["week_boot_ci95"][0] > 0
            else "NO_SUPPORT_FOR_POSITIVE_JOINT_SELECTION_LIFT"
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if _digest(args.market) != SHA:
        raise ValueError("M1 historical source SHA256 failed")
    raw, complete, _ = census_raw(args.market)
    ledger = json.loads(args.ledger.read_text(encoding="utf8"))
    approved, _ = prepare(ledger)
    needed = set()
    for item in (*raw.values(), *approved):
        for m in range(HORIZON+1):
            needed.add(item["formed"] + timedelta(minutes=m))
    opens = get_opens(args.market, needed)
    report = adjudicate(ledger, raw, complete, opens)
    report["approved_ledger_SHA256"] = _digest(args.ledger)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
