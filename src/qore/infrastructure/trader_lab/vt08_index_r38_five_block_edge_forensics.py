"""VT08 Index R38 — exact five-block structural edge forensics.

Diagnostic only. R38 explains the remaining R35-R37 temporal failure without
changing signals, targets, stops, risk, or authorization. It evaluates the
same source-complete 2,448 structural events in the five exact 12-month blocks
and attributes raw edge to pre-existing structural dimensions.

No cohort discovered here is automatically an operational rule. The purpose is
to determine whether the weak first block is associated with a structural
dimension that remains informative across the other four blocks.
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
    vt08_index_r35_five_year_temporal_contract as r35,
)

SCHEMA = "qore.trader_lab.vt08_index_r38_five_block_edge_forensics.v1"
IDENTITY = "VT08_INDEX_R38_FIVE_BLOCK_EDGE_FORENSICS_001"
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")


def _block_id(row: dict[str, Any]) -> str:
    exited = row["outcome"].exited_at.date()
    boundaries = r35._annual_boundaries()
    for index in range(5):
        if boundaries[index] <= exited < boundaries[index + 1]:
            return f"Y{index + 1}"
    raise ValueError(f"outcome outside exact five-year window: {exited}")


def _metrics(
    rows: Sequence[dict[str, Any]],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    values = tuple(
        row["outcome"].r_multiple - stress
        for row in sorted(
            rows,
            key=lambda item: (
                item["outcome"].exited_at,
                item["opportunity"].signal.symbol,
                item["opportunity"].signal.signal_at,
            ),
        )
    )
    return fx._metrics(values)


def _breakdown_by_block(
    rows: Sequence[dict[str, Any]],
    *,
    labeler: Callable[[dict[str, Any]], str],
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        grouped[labeler(row)][_block_id(row)].append(row)

    result: dict[str, dict[str, dict[str, Any]]] = {}
    for label, block_rows in sorted(grouped.items()):
        result[label] = {}
        for block in (f"Y{i}" for i in range(1, 6)):
            items = block_rows.get(block, [])
            result[label][block] = {
                "primary": _metrics(items, stress=PRIMARY_STRESS),
                "secondary": _metrics(items, stress=SECONDARY_STRESS),
            }
    return result


def _stability(
    breakdown: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, blocks in breakdown.items():
        secondary_totals = [
            Decimal(str(blocks[f"Y{i}"]["secondary"]["total_r"]))
            for i in range(1, 6)
        ]
        samples = [
            int(blocks[f"Y{i}"]["secondary"]["sample"])
            for i in range(1, 6)
        ]
        rows.append(
            {
                "label": label,
                "secondary_positive_blocks": sum(
                    value > 0 for value in secondary_totals
                ),
                "secondary_negative_blocks": sum(
                    value < 0 for value in secondary_totals
                ),
                "secondary_total_5y_r": str(sum(secondary_totals, Decimal())),
                "minimum_block_sample": min(samples),
                "block_samples": samples,
                "secondary_block_totals_r": [
                    str(value) for value in secondary_totals
                ],
            }
        )
    rows.sort(
        key=lambda item: (
            int(item["secondary_positive_blocks"]),
            Decimal(str(item["secondary_total_5y_r"])),
            int(item["minimum_block_sample"]),
        )
    )
    return rows


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
    stream, _bars, _opened, provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(f"R38 density drift: {len(stream)}")

    rows = [
        {
            "opportunity": opportunity,
            "outcome": outcome,
        }
        for opportunity, outcome in stream
    ]

    def market(row: dict[str, Any]) -> str:
        return str(row["opportunity"].signal.symbol)

    def side(row: dict[str, Any]) -> str:
        return str(row["opportunity"].signal.side.value)

    def poi(row: dict[str, Any]) -> str:
        return str(row["opportunity"].source_poi_kind)

    def anchor(row: dict[str, Any]) -> str:
        return str(row["opportunity"].signal.h4_opened_at.hour)

    def model(row: dict[str, Any]) -> str:
        return str(row["opportunity"].signal.model_kind.value)

    def rearm(row: dict[str, Any]) -> str:
        return (
            "REARM"
            if int(row["opportunity"].rearm_index) > 0
            else "INITIAL"
        )

    def tier(row: dict[str, Any]) -> str:
        return r25._quality_tier(row["opportunity"])

    def market_side(row: dict[str, Any]) -> str:
        return f"{market(row)}|{side(row)}"

    def side_poi(row: dict[str, Any]) -> str:
        return f"{side(row)}|{poi(row)}"

    def market_poi(row: dict[str, Any]) -> str:
        return f"{market(row)}|{poi(row)}"

    def market_side_poi(row: dict[str, Any]) -> str:
        return f"{market(row)}|{side(row)}|{poi(row)}"

    dimensions = {
        "market": market,
        "side": side,
        "poi": poi,
        "anchor": anchor,
        "model": model,
        "rearm": rearm,
        "formation_tier": tier,
        "market_side": market_side,
        "side_poi": side_poi,
        "market_poi": market_poi,
        "market_side_poi": market_side_poi,
    }

    breakdowns = {
        name: _breakdown_by_block(rows, labeler=labeler)
        for name, labeler in dimensions.items()
    }
    stability = {
        name: _stability(breakdown)
        for name, breakdown in breakdowns.items()
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "sample": len(rows),
        "exact_block_boundaries": [
            value.isoformat() for value in r35._annual_boundaries()
        ],
        "aggregate": {
            "primary": _metrics(rows, stress=PRIMARY_STRESS),
            "secondary": _metrics(rows, stress=SECONDARY_STRESS),
        },
        "breakdowns": breakdowns,
        "stability": stability,
        "provenance": provenance,
        "governance": {
            "forensics_only": True,
            "consumed_window": True,
            "fresh_holdout_claim": False,
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

    summaries = {
        name: rows[:12]
        for name, rows in report["stability"].items()
        if name in {
            "market",
            "side",
            "poi",
            "formation_tier",
            "market_side",
            "side_poi",
            "market_poi",
            "market_side_poi",
        }
    }
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "sample": report["sample"],
                "aggregate": report["aggregate"],
                "stability": summaries,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
