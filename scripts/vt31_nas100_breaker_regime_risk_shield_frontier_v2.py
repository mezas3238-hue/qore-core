"""VT31_NAS100 stable breaker regime risk shield V2.

Consumed development evidence only.

Research reference:
- current exact stack from Residual Regime Forensics V2
- V1 breaker regime shield: X0.35 on either
  * breaker + confirmation latency 3-5m + premarket bearish
  * breaker short + cash-open rotation + risk_ref low

V2 tests one additional state discovered negative across R5/R6/R8/consumed:
- breaker short + prior_day_state rotation

The V1 X0.35 treatment remains fixed. For the new state V2 compares X0.50 and
X0.35. If states overlap, the most conservative applicable multiplier is used
once; multipliers are never compounded.

No trade is removed. Calendar/fold identity is never a runtime input.
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

import vt31_nas100_breaker_regime_risk_shield_frontier_v1 as v1
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as shield
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.breaker_regime_risk_shield_frontier.v2"
V1_MULTIPLIER = Decimal("0.35")

VARIANTS: dict[str, Decimal | None] = {
    "CURRENT_COMBINED_X035": None,
    "PLUS_SHORT_PRIOR_ROT_X050": Decimal("0.50"),
    "PLUS_SHORT_PRIOR_ROT_X035": Decimal("0.35"),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _tertiary(row: dict[str, object]) -> bool:
    return (
        row.get("entry_family") == "breaker"
        and row.get("side") == "short"
        and row.get("prior_day_state") == "rotation"
    )


def _apply(
    rows: list[dict[str, object]],
    *,
    tertiary_multiplier: Decimal | None,
) -> list[dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        reasons = list(v1._reasons(updated, scope="COMBINED"))
        multipliers: list[Decimal] = []

        if reasons:
            multipliers.append(V1_MULTIPLIER)

        if tertiary_multiplier is not None and _tertiary(updated):
            reasons.append(
                "BREAKER_SHORT_PRIOR_DAY_ROTATION_4OF4_NEGATIVE"
            )
            multipliers.append(tertiary_multiplier)

        applied = min(multipliers) if multipliers else Decimal("1.00")
        updated["breaker_regime_v2_shield_reasons"] = reasons
        updated["breaker_regime_v2_shield_multiplier"] = format(
            applied, "f"
        )
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
    for name, tertiary_multiplier in VARIANTS.items():
        adjusted = _apply(
            rows,
            tertiary_multiplier=tertiary_multiplier,
        )
        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"BREAKER_REGIME_SHIELD_V2:{name}:{partition}",
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
        multiplier_counts: dict[str, int] = defaultdict(int)
        shielded = 0
        for row in adjusted:
            reasons = cast(
                list[str],
                row["breaker_regime_v2_shield_reasons"],
            )
            multiplier = cast(
                str,
                row["breaker_regime_v2_shield_multiplier"],
            )
            multiplier_counts[multiplier] += 1
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
            "v1_multiplier": format(V1_MULTIPLIER, "f"),
            "tertiary_multiplier": (
                None
                if tertiary_multiplier is None
                else format(tertiary_multiplier, "f")
            ),
            "shielded_trade_count": shielded,
            "reason_counts": dict(sorted(reason_counts.items())),
            "multiplier_counts": dict(sorted(multiplier_counts.items())),
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
            "v1_states_predeclared_and_frozen": True,
            "tertiary_state_predeclared_from_4of4_bifurcation": True,
            "risk_only_extension": True,
            "multipliers_not_compounded": True,
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
