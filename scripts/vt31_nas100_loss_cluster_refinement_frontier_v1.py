"""Loss-cluster shield refinement on the current VT31_NAS100 reference stack.

Consumed development evidence only.

Reference stack before this refinement:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- Breaker +1R -> +0.25R lock
- LOSS_CLUSTER_SHIELD_060
- stable Breaker Regime Shield V1 X0.35

Residual Regime Forensics V2 showed that the loss-cluster states remain
negative across R5/R6/R8/consumed even after the existing X0.60 treatment,
especially entry_family=order-block.

This frontier retargets the already-existing loss-cluster multiplier from
0.60 to 0.50 or 0.35. It does not add a new state, remove trades, or use
calendar/fold identity. Breaker Regime Shield V1 remains fixed at X0.35.
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

import vt31_nas100_breaker_regime_risk_shield_frontier_v1 as breaker_shield
import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.loss_cluster_refinement_frontier.v1"
CURRENT_LOSS_CLUSTER = Decimal("0.60")
BREAKER_REGIME_MULTIPLIER = Decimal("0.35")

VARIANTS = {
    "CURRENT_LC060_BR035": Decimal("0.60"),
    "LC050_BR035": Decimal("0.50"),
    "LC035_BR035": Decimal("0.35"),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _retarget_loss_cluster(
    rows: list[dict[str, object]],
    *,
    target: Decimal,
) -> list[dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    for row in rows:
        updated = dict(row)
        reasons = cast(
            list[str],
            updated.get("loss_cluster_shield_reasons", []),
        )
        current = _d(
            updated.get("loss_cluster_shield_multiplier", "1.00")
        )
        if reasons:
            if current != CURRENT_LOSS_CLUSTER:
                raise AssertionError(
                    f"expected existing loss-cluster multiplier "
                    f"{CURRENT_LOSS_CLUSTER}, got {current}"
                )
            ratio = target / current
            updated["requested_risk_r"] = format(
                _d(updated["requested_risk_r"]) * ratio,
                "f",
            )
            updated["capital_weighted_net_r"] = format(
                _d(updated["capital_weighted_net_r"]) * ratio,
                "f",
            )
            updated["loss_cluster_refined_multiplier"] = format(
                target, "f"
            )
        else:
            updated["loss_cluster_refined_multiplier"] = "1.00"
        adjusted.append(updated)
    return adjusted


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence_info, diagnostics, source_stats = residual._reference_rows(
        path
    )

    variants: dict[str, object] = {}
    for name, target in VARIANTS.items():
        loss_refined = _retarget_loss_cluster(
            rows,
            target=target,
        )
        adjusted = breaker_shield._apply(
            loss_refined,
            scope="COMBINED",
            multiplier=BREAKER_REGIME_MULTIPLIER,
        )

        metrics = residual._metrics(adjusted)
        mc = engine._monte_carlo(
            adjusted,
            variant=f"LOSS_CLUSTER_REFINEMENT:{name}:{partition}",
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

        refined_count = sum(
            bool(
                cast(
                    list[str],
                    row.get("loss_cluster_shield_reasons", []),
                )
            )
            for row in adjusted
        )
        breaker_count = sum(
            bool(
                cast(
                    list[str],
                    row.get("breaker_regime_shield_reasons", []),
                )
            )
            for row in adjusted
        )
        reason_counts: dict[str, int] = defaultdict(int)
        for row in adjusted:
            for reason in cast(
                list[str],
                row.get("loss_cluster_shield_reasons", []),
            ):
                reason_counts[f"LC:{reason}"] += 1
            for reason in cast(
                list[str],
                row.get("breaker_regime_shield_reasons", []),
            ):
                reason_counts[f"BR:{reason}"] += 1

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
            "loss_cluster_multiplier": format(target, "f"),
            "breaker_regime_multiplier": format(
                BREAKER_REGIME_MULTIPLIER, "f"
            ),
            "loss_cluster_refined_trade_count": refined_count,
            "breaker_regime_shielded_trade_count": breaker_count,
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
            "existing_loss_cluster_states_only": True,
            "loss_cluster_remained_4of4_negative_after_x060": True,
            "breaker_regime_v1_frozen_at_x035": True,
            "risk_only_refinement": True,
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
