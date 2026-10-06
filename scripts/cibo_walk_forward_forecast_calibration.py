#!/usr/bin/env python3
"""Postdecision calibration diagnostics for causal CIBO walk-forward forecasts.

This script evaluates forecasts only after the frozen historical outcome is
available. It never writes expectation inputs back into the manifest and has no
sizing, Risk, execution, tuning or certification authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    validate_single_account_manifest_sha256,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    manifest_row_to_shadow_outcome_observation,
)


@dataclass(frozen=True, slots=True)
class _CalibrationRow:
    trader_id: str
    expected_r: Decimal
    realized_r: Decimal
    expected_minutes: Decimal
    realized_minutes: Decimal
    evidence_age_minutes: Decimal
    observation_count: int
    block_dispersion_r: Decimal


def _d(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            f"{name} must be Decimal-compatible"
        ) from error
    if not result.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite")
    return result


def _dt(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(f"{name} must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")
    return result


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    with localcontext() as context:
        context.prec = 100
        return sum(values, Decimal(0)) / Decimal(len(values))


def _median(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    with localcontext() as context:
        context.prec = 100
        return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _summary(rows: list[_CalibrationRow]) -> dict[str, object]:
    if not rows:
        return {"forecast_count": 0}

    expected_r = [item.expected_r for item in rows]
    realized_r = [item.realized_r for item in rows]
    errors = [
        item.expected_r - item.realized_r
        for item in rows
    ]
    abs_errors = [abs(value) for value in errors]
    squared_errors = [value * value for value in errors]
    expected_minutes = [item.expected_minutes for item in rows]
    realized_minutes = [item.realized_minutes for item in rows]
    duration_errors = [
        item.expected_minutes - item.realized_minutes
        for item in rows
    ]
    duration_ratios = [
        item.realized_minutes / item.expected_minutes
        for item in rows
    ]
    positive = [item for item in rows if item.expected_r > 0]
    nonpositive = [item for item in rows if item.expected_r <= 0]
    sign_correct = sum(
        1
        for item in rows
        if (
            (item.expected_r > 0 and item.realized_r > 0)
            or (item.expected_r <= 0 and item.realized_r <= 0)
        )
    )

    with localcontext() as context:
        context.prec = 100
        rmse = _mean(squared_errors).sqrt()
        sign_accuracy = Decimal(sign_correct) / Decimal(len(rows))
        positive_hit = (
            Decimal(sum(1 for item in positive if item.realized_r > 0))
            / Decimal(len(positive))
            if positive
            else Decimal(0)
        )
        nonpositive_realized_positive = (
            Decimal(sum(1 for item in nonpositive if item.realized_r > 0))
            / Decimal(len(nonpositive))
            if nonpositive
            else Decimal(0)
        )

    return {
        "forecast_count": len(rows),
        "mean_expected_structural_r": _fmt(_mean(expected_r)),
        "mean_realized_structural_r": _fmt(_mean(realized_r)),
        "forecast_bias_expected_minus_realized_r": _fmt(_mean(errors)),
        "mean_absolute_error_r": _fmt(_mean(abs_errors)),
        "root_mean_square_error_r": _fmt(rmse),
        "positive_forecast_count": len(positive),
        "realized_positive_rate_when_forecast_positive": _fmt(positive_hit),
        "nonpositive_forecast_count": len(nonpositive),
        "realized_positive_rate_when_forecast_nonpositive": _fmt(
            nonpositive_realized_positive
        ),
        "sign_accuracy": _fmt(sign_accuracy),
        "mean_expected_capital_minutes": _fmt(_mean(expected_minutes)),
        "mean_realized_capital_minutes": _fmt(_mean(realized_minutes)),
        "mean_duration_error_expected_minus_realized_minutes": _fmt(
            _mean(duration_errors)
        ),
        "mean_absolute_duration_error_minutes": _fmt(
            _mean([abs(value) for value in duration_errors])
        ),
        "mean_actual_over_expected_duration_ratio": _fmt(
            _mean(duration_ratios)
        ),
        "median_evidence_age_minutes": _fmt(
            _median([item.evidence_age_minutes for item in rows])
        ),
        "max_evidence_age_minutes": _fmt(
            max(item.evidence_age_minutes for item in rows)
        ),
        "minimum_observation_count": min(item.observation_count for item in rows),
        "median_observation_count": _fmt(
            _median([Decimal(item.observation_count) for item in rows])
        ),
        "maximum_observation_count": max(item.observation_count for item in rows),
        "median_block_dispersion_r": _fmt(
            _median([item.block_dispersion_r for item in rows])
        ),
    }


def _observation_bucket(count: int) -> str:
    if count < 10:
        return "05_09"
    if count < 25:
        return "10_24"
    if count < 50:
        return "25_49"
    if count < 100:
        return "50_99"
    return "100_plus"


def _staleness_bucket(minutes: Decimal) -> str:
    if minutes <= Decimal(60):
        return "00_60m"
    if minutes <= Decimal(1440):
        return "01h_24h"
    if minutes <= Decimal(10080):
        return "01d_07d"
    return "07d_plus"


def build_calibration_report(manifest: dict[str, Any]) -> dict[str, object]:
    manifest_sha = validate_single_account_manifest_sha256(manifest)
    rows = manifest.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise CiboCapitalManagementError(
            "walk-forward calibration requires opportunity rows"
        )

    calibrated: list[_CalibrationRow] = []
    cold_start_count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "walk-forward calibration row must be mapping"
            )
        expectation = row.get("expectation")
        if not isinstance(expectation, dict):
            raise CiboCapitalManagementError(
                "walk-forward calibration expectation missing"
            )
        basis = expectation.get("basis")
        if basis == CausalExpectationBasis.COLD_START_NO_FORECAST.value:
            cold_start_count += 1
            continue
        if basis != CausalExpectationBasis.WALK_FORWARD_EMPIRICAL_FORECAST.value:
            raise CiboCapitalManagementError(
                "walk-forward calibration found non-causal forecast basis"
            )
        if expectation.get("walk_forward_cold_start") is not False:
            raise CiboCapitalManagementError(
                "walk-forward calibration forecast/cold-start drift"
            )

        decision_at = _dt(
            row.get("market_decision_at"),
            "market_decision_at",
        )
        evidence_available_at = _dt(
            expectation.get("evidence_available_at"),
            "evidence_available_at",
        )
        if evidence_available_at > decision_at:
            raise CiboCapitalManagementError(
                "walk-forward calibration found future expectation evidence"
            )
        observation_count = expectation.get("walk_forward_observation_count")
        if (
            not isinstance(observation_count, int)
            or isinstance(observation_count, bool)
            or observation_count < 5
        ):
            raise CiboCapitalManagementError(
                "walk-forward calibration observation count invalid"
            )
        block_means_raw = expectation.get("walk_forward_block_means_r")
        if not isinstance(block_means_raw, list) or len(block_means_raw) != 5:
            raise CiboCapitalManagementError(
                "walk-forward calibration block means invalid"
            )
        block_means = [
            _d(value, "walk_forward_block_mean_r")
            for value in block_means_raw
        ]
        expected_r = _d(
            expectation.get("walk_forward_expected_structural_r"),
            "walk_forward_expected_structural_r",
        )
        expected_minutes = _d(
            expectation.get("expected_capital_minutes"),
            "expected_capital_minutes",
        )
        if expected_minutes <= 0:
            raise CiboCapitalManagementError(
                "walk-forward calibration expected duration must be positive"
            )

        outcome = manifest_row_to_shadow_outcome_observation(row)
        with localcontext() as context:
            context.prec = 100
            evidence_age_minutes = (
                Decimal(str((decision_at - evidence_available_at).total_seconds()))
                / Decimal(60)
            )
        calibrated.append(
            _CalibrationRow(
                trader_id=str(row.get("trader_id", "")),
                expected_r=expected_r,
                realized_r=outcome.gross_structural_outcome_r,
                expected_minutes=expected_minutes,
                realized_minutes=outcome.capital_minutes,
                evidence_age_minutes=evidence_age_minutes,
                observation_count=observation_count,
                block_dispersion_r=max(block_means) - min(block_means),
            )
        )

    by_trader: dict[str, list[_CalibrationRow]] = defaultdict(list)
    by_observations: dict[str, list[_CalibrationRow]] = defaultdict(list)
    by_staleness: dict[str, list[_CalibrationRow]] = defaultdict(list)
    for item in calibrated:
        by_trader[item.trader_id].append(item)
        by_observations[_observation_bucket(item.observation_count)].append(item)
        by_staleness[_staleness_bucket(item.evidence_age_minutes)].append(item)

    return {
        "schema": "qore.cibo.walk-forward-forecast-calibration.v1",
        "manifest_sha256": manifest_sha,
        "forecast_count": len(calibrated),
        "cold_start_count": cold_start_count,
        "future_outcome_used_for_forecast": False,
        "outcome_used_for_predecision": False,
        "outcome_aware_tuning": False,
        "certification_claimed": False,
        "research_only": True,
        "global": _summary(calibrated),
        "by_trader": {
            key: _summary(value)
            for key, value in sorted(by_trader.items())
        },
        "by_observation_count_bucket": {
            key: _summary(value)
            for key, value in sorted(by_observations.items())
        },
        "by_evidence_staleness_bucket": {
            key: _summary(value)
            for key, value in sorted(by_staleness.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = build_calibration_report(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
