"""Residual SECONDARY path-state risk frontier for VT31_NAS100.

Consumed development evidence only.

Base stack:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- Breaker closed +1R -> +0.25R lock
- loss-cluster retargeted to X0.35
- stable Breaker Regime Shield V1 X0.35

Alt Tier Bifurcation V1 found three material SECONDARY path states that remain
negative across R5/R6/R8/consumed with adequate sample:
- reference volatility normal + current_path mid
- long + current_path mid
- short + current_path low

It also reconfirmed SECONDARY + breaker as 4/4 residual-negative.

This frontier tests bounded risk compression only. No trade is removed; Silver
Bullet, admission, entry, stop, target, lifecycle and rearm are unchanged.
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

SCHEMA = "qore.vt31.nas100.residual_secondary_path_risk_frontier.v1"

VARIANTS = {
    "BASE": ("NONE", Decimal("1.00")),
    "NORMAL_MID_X050": ("NORMAL_MID", Decimal("0.50")),
    "LONG_MID_X050": ("LONG_MID", Decimal("0.50")),
    "SHORT_LOW_X050": ("SHORT_LOW", Decimal("0.50")),
    "PATH_UNION_X050": ("PATH_UNION", Decimal("0.50")),
    "PATH_UNION_X035": ("PATH_UNION", Decimal("0.35")),
    "BREAKER_PATH_UNION_X050": ("BREAKER_PATH_UNION", Decimal("0.50")),
    "BREAKER_PATH_UNION_X035": ("BREAKER_PATH_UNION", Decimal("0.35")),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _normal_mid(row: dict[str, object]) -> bool:
    return (
        row.get("tier") == "SECONDARY"
        and row.get("reference_volatility_state") == "normal"
        and row.get("current_path_bucket") == "mid"
    )


def _long_mid(row: dict[str, object]) -> bool:
    return (
        row.get("tier") == "SECONDARY"
        and row.get("side") == "long"
        and row.get("current_path_bucket") == "mid"
    )


def _short_low(row: dict[str, object]) -> bool:
    return (
        row.get("tier") == "SECONDARY"
        and row.get("side") == "short"
        and row.get("current_path_bucket") == "low"
    )


def _secondary_breaker(row: dict[str, object]) -> bool:
    return (
        row.get("tier") == "SECONDARY"
        and row.get("entry_family") == "breaker"
    )


def _reasons(row: dict[str, object], *, scope: str) -> tuple[str, ...]:
    reasons: list[str] = []
    if scope in {"NORMAL_MID", "PATH_UNION", "BREAKER_PATH_UNION"} and (
        _normal_mid(row)
    ):
        reasons.append("SECONDARY_NORMAL_VOL_CURRENT_PATH_MID_4OF4_NEGATIVE")
    if scope in {"LONG_MID", "PATH_UNION", "BREAKER_PATH_UNION"} and (
        _long_mid(row)
    ):
        reasons.append("SECONDARY_LONG_CURRENT_PATH_MID_4OF4_NEGATIVE")
    if scope in {"SHORT_LOW", "PATH_UNION", "BREAKER_PATH_UNION"} and (
        _short_low(row)
    ):
        reasons.append("SECONDARY_SHORT_CURRENT_PATH_LOW_4OF4_NEGATIVE")
    if scope == "BREAKER_PATH_UNION" and _secondary_breaker(row):
        reasons.append("SECONDARY_BREAKER_4OF4_RESIDUAL_NEGATIVE")
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
        updated["residual_secondary_path_reasons"] = list(reasons)
        updated["residual_secondary_path_multiplier"] = format(applied, "f")
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
            variant=f"RESIDUAL_SECONDARY_PATH:{name}:{partition}",
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
                row.get("residual_secondary_path_reasons", []),
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
            "crossfold_4of4_states_only": True,
            "risk_only_extension": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_changed": False,
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
