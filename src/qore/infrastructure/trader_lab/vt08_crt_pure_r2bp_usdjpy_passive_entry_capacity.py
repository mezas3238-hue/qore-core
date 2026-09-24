"""R2-BP USDJPY market-specific passive-entry capacity census.

R2-BN failed to create positive expectancy from small Expected-R memories.
This lab therefore opens the predeclared second line: improve entry price.

No AUDUSD passive arm is imported. USDJPY gets its own predeclared structural
risk-retracement family. Each level moves from the current next-M15-open decision
price toward the source-candle structural stop by a fixed fraction of the
original structural risk:

- RISK_RETRACE_025
- RISK_RETRACE_050
- RISK_RETRACE_075

This is capacity only: observed M5 touch within 30 minutes, with pending-order
invalidation if the original stop is touched before fill. No PnL is evaluated.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import timedelta
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bl_usdjpy_pf_root_cause import (
    BASE_POLICY,
    END,
    MARKET,
    START,
    YEARS,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2BP_USDJPY_PASSIVE_ENTRY_CAPACITY_001"
SCHEMA = "qore.vt08.crt_pure.r2bp_usdjpy_passive_entry_capacity.v1"
HORIZON = timedelta(minutes=30)


class EntryArm(StrEnum):
    NEXT_OPEN_CONTROL = "NEXT_OPEN_CONTROL"
    RISK_RETRACE_025 = "RISK_RETRACE_025"
    RISK_RETRACE_050 = "RISK_RETRACE_050"
    RISK_RETRACE_075 = "RISK_RETRACE_075"


RETRACE_FRACTION: dict[EntryArm, Decimal] = {
    EntryArm.RISK_RETRACE_025: Decimal("0.25"),
    EntryArm.RISK_RETRACE_050: Decimal("0.50"),
    EntryArm.RISK_RETRACE_075: Decimal("0.75"),
}


def _stop(
    *,
    parent: ParentCrt,
    source: M15Bar,
) -> Decimal:
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        return Decimal(source.low_price)
    return Decimal(source.high_price)


def _level(
    *,
    arm: EntryArm,
    parent: ParentCrt,
    source: M15Bar,
    decision_bar: M15Bar,
) -> Decimal:
    entry = Decimal(decision_bar.open_price)
    if arm is EntryArm.NEXT_OPEN_CONTROL:
        return entry
    stop = _stop(parent=parent, source=source)
    fraction = RETRACE_FRACTION[arm]
    return entry + fraction * (stop - entry)


def _valid_risk(
    *,
    parent: ParentCrt,
    stop: Decimal,
    level: Decimal,
) -> bool:
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        return stop < level
    return stop > level


def _stop_touched(
    *,
    parent: ParentCrt,
    stop: Decimal,
    bar: Any,
) -> bool:
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        return Decimal(bar.low_price) <= stop
    return Decimal(bar.high_price) >= stop


def _fill_state(
    *,
    arm: EntryArm,
    parent: ParentCrt,
    level: Decimal,
    stop: Decimal,
    decision_at: Any,
    c3_closed_at: Any,
    m5_by_time: dict[Any, Any],
) -> tuple[Any | None, str]:
    if arm is EntryArm.NEXT_OPEN_CONTROL:
        return decision_at, "CONTROL"

    end = min(decision_at + HORIZON, c3_closed_at)
    cursor = decision_at
    while cursor < end:
        bar = m5_by_time.get(cursor)
        if bar is None:
            return None, "MISSING_M5"
        level_touched = Decimal(bar.low_price) <= level <= Decimal(bar.high_price)
        stop_touched = _stop_touched(
            parent=parent,
            stop=stop,
            bar=bar,
        )
        if level_touched:
            return (
                cursor,
                "FILL_AND_STOP_SAME_M5" if stop_touched else "FILL",
            )
        if stop_touched:
            return None, "STOP_INVALIDATED_BEFORE_FILL"
        cursor += timedelta(minutes=5)
    return None, "NO_FILL_WITHIN_30M"


def _annual_key(opened_at: Any) -> str:
    boundary = opened_at.replace(
        month=9,
        day=21,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
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

        observation, _, decision_bar = selected
        source = observation.group.source_candle
        stop = _stop(parent=parent, source=source)
        year_key = _annual_key(decision_bar.opened_at)
        diagnostics["selected_opportunity"] += 1

        for arm in EntryArm:
            counter = counters[arm]
            year_counter = annual[arm][year_key]
            counter["opportunities"] += 1
            year_counter["opportunities"] += 1

            level = _level(
                arm=arm,
                parent=parent,
                source=source,
                decision_bar=decision_bar,
            )
            if not _valid_risk(
                parent=parent,
                stop=stop,
                level=level,
            ):
                counter["invalid_structural_risk"] += 1
                year_counter["invalid_structural_risk"] += 1
                continue

            filled_at, state = _fill_state(
                arm=arm,
                parent=parent,
                level=level,
                stop=stop,
                decision_at=decision_bar.opened_at,
                c3_closed_at=parent.c3_closed_at,
                m5_by_time=m5_by_time,
            )
            counter[state] += 1
            year_counter[state] += 1
            if filled_at is None:
                continue

            counter["fills"] += 1
            year_counter["fills"] += 1
            delay = int(
                (filled_at - decision_bar.opened_at).total_seconds() / 60
            )
            counter[f"fill_delay_min_{delay}"] += 1
            year_counter[f"fill_delay_min_{delay}"] += 1

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
                "fill_rate": 0.0 if not opp else round(fill / opp, 8),
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
        "level_family": "USDJPY_STRUCTURAL_RISK_RETRACEMENT",
        "arms_frozen_before_results": [arm.value for arm in EntryArm],
        "audusd_entry_arm_transferred": False,
        "fill_horizon_minutes": int(HORIZON.total_seconds() / 60),
        "fill_resolution": "M5",
        "fill_rule": "OBSERVED_RANGE_TOUCH_ONLY",
        "pre_fill_stop_invalidation": True,
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
    print("CRT_R2BP_USDJPY_PASSIVE_CAPACITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
