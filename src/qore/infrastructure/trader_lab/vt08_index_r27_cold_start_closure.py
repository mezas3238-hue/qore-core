"""VT08 Index R27 — bounded formation cold-start closure.

R26 reduced conservative portfolio DD below 3R while preserving all 1,574
signals, but the partial 2018 segment remained slightly negative. R26 also
showed that increasing cold-start confidence worsened that segment materially.

R27 changes one thing only: the non-zero capital multiplier used before a high
weight A/B formation has accumulated enough own completed experience.
Everything else is fixed to the R26 best causal identity.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r24_open_position_pressure as r24
from qore.infrastructure.trader_lab import vt08_index_r26_formation_health_governor as r26

SCHEMA = "qore.trader_lab.vt08_index_r27_cold_start_closure.v1"
IDENTITY = "VT08_INDEX_R27_COLD_START_CLOSURE_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")


def _profiles() -> tuple[r26.FormationHealthProfile, ...]:
    return tuple(
        r26.FormationHealthProfile(
            rolling_tier_trades=6,
            min_observations=minimum,
            cold_multiplier=cold,
            weak_multiplier=Decimal("0.05"),
            healthy_mean_threshold_r=Decimal("0.00"),
        )
        for minimum in (3, 5)
        for cold in (
            Decimal("0.025"),
            Decimal("0.050"),
            Decimal("0.075"),
            Decimal("0.100"),
        )
    )


def _rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal]:
    return (
        int(bool(row["goal_pass"])),
        int(row["positive_primary_years"]),
        -max(
            Decimal(row["primary_conservative_mark_to_market"]["max_drawdown_r"]),
            Decimal(row["secondary_conservative_mark_to_market"]["max_drawdown_r"]),
        ),
        Decimal(str(row["primary"]["profit_factor"] or "0")),
    )


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
    (
        stream,
        bars_by_symbol,
        _indexed,
        opened_by_symbol,
        provenance,
    ) = r15._build_five_year_stream(roots=roots)
    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"R27 density drift: {len(stream)}")

    rows: list[dict[str, Any]] = []
    for profile in _profiles():
        row, assigned = r26._row(stream, profile=profile)
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
        primary = row["primary"]
        secondary = row["secondary"]
        diagnostics = row["diagnostics"]
        goal_pass = (
            len(assigned) == len(stream)
            and int(diagnostics["suppressed_trade_count"]) == 0
            and int(diagnostics["max_concurrent_open_positions"]) >= 2
            and Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
            and Decimal(str(secondary["profit_factor"] or "0")) >= PF_SECONDARY_MIN
            and Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and bool(row["all_primary_years_positive"])
        )
        final = dict(row)
        final["primary_conservative_mark_to_market"] = primary_mtm
        final["secondary_conservative_mark_to_market"] = secondary_mtm
        final["goal_pass"] = goal_pass
        rows.append(final)

    rows.sort(key=_rank, reverse=True)
    goals = [row for row in rows if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(stream),
        "profile_count": len(_profiles()),
        "goal_candidate_count": len(goals),
        "fixed_r26_identity": {
            "rolling_tier_trades": 6,
            "weak_multiplier": "0.05",
            "healthy_mean_threshold_r": "0.00",
            "adaptive_tiers": list(r26.ADAPTIVE_TIERS),
            "quality_base": r24.BASE_QUALITY.payload(),
            "global_risk": r24.BASE_RISK.payload(),
        },
        "best": rows[0],
        "all_profiles": rows,
        "goal_candidates": goals,
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "bounded_single_dimension_refinement": "formation_cold_start_confidence",
            "calendar_or_year_feature_used": False,
            "future_outcome_used_for_current_authorization": False,
            "all_trades_preserved": True,
            "cross_market_concurrency_preserved": True,
            "signal_suppression_allowed": False,
            "zero_risk_allowed": False,
            "five_year_window_consumed": True,
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
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "sample": report["sample"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
