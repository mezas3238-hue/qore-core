"""Run train-only burned categorical calibration for CE2I T02."""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_t02_context_calibration import (
    T02CategoricalObservation,
    calibrate_t02_categorical_structure,
)

_HOLDOUT_START = datetime(2017, 1, 1, tzinfo=UTC)
_HOLDOUT_END = datetime(2017, 7, 1, tzinfo=UTC)

_SOURCES: dict[str, tuple[int, str, tuple[str, ...]]] = {
    "R34_XAUUSD": (
        10972757083,
        "phase18-xauusd-r34-bound-trades.jsonl",
        ("family", "posture", "target_rank", "target_route", "side", "source"),
    ),
    "R38_EURUSD": (
        10972572540,
        "phase18-eurusd-r38-bound-trades.jsonl",
        (
            "family",
            "posture",
            "target_rank",
            "target_route",
            "side",
            "source",
            "fragility_flag_count",
            "fragility_flags",
        ),
    ),
    "R43_GBPUSD": (
        10972906353,
        "phase18-gbpusd-r43-bound-trades.jsonl",
        (
            "classification",
            "family",
            "posture",
            "regime",
            "setup_context",
            "target_rank",
            "target_route",
            "side",
            "source",
        ),
    ),
    "R38_GBPJPY": (
        10972846579,
        "phase18-gbpjpy-r38-bound-trades.jsonl",
        (
            "authority_tier",
            "posture",
            "regime",
            "setup_context",
            "target_rank",
            "target_route",
            "side",
            "source_scheme",
            "validation_class",
        ),
    ),
    "R42_AUDJPY": (
        10972467350,
        "phase18-audjpy-r42-bound-trades.jsonl",
        (
            "authority_tier",
            "posture",
            "regime",
            "setup_context",
            "target_rank",
            "target_route",
            "side",
            "source_scheme",
            "validation_class",
            "fragility_flag_count",
            "fragility_flags",
        ),
    ),
    "VT08_FOREX": (
        10972037659,
        "phase18-vt08-r315-fundednext-trades.jsonl",
        ("profile_id", "side", "symbol"),
    ),
    "VT31_NAS100": (
        10971913368,
        "phase18-vt31-v4-bound-trades.jsonl",
        (
            "entry_family",
            "tier",
            "side",
            "h1_state",
            "h4_state",
            "premarket_state",
            "prior_day_state",
            "risk_ref_bucket",
            "reference_volatility_state",
            "confirmation_latency_bucket",
            "reclaim_age_bucket",
            "last_structure_event_family",
            "candidate_families",
            "authorization_reason",
        ),
    ),
}


def _normalized(value: object) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _outcome(row: dict[str, object]) -> Decimal:
    for name in ("raw_net_010_r", "raw_outcome_r", "r_multiple"):
        if row.get(name) is not None:
            return Decimal(str(row[name]))
    raise ValueError("T02 context row missing structural outcome")


def _observation(
    row: dict[str, object],
    *,
    allowed_fields: tuple[str, ...],
) -> T02CategoricalObservation:
    entry_at = datetime.fromisoformat(str(row["entry_at"]))
    if _HOLDOUT_START <= entry_at < _HOLDOUT_END:
        raise ValueError("2017H1 holdout row entered T02 context calibration")
    contexts = tuple(
        (field, _normalized(row[field]))
        for field in allowed_fields
        if row.get(field) is not None and _normalized(row[field])
    )
    return T02CategoricalObservation(
        entry_at=entry_at,
        contexts=contexts,
        stopped="stop" in str(row.get("exit_reason", "")).lower(),
        structural_outcome_r=_outcome(row),
    )


def _load(
    path: Path,
    *,
    jsonl_name: str,
    allowed_fields: tuple[str, ...],
) -> tuple[T02CategoricalObservation, ...]:
    with zipfile.ZipFile(path) as archive:
        rows = tuple(
            json.loads(line)
            for line in archive.read(jsonl_name).decode().splitlines()
            if line.strip()
        )
    observations = tuple(
        _observation(row, allowed_fields=allowed_fields)
        for row in rows
    )
    if not observations:
        raise ValueError("T02 context burned source is empty")
    return observations


def build_report(paths: dict[str, Path]) -> dict[str, Any]:
    results = []
    for lineage, (artifact_id, jsonl_name, allowed_fields) in _SOURCES.items():
        observations = _load(
            paths[lineage],
            jsonl_name=jsonl_name,
            allowed_fields=allowed_fields,
        )
        result = calibrate_t02_categorical_structure(
            lineage=lineage,
            observations=observations,
            allowed_fields=allowed_fields,
        )
        results.append(
            {
                "lineage": result.lineage,
                "source_artifact_id": artifact_id,
                "allowed_fields": list(allowed_fields),
                "train_rows": result.train_rows,
                "validation_rows": result.validation_rows,
                "selected_field": result.selected_field,
                "selected_value": result.selected_value,
                "training_candidate_rows": result.training_candidate_rows,
                "validation_candidate_rows": result.validation_candidate_rows,
                "training_baseline_stop_rate": str(
                    result.training_baseline_stop_rate
                ),
                "training_candidate_stop_rate": (
                    None
                    if result.training_candidate_stop_rate is None
                    else str(result.training_candidate_stop_rate)
                ),
                "validation_baseline_stop_rate": str(
                    result.validation_baseline_stop_rate
                ),
                "validation_candidate_stop_rate": (
                    None
                    if result.validation_candidate_stop_rate is None
                    else str(result.validation_candidate_stop_rate)
                ),
                "validation_baseline_p95_loss_r": str(
                    result.validation_baseline_p95_loss_r
                ),
                "validation_candidate_p95_loss_r": (
                    None
                    if result.validation_candidate_p95_loss_r is None
                    else str(result.validation_candidate_p95_loss_r)
                ),
                "minimum_train_support_met": result.minimum_train_support_met,
                "minimum_validation_support_met": (
                    result.minimum_validation_support_met
                ),
                "strict_validation_stop_rate_improvement": (
                    result.strict_validation_stop_rate_improvement
                ),
                "validation_tail_loss_not_worse": (
                    result.validation_tail_loss_not_worse
                ),
                "eligible_for_structural_leverage": (
                    result.eligible_for_structural_leverage
                ),
            }
        )

    eligible = tuple(
        row["lineage"]
        for row in results
        if row["eligible_for_structural_leverage"]
    )
    return {
        "schema": "qore.cibo.t02.burned_context_calibration.v1",
        "status": "PARTIAL_CAUSAL_STRUCTURAL_CALIBRATION",
        "calibration_source": "BURNED_PHASE18_ONLY",
        "selection_policy": (
            "TRAIN_ONLY_SINGLE_CATEGORICAL_STATE_MIN_STOP_RATE_"
            "WITH_SUPPORT_AND_10_PERCENT_RELATIVE_IMPROVEMENT"
        ),
        "train_fraction": "0.60",
        "validation_fraction": "0.40",
        "minimum_train_rows": 15,
        "minimum_train_fraction": "0.08",
        "required_train_relative_improvement": "0.10",
        "minimum_validation_rows": 20,
        "eligible_lineages": list(eligible),
        "ineligible_lineages": [
            row["lineage"]
            for row in results
            if not row["eligible_for_structural_leverage"]
        ],
        "lineages": results,
        "governance": {
            "holdout_2017h1_used": False,
            "holdout_2017h1_outcomes_used": False,
            "mae_mfe_used": False,
            "post_entry_path_features_used": False,
            "validation_used_to_select_category": False,
            "provider_usd_economics_claimed": False,
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
