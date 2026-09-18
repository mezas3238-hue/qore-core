"""VT08 Index R25 — density reconstitution forensics under Owner Contract V2.

This is a census/forensics stage, not an economic candidate and not a target
optimization round.

Owner Contract V2:
- 5Y: 2,300-2,500 trades across NAS100/SP500/US30.
- 2Y: at least 1,000 trades.
- portfolio drawdown target/ceiling: around 6R / max 6R.
- three markets remain independently concurrent.

R25 asks where valid VT08 density exists before any new rule is invented:
1) R8 source-priority POI + structural rearm surface;
2) source-complete FVG/relevant-swing/CISD + structural rearm surface;
3) the number of source-complete signals lost only because one-active-position
   per symbol keeps later valid structural events from being admitted.

The target grid below is a lifecycle occupancy diagnostic only. It MUST NOT be
ranked or selected by PnL in this stage.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as r6
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r25_density_reconstitution_forensics.v1"
IDENTITY = "VT08_INDEX_R25_DENSITY_RECONSTITUTION_FORENSICS_001"
DIAGNOSTIC_TARGETS = (
    Decimal("1.5"),
    Decimal("2.0"),
    Decimal("2.5"),
    Decimal("3.0"),
)


def _sequential_count(
    opportunities: Sequence[Any],
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    target: Decimal,
) -> int:
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
    policy = r8._target_policy(target)
    candidates = [
        (
            item,
            r5._manage_trade(
                item.signal,
                bars=bars,
                opened=opened,
                policy=policy,
            ),
        )
        for item in opportunities
    ]
    count = 0
    last_exit: datetime | None = None
    for opportunity, outcome in sorted(
        candidates,
        key=lambda item: (
            item[0].signal.signal_at,
            item[0].signal.symbol,
            item[0].signal.entry,
            item[0].signal.stop,
        ),
    ):
        if last_exit is not None and opportunity.signal.signal_at < last_exit:
            continue
        count += 1
        last_exit = outcome.exited_at
    return count


def _surface_summary(opportunities: Sequence[Any]) -> dict[str, Any]:
    poi = Counter(item.source_poi_kind for item in opportunities)
    rearm = sum(int(item.rearm_index) > 0 for item in opportunities)
    initial = len(opportunities) - rearm
    unique_identity_count = len({item.identity() for item in opportunities})
    return {
        "count": len(opportunities),
        "unique_identity_count": unique_identity_count,
        "initial_count": initial,
        "rearm_count": rearm,
        "by_poi": dict(sorted(poi.items())),
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    by_market: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    all_source_complete: list[Any] = []
    all_priority: list[Any] = []

    for symbol in contract.MARKETS:
        bars, source = r6._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        source_complete = r6._build_surface_5y(symbol=symbol, bars=bars)
        priority = r8._opportunities(symbol=symbol, bars=bars)

        lifecycle_counts = {
            str(target): _sequential_count(
                source_complete,
                bars=bars,
                target=target,
            )
            for target in DIAGNOSTIC_TARGETS
        }
        priority_lifecycle_counts = {
            str(target): _sequential_count(
                priority,
                bars=bars,
                target=target,
            )
            for target in DIAGNOSTIC_TARGETS
        }

        by_market[symbol] = {
            "source_complete": _surface_summary(source_complete),
            "source_priority": _surface_summary(priority),
            "source_complete_one_active_per_symbol_by_target": lifecycle_counts,
            "source_priority_one_active_per_symbol_by_target": (
                priority_lifecycle_counts
            ),
        }
        provenance[symbol] = source
        all_source_complete.extend(source_complete)
        all_priority.extend(priority)

    source_complete_total = len(all_source_complete)
    priority_total = len(all_priority)
    source_complete_by_target = {
        str(target): sum(
            int(
                by_market[symbol][
                    "source_complete_one_active_per_symbol_by_target"
                ][str(target)]
            )
            for symbol in contract.MARKETS
        )
        for target in DIAGNOSTIC_TARGETS
    }
    priority_by_target = {
        str(target): sum(
            int(
                by_market[symbol][
                    "source_priority_one_active_per_symbol_by_target"
                ][str(target)]
            )
            for symbol in contract.MARKETS
        )
        for target in DIAGNOSTIC_TARGETS
    }

    target_low, target_high = contract.FIVE_YEAR_TRADE_RANGE
    raw_surface_in_target = target_low <= source_complete_total <= target_high
    diagnostic_lifecycle_in_target = {
        target: target_low <= count <= target_high
        for target, count in source_complete_by_target.items()
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "owner_contract": {
            "contract_id": contract.CONTRACT_ID,
            "five_year_trade_range": list(contract.FIVE_YEAR_TRADE_RANGE),
            "two_year_min_trades": contract.TWO_YEAR_MIN_TRADES,
            "portfolio_max_drawdown_r": str(contract.PORTFOLIO_MAX_DRAWDOWN_R),
            "markets": list(contract.MARKETS),
            "cross_market_concurrency_required": (
                contract.CROSS_MARKET_CONCURRENCY_REQUIRED
            ),
        },
        "window": {
            "start_date": r6.START_DATE.isoformat(),
            "end_date_exclusive": r6.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_DEVELOPMENT_FORENSICS",
            "fresh_holdout_claim": False,
        },
        "source_complete_raw_surface_count": source_complete_total,
        "source_priority_raw_surface_count": priority_total,
        "source_complete_raw_surface_in_5y_target": raw_surface_in_target,
        "source_complete_one_active_per_symbol_by_target": (
            source_complete_by_target
        ),
        "source_priority_one_active_per_symbol_by_target": priority_by_target,
        "source_complete_lifecycle_density_pass_by_target": (
            diagnostic_lifecycle_in_target
        ),
        "by_market": by_market,
        "provenance": provenance,
        "interpretation_contract": {
            "target_grid_is_occupancy_diagnostic_only": True,
            "target_grid_may_not_be_ranked_by_pnl": True,
            "no_economic_candidate_selected": True,
            "no_signal_filter_added": True,
            "no_market_removed": True,
            "no_side_removed": True,
            "structural_rearm_preserved": True,
            "source_pois": ["fvg", "relevant-swing", "cisd"],
        },
        "governance": {
            "development_only": True,
            "consumed_window": True,
            "fresh_holdout_claim": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
