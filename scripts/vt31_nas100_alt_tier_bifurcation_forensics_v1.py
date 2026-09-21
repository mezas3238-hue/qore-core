"""Alternative-tier residual bifurcation for VT31_NAS100.

Consumed development evidence only. Diagnostic-only.

Exact research stack:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- Breaker +1R -> +0.25R lock
- loss-cluster retargeted to X0.35
- stable Breaker Regime Shield V1 X0.35

REARM, SCOUT and SECONDARY change sign across broad folds, so they must not be
penalized as whole tiers. This lab searches only for additional decision-time
subconditions that remain negative across R5/R6/R8/consumed.

H4/H1 and calendar/fold identity are excluded from the causal feature set.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import vt31_nas100_breaker_regime_risk_shield_frontier_v1 as breaker_shield
import vt31_nas100_loss_cluster_refinement_frontier_v1 as lc_refine
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.alt_tier_bifurcation_forensics.v1"
LOSS_CLUSTER_TARGET = Decimal("0.35")
BREAKER_TARGET = Decimal("0.35")
FOCUS_TIERS = ("REARM", "SCOUT", "SECONDARY")

FIELDS = (
    "entry_family",
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

PAIRS = (
    ("entry_family", "side"),
    ("entry_family", "reference_volatility_state"),
    ("entry_family", "premarket_state"),
    ("entry_family", "cash_open_state"),
    ("entry_family", "last_structure_event_family"),
    ("entry_family", "current_path_bucket"),
    ("entry_family", "risk_ref_bucket"),
    ("entry_family", "reclaim_age_bucket"),
    ("entry_family", "confirmation_latency_bucket"),
    ("side", "premarket_state"),
    ("side", "cash_open_state"),
    ("side", "current_path_bucket"),
    ("side", "risk_ref_bucket"),
    ("premarket_state", "cash_open_state"),
    ("premarket_state", "current_path_bucket"),
    ("premarket_state", "risk_ref_bucket"),
    ("cash_open_state", "current_path_bucket"),
    ("cash_open_state", "risk_ref_bucket"),
    ("reference_volatility_state", "current_path_bucket"),
    ("reference_volatility_state", "risk_ref_bucket"),
    ("last_structure_event_family", "current_path_bucket"),
    ("last_structure_event_family", "risk_ref_bucket"),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _current_rows(
    path: Path,
) -> tuple[
    list[dict[str, object]],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    rows, evidence, diagnostics, stats = residual._reference_rows(path)
    rows = lc_refine._retarget_loss_cluster(
        rows,
        target=LOSS_CLUSTER_TARGET,
    )
    rows = breaker_shield._apply(
        rows,
        scope="COMBINED",
        multiplier=BREAKER_TARGET,
    )
    return rows, evidence, diagnostics, stats


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    return residual._metrics(rows)


def _group(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(f"{field}={row.get(field)}" for field in fields)
        groups[key].append(row)

    result: dict[str, object] = {}
    for key, items in sorted(groups.items()):
        losses = [
            row
            for row in items
            if _d(row["capital_weighted_net_r"]) < 0
        ]
        path_counts: dict[str, int] = defaultdict(int)
        for row in losses:
            path_counts[str(row["loss_path_class"])] += 1
        result[key] = {
            "sample": len(items),
            "metrics": _metrics(items),
            "loss_rate": (
                "0"
                if not items
                else format(
                    Decimal(len(losses)) / Decimal(len(items)),
                    "f",
                )
            ),
            "loss_path_counts": dict(sorted(path_counts.items())),
        }
    return result


def _focus(rows: list[dict[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for tier in FOCUS_TIERS:
        selected = [row for row in rows if row.get("tier") == tier]
        conditions: dict[str, object] = {}
        for field in FIELDS:
            for state, item in _group(selected, (field,)).items():
                conditions[f"single:{field}:{state}"] = item
        for fields in PAIRS:
            family = "x".join(fields)
            for state, item in _group(selected, fields).items():
                conditions[f"pair:{family}:{state}"] = item
        result[tier] = {
            "overall": {
                "sample": len(selected),
                "metrics": _metrics(selected),
            },
            "conditions": dict(sorted(conditions.items())),
        }
    return result


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = _current_rows(path)
    return {
        "schema": SCHEMA,
        "partition": partition,
        "stack": {
            "loss_cluster_multiplier": format(
                LOSS_CLUSTER_TARGET, "f"
            ),
            "breaker_regime_multiplier": format(
                BREAKER_TARGET, "f"
            ),
        },
        "overall_metrics": _metrics(rows),
        "focus": _focus(rows),
        "source_stats": stats,
        "diagnostics": diagnostics,
        "evidence": evidence,
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "exact_improved_stack_replayed": True,
            "whole_tier_penalty_forbidden": True,
            "searches_crossfold_subconditions_only": True,
            "h4_h1_excluded_from_primary_causal_features": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_calendar_date_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "trade_policy_changed": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
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
                "overall_metrics": payload["overall_metrics"],
                "focus": payload["focus"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
