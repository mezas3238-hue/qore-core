"""Cross-fold sequence x causal-state forensics for VT31_NAS100.

Consumed development evidence only. Diagnostic-only.

Purpose:
- explain why unconditional loss-streak taper harms recovery;
- annotate each current-best-stack trade with ONLY already-closed prior losses;
- intersect that causal sequence state with decision-time market/trader state;
- identify interactions that remain negative across R5/R6/R8/consumed.

No policy is changed. Calendar/fold identity and terminal outcome are not
runtime features. H4/H1 are intentionally excluded from primary causal fields.
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

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.sequence_state_interaction_forensics.v1"

CONSUMED_BLOCKS = {
    "Y1": (date(2022, 7, 18), date(2023, 7, 18)),
    "Y2": (date(2023, 7, 18), date(2024, 7, 18)),
}

FIELDS = (
    "tier",
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


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _bucket(streak: int) -> str:
    if streak == 0:
        return "0"
    if streak == 1:
        return "1"
    if streak <= 3:
        return "2_3"
    return "4_plus"


def _annotate(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    result: list[dict[str, object]] = []
    streak = 0
    for row in ordered:
        updated = dict(row)
        updated["pre_loss_streak"] = streak
        updated["pre_loss_streak_bucket"] = _bucket(streak)
        updated["pre_loss_ge_2"] = streak >= 2
        updated["pre_loss_ge_3"] = streak >= 3
        updated["pre_loss_ge_4"] = streak >= 4
        result.append(updated)
        if _d(row["capital_weighted_net_r"]) < 0:
            streak += 1
        else:
            streak = 0
    return result


def _state_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    metrics = residual._metrics(rows)
    losses = [row for row in rows if _d(row["capital_weighted_net_r"]) < 0]
    path_counts: dict[str, int] = defaultdict(int)
    for row in losses:
        path_counts[str(row.get("loss_path_class"))] += 1
    return {
        "sample": len(rows),
        "metrics": metrics,
        "loss_rate": (
            "0"
            if not rows
            else format(Decimal(len(losses)) / Decimal(len(rows)), "f")
        ),
        "loss_path_counts": dict(sorted(path_counts.items())),
    }


def _interactions(rows: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in rows:
        bucket = str(row["pre_loss_streak_bucket"])
        grouped[f"bucket:{bucket}"].append(row)

        for threshold in ("pre_loss_ge_2", "pre_loss_ge_3", "pre_loss_ge_4"):
            if bool(row[threshold]):
                grouped[f"{threshold}:ALL"].append(row)
                for field in FIELDS:
                    grouped[
                        f"{threshold}|{field}={row.get(field)}"
                    ].append(row)

        for field in FIELDS:
            grouped[
                f"bucket={bucket}|{field}={row.get(field)}"
            ].append(row)

    return {
        key: _state_metrics(items)
        for key, items in sorted(grouped.items())
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = alt._current_rows(path)
    annotated = _annotate(rows)

    blocks: dict[str, object] = {}
    if partition == "consumed_holdout":
        for name, (start, end) in CONSUMED_BLOCKS.items():
            selected = [
                row
                for row in annotated
                if start
                <= date.fromisoformat(cast(str, row["local_date"]))
                < end
            ]
            blocks[name] = {
                "start": start.isoformat(),
                "end_exclusive": end.isoformat(),
                "metrics": residual._metrics(selected),
                "interactions": _interactions(selected),
            }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "base_stack": {
            "loss_cluster_multiplier": "0.35",
            "breaker_regime_multiplier": "0.35",
        },
        "trade_count": len(annotated),
        "metrics": residual._metrics(annotated),
        "interactions": _interactions(annotated),
        "consumed_blocks": blocks,
        "source_stats": stats,
        "diagnostics": diagnostics,
        "evidence": evidence,
        "governance": {
            "consumed_evidence_only": True,
            "diagnostic_only": True,
            "sequence_state_uses_closed_prior_trades_only": True,
            "h4_h1_excluded_from_primary_causal_features": True,
            "trade_policy_changed": False,
            "uses_current_trade_terminal_pnl_for_sequence_state": False,
            "uses_future_journey_label_at_runtime": False,
            "uses_calendar_date_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
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
                "trade_count": payload["trade_count"],
                "metrics": payload["metrics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
