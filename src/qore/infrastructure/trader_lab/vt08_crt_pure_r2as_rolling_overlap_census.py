"""R2-AS rolling-H4 causal overlap census for VT08 CRT PURE FX.

Rolling H4 uses overlapping parent CRT windows. This census verifies that the
high-density count is not materially inflated by counting the same Model #1
event or same execution slot under multiple overlapping parents.

It regenerates the R2-AO FIXED_1_5R population and measures:
- raw trade count;
- unique exact causal hypothesis signature;
- unique source event signature;
- unique entry-time + direction slot;
- multiplicity distributions and collisions.

No trade is removed and no PnL is evaluated for promotion here. This is a
density-integrity audit only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
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

IDENTITY = "VT08_CRT_PURE_R2AS_ROLLING_CAUSAL_OVERLAP_CENSUS_001"
SCHEMA = "qore.vt08.crt_pure.r2as_rolling_causal_overlap_census.v1"
START = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
LATTICE = TimingLattice.ROLLING_H4
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]


@dataclass(frozen=True, slots=True)
class CausalTrade:
    trade: Model1LabTrade
    parent_c3_opened_at: str

    @property
    def exact_signature(self) -> tuple[Any, ...]:
        return (
            self.trade.parent_direction,
            self.trade.source_opened_at,
            self.trade.confirmation_opened_at,
            self.trade.entry_opened_at,
            self.trade.stop_price_relative,
            self.trade.reference_ids,
        )

    @property
    def source_signature(self) -> tuple[Any, ...]:
        return (
            self.trade.parent_direction,
            self.trade.source_opened_at,
            self.trade.reference_ids,
        )

    @property
    def entry_slot_signature(self) -> tuple[str, str]:
        return (
            self.trade.parent_direction,
            self.trade.entry_opened_at,
        )


def _multiplicity(values: tuple[tuple[Any, ...], ...]) -> dict[str, Any]:
    counts = Counter(values)
    histogram = Counter(counts.values())
    return {
        "unique": len(counts),
        "colliding_unique_keys": sum(value > 1 for value in counts.values()),
        "duplicate_rows": sum(value - 1 for value in counts.values()),
        "max_multiplicity": max(counts.values(), default=0),
        "multiplicity_histogram": {
            str(key): value for key, value in sorted(histogram.items())
        },
    }


def run_census(market: CrtPureMarket) -> dict[str, Any]:
    if market not in FX_MARKETS:
        raise ValueError("R2-AS is FX-only")

    bars = load_m5_window(
        market,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=2),
    )
    parents = _parents(market=market, bars=bars, lattice=LATTICE)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: list[CausalTrade] = []
    diagnostics: dict[str, int] = defaultdict(int)
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

        diagnostics["raw_trade_count"] += 1
        rows.append(
            CausalTrade(
                trade=trade,
                parent_c3_opened_at=parent.c3_opened_at.isoformat(),
            )
        )

    frozen = tuple(
        sorted(
            rows,
            key=lambda item: (
                item.trade.entry_opened_at,
                item.parent_c3_opened_at,
            ),
        )
    )
    exact = tuple(item.exact_signature for item in frozen)
    source = tuple(item.source_signature for item in frozen)
    entry = tuple(item.entry_slot_signature for item in frozen)

    exact_result = _multiplicity(exact)
    source_result = _multiplicity(source)
    entry_result = _multiplicity(entry)
    raw = len(frozen)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "timing_lattice": LATTICE.value,
        "target_arm": ARM.value,
        "base_competition_policy": BASE_POLICY.value,
        "diagnostics": dict(diagnostics),
        "raw_trades": raw,
        "raw_trades_per_year": round(raw / 6, 8),
        "exact_causal_signature": exact_result,
        "source_event_signature": source_result,
        "entry_slot_signature": entry_result,
        "unique_entry_slots_per_year": round(
            int(entry_result["unique"]) / 6,
            8,
        ),
        "entry_slot_retention_after_dedup": (
            None
            if raw == 0
            else round(int(entry_result["unique"]) / raw, 8)
        ),
        "pnl_evaluated": False,
        "dedup_policy_promoted": False,
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
    print("CRT_R2AS_OVERLAP_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
