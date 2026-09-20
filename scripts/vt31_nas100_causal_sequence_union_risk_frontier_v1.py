"""Causal sequence-union risk frontier for VT31_NAS100.

Consumed development evidence only.

This frontier combines only sequence interactions already shown negative across
R5/R6/R8/consumed:
- bucket 0 + (premarket directional OR confirmation latency 3-5m)
- pre-loss streak >=2 + order-block
- bucket 1 + long side

Each trade is compressed at most once even if multiple reasons overlap.
No trade is removed. Silver Bullet, admission, entry, stop, target, lifecycle
and rearm remain unchanged. Only already-closed prior outcomes are used.
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
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_sequence_state_interaction_forensics_v1 as seq

SCHEMA = "qore.vt31.nas100.causal_sequence_union_risk_frontier.v1"

VARIANTS = {
    "BASE": ("NONE", Decimal("1.00")),
    "B0_ONLY_X050": ("B0", Decimal("0.50")),
    "B0_L2OB_X050": ("B0_L2OB", Decimal("0.50")),
    "B0_L1LONG_X050": ("B0_L1LONG", Decimal("0.50")),
    "B0_L2OB_L1LONG_X050": ("FULL", Decimal("0.50")),
    "B0_L2OB_L1LONG_X060": ("FULL", Decimal("0.60")),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _b0(row: dict[str, object]) -> bool:
    return (
        row.get("pre_loss_streak_bucket") == "0"
        and (
            row.get("premarket_state") in {"bearish", "bullish"}
            or row.get("confirmation_latency_bucket") == "3_5m"
        )
    )


def _l2_ob(row: dict[str, object]) -> bool:
    return bool(row.get("pre_loss_ge_2")) and row.get("entry_family") == "order-block"


def _l1_long(row: dict[str, object]) -> bool:
    return row.get("pre_loss_streak_bucket") == "1" and row.get("side") == "long"


def _reasons(row: dict[str, object], *, scope: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if scope in {"B0", "B0_L2OB", "B0_L1LONG", "FULL"} and _b0(row):
        reasons.append("B0_DIRECTIONAL_OR_LAT35_4OF4_NEGATIVE")
    if scope in {"B0_L2OB", "FULL"} and _l2_ob(row):
        reasons.append("PRELOSS_GE2_ORDER_BLOCK_4OF4_NEGATIVE")
    if scope in {"B0_L1LONG", "FULL"} and _l1_long(row):
        reasons.append("B1_LONG_4OF4_NEGATIVE")
    return tuple(reasons)


def _apply(
    rows: list[dict[str, object]],
    *,
    scope: str,
    multiplier: Decimal,
) -> list[dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        reasons = _reasons(updated, scope=scope)
        applied = multiplier if reasons else Decimal("1.00")
        updated["sequence_union_reasons"] = list(reasons)
        updated["sequence_union_multiplier"] = format(applied, "f")
        updated["requested_risk_r"] = format(
            _d(updated["requested_risk_r"]) * applied,
            "f",
        )
        updated["capital_weighted_net_r"] = format(
            _d(updated["capital_weighted_net_r"]) * applied,
            "f",
        )
        adjusted.append(updated)
    return adjusted


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = alt._current_rows(path)
    annotated = seq._annotate(rows)

    variants: dict[str, object] = {}
    for name, (scope, multiplier) in VARIANTS.items():
        adjusted = _apply(annotated, scope=scope, multiplier=multiplier)
        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"CAUSAL_SEQUENCE_UNION:{name}:{partition}",
        )
        annual = (
            annuals._annual_blocks(
                adjusted,
                start=date(2022, 7, 18),
                years=2,
            )
            if partition == "consumed_holdout"
            else []
        )

        reason_counts: dict[str, int] = defaultdict(int)
        shielded = 0
        overlap = 0
        for row in adjusted:
            reasons = cast(list[str], row.get("sequence_union_reasons", []))
            if reasons:
                shielded += 1
            if len(reasons) > 1:
                overlap += 1
            for reason in reasons:
                reason_counts[reason] += 1

        objectives = {
            "density_300_350": 300 <= len(adjusted) <= 350,
            "pf_ge_1_50": (
                metrics["profit_factor"] is not None
                and _d(metrics["profit_factor"]) >= Decimal("1.50")
            ),
            "dd_le_6": _d(metrics["max_drawdown_r"]) <= Decimal("6"),
            "mc_positive_ge_0_90": (
                _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
            ),
            "mc_p95_dd_le_15": (
                _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
            ),
        }
        if annual:
            objectives["both_consumed_years_positive"] = all(
                bool(block["positive"]) for block in annual
            )

        variants[name] = {
            "trade_count": len(adjusted),
            "scope": scope,
            "multiplier": format(multiplier, "f"),
            "shielded_trade_count": shielded,
            "overlap_trade_count": overlap,
            "reason_counts": dict(sorted(reason_counts.items())),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "objectives": objectives,
            "passes_economic_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "variants": variants,
        "source_stats": stats,
        "diagnostics": diagnostics,
        "evidence": evidence,
        "governance": {
            "consumed_evidence_only": True,
            "states_predeclared_from_4of4_sequence_forensics": True,
            "single_compression_per_trade": True,
            "sequence_state_uses_closed_prior_trades_only": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_changed": False,
            "uses_current_trade_terminal_pnl_for_sequence_state": False,
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
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
