#!/usr/bin/env python3
"""CIBO T02 multi-timeframe Trader Lab Explorer/Validator.

Research-only laboratory:
1) consumes the causal X_PREDECISION/Y_OUTCOME dataset produced by Architect 2;
2) requires genuine Trader Lab candidates to be RESEARCH_READY;
3) explores many predecision-only rules on TRAIN;
4) freezes the selected rule before each chronological TEST;
5) reports a live-style positive leaderboard without using that leaderboard as
   certification evidence.

No productive T02 policy, sizing authority, broker mutation, LIVE, Production,
real capital, or merge authority is granted by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

SCHEMA = "qore.cibo.t02-multitimeframe-trader-lab-arch2.v1"
SEED = 20261003
SIMS = 5000
LEVERAGE_FRACTIONS = (
    Decimal("0.25"),
    Decimal("0.50"),
    Decimal("0.75"),
    Decimal("1.00"),
)

CAT_FIELDS = (
    "side",
    "family",
    "target_route",
    "fragility_flag_count",
    "posture",
    "reg_d1_body_alignment",
    "reg_d1_range_state",
    "reg_h4_body_alignment",
    "reg_h4_range_state",
    "reg_h1_body_alignment",
    "reg_h1_range_state",
    "reg_m5_displacement_alignment",
    "reg_m5_efficiency_state",
    "reg_m5_volatility_state",
    "reg_m1_last_body_alignment",
    "reg_m1_raid_state",
    "ctx_session",
    "ctx_timeframe",
    "ctx_prior_body_alignment",
    "ctx_source_range_state_bucket",
    "ctx_rejection_wick_bucket",
    "ctx_reclaim_latency_bucket",
    "ctx_strategy_projected_r_bucket",
    "ctx_strategy_target_distance_range_bucket",
)

NUM_FIELDS = (
    "expected_net_value_usd",
    "expected_capital_minutes",
    "provider_cost_to_extra_risk",
    "pre_ce2i_stop_risk_usd",
    "pre_ce2i_margin_usd",
    "hard_risk_headroom_usd",
    "margin_headroom_usd",
    "m1_last_body_efficiency",
    "m1_last_range_to_60_avg",
    "m1_range_5_to_60_avg",
    "m1_range_15_to_60_avg",
    "m1_return_5_in_60_avg_range",
    "m1_return_15_in_60_avg_range",
    "m1_position_in_60_range",
    "m1_reference_range_width_in_stop_units",
    "m1_entry_to_reference_high_in_stop_units",
    "m1_entry_to_reference_low_in_stop_units",
    "m1_minutes_from_ny_1000",
    "m1_closed_bar_count_predecision",
)

REQUIRED_TIMEFRAME_KEYS = {
    "D1": ("reg_d1_body_alignment", "reg_d1_range_state"),
    "H4": ("reg_h4_body_alignment", "reg_h4_range_state"),
    "H1": ("reg_h1_body_alignment", "reg_h1_range_state"),
    "M5": (
        "reg_m5_displacement_alignment",
        "reg_m5_efficiency_state",
        "reg_m5_volatility_state",
    ),
    "M1": (
        "reg_m1_last_body_alignment",
        "reg_m1_raid_state",
        "m1_last_body_efficiency",
        "m1_last_range_to_60_avg",
        "m1_position_in_60_range",
        "m1_reference_range_width_in_stop_units",
    ),
}


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


def blocks(rows: list[dict[str, Any]], count: int) -> list[list[dict[str, Any]]]:
    return [
        rows[i * len(rows) // count : (i + 1) * len(rows) // count]
        for i in range(count)
    ]


def load_trader_lab(audit_path: Path) -> dict[str, str]:
    audit = json.loads(audit_path.read_text())
    if audit.get("all_phases_green") is not True:
        raise RuntimeError("Trader Lab audit is not all-phases GREEN")
    if audit.get("candidate_count") != 7:
        raise RuntimeError("Trader Lab audit must contain seven candidates")
    phase = audit["phases"][0]
    out: dict[str, str] = {}
    for trader, row in phase["traders"].items():
        if row.get("trader_lab_candidate") is not True:
            raise RuntimeError(f"{trader}: not a genuine Trader Lab candidate")
        if row.get("trader_lab_state") != "research_ready":
            raise RuntimeError(f"{trader}: Trader Lab state is not RESEARCH_READY")
        token = str(row.get("output_token") or "")
        if len(token) != 64:
            raise RuntimeError(f"{trader}: candidate fingerprint missing")
        out[str(trader)] = token
    if len(out) != 7:
        raise RuntimeError("expected seven Trader Lab candidate fingerprints")
    return out


def load_rows(dataset_path: Path, candidate_fps: dict[str, str]) -> list[dict[str, Any]]:
    out = []
    for line in dataset_path.read_text().splitlines():
        if not line.strip():
            continue
        wrapped = json.loads(line)
        x = wrapped["X_PREDECISION"]
        y = wrapped["Y_OUTCOME"]
        if not x["core_selected_before_t02"]:
            continue
        trader = str(x["trader_id_measurement_only"])
        if trader not in candidate_fps:
            raise RuntimeError(f"{trader}: no Trader Lab candidate binding")
        context = dict(x["context"])
        row: dict[str, Any] = {
            "time": str(x["decision_timestamp"]),
            "fingerprint": str(x["signal_fingerprint"]),
            "candidate_fingerprint": candidate_fps[trader],
            "trader_measurement_only": trader,
            "symbol_measurement_only": str(x["symbol_measurement_only"]),
            "side": str(x["side"]),
            "family": context.get("family"),
            "target_route": context.get("target_route"),
            "fragility_flag_count": context.get("fragility_flag_count"),
            "posture": context.get("posture"),
            "pnl": dec(y["one_step_incremental_pnl_usd"]),
            "gross": dec(y["one_step_gross_incremental_usd"]),
            "extra_risk": dec(x["extra_step_stop_risk_usd"]),
            "provider_cost": dec(x["provider_total_cost_usd"]),
            "spread_cost": dec(x["provider_spread_cost_usd"]),
        }
        for key, value in context.items():
            row[key] = value
        for key in NUM_FIELDS:
            row[key] = dec(x[key])
        out.append(row)
    return sorted(out, key=lambda row: row["time"])


@dataclass(frozen=True)
class Atom:
    field: str
    op: str
    value: str

    def key(self) -> tuple[str, str, str]:
        return (self.field, self.op, self.value)

    def matches(self, row: dict[str, Any]) -> bool:
        value = row.get(self.field)
        if self.op == "eq":
            return value is not None and str(value) == self.value
        threshold = dec(self.value)
        if value is None:
            return False
        observed = dec(value)
        if self.op == "le":
            return observed <= threshold
        if self.op == "ge":
            return observed >= threshold
        raise ValueError(self.op)

    def render(self) -> str:
        symbol = {"eq": "==", "le": "<=", "ge": ">="}[self.op]
        return f"{self.field} {symbol} {self.value}"


def build_atoms(train: list[dict[str, Any]]) -> list[Atom]:
    minimum = max(3, len(train) // 20)
    atoms: list[Atom] = []
    for field in CAT_FIELDS:
        values = Counter(str(row[field]) for row in train if row.get(field) is not None)
        for value, n in values.items():
            if n >= minimum:
                atoms.append(Atom(field, "eq", value))
    for field in NUM_FIELDS:
        values = [dec(row[field]) for row in train if row.get(field) is not None]
        if len(values) < minimum:
            continue
        thresholds = {
            qtile(values, Decimal("0.25")),
            qtile(values, Decimal("0.50")),
            qtile(values, Decimal("0.75")),
        }
        for threshold in thresholds:
            atoms.append(Atom(field, "le", fmt(threshold)))
            atoms.append(Atom(field, "ge", fmt(threshold)))
    return sorted(set(atoms), key=Atom.key)


def apply_rule(
    rows: list[dict[str, Any]],
    atoms: tuple[Atom, ...],
) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if all(atom.matches(row) for atom in atoms)
    ]


def rule_metrics(
    rows: list[dict[str, Any]],
    atoms: tuple[Atom, ...],
    fraction: Decimal,
) -> dict[str, Any]:
    selected = apply_rule(rows, atoms)
    pnl = sum((row["pnl"] * fraction for row in selected), Decimal(0))
    risk = sum((row["extra_risk"] * fraction for row in selected), Decimal(0))
    values = [row["pnl"] * fraction for row in selected]
    return {
        "n": len(selected),
        "pnl": pnl,
        "ror": pnl / risk if risk > 0 else Decimal("-999"),
        "dd": max_drawdown(values),
        "trader_count": len({row["trader_measurement_only"] for row in selected}),
    }


def compatible(atoms: tuple[Atom, ...]) -> bool:
    fields = [atom.field for atom in atoms]
    return len(fields) == len(set(fields))


def explorer(
    train: list[dict[str, Any]],
    *,
    max_rules: int = 12000,
    leaderboard_n: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    atoms = build_atoms(train)
    min_n = max(6, len(train) // 12)

    singles: list[tuple[float, Atom]] = []
    for atom in atoms:
        m = rule_metrics(train, (atom,), Decimal("1"))
        if m["n"] < min_n:
            continue
        score = float(m["pnl"] - Decimal("0.35") * m["dd"])
        singles.append((score, atom))
    singles.sort(key=lambda x: (x[0], x[1].key()), reverse=True)
    seed_atoms = [atom for _, atom in singles[:36]]
    triple_atoms = seed_atoms[:16]

    rules: list[tuple[Atom, ...]] = [(atom,) for atom in seed_atoms]
    rules.extend(
        pair
        for pair in itertools.combinations(seed_atoms, 2)
        if compatible(pair)
    )
    rules.extend(
        triple
        for triple in itertools.combinations(triple_atoms, 3)
        if compatible(triple)
    )
    unique: dict[tuple[tuple[str, str, str], ...], tuple[Atom, ...]] = {}
    for rule in rules:
        key = tuple(sorted(atom.key() for atom in rule))
        unique[key] = tuple(sorted(rule, key=Atom.key))
        if len(unique) >= max_rules:
            break

    scored = []
    for rule in unique.values():
        for fraction in LEVERAGE_FRACTIONS:
            m = rule_metrics(train, rule, fraction)
            if m["n"] < min_n or m["pnl"] <= 0 or m["ror"] <= 0:
                continue
            concentration_penalty = Decimal("0.20") * m["dd"]
            score = m["pnl"] - concentration_penalty
            scored.append(
                {
                    "rule": rule,
                    "fraction": fraction,
                    "metrics": m,
                    "score": score,
                }
            )
    scored.sort(
        key=lambda x: (
            x["score"],
            x["metrics"]["pnl"],
            x["metrics"]["ror"],
            x["metrics"]["n"],
        ),
        reverse=True,
    )
    return scored[:leaderboard_n], len(unique) * len(LEVERAGE_FRACTIONS)


def serial_rule(item: dict[str, Any]) -> dict[str, Any]:
    atoms = item["rule"]
    m = item["metrics"]
    return {
        "formula": " AND ".join(atom.render() for atom in atoms),
        "conditions": [
            {"field": atom.field, "op": atom.op, "value": atom.value}
            for atom in atoms
        ],
        "leverage_fraction_of_one_provider_step": fmt(item["fraction"]),
        "train_n": m["n"],
        "train_incremental_pnl_usd": fmt(m["pnl"]),
        "train_incremental_return_on_extra_risk": fmt(m["ror"]),
        "train_max_drawdown_usd": fmt(m["dd"]),
        "train_trader_diversity": m["trader_count"],
        "train_score": fmt(item["score"]),
        "uses_m1_features": any(
            atom.field.startswith("m1_") or atom.field.startswith("reg_m1_")
            for atom in atoms
        ),
    }


def evaluate_frozen(
    test: list[dict[str, Any]],
    selected: dict[str, Any],
) -> dict[str, Any]:
    m = rule_metrics(test, selected["rule"], selected["fraction"])
    return {
        "n": m["n"],
        "incremental_pnl_usd": fmt(m["pnl"]),
        "incremental_return_on_extra_risk": fmt(m["ror"]) if m["n"] else "0",
        "max_drawdown_usd": fmt(m["dd"]),
        "trader_diversity": m["trader_count"],
        "positive": m["n"] > 0 and m["pnl"] > 0 and m["ror"] > 0,
    }


def rolling(rows: list[dict[str, Any]], count: int) -> dict[str, Any]:
    parts = blocks(rows, count)
    rolls = []
    all_positive = True
    for test_idx in range(1, count):
        train = [row for part in parts[:test_idx] for row in part]
        test = parts[test_idx]
        board, searched = explorer(train, leaderboard_n=10)
        if not board:
            rolls.append(
                {
                    "roll": test_idx,
                    "searched_rule_fraction_count": searched,
                    "status": "NO_POSITIVE_TRAIN_RULE",
                    "positive": False,
                }
            )
            all_positive = False
            continue
        selected = board[0]
        test_result = evaluate_frozen(test, selected)
        all_positive = all_positive and test_result["positive"]
        rolls.append(
            {
                "roll": test_idx,
                "searched_rule_fraction_count": searched,
                "selected_from_train": serial_rule(selected),
                "test": test_result,
                "positive": test_result["positive"],
            }
        )
    return {
        "partition_count": count,
        "all_tests_positive": all_positive,
        "rolls": rolls,
    }


def bootstrap(values: list[Decimal], salt: str) -> dict[str, Any]:
    if not values:
        return {
            "simulation_count": SIMS,
            "median_incremental_pnl_usd": "0",
            "p05_incremental_pnl_usd": "0",
        }
    seed = int(hashlib.sha256((str(SEED) + salt).encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    totals = sorted(
        sum((rng.choice(values) for _ in values), Decimal(0))
        for _ in range(SIMS)
    )
    return {
        "simulation_count": SIMS,
        "median_incremental_pnl_usd": fmt(qtile(totals, Decimal("0.50"))),
        "p05_incremental_pnl_usd": fmt(qtile(totals, Decimal("0.05"))),
    }


def terminal_freeze(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cut = len(rows) * 3 // 5
    train = rows[:cut]
    untouched = rows[cut:]
    validation_blocks = blocks(untouched, 2)
    board, searched = explorer(train, leaderboard_n=25)
    if not board:
        return {
            "searched_rule_fraction_count": searched,
            "status": "NO_POSITIVE_TRAIN_RULE",
            "all_validation_blocks_positive": False,
        }
    selected = board[0]
    block_results = [
        evaluate_frozen(block, selected) for block in validation_blocks
    ]
    selected_rows = apply_rule(untouched, selected["rule"])
    fraction = selected["fraction"]
    values = [row["pnl"] * fraction for row in selected_rows]

    stress = {}
    for multiplier in (Decimal("1.25"), Decimal("1.50"), Decimal("2.00")):
        stressed = sum(
            (
                (row["gross"] - row["provider_cost"] * multiplier) * fraction
                for row in selected_rows
            ),
            Decimal(0),
        )
        stress[f"provider_cost_x{fmt(multiplier)}"] = fmt(stressed)
    ordered = sorted(values, reverse=True)
    stress["remove_best_1"] = fmt(sum(ordered[1:], Decimal(0))) if ordered else "0"
    stress["remove_best_2"] = fmt(sum(ordered[2:], Decimal(0))) if len(ordered) > 1 else "0"
    stress["remove_best_3"] = fmt(sum(ordered[3:], Decimal(0))) if len(ordered) > 2 else "0"

    return {
        "train_fraction": "0.60",
        "validation_fraction": "0.40",
        "searched_rule_fraction_count": searched,
        "frozen_rule": serial_rule(selected),
        "validation_blocks": block_results,
        "all_validation_blocks_positive": all(x["positive"] for x in block_results),
        "validation_candidate_n": len(selected_rows),
        "validation_monte_carlo": bootstrap(
            values, "terminal:" + serial_rule(selected)["formula"]
        ),
        "validation_stress": stress,
    }


def timeframe_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for timeframe, keys in REQUIRED_TIMEFRAME_KEYS.items():
        present = sum(
            1 for row in rows
            if all(row.get(key) is not None for key in keys)
        )
        out[timeframe] = {
            "required_keys": list(keys),
            "rows_with_all_keys": present,
            "coverage_ratio": fmt(
                Decimal(present) / Decimal(len(rows)) if rows else Decimal(0)
            ),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--causal-dataset", type=Path, required=True)
    parser.add_argument("--trader-lab-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    candidate_fps = load_trader_lab(args.trader_lab_audit)
    rows = load_rows(args.causal_dataset, candidate_fps)
    if len(rows) != 145:
        raise RuntimeError(
            f"expected 145 rich-context Core-selected rows after VT31 M1 augmentation, got {len(rows)}"
        )

    board, searched = explorer(rows, leaderboard_n=50)
    live_board = [serial_rule(item) for item in board]
    wfo5 = rolling(rows, 5)
    wfo6 = rolling(rows, 6)
    terminal = terminal_freeze(rows)

    mc = terminal.get("validation_monte_carlo", {})
    validation_blocks = terminal.get("validation_blocks", [])
    universality_proven = bool(
        terminal.get("frozen_rule", {}).get("train_trader_diversity", 0) >= 2
        and validation_blocks
        and all(block.get("trader_diversity", 0) >= 2 for block in validation_blocks)
    )
    scientific_pass = bool(
        wfo5["all_tests_positive"]
        and wfo6["all_tests_positive"]
        and terminal.get("all_validation_blocks_positive") is True
        and terminal.get("validation_candidate_n", 0) >= 20
        and dec(mc.get("median_incremental_pnl_usd", "0")) > 0
        and dec(mc.get("p05_incremental_pnl_usd", "0")) > 0
        and universality_proven
    )
    has_positive_exploration = bool(live_board)
    conclusion = (
        "T02_SCIENTIFIC_CANDIDATE_PASS"
        if scientific_pass
        else "T02_MORE_RESEARCH_REQUIRED"
        if has_positive_exploration
        else "T02_FALSIFIED_ON_CURRENT_EVIDENCE"
    )

    report = {
        "schema": SCHEMA,
        "mode": "NON_CERTIFYING_REUSED_HOLDOUT_RESEARCH",
        "conclusion": conclusion,
        "population": {
            "rich_context_core_selected_count": len(rows),
            "candidate_binding_count": len(candidate_fps),
            "candidate_bindings": candidate_fps,
            "timeframe_coverage": timeframe_coverage(rows),
            "available_timeframes": list(REQUIRED_TIMEFRAME_KEYS),
            "missing_timeframes_are_never_invented": True,
        },
        "explorer": {
            "training_feature_policy": "X_PREDECISION_ONLY",
            "outcome_features_forbidden_as_rule_inputs": True,
            "trader_or_symbol_predicate_forbidden": True,
            "leverage_fractions": [fmt(x) for x in LEVERAGE_FRACTIONS],
            "searched_rule_fraction_count": searched,
            "leaderboard_is_exploratory_not_validation": True,
            "positive_leaderboard": live_board,
        },
        "validator": {
            "rolling_5": wfo5,
            "rolling_6": wfo6,
            "terminal_freeze_60_40": terminal,
            "hard_gate": "every chronological TEST > 0; no pooled rescue",
            "universality_gate_proven": universality_proven,
            "universality_rule": (
                "No trader/symbol predicate. A final rule must span at least two "
                "Trader lineages in TRAIN and every terminal validation block. "
                "M1-only VT31 signals remain exploratory until cross-lineage evidence exists."
            ),
        },
        "governance": {
            "runtime_policy_changed": False,
            "productive_t02_policy_edited": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "vps_used": False,
            "merge_authority": False,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "outcome_aware_test_admission": False,
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "t02-multitimeframe-trader-lab-report.json"
    dashboard_path = args.output_dir / "t02-positive-dashboard.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    dashboard_path.write_text(
        json.dumps(
            {
                "schema": "qore.cibo.t02-positive-dashboard.v1",
                "conclusion": conclusion,
                "available_timeframes": list(REQUIRED_TIMEFRAME_KEYS),
                "searched_rule_fraction_count": searched,
                "top_positive_rules": live_board[:20],
                "rolling_5_all_tests_positive": wfo5["all_tests_positive"],
                "rolling_6_all_tests_positive": wfo6["all_tests_positive"],
                "terminal_validation_all_positive": terminal.get(
                    "all_validation_blocks_positive", False
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        json.dumps(
            {
                "conclusion": conclusion,
                "rows": len(rows),
                "searched_rule_fraction_count": searched,
                "positive_dashboard_rows": len(live_board),
                "rolling_5_all_positive": wfo5["all_tests_positive"],
                "rolling_6_all_positive": wfo6["all_tests_positive"],
                "terminal_all_positive": terminal.get(
                    "all_validation_blocks_positive", False
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
