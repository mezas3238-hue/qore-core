"""Run a forward temporal-stability check for Phase-19 overlap evidence.

The first 60% of the fully observed seven-Trader common time window is frozen as
training evidence. The final 40% is validation only. Positions crossing the split
are excluded from both segments. No strategy outcome, USD capital arithmetic, or
cross-Trader R aggregation is used.
"""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
    _parse_row,
)
from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase19_temporal_stability import (
    Phase19TemporalStabilityStatus,
    measure_phase19_temporal_overlap_stability,
)

TRAINING_FRACTION_NUMERATOR = 3
TRAINING_FRACTION_DENOMINATOR = 5
EXPECTED_SPLIT_AT = "2022-03-09T17:00:00+00:00"
EXPECTED_TRAINING_OPPORTUNITIES = 523
EXPECTED_VALIDATION_OPPORTUNITIES = 332
EXPECTED_BOUNDARY_CROSSING_EXCLUDED = 0
EXPECTED_TRAINING_CROSS_TRADER_OVERLAPS = 155
EXPECTED_VALIDATION_CROSS_TRADER_OVERLAPS = 95
EXPECTED_TOTAL_VARIATION_DISTANCE = "0.2258064516129032258064516130"
EXPECTED_WEIGHTED_JACCARD_SIMILARITY = "0.6315789473684210526315789475"


def run_validation(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19 temporal stability source set drift")

    parsed_by_trader: dict[
        TraderLineage,
        list[Phase19ChronologicalOpportunity],
    ] = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-18 source row-count drift"
            )
        parsed_by_trader[spec.trader_id] = [
            _parse_row(row, spec=spec).opportunity for row in rows
        ]

    if set(parsed_by_trader) != set(PHASE19_REQUIRED_TRADERS):
        raise ValueError("Phase 19 temporal stability Trader population drift")

    common_start = max(
        min(item.entry_at for item in items)
        for items in parsed_by_trader.values()
    )
    common_end = min(
        max(item.exit_at for item in items)
        for items in parsed_by_trader.values()
    )
    if common_start.isoformat() != EXPECTED_COMMON_START:
        raise ValueError("Phase 19 temporal stability common-start drift")
    if common_end.isoformat() != EXPECTED_COMMON_END:
        raise ValueError("Phase 19 temporal stability common-end drift")

    opportunities = tuple(
        item
        for trader in PHASE19_REQUIRED_TRADERS
        for item in parsed_by_trader[trader]
        if item.entry_at >= common_start and item.exit_at <= common_end
    )
    for trader in PHASE19_REQUIRED_TRADERS:
        selected_count = sum(
            item.trader_id is trader for item in opportunities
        )
        if selected_count != EXPECTED_COMMON_ROWS[trader]:
            raise ValueError(
                f"{trader.value} temporal stability common row-count drift"
            )

    duration_seconds = int((common_end - common_start).total_seconds())
    training_seconds = (
        duration_seconds
        * TRAINING_FRACTION_NUMERATOR
        // TRAINING_FRACTION_DENOMINATOR
    )
    split_at = common_start + timedelta(seconds=training_seconds)

    evidence = measure_phase19_temporal_overlap_stability(
        opportunities=opportunities,
        common_window_start=common_start,
        split_at=split_at,
        common_window_end=common_end,
    )
    if evidence.status is not (
        Phase19TemporalStabilityStatus.MEASURED_OBSERVATIONAL_ONLY
    ):
        raise ValueError(
            "Phase 19 temporal stability lacks full seven-Trader segment coverage"
        )
    if split_at.isoformat() != EXPECTED_SPLIT_AT:
        raise ValueError("Phase 19 temporal stability split drift")
    if evidence.training_opportunities != EXPECTED_TRAINING_OPPORTUNITIES:
        raise ValueError("Phase 19 training opportunity-count drift")
    if evidence.validation_opportunities != EXPECTED_VALIDATION_OPPORTUNITIES:
        raise ValueError("Phase 19 validation opportunity-count drift")
    if (
        evidence.boundary_crossing_opportunities_excluded
        != EXPECTED_BOUNDARY_CROSSING_EXCLUDED
    ):
        raise ValueError("Phase 19 split-boundary exclusion drift")
    if (
        evidence.training_cross_trader_overlap_pairs
        != EXPECTED_TRAINING_CROSS_TRADER_OVERLAPS
    ):
        raise ValueError("Phase 19 training overlap-count drift")
    if (
        evidence.validation_cross_trader_overlap_pairs
        != EXPECTED_VALIDATION_CROSS_TRADER_OVERLAPS
    ):
        raise ValueError("Phase 19 validation overlap-count drift")
    if str(evidence.total_variation_distance) != EXPECTED_TOTAL_VARIATION_DISTANCE:
        raise ValueError("Phase 19 total-variation drift")
    if (
        str(evidence.weighted_jaccard_similarity)
        != EXPECTED_WEIGHTED_JACCARD_SIMILARITY
    ):
        raise ValueError("Phase 19 weighted-Jaccard drift")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.temporal_stability_validation.v1",
        "identity": "CIBO_PHASE19_TEMPORAL_STABILITY_VALIDATION_V1",
        "status": evidence.status.value,
        "split_policy": {
            "kind": "FROZEN_TIME_FRACTION_60_40",
            "training_fraction_numerator": TRAINING_FRACTION_NUMERATOR,
            "training_fraction_denominator": TRAINING_FRACTION_DENOMINATOR,
            "outcomes_used_to_choose_split": False,
        },
        "common_window": {
            "start": common_start.isoformat(),
            "split_at": split_at.isoformat(),
            "end": common_end.isoformat(),
        },
        "training_opportunities": evidence.training_opportunities,
        "validation_opportunities": evidence.validation_opportunities,
        "boundary_crossing_opportunities_excluded": (
            evidence.boundary_crossing_opportunities_excluded
        ),
        "training_cross_trader_overlap_pairs": (
            evidence.training_cross_trader_overlap_pairs
        ),
        "validation_cross_trader_overlap_pairs": (
            evidence.validation_cross_trader_overlap_pairs
        ),
        "training_population": [
            trader.value for trader in evidence.training_population
        ],
        "validation_population": [
            trader.value for trader in evidence.validation_population
        ],
        "total_variation_distance": str(
            evidence.total_variation_distance
        ),
        "weighted_jaccard_similarity": str(
            evidence.weighted_jaccard_similarity
        ),
        "pair_stability": [
            {
                "left_trader": item.left_trader.value,
                "right_trader": item.right_trader.value,
                "training_overlap_pairs": item.training_overlap_pairs,
                "validation_overlap_pairs": item.validation_overlap_pairs,
                "training_share": str(item.training_share),
                "validation_share": str(item.validation_share),
            }
            for item in evidence.pair_stability
        ],
        "source_evidence": {
            key: {
                "trader_id": spec.trader_id.value,
                "artifact_id": spec.artifact_id,
                "artifact_digest": spec.artifact_digest,
            }
            for key, spec in SOURCE_SPECS.items()
        },
        "interpretation": {
            "observational_only": True,
            "predictive_value_claimed": False,
            "allocator_penalty_authorized": False,
            "sizing_change_authorized": False,
            "threshold_tuned_on_validation": False,
        },
        "governance": {
            "strategy_outcomes_used": False,
            "usd_capital_arithmetic_performed": False,
            "cross_trader_r_aggregation_performed": False,
            "qore_risk_authority_changed": False,
            "execution_authority_changed": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
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
    paths = {key: getattr(args, key) for key in SOURCE_SPECS}
    print(
        json.dumps(
            run_validation(paths=paths, output_path=args.output),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
