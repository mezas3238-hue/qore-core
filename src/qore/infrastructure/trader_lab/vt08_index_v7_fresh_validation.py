"""Frozen one-shot fresh-holdout adjudication for VT-08 Index V7."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt08_index_v7_ttrades_source_corrected import (
    CANDIDATE_ID,
    RULE_FINGERPRINT,
)
from qore.kernel.errors import InfrastructureError

HOLDOUT_START = "2018-09-15"
HOLDOUT_END_EXCLUSIVE = "2020-09-15"
MIN_SAMPLE = 30
MIN_PRIMARY_PF = Decimal("1.15")
MAX_PRIMARY_DD_R = Decimal("15")
MIN_SUPPORTED_MARKET = 8
MIN_SUPPORTED_SIDE = 10
MIN_SUPPORTED_MEAN_R = Decimal("-0.10")


class Vt08IndexV7FreshValidationError(InfrastructureError):
    __slots__ = ()


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict:
        raise Vt08IndexV7FreshValidationError(f"{name} must be object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08IndexV7FreshValidationError(f"{name} must be array")
    return cast(list[object], value)


def _integer(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise Vt08IndexV7FreshValidationError(f"{name} must be integer")
    return value


def _decimal(value: object, *, name: str) -> Decimal:
    if type(value) is not str:
        raise Vt08IndexV7FreshValidationError(f"{name} must be decimal string")
    try:
        return Decimal(value)
    except Exception as error:
        raise Vt08IndexV7FreshValidationError(f"{name} is invalid decimal") from error


def _profit_factor(metrics: dict[str, object], *, name: str) -> Decimal:
    value = metrics.get("profit_factor")
    if value is None:
        wins = _integer(metrics.get("wins"), name=f"{name}.wins")
        losses = _integer(metrics.get("losses"), name=f"{name}.losses")
        if wins > 0 and losses == 0:
            return Decimal("Infinity")
        return Decimal()
    return _decimal(value, name=f"{name}.profit_factor")


def _supported_breakdown_gate(
    raw: object, *, name: str, minimum_sample: int
) -> tuple[bool, dict[str, object]]:
    breakdown = _object(raw, name=name)
    details: dict[str, object] = {}
    passed = True
    for label, raw_metrics in sorted(breakdown.items()):
        metrics = _object(raw_metrics, name=f"{name}.{label}")
        sample = _integer(metrics.get("sample"), name=f"{name}.{label}.sample")
        mean_r = _decimal(metrics.get("mean_r"), name=f"{name}.{label}.mean_r")
        supported = sample >= minimum_sample
        item_pass = (not supported) or mean_r > MIN_SUPPORTED_MEAN_R
        details[label] = {
            "sample": sample,
            "mean_r": str(mean_r),
            "supported": supported,
            "pass": item_pass,
        }
        passed = passed and item_pass
    return passed, details


def validate_report(report: dict[str, object]) -> dict[str, object]:
    if report.get("candidate_id") != CANDIDATE_ID:
        raise Vt08IndexV7FreshValidationError("candidate identity drifted")
    if report.get("rule_fingerprint") != RULE_FINGERPRINT:
        raise Vt08IndexV7FreshValidationError("rule fingerprint drifted")
    partition = _object(report.get("partition"), name="partition")
    if partition != {
        "start_date": HOLDOUT_START,
        "end_date_exclusive": HOLDOUT_END_EXCLUSIVE,
    }:
        raise Vt08IndexV7FreshValidationError("fresh partition drifted")

    primary = _object(report.get("metrics_primary_stress"), name="primary")
    secondary = _object(report.get("metrics_secondary_stress"), name="secondary")
    sample = _integer(primary.get("sample"), name="primary.sample")
    primary_mean = _decimal(primary.get("mean_r"), name="primary.mean_r")
    primary_pf = _profit_factor(primary, name="primary")
    primary_dd = _decimal(primary.get("max_drawdown_r"), name="primary.max_drawdown_r")
    secondary_mean = _decimal(secondary.get("mean_r"), name="secondary.mean_r")
    secondary_pf = _profit_factor(secondary, name="secondary")

    halves = _array(report.get("halves_primary_stress"), name="halves_primary_stress")
    if len(halves) != 2:
        raise Vt08IndexV7FreshValidationError("fresh halves must contain two partitions")
    half_means = tuple(
        _decimal(
            _object(item, name=f"half[{index}]").get("mean_r"),
            name=f"half[{index}].mean_r",
        )
        for index, item in enumerate(halves)
    )

    quartiles = _array(
        report.get("quartile_mean_r_primary_stress"),
        name="quartile_mean_r_primary_stress",
    )
    if len(quartiles) != 4:
        raise Vt08IndexV7FreshValidationError("fresh quartiles must contain four partitions")
    quartile_means = tuple(
        _decimal(item, name=f"quartile[{index}]") for index, item in enumerate(quartiles)
    )
    quartile_sizes = tuple(
        (sample * (index + 1)) // 4 - (sample * index) // 4 for index in range(4)
    )
    quartile_passes = tuple(
        size >= 5 and mean > 0 for size, mean in zip(quartile_sizes, quartile_means, strict=True)
    )

    market_pass, market_details = _supported_breakdown_gate(
        report.get("by_market_primary_stress"),
        name="by_market_primary_stress",
        minimum_sample=MIN_SUPPORTED_MARKET,
    )
    side_pass, side_details = _supported_breakdown_gate(
        report.get("by_side_primary_stress"),
        name="by_side_primary_stress",
        minimum_sample=MIN_SUPPORTED_SIDE,
    )

    gates = {
        "sample_ge_30": sample >= MIN_SAMPLE,
        "primary_mean_positive": primary_mean > 0,
        "primary_pf_ge_1_15": primary_pf >= MIN_PRIMARY_PF,
        "primary_max_dd_le_15r": primary_dd <= MAX_PRIMARY_DD_R,
        "both_halves_positive": all(mean > 0 for mean in half_means),
        "three_of_four_quartiles_positive": sum(quartile_passes) >= 3,
        "secondary_mean_positive": secondary_mean > 0,
        "secondary_pf_gt_1": secondary_pf > 1,
        "supported_markets_not_materially_negative": market_pass,
        "supported_sides_not_materially_negative": side_pass,
    }
    passed = all(gates.values())
    return {
        "schema": "qore.trader_lab.vt08_index_v7_fresh_validation.v1",
        "candidate_id": CANDIDATE_ID,
        "rule_fingerprint": RULE_FINGERPRINT,
        "partition": partition,
        "fresh_holdout_opened": True,
        "fresh_holdout_pass": passed,
        "gates": gates,
        "metrics": {
            "sample": sample,
            "primary_mean_r": str(primary_mean),
            "primary_profit_factor": str(primary_pf),
            "primary_max_drawdown_r": str(primary_dd),
            "half_mean_r": [str(value) for value in half_means],
            "quartile_sizes": list(quartile_sizes),
            "quartile_mean_r": [str(value) for value in quartile_means],
            "quartile_pass": list(quartile_passes),
            "secondary_mean_r": str(secondary_mean),
            "secondary_profit_factor": str(secondary_pf),
            "markets": market_details,
            "sides": side_details,
        },
        "governance": {
            "post_result_tuning_permitted": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        decoded: object = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt08IndexV7FreshValidationError("cannot read V7 fresh report") from error
    report = _object(decoded, name="report")
    result = validate_report(report)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
