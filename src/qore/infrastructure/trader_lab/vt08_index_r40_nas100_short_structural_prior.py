"""VT08 Index R40 — stable NAS100-short structural risk prior.

R38 showed one high-sample market/side cohort with the same adverse sign in all
five exact 12-month development blocks: NAS100 SHORT (0/5 positive blocks under
the secondary -0.10R friction surface). R40 preregisters one bounded response:

- keep every source-complete structural event;
- preserve the frozen R34 formation + POI causal governor unchanged;
- attenuate only NAS100 SHORT assigned risk by 0.25;
- keep the strict 0.005R minimum;
- do not reallocate released risk to other trades;
- use no calendar/year label at runtime.

This is development evidence only. A passing 5Y result must be frozen before
any 2Y reproduction and may not be retuned from that reproduction.
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

SCHEMA = "qore.trader_lab.vt08_index_r40_nas100_short_structural_prior.v1"
IDENTITY = "VT08_INDEX_R40_NAS100_SHORT_STRUCTURAL_PRIOR_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")
NAS100_SHORT_MULTIPLIER = Decimal("0.25")

BASE_POI_OVERLAY = r34.PoiOverlayProfile(
    rolling_family_trades=10,
    min_observations=5,
    cold_multiplier=Decimal("0.50"),
    weak_multiplier=Decimal("0.50"),
    healthy_mean_threshold_r=Decimal("0.05"),
)


def _is_target(item: r15.AssignedTrade) -> bool:
    return item.symbol == "NAS100" and item.opportunity.signal.side.value == "short"


def _attenuated_weight(item: r15.AssignedTrade) -> Decimal:
    if not _is_target(item):
        return item.weight
    return max(MIN_EFFECTIVE_WEIGHT, item.weight * NAS100_SHORT_MULTIPLIER)


def _apply_structural_prior(
    assigned: tuple[r15.AssignedTrade, ...],
) -> tuple[tuple[r15.AssignedTrade, ...], dict[str, Any]]:
    adjusted: list[r15.AssignedTrade] = []
    target_count = 0
    reduced_count = 0
    before_target = Decimal()
    after_target = Decimal()

    for item in assigned:
        weight = _attenuated_weight(item)
        if _is_target(item):
            target_count += 1
            before_target += item.weight
            after_target += weight
            reduced_count += int(weight < item.weight)
        adjusted.append(replace(item, weight=weight))

    result = tuple(adjusted)
    if len(result) != len(assigned):
        raise ValueError("R40 changed source-complete trade count")
    if any(item.weight < MIN_EFFECTIVE_WEIGHT for item in result):
        raise ValueError("R40 violated minimum effective risk floor")

    return result, {
        "assigned_trade_count": len(result),
        "suppressed_trade_count": 0,
        "target_market_side": "NAS100|short",
        "target_trade_count": target_count,
        "risk_reduced_count": reduced_count,
        "target_weight_before_r": str(before_target),
        "target_weight_after_r": str(after_target),
        "minimum_effective_weight": str(min(item.weight for item in result)),
        "maximum_effective_weight": str(max(item.weight for item in result)),
        "mean_effective_weight": str(
            sum((item.weight for item in result), Decimal()) / len(result)
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
        raise ValueError(f"R40 density drift: {len(stream)}")

    _base_row, base_assigned = r34._row(
        stream,
        overlay=BASE_POI_OVERLAY,
    )
    assigned, diagnostics = _apply_structural_prior(base_assigned)

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
        "structural_prior": {
            "market": "NAS100",
            "side": "short",
            "multiplier": str(NAS100_SHORT_MULTIPLIER),
            "minimum_effective_weight": str(MIN_EFFECTIVE_WEIGHT),
            "released_risk_reallocated": False,
            "selection_basis": (
                "R38 exact-five-block development forensics: "
                "NAS100|short secondary sign negative in 5/5 blocks"
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
            "post_r38_preregistered_single_structural_prior": True,
            "optimization_grid_used": False,
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
