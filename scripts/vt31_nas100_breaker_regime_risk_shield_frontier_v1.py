"""Stable breaker regime risk shield frontier for VT31_NAS100.

Consumed development evidence only.

This frontier is derived only from Breaker Regime Bifurcation V1 states that
remained negative across R5/R6/R8/consumed after the current reference stack.

Primary state:
- breaker
- confirmation latency 3-5m
- premarket bearish

Secondary stable state:
- breaker short
- cash-open rotation
- risk_ref low

No trade is removed. The experiment changes only capital at risk after the
trade has already been causally authorized. Calendar/fold identity is never a
runtime input.
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

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.breaker_regime_risk_shield_frontier.v1"

VARIANTS = {
    "BASE": ("NONE", Decimal("1.00")),
    "LAT35_PRE_BEAR_X050": ("PRIMARY", Decimal("0.50")),
    "LAT35_PRE_BEAR_X035": ("PRIMARY", Decimal("0.35")),
    "STABLE_BREAKER_COMBINED_X035": ("COMBINED", Decimal("0.35")),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _primary(row: dict[str, object]) -> bool:
    latency = row.get("confirmation_latency_minutes")
    return (
        row.get("entry_family") == "breaker"
        and latency is not None
        and 3 <= int(latency) <= 5
        and row.get("premarket_state") == "bearish"
    )


def _secondary(row: dict[str, object]) -> bool:
    risk_ref = row.get("risk_ref")
    return (
        row.get("entry_family") == "breaker"
        and row.get("side") == "short"
        and row.get("cash_open_state") == "rotation"
        and risk_ref is not None
        and _d(risk_ref) < Decimal("0.30")
    )


def _reasons(
    row: dict[str, object],
    *,
    scope: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if scope in {"PRIMARY", "COMBINED"} and _primary(row):
        reasons.append("BREAKER_LAT35_PREMARKET_BEARISH_4OF4_NEGATIVE")
    if scope == "COMBINED" and _secondary(row):
        reasons.append("BREAKER_SHORT_CASH_ROTATION_LOW_RISK_REF_4OF4_NEGATIVE")
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
        updated["breaker_regime_shield_reasons"] = list(reasons)
        updated["breaker_regime_shield_multiplier"] = format(applied, "f")
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
    rows, evidence_info, diagnostics, source_stats = residual._reference_rows(
        path
    )

    variants: dict[str, object] = {}
    for name, (scope, multiplier) in VARIANTS.items():
        adjusted = _apply(
            rows,
            scope=scope,
            multiplier=multiplier,
        )
        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"BREAKER_REGIME_SHIELD:{name}:{partition}",
        )
        annual = (
            shield._annual_blocks(
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
                row["breaker_regime_shield_reasons"],
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
        "source_stats": source_stats,
        "diagnostics": diagnostics,
        "evidence": evidence_info,
        "governance": {
            "consumed_evidence_only": True,
            "states_predeclared_from_4of4_bifurcation": True,
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
