"""Cross-fold stability analysis for VT31 full-cognition attribution.

Diagnostic only. It consumes attribution artifacts from R5, R6, R8 and the
consumed 2Y window, then identifies cognition states with consistent economic
sign. It never promotes a runtime rule or opens a holdout.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

SCHEMA = "qore.vt31.nas100.full_cognition_cross_fold.v1"
FOLDS = ("r5", "r6", "r8", "consumed")
MIN_SAMPLE_PER_FOLD = 10
CATEGORIES = (
    "by_management_context",
    "by_destination_state",
    "by_support_margin",
    "by_entry_family",
    "by_reference_volatility",
    "by_context_destination",
    "by_family_destination",
    "signal_metrics_min_sample_10",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _eligible(metric: dict[str, object]) -> bool:
    return (
        int(cast(int, metric["sample"])) >= MIN_SAMPLE_PER_FOLD
        and metric["mean_r"] is not None
        and metric["profit_factor"] is not None
    )


def _classification(
    per_fold: dict[str, dict[str, object]],
) -> str:
    if set(per_fold) != set(FOLDS):
        return "INCOMPLETE"
    if not all(_eligible(item) for item in per_fold.values()):
        return "INSUFFICIENT_SAMPLE"

    means = [_d(per_fold[fold]["mean_r"]) for fold in FOLDS]
    pfs = [_d(per_fold[fold]["profit_factor"]) for fold in FOLDS]
    if all(value > 0 for value in means) and all(value > 1 for value in pfs):
        if all(value >= Decimal("1.15") for value in pfs):
            return "STRONG_POSITIVE_4_OF_4"
        return "POSITIVE_4_OF_4"
    if all(value < 0 for value in means) and all(value < 1 for value in pfs):
        if all(value <= Decimal("0.85") for value in pfs):
            return "STRONG_NEGATIVE_4_OF_4"
        return "NEGATIVE_4_OF_4"
    return "MIXED"


def _analyze_category(
    payloads: dict[str, dict[str, object]],
    category: str,
) -> dict[str, object]:
    states: set[str] = set()
    for payload in payloads.values():
        block = cast(dict[str, object], payload[category])
        states.update(block)

    result: dict[str, object] = {}
    for state in sorted(states):
        per_fold: dict[str, dict[str, object]] = {}
        for fold in FOLDS:
            block = cast(
                dict[str, dict[str, object]],
                payloads[fold][category],
            )
            if state in block:
                per_fold[fold] = block[state]
        label = _classification(per_fold)
        result[state] = {
            "classification": label,
            "per_fold": per_fold,
            "minimum_sample": (
                min(
                    int(cast(int, item["sample"]))
                    for item in per_fold.values()
                )
                if per_fold
                else 0
            ),
            "minimum_pf": (
                format(
                    min(
                        _d(item["profit_factor"])
                        for item in per_fold.values()
                        if item["profit_factor"] is not None
                    ),
                    "f",
                )
                if per_fold
                and all(
                    item["profit_factor"] is not None
                    for item in per_fold.values()
                )
                else None
            ),
            "minimum_mean_r": (
                format(
                    min(
                        _d(item["mean_r"])
                        for item in per_fold.values()
                        if item["mean_r"] is not None
                    ),
                    "f",
                )
                if per_fold
                and all(
                    item["mean_r"] is not None
                    for item in per_fold.values()
                )
                else None
            ),
        }
    return result


def analyze(paths: dict[str, Path]) -> dict[str, object]:
    payloads = {
        fold: json.loads(paths[fold].read_text(encoding="utf-8"))
        for fold in FOLDS
    }
    for fold, payload in payloads.items():
        governance = payload["governance"]
        assert governance["consumed_evidence_only"] is True
        assert governance["normalized_equal_r_economics"] is True
        assert governance["capital_weighted_net_r_used"] is False
        assert governance["position_sizing_used"] is False
        assert governance["absolute_volume_used"] is False
        assert governance["opens_new_holdout"] is False
        if fold == "consumed":
            assert payload["market"] == "NAS100"

    categories = {
        category: _analyze_category(payloads, category)
        for category in CATEGORIES
    }
    stable_positive: list[dict[str, object]] = []
    stable_negative: list[dict[str, object]] = []
    for category, block in categories.items():
        for state, item_raw in cast(
            dict[str, dict[str, object]],
            block,
        ).items():
            item = dict(item_raw)
            record = {
                "category": category,
                "state": state,
                **item,
            }
            label = str(item["classification"])
            if "POSITIVE_4_OF_4" in label:
                stable_positive.append(record)
            elif "NEGATIVE_4_OF_4" in label:
                stable_negative.append(record)

    stable_positive.sort(
        key=lambda item: (
            -int(cast(int, item["minimum_sample"])),
            str(item["category"]),
            str(item["state"]),
        )
    )
    stable_negative.sort(
        key=lambda item: (
            -int(cast(int, item["minimum_sample"])),
            str(item["category"]),
            str(item["state"]),
        )
    )

    return {
        "schema": SCHEMA,
        "folds": list(FOLDS),
        "minimum_sample_per_fold": MIN_SAMPLE_PER_FOLD,
        "overall": {
            fold: payloads[fold]["overall_normalized"]
            for fold in FOLDS
        },
        "categories": categories,
        "stable_positive": stable_positive,
        "stable_negative": stable_negative,
        "governance": {
            "diagnostic_only": True,
            "fold_identity_runtime_input": False,
            "terminal_pnl_runtime_input": False,
            "calendar_rule_promoted": False,
            "runtime_rule_promoted": False,
            "normalized_equal_r_economics": True,
            "capital_weighting_used": False,
            "position_sizing_used": False,
            "absolute_volume_used": False,
            "opens_new_holdout": False,
            "candidate_certified": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for fold in FOLDS:
        parser.add_argument(f"--{fold}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {
        fold: cast(Path, getattr(args, fold))
        for fold in FOLDS
    }
    payload = analyze(paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "overall": payload["overall"],
                "stable_positive": payload["stable_positive"],
                "stable_negative": payload["stable_negative"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
