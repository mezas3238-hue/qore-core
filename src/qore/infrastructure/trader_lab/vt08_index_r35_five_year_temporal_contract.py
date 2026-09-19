"""VT08 Index R35 — exact five-year temporal contract correction.

The consumed development window is exactly:
    2018-09-15 <= trade time < 2023-09-15

Prior R31-R34 diagnostics reported calendar-year buckets, which creates two
partial edge buckets (2018 and 2023) and therefore six labels for a five-year
window. The Owner contract requires five consecutive years of stability.

R35 changes no trading rule and introduces no new optimization dimension.
It re-evaluates the already preregistered R34 profile family using exactly five
consecutive 12-month blocks anchored to the frozen window start:

Y1 2018-09-15 .. 2019-09-15
Y2 2019-09-15 .. 2020-09-15
Y3 2020-09-15 .. 2021-09-15
Y4 2021-09-15 .. 2022-09-15
Y5 2022-09-15 .. 2023-09-15

Calendar year is never used by runtime decisions; this is evaluation only.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as r6
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import vt08_index_r34_hybrid_formation_poi_health as r34

SCHEMA = "qore.trader_lab.vt08_index_r35_five_year_temporal_contract.v1"
IDENTITY = "VT08_INDEX_R35_FIVE_YEAR_TEMPORAL_CONTRACT_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")


def _annual_boundaries() -> tuple[date, ...]:
    start = r6.START_DATE
    return tuple(
        date(start.year + offset, start.month, start.day)
        for offset in range(6)
    )


def _five_full_year_blocks(
    assigned: tuple[r15.AssignedTrade, ...],
    *,
    stress: Decimal,
) -> dict[str, dict[str, Any]]:
    boundaries = _annual_boundaries()
    result: dict[str, dict[str, Any]] = {}
    for index in range(5):
        start = boundaries[index]
        end = boundaries[index + 1]
        items = sorted(
            (
                item
                for item in assigned
                if start <= item.exited_at.date() < end
            ),
            key=lambda item: (item.exited_at, item.symbol, item.trade_id),
        )
        values = tuple(
            (item.outcome.r_multiple - stress) * item.weight
            for item in items
        )
        metrics = fx._metrics(values)
        result[f"Y{index + 1}"] = {
            "start_date": start.isoformat(),
            "end_date_exclusive": end.isoformat(),
            **metrics,
        }
    return result


def _all_blocks_positive(blocks: dict[str, dict[str, Any]]) -> bool:
    return len(blocks) == 5 and all(
        int(block["sample"]) > 0 and Decimal(str(block["total_r"])) > 0
        for block in blocks.values()
    )


def _row(
    stream: tuple[tuple[Any, Any], ...],
    *,
    profile: r34.PoiOverlayProfile,
) -> tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]:
    base, assigned = r34._row(stream, overlay=profile)
    primary_blocks = _five_full_year_blocks(
        assigned,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = _five_full_year_blocks(
        assigned,
        stress=SECONDARY_STRESS,
    )
    result = dict(base)
    result["five_year_blocks_primary"] = primary_blocks
    result["five_year_blocks_secondary"] = secondary_blocks
    result["all_five_primary_blocks_positive"] = _all_blocks_positive(
        primary_blocks
    )
    result["all_five_secondary_blocks_positive"] = _all_blocks_positive(
        secondary_blocks
    )
    return result, assigned


def _rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    primary = row["primary"]
    secondary = row["secondary"]
    temporal = (
        bool(row["all_five_primary_blocks_positive"])
        and bool(row["all_five_secondary_blocks_positive"])
    )
    economic = (
        Decimal(str(primary["profit_factor"] or "0")) >= PF_PRIMARY_MIN
        and Decimal(str(secondary["profit_factor"] or "0"))
        >= PF_SECONDARY_MIN
    )
    return (
        int(temporal and economic),
        int(temporal),
        Decimal(str(primary["profit_factor"] or "0")),
        -max(
            Decimal(str(primary["max_drawdown_r"])),
            Decimal(str(secondary["max_drawdown_r"])),
        ),
        Decimal(str(primary["total_r"])),
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
    stream, bars_by_symbol, opened_by_symbol, provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"R35 density drift: {len(stream)}")

    raw_primary = r31._raw_metrics(stream, stress=PRIMARY_STRESS)
    raw_edge_pass = (
        Decimal(str(raw_primary["profit_factor"] or "0")) >= Decimal("1")
        and Decimal(str(raw_primary["total_r"])) > 0
    )

    search = [_row(stream, profile=profile) for profile in r34._profiles()]
    search.sort(key=lambda item: _rank(item[0]), reverse=True)

    finalists: list[dict[str, Any]] = []
    for row, assigned in search[:48]:
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
        goal_pass = (
            raw_edge_pass
            and Decimal(str(primary["profit_factor"] or "0"))
            >= PF_PRIMARY_MIN
            and Decimal(str(secondary["profit_factor"] or "0"))
            >= PF_SECONDARY_MIN
            and Decimal(primary_mtm["max_drawdown_r"])
            <= PORTFOLIO_DD_MAX
            and Decimal(secondary_mtm["max_drawdown_r"])
            <= PORTFOLIO_DD_MAX
            and bool(row["all_five_primary_blocks_positive"])
            and bool(row["all_five_secondary_blocks_positive"])
            and int(row["diagnostics"]["suppressed_trade_count"]) == 0
        )
        final = dict(row)
        final["primary_conservative_mark_to_market"] = primary_mtm
        final["secondary_conservative_mark_to_market"] = secondary_mtm
        final["goal_pass"] = goal_pass
        finalists.append(final)

    finalists.sort(
        key=lambda row: (
            int(bool(row["goal_pass"])),
            int(
                bool(row["all_five_primary_blocks_positive"])
                and bool(row["all_five_secondary_blocks_positive"])
            ),
            Decimal(str(row["primary"]["profit_factor"] or "0")),
            -max(
                Decimal(
                    row["primary_conservative_mark_to_market"][
                        "max_drawdown_r"
                    ]
                ),
                Decimal(
                    row["secondary_conservative_mark_to_market"][
                        "max_drawdown_r"
                    ]
                ),
            ),
        ),
        reverse=True,
    )
    goals = [row for row in finalists if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(stream),
        "raw_primary": raw_primary,
        "raw_edge_pass": raw_edge_pass,
        "evaluated_profile_count": len(search),
        "goal_candidate_count": len(goals),
        "best": finalists[0] if finalists else None,
        "top_10": finalists[:10],
        "goal_candidates": goals[:10],
        "temporal_contract": {
            "window_start": r6.START_DATE.isoformat(),
            "window_end_exclusive": r6.END_DATE_EXCLUSIVE.isoformat(),
            "boundaries": [x.isoformat() for x in _annual_boundaries()],
            "full_year_block_count": 5,
            "calendar_partial_years_are_certification_gate": False,
            "runtime_calendar_year_used": False,
        },
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
            "trading_rule_changed_from_r34": False,
            "new_optimization_dimension_added": False,
            "temporal_evaluation_contract_corrected": True,
            "calendar_year_used_for_runtime_decision": False,
            "all_structural_signals_preserved": True,
            "signal_suppression_allowed": False,
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
