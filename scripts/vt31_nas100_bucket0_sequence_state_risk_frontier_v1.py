"""Bucket-zero sequence-state risk frontier for VT31_NAS100.

Consumed development evidence only.

Sequence State Interaction Forensics V1 found three runtime-causal interactions
negative across R5/R6/R8/consumed:
- pre-loss streak bucket 0 + premarket bearish
- pre-loss streak bucket 0 + premarket bullish
- pre-loss streak bucket 0 + confirmation latency 3-5m

Bucket 0 means zero already-closed consecutive losing trades before the current
trade. It is causal and available at decision time.

This frontier compresses risk only. It does not remove trades or alter Silver
Bullet, admission, entry, stop, target, lifecycle or rearm.
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

SCHEMA = "qore.vt31.nas100.bucket0_sequence_state_risk_frontier.v1"

VARIANTS = {
    "BASE": ("NONE", Decimal("1.00")),
    "B0_PRE_DIRECTIONAL_X050": ("PRE_DIRECTIONAL", Decimal("0.50")),
    "B0_PRE_DIRECTIONAL_X035": ("PRE_DIRECTIONAL", Decimal("0.35")),
    "B0_LAT35_X050": ("LAT35", Decimal("0.50")),
    "B0_LAT35_X035": ("LAT35", Decimal("0.35")),
    "B0_COMBINED_X050": ("COMBINED", Decimal("0.50")),
    "B0_COMBINED_X035": ("COMBINED", Decimal("0.35")),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _pre_directional(row: dict[str, object]) -> bool:
    return (
        row.get("pre_loss_streak_bucket") == "0"
        and row.get("premarket_state") in {"bearish", "bullish"}
    )


def _lat35(row: dict[str, object]) -> bool:
    return (
        row.get("pre_loss_streak_bucket") == "0"
        and row.get("confirmation_latency_bucket") == "3_5m"
    )


def _reasons(row: dict[str, object], *, scope: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if scope in {"PRE_DIRECTIONAL", "COMBINED"} and _pre_directional(row):
        reasons.append("B0_PREMARKET_DIRECTIONAL_4OF4_NEGATIVE")
    if scope in {"LAT35", "COMBINED"} and _lat35(row):
        reasons.append("B0_CONFIRMATION_LAT35_4OF4_NEGATIVE")
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
        updated["bucket0_sequence_risk_reasons"] = list(reasons)
        updated["bucket0_sequence_risk_multiplier"] = format(applied, "f")
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
            variant=f"BUCKET0_SEQUENCE_STATE:{name}:{partition}",
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
        for row in adjusted:
            reasons = cast(
                list[str],
                row.get("bucket0_sequence_risk_reasons", []),
            )
            if reasons:
                shielded += 1
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
            "sequence_state_uses_closed_prior_trades_only": True,
            "risk_only_extension": True,
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
