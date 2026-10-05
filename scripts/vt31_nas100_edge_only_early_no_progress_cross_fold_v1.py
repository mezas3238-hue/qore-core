"""Cross-fold diagnostics for VT31 edge-only early no-progress scratches.

Consumes only already-generated consumed-evidence reports. It attributes the
delta caused by SCRATCH_5M / SCRATCH_8M and groups changed trades by causal
cognition fields that were already present at the scratch checkpoint.

Diagnostic only: this script does not select or promote a runtime rule.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

SCHEMA = "qore.vt31.nas100.edge_only_early_no_progress_cross_fold.v1"
FOLDS = ("r5", "r6", "r8", "consumed")
VARIANTS = ("SCRATCH_5M", "SCRATCH_8M")
GROUP_FIELDS = (
    "entry_family",
    "destination_state",
    "management_context",
    "last_structure_event_family",
    "path_not_compressed",
    "reference_volatility_state",
    "side",
)
MIN_CHANGED_PER_FOLD = 1


def _d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite delta")
    return result


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "qore.vt31.nas100.edge_only_early_no_progress.v1":
        raise ValueError("unexpected early-no-progress schema")
    governance = payload.get("governance", {})
    if governance.get("consumed_evidence_only") is not True:
        raise ValueError("diagnostic requires consumed evidence")
    if governance.get("capital_weighted_net_r_used") is not False:
        raise ValueError("capital-weighted economics prohibited")
    if governance.get("position_sizing_used") is not False:
        raise ValueError("sizing prohibited")
    return payload


def _changed_rows(
    payload: dict[str, Any],
    variant: str,
) -> list[dict[str, object]]:
    rows = payload["trade_rows"]
    baseline = {
        str(row["trade_id"]): row
        for row in rows["BASELINE"]
    }
    candidate = {
        str(row["trade_id"]): row
        for row in rows[variant]
    }
    changed: list[dict[str, object]] = []
    for trade_id, managed in candidate.items():
        if managed.get("scratch_applied") is not True:
            continue
        base = baseline[trade_id]
        delta = _d(managed["r_multiple"]) - _d(base["r_multiple"])
        changed.append(
            {
                "trade_id": trade_id,
                "local_date": managed["local_date"],
                "side": managed["side"],
                "delta_r": format(delta, "f"),
                "baseline_r": str(base["r_multiple"]),
                "managed_r": str(managed["r_multiple"]),
                "baseline_exit_reason": base["exit_reason"],
                "managed_exit_reason": managed["exit_reason"],
                "entry_family": managed["entry_family"],
                "destination_state": managed["destination_state"],
                "management_context": managed["management_context"],
                "last_structure_event_family": managed[
                    "last_structure_event_family"
                ],
                "path_not_compressed": managed["path_not_compressed"],
                "reference_volatility_state": managed[
                    "reference_volatility_state"
                ],
                "support_score": managed["support_score"],
                "caution_score": managed["caution_score"],
                "support_margin": (
                    int(managed["support_score"])
                    - int(managed["caution_score"])
                ),
                "scratch_checkpoint_mfe_r": managed[
                    "scratch_checkpoint_mfe_r"
                ],
                "scratch_checkpoint_close_r": managed[
                    "scratch_checkpoint_close_r"
                ],
                "baseline_winner_changed": _d(base["r_multiple"]) > 0,
            }
        )
    return changed


def _delta_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["delta_r"]) for row in rows]
    if not values:
        return {
            "sample": 0,
            "mean_delta_r": None,
            "total_delta_r": "0",
            "improved": 0,
            "worsened": 0,
            "baseline_winners_changed": 0,
        }
    total = sum(values, Decimal(0))
    return {
        "sample": len(values),
        "mean_delta_r": format(total / Decimal(len(values)), "f"),
        "total_delta_r": format(total, "f"),
        "improved": sum(value > 0 for value in values),
        "worsened": sum(value < 0 for value in values),
        "baseline_winners_changed": sum(
            bool(row["baseline_winner_changed"]) for row in rows
        ),
    }


def analyze(paths: dict[str, Path]) -> dict[str, object]:
    payloads = {fold: _load(paths[fold]) for fold in FOLDS}
    variants: dict[str, object] = {}
    stable_positive: list[dict[str, object]] = []
    stable_negative: list[dict[str, object]] = []

    for variant in VARIANTS:
        changed = {
            fold: _changed_rows(payloads[fold], variant)
            for fold in FOLDS
        }
        groups: dict[str, object] = {}
        for field in GROUP_FIELDS:
            values: set[str] = set()
            for rows in changed.values():
                values.update(str(row[field]) for row in rows)

            by_value: dict[str, object] = {}
            for value in sorted(values):
                per_fold: dict[str, object] = {}
                for fold in FOLDS:
                    selected = [
                        row
                        for row in changed[fold]
                        if str(row[field]) == value
                    ]
                    if selected:
                        per_fold[fold] = _delta_metrics(selected)
                by_value[value] = per_fold

                if set(per_fold) != set(FOLDS):
                    continue
                if not all(
                    int(item["sample"]) >= MIN_CHANGED_PER_FOLD
                    for item in per_fold.values()
                ):
                    continue
                means = [
                    _d(per_fold[fold]["mean_delta_r"])
                    for fold in FOLDS
                ]
                record = {
                    "variant": variant,
                    "field": field,
                    "value": value,
                    "per_fold": per_fold,
                }
                if all(value_ > 0 for value_ in means):
                    stable_positive.append(record)
                elif all(value_ < 0 for value_ in means):
                    stable_negative.append(record)
            groups[field] = by_value

        variants[variant] = {
            "changed_trade_count_by_fold": {
                fold: len(rows) for fold, rows in changed.items()
            },
            "overall_delta_by_fold": {
                fold: _delta_metrics(rows)
                for fold, rows in changed.items()
            },
            "groups": groups,
            "changed_rows": changed,
        }

    return {
        "schema": SCHEMA,
        "folds": list(FOLDS),
        "variants": variants,
        "stable_positive_single_field_states": stable_positive,
        "stable_negative_single_field_states": stable_negative,
        "governance": {
            "diagnostic_only": True,
            "consumed_evidence_only": True,
            "automatic_runtime_selection": False,
            "trade_admission_changed": False,
            "entry_changed": False,
            "normalized_equal_r_economics": True,
            "capital_weighted_net_r_used": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "absolute_volume_used": False,
            "opens_new_holdout": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for fold in FOLDS:
        parser.add_argument(f"--{fold}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = analyze(
        {fold: getattr(args, fold) for fold in FOLDS}
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "stable_positive_single_field_states": payload[
                    "stable_positive_single_field_states"
                ],
                "stable_negative_single_field_states": payload[
                    "stable_negative_single_field_states"
                ],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
