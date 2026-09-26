"""Bind Phase 19F overlap-conditioned dependence to sealed 7-Trader evidence.

TRAIN and VALIDATION are measured separately using the already-frozen Phase 19B
split. The output is descriptive only and cannot change sizing/allocation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_dependence import (
    Phase19DependenceAtlas,
    Phase19GeometryOutcome,
    measure_phase19_overlap_dependence,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_COMMON_END,
    EXPECTED_COMMON_ROWS,
    EXPECTED_COMMON_START,
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
    _parse_row,
)
from cibo_phase19_normalized_capital_mechanics import (
    _normalized_outcome_r,
    _source_evidence_id,
)
from cibo_phase19_temporal_stability_validation import (
    EXPECTED_SPLIT_AT,
    EXPECTED_TRAINING_CROSS_TRADER_OVERLAPS,
    EXPECTED_TRAINING_OPPORTUNITIES,
    EXPECTED_VALIDATION_CROSS_TRADER_OVERLAPS,
    EXPECTED_VALIDATION_OPPORTUNITIES,
)


def _serialize(atlas: Phase19DependenceAtlas) -> dict[str, Any]:
    return {
        "total_cross_trader_overlap_pairs": (
            atlas.total_cross_trader_overlap_pairs
        ),
        "pair_evidence": [
            {
                "left_trader": item.left_trader.value,
                "right_trader": item.right_trader.value,
                "overlapping_pairs": item.overlapping_pairs,
                "left_loss_pairs": item.left_loss_pairs,
                "right_loss_pairs": item.right_loss_pairs,
                "joint_loss_pairs": item.joint_loss_pairs,
                "same_nonzero_sign_pairs": item.same_nonzero_sign_pairs,
                "left_loss_rate": (
                    None
                    if item.left_loss_rate is None
                    else str(item.left_loss_rate)
                ),
                "right_loss_rate": (
                    None
                    if item.right_loss_rate is None
                    else str(item.right_loss_rate)
                ),
                "joint_loss_rate": (
                    None
                    if item.joint_loss_rate is None
                    else str(item.joint_loss_rate)
                ),
                "independent_joint_loss_rate": (
                    None
                    if item.independent_joint_loss_rate is None
                    else str(item.independent_joint_loss_rate)
                ),
                "joint_loss_excess": (
                    None
                    if item.joint_loss_excess is None
                    else str(item.joint_loss_excess)
                ),
                "same_nonzero_sign_rate": (
                    None
                    if item.same_nonzero_sign_rate is None
                    else str(item.same_nonzero_sign_rate)
                ),
            }
            for item in atlas.pair_evidence
        ],
    }


def validate(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19F source set drift")

    parsed_by_trader: dict[
        TraderLineage,
        list[Phase19GeometryOutcome],
    ] = {}
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        if len(rows) != EXPECTED_SOURCE_ROWS[spec.trader_id]:
            raise ValueError(
                f"{spec.trader_id.value} Phase-19F source row-count drift"
            )
        evidence_id = _source_evidence_id(spec)
        observations: list[Phase19GeometryOutcome] = []
        for row in rows:
            opportunity = _parse_row(row, spec=spec).opportunity
            observations.append(
                Phase19GeometryOutcome(
                    opportunity=opportunity,
                    normalized_outcome_r=_normalized_outcome_r(
                        row,
                        trader_id=spec.trader_id,
                    ),
                    evidence_id=evidence_id,
                )
            )
        parsed_by_trader[spec.trader_id] = observations

    if set(parsed_by_trader) != set(PHASE19_REQUIRED_TRADERS):
        raise ValueError("Phase 19F Trader population drift")

    common_start = max(
        min(item.opportunity.entry_at for item in items)
        for items in parsed_by_trader.values()
    )
    common_end = min(
        max(item.opportunity.exit_at for item in items)
        for items in parsed_by_trader.values()
    )
    if common_start.isoformat() != EXPECTED_COMMON_START:
        raise ValueError("Phase 19F common-start drift")
    if common_end.isoformat() != EXPECTED_COMMON_END:
        raise ValueError("Phase 19F common-end drift")

    common = tuple(
        item
        for trader in PHASE19_REQUIRED_TRADERS
        for item in parsed_by_trader[trader]
        if item.opportunity.entry_at >= common_start
        and item.opportunity.exit_at <= common_end
    )
    for trader in PHASE19_REQUIRED_TRADERS:
        count = sum(
            item.opportunity.trader_id is trader for item in common
        )
        if count != EXPECTED_COMMON_ROWS[trader]:
            raise ValueError(
                f"{trader.value} Phase-19F common-window row drift"
            )

    split_at = datetime.fromisoformat(EXPECTED_SPLIT_AT)
    training = tuple(
        item
        for item in common
        if item.opportunity.exit_at <= split_at
    )
    validation = tuple(
        item
        for item in common
        if item.opportunity.entry_at >= split_at
    )
    crossing = len(common) - len(training) - len(validation)
    if len(training) != EXPECTED_TRAINING_OPPORTUNITIES:
        raise ValueError("Phase 19F training row-count drift")
    if len(validation) != EXPECTED_VALIDATION_OPPORTUNITIES:
        raise ValueError("Phase 19F validation row-count drift")
    if crossing != 0:
        raise ValueError("Phase 19F unexpected split-crossing opportunity")

    training_atlas = measure_phase19_overlap_dependence(training)
    validation_atlas = measure_phase19_overlap_dependence(validation)
    if training_atlas.total_cross_trader_overlap_pairs != (
        EXPECTED_TRAINING_CROSS_TRADER_OVERLAPS
    ):
        raise ValueError("Phase 19F training overlap drift")
    if validation_atlas.total_cross_trader_overlap_pairs != (
        EXPECTED_VALIDATION_CROSS_TRADER_OVERLAPS
    ):
        raise ValueError("Phase 19F validation overlap drift")

    report: dict[str, Any] = {
        "schema": "qore.cibo.phase19.overlap_dependence.v1",
        "identity": "CIBO_PHASE19F_OVERLAP_DEPENDENCE_V1",
        "status": "TRAIN_VALIDATION_DEPENDENCE_MEASURED_DESCRIPTIVE_ONLY",
        "common_window": {
            "start": common_start.isoformat(),
            "split_at": split_at.isoformat(),
            "end": common_end.isoformat(),
        },
        "training_opportunities": len(training),
        "validation_opportunities": len(validation),
        "boundary_crossing_excluded": crossing,
        "training": _serialize(training_atlas),
        "validation": _serialize(validation_atlas),
        "governance": {
            "outcomes_used_offline_after_overlap_fixed": True,
            "historical_sizing_used": False,
            "usd_pnl_used": False,
            "provider_economics_used": False,
            "full_window_parameter_tuning_authorized": False,
            "descriptive_only": True,
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
    paths = {key: getattr(args, key) for key in SOURCE_SPECS}
    print(json.dumps(validate(paths=paths, output_path=args.output), sort_keys=True))


if __name__ == "__main__":
    main()
