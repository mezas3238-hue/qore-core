"""Causal loss-sequence risk taper frontier for VT31_NAS100.

Consumed development evidence only.

This lab applies a bounded QORE-Risk-style capital taper to the current best
development stack. The next trade's risk multiplier is determined only by
consecutive already-closed losing trades. No entry is filtered and no future
outcome is used.

Crucially, Monte Carlo replays the taper state inside every moving-block
bootstrap path. It does not bootstrap historically pre-weighted returns.

Base stack:
- ALLOC_G_CORE_FAMILY_050
- SHIELD_060
- Breaker closed +1R -> +0.25R lock
- loss-cluster X0.35
- stable Breaker Regime Shield V1 X0.35
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
import vt31_nas100_residual_regime_forensics_v2 as residual
import vt31_nas100_r5_causal_state_risk_shield_frontier_v1 as annuals

SCHEMA = "qore.vt31.nas100.causal_loss_sequence_risk_taper_frontier.v1"
MC_PATHS = 10000
MC_BLOCK = 5

VARIANTS: dict[str, tuple[int, Decimal, int | None, Decimal | None]] = {
    "BASE": (10**9, Decimal("1.00"), None, None),
    "LOSS2_X050": (2, Decimal("0.50"), None, None),
    "LOSS3_X050": (3, Decimal("0.50"), None, None),
    "LOSS3_X035": (3, Decimal("0.35"), None, None),
    "STAGED_L2_X075_L4_X035": (
        2,
        Decimal("0.75"),
        4,
        Decimal("0.35"),
    ),
    "STAGED_L2_X060_L4_X025": (
        2,
        Decimal("0.60"),
        4,
        Decimal("0.25"),
    ),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _multiplier(
    pre_loss_streak: int,
    spec: tuple[int, Decimal, int | None, Decimal | None],
) -> Decimal:
    first_n, first_mult, second_n, second_mult = spec
    if second_n is not None and second_mult is not None:
        if pre_loss_streak >= second_n:
            return second_mult
    if pre_loss_streak >= first_n:
        return first_mult
    return Decimal("1.00")


def _apply_history(
    rows: list[dict[str, object]],
    *,
    spec: tuple[int, Decimal, int | None, Decimal | None],
) -> list[dict[str, object]]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    adjusted: list[dict[str, object]] = []
    loss_streak = 0

    for row in ordered:
        updated = dict(row)
        mult = _multiplier(loss_streak, spec)
        base_r = _d(updated["capital_weighted_net_r"])
        updated["pre_loss_streak"] = loss_streak
        updated["sequence_risk_multiplier"] = format(mult, "f")
        updated["requested_risk_r"] = format(
            _d(updated["requested_risk_r"]) * mult,
            "f",
        )
        updated["capital_weighted_net_r"] = format(base_r * mult, "f")
        adjusted.append(updated)

        if base_r < 0:
            loss_streak += 1
        else:
            loss_streak = 0

    return adjusted


def _sequence_mc(
    rows: list[dict[str, object]],
    *,
    variant: str,
    spec: tuple[int, Decimal, int | None, Decimal | None],
) -> dict[str, object]:
    base = [_d(row["capital_weighted_net_r"]) for row in rows]
    n = len(base)
    if not base:
        return {
            "algorithm": "sha256-moving-block-bootstrap-sequence-policy-v1",
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
    domain = f"VT31_SEQUENCE_TAPER:{variant}".encode()

    for path_index in range(MC_PATHS):
        sampled: list[Decimal] = []
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
                base[(start + offset) % n]
                for offset in range(MC_BLOCK)
            )
            block_index += 1

        equity = Decimal(0)
        peak = Decimal(0)
        max_dd = Decimal(0)
        loss_streak = 0

        for base_r in sampled[:n]:
            mult = _multiplier(loss_streak, spec)
            realized = base_r * mult
            equity += realized
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
            if base_r < 0:
                loss_streak += 1
            else:
                loss_streak = 0

        terminals.append(equity)
        drawdowns.append(max_dd)

    terminals.sort()
    drawdowns.sort()

    return {
        "algorithm": "sha256-moving-block-bootstrap-sequence-policy-v1",
        "paths": MC_PATHS,
        "block_length": MC_BLOCK,
        "positive_terminal_probability": format(
            Decimal(sum(item > 0 for item in terminals))
            / Decimal(MC_PATHS),
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
    for name, spec in VARIANTS.items():
        adjusted = _apply_history(rows, spec=spec)
        metrics = residual._metrics(adjusted)
        mc = _sequence_mc(rows, variant=name, spec=spec)
        annual = (
            annuals._annual_blocks(
                adjusted,
                start=date(2022, 7, 18),
                years=2,
            )
            if partition == "consumed_holdout"
            else []
        )

        tapered = sum(
            _d(row["sequence_risk_multiplier"]) < Decimal("1")
            for row in adjusted
        )
        multiplier_counts: dict[str, int] = {}
        for row in adjusted:
            key = str(row["sequence_risk_multiplier"])
            multiplier_counts[key] = multiplier_counts.get(key, 0) + 1

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
            "tapered_trade_count": tapered,
            "multiplier_counts": dict(sorted(multiplier_counts.items())),
            "spec": {
                "first_loss_threshold": spec[0],
                "first_multiplier": format(spec[1], "f"),
                "second_loss_threshold": spec[2],
                "second_multiplier": (
                    None if spec[3] is None else format(spec[3], "f")
                ),
                "reset_after_non_loss": True,
            },
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
            "risk_only_extension": True,
            "trade_count_changed": False,
            "trade_admission_changed": False,
            "silver_bullet_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_changed": False,
            "sequence_state_uses_closed_prior_trades_only": True,
            "monte_carlo_replays_sequence_policy": True,
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
