#!/usr/bin/env python3
"""Non-certifying deep reused-holdout research for CE2I T02."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_t02_calibration_binding import (
    T02_BURNED_CONTEXT_RULES,
    T02_RUNTIME_MINIMUM_OOS_SAMPLE,
)

FAMILY = (
    ("H1_OPPOSED", (("reg_h1_body_alignment", "opposed"),)),
    (
        "H1_OPPOSED_M5_LOW",
        (
            ("reg_h1_body_alignment", "opposed"),
            ("reg_m5_efficiency_state", "low"),
        ),
    ),
    (
        "H1_OPPOSED_D1_OPPOSED",
        (
            ("reg_h1_body_alignment", "opposed"),
            ("reg_d1_body_alignment", "opposed"),
        ),
    ),
    (
        "M5_LOW_REJECTION_Q3",
        (
            ("reg_m5_efficiency_state", "low"),
            ("ctx_rejection_wick_bucket", "q3:<=0.50"),
        ),
    ),
)
PARTITIONS = (4, 5, 6)
SIMS = 10000
SEED = 20261003
FILES = {
    "R34_XAUUSD": "phase18-xauusd-r34-geometry-trades.jsonl",
    "R38_EURUSD": "phase18-eurusd-r38-geometry-trades.jsonl",
    "R43_GBPUSD": "phase18-gbpusd-r39-geometry-trades.jsonl",
    "R38_GBPJPY": "phase18-gbpjpy-r37-geometry-trades.jsonl",
    "R42_AUDJPY": "phase18-audjpy-r40-geometry-trades.jsonl",
}


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def load_native(root: Path) -> dict[str, dict[tuple[str, ...], dict[str, Any]]]:
    out = {}
    for trader, name in FILES.items():
        paths = tuple(root.rglob(name))
        if len(paths) != 1:
            raise RuntimeError(f"{trader} native file must be unique")
        rows = [
            json.loads(line)
            for line in paths[0].read_text().splitlines()
            if line.strip()
        ]
        out[trader] = {
            (
                str(row["signal_at"]),
                str(row["side"]),
                str(row["entry_price"]),
                str(row["structural_stop"]),
                str(row["technical_target"]),
            ): row
            for row in rows
        }
    return out


def tkey(row: dict[str, Any]) -> tuple[str, ...]:
    op = row["trader_opportunity"]
    return (
        str(row["market_decision_at"]),
        str(op["side"]),
        str(op["intended_entry"]),
        str(op["stop_loss"]),
        str(op["take_profit"]),
    )


def context(row: dict[str, Any]) -> dict[str, str]:
    out = {}
    for name in ("family", "target_route", "fragility_flag_count", "posture"):
        if row.get(name) is not None:
            out[name] = str(row[name])
    for prefix, name in (("ctx_", "setup_context"), ("reg_", "regime")):
        raw = row.get(name)
        if isinstance(raw, dict):
            out.update({prefix + str(k): str(v) for k, v in raw.items()})
    return out


def rule_value(row: dict[str, Any], field: str) -> str | None:
    if field == "side":
        return str(row["side"])
    value = row.get(field)
    return None if value is None else str(value)


def incremental(trace: dict[str, Any], native: dict[str, Any]) -> Decimal:
    op = trace["trader_opportunity"]
    provider = trace["market_predecision_state"]["provider_observation"]
    step = dec(op["volume_step"])
    extra_risk = step * dec(op["stop_loss_per_volume"])
    spread = (
        (dec(provider["ask"]) - dec(provider["bid"]))
        / dec(provider["tick_size"])
        * dec(provider["tick_value"])
    )
    cost = step * (
        spread
        + dec(provider["commission_per_volume_usd"])
        + dec(provider["slippage_reserve_per_volume_usd"])
    )
    return dec(native["raw_net_010_r"]) * extra_risk - cost


def dataset(\n    trace: dict[str, Any],\n    native_root: Path,\n) -> tuple[list[dict[str, Any]], dict[str, int]]:
    native = load_native(native_root)
    matched = Counter()
    rows = []
    for item in trace["opportunities"]:
        trader = str(item["trader_id"])
        if trader not in native:
            continue
        raw = native[trader].get(tkey(item))
        if raw is None:
            raise RuntimeError(f"context join failed: {trader}")
        matched[trader] += 1
        rules = [r for r in T02_BURNED_CONTEXT_RULES if r.lineage.value == trader]
        if len(rules) != 1:
            raise RuntimeError(f"T02 rule drift: {trader}")
        rule = rules[0]
        if (
            not rule.eligible_for_structural_leverage
            or rule.validation_candidate_rows < T02_RUNTIME_MINIMUM_OOS_SAMPLE
            or rule_value(raw, rule.selected_field) != rule.selected_value
        ):
            continue
        rows.append(
            {
                "time": str(item["market_decision_at"]),
                "trader": trader,
                "pnl": incremental(item, raw),
                "context": context(raw),
            }
        )
    return sorted(rows, key=lambda x: x["time"]), dict(sorted(matched.items()))


def selected(\n    rows: list[dict[str, Any]],\n    conds: tuple[tuple[str, str], ...],\n) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if all(row["context"].get(k) == v for k, v in conds)
    ]


def pnl(rows: list[dict[str, Any]]) -> Decimal:
    return sum((row["pnl"] for row in rows), Decimal(0))


def buckets(rows: list[dict[str, Any]], count: int) -> list[list[dict[str, Any]]]:
    return [
        rows[i * len(rows) // count:(i + 1) * len(rows) // count]
        for i in range(count)
    ]


def bootstrap_p05(rows: list[dict[str, Any]]) -> Decimal:
    values = [row["pnl"] for row in rows]
    if not values:
        return Decimal(0)
    rng = random.Random(SEED)
    totals = sorted(
        sum((rng.choice(values) for _ in values), Decimal(0))
        for _ in range(SIMS)
    )
    return totals[int(Decimal("0.05") * Decimal(SIMS - 1))]


def candidate(\n    rows: list[dict[str, Any]],\n    name: str,\n    conds: tuple[tuple[str, str], ...],\n) -> dict[str, Any]:
    chosen = selected(rows, conds)
    partition_results = {}
    stable = True
    for count in PARTITIONS:
        report = []
        for index, bucket in enumerate(buckets(rows, count), 1):
            sample = selected(bucket, conds)
            value = pnl(sample)
            positive = bool(sample) and value > 0
            stable = stable and positive
            report.append(
                {
                    "index": index,
                    "n": len(sample),
                    "pnl_usd": format(value, "f"),
                    "positive": positive,
                }
            )
        partition_results[str(count)] = report
    return {
        "id": name,
        "conditions": list(conds),
        "n": len(chosen),
        "trader_counts": dict(sorted(Counter(x["trader"] for x in chosen).items())),
        "pnl_usd": format(pnl(chosen), "f"),
        "bootstrap_p05_usd": format(bootstrap_p05(chosen), "f"),
        "partitions": partition_results,
        "all_4_5_6_positive": stable,
    }


def rolling(rows: list[dict[str, Any]]) -> dict[str, Any]:
    parts = buckets(rows, 5)
    out = []
    all_positive = True
    for test_index in range(1, 5):
        train = [row for part in parts[:test_index] for row in part]
        test = parts[test_index]
        ranked = []
        for name, conds in FAMILY:
            sample = selected(train, conds)
            ranked.append((pnl(sample), len(sample), name, conds))
        best = max(ranked, key=lambda x: (x[0], x[1], x[2]))
        test_rows = selected(test, best[3])
        test_pnl = pnl(test_rows)
        positive = bool(test_rows) and test_pnl > 0
        all_positive = all_positive and positive
        out.append(
            {
                "roll": test_index,
                "selected": best[2],
                "train_n": best[1],
                "train_pnl_usd": format(best[0], "f"),
                "test_n": len(test_rows),
                "test_pnl_usd": format(test_pnl, "f"),
                "positive": positive,
            }
        )
    return {"all_tests_positive": all_positive, "rolls": out}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    trace = json.loads(args.decision_trace.read_text())
    if trace.get("status") != "OBSERVATIONAL":
        raise RuntimeError("observational P0 trace required")
    rows, matched = dataset(trace, args.native_root)
    reports = [candidate(rows, name, conds) for name, conds in FAMILY]
    passed = [
        row["id"] for row in reports
        if dec(row["pnl_usd"]) > 0
        and dec(row["bootstrap_p05_usd"]) > 0
        and row["all_4_5_6_positive"]
    ]
    report = {
        "schema": "qore.cibo.t02-deep-structural-research.v1",
        "mode": "NON_CERTIFYING_REUSED_HOLDOUT",
        "native_context_match_counts": matched,
        "runtime_eligible_original_rule_n": len(rows),
        "runtime_eligible_original_rule_pnl_usd": format(pnl(rows), "f"),
        "semantic_family": [name for name, _ in FAMILY],
        "candidates": reports,
        "rolling_train_test": rolling(rows),
        "promotion_gate_passed_candidates": passed,
        "governance": {
            "runtime_policy_changed": False,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "merge_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "n": len(rows),
        "original_pnl_usd": report["runtime_eligible_original_rule_pnl_usd"],
        "passed_candidates": passed,
        "rolling": report["rolling_train_test"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
