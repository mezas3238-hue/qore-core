"""R2-AQ historical validation of the high-density FX core.

Frozen after R2-AO, before older-window outcomes.

Candidate core:
- ROLLING_H4 timing lattice;
- FIXED_1_5R target;
- no EFF or context filter;
- one selected hypothesis max per parent;
- R2-G NEWEST_SUPERSEDES_CONFIRMATION_FIRST;
- source-candle structural stop;
- C3-close expiry;
- STOP_FIRST.

Validation windows are older than the 2020-2026 R2-AO development evidence:
- AUDUSD: 2016-09-21 -> 2020-09-21
- USDJPY: 2014-09-21 -> 2020-09-21

This is historical validation, not untouched final certification evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    _aggregate,
    _days,
    _segment,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    ParentCrt,
    _parent_direction,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    TimingLattice,
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
from qore.infrastructure.traders.crt_pure_timing_policy import NY

IDENTITY = "VT08_CRT_PURE_R2AQ_HIGH_DENSITY_HISTORICAL_VALIDATION_001"
SCHEMA = "qore.vt08.crt_pure.r2aq_high_density_historical_validation.v1"
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
LATTICE = TimingLattice.ROLLING_H4
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]


@dataclass(frozen=True, slots=True)
class ValidationWindow:
    market: CrtPureMarket
    start: datetime
    end: datetime


WINDOWS: dict[CrtPureMarket, ValidationWindow] = {
    CrtPureMarket.AUDUSD: ValidationWindow(
        market=CrtPureMarket.AUDUSD,
        start=datetime(2016, 9, 21, 0, 0, tzinfo=UTC),
        end=datetime(2020, 9, 21, 0, 0, tzinfo=UTC),
    ),
    CrtPureMarket.USDJPY: ValidationWindow(
        market=CrtPureMarket.USDJPY,
        start=datetime(2014, 9, 21, 0, 0, tzinfo=UTC),
        end=datetime(2020, 9, 21, 0, 0, tzinfo=UTC),
    ),
}


def _annual_boundaries(window: ValidationWindow) -> tuple[datetime, ...]:
    return tuple(
        datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        for year in range(window.start.year, window.end.year + 1)
    )


def _window(
    rows: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        row
        for row in rows
        if start <= datetime.fromisoformat(row.entry_opened_at) < end
    )


def _annual(
    rows: tuple[Model1LabTrade, ...],
    window: ValidationWindow,
) -> dict[str, dict[str, Any]]:
    boundaries = _annual_boundaries(window)
    return {
        f"{left.year}_{right.year}": _summary(_window(rows, left, right))
        for left, right in zip(
            boundaries[:-1],
            boundaries[1:],
            strict=True,
        )
    }


def _rolling_parents(
    *,
    market: CrtPureMarket,
    bars: tuple[Any, ...],
    window: ValidationWindow,
) -> tuple[ParentCrt, ...]:
    by_time = {bar.opened_at: bar for bar in bars}
    start_day = (window.start - timedelta(days=1)).astimezone(NY).date()
    end_day = window.end.astimezone(NY).date()
    parents: list[ParentCrt] = []

    for date_value in _days(start_day, end_day):
        for index, hour in enumerate((1, 5, 9, 13, 17, 21), start=1):
            c1_local = datetime(
                date_value.year,
                date_value.month,
                date_value.day,
                hour,
                tzinfo=NY,
            )
            c2_local = c1_local + timedelta(hours=4)
            c3_local = c1_local + timedelta(hours=8)
            close_local = c1_local + timedelta(hours=12)

            c1_open = c1_local.astimezone(UTC)
            c2_open = c2_local.astimezone(UTC)
            c3_open = c3_local.astimezone(UTC)
            close = close_local.astimezone(UTC)

            if not window.start <= c3_open < window.end:
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
                    triplet=f"ROLLING_H4:{index}",
                    c3_opened_at=c3_open,
                    c3_closed_at=close,
                    c1=c1,
                    c2=c2,
                    c3_m5=c3_m5,
                )
            )
    return tuple(parents)


def run_validation(
    market: CrtPureMarket,
) -> tuple[tuple[Model1LabTrade, ...], dict[str, Any]]:
    window = WINDOWS[market]
    bars = load_m5_window(
        market,
        start=window.start - timedelta(days=2),
        end_exclusive=window.end + timedelta(days=2),
    )
    parents = _rolling_parents(
        market=market,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: list[Model1LabTrade] = []
    diagnostics: dict[str, int] = {
        "parent_count": len(parents),
        "source_event_count": 0,
        "no_selected_hypothesis": 0,
        "selected_hypothesis": 0,
        "invalid_structural_geometry": 0,
        "trade_created": 0,
    }

    for parent in parents:
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        diagnostics["source_event_count"] += len(observations)
        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if selected is None:
            diagnostics["no_selected_hypothesis"] += 1
            continue

        diagnostics["selected_hypothesis"] += 1
        observation, confirmation, entry = selected
        trade = _resolve_fixed_target(
            arm=ARM,
            multiple=MULTIPLE,
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_structural_geometry"] += 1
            continue

        diagnostics["trade_created"] += 1
        rows.append(trade)

    frozen = tuple(sorted(rows, key=lambda item: item.entry_opened_at))
    annual = _annual(frozen, window)
    years = window.end.year - window.start.year
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "validation_start": window.start.isoformat(),
        "validation_end_exclusive": window.end.isoformat(),
        "years": years,
        "timing_lattice": LATTICE.value,
        "target_arm": ARM.value,
        "base_competition_policy": BASE_POLICY.value,
        "efficiency_regime_filter": "OFF",
        "historical_validation_frozen_before_outcomes": True,
        "diagnostics": diagnostics,
        "full_window": _summary(frozen),
        "annual": annual,
        "trades_per_year": round(len(frozen) / years, 8),
        "positive_annual_windows": sum(
            float(item["total_r"]) > 0 for item in annual.values()
        ),
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in WINDOWS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    trades, report = run_validation(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    print("CRT_R2AQ_HISTORICAL_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
