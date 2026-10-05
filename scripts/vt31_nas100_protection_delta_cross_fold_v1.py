"""Cross-fold delta forensics for VT31 cognitive structural protection.

Consumes trade-row outputs from the protection frontier and attributes only the
change caused by post-entry protection. Diagnostic only; no runtime policy is
selected by this script.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

SCHEMA = "qore.vt31.nas100.protection_delta_cross_fold.v1"
FOLDS = ("r5", "r6", "r8", "consumed")
VARIANTS = (
    "BREAKER_NONDEEP_PS1",
    "LAST_BREAKER_BREAKER_PS1",
    "PATH_NOT_COMPRESSED_PS1",
    "NEGATIVE_UNION_PS1",
    "NEGATIVE_UNION_PS2",
)
MIN_CHANGED_PER_FOLD = 3


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _margin_bucket(row: dict[str, object]) -> str:
    margin = int(cast(int, row["support_score"])) - int(
        cast(int, row["caution_score"])
    )
    if margin <= -5:
        return "LE_NEG5"
    if margin <= -2:
        return "NEG4_TO_NEG2"
    if margin <= 1:
        return "NEG1_TO_POS1"
    if margin <= 4:
        return "POS2_TO_POS4"
    return "GE_POS5"


def _delta_metrics(values: list[Decimal]) -> dict[str, object]:
    if not values:
        return {
            "sample": 0,
            "mean_delta_r": None,
            "total_delta_r": "0",
            "improved": 0,
            "worsened": 0,
            "unchanged": 0,
        }
    total = sum(values, Decimal(0))
    return {
        "sample": len(values),
        "mean_delta_r": format(total / Decimal(len(values)), "f"),
        "total_delta_r": format(total, "f"),
        "improved": sum(value > 0 for value in values),
        "worsened": sum(value < 0 for value in values),
        "unchanged": sum(value == 0 for value in values),
    }


def _fold_variant(
    payload: dict[str, object],
    variant: str,
) -> dict[str, object]:
    rows = cast(
        dict[str, list[dict[str, object]]],
        payload["trade_rows"],
    )
    base = {
        str(row["trade_id"]): row
        for row in rows["BASELINE"]
    }
    candidate = {
        str(row["trade_id"]): row
        for row in rows[variant]
    }

    deltas: list[dict[str, object]] = []
    for trade_id, base_row in base.items():
        candidate_row = candidate.get(trade_id)
        if candidate_row is None:
            continue
        base_r = _d(base_row["r_multiple"])
        candidate_r = _d(candidate_row["r_multiple"])
        delta = candidate_r - base_r
        if delta == 0:
            continue
        deltas.append(
            {
                "trade_id": trade_id,
                "delta_r": format(delta, "f"),
                "baseline_r": format(base_r, "f"),
                "candidate_r": format(candidate_r, "f"),
                "destination_state": candidate_row[
                    "destination_state"
                ],
                "management_context": candidate_row[
                    "management_context"
                ],
                "path_not_compressed": candidate_row[
                    "path_not_compressed"
                ],
                "support_margin_bucket": _margin_bucket(candidate_row),
                "baseline_exit_reason": base_row["exit_reason"],
                "candidate_exit_reason": candidate_row["exit_reason"],
            }
        )

    group_specs = {
        "destination": lambda row: str(row["destination_state"]),
        "context": lambda row: str(row["management_context"]),
        "path_not_compressed": lambda row: str(
            row["path_not_compressed"]
        ),
        "support_margin": lambda row: str(
            row["support_margin_bucket"]
        ),
        "destination_x_margin": lambda row: (
            f"{row['destination_state']}|"
            f"{row['support_margin_bucket']}"
        ),
        "destination_x_path": lambda row: (
            f"{row['destination_state']}|"
            f"path={row['path_not_compressed']}"
        ),
    }
    grouped: dict[str, object] = {}
    for name, key_fn in group_specs.items():
        values: dict[str, list[Decimal]] = defaultdict(list)
        for row in deltas:
            values[key_fn(row)].append(_d(row["delta_r"]))
        grouped[name] = {
            key: _delta_metrics(items)
            for key, items in sorted(values.items())
        }

    return {
        "changed_trade_count": len(deltas),
        "overall_delta": _delta_metrics(
            [_d(row["delta_r"]) for row in deltas]
        ),
        "groups": grouped,
        "rows": deltas,
    }


def analyze(paths: dict[str, Path]) -> dict[str, object]:
    payloads = {
        fold: json.loads(paths[fold].read_text(encoding="utf-8"))
        for fold in FOLDS
    }
    per_variant = {
        variant: {
            fold: _fold_variant(payloads[fold], variant)
            for fold in FOLDS
        }
        for variant in VARIANTS
    }

    stable_positive: list[dict[str, object]] = []
    stable_negative: list[dict[str, object]] = []
    for variant, fold_data in per_variant.items():
        group_names = cast(
            dict[str, object],
            fold_data["r5"]["groups"],
        ).keys()
        for group_name in group_names:
            states: set[str] = set()
            for fold in FOLDS:
                block = cast(
                    dict[str, dict[str, object]],
                    cast(
                        dict[str, object],
                        fold_data[fold]["groups"],
                    )[group_name],
                )
                states.update(block)
            for state in sorted(states):
                metrics: dict[str, dict[str, object]] = {}
                for fold in FOLDS:
                    block = cast(
                        dict[str, dict[str, object]],
                        cast(
                            dict[str, object],
                            fold_data[fold]["groups"],
                        )[group_name],
                    )
                    if state in block:
                        metrics[fold] = block[state]
                if set(metrics) != set(FOLDS):
                    continue
                if not all(
                    int(cast(int, item["sample"]))
                    >= MIN_CHANGED_PER_FOLD
                    for item in metrics.values()
                ):
                    continue
                means = [
                    _d(metrics[fold]["mean_delta_r"])
                    for fold in FOLDS
                ]
                record = {
                    "variant": variant,
                    "group": group_name,
                    "state": state,
                    "per_fold": metrics,
                }
                if all(value > 0 for value in means):
                    stable_positive.append(record)
                elif all(value < 0 for value in means):
                    stable_negative.append(record)

    return {
        "schema": SCHEMA,
        "folds": list(FOLDS),
        "minimum_changed_per_fold": MIN_CHANGED_PER_FOLD,
        "variants": per_variant,
        "stable_positive_delta_states": stable_positive,
        "stable_negative_delta_states": stable_negative,
        "governance": {
            "diagnostic_only": True,
            "post_entry_delta_only": True,
            "fold_identity_runtime_input": False,
            "terminal_pnl_runtime_input": False,
            "runtime_policy_promoted": False,
            "capital_weighting_used": False,
            "position_sizing_used": False,
            "absolute_volume_used": False,
            "opens_new_holdout": False,
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
                "stable_positive_delta_states": payload[
                    "stable_positive_delta_states"
                ],
                "stable_negative_delta_states": payload[
                    "stable_negative_delta_states"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
