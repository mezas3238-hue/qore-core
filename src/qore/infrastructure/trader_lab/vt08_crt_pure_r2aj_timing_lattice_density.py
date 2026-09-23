"""R2-AJ H4 timing-lattice density census for VT08 CRT PURE FX.

The CRT structural methodology is unchanged: C1 reference -> C2 one-sided
liquidation/reclaim -> C3 opportunity window.

This lab changes only the engineering timing lattice used to *observe* possible
H4 triplets:

CONTROL_NON_OVERLAP
    Existing FX policy: starts at 01:00 and 13:00 New York.

ROLLING_H4
    Every consecutive H4 start on the same NY lattice:
    01, 05, 09, 13, 17, 21.

The rolling family therefore adds overlapping C1/C2/C3 triplets without changing
the meaning of C1, C2 or C3.

No PnL is evaluated and no timing family is promoted here.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    _aggregate,
    _days,
    _segment,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    ParentCrt,
    _parent_direction,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    _candidate_pairs,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ai_opportunity_capacity import (
    _midpoint_valid,
    _structural_risk_valid,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_timing_policy import NY

IDENTITY = "VT08_CRT_PURE_R2AJ_H4_TIMING_LATTICE_DENSITY_001"
SCHEMA = "qore.vt08.crt_pure.r2aj_h4_timing_lattice_density.v1"

START = datetime(2020, 9, 21, 0, 0, tzinfo=NY).astimezone()
END = datetime(2026, 9, 21, 0, 0, tzinfo=NY).astimezone()
FX_MARKETS = (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY)


class TimingLattice(StrEnum):
    CONTROL_NON_OVERLAP = "CONTROL_NON_OVERLAP"
    ROLLING_H4 = "ROLLING_H4"


START_HOURS: dict[TimingLattice, tuple[int, ...]] = {
    TimingLattice.CONTROL_NON_OVERLAP: (1, 13),
    TimingLattice.ROLLING_H4: (1, 5, 9, 13, 17, 21),
}


@dataclass(frozen=True, slots=True)
class H4Window:
    c1_open: datetime
    c2_open: datetime
    c3_open: datetime
    close: datetime


def _window(day: datetime, start_hour: int) -> H4Window:
    local = day.astimezone(NY)
    c1 = datetime(
        local.year,
        local.month,
        local.day,
        start_hour,
        tzinfo=NY,
    )
    return H4Window(
        c1_open=c1,
        c2_open=c1 + timedelta(hours=4),
        c3_open=c1 + timedelta(hours=8),
        close=c1 + timedelta(hours=12),
    )


def _parents(
    *,
    market: CrtPureMarket,
    bars: tuple[Any, ...],
    lattice: TimingLattice,
) -> tuple[ParentCrt, ...]:
    by_time = {bar.opened_at: bar for bar in bars}
    start_day = (START - timedelta(days=1)).astimezone(NY).date()
    end_day = END.astimezone(NY).date()
    parents: list[ParentCrt] = []

    for date_value in _days(start_day, end_day):
        local_noon = datetime(
            date_value.year,
            date_value.month,
            date_value.day,
            12,
            tzinfo=NY,
        )
        for index, hour in enumerate(START_HOURS[lattice], start=1):
            window = _window(local_noon, hour)
            c1_open = window.c1_open.astimezone(START.tzinfo)
            c2_open = window.c2_open.astimezone(START.tzinfo)
            c3_open = window.c3_open.astimezone(START.tzinfo)
            close = window.close.astimezone(START.tzinfo)
            if not START <= c3_open < END:
                continue

            c1_m5 = _segment(by_time, c1_open, c2_open)
            c2_m5 = _segment(by_time, c2_open, c3_open)
            c3_m5 = _segment(by_time, c3_open, close)
            if c1_m5 is None or c2_m5 is None or c3_m5 is None:
                continue

            c1 = _aggregate(c1_m5, c1_open, c2_open)
            c2 = _aggregate(c2_m5, c2_open, c3_open)
            direction = _parent_direction(c1, c2)
            if direction is None:
                continue

            parents.append(
                ParentCrt(
                    market=market,
                    direction=direction,
                    triplet=f"{lattice.value}:{index}",
                    c3_opened_at=c3_open,
                    c3_closed_at=close,
                    c1=c1,
                    c2=c2,
                    c3_m5=c3_m5,
                )
            )
    return tuple(parents)


def _summarize(
    *,
    parents: tuple[ParentCrt, ...],
    bars: tuple[Any, ...],
) -> dict[str, Any]:
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)
    counter: Counter[str] = Counter()

    for parent in parents:
        counter["parent_count"] += 1
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        counter["source_event_count"] += len(observations)
        pairs = _candidate_pairs(
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        counter["confirmed_slot_count"] += len(pairs)

        structural = 0
        midpoint = 0
        for observation, _, entry_bar in pairs:
            source = observation.group.source_candle
            if _structural_risk_valid(
                parent=parent,
                source_low=source.low_price,
                source_high=source.high_price,
                entry=entry_bar.open_price,
            ):
                structural += 1
            if _midpoint_valid(
                parent=parent,
                source_low=source.low_price,
                source_high=source.high_price,
                entry=entry_bar.open_price,
            ):
                midpoint += 1

        counter["structural_slot_count"] += structural
        counter["midpoint_slot_count"] += midpoint
        counter["confirmed_cap1"] += min(len(pairs), 1)
        counter["structural_cap1"] += min(structural, 1)
        counter["midpoint_cap1"] += min(midpoint, 1)
        counter["confirmed_cap2"] += min(len(pairs), 2)
        counter["structural_cap2"] += min(structural, 2)
        counter["midpoint_cap2"] += min(midpoint, 2)

    years = 6
    return {
        **dict(counter),
        "parents_per_year": round(counter["parent_count"] / years, 8),
        "confirmed_slots_per_year": round(
            counter["confirmed_slot_count"] / years,
            8,
        ),
        "structural_slots_per_year": round(
            counter["structural_slot_count"] / years,
            8,
        ),
        "midpoint_slots_per_year": round(
            counter["midpoint_slot_count"] / years,
            8,
        ),
        "structural_cap1_per_year": round(
            counter["structural_cap1"] / years,
            8,
        ),
        "structural_cap2_per_year": round(
            counter["structural_cap2"] / years,
            8,
        ),
    }


def run_census(market: CrtPureMarket) -> dict[str, Any]:
    if market not in FX_MARKETS:
        raise ValueError("R2-AJ is FX-only")

    fetch_start = START - timedelta(days=2)
    fetch_end = END + timedelta(days=2)
    bars = load_m5_window(
        market,
        start=fetch_start,
        end_exclusive=fetch_end,
    )

    results: dict[str, Any] = {}
    for lattice in TimingLattice:
        parents = _parents(
            market=market,
            bars=bars,
            lattice=lattice,
        )
        results[lattice.value] = _summarize(
            parents=parents,
            bars=bars,
        )

    control = results[TimingLattice.CONTROL_NON_OVERLAP.value]
    rolling = results[TimingLattice.ROLLING_H4.value]
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": 6,
        "lattices": results,
        "rolling_vs_control": {
            "parent_multiplier": (
                0.0
                if int(control["parent_count"]) == 0
                else round(
                    int(rolling["parent_count"])
                    / int(control["parent_count"]),
                    8,
                )
            ),
            "structural_slot_multiplier": (
                0.0
                if int(control["structural_slot_count"]) == 0
                else round(
                    int(rolling["structural_slot_count"])
                    / int(control["structural_slot_count"]),
                    8,
                )
            ),
            "structural_cap1_multiplier": (
                0.0
                if int(control["structural_cap1"]) == 0
                else round(
                    int(rolling["structural_cap1"])
                    / int(control["structural_cap1"]),
                    8,
                )
            ),
        },
        "single_changed_dimension": "H4_TIMING_LATTICE",
        "c1_c2_c3_semantics_unchanged": True,
        "pnl_evaluated": False,
        "filter_promoted": False,
        "trades_created": 0,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in FX_MARKETS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    report = run_census(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print("CRT_R2AJ_TIMING_DENSITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
