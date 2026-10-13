#!/usr/bin/env python3
"""Independent four-family TTrades-AM *source-only* causal detector.

Source-only = detection of timestamped *hypotheses*, never broker entries.
TTrades article enumerates FVG / OB / breaker / reversal displacement, but
exact numerical definitions here are PREREGISTERED QORE operational proxies.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from scripts.vt31_ttrades_am_source_20261013 import (
    Bar,
    collect_days,
    diagnostic,
    displacement,
    file_hash,
    full_hour,
    fvg,
    market_source,
)

FAMILIES = (
    "DISPLACEMENT_DIRECT", "FVG_3M1", "ORDER_BLOCK_RETEST", "BREAKER_RETEST",
)
SOURCE_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
PREREG = "0a3ee8a7c307d2adf7cdda24eb609732c2e703a1"


def find_pivot(prior_9am: list[Bar], side: str) -> tuple[float, datetime] | None:
    """Last already confirmed three-bar 9am extremum, not a retro swing."""
    found: list[tuple[float, datetime]] = []
    for j in range(1, len(prior_9am) - 1):
        left, x, right = prior_9am[j-1:j+2]
        if (left.time + timedelta(minutes=1) != x.time or
                x.time + timedelta(minutes=1) != right.time):
            continue
        if side == "SHORT" and x.high > left.high and x.high > right.high:
            found.append((x.high, right.time + timedelta(minutes=1)))
        elif side == "LONG" and x.low < left.low and x.low < right.low:
            found.append((x.low, right.time + timedelta(minutes=1)))
    return found[-1] if found else None


def context(
    nine: list[Bar], ten: list[Bar],
) -> tuple[str, dict[str, Any] | None]:
    """Find first sweep then first STRICT inside-range displacement causally."""
    if not full_hour(nine, 9):
        return "MISSING_REFERENCE_H1", None
    if not full_hour(ten, 10):
        return "MISSING_SB_HOUR", None
    hi = max(x.high for x in nine)
    lo = min(x.low for x in nine)
    if hi <= lo:
        return "DEGENERATE_9AM_RANGE", None

    side = None
    sweep_i = None
    disp_i = None
    sweep_extreme = None
    for i, candle in enumerate(ten):
        hit_high = candle.high > hi
        hit_low = candle.low < lo
        if side is None:
            if hit_high and hit_low:
                return "DOUBLE_SWEEP_AMBIGUOUS", None
            if hit_high:
                side = "SHORT"
                sweep_i = i
                sweep_extreme = candle.high
            elif hit_low:
                side = "LONG"
                sweep_i = i
                sweep_extreme = candle.low
            continue
        if (side == "SHORT" and hit_low) or (
            side == "LONG" and hit_high
        ):
            return "DOUBLE_SWEEP_BEFORE_DISPLACEMENT", None
        if disp_i is not None:
            break
        assert sweep_extreme is not None and sweep_i is not None
        sweep_extreme = (
            max(sweep_extreme, candle.high)
            if side == "SHORT" else min(sweep_extreme, candle.low)
        )
        if i > sweep_i and lo < candle.close < hi and displacement(
            nine + ten[:i], candle, side, hi, lo,
        ):
            disp_i = i
            break
    if side is None:
        return "NO_SWEEP", None
    if disp_i is None:
        return "NO_DISPLACEMENT_IN_RANGE", None
    assert sweep_i is not None and sweep_extreme is not None
    return "CONTEXT_CONFIRMED", {
        "side": side, "sweep_i": sweep_i, "disp_i": disp_i,
        "high9": hi, "low9": lo, "sweep_extreme_at_displacement": sweep_extreme,
        "pivot": find_pivot(nine, side),
    }


def _stopped_or_target_same_bar(
    b: Bar, *, stop: float, target: float,
) -> bool:
    # This is a conservative warning; never infer intrabar sequence.
    return b.low <= stop or b.high >= target


def _output(
    *, day: str, family: str, index: int, side: str, ref_price: float,
    sweep_extreme: float, high9: float, low9: float,
    ten: list[Bar], zone: tuple[float, float] | None = None,
    source: str, ambiguous_retest_bar: bool = False,
) -> dict[str, Any] | None:
    target = high9 if side == "LONG" else low9
    if not (
        sweep_extreme < ref_price < target
        if side == "LONG" else target < ref_price < sweep_extreme
    ):
        return None
    b = ten[index]
    close_at = b.time + timedelta(minutes=1)
    return {
        "id": f"TTRADES_ALL4_V1|{day}|{family}|{close_at.isoformat()}",
        "day_ny": day, "family": family, "side": side,
        "source_witness": source,
        "confirmed_at": close_at.isoformat(),
        "reference_price_NOT_FILL": ref_price,
        "candidate_swing_stop_NOT_BROKER_SL": sweep_extreme,
        "DOL_opposite_9am_H1": target,
        "zone_low_high": list(zone) if zone is not None else None,
        "retest_bar_stop_target_ambiguous_NOT_EXECUTION": ambiguous_retest_bar,
        "source_only_NO_EXECUTION": True,
        "gross_15m_after_next_M1_OPEN_not_trade": None,
    }


def _opposite_raid(b: Bar, side: str, high9: float, low9: float) -> bool:
    return (b.low < low9) if side == "SHORT" else (b.high > high9)


def emit_day(
    day: str, hours: dict[int, list[Bar]],
) -> tuple[str, dict[str, dict[str, Any]], dict[str, str]]:
    """At most one fixed first causal source for EACH family; no PnL ranking."""
    nine, ten = hours[9], hours[10]
    status, ctx = context(nine, ten)
    if ctx is None:
        return status, {}, {key: status for key in FAMILIES}
    side = ctx["side"]
    si = ctx["sweep_i"]
    di = ctx["disp_i"]
    hi = ctx["high9"]
    lo = ctx["low9"]
    assert isinstance(side, str) and isinstance(si, int) and isinstance(di, int)
    assert isinstance(hi, float) and isinstance(lo, float)
    sweep = float(ctx["sweep_extreme_at_displacement"])
    proposals: dict[str, dict[str, Any]] = {}
    outcomes = {key: "NO_SOURCE_WITNESS" for key in FAMILIES}

    # Direct displacement close is its own research source, NOT an automatic trade.
    direct = _output(
        day=day, family="DISPLACEMENT_DIRECT", index=di,
        side=side, ref_price=ten[di].close, sweep_extreme=sweep,
        high9=hi, low9=lo, ten=ten,
        source="POST_SWEEP_M1_DISPLACEMENT_CLOSE",
    )
    outcomes["DISPLACEMENT_DIRECT"] = (
        "SOURCE_ONLY_CANDIDATE" if direct else "NONEXECUTABLE_GEOMETRY"
    )
    if direct:
        proposals["DISPLACEMENT_DIRECT"] = direct

    # OB candle is determined at displacement; retest can only occur later.
    opposing = [
        i for i in range(si, di)
        if (ten[i].close < ten[i].open if side == "LONG"
            else ten[i].close > ten[i].open)
    ]
    ob_i = opposing[-1] if opposing else None
    ob_ref = (
        (ten[ob_i].open + ten[ob_i].close) / 2
        if ob_i is not None else None
    )
    pivot = ctx["pivot"]
    # The 9am swing MUST be confirmed before the 10am first sweep.
    breaker_level: float | None = None
    if pivot is not None:
        level, confirmed = pivot
        passed = (
            any(x.high > level for x in ten[si:di+1])
            if side == "SHORT" else
            any(x.low < level for x in ten[si:di+1])
        )
        reclaimed = (
            ten[di].close < level if side == "SHORT"
            else ten[di].close > level
        )
        if confirmed <= ten[si].time and passed and reclaimed:
            breaker_level = level

    # FVG at/after displacement must be a contiguous triple starting
    # NO EARLIER than sweep candle; no future facts in its confirmation.
    sweep_extreme_now = sweep
    for i in range(di, 60):
        bar = ten[i]
        if i > di and _opposite_raid(bar, side, hi, lo):
            for key in FAMILIES:
                if key not in proposals and outcomes[key] == "NO_SOURCE_WITNESS":
                    outcomes[key] = "OPPOSITE_RAID_BEFORE_SETUP"
            break
        if i > di:
            sweep_extreme_now = (
                max(sweep_extreme_now, bar.high) if side == "SHORT"
                else min(sweep_extreme_now, bar.low)
            )

        if i >= 2 and i - 2 >= si and "FVG_3M1" not in proposals and (
            outcomes["FVG_3M1"] == "NO_SOURCE_WITNESS"
        ):
            zone = fvg(ten[i-2], ten[i-1], bar, side)
            if zone:
                midpoint = (zone[0] + zone[1]) / 2
                entry = _output(
                    day=day, family="FVG_3M1", index=i, side=side,
                    ref_price=midpoint, sweep_extreme=sweep_extreme_now,
                    high9=hi, low9=lo, ten=ten, zone=zone,
                    source="THREE_CONTIGUOUS_M1_FIRST_FVG_CONFIRMED",
                )
                outcomes["FVG_3M1"] = (
                    "SOURCE_ONLY_CANDIDATE" if entry
                    else "NONEXECUTABLE_GEOMETRY"
                )
                if entry:
                    proposals["FVG_3M1"] = entry

        if i <= di:
            continue
        for family, price, src in (
            ("ORDER_BLOCK_RETEST", ob_ref, "LAST_OPPOSING_PRE_DISP_BODY_MID_RETEST"),
            ("BREAKER_RETEST", breaker_level, "CONFIRMED_PRE_SWEEP_PIVOT_RECLAIM_RETEST"),
        ):
            if family in proposals or outcomes[family] != "NO_SOURCE_WITNESS":
                continue
            if price is None:
                continue
            if not bar.low <= price <= bar.high:
                continue
            item = _output(
                day=day, family=family, index=i, side=side,
                ref_price=price, sweep_extreme=sweep_extreme_now,
                high9=hi, low9=lo, ten=ten,
                source=src,
                ambiguous_retest_bar=_stopped_or_target_same_bar(
                    bar, stop=sweep_extreme_now,
                    target=hi if side == "LONG" else lo,
                ),
            )
            outcomes[family] = (
                "SOURCE_ONLY_CANDIDATE" if item
                else "NONEXECUTABLE_GEOMETRY"
            )
            if item:
                proposals[family] = item

    return "CONTEXT_CONFIRMED", proposals, outcomes


def forward_15(
    event: dict[str, Any], hours: dict[int, list[Bar]],
) -> float | None:
    end = datetime.fromisoformat(event["confirmed_at"])
    recorded = {x.time: x for hour in (10, 11) for x in hours[hour]}
    times = [end + timedelta(minutes=i) for i in range(16)]
    if any(t not in recorded for t in times):
        return None
    sign = 1 if event["side"] == "LONG" else -1
    return sign * (recorded[times[-1]].open - recorded[times[0]].open)


def analyze(days: dict[str, dict[int, list[Bar]]]) -> dict[str, Any]:
    if not days:
        raise ValueError("at least one M1 day needed")
    context_counts: Counter[str] = Counter()
    family_counts: dict[str, Counter[str]] = {
        key: Counter() for key in FAMILIES
    }
    by_year: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    signals: dict[str, list[dict[str, Any]]] = {key: [] for key in FAMILIES}
    returns: dict[str, list[tuple[str, float]]] = {
        key: [] for key in FAMILIES
    }
    union_days = 0
    for day, hours in sorted(days.items()):
        status, proposals, reason = emit_day(day, hours)
        context_counts[status] += 1
        if proposals:
            union_days += 1
        for family in FAMILIES:
            family_counts[family][reason[family]] += 1
            by_year[day[:4]][family] += int(family in proposals)
            if family not in proposals:
                continue
            candidate = proposals[family]
            forward = forward_15(candidate, hours)
            if forward is None:
                family_counts[family]["NO_M1_FORWARD_COVERAGE"] += 1
            else:
                candidate["gross_15m_after_next_M1_OPEN_not_trade"] = round(
                    forward, 6
                )
                returns[family].append((day, forward))
            signals[family].append(candidate)

    for name in FAMILIES:
        denominator = sum(
            n for k, n in family_counts[name].items()
            if k != "NO_M1_FORWARD_COVERAGE"
        )
        if denominator != len(days) or len(signals[name]) != family_counts[
            name
        ]["SOURCE_ONLY_CANDIDATE"]:
            raise ValueError("family source partition invalid")

    return {
        "schema": "qore.vt31.ttrades_am_all_entry_families_source.v1",
        "pre_replay_prereg_commit": PREREG,
        "market_sha256": SOURCE_SHA,
        "M1_3year_total": 1059784,
        "source_days_ny": len(days),
        "family_independently_evaluated_no_winner_chosen": list(FAMILIES),
        "days_with_at_least_one_family": union_days,
        "context_counts": dict(sorted(context_counts.items())),
        "family_source_counts": {
            name: dict(sorted(family_counts[name].items()))
            for name in FAMILIES
        },
        "by_year": {k: dict(sorted(v.items())) for k, v in sorted(by_year.items())},
        "family_fixed_15m_directional_only": {
            name: diagnostic(returns[name]) for name in FAMILIES
        },
        "family_source_witnesses": signals,
        "QORE_operational_definitions_NOT_author_literal": True,
        "retest_M1_OHLC_not_actual_limit_fill": True,
        "multiple_families_same_day_are_not_multiple_trades": True,
        "broker_quotes_order_ack": 0,
        "economic_pf_dd_sharpe": None,
        "source_does_not_recreate_NQ_futures": True,
        "g3_original_unchanged_unsigned": True,
        "fresh_holdout_opened": False,
        "live_trades": 0,
        "economic_edge": "NOT_IDENTIFIED",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        t = datetime.fromisoformat("2025-07-01T13:00:00+00:00")
        assert find_pivot([], "SHORT") is None
        assert _opposite_raid(
            Bar(t, 30000, 30002, 29990, 30001),
            "LONG", 30001, 29985,
        ) is True
        print("SOURCE-ONLY FOUR FAMILIES synthetic selftest PASS")
        return
    if args.market is None or args.out is None:
        p.error("frozen original market and output required")
    if file_hash(args.market) != SOURCE_SHA:
        raise ValueError("M1 source sha256 drift / prohibited replacement")
    days = collect_days(market_source(args.market))
    report = analyze(days)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "source_days": report["source_days_ny"],
        "union_source_days_not_trades": report["days_with_at_least_one_family"],
        "family_counts": {
            k: v.get("SOURCE_ONLY_CANDIDATE", 0)
            for k, v in report["family_source_counts"].items()
        },
        "gross_15m_NOT_PNL": report["family_fixed_15m_directional_only"],
        "economic_edge": report["economic_edge"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
