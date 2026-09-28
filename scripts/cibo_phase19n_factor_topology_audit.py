"""Audit direction-only factor topology for burned Phase19 T08 evidence.

The audit uses symbol, side and active position intervals only. Trade outcomes,
provider USD economics, exposure magnitudes and correlations are not consumed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_CROSS_TRADER_OVERLAP_PAIRS,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
)

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_factor_topology import (
    FactorTopologyRelation,
    compare_factor_topology,
    directional_factor_exposures,
)

EXPECTED_NO_SHARED_FACTOR = 124
EXPECTED_SAME_DIRECTION = 67
EXPECTED_OPPOSING_DIRECTION = 59
EXPECTED_MIXED_DIRECTION = 0
EXPECTED_FACTOR_DIRECTION_COUNTS = {
    "AUD": {"same": 4, "opposing": 0},
    "GBP": {"same": 12, "opposing": 16},
    "JPY": {"same": 31, "opposing": 11},
    "USD": {"same": 28, "opposing": 34},
}


def _symbol(row: dict[str, Any], *, key: str) -> str:
    fixed = SOURCE_SPECS[key].qore_symbol
    return fixed if fixed is not None else str(row["symbol"])


def _common_rows(
    rows: list[dict[str, Any]],
    *,
    key: str,
) -> tuple[dict[str, Any], ...]:
    common_start = datetime.fromisoformat(EXPECTED_COMMON_START)
    common_end = datetime.fromisoformat(EXPECTED_COMMON_END)
    selected = []
    for row in rows:
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        if signal_at > entry_at:
            raise ValueError("Phase19N signal occurs after entry")
        if entry_at >= common_start and exit_at <= common_end:
            selected.append(
                {
                    "trader_id": SOURCE_SPECS[key].trader_id,
                    "qore_symbol": _symbol(row, key=key),
                    "side": str(row["side"]),
                    "entry_at": entry_at,
                    "exit_at": exit_at,
                }
            )
    return tuple(selected)


def run(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase19N source set drift")

    by_trader: dict[TraderLineage, tuple[dict[str, Any], ...]] = {}
    source_evidence: dict[str, Any] = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase19N source row-count drift"
            )
        common = _common_rows(rows, key=key)
        if len(common) != EXPECTED_COMMON_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase19N common row-count drift"
            )
        by_trader[spec.trader_id] = common
        source_evidence[key] = {
            "trader_id": spec.trader_id.value,
            "artifact_id": spec.artifact_id,
            "artifact_digest": spec.artifact_digest,
            "common_rows": len(common),
        }

    combined = sorted(
        (
            row
            for rows in by_trader.values()
            for row in rows
        ),
        key=lambda row: (
            row["entry_at"],
            row["trader_id"].value,
            row["qore_symbol"],
        ),
    )

    relation_counts: Counter[str] = Counter()
    factor_same: Counter[str] = Counter()
    factor_opposing: Counter[str] = Counter()
    cross_trader_overlaps = 0

    for left_index, left in enumerate(combined):
        for right in combined[left_index + 1 :]:
            if right["entry_at"] >= left["exit_at"]:
                break
            if left["trader_id"] is right["trader_id"]:
                continue
            if not (
                left["entry_at"] < right["exit_at"]
                and right["entry_at"] < left["exit_at"]
            ):
                continue
            cross_trader_overlaps += 1
            comparison = compare_factor_topology(
                left=directional_factor_exposures(
                    qore_symbol=left["qore_symbol"],
                    side=left["side"],
                ),
                right=directional_factor_exposures(
                    qore_symbol=right["qore_symbol"],
                    side=right["side"],
                ),
            )
            relation_counts[comparison.relation.value] += 1
            for factor in comparison.same_direction_factors:
                factor_same[factor] += 1
            for factor in comparison.opposing_direction_factors:
                factor_opposing[factor] += 1

    if cross_trader_overlaps != EXPECTED_CROSS_TRADER_OVERLAP_PAIRS:
        raise ValueError("Phase19N overlap population drift")
    expected_relations = {
        FactorTopologyRelation.NO_SHARED_FACTOR.value: EXPECTED_NO_SHARED_FACTOR,
        FactorTopologyRelation.SAME_DIRECTION.value: EXPECTED_SAME_DIRECTION,
        FactorTopologyRelation.OPPOSING_DIRECTION.value: (
            EXPECTED_OPPOSING_DIRECTION
        ),
        FactorTopologyRelation.MIXED_DIRECTION.value: EXPECTED_MIXED_DIRECTION,
    }
    for relation, expected in expected_relations.items():
        if relation_counts[relation] != expected:
            raise ValueError(
                f"Phase19N {relation} count drift"
            )
    for factor, expected in EXPECTED_FACTOR_DIRECTION_COUNTS.items():
        if factor_same[factor] != expected["same"]:
            raise ValueError(f"Phase19N {factor} same-direction drift")
        if factor_opposing[factor] != expected["opposing"]:
            raise ValueError(f"Phase19N {factor} opposing-direction drift")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19n.factor_topology_audit.v1",
        "identity": "CIBO_PHASE19N_FACTOR_TOPOLOGY_AUDIT_V1",
        "status": "DIRECTIONAL_FACTOR_TOPOLOGY_IDENTIFIED_NETTING_MAGNITUDE_BLOCKED",
        "common_window": {
            "start": EXPECTED_COMMON_START,
            "end": EXPECTED_COMMON_END,
            "common_rows": len(combined),
            "cross_trader_overlap_pairs": cross_trader_overlaps,
        },
        "directional_topology": {
            "lineage_coverage": "7_OF_7",
            "no_shared_factor_pairs": relation_counts[
                FactorTopologyRelation.NO_SHARED_FACTOR.value
            ],
            "shared_factor_pairs": (
                relation_counts[FactorTopologyRelation.SAME_DIRECTION.value]
                + relation_counts[
                    FactorTopologyRelation.OPPOSING_DIRECTION.value
                ]
                + relation_counts[FactorTopologyRelation.MIXED_DIRECTION.value]
            ),
            "same_direction_pairs": relation_counts[
                FactorTopologyRelation.SAME_DIRECTION.value
            ],
            "opposing_direction_pairs": relation_counts[
                FactorTopologyRelation.OPPOSING_DIRECTION.value
            ],
            "mixed_direction_pairs": relation_counts[
                FactorTopologyRelation.MIXED_DIRECTION.value
            ],
            "factor_direction_counts": {
                factor: {
                    "same": factor_same[factor],
                    "opposing": factor_opposing[factor],
                }
                for factor in sorted(EXPECTED_FACTOR_DIRECTION_COUNTS)
            },
        },
        "t08_required_evidence": {
            "factor_map": "DIRECTIONAL_TOPOLOGY_IDENTIFIED_7_OF_7",
            "position_exposures": "ACTIVE_DIRECTION_ONLY_MAGNITUDE_UNCALIBRATED",
            "correlation_state": "NOT_IDENTIFIED",
        },
        "source_evidence": source_evidence,
        "interpretation": {
            "factor_topology_causal_from_symbol_side": True,
            "monetary_factor_magnitude_identified": False,
            "observed_correlation_identified": False,
            "opposing_direction_is_hedge_credit": False,
            "same_direction_is_quantified_concentration": False,
            "t08_calibration_promotion_from_this_report": False,
            "netting_credit_authorized": False,
            "fresh_oos_netting_utility_required": True,
        },
        "governance": {
            "trade_outcomes_read": False,
            "outcome_fields_used": [],
            "holdout_2017h1_used": False,
            "historical_provider_usd_claimed": False,
            "correlation_fabricated": False,
            "exposure_magnitude_fabricated": False,
            "policy_certified": False,
            "oos_ready": False,
            "allocation_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        paths={key: getattr(args, key) for key in SOURCE_SPECS},
        output_path=args.output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
