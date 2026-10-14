#!/usr/bin/env python3
"""Four-leg BREAKER QORE structural witness, never an author-certified entry.

Compares a single three-bar pivot with source text requiring four swing legs
and a directional candle zone. The precise pivot/tie rule is QORE engineering.
No orders, no stops, no broker fills and no live authorization.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    MARKET_SHA,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
)

PREREG = "833fd1746659c6034cfcd49c816fb5c4804dedb1"
SUCCESS = "FOUR_LEG_RESEARCH_WITNESS_NOT_AUTHOR_CERTIFIED"


@dataclass(frozen=True)
class Pivot:
    kind: str
    price: str
    middle_index: int
    available_at: datetime


def confirmed_pivots(bars: tuple[M1Bar, ...]) -> tuple[Pivot, ...]:
    """Strict 3×M1 pivot, visible only at RIGHT neighbor closed_at."""
    results = []
    for i in range(1, len(bars) - 1):
        left, mid, right = bars[i-1:i+2]
        if left.closed_at != mid.opened_at or mid.closed_at != right.opened_at:
            raise ValueError("M1_GAP_OR_DUPLICATE_IN_PIVOT_SOURCE")
        is_high = mid.high > left.high and mid.high > right.high
        is_low = mid.low < left.low and mid.low < right.low
        if is_high and is_low:
            # Unknown intraminute high-low order: no swing identity inferred.
            continue
        if is_high:
            results.append(Pivot("HIGH", str(mid.high), i, right.closed_at))
        elif is_low:
            results.append(Pivot("LOW", str(mid.low), i, right.closed_at))
    return tuple(results)


def _first_prior_pair(
    swings: tuple[Pivot, ...], *, side: str,
) -> tuple[Pivot, Pivot] | None:
    """Pick first leg then first confirming second leg, never rescue."""
    first_kind, second_kind = (
        ("LOW", "HIGH") if side == "LONG" else ("HIGH", "LOW")
    )
    first = next((x for x in swings if x.kind == first_kind), None)
    if first is None:
        return None
    second = next(
        (x for x in swings
         if x.kind == second_kind and x.middle_index > first.middle_index),
        None,
    )
    return (first, second) if second is not None else None


def _case(
    day: str, state: str, *, side: str | None = None,
    raid_at: datetime | None = None,
    pair: tuple[Pivot, Pivot] | None = None,
    third: Pivot | None = None,
    fourth: Pivot | None = None,
    zone: tuple[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "ny_day": day, "state": state, "side": side,
        "raid_m1_closed_at": raid_at.isoformat() if raid_at else None,
        "h1_first_pivot": pair[0].__dict__ | {
            "available_at": pair[0].available_at.isoformat()
        } if pair else None,
        "h1_second_pivot": pair[1].__dict__ | {
            "available_at": pair[1].available_at.isoformat()
        } if pair else None,
        "third_pivot": third.__dict__ | {
            "available_at": third.available_at.isoformat()
        } if third else None,
        "fourth_pivot": fourth.__dict__ | {
            "available_at": fourth.available_at.isoformat()
        } if fourth else None,
        "zone_proxy_from_directional_candle_series": zone,
        "author_breaker_certified": False,
        "four_leg_pivot_rule_author_attributed": False,
        "retest_or_entry_executed": False,
    }


def audit_day(
    day: str, hours: dict[int, tuple[M1Bar, ...]],
) -> dict[str, Any]:
    nine, ten = hours.get(9, ()), hours.get(10, ())
    if not complete_hour(day, 9, nine) or not complete_hour(day, 10, ten):
        return _case(day, "INCOMPLETE_09_10")
    h1_hi = max(x.high for x in nine)
    h1_lo = min(x.low for x in nine)
    if h1_hi <= h1_lo:
        return _case(day, "INCOMPLETE_09_10")
    prior_swings = confirmed_pivots(nine)
    first_raid_i: int | None = None
    raid_at: datetime | None = None
    side: str | None = None
    pair: tuple[Pivot, Pivot] | None = None
    zone: tuple[str, str] | None = None
    third: Pivot | None = None
    fourth: Pivot | None = None

    for i, bar in enumerate(ten):
        high_raid = bar.high > h1_hi
        low_raid = bar.low < h1_lo
        if high_raid and low_raid:
            return _case(day, "DOUBLE_FIRST_RAID_UNKNOWN", side=side)
        if first_raid_i is None:
            if high_raid or low_raid:
                side = "SHORT" if high_raid else "LONG"
                first_raid_i, raid_at = i, bar.closed_at
                pair = _first_prior_pair(prior_swings, side=side)
                if pair is None:
                    return _case(
                        day, "NO_H1_CONFIRMED_PAIR", side=side, raid_at=raid_at,
                    )
                a, z = pair
                segment = nine[a.middle_index:z.middle_index+1]
                directional = tuple(
                    row for row in segment
                    if (row.close > row.open if side == "LONG"
                        else row.close < row.open)
                )
                if directional:
                    zone = (
                        str(min(x.low for x in directional)),
                        str(max(x.high for x in directional)),
                    )
            continue
        if (side == "LONG" and high_raid) or (side == "SHORT" and low_raid):
            return _case(day, "OPPOSITE_RAID_BEFORE_CONTEXT", side=side)
        if i < 2:
            continue
        left, mid, right = ten[i-2:i+1]
        if left.closed_at != mid.opened_at or mid.closed_at != right.opened_at:
            raise ValueError("TEN_AM_M1_SOURCE_GAP")
        is_hi = mid.high > left.high and mid.high > right.high
        is_lo = mid.low < left.low and mid.low < right.low
        if is_hi and is_lo:
            continue
        assert pair is not None and first_raid_i is not None
        if (i-1) < first_raid_i:
            continue
        if third is None:
            if (
                (side == "LONG" and is_lo and mid.low < type(mid.low)(pair[0].price))
                or (side == "SHORT" and is_hi and mid.high > type(mid.high)(pair[0].price))
            ):
                third = Pivot(
                    "LOW" if side == "LONG" else "HIGH",
                    str(mid.low if side == "LONG" else mid.high),
                    i-1, right.closed_at,
                )
            continue
        if (i-1) <= third.middle_index:
            continue
        if (
            (side == "LONG" and is_hi and mid.high > type(mid.high)(pair[1].price))
            or (side == "SHORT" and is_lo and mid.low < type(mid.low)(pair[1].price))
        ):
            fourth = Pivot(
                "HIGH" if side == "LONG" else "LOW",
                str(mid.high if side == "LONG" else mid.low),
                i-1, right.closed_at,
            )
            break
    if first_raid_i is None:
        return _case(day, "NO_FIRST_RAID")
    if third is None:
        return _case(
            day, "NO_10AM_FIRST_FAILURE_SWING", side=side,
            raid_at=raid_at, pair=pair, zone=zone,
        )
    if fourth is None:
        return _case(
            day, "NO_10AM_CONFIRMATION_SWING", side=side,
            raid_at=raid_at, pair=pair, third=third, zone=zone,
        )
    if zone is None:
        return _case(
            day, "NO_BLOCK_CANDLE_ZONE", side=side,
            raid_at=raid_at, pair=pair, third=third, fourth=fourth,
        )
    return _case(
        day, SUCCESS, side=side, raid_at=raid_at, pair=pair,
        third=third, fourth=fourth, zone=zone,
    )


def census_source(
    groups: dict[str, dict[int, tuple[M1Bar, ...]]],
    *, validate_full: bool = True,
) -> dict[str, Any]:
    cases = [audit_day(day, data) for day, data in sorted(groups.items())]
    counts = dict(sorted(Counter(x["state"] for x in cases).items()))
    if validate_full:
        if len(cases) != 775 or counts.get("INCOMPLETE_09_10", 0) != 6:
            raise ValueError("FROZEN_775_DAYS_769_COMPLETE_H1_SOURCE_CHANGED")
    return {
        "prereg_commit": PREREG,
        "source_sha256": MARKET_SHA,
        "research_model": "STRICT_QORE_4_LEG_BREAKER_DIAGNOSTIC_NOT_AUTHOR_METHOD",
        "total_ny_days": len(cases),
        "status_counts": counts,
        "all_cases": cases,
        "author_breaker_certified": False,
        "candidate_binding_reused_as_certification": False,
        "trader_lab_L1_qualified": False,
        "trader_lab_L2_to_L10_qualified": False,
        "broker_orders": 0, "entry_fills": 0, "risk_sizing": 0,
        "financial_edge_established": False,
        "fresh_holdout": False, "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("SOURCE_SHA256_CHANGED")
    groups, total = collect_hours(market_rows(args.market))
    if total != 1_059_784:
        raise ValueError("SOURCE_M1_COUNT_CHANGED")
    result = census_source(groups)
    result["original_m1_count"] = total
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "original_m1_count": total, "total_ny_days": result["total_ny_days"],
        "status_counts": result["status_counts"],
        "author_breaker_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
