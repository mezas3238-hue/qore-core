"""Consumed-only VT-31 prop-firm drawdown governor research.

This research does not change R8 trading semantics or open fresh evidence. It
uses the already-consumed, gap05-resolved R5/R6/R8 trades and tests a finite,
predeclared family of account-level risk throttles. Each throttle is causal: the
multiplier depends only on drawdown known before the next trade. The objective
is to reduce realized and Monte-Carlo tail drawdown while preserving positive
market/side/partition economics under extra execution-cost stress.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

POLICY = "gap05"
PARTITIONS = ("r8_fresh", "r6", "r5")  # chronological
MARKETS = ("NAS100", "SP500", "US30")
SIDES = ("long", "short")
EXPECTED_SAMPLES = {"r8_fresh": 100, "r6": 111, "r5": 128}
FRICTIONS = (Decimal("0.05"), Decimal("0.075"), Decimal("0.10"))
BASE_RISK_PCTS = (
    Decimal("0.10"),
    Decimal("0.125"),
    Decimal("0.15"),
    Decimal("0.175"),
    Decimal("0.20"),
    Decimal("0.25"),
)
PROP_P95_DD_TARGET_PCT = Decimal("3.0")
PROP_P95_DD_TARGET_R_AT_0_25 = Decimal("12")
MIN_MC_POSITIVE_TERMINAL = Decimal("0.70")
POLICIES = (
    "full",
    "dd2_half",
    "dd2_5_5_half_quarter",
    "dd2_4_half_quarter",
    "dd1_5_3_half_quarter",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _weight(policy: str, drawdown: Decimal) -> Decimal:
    if policy == "full":
        return Decimal(1)
    if policy == "dd2_half":
        return Decimal(1) if drawdown < Decimal(2) else Decimal("0.5")
    if policy == "dd2_5_5_half_quarter":
        if drawdown < Decimal("2.5"):
            return Decimal(1)
        return Decimal("0.5") if drawdown < Decimal(5) else Decimal("0.25")
    if policy == "dd2_4_half_quarter":
        if drawdown < Decimal(2):
            return Decimal(1)
        return Decimal("0.5") if drawdown < Decimal(4) else Decimal("0.25")
    if policy == "dd1_5_3_half_quarter":
        if drawdown < Decimal("1.5"):
            return Decimal(1)
        return Decimal("0.5") if drawdown < Decimal(3) else Decimal("0.25")
    raise ValueError(f"unknown policy: {policy}")


def _load_trades(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text())
    partitions = cast(dict[str, dict[str, dict[str, object]]], payload["partitions"])
    rows: list[dict[str, object]] = []
    for partition in PARTITIONS:
        observed = 0
        for market in MARKETS:
            trades = cast(
                dict[str, list[dict[str, object]]],
                partitions[partition][market]["resolved_trades"],
            )[POLICY]
            for trade in trades:
                row = dict(trade)
                row["partition"] = partition
                rows.append(row)
                observed += 1
        if observed != EXPECTED_SAMPLES[partition]:
            raise AssertionError(
                f"{partition} gap05 parity failed: {observed} != {EXPECTED_SAMPLES[partition]}"
            )
    rows.sort(key=lambda row: (str(row["signal_at"]), str(row["market"])))
    if len(rows) != sum(EXPECTED_SAMPLES.values()):
        raise AssertionError("combined gap05 sample parity failed")
    return rows


def _apply(
    trades: list[dict[str, object]], policy: str, friction: Decimal
) -> list[dict[str, object]]:
    equity = Decimal(0)
    peak = Decimal(0)
    result: list[dict[str, object]] = []
    for trade in trades:
        drawdown_before = peak - equity
        weight = _weight(policy, drawdown_before)
        net = weight * (_d(trade["r_multiple"]) - friction)
        equity += net
        peak = max(peak, equity)
        row = dict(trade)
        row["risk_multiplier"] = format(weight, "f")
        row["net_base_r"] = format(net, "f")
        row["drawdown_before_base_r"] = format(drawdown_before, "f")
        result.append(row)
    return result


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["net_base_r"]) for row in rows]
    total = sum(values, Decimal(0))
    wins = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    drawdown = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "sample": len(values),
        "total_base_r": format(total, "f"),
        "mean_base_r": format(total / Decimal(len(values)), "f") if values else "0",
        "profit_factor": format(wins / losses, "f") if losses > 0 else None,
        "max_drawdown_base_r": format(drawdown, "f"),
    }


def _groups(rows: list[dict[str, object]], key: str) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return {name: _metrics(items) for name, items in sorted(grouped.items())}


def _worst_day(rows: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        grouped[str(row["local_date"])] += _d(row["net_base_r"])
    day, value = min(grouped.items(), key=lambda item: item[1])
    return {"local_date": day, "net_base_r": format(value, "f")}


def _monte_carlo(
    trades: list[dict[str, object]], policy: str, friction: Decimal
) -> dict[str, object]:
    raw = [_d(row["r_multiple"]) for row in trades]
    n = len(raw)
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    domain = (
        f"qore:vt31:prop-dd-governor:v1:{policy}:{format(friction, 'f')}"
    ).encode()
    for path_index in range(10000):
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
            sampled.extend(raw[(start + offset) % n] for offset in range(5))
            block_index += 1
        equity = Decimal(0)
        peak = Decimal(0)
        drawdown = Decimal(0)
        for raw_r in sampled[:n]:
            multiplier = _weight(policy, peak - equity)
            equity += multiplier * (raw_r - friction)
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        terminals.append(equity)
        drawdowns.append(drawdown)
    terminals.sort()
    drawdowns.sort()

    def q(values: list[Decimal], pct: int) -> Decimal:
        return values[(len(values) - 1) * pct // 100]

    probability = Decimal(sum(value > 0 for value in terminals)) / Decimal(10000)
    return {
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(probability, "f"),
        "p05_terminal_base_r": format(q(terminals, 5), "f"),
        "p50_terminal_base_r": format(q(terminals, 50), "f"),
        "p95_max_drawdown_base_r": format(q(drawdowns, 95), "f"),
    }


def _positive_group_means(groups: dict[str, dict[str, object]]) -> bool:
    return all(_d(value["mean_base_r"]) > 0 for value in groups.values())


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: vt31_prop_dd_governor_research.py FILL_ATTRITION_JSON")
        return 2
    trades = _load_trades(Path(args[0]))
    results: dict[str, object] = {}
    pass_under_worst: dict[str, bool] = {}

    for policy in POLICIES:
        friction_rows: dict[str, object] = {}
        for friction in FRICTIONS:
            weighted = _apply(trades, policy, friction)
            metrics = _metrics(weighted)
            markets = _groups(weighted, "market")
            sides = _groups(weighted, "side")
            partitions = _groups(weighted, "partition")
            mc = _monte_carlo(trades, policy, friction)
            friction_rows[format(friction, "f")] = {
                "metrics": metrics,
                "markets": markets,
                "sides": sides,
                "partitions": partitions,
                "worst_realized_day": _worst_day(weighted),
                "monte_carlo": mc,
            }
        results[policy] = friction_rows
        worst = cast(dict[str, object], friction_rows["0.10"])
        worst_mc = cast(dict[str, object], worst["monte_carlo"])
        pass_under_worst[policy] = (
            _d(worst_mc["p95_max_drawdown_base_r"]) <= PROP_P95_DD_TARGET_R_AT_0_25
            and _d(worst_mc["positive_terminal_probability"]) >= MIN_MC_POSITIVE_TERMINAL
            and _positive_group_means(cast(dict[str, dict[str, object]], worst["markets"]))
            and _positive_group_means(cast(dict[str, dict[str, object]], worst["sides"]))
            and _positive_group_means(cast(dict[str, dict[str, object]], worst["partitions"]))
        )

    selected = next((policy for policy in POLICIES if pass_under_worst[policy]), None)
    if selected is None:
        risk_sensitivity: dict[str, object] = {}
    else:
        selected_worst = cast(
            dict[str, object], cast(dict[str, object], results[selected])["0.10"]
        )
        mc = cast(dict[str, object], selected_worst["monte_carlo"])
        p95_r = _d(mc["p95_max_drawdown_base_r"])
        realized_r = _d(cast(dict[str, object], selected_worst["metrics"])["max_drawdown_base_r"])
        worst_day_r = -min(Decimal(0), _d(cast(dict[str, object], selected_worst["worst_realized_day"])["net_base_r"]))
        risk_sensitivity = {
            format(risk, "f"): {
                "base_risk_pct": format(risk, "f"),
                "realized_dd_equity_pct": format(realized_r * risk, "f"),
                "p95_dd_equity_pct": format(p95_r * risk, "f"),
                "worst_realized_day_loss_pct": format(worst_day_r * risk, "f"),
                "p95_target_3pct_pass": p95_r * risk <= PROP_P95_DD_TARGET_PCT,
            }
            for risk in BASE_RISK_PCTS
        }

    selected_index = POLICIES.index(selected) if selected is not None else -1
    adjacent_support = (
        selected is not None
        and selected_index + 1 < len(POLICIES)
        and pass_under_worst[POLICIES[selected_index + 1]]
    )
    report = {
        "schema": "qore.trader_lab.vt31_prop_dd_governor_research.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_NEW_CANDIDATE_YET",
        "source_trade_set": "R5/R6/R8-consumed gap05 resolved-only pre-tick baseline",
        "sample": len(trades),
        "finite_policy_order_least_to_more_restrictive": list(POLICIES),
        "execution_cost_stress_r": [format(value, "f") for value in FRICTIONS],
        "prop_safety_target": {
            "p95_drawdown_equity_pct": format(PROP_P95_DD_TARGET_PCT, "f"),
            "equivalent_base_r_at_0_25pct_full_risk": format(PROP_P95_DD_TARGET_R_AT_0_25, "f"),
            "minimum_mc_positive_terminal_probability": format(MIN_MC_POSITIVE_TERMINAL, "f"),
            "classification": "QORE empirical consumed-only safety target; not a prop-firm rule",
        },
        "results": results,
        "passes_worst_friction_selection_gate": pass_under_worst,
        "selected_least_restrictive_policy": selected,
        "selected_has_adjacent_more_conservative_support": adjacent_support,
        "risk_sensitivity_under_0_10r_friction": risk_sensitivity,
        "governance": (
            "This is a pre-tick consumed baseline. Re-run unchanged after historical tick "
            "resolution and provider perturbation; do not promote from this result alone."
        ),
    }
    Path("vt31-prop-dd-governor-research.json").write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    )
    summary = {
        policy: {
            "worst_friction_pass": pass_under_worst[policy],
            "realized_dd_r_0_10": cast(dict[str, object], cast(dict[str, object], results[policy])["0.10"])["metrics"]["max_drawdown_base_r"],
            "p95_dd_r_0_10": cast(dict[str, object], cast(dict[str, object], cast(dict[str, object], results[policy])["0.10"])["monte_carlo"])["p95_max_drawdown_base_r"],
            "mc_positive_0_10": cast(dict[str, object], cast(dict[str, object], cast(dict[str, object], results[policy])["0.10"])["monte_carlo"])["positive_terminal_probability"],
        }
        for policy in POLICIES
    }
    summary["selection"] = {
        "selected": selected,
        "adjacent_support": adjacent_support,
        "risk_sensitivity": risk_sensitivity,
    }
    Path("vt31-prop-dd-governor-summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
