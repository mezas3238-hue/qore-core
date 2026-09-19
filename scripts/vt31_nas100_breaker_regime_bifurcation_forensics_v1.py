"""Focused breaker regime-bifurcation forensics for VT31_NAS100.

Consumed development evidence only. Diagnostic-only.

This lab investigates the largest residual Y1 sign reversals found by Residual
Regime Forensics V2, especially breaker trades with 3-5m confirmation latency,
bullish cash-open state, and short side.

The purpose is not to gate those broad states. They are positive in other
consumed folds. Instead, this lab searches for an additional decision-time
condition that separates harmful from beneficial breaker regimes and remains
cross-fold stable.

Calendar identity is diagnostic only and H4/H1 are excluded from primary
causal analysis.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.breaker_regime_bifurcation_forensics.v1"

FOCUS_PREDICATES = {
    "BREAKER_LATENCY_3_5": lambda row: (
        row.get("entry_family") == "breaker"
        and row.get("confirmation_latency_bucket") == "3_5m"
    ),
    "BREAKER_CASH_BULLISH": lambda row: (
        row.get("entry_family") == "breaker"
        and row.get("cash_open_state") == "bullish"
    ),
    "BREAKER_SHORT": lambda row: (
        row.get("entry_family") == "breaker"
        and row.get("side") == "short"
    ),
}

CONDITION_FIELDS = (
    "tier",
    "side",
    "reference_volatility_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
    "authorization_reason",
)

PAIR_CONDITIONS = (
    ("tier", "reference_volatility_state"),
    ("tier", "premarket_state"),
    ("tier", "cash_open_state"),
    ("tier", "current_path_bucket"),
    ("tier", "risk_ref_bucket"),
    ("tier", "reclaim_age_bucket"),
    ("side", "reference_volatility_state"),
    ("side", "premarket_state"),
    ("side", "cash_open_state"),
    ("side", "current_path_bucket"),
    ("side", "risk_ref_bucket"),
    ("side", "reclaim_age_bucket"),
    ("premarket_state", "cash_open_state"),
    ("premarket_state", "current_path_bucket"),
    ("premarket_state", "risk_ref_bucket"),
    ("cash_open_state", "current_path_bucket"),
    ("cash_open_state", "risk_ref_bucket"),
    ("reference_volatility_state", "current_path_bucket"),
    ("reference_volatility_state", "risk_ref_bucket"),
    ("current_path_bucket", "risk_ref_bucket"),
    ("last_structure_event_family", "current_path_bucket"),
    ("last_structure_event_family", "risk_ref_bucket"),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _state_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    metrics = residual._metrics(rows)
    losses = [
        row
        for row in rows
        if _d(row["capital_weighted_net_r"]) < 0
    ]
    paths: dict[str, int] = defaultdict(int)
    for row in losses:
        paths[str(row["loss_path_class"])] += 1
    return {
        "sample": len(rows),
        "metrics": metrics,
        "loss_rate": (
            "0"
            if not rows
            else format(Decimal(len(losses)) / Decimal(len(rows)), "f")
        ),
        "loss_path_counts": dict(sorted(paths.items())),
    }


def _condition_groups(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in CONDITION_FIELDS:
        groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            key = f"{field}={row.get(field)}"
            groups[key].append(row)
        for key, items in groups.items():
            result[f"single:{key}"] = _state_metrics(items)

    for fields in PAIR_CONDITIONS:
        groups = defaultdict(list)
        for row in rows:
            key = "|".join(
                f"{field}={row.get(field)}" for field in fields
            )
            groups[key].append(row)
        family = "x".join(fields)
        for key, items in groups.items():
            result[f"pair:{family}:{key}"] = _state_metrics(items)
    return dict(sorted(result.items()))


def _analysis(rows: list[dict[str, object]]) -> dict[str, object]:
    focus: dict[str, object] = {}
    for name, predicate in FOCUS_PREDICATES.items():
        selected = [row for row in rows if predicate(row)]
        focus[name] = {
            "overall": _state_metrics(selected),
            "conditions": _condition_groups(selected),
        }
    return focus


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence_info, diagnostics, source_stats = residual._reference_rows(
        path
    )

    blocks: dict[str, object] = {}
    if partition == "consumed_holdout":
        for name, (start, end) in residual.CONSUMED_BLOCKS.items():
            selected = [
                row
                for row in rows
                if start
                <= date.fromisoformat(cast(str, row["local_date"]))
                < end
            ]
            blocks[name] = _analysis(selected)

    return {
        "schema": SCHEMA,
        "partition": partition,
        "focus_overall": _analysis(rows),
        "consumed_blocks": blocks,
        "source_stats": source_stats,
        "diagnostics": diagnostics,
        "evidence": evidence_info,
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "current_reference_stack_reused": True,
            "broad_sign_reversing_breaker_states_not_gated": True,
            "searches_additional_decision_time_condition": True,
            "h4_h1_excluded_from_primary_causal_features": True,
            "calendar_blocks_diagnostic_only": True,
            "calendar_blocks_used_at_runtime": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "trade_policy_changed": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "focus_overall": payload["focus_overall"],
                "consumed_blocks": payload["consumed_blocks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
