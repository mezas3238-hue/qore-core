"""Run the burned-only CE2I T02 structural-precision falsification probe."""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_t02_burned_calibration import (
    T02StructuralObservation,
    calibrate_t02_structural_precision,
)

_HOLDOUT_START = datetime(2017, 1, 1, tzinfo=UTC)
_HOLDOUT_END = datetime(2017, 7, 1, tzinfo=UTC)

_SOURCES = {
    "R34_XAUUSD": (10972757083, "phase18-xauusd-r34-bound-trades.jsonl"),
    "R38_EURUSD": (10972572540, "phase18-eurusd-r38-bound-trades.jsonl"),
    "R43_GBPUSD": (10972906353, "phase18-gbpusd-r43-bound-trades.jsonl"),
    "R38_GBPJPY": (10972846579, "phase18-gbpjpy-r38-bound-trades.jsonl"),
    "R42_AUDJPY": (10972467350, "phase18-audjpy-r42-bound-trades.jsonl"),
    "VT08_FOREX": (10972037659, "phase18-vt08-r315-fundednext-trades.jsonl"),
    "VT31_NAS100": (10971913368, "phase18-vt31-v4-bound-trades.jsonl"),
}


def _decimal(row: dict[str, object], *names: str) -> Decimal:
    for name in names:
        value = row.get(name)
        if value is not None:
            return Decimal(str(value))
    raise ValueError(f"missing numeric field from {names}")


def _observation(row: dict[str, object]) -> T02StructuralObservation:
    entry_at = datetime.fromisoformat(str(row["entry_at"]))
    if _HOLDOUT_START <= entry_at < _HOLDOUT_END:
        raise ValueError("2017H1 holdout row entered T02 calibration")
    entry = _decimal(row, "entry_price", "entry")
    stop = _decimal(row, "structural_stop", "initial_stop")
    target = _decimal(row, "technical_target", "structural_target")
    stop_distance = abs(entry - stop)
    target_distance = abs(target - entry)
    if stop_distance <= 0 or target_distance <= 0:
        raise ValueError("invalid T02 structural geometry")
    outcome = _decimal(
        row,
        "raw_net_010_r",
        "raw_outcome_r",
        "r_multiple",
    )
    reason = str(row.get("exit_reason", "")).lower()
    return T02StructuralObservation(
        entry_at=entry_at,
        stop_to_target_ratio=stop_distance / target_distance,
        stopped="stop" in reason,
        structural_outcome_r=outcome,
    )


def _load(path: Path, *, jsonl_name: str) -> tuple[T02StructuralObservation, ...]:
    with zipfile.ZipFile(path) as archive:
        rows = tuple(
            json.loads(line)
            for line in archive.read(jsonl_name).decode().splitlines()
            if line.strip()
        )
    observations = tuple(_observation(row) for row in rows)
    if not observations:
        raise ValueError("T02 burned source is empty")
    return observations


def build_report(paths: dict[str, Path]) -> dict[str, Any]:
    results = []
    for lineage, (_, jsonl_name) in _SOURCES.items():
        observations = _load(paths[lineage], jsonl_name=jsonl_name)
        result = calibrate_t02_structural_precision(
            lineage=lineage,
            observations=observations,
        )
        results.append(
            {
                "lineage": result.lineage,
                "train_rows": result.train_rows,
                "validation_rows": result.validation_rows,
                "train_threshold_stop_to_target": str(
                    result.train_threshold_stop_to_target
                ),
                "validation_candidate_rows": result.validation_candidate_rows,
                "baseline_stop_rate": str(result.baseline_stop_rate),
                "candidate_stop_rate": str(result.candidate_stop_rate),
                "baseline_p95_loss_r": str(result.baseline_p95_loss_r),
                "candidate_p95_loss_r": str(result.candidate_p95_loss_r),
                "strict_stop_rate_improvement": (
                    result.strict_stop_rate_improvement
                ),
                "tail_loss_not_worse": result.tail_loss_not_worse,
                "minimum_validation_sample_met": (
                    result.minimum_validation_sample_met
                ),
                "eligible_for_structural_leverage": (
                    result.eligible_for_structural_leverage
                ),
            }
        )

    eligible = [
        row["lineage"]
        for row in results
        if row["eligible_for_structural_leverage"]
    ]
    return {
        "schema": "qore.cibo.t02.burned_structural_calibration.v1",
        "status": (
            "STRUCTURAL_PRECISION_PROXY_FALSIFIED"
            if not eligible
            else "PARTIAL_STRUCTURAL_PRECISION_ELIGIBILITY_RESEARCH_ONLY"
        ),
        "calibration_source": "BURNED_PHASE18_ONLY",
        "threshold_policy": "TRAIN_MEDIAN_STOP_TO_TARGET_RATIO_SINGLE_SHOT",
        "threshold_search_count": 1,
        "train_fraction": "0.60",
        "minimum_validation_candidate_rows": 30,
        "eligible_lineages": eligible,
        "lineages": results,
        "source_artifacts": {
            lineage: artifact_id
            for lineage, (artifact_id, _) in _SOURCES.items()
        },
        "governance": {
            "holdout_2017h1_used": False,
            "holdout_2017h1_outcomes_used": False,
            "provider_usd_economics_claimed": False,
            "threshold_reoptimized_on_validation": False,
            "target_aware": False,
            "oos_ready": False,
            "certification_ready": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for lineage in _SOURCES:
        parser.add_argument(
            f"--{lineage.lower().replace('_', '-')}",
            type=Path,
            required=True,
        )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {
        lineage: getattr(args, lineage.lower())
        for lineage in _SOURCES
    }
    payload = build_report(paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
