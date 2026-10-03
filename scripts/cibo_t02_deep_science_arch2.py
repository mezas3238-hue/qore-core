#!/usr/bin/env python3
"""CIBO Architect 2 — non-certifying deep science for CE2I T02.

This script is intentionally isolated from productive T02 policy. It reconstructs
predecision context from retained Phase22/native Trader evidence, separates
X_PREDECISION from Y_OUTCOME, evaluates a small preregistered universal family,
and enforces chronological TRAIN->TEST, Monte Carlo, and stress reporting.

It MUST NOT be used to authorize LIVE/Production/real-capital behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from collections.abc import Callable
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

getcontext().prec = 50

SCHEMA = "qore.cibo.t02-deep-science-arch2.v1"
DATASET_SCHEMA = "qore.cibo.t02-causal-dataset-arch2.v1"
SEED = 20261003
BOOTSTRAP_SIMS = 10_000
PERMUTATION_SIMS = 5_000
INITIAL_CAPITAL_USD = Decimal("60")
MIN_CANDIDATE_N = 20

NATIVE_FILES = {
    "R34_XAUUSD": "phase18-xauusd-r34-geometry-trades.jsonl",
    "R38_EURUSD": "phase18-eurusd-r38-geometry-trades.jsonl",
    "R43_GBPUSD": "phase18-gbpusd-r39-geometry-trades.jsonl",
    "R38_GBPJPY": "phase18-gbpjpy-r37-geometry-trades.jsonl",
    "R42_AUDJPY": "phase18-audjpy-r40-geometry-trades.jsonl",
}

# Small preregistered family. No symbol/trader-name predicate is allowed.
# H1/H2 are explicitly requested in the Owner handoff. H3-H5 are the stated
# semantic extensions: expected value, capital duration, and provider cost/risk.
FAMILY: tuple[dict[str, Any], ...] = (
    {
        "id": "H1_STRUCTURAL_OPPOSED",
        "formula": "reg_h1_body_alignment == 'opposed'",
    },
    {
        "id": "H2_STRUCTURAL_OPPOSED_M5_LOW",
        "formula": (
            "reg_h1_body_alignment == 'opposed' and "
            "reg_m5_efficiency_state == 'low'"
        ),
    },
    {
        "id": "H3_H2_EXPECTED_NET_POSITIVE",
        "formula": "H2 and expected_net_value_usd > 0",
    },
    {
        "id": "H4_H2_CAPITAL_DURATION_LE_60M",
        "formula": "H2 and expected_capital_minutes <= 60",
    },
    {
        "id": "H5_H2_PROVIDER_COST_RISK_LE_025",
        "formula": "H2 and provider_cost_to_extra_risk <= 0.25",
    },
)


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal) -> str:
    return format(value, "f")


def qtile(values: list[Decimal], q: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * Decimal(len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - Decimal(lo)
    return ordered[lo] * (Decimal(1) - frac) + ordered[hi] * frac


def max_drawdown(values: list[Decimal], opening: Decimal = Decimal(0)) -> Decimal:
    equity = opening
    peak = opening
    worst = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def min_equity(values: list[Decimal], opening: Decimal) -> Decimal:
    equity = opening
    low = opening
    for value in values:
        equity += value
        low = min(low, equity)
    return low


def temporal_buckets(
    rows: list[dict[str, Any]], count: int
) -> list[list[dict[str, Any]]]:
    return [
        rows[i * len(rows) // count : (i + 1) * len(rows) // count]
        for i in range(count)
    ]


def native_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row["signal_at"]),
        str(row["side"]),
        str(row["entry_price"]),
        str(row["structural_stop"]),
        str(row["technical_target"]),
    )


def trace_key(row: dict[str, Any]) -> tuple[str, ...]:
    op = row["trader_opportunity"]
    return (
        str(row["market_decision_at"]),
        str(op["side"]),
        str(op["intended_entry"]),
        str(op["stop_loss"]),
        str(op["take_profit"]),
    )


def load_native(
    root: Path,
) -> dict[str, dict[tuple[str, ...], dict[str, Any]]]:
    result: dict[str, dict[tuple[str, ...], dict[str, Any]]] = {}
    for trader, filename in NATIVE_FILES.items():
        paths = tuple(root.rglob(filename))
        if len(paths) != 1:
            raise RuntimeError(
                f"{trader}: expected exactly one {filename}, got {len(paths)}"
            )
        rows = [
            json.loads(line)
            for line in paths[0].read_text().splitlines()
            if line.strip()
        ]
        keyed = {native_key(row): row for row in rows}
        if len(keyed) != len(rows):
            raise RuntimeError(f"{trader}: native identity collision")
        result[trader] = keyed
    return result


def predecision_context(native: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("family", "target_route", "fragility_flag_count", "posture"):
        if native.get(key) is not None:
            out[key] = str(native[key])
    for prefix, key in (("ctx_", "setup_context"), ("reg_", "regime")):
        raw = native.get(key)
        if isinstance(raw, dict):
            for name, value in raw.items():
                out[prefix + str(name)] = str(value)
    return out


def economics(
    trace: dict[str, Any], native: dict[str, Any]
) -> dict[str, Decimal]:
    op = trace["trader_opportunity"]
    provider = trace["market_predecision_state"]["provider_observation"]
    step = dec(op["volume_step"])
    extra_risk = step * dec(op["stop_loss_per_volume"])
    extra_margin = step * dec(op["margin_per_volume"])
    spread_per_volume = (
        (dec(provider["ask"]) - dec(provider["bid"]))
        / dec(provider["tick_size"])
        * dec(provider["tick_value"])
    )
    spread_cost = step * spread_per_volume
    commission_cost = step * dec(provider["commission_per_volume_usd"])
    slippage_cost = step * dec(provider["slippage_reserve_per_volume_usd"])
    provider_cost = spread_cost + commission_cost + slippage_cost
    gross = dec(native["raw_net_010_r"]) * extra_risk
    incremental = gross - provider_cost
    return {
        "extra_risk": extra_risk,
        "extra_margin": extra_margin,
        "spread_cost": spread_cost,
        "commission_cost": commission_cost,
        "slippage_cost": slippage_cost,
        "provider_cost": provider_cost,
        "gross": gross,
        "incremental": incremental,
    }


def t02_decision(trace: dict[str, Any]) -> dict[str, Any] | None:
    matches = [
        item
        for item in (
            (trace.get("ce2i") or {}).get("opportunity_advanced_decisions") or []
        )
        if item.get("tool_code") == "T02"
    ]
    if len(matches) > 1:
        raise RuntimeError("multiple T02 decisions for one opportunity")
    return matches[0] if matches else None


def build_dataset(
    trace: dict[str, Any], native_root: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    native = load_native(native_root)
    matched = Counter()
    all_t02_decisions = 0
    all_t02_applied = 0
    rows: list[dict[str, Any]] = []

    for item in trace["opportunities"]:
        decision = t02_decision(item)
        if decision is not None:
            all_t02_decisions += 1
            if decision.get("disposition") == "APPLIED":
                all_t02_applied += 1

        trader = str(item["trader_id"])
        if trader not in native:
            continue
        raw = native[trader].get(trace_key(item))
        if raw is None:
            raise RuntimeError(
                f"native context join failed: {trader} {item['signal_fingerprint']}"
            )
        matched[trader] += 1
        econ = economics(item, raw)
        provider = item["market_predecision_state"]["provider_observation"]
        exp = item["expectation"]
        context = predecision_context(raw)
        selected = bool(
            (item.get("allocation") or {}).get("selected_by_cibo_policy")
        )
        applied = bool(
            decision and decision.get("disposition") == "APPLIED"
        )
        x = {
            "signal_fingerprint": str(item["signal_fingerprint"]),
            "trader_id_measurement_only": trader,
            "symbol_measurement_only": str(item["qore_symbol"]),
            "decision_timestamp": str(item["market_decision_at"]),
            "entry_timestamp": str(
                raw.get("entry_at") or item["market_decision_at"]
            ),
            "side": str(item["trader_opportunity"]["side"]),
            "context": context,
            "expected_net_value_usd": fmt(
                dec(exp["expected_net_value_usd"])
            ),
            "expected_capital_minutes": fmt(
                dec(exp["expected_capital_minutes"])
            ),
            "pre_ce2i_stop_risk_usd": fmt(
                dec(item["cma"]["pre_ce2i_stop_risk_usd"])
            ),
            "pre_ce2i_margin_usd": fmt(
                dec(item["cma"]["pre_ce2i_margin_usd"])
            ),
            "hard_risk_headroom_usd": fmt(
                dec(
                    item["market_predecision_state"][
                        "hard_risk_headroom_usd"
                    ]
                )
            ),
            "margin_headroom_usd": fmt(
                dec(item["market_predecision_state"]["margin_headroom_usd"])
            ),
            "extra_step_stop_risk_usd": fmt(econ["extra_risk"]),
            "extra_step_margin_usd": fmt(econ["extra_margin"]),
            "provider_spread_cost_usd": fmt(econ["spread_cost"]),
            "provider_commission_cost_usd": fmt(
                econ["commission_cost"]
            ),
            "provider_slippage_reserve_usd": fmt(
                econ["slippage_cost"]
            ),
            "provider_total_cost_usd": fmt(econ["provider_cost"]),
            "provider_cost_to_extra_risk": fmt(
                econ["provider_cost"] / econ["extra_risk"]
                if econ["extra_risk"] > 0
                else Decimal("999")
            ),
            "core_selected_before_t02": selected,
            "current_t02_applied": applied,
            "current_t02_disposition": (
                None if decision is None else decision.get("disposition")
            ),
            "current_t02_reason": (
                None if decision is None else decision.get("reason")
            ),
            "provider_key": str(provider["provider_key"]),
            "provider_symbol": str(provider["provider_symbol"]),
        }
        y = {
            "raw_net_r": fmt(dec(raw["raw_net_010_r"])),
            "exit_reason": str(raw["exit_reason"]),
            "exit_timestamp": str(raw["exit_at"]),
            "one_step_gross_incremental_usd": fmt(econ["gross"]),
            "one_step_incremental_pnl_usd": fmt(econ["incremental"]),
        }
        rows.append(
            {
                "schema": DATASET_SCHEMA,
                "X_PREDECISION": x,
                "Y_OUTCOME": y,
            }
        )

    meta = {
        "phase22_opportunity_count": len(trace["opportunities"]),
        "native_match_counts": dict(sorted(matched.items())),
        "native_match_total": sum(matched.values()),
        "t02_decision_population_all_traders": all_t02_decisions,
        "current_t02_applied_all_traders": all_t02_applied,
    }
    return (
        sorted(
            rows,
            key=lambda row: row["X_PREDECISION"]["decision_timestamp"],
        ),
        meta,
    )


def analysis_rows(
    dataset: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for wrapped in dataset:
        x = wrapped["X_PREDECISION"]
        y = wrapped["Y_OUTCOME"]
        if not x["core_selected_before_t02"]:
            continue
        rows.append(
            {
                "time": x["decision_timestamp"],
                "fingerprint": x["signal_fingerprint"],
                "trader": x["trader_id_measurement_only"],
                "symbol": x["symbol_measurement_only"],
                "side": x["side"],
                "context": x["context"],
                "expected_net": dec(x["expected_net_value_usd"]),
                "expected_minutes": dec(
                    x["expected_capital_minutes"]
                ),
                "stop_risk": dec(x["pre_ce2i_stop_risk_usd"]),
                "margin": dec(x["pre_ce2i_margin_usd"]),
                "headroom_risk": dec(x["hard_risk_headroom_usd"]),
                "headroom_margin": dec(x["margin_headroom_usd"]),
                "extra_risk": dec(x["extra_step_stop_risk_usd"]),
                "extra_margin": dec(x["extra_step_margin_usd"]),
                "spread_cost": dec(x["provider_spread_cost_usd"]),
                "commission_cost": dec(
                    x["provider_commission_cost_usd"]
                ),
                "slippage_cost": dec(
                    x["provider_slippage_reserve_usd"]
                ),
                "cost": dec(x["provider_total_cost_usd"]),
                "cost_risk": dec(
                    x["provider_cost_to_extra_risk"]
                ),
                "gross": dec(
                    y["one_step_gross_incremental_usd"]
                ),
                "pnl": dec(y["one_step_incremental_pnl_usd"]),
                "raw_r": dec(y["raw_net_r"]),
                "current_applied": bool(x["current_t02_applied"]),
            }
        )
    return sorted(rows, key=lambda row: row["time"])


def predicate(
    rule_id: str,
) -> Callable[[dict[str, Any]], bool]:
    def h2(row: dict[str, Any]) -> bool:
        return (
            row["context"].get("reg_h1_body_alignment") == "opposed"
            and row["context"].get("reg_m5_efficiency_state") == "low"
        )

    if rule_id == "H1_STRUCTURAL_OPPOSED":
        return (
            lambda row: row["context"].get(
                "reg_h1_body_alignment"
            )
            == "opposed"
        )
    if rule_id == "H2_STRUCTURAL_OPPOSED_M5_LOW":
        return h2
    if rule_id == "H3_H2_EXPECTED_NET_POSITIVE":
        return lambda row: h2(row) and row["expected_net"] > 0
    if rule_id == "H4_H2_CAPITAL_DURATION_LE_60M":
        return (
            lambda row: h2(row)
            and row["expected_minutes"] <= Decimal("60")
        )
    if rule_id == "H5_H2_PROVIDER_COST_RISK_LE_025":
        return (
            lambda row: h2(row)
            and row["cost_risk"] <= Decimal("0.25")
        )
    raise KeyError(rule_id)


def subset(
    rows: list[dict[str, Any]], rule_id: str
) -> list[dict[str, Any]]:
    keep = predicate(rule_id)
    return [row for row in rows if keep(row)]


def bootstrap(
    rows: list[dict[str, Any]], *, salt: str
) -> dict[str, Any]:
    values = [row["pnl"] for row in rows]
    if not values:
        return {
            "simulation_count": BOOTSTRAP_SIMS,
            "median_incremental_pnl_usd": "0",
            "p05_incremental_pnl_usd": "0",
            "protected_capital_breach_paths": 0,
        }
    digest = hashlib.sha256(
        (str(SEED) + salt).encode()
    ).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    totals: list[Decimal] = []
    breaches = 0
    for _ in range(BOOTSTRAP_SIMS):
        sample = [rng.choice(values) for _ in values]
        totals.append(sum(sample, Decimal(0)))
        if min_equity(sample, INITIAL_CAPITAL_USD) <= 0:
            breaches += 1
    totals.sort()
    return {
        "simulation_count": BOOTSTRAP_SIMS,
        "median_incremental_pnl_usd": fmt(
            qtile(totals, Decimal("0.50"))
        ),
        "p05_incremental_pnl_usd": fmt(
            qtile(totals, Decimal("0.05"))
        ),
        "protected_capital_breach_paths": breaches,
    }


def permutation_dd(
    rows: list[dict[str, Any]], *, salt: str
) -> dict[str, Any]:
    values = [row["pnl"] for row in rows]
    if not values:
        return {
            "simulation_count": PERMUTATION_SIMS,
            "median_dd_usd": "0",
            "p95_dd_usd": "0",
        }
    digest = hashlib.sha256(
        (str(SEED) + salt + "dd").encode()
    ).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    dds: list[Decimal] = []
    for _ in range(PERMUTATION_SIMS):
        seq = list(values)
        rng.shuffle(seq)
        dds.append(max_drawdown(seq))
    dds.sort()
    return {
        "simulation_count": PERMUTATION_SIMS,
        "median_dd_usd": fmt(qtile(dds, Decimal("0.50"))),
        "p95_dd_usd": fmt(qtile(dds, Decimal("0.95"))),
    }


def block_report(
    rows: list[dict[str, Any]], rule_id: str, count: int
) -> list[dict[str, Any]]:
    pred = predicate(rule_id)
    out = []
    for index, block in enumerate(
        temporal_buckets(rows, count), 1
    ):
        chosen = [row for row in block if pred(row)]
        value = sum(
            (row["pnl"] for row in chosen), Decimal(0)
        )
        out.append(
            {
                "index": index,
                "n": len(chosen),
                "incremental_pnl_usd": fmt(value),
                "positive": bool(chosen) and value > 0,
            }
        )
    return out


def candidate_report(
    rows: list[dict[str, Any]], rule: dict[str, Any]
) -> dict[str, Any]:
    chosen = subset(rows, rule["id"])
    pnl = sum((row["pnl"] for row in chosen), Decimal(0))
    total_risk = sum(
        (row["extra_risk"] for row in chosen), Decimal(0)
    )
    seq = [row["pnl"] for row in chosen]
    blocks = {
        str(k): block_report(rows, rule["id"], k)
        for k in (4, 5, 6)
    }
    all_blocks_positive = all(
        item["positive"]
        for report in blocks.values()
        for item in report
    )
    mc = bootstrap(chosen, salt=rule["id"])
    ddmc = permutation_dd(chosen, salt=rule["id"])
    adverse_r = [
        max(Decimal(0), -row["raw_r"]) for row in chosen
    ]
    return {
        "id": rule["id"],
        "formula": rule["formula"],
        "n": len(chosen),
        "participation_ratio_of_rich_core": (
            fmt(Decimal(len(chosen)) / Decimal(len(rows)))
            if rows
            else "0"
        ),
        "trader_counts_measurement_only": dict(
            sorted(Counter(row["trader"] for row in chosen).items())
        ),
        "incremental_pnl_usd": fmt(pnl),
        "incremental_return_on_extra_risk": (
            fmt(pnl / total_risk) if total_risk > 0 else "0"
        ),
        "chronological_max_drawdown_usd": fmt(
            max_drawdown(seq)
        ),
        "p95_adverse_r": fmt(
            qtile(adverse_r, Decimal("0.95"))
        ),
        "temporal_blocks": blocks,
        "all_4_5_6_blocks_positive": all_blocks_positive,
        "monte_carlo": mc,
        "permutation_drawdown": ddmc,
        "aggregate_positive": pnl > 0,
        "density_gate": len(chosen) >= MIN_CANDIDATE_N,
    }


def rolling_family(
    rows: list[dict[str, Any]], count: int
) -> dict[str, Any]:
    parts = temporal_buckets(rows, count)
    rolls = []
    all_positive = True
    for test_index in range(1, count):
        train = [
            row
            for part in parts[:test_index]
            for row in part
        ]
        test = parts[test_index]
        ranked: list[
            tuple[Decimal, Decimal, int, str]
        ] = []
        for rule in FAMILY:
            sample = subset(train, rule["id"])
            pnl = sum(
                (row["pnl"] for row in sample), Decimal(0)
            )
            total_risk = sum(
                (row["extra_risk"] for row in sample),
                Decimal(0),
            )
            ror = (
                pnl / total_risk
                if total_risk > 0
                else Decimal("-999")
            )
            ranked.append(
                (pnl, ror, len(sample), rule["id"])
            )
        best = max(
            ranked,
            key=lambda item: (
                item[0],
                item[1],
                item[2],
                item[3],
            ),
        )
        selected_id = best[3]
        test_rows = subset(test, selected_id)
        test_pnl = sum(
            (row["pnl"] for row in test_rows),
            Decimal(0),
        )
        test_risk = sum(
            (row["extra_risk"] for row in test_rows),
            Decimal(0),
        )
        positive = (
            bool(test_rows)
            and test_pnl > 0
            and test_risk > 0
        )
        all_positive = all_positive and positive
        rolls.append(
            {
                "roll": test_index,
                "selected_rule_from_train": selected_id,
                "train_n": best[2],
                "train_incremental_pnl_usd": fmt(best[0]),
                "train_incremental_return_on_extra_risk": fmt(
                    best[1]
                ),
                "test_n": len(test_rows),
                "test_incremental_pnl_usd": fmt(test_pnl),
                "test_incremental_return_on_extra_risk": (
                    fmt(test_pnl / test_risk)
                    if test_risk > 0
                    else "0"
                ),
                "positive": positive,
            }
        )
    return {
        "partition_count": count,
        "all_tests_positive": all_positive,
        "rolls": rolls,
    }


def stress_h2(
    rows: list[dict[str, Any]]
) -> dict[str, Any]:
    chosen = subset(
        rows, "H2_STRUCTURAL_OPPOSED_M5_LOW"
    )

    def total_for(
        cost_mult: Decimal = Decimal(1),
        extra_slippage_spread_mult: Decimal = Decimal(0),
    ) -> Decimal:
        return sum(
            (
                row["gross"]
                - row["cost"] * cost_mult
                - row["spread_cost"]
                * extra_slippage_spread_mult
                for row in chosen
            ),
            Decimal(0),
        )

    removal = []
    ordered = sorted(
        chosen, key=lambda row: row["pnl"], reverse=True
    )
    for n in (1, 2, 3):
        kept = ordered[n:]
        removal.append(
            {
                "remove_best_n": n,
                "remaining_n": len(kept),
                "incremental_pnl_usd": fmt(
                    sum(
                        (row["pnl"] for row in kept),
                        Decimal(0),
                    )
                ),
            }
        )

    losses_first = sorted(row["pnl"] for row in chosen)
    winners_first = sorted(
        (row["pnl"] for row in chosen), reverse=True
    )

    scarcity = []
    for ratio in (
        Decimal("0.05"),
        Decimal("0.025"),
        Decimal("0.01"),
    ):
        kept = [
            row
            for row in chosen
            if row["extra_risk"]
            <= row["headroom_risk"] * ratio
        ]
        scarcity.append(
            {
                "max_extra_risk_share_of_headroom": fmt(
                    ratio
                ),
                "n": len(kept),
                "incremental_pnl_usd": fmt(
                    sum(
                        (row["pnl"] for row in kept),
                        Decimal(0),
                    )
                ),
            }
        )

    margin_stress = []
    for ratio in (
        Decimal("0.10"),
        Decimal("0.05"),
        Decimal("0.025"),
    ):
        kept = [
            row
            for row in chosen
            if row["extra_margin"]
            <= row["headroom_margin"] * ratio
        ]
        margin_stress.append(
            {
                "max_extra_margin_share_of_headroom": fmt(
                    ratio
                ),
                "n": len(kept),
                "incremental_pnl_usd": fmt(
                    sum(
                        (row["pnl"] for row in kept),
                        Decimal(0),
                    )
                ),
            }
        )

    return {
        "provider_cost_multiplier": [
            {
                "multiplier": fmt(m),
                "incremental_pnl_usd": fmt(
                    total_for(cost_mult=m)
                ),
            }
            for m in (
                Decimal("1.25"),
                Decimal("1.50"),
                Decimal("2.00"),
            )
        ],
        "slippage_proxy_extra_spread": [
            {
                "extra_spread_multiplier": fmt(m),
                "incremental_pnl_usd": fmt(
                    total_for(
                        extra_slippage_spread_mult=m
                    )
                ),
            }
            for m in (
                Decimal("0.25"),
                Decimal("0.50"),
                Decimal("1.00"),
            )
        ],
        "remove_best_outcomes": removal,
        "losses_first_max_drawdown_usd": fmt(
            max_drawdown(losses_first)
        ),
        "winners_first_max_drawdown_usd": fmt(
            max_drawdown(winners_first)
        ),
        "capital_scarcity": scarcity,
        "higher_margin_usage": margin_stress,
        "different_chronological_block_sizes": {
            str(k): block_report(
                rows,
                "H2_STRUCTURAL_OPPOSED_M5_LOW",
                k,
            )
            for k in (4, 5, 6, 7, 8)
        },
    }


def compound_interaction(
    rows: list[dict[str, Any]],
    lab_result: dict[str, Any],
) -> dict[str, Any]:
    lane = lab_result[
        "all_trader_cibo_compound_portfolio"
    ]
    trades = {
        row["signal_fingerprint"]: row
        for row in lane["trades"]
    }
    h2 = subset(
        rows, "H2_STRUCTURAL_OPPOSED_M5_LOW"
    )
    overlap = [
        row for row in h2
        if row["fingerprint"] in trades
    ]
    nonoverlap = [
        row for row in h2
        if row["fingerprint"] not in trades
    ]
    overlap_compound = sum(
        (
            dec(
                trades[row["fingerprint"]][
                    "incremental_realized_pnl_usd"
                ]
            )
            for row in overlap
        ),
        Decimal(0),
    )
    return {
        "compound_selected_count": int(
            lane["compound_selected_count"]
        ),
        "compound_allowed_count": int(
            lane["compound_allowed_count"]
        ),
        "compound_incremental_pnl_usd": str(
            lane["compound_incremental_pnl_usd"]
        ),
        "h2_candidate_count": len(h2),
        "h2_overlap_with_compound_count": len(overlap),
        "h2_overlap_compound_incremental_pnl_usd": fmt(
            overlap_compound
        ),
        "h2_same_rows_t02_one_step_incremental_pnl_usd": fmt(
            sum(
                (row["pnl"] for row in overlap),
                Decimal(0),
            )
        ),
        "h2_noncompound_count": len(nonoverlap),
        "h2_noncompound_t02_incremental_pnl_usd": fmt(
            sum(
                (row["pnl"] for row in nonoverlap),
                Decimal(0),
            )
        ),
        "interpretation": (
            "Overlap is an opportunity-cost warning: on these rows "
            "Compound and one-step T02 measure the same incremental "
            "exposure economics. A productive policy must prove that "
            "T02 does not displace higher-utility Compound/Portfolio "
            "use of released capacity."
        ),
    }


def current_t02_baseline(
    rows: list[dict[str, Any]]
) -> dict[str, Any]:
    applied = [
        row for row in rows if row["current_applied"]
    ]
    value = sum(
        (row["pnl"] for row in applied), Decimal(0)
    )
    risk = sum(
        (row["extra_risk"] for row in applied),
        Decimal(0),
    )
    return {
        "applied_count_rich_context": len(applied),
        "incremental_pnl_usd": fmt(value),
        "incremental_return_on_extra_risk": (
            fmt(value / risk) if risk > 0 else "0"
        ),
        "trader_counts_measurement_only": dict(
            sorted(
                Counter(
                    row["trader"] for row in applied
                ).items()
            )
        ),
        "economic_status": (
            "FAIL"
            if value <= 0
            else "POSITIVE_MEASUREMENT_ONLY"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--decision-trace", type=Path, required=True
    )
    parser.add_argument(
        "--native-root", type=Path, required=True
    )
    parser.add_argument(
        "--lab-result", type=Path, required=True
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True
    )
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text())
    if trace.get("status") != "OBSERVATIONAL":
        raise RuntimeError(
            "T02 research requires the observational reused-holdout trace"
        )
    lab_result = json.loads(args.lab_result.read_text())
    dataset, meta = build_dataset(
        trace, args.native_root
    )
    rows = analysis_rows(dataset)

    if meta["native_match_total"] != 486:
        raise RuntimeError(
            "expected 486 deterministic Turtle matches, "
            f"got {meta['native_match_total']}"
        )
    if meta["t02_decision_population_all_traders"] != 150:
        raise RuntimeError(
            "expected 150 runtime T02 evaluations on the P0 population"
        )
    if meta["current_t02_applied_all_traders"] != 15:
        raise RuntimeError(
            "expected 15 current T02 APPLIED decisions"
        )
    if len(rows) != 127:
        raise RuntimeError(
            "expected 127 rich-context Core-selected rows, "
            f"got {len(rows)}"
        )

    candidates = [
        candidate_report(rows, rule)
        for rule in FAMILY
    ]
    rolling = [
        rolling_family(rows, count)
        for count in (5, 6)
    ]
    rolling_all_positive = all(
        item["all_tests_positive"] for item in rolling
    )

    promotion_candidates = [
        row["id"]
        for row in candidates
        if row["density_gate"]
        and row["aggregate_positive"]
        and dec(
            row[
                "incremental_return_on_extra_risk"
            ]
        )
        > 0
        and dec(
            row["monte_carlo"][
                "median_incremental_pnl_usd"
            ]
        )
        > 0
        and row["monte_carlo"][
            "protected_capital_breach_paths"
        ]
        == 0
        and row["all_4_5_6_blocks_positive"]
    ]

    scientific_candidates = (
        promotion_candidates
        if rolling_all_positive
        else []
    )
    any_signal = any(
        row["aggregate_positive"]
        and row["n"] >= MIN_CANDIDATE_N
        for row in candidates
    )
    conclusion = (
        "T02_SCIENTIFIC_CANDIDATE_PASS"
        if scientific_candidates
        else "T02_MORE_RESEARCH_REQUIRED"
        if any_signal
        else "T02_FALSIFIED_ON_CURRENT_EVIDENCE"
    )

    report = {
        "schema": SCHEMA,
        "mode": "NON_CERTIFYING_REUSED_HOLDOUT_RESEARCH",
        "conclusion": conclusion,
        "source": {
            "p0_workflow_run_id": 37127302531,
            "p0_artifact_id": 11275124190,
            "p0_head_sha": (
                "3e2e6ca898d400d8ed8359659ed032708cf7eeb3"
            ),
            "native_artifact_ids": [
                11255538834,
                11256765185,
                11256465614,
                11255244229,
                11256249712,
            ],
        },
        "population": {
            **meta,
            "rich_context_core_selected_count": len(rows),
            "rich_context_coverage_of_t02_decision_population": fmt(
                Decimal(len(rows))
                / Decimal(
                    meta[
                        "t02_decision_population_all_traders"
                    ]
                )
            ),
            "missing_rich_context_core_selected_count": (
                meta["t02_decision_population_all_traders"]
                - len(rows)
            ),
        },
        "causal_separation": {
            "decision_surface": "X_PREDECISION only",
            "evaluation_surface": (
                "Y_OUTCOME only after rule freeze"
            ),
            "symbol_used_as_primary_rule": False,
            "trader_id_used_as_primary_rule": False,
            "outcome_used_for_admission": False,
            "future_market_used_for_admission": False,
        },
        "current_t02": current_t02_baseline(rows),
        "preregistered_family": FAMILY,
        "candidates": candidates,
        "rolling_train_test": rolling,
        "rolling_all_tests_positive": (
            rolling_all_positive
        ),
        "promotion_gate_candidates_before_family_rolling": (
            promotion_candidates
        ),
        "scientific_candidate_ids": scientific_candidates,
        "h2_stress_matrix": stress_h2(rows),
        "compound_interaction": compound_interaction(
            rows, lab_result
        ),
        "decision": {
            "minimum_candidate_n": MIN_CANDIDATE_N,
            "hard_walk_forward_rule": (
                "EVERY TEST incremental P/L must be > 0; "
                "no pooled rescue"
            ),
            "reason": (
                "Positive aggregate signal exists, but the "
                "preregistered family fails the mandatory "
                "chronological TRAIN->TEST gate. No runtime "
                "policy promotion is scientifically justified."
                if conclusion
                == "T02_MORE_RESEARCH_REQUIRED"
                else "See candidate gates."
            ),
        },
        "governance": {
            "runtime_policy_changed": False,
            "productive_t02_policy_edited": False,
            "phase22_transport_edited": False,
            "cma_edited": False,
            "qore_risk_edited": False,
            "settlement_edited": False,
            "broker_mutation": False,
            "vps_used": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "fundednext_live": False,
            "merge_authority": False,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
        },
    }

    args.output_dir.mkdir(
        parents=True, exist_ok=True
    )
    dataset_path = (
        args.output_dir
        / "t02-causal-dataset-arch2.jsonl"
    )
    report_path = (
        args.output_dir
        / "t02-deep-science-arch2-report.json"
    )
    dataset_path.write_text(
        "".join(
            json.dumps(row, sort_keys=True) + "\n"
            for row in dataset
        )
    )
    report_path.write_text(
        json.dumps(
            report, indent=2, sort_keys=True
        )
        + "\n"
    )

    print(
        json.dumps(
            {
                "conclusion": conclusion,
                "current_t02_incremental_pnl_usd": report[
                    "current_t02"
                ]["incremental_pnl_usd"],
                "rich_context_core_selected_count": len(rows),
                "candidate_summary": [
                    {
                        "id": row["id"],
                        "n": row["n"],
                        "pnl_usd": row[
                            "incremental_pnl_usd"
                        ],
                        "mc_p05_usd": row[
                            "monte_carlo"
                        ]["p05_incremental_pnl_usd"],
                        "all_4_5_6_positive": row[
                            "all_4_5_6_blocks_positive"
                        ],
                    }
                    for row in candidates
                ],
                "rolling_all_tests_positive": (
                    rolling_all_positive
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
