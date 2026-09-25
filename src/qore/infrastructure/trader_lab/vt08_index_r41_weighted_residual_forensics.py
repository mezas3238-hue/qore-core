"""VT08 Index R41 — weighted residual-edge forensics after rejected R40.

R40 improved aggregate PF and DD but the exact first 12-month block remained
slightly negative under -0.10R friction. R41 is diagnostic only: it reconstructs
R40 exactly and attributes the *effective weighted* result by pre-existing
structural dimensions. No signal, weight, target, stop, or authority changes.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
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
    vt08_index_r25_r23_failure_forensics as r25,
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
    vt08_index_r38_five_block_edge_forensics as r38,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r40_nas100_short_structural_prior as r40,
)
from qore.infrastructure.trader_lab.vt08_index_r15_concurrent_portfolio_validation import (
    AssignedTrade,
)

SCHEMA = "qore.trader_lab.vt08_index_r41_weighted_residual_forensics.v1"
IDENTITY = "VT08_INDEX_R41_WEIGHTED_RESIDUAL_FORENSICS_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")


def _block_id(item: AssignedTrade) -> str | None:
    boundaries = r35._annual_boundaries()
    exited = item.exited_at.date()
    for index in range(5):
        if boundaries[index] <= exited < boundaries[index + 1]:
            return f"Y{index + 1}"
    return None


def _metrics(
    items: Sequence[AssignedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    ordered = sorted(items, key=lambda item: (item.exited_at, item.symbol, item.trade_id))
    values = tuple(
        (item.outcome.r_multiple - stress) * item.weight
        for item in ordered
    )
    return fx._metrics(values)


def _breakdown(
    assigned: Sequence[AssignedTrade],
    *,
    labeler: Callable[[AssignedTrade], str],
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, list[AssignedTrade]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in assigned:
        block = _block_id(item)
        if block is None:
            continue
        grouped[labeler(item)][block].append(item)

    result: dict[str, dict[str, dict[str, Any]]] = {}
    for label, blocks in sorted(grouped.items()):
        result[label] = {}
        for index in range(1, 6):
            key = f"Y{index}"
            rows = blocks.get(key, [])
            result[label][key] = {
                "primary": _metrics(rows, stress=PRIMARY_STRESS),
                "secondary": _metrics(rows, stress=SECONDARY_STRESS),
                "effective_risk_sum": str(
                    sum((item.weight for item in rows), Decimal())
                ),
            }
    return result


def _ranking(
    breakdown: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for label, blocks in breakdown.items():
        totals = [
            Decimal(str(blocks[f"Y{i}"]["secondary"]["total_r"]))
            for i in range(1, 6)
        ]
        samples = [
            int(blocks[f"Y{i}"]["secondary"]["sample"])
            for i in range(1, 6)
        ]
        result.append(
            {
                "label": label,
                "y1_secondary_total_r": str(totals[0]),
                "secondary_block_totals_r": [str(value) for value in totals],
                "secondary_positive_blocks": sum(value > 0 for value in totals),
                "secondary_negative_blocks": sum(value < 0 for value in totals),
                "secondary_total_5y_r": str(sum(totals, Decimal())),
                "minimum_block_sample": min(samples),
                "block_samples": samples,
            }
        )
    result.sort(
        key=lambda row: (
            Decimal(str(row["y1_secondary_total_r"])),
            int(row["secondary_positive_blocks"]),
            Decimal(str(row["secondary_total_5y_r"])),
        )
    )
    return result


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
    stream, _bars, _opened, provenance = r31._build_source_complete_stream(
        roots=roots
    )
    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"R41 density drift: {len(stream)}")

    _base, base_assigned = r34._row(
        stream,
        overlay=r40.BASE_POI_OVERLAY,
    )
    assigned, r40_diagnostics = r40._apply_structural_prior(base_assigned)

    def market(item: AssignedTrade) -> str:
        return item.symbol

    def side(item: AssignedTrade) -> str:
        return str(item.opportunity.signal.side.value)

    def poi(item: AssignedTrade) -> str:
        return str(item.opportunity.source_poi_kind)

    def tier(item: AssignedTrade) -> str:
        return r25._quality_tier(item.opportunity)

    def market_side(item: AssignedTrade) -> str:
        return f"{market(item)}|{side(item)}"

    def market_poi(item: AssignedTrade) -> str:
        return f"{market(item)}|{poi(item)}"

    def side_poi(item: AssignedTrade) -> str:
        return f"{side(item)}|{poi(item)}"

    def market_side_poi(item: AssignedTrade) -> str:
        return f"{market(item)}|{side(item)}|{poi(item)}"

    dimensions = {
        "market": market,
        "side": side,
        "poi": poi,
        "formation_tier": tier,
        "market_side": market_side,
        "market_poi": market_poi,
        "side_poi": side_poi,
        "market_side_poi": market_side_poi,
    }
    breakdowns = {
        name: _breakdown(assigned, labeler=labeler)
        for name, labeler in dimensions.items()
    }
    rankings = {
        name: _ranking(breakdown)
        for name, breakdown in breakdowns.items()
    }

    primary_blocks = r35._five_full_year_blocks(
        assigned,
        stress=PRIMARY_STRESS,
    )
    secondary_blocks = r35._five_full_year_blocks(
        assigned,
        stress=SECONDARY_STRESS,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(assigned),
        "r40_identity": r40.IDENTITY,
        "r40_goal_pass": False,
        "r40_diagnostics": r40_diagnostics,
        "five_year_blocks_primary": primary_blocks,
        "five_year_blocks_secondary": secondary_blocks,
        "breakdowns": breakdowns,
        "rankings": rankings,
        "raw_r38_reference_identity": r38.IDENTITY,
        "provenance": provenance,
        "governance": {
            "forensics_only": True,
            "consumed_window": True,
            "fresh_holdout_claim": False,
            "r40_reconstructed_exactly": True,
            "trading_rule_changed": False,
            "risk_rule_changed": False,
            "trade_suppression_performed": False,
            "calendar_or_year_feature_proposed_for_runtime": False,
            "cohort_to_rule_automatic": False,
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
                "five_year_blocks_secondary": report[
                    "five_year_blocks_secondary"
                ],
                "rankings": {
                    name: rows[:12]
                    for name, rows in report["rankings"].items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
