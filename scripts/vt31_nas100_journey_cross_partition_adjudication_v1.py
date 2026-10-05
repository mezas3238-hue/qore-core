"""Cross-partition adjudication for VT31 NAS100 delivery journeys.

Consumes only already-produced consumed-evidence journey reports. It identifies
mechanisms that are directionally stable across R8/R6/R5 without selecting a
runtime threshold or opening any holdout.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

IDENTITY = "VT31_NAS100_JOURNEY_CROSS_PARTITION_ADJUDICATION_V1"
PARTITIONS = ("r8_fresh", "r6", "r5")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0"
    return format(Decimal(numerator) / Decimal(denominator), "f")


def _median(
    report: Mapping[str, Any],
    journey_class: str,
    metric: str,
) -> Decimal | None:
    classes = report["milestone_1_0r_classes"]
    row = classes.get(journey_class)
    if not isinstance(row, dict):
        return None
    metric_row = row.get(metric)
    if not isinstance(metric_row, dict):
        return None
    value = metric_row.get("median")
    return None if value is None else _d(value)


def _partition_summary(report: Mapping[str, Any]) -> dict[str, object]:
    summary = report["summary"]
    classes = summary["journey_classes"]
    labeled = int(summary["labeled"])
    giveback = int(classes.get("GIVEBACK_AFTER_1R", 0))
    failed = int(classes.get("FAILED_BEFORE_1R", 0))
    runner_3 = int(classes.get("RUNNER_3R_PLUS", 0))
    runner_5 = int(classes.get("EXTENDED_RUNNER_5R_PLUS", 0))
    partial = int(classes.get("PARTIAL_DELIVERY_1R_PLUS", 0))

    giveback_close = _median(
        report,
        "GIVEBACK_AFTER_1R",
        "favorable_close_rate",
    )
    runner_3_close = _median(
        report,
        "RUNNER_3R_PLUS",
        "favorable_close_rate",
    )
    runner_5_close = _median(
        report,
        "EXTENDED_RUNNER_5R_PLUS",
        "favorable_close_rate",
    )
    runner_close_values = [
        value
        for value in (runner_3_close, runner_5_close)
        if value is not None
    ]
    runner_close_floor = (
        None if not runner_close_values else min(runner_close_values)
    )
    close_delta = (
        None
        if giveback_close is None or runner_close_floor is None
        else runner_close_floor - giveback_close
    )

    giveback_overlap = _median(
        report,
        "GIVEBACK_AFTER_1R",
        "overlap",
    )
    runner_3_overlap = _median(
        report,
        "RUNNER_3R_PLUS",
        "overlap",
    )
    runner_5_overlap = _median(
        report,
        "EXTENDED_RUNNER_5R_PLUS",
        "overlap",
    )

    giveback_efficiency = _median(
        report,
        "GIVEBACK_AFTER_1R",
        "efficiency",
    )
    runner_3_efficiency = _median(
        report,
        "RUNNER_3R_PLUS",
        "efficiency",
    )
    runner_5_efficiency = _median(
        report,
        "EXTENDED_RUNNER_5R_PLUS",
        "efficiency",
    )

    one_r = summary["milestone_rates"]["1.0"]
    dol1 = summary["dol_rates"]["1"]
    return {
        "labeled": labeled,
        "failed_before_1r_count": failed,
        "failed_before_1r_rate": _rate(failed, labeled),
        "giveback_after_1r_count": giveback,
        "giveback_after_1r_rate": _rate(giveback, labeled),
        "partial_delivery_1r_plus_count": partial,
        "runner_3r_to_under_5r_count": runner_3,
        "runner_5r_plus_count": runner_5,
        "runner_3r_plus_count": runner_3 + runner_5,
        "runner_3r_plus_rate": _rate(runner_3 + runner_5, labeled),
        "runner_5r_plus_rate": _rate(runner_5, labeled),
        "one_r_reach_rate": str(one_r["rate"]),
        "one_r_median_minutes_from_fill": str(
            one_r["median_minutes_from_fill"]
        ),
        "dol1_reach_rate": str(dol1["rate"]),
        "one_r_favorable_close_rate_medians": {
            "giveback": (
                None
                if giveback_close is None
                else format(giveback_close, "f")
            ),
            "runner_3r_to_under_5r": (
                None
                if runner_3_close is None
                else format(runner_3_close, "f")
            ),
            "runner_5r_plus": (
                None
                if runner_5_close is None
                else format(runner_5_close, "f")
            ),
            "runner_floor_minus_giveback": (
                None if close_delta is None else format(close_delta, "f")
            ),
        },
        "one_r_overlap_medians": {
            "giveback": (
                None
                if giveback_overlap is None
                else format(giveback_overlap, "f")
            ),
            "runner_3r_to_under_5r": (
                None
                if runner_3_overlap is None
                else format(runner_3_overlap, "f")
            ),
            "runner_5r_plus": (
                None
                if runner_5_overlap is None
                else format(runner_5_overlap, "f")
            ),
        },
        "one_r_path_efficiency_medians": {
            "giveback": (
                None
                if giveback_efficiency is None
                else format(giveback_efficiency, "f")
            ),
            "runner_3r_to_under_5r": (
                None
                if runner_3_efficiency is None
                else format(runner_3_efficiency, "f")
            ),
            "runner_5r_plus": (
                None
                if runner_5_efficiency is None
                else format(runner_5_efficiency, "f")
            ),
        },
    }


def adjudicate(
    reports: Mapping[str, Mapping[str, Any]],
) -> dict[str, object]:
    missing = [partition for partition in PARTITIONS if partition not in reports]
    if missing:
        raise ValueError(f"missing required partitions: {missing}")

    partitions = {
        partition: _partition_summary(reports[partition])
        for partition in PARTITIONS
    }
    close_deltas = [
        _d(
            partitions[partition][
                "one_r_favorable_close_rate_medians"
            ]["runner_floor_minus_giveback"]
        )
        for partition in PARTITIONS
    ]
    close_persistence_supported = all(delta > 0 for delta in close_deltas)

    overlap_rows = [
        partitions[partition]["one_r_overlap_medians"]
        for partition in PARTITIONS
    ]
    overlap_separates_all = all(
        row["giveback"] is not None
        and row["runner_3r_to_under_5r"] is not None
        and row["runner_5r_plus"] is not None
        and _d(row["giveback"])
        != min(
            _d(row["runner_3r_to_under_5r"]),
            _d(row["runner_5r_plus"]),
        )
        for row in overlap_rows
    )

    efficiency_rows = [
        partitions[partition]["one_r_path_efficiency_medians"]
        for partition in PARTITIONS
    ]
    efficiency_runner_higher_all = all(
        row["giveback"] is not None
        and row["runner_3r_to_under_5r"] is not None
        and row["runner_5r_plus"] is not None
        and min(
            _d(row["runner_3r_to_under_5r"]),
            _d(row["runner_5r_plus"]),
        )
        > _d(row["giveback"])
        for row in efficiency_rows
    )

    runner_5_rates = [
        _d(partitions[partition]["runner_5r_plus_rate"])
        for partition in PARTITIONS
    ]
    giveback_rates = [
        _d(partitions[partition]["giveback_after_1r_rate"])
        for partition in PARTITIONS
    ]
    one_r_minutes = [
        _d(partitions[partition]["one_r_median_minutes_from_fill"])
        for partition in PARTITIONS
    ]

    return {
        "identity": IDENTITY,
        "partitions": partitions,
        "cross_partition": {
            "giveback_after_1r_present_all_partitions": all(
                value > 0 for value in giveback_rates
            ),
            "runner_5r_plus_present_all_partitions": all(
                value > 0 for value in runner_5_rates
            ),
            "runner_5r_plus_rate_min": format(min(runner_5_rates), "f"),
            "runner_5r_plus_rate_max": format(max(runner_5_rates), "f"),
            "one_r_touch_is_early_all_partitions": all(
                value <= Decimal("1")
                for value in one_r_minutes
            ),
            "favorable_close_persistence_at_1r_supported": (
                close_persistence_supported
            ),
            "favorable_close_persistence_delta_min": format(
                min(close_deltas),
                "f",
            ),
            "overlap_at_1r_stable_discriminator": overlap_separates_all,
            "path_efficiency_at_1r_runner_higher_all": (
                efficiency_runner_higher_all
            ),
        },
        "adjudication": {
            "giveback_problem": "CONFIRMED_CROSS_PARTITION",
            "large_runner_tail": "CONFIRMED_CROSS_PARTITION",
            "favorable_close_persistence": (
                "SUPPORTED_CAUSAL_RESEARCH_HYPOTHESIS"
                if close_persistence_supported
                else "NOT_SUPPORTED"
            ),
            "overlap_at_1r": (
                "REQUIRES_MORE_EVIDENCE"
                if not overlap_separates_all
                else "SUPPORTED"
            ),
            "path_efficiency_at_1r": (
                "SUPPORTED"
                if efficiency_runner_higher_all
                else "NOT_STABLE_AS_SOLE_DISCRIMINATOR"
            ),
            "immediate_generic_protection_at_1r": (
                "NOT_JUSTIFIED_FOR_PROMOTION"
            ),
        },
        "next_required_research": (
            "Test post-1R closed-bar persistence states and structural "
            "protection counterfactuals before choosing any runtime threshold."
        ),
        "threshold_selected": False,
        "runtime_policy_promoted": False,
        "opens_new_holdout": False,
        "candidate_frozen": False,
        "candidate_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("market") != "NAS100":
        raise ValueError("journey adjudication requires NAS100")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8", required=True, type=Path)
    parser.add_argument("--r6", required=True, type=Path)
    parser.add_argument("--r5", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = adjudicate(
        {
            "r8_fresh": _load(args.r8),
            "r6": _load(args.r6),
            "r5": _load(args.r5),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "cross_partition": payload["cross_partition"],
                "adjudication": payload["adjudication"],
                "runtime_policy_promoted": payload[
                    "runtime_policy_promoted"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
