#!/usr/bin/env python3
"""Build one integrated 1Y CIBO scientific group result.

The seven frozen Traders are only opportunity/outcome producers. Every
candidate is a CIBO-only configuration evaluated on one shared chronology,
one shared USD60 capital state and one sovereign QORE Risk state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

TRADERS = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)
TIMEFRAMES = ("H4", "H1", "M15", "M5", "M1")
SIMS = 5000
SEED = 20261003


def dec(value: object) -> Decimal:
    value = Decimal(str(value))
    if not value.is_finite():
        raise ValueError("non-finite decimal")
    return value


def fmt(value: Decimal) -> str:
    return format(value, "f")


def sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def max_drawdown(values: list[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    worst = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [row["pnl"] for row in rows]
    positives = sum((x for x in values if x > 0), Decimal(0))
    losses = -sum((x for x in values if x < 0), Decimal(0))
    net = sum(values, Decimal(0))
    count = len(values)
    return {
        "settled_count": count,
        "final_pnl_usd": fmt(net),
        "net_pnl_usd": fmt(net),
        "gross_profit_usd": fmt(positives),
        "gross_loss_usd": fmt(losses),
        "profit_factor": None if losses == 0 else fmt(positives / losses),
        "expectancy_usd": fmt(
            net / Decimal(count) if count else Decimal(0)
        ),
        "max_drawdown_usd": fmt(max_drawdown(values)),
    }


def blocks(rows: list[dict[str, Any]], count: int) -> list[Decimal]:
    return [
        sum(
            (row["pnl"] for row in rows[i * len(rows) // count : (i + 1) * len(rows) // count]),
            Decimal(0),
        )
        for i in range(count)
    ]


def quantile(values: list[Decimal], q: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * Decimal(len(ordered) - 1)
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    frac = position - Decimal(lo)
    return ordered[lo] * (Decimal(1) - frac) + ordered[hi] * frac


def monte_carlo(rows: list[dict[str, Any]], salt: str) -> dict[str, str | int]:
    values = [row["pnl"] for row in rows]
    if not values:
        return {
            "simulation_count": SIMS,
            "median_pnl_usd": "0",
            "p05_pnl_usd": "0",
            "p95_drawdown_usd": "0",
        }
    seed = int(hashlib.sha256((str(SEED) + salt).encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    totals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for _ in range(SIMS):
        sample = [rng.choice(values) for _ in values]
        totals.append(sum(sample, Decimal(0)))
        drawdowns.append(max_drawdown(sample))
    return {
        "simulation_count": SIMS,
        "median_pnl_usd": fmt(quantile(totals, Decimal("0.50"))),
        "p05_pnl_usd": fmt(quantile(totals, Decimal("0.05"))),
        "p95_drawdown_usd": fmt(quantile(drawdowns, Decimal("0.95"))),
    }


def stress(rows: list[dict[str, Any]]) -> dict[str, str]:
    values = [row["pnl"] for row in rows]
    ordered = sorted(values, reverse=True)
    provider_x2 = sum(
        (row["gross"] - row["provider_cost"] * Decimal(2) for row in rows),
        Decimal(0),
    )
    return {
        "provider_cost_x2_pnl_usd": fmt(provider_x2),
        "remove_best_3_pnl_usd": fmt(
            sum(ordered[3:], Decimal(0))
            if len(ordered) > 3
            else Decimal(0)
        ),
    }


def core_events(trace: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
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
    return sorted(out, key=lambda row: (row["time"], row["signal"]))


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
        key=lambda row: (row["time"], row["signal"]),
    )


def cibo_behavior(coverage: dict[str, Any]) -> dict[str, Any]:
    rows = coverage["rows"]
    capabilities = {str(row["capability"]): row for row in rows}
    cognitive = tuple(f"CF{i:02d}" for i in range(1, 20))
    ce2i = tuple(f"T{i:02d}" for i in range(1, 21))
    capital = tuple(f"GEN-C{i}" for i in range(1, 15))
    required = (*cognitive, *ce2i, *capital)
    return {
        "cognitive_faculties": list(cognitive),
        "ce2i_tools": list(ce2i),
        "capital_science": list(capital),
        "per_function_observability_complete": all(
            code in capabilities for code in required
        ),
        "not_integrated": [
            code
            for code in required
            if code not in capabilities
            or capabilities[code].get("status") == "NOT_INTEGRATED"
        ],
        "rows": rows,
    }


def capital_breaches(rows: list[dict[str, Any]]) -> int:
    capital = Decimal(60)
    breaches = 0
    for row in rows:
        capital += row["pnl"]
        if capital <= 0:
            breaches += 1
    return breaches


def candidate(
    *,
    group_id: str,
    multiplier: str,
    core: list[dict[str, Any]],
    local: dict[str, Any],
    portfolio: dict[str, Any],
    coverage: dict[str, Any],
) -> dict[str, Any]:
    extra = compound_events(portfolio)
    combined = sorted(
        [*core, *extra],
        key=lambda row: (row["time"], row["signal"], row["kind"]),
    )
    core_stats = stats(core)
    combined_stats = stats(combined)
    by_trader: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in combined:
        by_trader[row["trader"]].append(row)
    per_trader = {
        trader: stats(by_trader.get(trader, []))
        for trader in TRADERS
    }
    all_participate = all(
        row["settled_count"] > 0 for row in per_trader.values()
    )
    b5 = blocks(combined, 5)
    b6 = blocks(combined, 6)
    behavior = cibo_behavior(coverage)
    config = {
        "schema": "qore.cibo.trader-lab.3x1y-cibo-config.v1",
        "cibo_free_tool_choice": True,
        "t02_released_capacity": True,
        "cf01_cf19": True,
        "t01_t20": True,
        "genc01_genc14": True,
        "compound_seed_multiplier": multiplier,
        "compound_portfolio_seed_multiplier": multiplier,
        "qore_risk_sovereign": True,
    }
    return {
        "configuration_fingerprint": sha(config),
        "configuration": config,
        "configuration_scope": "CIBO_ONLY",
        "trader_parameters_changed": False,
        "trader_profitability_used_for_gate": True,
        "measurements": {
            "group_id": group_id,
            "all_7_traders_participate": all_participate,
            "per_trader_under_cibo": per_trader,
            "timeframes": list(TIMEFRAMES),
            "core": core_stats,
            "compound": {
                "incremental_pnl_usd": local["compound_incremental_pnl_usd"],
                "ending_capital_usd": local["ending_capital_usd"],
                "settled_count": local["compound_settled_count"],
            },
            "compound_portfolio": {
                "incremental_pnl_usd": portfolio["compound_incremental_pnl_usd"],
                "ending_capital_usd": portfolio["ending_capital_usd"],
                "settled_count": portfolio["compound_settled_count"],
                "value_add_vs_compound_usd": fmt(
                    dec(portfolio["compound_incremental_pnl_usd"])
                    - dec(local["compound_incremental_pnl_usd"])
                ),
            },
            "final_ending_capital_usd": portfolio["ending_capital_usd"],
            "chronological_5_blocks": [fmt(x) for x in b5],
            "chronological_6_blocks": [fmt(x) for x in b6],
            "chronological_folds_all_positive": (
                all(x > 0 for x in b5) and all(x > 0 for x in b6)
            ),
            "monte_carlo": monte_carlo(
                combined,
                f"{group_id}:{multiplier}",
            ),
            "stress": stress(combined),
            "protected_capital_breaches": capital_breaches(combined),
            "all_required_cibo_functions_accounted_for": coverage[
                "full_stack_runtime_coverage_complete"
            ],
            "cibo_function_behavior": behavior,
            "trader_profitability_used_for_gate": True,
            "qore_risk_sovereign": True,
            "combined": combined_stats,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--three-lane", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw = json.loads(args.three_lane.read_text(encoding="utf-8"))
    if raw.get("validation_mode") != "NON_CERTIFYING_BURNED_ADAPTIVE_RESEARCH":
        raise ValueError("3x1Y reporter requires burned adaptive research")
    group_id = raw.get("research_group_id")
    if group_id not in {"GROUP_1", "GROUP_2", "GROUP_3"}:
        raise ValueError("research group id missing")

    core = core_events(raw["decision_trace"])
    if not core:
        raise ValueError("integrated CIBO Core produced no settlements")
    coverage = raw["coverage"]
    candidates = []
    for multiplier in ("1", "2", "3", "4"):
        candidates.append(
            candidate(
                group_id=group_id,
                multiplier=multiplier,
                core=core,
                local=raw["compound_leverage_sweep"][multiplier],
                portfolio=raw["compound_portfolio_leverage_sweep"][multiplier],
                coverage=coverage,
            )
        )

    payload = {
        "schema": "qore.cibo.trader-lab.1y-group-result.v1",
        "group_id": group_id,
        "start_at": {
            "GROUP_1": "2019-06-30T00:00:00+00:00",
            "GROUP_2": "2020-06-30T00:00:00+00:00",
            "GROUP_3": "2021-06-30T00:00:00+00:00",
        }[group_id],
        "end_exclusive_at": {
            "GROUP_1": "2020-06-30T00:00:00+00:00",
            "GROUP_2": "2021-06-30T00:00:00+00:00",
            "GROUP_3": "2022-06-30T00:00:00+00:00",
        }[group_id],
        "traders": list(TRADERS),
        "adaptive_research_only": True,
        "execution_topology": "SINGLE_INTEGRATED_7_TRADER_PORTFOLIO",
        "shared_cibo_state": True,
        "shared_qore_risk_state": True,
        "shared_initial_capital_usd": "60",
        "per_trader_results_source_only": True,
        "integrated_per_trader_cibo_economics_required": True,
        "candidates": candidates,
        "source_three_lane_trace_sha256": raw["decision_trace"]["trace_sha256"],
        "fresh_oos_claimed": False,
        "certification_claimed": False,
        "broker_mutation": False,
        "live": False,
        "production": False,
        "real_capital": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "group_id": group_id,
                "candidate_count": len(candidates),
                "all_7_settled_by_multiplier": {
                    item["configuration"]["compound_seed_multiplier"]: item[
                        "measurements"
                    ]["all_7_traders_participate"]
                    for item in candidates
                },
                "all_7_positive_by_multiplier": {
                    item["configuration"]["compound_seed_multiplier"]: all(
                        dec(row["final_pnl_usd"]) > 0
                        for row in item["measurements"][
                            "per_trader_under_cibo"
                        ].values()
                    )
                    for item in candidates
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
