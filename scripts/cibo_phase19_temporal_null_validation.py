"""Run Phase 19E calendar-conditioned temporal null on sealed 7-Trader evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_temporal_null import (
    measure_phase19_temporal_null,
)
from scripts.cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_SOURCE_ROWS,
    PHASE19_REQUIRED_TRADERS,
    SOURCE_SPECS,
    _jsonl,
    _parse_row,
)

PERMUTATIONS = 1000
RANDOM_SEED = 19019


def validate(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19E source set drift")

    selected_by_trader: dict[TraderLineage, list[Any]] = {}
    common_start = None
    common_end = None

    parsed_all: dict[TraderLineage, list[Any]] = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-19E source row-count drift"
            )
        items = [_parse_row(row, spec=spec).opportunity for row in rows]
        parsed_all[spec.trader_id] = items

    starts = [
        min(item.entry_at for item in items)
        for items in parsed_all.values()
    ]
    ends = [
        max(item.exit_at for item in items)
        for items in parsed_all.values()
    ]
    common_start = max(starts)
    common_end = min(ends)
    if common_start.isoformat() != EXPECTED_COMMON_START:
        raise ValueError("Phase 19E common-window start drift")
    if common_end.isoformat() != EXPECTED_COMMON_END:
        raise ValueError("Phase 19E common-window end drift")

    for trader in PHASE19_REQUIRED_TRADERS:
        selected = [
            item
            for item in parsed_all[trader]
            if item.entry_at >= common_start and item.exit_at <= common_end
        ]
        if len(selected) != EXPECTED_COMMON_ROWS[trader]:
            raise ValueError(
                f"{trader.value} Phase-19E common-window row drift"
            )
        selected_by_trader[trader] = selected

    opportunities = tuple(
        item
        for trader in PHASE19_REQUIRED_TRADERS
        for item in selected_by_trader[trader]
    )
    result = measure_phase19_temporal_null(
        opportunities=opportunities,
        common_window_start=common_start,
        common_window_end=common_end,
        permutations=PERMUTATIONS,
        random_seed=RANDOM_SEED,
    )

    if result.observed_cross_trader_overlap_pairs != 250:
        raise ValueError("Phase 19E observed overlap drift")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.temporal_null.v1",
        "identity": "CIBO_PHASE19E_TEMPORAL_NULL_V1",
        "status": "OBSERVATIONAL_TEMPORAL_NULL_MEASURED",
        "common_window": {
            "start": common_start.isoformat(),
            "end": common_end.isoformat(),
        },
        "permutations": result.permutations,
        "random_seed": result.random_seed,
        "conditioning": list(result.conditioning),
        "observed_cross_trader_overlap_pairs": (
            result.observed_cross_trader_overlap_pairs
        ),
        "null_mean_cross_trader_overlap_pairs": str(
            result.null_mean_cross_trader_overlap_pairs
        ),
        "null_p95_cross_trader_overlap_pairs": (
            result.null_p95_cross_trader_overlap_pairs
        ),
        "upper_tail_probability": str(result.upper_tail_probability),
        "pair_evidence": [
            {
                "left_trader": item.left_trader.value,
                "right_trader": item.right_trader.value,
                "observed_overlap_pairs": item.observed_overlap_pairs,
                "null_mean_overlap_pairs": str(
                    item.null_mean_overlap_pairs
                ),
                "null_p95_overlap_pairs": item.null_p95_overlap_pairs,
                "upper_tail_probability": str(
                    item.upper_tail_probability
                ),
            }
            for item in result.pair_evidence
        ],
        "governance": {
            "outcomes_used": result.outcomes_used,
            "sizing_used": result.sizing_used,
            "provider_economics_used": result.provider_economics_used,
            "descriptive_only": True,
            "allocation_authority": result.allocation_authority,
            "risk_authority": result.risk_authority,
            "execution_authority": result.execution_authority,
            "correlation_claimed": False,
            "harmful_interaction_claimed": False,
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
    paths = {key: getattr(args, key) for key in SOURCE_SPECS}
    print(json.dumps(validate(paths=paths, output_path=args.output), sort_keys=True))


if __name__ == "__main__":
    main()
