"""Cross-fold causal route evidence for VT31 NAS100 reasoning.

Consumed development evidence only.

This lab does not select a production policy.  It asks a narrower question:
which pre-entry route/context classes keep the same sign when each one of the
four consumed folds is treated as the held-out fold?

The upstream inputs are the immutable ALLOC_G regime-root-cause artifacts.
No dates, fold labels, terminal PnL, or post-outcome fields are emitted as
runtime rules.  Fold identity exists only in this research harness.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

SCHEMA = "qore.vt31.nas100.family_reasoning_cross_fold.v1"
IDENTITY = "VT31_NAS100_FAMILY_REASONING_CROSS_FOLD_V1"
FOLDS = ("r5", "r6", "r8", "consumed_holdout")
MIN_SAMPLE_PER_FOLD = 10

INTERACTIONS = (
    "tier_x_family",
    "tier_x_h1",
    "tier_x_cash_open",
    "tier_x_confirmation_latency",
    "tier_x_current_path",
    "tier_x_family_x_h1",
    "tier_x_family_x_cash_open",
    "tier_x_family_x_confirmation_latency",
    "tier_x_family_x_current_path",
    "tier_x_family_x_reference_volatility",
    "family_x_h1",
    "family_x_cash_open",
    "family_x_premarket",
    "family_x_confirmation_latency",
    "family_x_current_path",
    "family_x_reference_volatility",
    "family_x_reclaim_age",
    "family_x_risk_ref",
    "family_x_prior_day",
    "family_x_last_structure",
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    partition = payload.get("partition")
    if partition not in FOLDS:
        raise ValueError(f"unexpected partition: {partition}")
    if payload.get("market") != "NAS100":
        raise ValueError("family reasoning lab requires NAS100")
    governance = payload.get("governance", {})
    if governance.get("consumed_evidence_only") is not True:
        raise ValueError("upstream artifact must be consumed-evidence only")
    return payload


def _metric(payload: dict[str, Any], interaction: str, key: str) -> dict[str, Any]:
    return payload["overall"]["interactions"][interaction][key]


def _mean(metric: dict[str, Any]) -> Decimal:
    return Decimal(str(metric["mean_r"]))


def _pf(metric: dict[str, Any]) -> Decimal | None:
    value = metric.get("profit_factor")
    return None if value is None else Decimal(str(value))


def _sample(metric: dict[str, Any]) -> int:
    return int(metric["sample"])


def analyze(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if set(inputs) != set(FOLDS):
        raise ValueError("exactly four named consumed folds are required")

    positive: list[dict[str, Any]] = []
    negative: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for interaction in INTERACTIONS:
        maps = [
            inputs[fold]["overall"]["interactions"].get(interaction, {})
            for fold in FOLDS
        ]
        common = set(maps[0])
        for item in maps[1:]:
            common &= set(item)

        for key in sorted(common):
            per_fold = {
                fold: _metric(inputs[fold], interaction, key)
                for fold in FOLDS
            }
            samples = {
                fold: _sample(per_fold[fold])
                for fold in FOLDS
            }
            if min(samples.values()) < MIN_SAMPLE_PER_FOLD:
                continue

            means = {
                fold: _mean(per_fold[fold])
                for fold in FOLDS
            }
            leave_one_out: dict[str, dict[str, Any]] = {}
            all_holdouts_positive = True
            all_holdouts_negative = True

            for heldout in FOLDS:
                training = tuple(fold for fold in FOLDS if fold != heldout)
                training_positive = all(means[fold] > 0 for fold in training)
                training_negative = all(means[fold] < 0 for fold in training)
                heldout_positive = means[heldout] > 0
                heldout_negative = means[heldout] < 0
                leave_one_out[heldout] = {
                    "training_folds": list(training),
                    "training_positive": training_positive,
                    "training_negative": training_negative,
                    "heldout_mean_r": format(means[heldout], "f"),
                    "heldout_positive": heldout_positive,
                    "heldout_negative": heldout_negative,
                    "generalizes_positive": (
                        training_positive and heldout_positive
                    ),
                    "generalizes_negative": (
                        training_negative and heldout_negative
                    ),
                }
                all_holdouts_positive &= (
                    training_positive and heldout_positive
                )
                all_holdouts_negative &= (
                    training_negative and heldout_negative
                )

            item = {
                "interaction": interaction,
                "class": key,
                "min_sample_per_fold": min(samples.values()),
                "samples": samples,
                "means_r": {
                    fold: format(means[fold], "f")
                    for fold in FOLDS
                },
                "profit_factors": {
                    fold: (
                        None
                        if _pf(per_fold[fold]) is None
                        else format(_pf(per_fold[fold]), "f")
                    )
                    for fold in FOLDS
                },
                "leave_one_out": leave_one_out,
            }
            if all_holdouts_positive:
                positive.append(item)
            elif all_holdouts_negative:
                negative.append(item)
            else:
                rejected.append(item)

    positive.sort(
        key=lambda item: (
            -int(item["min_sample_per_fold"]),
            str(item["interaction"]),
            str(item["class"]),
        )
    )
    negative.sort(
        key=lambda item: (
            -int(item["min_sample_per_fold"]),
            str(item["interaction"]),
            str(item["class"]),
        )
    )

    route_positive = [
        item
        for item in positive
        if str(item["interaction"]).startswith("tier_x_")
    ]
    route_negative = [
        item
        for item in negative
        if str(item["interaction"]).startswith("tier_x_")
    ]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "NAS100",
        "folds": list(FOLDS),
        "minimum_sample_per_fold": MIN_SAMPLE_PER_FOLD,
        "predeclared_interactions": list(INTERACTIONS),
        "leave_one_fold_out_positive_classes": positive,
        "leave_one_fold_out_negative_classes": negative,
        "route_positive_classes": route_positive,
        "route_negative_classes": route_negative,
        "rejected_mixed_sign_classes": rejected,
        "summary": {
            "positive_class_count": len(positive),
            "negative_class_count": len(negative),
            "route_positive_class_count": len(route_positive),
            "route_negative_class_count": len(route_negative),
        },
        "governance": {
            "consumed_evidence_only": True,
            "pre_entry_interactions_only": True,
            "fold_identity_used_only_for_research_validation": True,
            "fold_identity_allowed_at_runtime": False,
            "terminal_pnl_allowed_at_runtime": False,
            "calendar_date_allowed_as_runtime_rule": False,
            "minimum_sample_predeclared": True,
            "interaction_set_predeclared": True,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for fold in FOLDS:
        parser.add_argument(f"--{fold.replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    inputs = {
        "r5": _load(args.r5),
        "r6": _load(args.r6),
        "r8": _load(args.r8),
        "consumed_holdout": _load(args.consumed_holdout),
    }
    payload = analyze(inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "summary": payload["summary"],
                "route_positive_classes": payload["route_positive_classes"],
                "route_negative_classes": payload["route_negative_classes"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
