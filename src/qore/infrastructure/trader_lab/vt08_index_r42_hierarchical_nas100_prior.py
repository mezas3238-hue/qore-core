"""VT08 Index R42 — preregistered hierarchical NAS100 structural prior.

Preregistered before R41 weighted-residual results are read.

R38 exact five-block raw forensics showed:
- NAS100 aggregate secondary sign negative in 4/5 blocks;
- NAS100 SHORT secondary sign negative in 5/5 blocks.

R40 applied a 0.25 multiplier only to NAS100 SHORT and improved the rejected
Y1 secondary result without passing it. R42 preserves that exact short total
multiplier but expresses it hierarchically:
- NAS100 market multiplier: 0.50
- additional NAS100 SHORT multiplier: 0.50
- therefore NAS100 SHORT total multiplier: 0.25

No signal is removed, released risk is not reallocated, and calendar/year
labels are unavailable to runtime.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r6_5y_failure_forensics as fx,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r15_concurrent_portfolio_validation as r15,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r34_hybrid_formation_poi_health as r34,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as r35,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r40_nas100_short_structural_prior as r40,
)

SCHEMA = "qore.trader_lab.vt08_index_r42_hierarchical_nas100_prior.v1"
IDENTITY = "VT08_INDEX_R42_HIERARCHICAL_NAS100_PRIOR_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")

NAS100_MARKET_MULTIPLIER = Decimal("0.50")
NAS100_SHORT_EXTRA_MULTIPLIER = Decimal("0.50")
NAS100_SHORT_TOTAL_MULTIPLIER = (
    NAS100_MARKET_MULTIPLIER * NAS100_SHORT_EXTRA_MULTIPLIER
)

BASE_POI_OVERLAY = r40.BASE_POI_OVERLAY


def _hierarchical_weight(item: r15.AssignedTrade) -> Decimal:
    weight = item.weight
    if item.symbol != "NAS100":
        return weight
    weight *= NAS100_MARKET_MULTIPLIER
    if item.opportunity.signal.side.value == "short":
        weight *= NAS100_SHORT_EXTRA_MULTIPLIER
    return max(MIN_EFFECTIVE_WEIGHT, weight)


def _apply_prior(
    assigned: tuple[r15.AssignedTrade, ...],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    result: list[r15.AssignedTrade] = []
    market_count = 0
    short_count = 0
    reduced_count = 0
    nas_before = Decimal()
    nas_after = Decimal()
    short_before = Decimal()
    short_after = Decimal()

    for item in assigned:
        weight = _hierarchical_weight(item)
        if item.symbol == "NAS100":
            market_count += 1
            nas_before += item.weight
            nas_after += weight
            if item.opportunity.signal.side.value == "short":
                short_count += 1
                short_before += item.weight
                short_after += weight
            reduced_count += int(weight < item.weight)
        result.append(replace(item, weight=weight))

    adjusted = tuple(result)
    if len(adjusted) != len(assigned):
        raise ValueError("R42 changed source-complete trade count")
    if any(item.weight < MIN_EFFECTIVE_WEIGHT for item in adjusted):
        raise ValueError("R42 violated minimum effective risk floor")

    return adjusted, {
        "assigned_trade_count": len(adjusted),
        "suppressed_trade_count": 0,
        "nas100_trade_count": market_count,
        "nas100_short_trade_count": short_count,
        "risk_reduced_count": reduced_count,
        "nas100_weight_before_r": str(nas_before),
        "nas100_weight_after_r": str(nas_after),
        "nas100_short_weight_before_r": str(short_before),
        "nas100_short_weight_after_r": str(short_after),
        "minimum_effective_weight": str(
            min(item.weight for item in adjusted)
        ),
        "maximum_effective_weight": str(
            max(item.weight for item in adjusted)
        ),
        "mean_effective_weight": str(
            sum((item.weight for item in adjusted), Decimal())
            / len(adjusted)
        ),
        "released_risk_reallocated": False,
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
    stream, bars_by_symbol, opened_by_symbol, provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"R42 density drift: {len(stream)}")

    _base_row, base_assigned = r34._row(
        stream,
        overlay=BASE_POI_OVERLAY,
    )
    assigned, diagnostics = _apply_prior(base_assigned)

    primary = fx._metrics(
        r15._realized_values(assigned, stress=PRIMARY_STRESS)
    )
    secondary = fx._metrics(
        r15._realized_values(assigned, stress=SECONDARY_STRESS)
    )
    primary_blocks = r35._five_full_year_blocks(
        assigned,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = r35._five_full_year_blocks(
        assigned,
        stress=SECONDARY_STRESS,
    )
    primary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=PRIMARY_STRESS,
        adverse=True,
    )
    secondary_mtm = r15._portfolio_mark_to_market(
        assigned,
        bars_by_symbol=bars_by_symbol,
        opened_by_symbol=opened_by_symbol,
        stress=SECONDARY_STRESS,
        adverse=True,
    )

    raw_primary = r31._raw_metrics(stream, stress=PRIMARY_STRESS)
    raw_edge_pass = (
        Decimal(str(raw_primary["profit_factor"] or "0")) >= Decimal("1")
        and Decimal(str(raw_primary["total_r"])) > 0
    )
    all_primary = r35._all_blocks_positive(primary_blocks)
    all_secondary = r35._all_blocks_positive(secondary_blocks)

    goal_pass = (
        raw_edge_pass
        and contract.validates_trade_count(years=5, sample=len(assigned))
        and Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
        and Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
        and Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
        and Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
        and all_primary
        and all_secondary
        and int(diagnostics["suppressed_trade_count"]) == 0
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(assigned),
        "hierarchical_prior": {
            "nas100_market_multiplier": str(NAS100_MARKET_MULTIPLIER),
            "nas100_short_extra_multiplier": str(
                NAS100_SHORT_EXTRA_MULTIPLIER
            ),
            "nas100_short_total_multiplier": str(
                NAS100_SHORT_TOTAL_MULTIPLIER
            ),
            "minimum_effective_weight": str(MIN_EFFECTIVE_WEIGHT),
            "released_risk_reallocated": False,
            "selection_basis": (
                "R38 preregistration: NAS100 negative 4/5 exact blocks; "
                "NAS100|short negative 5/5 exact blocks"
            ),
        },
        "base_poi_overlay": BASE_POI_OVERLAY.payload(),
        "raw_primary": raw_primary,
        "raw_edge_pass": raw_edge_pass,
        "primary": primary,
        "secondary": secondary,
        "primary_conservative_mark_to_market": primary_mtm,
        "secondary_conservative_mark_to_market": secondary_mtm,
        "five_year_blocks_primary": primary_blocks,
        "five_year_blocks_secondary": secondary_blocks,
        "all_five_primary_blocks_positive": all_primary,
        "all_five_secondary_blocks_positive": all_secondary,
        "goal_pass": goal_pass,
        "diagnostics": diagnostics,
        "contract": {
            "five_year_trade_range": list(contract.FIVE_YEAR_TRADE_RANGE),
            "two_year_min_trades": contract.TWO_YEAR_MIN_TRADES,
            "primary_pf_minimum": str(PF_PRIMARY_MIN),
            "secondary_pf_minimum": str(PF_SECONDARY_MIN),
            "portfolio_dd_max_r": str(PORTFOLIO_DD_MAX),
            "five_full_blocks_positive_both_stresses": True,
            "all_signals_preserved": True,
        },
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "consumed_window": True,
            "fresh_holdout_claim": False,
            "preregistered_before_r41_result": True,
            "optimization_grid_used": False,
            "r40_short_total_multiplier_preserved": True,
            "calendar_or_year_feature_used_for_runtime": False,
            "trade_suppression_allowed": False,
            "zero_risk_allowed": False,
            "released_risk_reallocated": False,
            "all_structural_signals_preserved": True,
            "candidate_frozen": False,
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
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "sample": report["sample"],
                "goal_pass": report["goal_pass"],
                "primary": report["primary"],
                "secondary": report["secondary"],
                "primary_mtm": report["primary_conservative_mark_to_market"],
                "secondary_mtm": report["secondary_conservative_mark_to_market"],
                "five_year_blocks_primary": report["five_year_blocks_primary"],
                "five_year_blocks_secondary": report["five_year_blocks_secondary"],
                "diagnostics": report["diagnostics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
