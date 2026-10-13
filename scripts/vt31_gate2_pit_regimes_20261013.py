#!/usr/bin/env python3
"""VT31 Gate2 pre-window point-in-time regime screen (four frozen classes).

This tests JOINT COG+OPS selection against first raw FVG, NOT COG-only or PnL.
Development data previously explored; no holdout, quotes, trades or orders.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any

from scripts.vt31_edge_directional_15m_preregistered_3y_v1 import (
    _digest,
    _market_source,
    prepare,
    stamp,
)
from scripts.vt31_gate1_cogops_vs_raw_first_fvg_20261013 import (
    HOURS,
    NY,
    adjudicate,
    census_raw,
    get_opens,
    gross,
)

SOURCE_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
LEDGER_SHA = "e9683d87f0645b488968aeb3e207347649f4e9aea5c535202ab4f024c22e7646"
PREREG = "78cfa3c55487df620c450e0b12c6c26537dc683b"
CELLS = (
    "HIGH_VOL_TREND", "HIGH_VOL_CHOP",
    "LOW_VOL_TREND", "LOW_VOL_CHOP",
)
HIST = 20
TREND_MIN = .35
BOOT = 2000
SEED = 13102026
MIN_PAIRS = 100
MIN_WEEKS = 20


def classify_at_start(
    window_start: datetime,
    previous: list[tuple[datetime, float]],
    prev_vols: list[float],
) -> tuple[str, float | None, float | None]:
    """Use only prior closed M1. prev_vols NEVER includes the current hour."""
    if len(previous) != 60 or any(
        t != window_start - timedelta(minutes=60-i)
        for i, (t, _) in enumerate(previous)
    ):
        return "UNKNOWN_PREWINDOW", None, None
    realized = sum(
        abs(previous[i][1] - previous[i-1][1])
        for i in range(1, 60)
    )
    if realized <= 0:
        return "UNKNOWN_FLAT", realized, None
    eff = abs(previous[-1][1] - previous[0][1]) / realized
    if len(prev_vols) < HIST:
        return "UNKNOWN_WARMUP", realized, eff
    vol_tag = "HIGH_VOL" if realized > median(prev_vols[-HIST:]) else "LOW_VOL"
    trend_tag = "TREND" if eff >= TREND_MIN else "CHOP"
    return f"{vol_tag}_{trend_tag}", realized, eff


def classify_all_source_starts(
    market: Path,
) -> dict[tuple[str, str], str]:
    """Single streaming pass: compute every possible source start at exact NY 00."""
    previous: deque[tuple[datetime, float]] = deque(maxlen=60)
    reference: dict[str, deque[float]] = {
        session: deque(maxlen=HIST) for session in HOURS.values()
    }
    labels: dict[tuple[str, str], str] = {}
    last = None
    n = 0
    for row in _market_source(market):
        t = stamp(row["opened_at"])
        if last is not None and t <= last:
            raise ValueError("source M1 out of order")
        if stamp(row["closed_at"]) - t != timedelta(minutes=1):
            raise ValueError("invalid M1 duration")
        last = t
        local = t.astimezone(NY)
        if local.hour in HOURS and local.minute == 0:
            session = HOURS[local.hour]
            key = (local.date().isoformat(), session)
            if key in labels:
                raise ValueError("duplicate NY regime window")
            label, realized, _ = classify_at_start(
                t, list(previous), list(reference[session]),
            )
            labels[key] = label
            # Update history only AFTER labeling as-of t. Even on warmup,
            # a valid 60-M1 pre-window is a historical reference for later days.
            if realized is not None:
                reference[session].append(realized)
        value = float(row["close"])
        if not 1000 < value < 1000000:
            raise ValueError("invalid NAS100 close")
        previous.append((t, value))
        n += 1
    if n != 1059784:
        raise ValueError("original source M1 count changed")
    return labels


def quantile(vals: list[float], q: float) -> float:
    a = sorted(vals)
    j = (len(a)-1)*q
    i = int(j)
    return a[i] + (a[min(i+1,len(a)-1)] - a[i])*(j-i)


def summarize(rows: list[tuple[str, float]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "mean": None, "weeks": 0,
                "week_CI95": None, "week_CI98p75_bonferroni": None}
    week: dict[str, list[float]] = defaultdict(list)
    for label, value in rows:
        week[label].append(value)
    clusters = [(sum(v), len(v)) for v in week.values()]
    rnd = random.Random(SEED)
    boot = []
    for _ in range(BOOT):
        picked = [clusters[rnd.randrange(len(clusters))] for _ in clusters]
        boot.append(sum(s for s, _ in picked) / sum(n for _, n in picked))
    return {
        "n": len(rows),
        "mean": round(mean(v for _, v in rows), 6),
        "weeks": len(clusters),
        "week_CI95": [round(quantile(boot, .025), 6),
                      round(quantile(boot, .975), 6)],
        "week_CI98p75_bonferroni": [
            round(quantile(boot, .00625), 6),
            round(quantile(boot, .99375), 6),
        ],
    }


def review(
    raw: dict[tuple[str, str], dict[str, Any]],
    complete: set[tuple[str, str]],
    ledger: dict[str, Any],
    opens: dict[datetime, float],
    labels: dict[tuple[str, str], str],
) -> dict[str, Any]:
    chosen, _ = prepare(ledger)
    approved = {}
    for event in chosen:
        key = (event["formed"].astimezone(NY).date().isoformat(),
               event["session"])
        if key in approved or key not in complete:
            raise ValueError("invalid selected window")
        approved[key] = event
    counts: Counter[str] = Counter()
    pair: dict[str, list[tuple[str, float]]] = defaultdict(list)
    selected: dict[str, list[tuple[str, float]]] = defaultdict(list)
    raw_rows: dict[str, list[tuple[str, float]]] = defaultdict(list)
    by_session: dict[str, Counter[str]] = defaultdict(Counter)
    dir_agreement: Counter[str] = Counter()
    lag: dict[str, list[float]] = defaultdict(list)
    missing: Counter[str] = Counter()
    for key in sorted(complete):
        label = labels.get(key, "UNKNOWN_NO_SOURCE_START")
        counts[label] += 1
        by_session[key[1]][label] += 1
        if label not in CELLS:
            continue
        r = raw.get(key)
        a = approved.get(key)
        if r is None:
            missing["raw_missing_"+label] += 1
            continue
        raw_pnl = gross(r, opens)
        if raw_pnl is None:
            missing["raw_M1_missing_"+label] += 1
        else:
            raw_rows[label].append((r["week"], raw_pnl))
        if a is None:
            continue
        select_pnl = gross(a, opens)
        if select_pnl is None:
            missing["selected_M1_missing_"+label] += 1
        else:
            selected[label].append((a["ny_iso_week"], select_pnl))
        if select_pnl is None or raw_pnl is None:
            continue
        pair[label].append((a["ny_iso_week"], select_pnl - raw_pnl))
        dir_agreement[label] += int(a["side_sign"] == r["side_sign"])
        lag[label].append((a["formed"]-r["formed"]).total_seconds()/60)

    results = {}
    for name in CELLS:
        d = summarize(pair[name])
        s = summarize(selected[name])
        r = summarize(raw_rows[name])
        underpowered = d["n"] < MIN_PAIRS or d["weeks"] < MIN_WEEKS
        lifted = (
            not underpowered and d["mean"] > 0
            and s["mean"] is not None and s["mean"] > 0
            and d["week_CI98p75_bonferroni"][0] > 0
        )
        results[name] = {
            "source_complete_windows": counts[name],
            "raw_first": r, "COG_OPS_selected": s,
            "paired_selection_minus_first_raw": d,
            "pair_direction_same_n": dir_agreement[name],
            "timing_lag_selected_minus_raw_median_min": (
                round(median(lag[name]), 3) if lag[name] else None
            ),
            "timing_lag_selected_minus_raw_mean_min": (
                round(mean(lag[name]), 3) if lag[name] else None
            ),
            "gate": (
                "UNDERPOWERED" if underpowered else
                "EXPLORATORY_POSITIVE_NOT_ECONOMIC_EDGE" if lifted else
                "NO_SUPPORT"
            ),
        }
    if sum(counts.values()) != len(complete):
        raise ValueError("regime partition source windows incorrect")
    baseline = adjudicate(ledger, raw, complete, opens)
    if (
        baseline["paired_approved_minus_first_raw_first_window"]["n"] != 2140
        or abs(baseline["paired_approved_minus_first_raw_first_window"]["mean"] +
               .954117) > .000001
    ):
        raise ValueError("Gate1 baseline reproducibility drift")
    return {
        "schema": "qore.vt31.gate2.four_regimes_asof_window_start.v1",
        "preregistered_commit": PREREG,
        "market_sha256": SOURCE_SHA,
        "approved_ledger_sha256": LEDGER_SHA,
        "m1_original": 1059784,
        "complete_original_windows": len(complete),
        "COG_OPS_sources": 2140,
        "baseline_Gate1_paired_delta_gross_15m": -.954117,
        "regime_counts_including_unknown": dict(sorted(counts.items())),
        "regime_counts_by_session": {
            k: dict(sorted(v.items())) for k, v in sorted(by_session.items())
        },
        "missing_M1_details": dict(sorted(missing.items())),
        "four_frozen_cells": results,
        "multiplicity": "Bonferroni 4 two-sided CI98.75pct",
        "regime_features_only_prior_60m_and_prior_20_same_session": True,
        "repeated_development_NOT_independent_holdout": True,
        "confounded_selection_COG_PLUS_OPS_not_COG_only": True,
        "comparisons_different_signal_direction_or_confirmation_time": True,
        "no_broker_fills_orders_costs": True,
        "profit_factor_drawdown": None,
        "fresh_holdout_opened": False,
        "production_live_vps_modified": False,
        "G3": "PENDING_DUAL_SIGNATURE",
        "verdict": (
            "EXPLORATORY_REGIME_LIFT_REQUIRES_FRESH_OOS"
            if any(v["gate"] == "EXPLORATORY_POSITIVE_NOT_ECONOMIC_EDGE"
                   for v in results.values())
            else "NO_REGIME_SELECTION_LIFT_DEMONSTRATED"
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if _digest(args.market) != SOURCE_SHA:
        raise ValueError("immutable market checksum mismatch")
    if _digest(args.ledger) != LEDGER_SHA:
        raise ValueError("immutable approved ledger checksum mismatch")
    raw, complete, _ = census_raw(args.market)
    approved = json.loads(args.ledger.read_text(encoding="utf8"))
    sel, _ = prepare(approved)
    stamps = set()
    for event in (*raw.values(), *sel):
        for minute in range(16):
            stamps.add(event["formed"] + timedelta(minutes=minute))
    opens = get_opens(args.market, stamps)
    regimes = classify_all_source_starts(args.market)
    result = review(raw, complete, approved, opens, regimes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print(json.dumps({
        "counts": result["regime_counts_including_unknown"],
        "four": result["four_frozen_cells"],
        "verdict": result["verdict"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
