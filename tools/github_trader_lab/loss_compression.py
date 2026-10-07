#!/usr/bin/env python3
"""Decision-grade CIBO drawdown and gross-loss compression report."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


ZERO = Decimal(0)
ONE = Decimal(1)
HUNDRED = Decimal(100)


def d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite decimal in loss-compression report")
    return result


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return numerator / denominator


def fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _point(row: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    path = row["capital_path"]
    loss = row["loss_profile"]
    return (
        d(path["net_pnl_usd"]),
        d(path["maximum_drawdown_fraction"]),
        d(loss["gross_loss_usd"]),
    )


def _dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ap, add, agl = _point(a)
    bp, bdd, bgl = _point(b)
    nonworse = ap >= bp and add <= bdd and agl <= bgl
    strict = ap > bp or add < bdd or agl < bgl
    return nonworse and strict


def evaluate_loss_compression(
    profile: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    policy = profile.get("loss_compression_policy")
    if not isinstance(policy, dict) or not bool(policy.get("enabled")):
        return None

    lane = str(profile["science"]["primary_lane"])
    payload = payloads.get(lane)
    if not isinstance(payload, dict):
        return None
    variants = payload.get("variants")
    control = payload.get("control")
    if (
        not isinstance(variants, dict)
        or not isinstance(control, str)
        or control not in variants
    ):
        return None
    if any(
        not isinstance(row, dict) or "loss_profile" not in row
        for row in variants.values()
    ):
        return None

    target_dd = d(policy.get("target_drawdown_fraction", "0.25"))
    control_row = variants[control]
    control_path = control_row["capital_path"]
    control_loss = control_row["loss_profile"]
    control_net = d(control_path["net_pnl_usd"])
    control_end = d(control_path["ending_capital_usd"])
    control_dd = d(control_path["maximum_drawdown_fraction"])
    control_dd_usd = d(control_path["maximum_drawdown_usd"])
    control_gl = d(control_loss["gross_loss_usd"])
    control_gp = d(control_loss["gross_profit_usd"])
    control_pf = d(control_loss["profit_factor"]) if control_loss.get("profit_factor") is not None else None
    control_trades = int(control_row["trade_count"])

    rows: dict[str, dict[str, Any]] = {}
    strict_wins: list[str] = []
    target_dd_survivors: list[str] = []

    for name, row in variants.items():
        path = row["capital_path"]
        loss = row["loss_profile"]
        net = d(path["net_pnl_usd"])
        ending = d(path["ending_capital_usd"])
        dd = d(path["maximum_drawdown_fraction"])
        dd_usd = d(path["maximum_drawdown_usd"])
        gross_loss = d(loss["gross_loss_usd"])
        gross_profit = d(loss["gross_profit_usd"])
        pf = d(loss["profit_factor"]) if loss.get("profit_factor") is not None else None
        trade_count = int(row["trade_count"])

        production_delta = net - control_net
        dd_reduction = control_dd - dd
        gross_loss_saved = control_gl - gross_loss
        production_sacrifice = max(ZERO, control_net - net)

        ceiling_preserved = ending >= control_end
        entries_preserved = trade_count == control_trades
        dd_improved = dd < control_dd
        loss_improved = gross_loss < control_gl
        target_met = dd <= target_dd

        if name == control:
            verdict = "CONTROL"
        elif (
            ceiling_preserved
            and entries_preserved
            and dd_improved
            and loss_improved
        ):
            verdict = "STRICT_WIN"
            strict_wins.append(name)
        elif (
            ceiling_preserved
            and entries_preserved
            and dd <= control_dd
            and gross_loss <= control_gl
        ):
            verdict = "NO_DEGRADATION"
        elif dd_improved or loss_improved:
            verdict = "RISK_IMPROVEMENT_WITH_PRODUCTION_COST"
        else:
            verdict = "REJECT_NO_RISK_GAIN"

        if target_met:
            target_dd_survivors.append(name)

        rows[name] = {
            "verdict": verdict,
            "trade_count": trade_count,
            "entries_preserved": entries_preserved,
            "ending_capital_usd": format(ending, "f"),
            "net_production_usd": format(net, "f"),
            "production_delta_vs_control_usd": format(production_delta, "f"),
            "production_retention_fraction": fmt(ratio(net, control_net)),
            "gross_profit_usd": format(gross_profit, "f"),
            "gross_profit_retention_fraction": fmt(
                ratio(gross_profit, control_gp)
            ),
            "gross_loss_usd": format(gross_loss, "f"),
            "gross_loss_saved_vs_control_usd": format(
                gross_loss_saved, "f"
            ),
            "gross_loss_reduction_fraction": fmt(
                ratio(gross_loss_saved, control_gl)
            ),
            "profit_factor": None if pf is None else format(pf, "f"),
            "profit_factor_delta": (
                None
                if pf is None or control_pf is None
                else format(pf - control_pf, "f")
            ),
            "max_drawdown_usd": format(dd_usd, "f"),
            "max_drawdown_fraction": format(dd, "f"),
            "drawdown_reduction_fraction": fmt(ratio(dd_reduction, control_dd)),
            "drawdown_reduction_percentage_points": format(
                dd_reduction * HUNDRED, "f"
            ),
            "target_drawdown_met": target_met,
            "ceiling_preserved": ceiling_preserved,
            "production_sacrifice_per_dd_point_usd": (
                None
                if dd_reduction <= 0
                else format(
                    production_sacrifice
                    / (dd_reduction * HUNDRED),
                    "f",
                )
            ),
            "production_sacrifice_per_gross_loss_saved_usd": (
                None
                if gross_loss_saved <= 0
                else format(production_sacrifice / gross_loss_saved, "f")
            ),
            "losing_trade_count": int(loss["losing_trade_count"]),
            "max_losing_streak": int(loss["max_losing_streak"]),
            "worst_trade_loss_usd": str(loss["worst_trade_loss_usd"]),
            "top_10_losses_share": str(loss["top_10_losses_share"]),
            "top_5pct_losses_share": str(loss["top_5pct_losses_share"]),
            "gross_loss_by_mode_usd": loss["gross_loss_by_mode_usd"],
            "gross_loss_by_trader_usd": loss["gross_loss_by_trader_usd"],
            "gross_loss_by_multiplier_usd": loss[
                "gross_loss_by_multiplier_usd"
            ],
            "worst_losses": loss["worst_losses"],
            "max_drawdown_attribution": loss.get(
                "max_drawdown_attribution",
                {},
            ),
        }

    pareto: list[str] = []
    for name, row in variants.items():
        if not any(
            other != name and _dominates(other_row, row)
            for other, other_row in variants.items()
        ):
            pareto.append(name)

    best_dd = min(
        variants,
        key=lambda name: d(
            variants[name]["capital_path"]["maximum_drawdown_fraction"]
        ),
    )
    best_loss = min(
        variants,
        key=lambda name: d(
            variants[name]["loss_profile"]["gross_loss_usd"]
        ),
    )
    best_production = max(
        variants,
        key=lambda name: d(variants[name]["capital_path"]["net_pnl_usd"]),
    )

    return {
        "schema": "qore.github-trader-lab.loss-compression.v1",
        "subject": profile["subject"],
        "lane": lane,
        "control": control,
        "policy": {
            "target_drawdown_fraction": format(target_dd, "f"),
            "strict_ceiling_preservation": True,
            "strict_entry_preservation": True,
            "gross_loss_objective": "MINIMIZE",
            "final_acceptance": (
                "ENDING_CAPITAL_NONDEGRADE_AND_DD_LOWER_AND_GROSS_LOSS_LOWER"
            ),
        },
        "control_baseline": {
            "trade_count": control_trades,
            "ending_capital_usd": format(control_end, "f"),
            "net_production_usd": format(control_net, "f"),
            "gross_profit_usd": format(control_gp, "f"),
            "gross_loss_usd": format(control_gl, "f"),
            "profit_factor": (
                None if control_pf is None else format(control_pf, "f")
            ),
            "max_drawdown_usd": format(control_dd_usd, "f"),
            "max_drawdown_fraction": format(control_dd, "f"),
        },
        "variants": rows,
        "summary": {
            "strict_wins": strict_wins,
            "target_drawdown_survivors": target_dd_survivors,
            "pareto_frontier": pareto,
            "best_drawdown": best_dd,
            "best_gross_loss": best_loss,
            "best_net_production": best_production,
            "variant_count": len(rows),
        },
    }
