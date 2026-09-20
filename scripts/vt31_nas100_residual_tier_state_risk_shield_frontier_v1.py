"""Residual tier-state risk shield frontier for VT31_NAS100.

Consumed development evidence only.

Base stack is the current strongest development reference:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- Breaker closed +1R -> +0.25R lock
- loss-cluster retargeted to X0.35
- stable Breaker Regime Shield V1 X0.35

Alt Tier Bifurcation V1 showed that whole REARM/SCOUT/SECONDARY tiers are not
stable enough to penalize as whole units. This frontier therefore tests only
two predeclared substate families that remained negative across
R5/R6/R8/consumed:
1) SECONDARY + breaker
2) REARM + (premarket rotation OR cash-open bullish)

No trade is removed. Only requested risk and capital-weighted return are
scaled after causal authorization. Calendar/fold identity, terminal PnL and
future journey labels are not runtime inputs.
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

SCHEMA = "qore.vt31.nas100.residual_tier_state_risk_shield_frontier.v1"

VARIANTS = {
    "BASE": ("NONE", Decimal("1.00")),
    "SECONDARY_BREAKER_X050": ("SECONDARY_BREAKER", Decimal("0.50")),
    "SECONDARY_BREAKER_X035": ("SECONDARY_BREAKER", Decimal("0.35")),
    "REARM_ROT_OR_CASHBULL_X050": ("REARM_ROT_OR_CASHBULL", Decimal("0.50")),
    "COMBINED_X050": ("COMBINED", Decimal("0.50")),
    "COMBINED_X035": ("COMBINED", Decimal("0.35")),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _secondary_breaker(row: dict[str, object]) -> bool:
    return (
        row.get("tier") == "SECONDARY"
        and row.get("entry_family") == "breaker"
    )


def _rearm_rotation_or_cashbull(row: dict[str, object]) -> bool:
    return (
        row.get("tier") == "REARM"
        and (
            row.get("premarket_state") == "rotation"
            or row.get("cash_open_state") == "bullish"
        )
    )


def _reasons(row: dict[str, object], *, scope: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if scope in {"SECONDARY_BREAKER", "COMBINED"} and _secondary_breaker(row):
        reasons.append("SECONDARY_BREAKER_4OF4_RESIDUAL_NEGATIVE")
    if scope in {"REARM_ROT_OR_CASHBULL", "COMBINED"} and (
        _rearm_rotation_or_cashbull(row)
    ):
        if row.get("premarket_state") == "rotation":
            reasons.append("REARM_PREMARKET_ROTATION_4OF4_RESIDUAL_NEGATIVE")
        if row.get("cash_open_state") == "bullish":
            reasons.append("REARM_CASH_OPEN_BULLISH_4OF4_RESIDUAL_NEGATIVE")
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
        updated["residual_tier_state_reasons"] = list(reasons)
        updated["residual_tier_state_multiplier"] = format(applied, "f")
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

    variants: dict[str, object] = {}
    for name, (scope, multiplier) in VARIANTS.items():
        adjusted = _apply(rows, scope=scope, multiplier=multiplier)
        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"RESIDUAL_TIER_STATE:{name}:{partition}",
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

        shielded = 0
        reason_counts: dict[str, int] = defaultdict(int)
        for row in adjusted:
            reasons = cast(
                list[str],
                row.get("residual_tier_state_reasons", []),
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
        "base_stack": {
            "loss_cluster_multiplier": "0.35",
            "breaker_regime_multiplier": "0.35",
        },
        "variants": variants,
        "source_stats": stats,
        "diagnostics": diagnostics,
        "evidence": evidence,
        "governance": {
            "consumed_evidence_only": True,
            "states_predeclared_from_alt_tier_bifurcation": True,
            "whole_tier_penalty_forbidden": True,
            "risk_only_extension": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_admission_changed": False,
            "uses_terminal_pnl_at_runtime": False,
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
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
