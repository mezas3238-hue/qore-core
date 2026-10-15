#!/usr/bin/env python3
"""TTrades AUTHOR-sourced M4/M5 building blocks; NO trade, stop or sizing.

Source 2025: short-term swings use three bars (one either side);
MSS breaks a swing via displacement; CISD closes through opposing
candle open; OB body mean threshold; breaker has four structure legs.
This witness attests only these observable relations, NOT whole
TTrades AM strategy, entry/stop/authorial displacement or LIVE.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    Side,
)
from scripts.vt31_m3_ttrades_cog_wait_v2_20261015 import (
    TTradesAmWaitCognitionV2,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
    run_census,
)

PREREG = "ff27e6df536a45166c01443a300c38d844184e5a"
VERSION = "VT31_TTRADES_AUTHOR_PRIMARIES_M4_M5_SOURCE_BRIDGE_V1"
AUTHOR_PAGES = (
    "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
    "https://ttrades.com/order-blocks-simplified/",
    "https://ttrades.com/breaker-blocks-simplified/",
    "https://ttrades.com/market-structure-shifts-vs-change-in-the-state-of-delivery-a-clear-comparison/",
    "https://ttrades.com/advanced-market-structure-simplified-from-short-term-to-long-term-trends/",
)
FROZEN = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
ACTIVE = frozenset({
    "WAIT_FOR_CONFIRMATION",
    "QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED",
})


@dataclass(frozen=True)
class AuthorShortTermSwing:
    kind: Literal["HIGH", "LOW"]
    extremum: Decimal
    pivot_closed_at: datetime
    confirmed_at: datetime
    source_author_geometry: bool = True
    author_causative_for_displacement: bool = False


@dataclass(frozen=True)
class SourceFourLegSequence:
    direction: str
    first_at: datetime
    last_confirmed_at: datetime
    legs: tuple[AuthorShortTermSwing, ...]
    breaker_zone_and_retest_verified: bool = False
    author_entry_valid: bool = False


@dataclass(frozen=True)
class OrderBlockCisdEvidence:
    side: Side
    opposing_open: Decimal
    opposing_body_midpoint: Decimal
    opposing_candle_closed_at: datetime
    confirmed_at: datetime
    source_ob_cisd_closure: bool = True
    author_displacement_validated: bool = False
    author_trade_ready: bool = False


def short_term_swings(bars: tuple[M1Bar, ...]) -> tuple[AuthorShortTermSwing, ...]:
    """Exactly closed 3 adjacent M1 per TTrades short-term swing geometry."""
    events: list[AuthorShortTermSwing] = []
    for left, pivot, right in zip(bars, bars[1:], bars[2:], strict=False):
        if (
            left.closed_at != pivot.opened_at
            or pivot.closed_at != right.opened_at
        ):
            continue
        high = pivot.high > left.high and pivot.high > right.high
        low = pivot.low < left.low and pivot.low < right.low
        if high:
            events.append(AuthorShortTermSwing(
                "HIGH", pivot.high, pivot.closed_at, right.closed_at,
            ))
        if low:
            events.append(AuthorShortTermSwing(
                "LOW", pivot.low, pivot.closed_at, right.closed_at,
            ))
    return tuple(sorted(events, key=lambda p: (p.confirmed_at, p.kind)))


def source_breaker_four_leg(
    swings: tuple[AuthorShortTermSwing, ...],
    side: Side,
    *,
    as_of: datetime,
) -> SourceFourLegSequence | None:
    """Four consecutive confirmed swing events; NOT zone/retest.

    The author specifies the pattern, but does not define a unique
    tie-break for multiple swing hierarchies. Adjacent event policy is
    QORE formalization and must be labeled, not sold as author perfect.
    """
    if as_of.tzinfo is None:
        raise ValueError("AWARE_ASOF_REQUIRED")
    visible = [s for s in swings if s.confirmed_at <= as_of]
    pattern = (
        ("LOW", "HIGH", "LOW", "HIGH")
        if side is Side.LONG else
        ("HIGH", "LOW", "HIGH", "LOW")
    )
    for i in range(len(visible)-3):
        a, b, c, d = visible[i:i+4]
        if (a.kind, b.kind, c.kind, d.kind) != pattern:
            continue
        if side is Side.LONG:
            structure = c.extremum < a.extremum and d.extremum > b.extremum
        else:
            structure = c.extremum > a.extremum and d.extremum < b.extremum
        if structure and a.confirmed_at < b.confirmed_at < c.confirmed_at < d.confirmed_at:
            return SourceFourLegSequence(
                side.value, a.confirmed_at, d.confirmed_at,
                (a, b, c, d),
            )
    return None


def source_ob_cisd(
    observed: tuple[M1Bar, ...],
    side: Side,
    *,
    first_sweep_at: datetime,
) -> OrderBlockCisdEvidence | None:
    """CISD *closure* through OPEN of last opposite candle series.

    The author describes opposing candle(s) and close through their
    open. Using latest opposing candle only is an explicitly QORE
    single-candle diagnostic; NOT full OB series or author trade setup.
    """
    if first_sweep_at.tzinfo is None:
        raise ValueError("AWARE_SWEEP_REQUIRED")
    if len(observed) < 2:
        return None
    current = observed[-1]
    if current.closed_at <= first_sweep_at:
        return None
    for candidate in reversed(observed[:-1]):
        if candidate.closed_at < first_sweep_at:
            break
        is_opposing = (
            candidate.close < candidate.open
            if side is Side.LONG else candidate.close > candidate.open
        )
        if not is_opposing:
            continue
        if current.opened_at < candidate.closed_at:
            raise AssertionError("SOURCE_CISD_CLOCK_REVERSED")
        confirmed = (
            current.close > candidate.open
            if side is Side.LONG else current.close < candidate.open
        )
        if not confirmed:
            return None
        return OrderBlockCisdEvidence(
            side=side, opposing_open=candidate.open,
            opposing_body_midpoint=(candidate.open+candidate.close)/Decimal(2),
            opposing_candle_closed_at=candidate.closed_at,
            confirmed_at=current.closed_at,
        )
    return None


def ob_body_midpoint_status(
    *, evidence: OrderBlockCisdEvidence, subsequent: M1Bar,
) -> str:
    """50% BODY, not whole-wick or FVG CE; no OHLC fill inference."""
    if subsequent.opened_at < evidence.confirmed_at:
        raise ValueError("FUTURE_OB_CANNOT_BE_APPLIED_TO_PAST")
    mid = evidence.opposing_body_midpoint
    if evidence.side is Side.LONG:
        against = subsequent.close < mid
        touched = subsequent.low <= mid <= subsequent.high
    else:
        against = subsequent.close > mid
        touched = subsequent.low <= mid <= subsequent.high
    if touched and against:
        return "AMBIGUOUS_TOUCH_AND_INVALIDATION_SAME_M1_NO_FILL"
    if against:
        return "OB_INVALIDATED_BY_BODY_MID_CLOSE"
    if touched:
        return "OB_BODY_MID_TOUCHED_NOT_EXECUTION"
    return "OB_WAIT_NO_RETEST"


def audit_day(
    *, day: str, nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...], return_at: datetime,
) -> dict[str, object]:
    if not (complete_hour(day, 9, nine) and complete_hour(day, 10, ten)):
        raise ValueError("SOURCE_H1_09_10_REQUIRED")
    engine = TTradesAmWaitCognitionV2()
    for bar in nine:
        engine.observe_closed_m1(bar)
    snaps = [engine.observe_closed_m1(b) for b in ten]
    valid = [(i, snap) for i,snap in enumerate(snaps)
             if snap.first_return_at == return_at and snap.state in ACTIVE]
    cisd: OrderBlockCisdEvidence | None = None
    for i,snap in valid:
        if snap.as_of is None or snap.as_of <= return_at:
            continue
        if snap.bias not in ("LONG","SHORT") or snap.first_sweep_at is None:
            continue
        cisd = source_ob_cisd(
            ten[:i+1], Side(snap.bias),
            first_sweep_at=snap.first_sweep_at,
        )
        if cisd is not None:
            break

    pivot_events = short_term_swings(nine+ten)
    breaker: SourceFourLegSequence | None = None
    for _i,snap in valid:
        if snap.as_of is None or snap.as_of <= return_at or snap.bias not in ("LONG","SHORT"):
            continue
        candidate = source_breaker_four_leg(
            pivot_events, Side(snap.bias), as_of=snap.as_of,
        )
        if candidate is not None and candidate.last_confirmed_at >= return_at:
            breaker = candidate
            break

    # Per-profile source proof is only a building block and never a trade.
    return {
        "ny_day": day,
        "first_return_at": return_at.isoformat(),
        "source_profile": "TTRADES_NY_AM_2025",
        "short_term_swings_author_geometry_count_not_causes": len(pivot_events),
        "author_cisd_single_candle_diagnostic_confirmed_at": (
            cisd.confirmed_at.isoformat() if cisd else None
        ),
        "cisd_vs_mss_is_distinct": True,
        "ob_full_series_retest_author_certified": False,
        "author_breaker_four_leg_source_at": (
            breaker.last_confirmed_at.isoformat() if breaker else None
        ),
        "breaker_zone_retest_author_certified": False,
        "causative_swing_of_displacement_verified": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "sizing": False,
        "orders_ack_fills": 0,
    }


def audit_frozen_cases(
    groups: dict[str, dict[int, tuple[M1Bar, ...]]],
) -> dict[str, object]:
    census = run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != FROZEN:
        raise AssertionError("PREREGISTERED_SOURCE_DAYS_DRIFT")
    records: list[dict[str, object]] = []
    partitions: Counter[str] = Counter()
    first: dict[str, dict[str, object]] = {}
    for row in census["source_classifications"]:
        if row["classification"] != "FIRST_RETURN_NO_QORE_MSS":
            continue
        day=row["ny_day"]
        record=audit_day(
            day=day,nine=groups[day][9],ten=groups[day][10],
            return_at=datetime.fromisoformat(row["as_of"]).astimezone(UTC),
        )
        records.append(record)
        for field,name in (
            ("author_cisd_single_candle_diagnostic_confirmed_at","OB_CISD_SOURCE_COMPONENT_OBSERVED"),
            ("author_breaker_four_leg_source_at","BREAKER_FOUR_LEG_STRUCTURE_OBSERVED"),
        ):
            if record[field] is not None:
                partitions[name]+=1
                first.setdefault(name,record)
        if record["author_cisd_single_candle_diagnostic_confirmed_at"] is None:
            partitions["NO_CISD_COMPONENT"]+=1
            first.setdefault("NO_CISD_COMPONENT",record)
        if record["author_breaker_four_leg_source_at"] is None:
            partitions["NO_BREAKER_FOUR_LEG"]+=1
            first.setdefault("NO_BREAKER_FOUR_LEG",record)
    if len(records)!=483:
        raise AssertionError("FROZEN_483_NOT_EXHAUSTED")
    if partitions["OB_CISD_SOURCE_COMPONENT_OBSERVED"]+partitions["NO_CISD_COMPONENT"] != 483:
        raise AssertionError("CISD_PARTITION_DRIFT")
    if partitions["BREAKER_FOUR_LEG_STRUCTURE_OBSERVED"]+partitions["NO_BREAKER_FOUR_LEG"] != 483:
        raise AssertionError("BREAKER_PARTITION_DRIFT")
    if any(
        x["methodology_certified"] or x["cognition_certified"]
        or x["orders_ack_fills"] for x in records
    ):
        raise AssertionError("AUTHOR_SOURCE_COMPONENT_CANNOT_CREATE_TRADES")
    return {
        "schema":VERSION,
        "prereg_sha":PREREG,
        "original_m1_sha256":MARKET_SHA,
        "source_urls":AUTHOR_PAGES,
        "frozen_real_M1_cases":len(records),
        "component_evidence_by_case_not_PnL":dict(sorted(partitions.items())),
        "first_real_example_by_component":first,
        "all_real_cognitive_source_records":records,
        "short_term_swing_3bar_geometry_author_described":True,
        "swing_causation_proven":False,
        "OB_complete_structure_retest_proven":False,
        "Breaker_complete_zone_retest_proven":False,
        "M4_method_certified":False,
        "M5_method_certified":False,
        "M6_two_independent_signers_verified":False,
        "trader_method_cognition_certified":False,
        "PnL_sizing_or_optimization":False,
        "orders_ack_fills":0,
        "live_authorized":False,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--market",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if hash_file(args.market)!=MARKET_SHA:
        raise ValueError("M1_SOURCE_SHA256_MISMATCH")
    groups,total=collect_hours(market_rows(args.market))
    if total!=M1_TOTAL:
        raise AssertionError("M1_TOTAL_NOT_ORIGINAL")
    record=audit_frozen_cases(groups)
    record["source_m1_total"]=total
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "real_source_cases":record["frozen_real_M1_cases"],
        "semantic_components":record["component_evidence_by_case_not_PnL"],
        "first_real_dates": {
            k: v["ny_day"]
            for k,v in record["first_real_example_by_component"].items()
        },
        "M4_certified":False,"M5_certified":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
