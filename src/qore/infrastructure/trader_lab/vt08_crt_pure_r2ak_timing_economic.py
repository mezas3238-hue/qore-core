"""R2-AK economic characterization of the FX H4 timing lattice.

This lab is frozen before observing its outcomes.

Single changed dimension:
- CONTROL_NON_OVERLAP: existing 01/05/09 and 13/17/21 H4 triplets.
- ROLLING_H4: every consecutive H4 triplet on the 01/05/09/13/17/21 lattice.

Common contract:
- AUDUSD and USDJPY only;
- no EFF regime filter;
- same C1/C2/C3 structural semantics;
- same close-unmitigated Model #1 source builder;
- R2-G NEWEST_SUPERSEDES_CONFIRMATION_FIRST competition;
- max one selected hypothesis per parent;
- same structural source stop;
- same C1 midpoint target;
- same C3-close expiry;
- STOP_FIRST ambiguity.

The window is already-consumed research evidence (2020-2026). This lab cannot
certify or authorize deployment.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    FX_MARKETS,
    TimingLattice,
    _parents,
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

IDENTITY = "VT08_CRT_PURE_R2AK_H4_TIMING_ECONOMIC_001"
SCHEMA = "qore.vt08.crt_pure.r2ak_h4_timing_economic.v1"
START = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

YEAR_BOUNDARIES: tuple[datetime, ...] = tuple(
    datetime(year, 9, 21, 0, 0, tzinfo=UTC)
    for year in range(2020, 2027)
)


def _retag(
    trade: Model1LabTrade,
    *,
    lattice: TimingLattice,
) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{lattice.value}",
        market=trade.market,
        reference_policy=trade.reference_policy,
        reference_count=trade.reference_count,
        reference_ids=trade.reference_ids,
        parent_direction=trade.parent_direction,
        timing_triplet=trade.timing_triplet,
        c3_opened_at=trade.c3_opened_at,
        source_opened_at=trade.source_opened_at,
        confirmation_opened_at=trade.confirmation_opened_at,
        entry_opened_at=trade.entry_opened_at,
        entry_price_relative=trade.entry_price_relative,
        stop_price_relative=trade.stop_price_relative,
        target_price_relative=trade.target_price_relative,
        exit_price_relative=trade.exit_price_relative,
        exit_reason=trade.exit_reason,
        r_multiple=trade.r_multiple,
        research_only=True,
        promotion_forbidden_from_lab_pnl=True,
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


def _annual(rows: tuple[Model1LabTrade, ...]) -> dict[str, dict[str, Any]]:
    return {
        f"{left.year}_{right.year}": _summary(_window(rows, left, right))
        for left, right in zip(
            YEAR_BOUNDARIES[:-1],
            YEAR_BOUNDARIES[1:],
            strict=True,
        )
    }


def run_lab(
    market: CrtPureMarket,
) -> tuple[dict[TimingLattice, tuple[Model1LabTrade, ...]], dict[str, Any]]:
    if market not in FX_MARKETS:
        raise ValueError("R2-AK is FX-only")

    bars = load_m5_window(
        market,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=2),
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: dict[TimingLattice, list[Model1LabTrade]] = {
        lattice: [] for lattice in TimingLattice
    }
    diagnostics: dict[TimingLattice, dict[str, int]] = {
        lattice: defaultdict(int) for lattice in TimingLattice
    }

    for lattice in TimingLattice:
        parents = _parents(
            market=market,
            bars=bars,
            lattice=lattice,
        )
        diag = diagnostics[lattice]
        diag["parent_count"] = len(parents)

        for parent in parents:
            c3_m15 = _c3_m15(parent, m15_by_time)
            observations = _aligned_sources(
                parent=parent,
                c3_m15=c3_m15,
                breaches=breaches,
            )
            diag["source_event_count"] += len(observations)
            selected = select_competing_hypothesis(
                policy=BASE_POLICY,
                parent=parent,
                observations=observations,
                c3_m15=c3_m15,
            )
            if selected is None:
                diag["no_selected_hypothesis"] += 1
                continue

            diag["selected_hypothesis"] += 1
            observation, confirmation, entry = selected
            trade = _resolve_trade(
                parent=parent,
                group=observation.group,
                confirmation=confirmation,
                entry_bar=entry,
                c3_m15=c3_m15,
            )
            if trade is None:
                diag["invalid_midpoint_geometry"] += 1
                continue

            diag["trade_created"] += 1
            rows[lattice].append(_retag(trade, lattice=lattice))

    frozen = {
        lattice: tuple(sorted(trades, key=lambda item: item.entry_opened_at))
        for lattice, trades in rows.items()
    }

    lattices: dict[str, Any] = {}
    for lattice in TimingLattice:
        trades = frozen[lattice]
        annual = _annual(trades)
        lattices[lattice.value] = {
            "diagnostics": dict(diagnostics[lattice]),
            "full_6y": _summary(trades),
            "annual": annual,
            "trades_per_year": round(len(trades) / 6, 8),
            "positive_annual_windows": sum(
                float(summary["total_r"]) > 0
                for summary in annual.values()
            ),
        }

    control = lattices[TimingLattice.CONTROL_NON_OVERLAP.value]
    rolling = lattices[TimingLattice.ROLLING_H4.value]
    control_trades = int(control["full_6y"]["trades"])
    rolling_trades = int(rolling["full_6y"]["trades"])

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "efficiency_regime_filter": "OFF",
        "single_changed_dimension": "H4_TIMING_LATTICE",
        "same_stop_target_expiry": True,
        "one_selected_hypothesis_max_per_parent": True,
        "family_frozen_before_outcomes": [
            lattice.value for lattice in TimingLattice
        ],
        "lattices": lattices,
        "rolling_vs_control_trade_multiplier": (
            None
            if control_trades == 0
            else round(rolling_trades / control_trades, 8)
        ),
        "automatic_winner_selection": False,
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
    parser.add_argument("market", choices=[item.value for item in FX_MARKETS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    family, report = run_lab(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for lattice in TimingLattice:
            for trade in family[lattice]:
                row = asdict(trade)
                row["timing_lattice"] = lattice.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2AK_TIMING_ECONOMIC_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
