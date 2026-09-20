"""Selective sequence x state risk shield for VT31_NAS100.

Consumed development evidence only.

Derived from Sequence State Interaction Forensics V1. The policy changes risk
only when an already-closed loss sequence coincides with a predeclared current
decision-time state that was negative across R5/R6/R8/consumed.

Primary interaction:
- pre_loss_streak >= 2
- current entry_family == order-block

Secondary research interactions:
- exactly one prior loss + current side long
- pre_loss_streak >= 2 + current last_structure_event_family == fair-value-gap

No trade is removed. Monte Carlo recomputes sequence state inside each
bootstrap path before sizing the current sampled trade.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals
import vt31_nas100_residual_regime_forensics_v2 as residual

SCHEMA = "qore.vt31.nas100.selective_sequence_state_risk_frontier.v1"
MC_PATHS = 10000
MC_BLOCK = 5

VARIANTS = {
    "BASE": ("NONE", Decimal("1.00")),
    "L2_OB_X050": ("L2_OB", Decimal("0.50")),
    "L2_OB_X035": ("L2_OB", Decimal("0.35")),
    "L3_OB_X050": ("L3_OB", Decimal("0.50")),
    "L1_LONG_X050": ("L1_LONG", Decimal("0.50")),
    "L2_LAST_FVG_X050": ("L2_LAST_FVG", Decimal("0.50")),
    "L2_OB_PLUS_L1_LONG_X050": ("L2_OB_PLUS_L1_LONG", Decimal("0.50")),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _applies(
    row: dict[str, object],
    *,
    prior_losses: int,
    scope: str,
) -> bool:
    if scope == "NONE":
        return False
    if scope in {"L2_OB", "L2_OB_PLUS_L1_LONG"}:
        if prior_losses >= 2 and row.get("entry_family") == "order-block":
            return True
    if scope == "L3_OB":
        return prior_losses >= 3 and row.get("entry_family") == "order-block"
    if scope in {"L1_LONG", "L2_OB_PLUS_L1_LONG"}:
        if prior_losses == 1 and row.get("side") == "long":
            return True
    if scope == "L2_LAST_FVG":
        return (
            prior_losses >= 2
            and row.get("last_structure_event_family") == "fair-value-gap"
        )
    return False


def _apply_history(
    rows: list[dict[str, object]],
    *,
    scope: str,
    multiplier: Decimal,
) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    result: list[dict[str, object]] = []
    prior_losses = 0

    for row in ordered:
        updated = dict(row)
        applies = _applies(
            updated,
            prior_losses=prior_losses,
            scope=scope,
        )
        mult = multiplier if applies else Decimal("1.00")
        base_r = _d(updated["capital_weighted_net_r"])
        updated["pre_loss_streak"] = prior_losses
        updated["selective_sequence_state_applied"] = applies
        updated["selective_sequence_state_multiplier"] = format(mult, "f")
        updated["requested_risk_r"] = format(
            _d(updated["requested_risk_r"]) * mult,
            "f",
        )
        updated["capital_weighted_net_r"] = format(base_r * mult, "f")
        result.append(updated)

        if base_r < 0:
            prior_losses += 1
        else:
            prior_losses = 0

    return result


def _mc(
    rows: list[dict[str, object]],
    *,
    name: str,
    scope: str,
    multiplier: Decimal,
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    n = len(ordered)
    if not ordered:
        return {
            "algorithm": "sha256-moving-block-bootstrap-selective-sequence-v1",
            "paths": MC_PATHS,
            "block_length": MC_BLOCK,
            "positive_terminal_probability": "0",
            "p05_terminal_r": "0",
            "p50_terminal_r": "0",
            "p95_max_drawdown_r": "0",
            "p99_max_drawdown_r": "0",
        }

    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    domain = f"VT31_SELECTIVE_SEQUENCE:{name}".encode()

    for path_index in range(MC_PATHS):
        sampled: list[dict[str, object]] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(
                ordered[(start + offset) % n]
                for offset in range(MC_BLOCK)
            )
            block_index += 1

        equity = Decimal(0)
        peak = Decimal(0)
        max_dd = Decimal(0)
        prior_losses = 0

        for row in sampled[:n]:
            base_r = _d(row["capital_weighted_net_r"])
            applies = _applies(
                row,
                prior_losses=prior_losses,
                scope=scope,
            )
            mult = multiplier if applies else Decimal("1.00")
            realized = base_r * mult
            equity += realized
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)

            if base_r < 0:
                prior_losses += 1
            else:
                prior_losses = 0

        terminals.append(equity)
        drawdowns.append(max_dd)

    terminals.sort()
    drawdowns.sort()
    return {
        "algorithm": "sha256-moving-block-bootstrap-selective-sequence-v1",
        "paths": MC_PATHS,
        "block_length": MC_BLOCK,
        "positive_terminal_probability": format(
            Decimal(sum(x > 0 for x in terminals)) / Decimal(MC_PATHS),
            "f",
        ),
        "p05_terminal_r": format(
            terminals[(MC_PATHS - 1) * 5 // 100],
            "f",
        ),
        "p50_terminal_r": format(
            terminals[(MC_PATHS - 1) * 50 // 100],
            "f",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(MC_PATHS - 1) * 95 // 100],
            "f",
        ),
        "p99_max_drawdown_r": format(
            drawdowns[(MC_PATHS - 1) * 99 // 100],
            "f",
        ),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence, diagnostics, stats = alt._current_rows(path)
    rows = sorted(rows, key=lambda row: cast(str, row["signal_at"]))

    variants: dict[str, object] = {}
    for name, (scope, multiplier) in VARIANTS.items():
        adjusted = _apply_history(
            rows,
            scope=scope,
            multiplier=multiplier,
        )
        metrics = residual._metrics(adjusted)
        mc = _mc(
            rows,
            name=name,
            scope=scope,
            multiplier=multiplier,
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
        applied_count = sum(
            bool(row["selective_sequence_state_applied"])
            for row in adjusted
        )

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
            "applied_trade_count": applied_count,
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
            "states_predeclared_from_sequence_state_forensics": True,
            "sequence_state_uses_closed_prior_trades_only": True,
            "monte_carlo_replays_sequence_state": True,
            "risk_only_extension": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_changed": False,
            "uses_current_trade_terminal_pnl_for_risk": False,
            "uses_future_journey_label_at_runtime": False,
            "uses_calendar_date_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "qore_risk_sovereign": True,
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
