"""R2-BK AUDUSD causal passive-entry capacity census.

Question
--------
R2-BG showed that most full -1R stops are dead-on-arrival. Before changing the
entry contract economically, measure whether a passive retracement entry can
preserve density.

Population
----------
Exact high-density ROLLING_H4 + Model #1 selected opportunity population.

Passive levels are known by confirmation close:
- CONF_BODY_MID: midpoint of confirmation open/close;
- CONF_RANGE_MID: midpoint of confirmation high/low;
- SOURCE_OPEN: source candle open.

Fill observation:
- first 30 minutes after the current next-M15-open decision point;
- underlying M5 bars only;
- level must be touched by an observed M5 range;
- structural stop geometry must remain valid at the passive fill price.

No PnL is evaluated and no entry arm is promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aq_high_density_historical_validation import (
    ValidationWindow,
    _rolling_parents,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2BK_AUDUSD_PASSIVE_ENTRY_CAPACITY_001"
SCHEMA = "qore.vt08.crt_pure.r2bk_audusd_passive_entry_capacity.v1"
MARKET = CrtPureMarket.AUDUSD
START = datetime(2011, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
YEARS = 15
HORIZON = timedelta(minutes=30)
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


class EntryArm(StrEnum):
    NEXT_OPEN_CONTROL = "NEXT_OPEN_CONTROL"
    CONF_BODY_MID = "CONF_BODY_MID"
    CONF_RANGE_MID = "CONF_RANGE_MID"
    SOURCE_OPEN = "SOURCE_OPEN"


def _midpoint(left: int, right: int) -> Decimal:
    return (Decimal(left) + Decimal(right)) / Decimal("2")


def _level(
    *,
    arm: EntryArm,
    source: M15Bar,
    confirmation: M15Bar,
    entry_bar: M15Bar,
) -> Decimal:
    if arm is EntryArm.NEXT_OPEN_CONTROL:
        return Decimal(entry_bar.open_price)
    if arm is EntryArm.CONF_BODY_MID:
        return _midpoint(
            confirmation.open_price,
            confirmation.close_price,
        )
    if arm is EntryArm.CONF_RANGE_MID:
        return _midpoint(
            confirmation.high_price,
            confirmation.low_price,
        )
    if arm is EntryArm.SOURCE_OPEN:
        return Decimal(source.open_price)
    raise ValueError(arm)


def _valid_risk(
    *,
    parent: ParentCrt,
    source: M15Bar,
    entry: Decimal,
) -> bool:
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        return Decimal(source.low_price) < entry
    return Decimal(source.high_price) > entry


def _touch_time(
    *,
    level: Decimal,
    entry_opened_at: datetime,
    c3_closed_at: datetime,
    m5_by_time: dict[datetime, Any],
) -> datetime | None:
    end = min(entry_opened_at + HORIZON, c3_closed_at)
    cursor = entry_opened_at
    while cursor < end:
        bar = m5_by_time.get(cursor)
        if bar is None:
            return None
        if Decimal(bar.low_price) <= level <= Decimal(bar.high_price):
            return cursor
        cursor += timedelta(minutes=5)
    return None


def _annual_key(opened_at: datetime) -> str:
    boundary = datetime(
        opened_at.year,
        9,
        21,
        tzinfo=opened_at.tzinfo,
    )
    year = opened_at.year if opened_at >= boundary else opened_at.year - 1
    return f"{year}_{year + 1}"


def run_census() -> dict[str, Any]:
    window = ValidationWindow(market=MARKET, start=START, end=END)
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    m5_by_time = {bar.opened_at: bar for bar in bars}
    parents = _rolling_parents(
        market=MARKET,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    counters: dict[EntryArm, Counter[str]] = {
        arm: Counter() for arm in EntryArm
    }
    annual: dict[EntryArm, dict[str, Counter[str]]] = {
        arm: defaultdict(Counter) for arm in EntryArm
    }
    diagnostics: Counter[str] = Counter()
    diagnostics["parent_count"] = len(parents)

    for parent in parents:
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if selected is None:
            diagnostics["no_selected_hypothesis"] += 1
            continue

        observation, confirmation, entry_bar = selected
        source = observation.group.source_candle
        year_key = _annual_key(entry_bar.opened_at)
        diagnostics["selected_opportunity"] += 1

        for arm in EntryArm:
            counter = counters[arm]
            year_counter = annual[arm][year_key]
            counter["opportunities"] += 1
            year_counter["opportunities"] += 1

            level = _level(
                arm=arm,
                source=source,
                confirmation=confirmation,
                entry_bar=entry_bar,
            )
            if not _valid_risk(
                parent=parent,
                source=source,
                entry=level,
            ):
                counter["invalid_structural_risk"] += 1
                year_counter["invalid_structural_risk"] += 1
                continue

            touched_at: datetime | None
            if arm is EntryArm.NEXT_OPEN_CONTROL:
                touched_at = entry_bar.opened_at
            else:
                touched_at = _touch_time(
                    level=level,
                    entry_opened_at=entry_bar.opened_at,
                    c3_closed_at=parent.c3_closed_at,
                    m5_by_time=m5_by_time,
                )

            if touched_at is None:
                counter["no_fill_within_30m"] += 1
                year_counter["no_fill_within_30m"] += 1
                continue

            counter["fills"] += 1
            year_counter["fills"] += 1
            minutes = int(
                (touched_at - entry_bar.opened_at).total_seconds() / 60
            )
            counter[f"fill_delay_min_{minutes}"] += 1
            year_counter[f"fill_delay_min_{minutes}"] += 1
            counter[f"timing_{parent.triplet}"] += 1
            year_counter[f"timing_{parent.triplet}"] += 1

    arms: dict[str, Any] = {}
    for arm in EntryArm:
        counter = counters[arm]
        opportunities = counter["opportunities"]
        fills = counter["fills"]
        annual_rows: dict[str, Any] = {}
        for year in range(START.year, END.year):
            key = f"{year}_{year + 1}"
            row = annual[arm].get(key, Counter())
            opp = row["opportunities"]
            fill = row["fills"]
            annual_rows[key] = {
                **dict(row),
                "fill_rate": (
                    0.0 if not opp else round(fill / opp, 8)
                ),
                "fills_per_year": fill,
            }
        arms[arm.value] = {
            **dict(counter),
            "fill_rate": (
                0.0 if not opportunities else round(fills / opportunities, 8)
            ),
            "fills_per_year": round(fills / YEARS, 8),
            "annual": annual_rows,
        }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": YEARS,
        "base_policy": BASE_POLICY.value,
        "fill_horizon_minutes": 30,
        "fill_resolution": "M5",
        "fill_rule": "OBSERVED_RANGE_TOUCH_ONLY",
        "structural_stop_geometry_must_remain_valid": True,
        "diagnostics": dict(diagnostics),
        "arms": arms,
        "pnl_evaluated": False,
        "entry_arm_promoted": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report = run_census()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print("CRT_R2BK_PASSIVE_CAPACITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
