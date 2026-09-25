"""R2-AH long-window density attribution for VT08 CRT PURE.

This lab measures where opportunity density is lost. It does not invent a new
entry model or promote a filter.

For AUDUSD and USDJPY it compares:
- parent CRT count;
- available pre-parent context;
- parent with at least one aligned Model #1 source;
- selected confirmed hypothesis under frozen R2-G competition;
- valid structural-risk / midpoint geometry;
- current frozen efficiency-regime pass;
- current regime + selected hypothesis + valid geometry.

It also reports the economic summary of the unfiltered valid-geometry population
versus the current regime-filtered population so density can be recovered without
blindly discarding edge.

Research only. No execution/capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _resolve_trade,
    _summary,
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
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2q_usdjpy_multi_regime_atlas import (
    _context,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AH_LONG_WINDOW_DENSITY_ATTRIBUTION_001"
SCHEMA = "qore.vt08.crt_pure.r2ah_long_window_density_attribution.v1"
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


@dataclass(frozen=True, slots=True)
class MarketConfig:
    market: CrtPureMarket
    start: datetime
    efficiency_index: int
    efficiency_low: Decimal
    efficiency_high: Decimal


CONFIGS: dict[CrtPureMarket, MarketConfig] = {
    CrtPureMarket.AUDUSD: MarketConfig(
        market=CrtPureMarket.AUDUSD,
        start=datetime(2016, 9, 21, 0, 0, tzinfo=UTC),
        efficiency_index=2,
        efficiency_low=Decimal("0.10"),
        efficiency_high=Decimal("0.20"),
    ),
    CrtPureMarket.USDJPY: MarketConfig(
        market=CrtPureMarket.USDJPY,
        start=datetime(2014, 9, 21, 0, 0, tzinfo=UTC),
        efficiency_index=3,
        efficiency_low=Decimal("0.10"),
        efficiency_high=Decimal("0.20"),
    ),
}


def _annual_boundaries(start: datetime) -> tuple[datetime, ...]:
    return tuple(
        datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        for year in range(start.year, END.year + 1)
    )


def _annual_count(
    rows: tuple[Model1LabTrade, ...],
    start: datetime,
) -> dict[str, int]:
    boundaries = _annual_boundaries(start)
    return {
        f"{left.year}_{right.year}": sum(
            left <= datetime.fromisoformat(row.entry_opened_at) < right
            for row in rows
        )
        for left, right in zip(
            boundaries[:-1],
            boundaries[1:],
            strict=True,
        )
    }


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 8)


def run_density(
    market: CrtPureMarket,
) -> tuple[
    tuple[Model1LabTrade, ...],
    tuple[Model1LabTrade, ...],
    dict[str, Any],
]:
    config = CONFIGS[market]
    fetch_start = config.start - timedelta(days=25)
    bars = load_m5_window(market, start=fetch_start, end_exclusive=END)
    parents = build_parent_crts_for_window(
        market,
        bars,
        start=config.start,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    diagnostics: dict[str, int] = defaultdict(int)
    unfiltered: list[Model1LabTrade] = []
    regime_filtered: list[Model1LabTrade] = []

    for parent in parents:
        diagnostics["parent_count"] += 1

        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        if observations:
            diagnostics["parent_with_aligned_source"] += 1
            diagnostics["aligned_source_event_count"] += len(observations)

        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        unfiltered_trade: Model1LabTrade | None = None
        if selected is not None:
            diagnostics["selected_confirmed_hypothesis"] += 1
            observation, confirmation, entry = selected
            unfiltered_trade = _resolve_trade(
                parent=parent,
                group=observation.group,
                confirmation=confirmation,
                entry_bar=entry,
                c3_m15=c3_m15,
            )
            if unfiltered_trade is not None:
                diagnostics["unfiltered_valid_geometry"] += 1
                unfiltered.append(unfiltered_trade)
            else:
                diagnostics["unfiltered_geometry_rejected"] += 1
        else:
            diagnostics["no_selected_confirmed_hypothesis"] += 1

        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_context"] += 1
            continue
        diagnostics["context_available"] += 1

        efficiency = context[config.efficiency_index]
        if not isinstance(efficiency, Decimal):
            raise TypeError(
                "configured efficiency index did not resolve to Decimal"
            )
        regime_pass = (
            config.efficiency_low
            <= efficiency
            < config.efficiency_high
        )
        if not regime_pass:
            diagnostics["regime_rejected_parent"] += 1
            if unfiltered_trade is not None:
                diagnostics["recoverable_valid_trade_rejected_by_regime"] += 1
            continue

        diagnostics["regime_pass_parent"] += 1
        if observations:
            diagnostics["regime_pass_with_source"] += 1
        if selected is not None:
            diagnostics["regime_pass_selected_hypothesis"] += 1
        if unfiltered_trade is not None:
            diagnostics["regime_pass_valid_geometry"] += 1
            regime_filtered.append(unfiltered_trade)

    unfiltered_frozen = tuple(
        sorted(unfiltered, key=lambda item: item.entry_opened_at)
    )
    regime_frozen = tuple(
        sorted(regime_filtered, key=lambda item: item.entry_opened_at)
    )
    parents_count = diagnostics["parent_count"]
    unfiltered_count = len(unfiltered_frozen)
    regime_count = len(regime_frozen)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "window_start": config.start.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": END.year - config.start.year,
        "base_competition_policy": BASE_POLICY.value,
        "current_efficiency_bounds": [
            str(config.efficiency_low),
            str(config.efficiency_high),
        ],
        "current_efficiency_context_index": config.efficiency_index,
        "diagnostics": dict(diagnostics),
        "retention": {
            "parents_to_aligned_source": _rate(
                diagnostics["parent_with_aligned_source"],
                parents_count,
            ),
            "parents_to_selected_hypothesis": _rate(
                diagnostics["selected_confirmed_hypothesis"],
                parents_count,
            ),
            "parents_to_unfiltered_valid_trade": _rate(
                unfiltered_count,
                parents_count,
            ),
            "parents_to_regime_filtered_trade": _rate(
                regime_count,
                parents_count,
            ),
            "unfiltered_trade_retained_by_regime": _rate(
                regime_count,
                unfiltered_count,
            ),
            "unfiltered_trade_rejected_by_regime": _rate(
                diagnostics["recoverable_valid_trade_rejected_by_regime"],
                unfiltered_count,
            ),
        },
        "unfiltered_population": {
            "summary": _summary(unfiltered_frozen),
            "annual_trade_count": _annual_count(
                unfiltered_frozen,
                config.start,
            ),
            "trades_per_year": round(
                unfiltered_count / (END.year - config.start.year),
                8,
            ),
        },
        "current_regime_population": {
            "summary": _summary(regime_frozen),
            "annual_trade_count": _annual_count(
                regime_frozen,
                config.start,
            ),
            "trades_per_year": round(
                regime_count / (END.year - config.start.year),
                8,
            ),
        },
        "single_question": "WHERE_DENSITY_IS_LOST",
        "methodology_mutated": False,
        "filter_promoted": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return unfiltered_frozen, regime_frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in CONFIGS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    unfiltered, regime, report = run_density(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for population, rows in (
            ("UNFILTERED", unfiltered),
            ("REGIME_FILTERED", regime),
        ):
            for trade in rows:
                payload = {
                    "population": population,
                    "entry_opened_at": trade.entry_opened_at,
                    "r_multiple": trade.r_multiple,
                    "direction": trade.parent_direction,
                    "triplet": trade.timing_triplet,
                    "reference_count": trade.reference_count,
                }
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
    print("CRT_R2AH_DENSITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
