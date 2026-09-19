"""VT31 NAS100 hybrid CORE + SECONDARY capital-intelligence policy.

Research-only consumed-evidence composition.

CORE:
- exact intelligent specialist trades from the low-drawdown WFO identity;
- requested risk unit = 1.00R.

SECONDARY:
- causal OCO opportunity only on dates where CORE did not execute;
- requested risk unit = 0.05R;
- monthly secondary capital budget = 0.50R;
- unused budget may carry at most 0.05R into the next month.

The budget is a capital-exposure constraint, not a retrospective trade-count
filter. CORE trades do not consume SECONDARY budget. QORE Risk remains
sovereign and may reduce or deny requested exposure in runtime integration.

Economics below are capital-weighted:
net contribution = requested_risk_multiplier * (gross_trade_R - 0.05R).

Raw trade count remains the literal number of executed opportunities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

SCHEMA = "qore.vt31.nas100.hybrid_core_secondary.v1"
IDENTITY = "VT31_NAS100_HYBRID_CORE_SECONDARY_V1"
FRICTION = Decimal("0.05")
CORE_RISK = Decimal("1.00")
SECONDARY_RISK = Decimal("0.05")
SECONDARY_MONTHLY_BUDGET = Decimal("0.50")
SECONDARY_CARRY_CAP = Decimal("0.05")


def _metrics(values: list[Decimal]) -> dict[str, object]:
    if not values:
        return {
            "sample": 0,
            "wins": 0,
            "losses": 0,
            "flats": 0,
            "total_r": "0",
            "mean_r": None,
            "profit_factor": None,
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
        }
    gross_profit = sum((item for item in values if item > 0), Decimal(0))
    gross_loss = -sum((item for item in values if item < 0), Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    current_losing = 0
    max_losing = 0
    for item in values:
        equity += item
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if item < 0:
            current_losing += 1
            max_losing = max(max_losing, current_losing)
        else:
            current_losing = 0
    return {
        "sample": len(values),
        "wins": sum(item > 0 for item in values),
        "losses": sum(item < 0 for item in values),
        "flats": sum(item == 0 for item in values),
        "total_r": format(sum(values, Decimal(0)), "f"),
        "mean_r": format(sum(values, Decimal(0)) / Decimal(len(values)), "f"),
        "profit_factor": (
            None
            if gross_loss == 0
            else format(gross_profit / gross_loss, "f")
        ),
        "max_drawdown_r": format(max_dd, "f"),
        "max_losing_streak": max_losing,
    }


def _monte_carlo(
    values: list[Decimal],
    *,
    domain: bytes,
) -> dict[str, object]:
    n = len(values)
    if n == 0:
        return {
            "algorithm": "sha256-moving-block-bootstrap-v1",
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": "0",
            "p05_terminal_r": "0",
            "p50_terminal_r": "0",
            "p95_max_drawdown_r": "0",
        }
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
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
            sampled.extend(
                values[(start + offset) % n]
                for offset in range(5)
            )
            block_index += 1
        equity = Decimal(0)
        peak = Decimal(0)
        max_dd = Decimal(0)
        for value in sampled[:n]:
            equity += value
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        terminals.append(equity)
        drawdowns.append(max_dd)
    terminals.sort()
    drawdowns.sort()
    return {
        "algorithm": "sha256-moving-block-bootstrap-v1",
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(
            Decimal(sum(value > 0 for value in terminals))
            / Decimal(10000),
            "f",
        ),
        "p05_terminal_r": format(
            terminals[(len(terminals) - 1) * 5 // 100],
            "f",
        ),
        "p50_terminal_r": format(
            terminals[(len(terminals) - 1) * 50 // 100],
            "f",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(len(drawdowns) - 1) * 95 // 100],
            "f",
        ),
    }


def _core_file(root: Path) -> Path:
    matches = sorted(root.glob("vt31-nas100-specialist-r1-*.json"))
    if len(matches) != 1:
        raise ValueError(f"expected one CORE replay, got {len(matches)}")
    return matches[0]


def _oco_file(root: Path) -> Path:
    matches = sorted(root.glob("oco-*.json"))
    if len(matches) != 1:
        raise ValueError(f"expected one OCO replay, got {len(matches)}")
    return matches[0]


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def compose(core_root: Path, oco_root: Path) -> dict[str, object]:
    core = _load(_core_file(core_root))
    oco = _load(_oco_file(oco_root))

    if core.get("research_only") is not True:
        raise ValueError("CORE must be consumed research evidence")
    if core.get("opens_new_holdout") is not False:
        raise ValueError("CORE cannot open holdout")
    if oco.get("governance", {}).get("consumed_evidence_only") is not True:
        raise ValueError("OCO must be consumed evidence")
    if oco.get("governance", {}).get("opens_new_holdout") is not False:
        raise ValueError("OCO cannot open holdout")

    core_trades = cast(list[dict[str, Any]], core["trades"])
    core_by_date = {str(item["local_date"]): item for item in core_trades}

    secondary_rows = [
        row
        for row in cast(list[dict[str, Any]], oco["oco_rows"])
        if row.get("outcome_status") == "terminal"
    ]
    secondary_by_date = {
        str(item["local_date"]): item for item in secondary_rows
    }

    all_dates = sorted(set(core_by_date) | set(secondary_by_date))
    current_month: str | None = None
    available_secondary_budget = Decimal(0)
    carry = Decimal(0)
    rows: list[dict[str, object]] = []
    budget_ledger: dict[str, dict[str, object]] = defaultdict(dict)

    for local_date in all_dates:
        month = local_date[:7]
        if month != current_month:
            if current_month is not None:
                carry = min(
                    available_secondary_budget,
                    SECONDARY_CARRY_CAP,
                )
            available_secondary_budget = SECONDARY_MONTHLY_BUDGET + carry
            current_month = month
            budget_ledger[month] = {
                "opening_budget_r": format(
                    available_secondary_budget,
                    "f",
                ),
                "base_budget_r": format(SECONDARY_MONTHLY_BUDGET, "f"),
                "carry_in_r": format(carry, "f"),
                "executed_secondary": 0,
                "remaining_budget_r": format(
                    available_secondary_budget,
                    "f",
                ),
            }

        if local_date in core_by_date:
            item = core_by_date[local_date]
            at = str(item["signal_at"])
            gross = Decimal(str(item["r_multiple"]))
            weighted_net = CORE_RISK * (gross - FRICTION)
            rows.append(
                {
                    "local_date": local_date,
                    "timestamp": at,
                    "tier": "CORE",
                    "requested_risk_r": format(CORE_RISK, "f"),
                    "gross_trade_r": format(gross, "f"),
                    "capital_weighted_net_r": format(weighted_net, "f"),
                    "entry_family": item.get("entry_family"),
                }
            )
            continue

        item = secondary_by_date[local_date]
        at = str(item["decision_at"])
        if available_secondary_budget < SECONDARY_RISK:
            continue

        available_secondary_budget -= SECONDARY_RISK
        budget_ledger[month]["executed_secondary"] = (
            int(budget_ledger[month]["executed_secondary"]) + 1
        )
        budget_ledger[month]["remaining_budget_r"] = format(
            available_secondary_budget,
            "f",
        )
        gross = Decimal(str(item["r_multiple"]))
        weighted_net = SECONDARY_RISK * (gross - FRICTION)
        rows.append(
            {
                "local_date": local_date,
                "timestamp": at,
                "tier": "SECONDARY",
                "requested_risk_r": format(SECONDARY_RISK, "f"),
                "gross_trade_r": format(gross, "f"),
                "capital_weighted_net_r": format(weighted_net, "f"),
                "entry_family": item.get("selected_family"),
                "candidate_count": item.get("candidate_count"),
            }
        )

    rows.sort(key=lambda item: cast(str, item["timestamp"]))
    values = [
        Decimal(cast(str, item["capital_weighted_net_r"]))
        for item in rows
    ]
    metrics = _metrics(values)
    mc = _monte_carlo(
        values,
        domain=(
            IDENTITY.encode()
            + b":"
            + str(core["contract_fingerprint"]).encode()
            + b":"
            + str(oco["candidate_contract_fingerprint"]).encode()
        ),
    )
    core_count = sum(item["tier"] == "CORE" for item in rows)
    secondary_count = sum(item["tier"] == "SECONDARY" for item in rows)
    gates = {
        "trade_count_250_to_300": 250 <= len(rows) <= 300,
        "capital_weighted_profit_factor_at_least_2": (
            metrics["profit_factor"] is not None
            and Decimal(cast(str, metrics["profit_factor"])) >= Decimal(2)
        ),
        "capital_weighted_max_drawdown_at_most_10r": (
            Decimal(cast(str, metrics["max_drawdown_r"])) <= Decimal(10)
        ),
        "mc_positive_terminal_probability_at_least_0_90": (
            Decimal(cast(str, mc["positive_terminal_probability"]))
            >= Decimal("0.90")
        ),
        "mc_p95_max_drawdown_at_most_15r": (
            Decimal(cast(str, mc["p95_max_drawdown_r"])) <= Decimal(15)
        ),
    }
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": "NAS100",
        "core_contract_fingerprint": core["contract_fingerprint"],
        "oco_contract_fingerprint": oco["candidate_contract_fingerprint"],
        "capital_policy": {
            "core_requested_risk_r": format(CORE_RISK, "f"),
            "secondary_requested_risk_r": format(SECONDARY_RISK, "f"),
            "secondary_monthly_budget_r": format(
                SECONDARY_MONTHLY_BUDGET,
                "f",
            ),
            "secondary_carry_cap_r": format(SECONDARY_CARRY_CAP, "f"),
            "risk_authorization_remains_external_qore_risk": True,
        },
        "trade_count": len(rows),
        "core_trade_count": core_count,
        "secondary_trade_count": secondary_count,
        "capital_weighted_metrics": metrics,
        "monte_carlo": mc,
        "development_gates": gates,
        "passes_development_gates": all(gates.values()),
        "budget_ledger": dict(sorted(budget_ledger.items())),
        "rows": rows,
        "governance": {
            "consumed_evidence_only": True,
            "core_identity_changed": False,
            "secondary_is_oco_research_route": True,
            "secondary_budget_is_capital_governance": True,
            "raw_trade_count_not_risk_equivalent_count": True,
            "capital_weighted_pf_reported_explicitly": True,
            "opens_new_holdout": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("core_root", type=Path)
    parser.add_argument("oco_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = compose(args.core_root, args.oco_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "trade_count": payload["trade_count"],
                "core_trade_count": payload["core_trade_count"],
                "secondary_trade_count": payload["secondary_trade_count"],
                "capital_weighted_metrics": payload[
                    "capital_weighted_metrics"
                ],
                "monte_carlo": payload["monte_carlo"],
                "development_gates": payload["development_gates"],
                "passes_development_gates": payload[
                    "passes_development_gates"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
