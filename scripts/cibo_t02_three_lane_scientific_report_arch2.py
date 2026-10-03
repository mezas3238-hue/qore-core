#!/usr/bin/env python3
"""Consolidate Architect-2 T02 multi-timeframe and three-lane capital evidence.

Inputs are immutable artifacts from:
- the H4/H1/M15/M5/M1 T02 Explorer/Validator;
- the exact Core / Trader-local Compound / Compound Portfolio causal replay.

The report is research-only and makes no production/certification claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from decimal import Decimal
from pathlib import Path
from typing import Any

SIMS = 10000
SEED = 20261003


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal) -> str:
    return format(value, "f")


def qtile(values: list[Decimal], q: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = q * Decimal(len(values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    frac = pos - Decimal(lo)
    return values[lo] * (Decimal(1) - frac) + values[hi] * frac


def max_drawdown(values: list[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    worst = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def profit_factor(values: list[Decimal]) -> Decimal | None:
    gross_profit = sum((x for x in values if x > 0), Decimal(0))
    gross_loss = -sum((x for x in values if x < 0), Decimal(0))
    return None if gross_loss == 0 else gross_profit / gross_loss


def blocks(rows: list[dict[str, Any]], count: int) -> list[list[dict[str, Any]]]:
    return [
        rows[i * len(rows) // count : (i + 1) * len(rows) // count]
        for i in range(count)
    ]


def bootstrap(rows: list[dict[str, Any]], salt: str) -> dict[str, Any]:
    values = [row["pnl"] for row in rows]
    if not values:
        return {
            "simulation_count": SIMS,
            "median_pnl_usd": "0",
            "p05_pnl_usd": "0",
            "p95_drawdown_usd": "0",
        }
    seed = int(
        hashlib.sha256((str(SEED) + salt).encode()).hexdigest()[:16],
        16,
    )
    rng = random.Random(seed)
    totals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for _ in range(SIMS):
        sample = [rng.choice(values) for _ in values]
        totals.append(sum(sample, Decimal(0)))
        drawdowns.append(max_drawdown(sample))
    return {
        "simulation_count": SIMS,
        "median_pnl_usd": fmt(qtile(totals, Decimal("0.50"))),
        "p05_pnl_usd": fmt(qtile(totals, Decimal("0.05"))),
        "p95_drawdown_usd": fmt(qtile(drawdowns, Decimal("0.95"))),
    }


def core_events(trace: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for row in trace["opportunities"]:
        settlement = row.get("settlement")
        risk = row.get("qore_risk")
        if not isinstance(settlement, dict) or not isinstance(risk, dict):
            continue
        if risk.get("status") not in {"ALLOW", "REDUCE"}:
            continue
        stop_risk = dec(risk["authorized_stop_risk_usd"])
        gross = dec(settlement["gross_structural_outcome_r"]) * stop_risk
        pnl = dec(settlement["realized_net_pnl_usd"])
        out.append(
            {
                "time": str(settlement["capital_released_at"]),
                "signal": str(row["signal_fingerprint"]),
                "trader": str(row["trader_id"]),
                "pnl": pnl,
                "gross": gross,
                "provider_cost": gross - pnl,
                "kind": "CORE",
            }
        )
    return sorted(out, key=lambda x: (x["time"], x["signal"]))


def compound_events(lane: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "time": str(row["exit_at"]),
                "signal": str(row["signal_fingerprint"]),
                "trader": str(row["trader_id"]),
                "pnl": dec(row["incremental_realized_pnl_usd"]),
                "gross": (
                    dec(row["gross_structural_outcome_r"])
                    * dec(row["authorized_stop_risk_usd"])
                ),
                "provider_cost": dec(row["provider_cost_usd"]),
                "kind": "COMPOUND",
            }
            for row in lane["trades"]
        ],
        key=lambda x: (x["time"], x["signal"]),
    )


def metrics(rows: list[dict[str, Any]], salt: str) -> dict[str, Any]:
    values = [row["pnl"] for row in rows]
    pnl = sum(values, Decimal(0))
    pf = profit_factor(values)
    block5 = [
        sum((row["pnl"] for row in part), Decimal(0))
        for part in blocks(rows, 5)
    ]
    block6 = [
        sum((row["pnl"] for row in part), Decimal(0))
        for part in blocks(rows, 6)
    ]
    return {
        "event_count": len(rows),
        "net_pnl_usd": fmt(pnl),
        "profit_factor": None if pf is None else fmt(pf),
        "max_drawdown_usd": fmt(max_drawdown(values)),
        "chronological_5_blocks": [fmt(x) for x in block5],
        "chronological_5_all_positive": all(x > 0 for x in block5),
        "chronological_6_blocks": [fmt(x) for x in block6],
        "chronological_6_all_positive": all(x > 0 for x in block6),
        "monte_carlo": bootstrap(rows, salt),
    }


def stress(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [row["pnl"] for row in rows]
    ordered = sorted(values, reverse=True)
    report: dict[str, Any] = {
        "remove_best_1_pnl_usd": fmt(
            sum(ordered[1:], Decimal(0)) if ordered else Decimal(0)
        ),
        "remove_best_2_pnl_usd": fmt(
            sum(ordered[2:], Decimal(0)) if len(ordered) > 1 else Decimal(0)
        ),
        "remove_best_3_pnl_usd": fmt(
            sum(ordered[3:], Decimal(0)) if len(ordered) > 2 else Decimal(0)
        ),
        "losses_first_drawdown_usd": fmt(max_drawdown(sorted(values))),
        "winners_first_drawdown_usd": fmt(
            max_drawdown(sorted(values, reverse=True))
        ),
    }
    for multiplier in (Decimal("1.25"), Decimal("1.50"), Decimal("2.00")):
        pnl = sum(
            (
                row["gross"] - row["provider_cost"] * multiplier
                for row in rows
            ),
            Decimal(0),
        )
        report[f"provider_cost_x{fmt(multiplier)}_pnl_usd"] = fmt(pnl)
    return report


def lane_sweep(
    *,
    core: list[dict[str, Any]],
    sweep: dict[str, Any],
    name: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for multiplier, lane in sorted(
        sweep.items(),
        key=lambda item: Decimal(item[0]),
    ):
        incremental = compound_events(lane)
        combined = sorted(
            [*core, *incremental],
            key=lambda x: (x["time"], x["signal"], x["kind"]),
        )
        result[multiplier] = {
            "exact_replay": {
                "ending_capital_usd": lane["ending_capital_usd"],
                "net_realized_pnl_usd": lane["net_realized_pnl_usd"],
                "compound_incremental_pnl_usd": lane[
                    "compound_incremental_pnl_usd"
                ],
                "compound_settled_count": lane["compound_settled_count"],
                "compound_rejected_count": lane["compound_rejected_count"],
                "cross_trader_compound_deployments": lane[
                    "cross_trader_compound_deployments"
                ],
                "profit_factor": lane["profit_factor"],
                "pool_scope": lane["pool_scope"],
                "seed_multiplier": lane["seed_multiplier"],
            },
            "incremental_compound_only": {
                **metrics(incremental, f"{name}:{multiplier}:incremental"),
                "stress": stress(incremental),
            },
            "combined_core_plus_compound": metrics(
                combined,
                f"{name}:{multiplier}:combined",
            ),
        }
    return result


def timeframe_summary(multitimeframe: dict[str, Any]) -> dict[str, Any]:
    reports = multitimeframe["explorer"]["timeframe_reports"]
    result: dict[str, Any] = {}
    for timeframe in ("H4", "H1", "M15", "M5", "M1"):
        raw = reports[timeframe]
        positive = raw["positive_rules_using_timeframe"]
        result[timeframe] = {
            "population_n": raw["population_n"],
            "trader_diversity": raw["trader_diversity"],
            "positive_rule_count": len(positive),
            "best_positive_rule": None if not positive else positive[0],
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--three-lane", type=Path, required=True)
    parser.add_argument("--multitimeframe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    three = json.loads(args.three_lane.read_text())
    multi = json.loads(args.multitimeframe.read_text())
    if three["schema"] != "qore.cibo.t02-three-lane-capital-lab-arch2.v1":
        raise RuntimeError("three-lane schema drift")
    if multi["population"]["available_timeframes"] != [
        "H4",
        "H1",
        "M15",
        "M5",
        "M1",
    ]:
        raise RuntimeError("operational timeframe surface drift")

    core = core_events(three["decision_trace"])
    if len(core) != 150:
        raise RuntimeError(f"expected 150 Core settlements, got {len(core)}")

    core_metrics = metrics(core, "CORE:1")
    core_metrics["ending_capital_usd"] = three["all_trader_cibo_core"][
        "ending_capital_usd"
    ]
    core_metrics["exact_profit_factor"] = three["all_trader_cibo_core"][
        "profit_factor"
    ]

    compound = lane_sweep(
        core=core,
        sweep=three["compound_leverage_sweep"],
        name="COMPOUND",
    )
    portfolio = lane_sweep(
        core=core,
        sweep=three["compound_portfolio_leverage_sweep"],
        name="COMPOUND_PORTFOLIO",
    )

    portfolio_value_add = three["portfolio_incremental_over_local_compound"]
    best_global = multi["explorer"]["positive_leaderboard"][0]
    terminal = multi["validator"]["terminal_freeze_60_40"]

    report = {
        "schema": "qore.cibo.t02-three-lane-scientific-report-arch2.v1",
        "mode": "NON_CERTIFYING_REUSED_HOLDOUT_RESEARCH",
        "conclusion": "THREE_LANE_LAB_COMPLETE_MORE_RESEARCH_REQUIRED",
        "source": {
            "three_lane_run_id": 37137566084,
            "three_lane_artifact_id": 11278986565,
            "multitimeframe_run_id": 37134372815,
            "multitimeframe_artifact_id": 11278316141,
        },
        "market_context_lab": {
            "timeframes": ["H4", "H1", "M15", "M5", "M1"],
            "D1_excluded": True,
            "timeframe_reports": timeframe_summary(multi),
            "searched_rule_fraction_count": multi["explorer"][
                "searched_rule_fraction_count"
            ],
            "best_global_exploratory_rule": best_global,
            "rolling_5_all_positive": multi["validator"]["rolling_5"][
                "all_tests_positive"
            ],
            "rolling_6_all_positive": multi["validator"]["rolling_6"][
                "all_tests_positive"
            ],
            "terminal_all_positive": terminal["all_validation_blocks_positive"],
            "terminal_monte_carlo": terminal["validation_monte_carlo"],
            "t02_conclusion": multi["conclusion"],
        },
        "CORE": {
            "exact_1x": core_metrics,
            "t02_shadow_leverage": multi["explorer"]["shadow_leverage"],
            "note": (
                "Core base sizing is not mutated. 2x-4x Core values remain "
                "T02 shadow leverage only; Compound/Portfolio multipliers are "
                "executed inside their causal replays."
            ),
        },
        "COMPOUND": compound,
        "COMPOUND_PORTFOLIO": portfolio,
        "portfolio_value_add_at_1x": portfolio_value_add,
        "scientific_findings": {
            "compound_1x_incremental_positive": (
                dec(compound["1"]["exact_replay"][
                    "compound_incremental_pnl_usd"
                ]) > 0
            ),
            "portfolio_1x_incremental_positive": (
                dec(portfolio["1"]["exact_replay"][
                    "compound_incremental_pnl_usd"
                ]) > 0
            ),
            "portfolio_adds_value_over_local_compound_1x": (
                dec(portfolio_value_add["ending_capital_delta_usd"]) > 0
            ),
            "compound_2x_3x_incremental_positive": all(
                dec(compound[key]["exact_replay"][
                    "compound_incremental_pnl_usd"
                ]) > 0
                for key in ("2", "3")
            ),
            "portfolio_2x_3x_4x_incremental_positive": all(
                dec(portfolio[key]["exact_replay"][
                    "compound_incremental_pnl_usd"
                ]) > 0
                for key in ("2", "3", "4")
            ),
            "any_total_lane_above_initial_usd60": any(
                dec(row["exact_replay"]["ending_capital_usd"]) > Decimal("60")
                for lane in (compound, portfolio)
                for row in lane.values()
            ),
            "promotion_authorized": False,
        },
        "governance": {
            "runtime_policy_changed": False,
            "productive_sizing_changed": False,
            "qore_risk_sovereign": True,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "merge_authority": False,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "conclusion": report["conclusion"],
                "core_ending_capital_usd": report["CORE"]["exact_1x"][
                    "ending_capital_usd"
                ],
                "compound_1x_ending_capital_usd": compound["1"]["exact_replay"][
                    "ending_capital_usd"
                ],
                "portfolio_1x_ending_capital_usd": portfolio["1"][
                    "exact_replay"
                ]["ending_capital_usd"],
                "portfolio_value_add_usd": portfolio_value_add[
                    "ending_capital_delta_usd"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
