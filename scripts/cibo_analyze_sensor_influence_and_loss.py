#!/usr/bin/env python3
"""Analyze CIBO decision influence and observed loss concentration.

This is a diagnostic attribution layer, not causal proof. It joins each settled
outcome to the exact sovereign decision and its read-only sensor receipts.

A component becomes a causal contributor/drag only after an isolated frozen
ablation. Until then this report identifies influence gates and economic
concentration to prioritize those ablations.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


def _decimal(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite monetary value")
    return result


def _sum(values: list[Decimal]) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return sum(values, Decimal(0))


def _money(value: Decimal) -> str:
    return format(value, "f")


def _bucket_row() -> dict[str, Any]:
    return {
        "settlement_count": 0,
        "winner_count": 0,
        "loser_count": 0,
        "net_pnl_usd": Decimal(0),
        "gross_profit_usd": Decimal(0),
        "gross_loss_usd": Decimal(0),
    }


def _add_outcome(bucket: dict[str, Any], pnl: Decimal) -> None:
    bucket["settlement_count"] += 1
    bucket["net_pnl_usd"] += pnl
    if pnl > 0:
        bucket["winner_count"] += 1
        bucket["gross_profit_usd"] += pnl
    elif pnl < 0:
        bucket["loser_count"] += 1
        bucket["gross_loss_usd"] += -pnl


def _finalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    settlements = int(bucket["settlement_count"])
    losers = int(bucket["loser_count"])
    return {
        "settlement_count": settlements,
        "winner_count": int(bucket["winner_count"]),
        "loser_count": losers,
        "loss_rate": (
            "0"
            if settlements == 0
            else format(Decimal(losers) / Decimal(settlements), "f")
        ),
        "net_pnl_usd": _money(bucket["net_pnl_usd"]),
        "gross_profit_usd": _money(bucket["gross_profit_usd"]),
        "gross_loss_usd": _money(bucket["gross_loss_usd"]),
    }


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    decisions = payload.get("decision_receipts")
    settlements = payload.get("settlement_receipts")
    if not isinstance(decisions, list) or not isinstance(settlements, list):
        raise ValueError("replay decision/settlement receipts missing")

    by_signal = {
        str(item["signal_fingerprint"]): item
        for item in decisions
    }
    if len(by_signal) != len(decisions):
        raise ValueError("duplicate decision signal")

    trader: dict[str, dict[str, Any]] = defaultdict(_bucket_row)
    leverage: dict[str, dict[str, Any]] = defaultdict(_bucket_row)
    sizing: dict[str, dict[str, Any]] = defaultdict(_bucket_row)
    risk: dict[str, dict[str, Any]] = defaultdict(_bucket_row)
    disposition: dict[str, dict[str, Any]] = defaultdict(_bucket_row)
    cognitive_gate: dict[str, dict[str, Any]] = defaultdict(_bucket_row)
    function_gate: dict[str, dict[str, Any]] = defaultdict(_bucket_row)
    cognitive_component: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "event_count": 0,
            "gate_count": 0,
            "settled_gate_count": 0,
            "gate_net_pnl_usd": Decimal(0),
            "gate_gross_loss_usd": Decimal(0),
            "gate_gross_profit_usd": Decimal(0),
            "gate_loser_count": 0,
            "gate_winner_count": 0,
            "reached_capital_count": 0,
            "individual_contribution_state": "UNPROVEN",
        }
    )
    function_component: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "event_count": 0,
            "gate_count": 0,
            "settled_gate_count": 0,
            "gate_net_pnl_usd": Decimal(0),
            "gate_gross_loss_usd": Decimal(0),
            "gate_gross_profit_usd": Decimal(0),
            "gate_loser_count": 0,
            "gate_winner_count": 0,
        }
    )

    for decision in decisions:
        for sensor in decision.get("cognitive_sensors", []):
            code = str(sensor["component_code"])
            row = cognitive_component[code]
            row["event_count"] += 1
            if sensor.get("constraint_or_gate_emitted") is True:
                row["gate_count"] += 1
            if sensor.get("reached_capital_decision") is True:
                row["reached_capital_count"] += 1
        for sensor in decision.get("function_sensors", []):
            code = str(sensor["function_code"])
            row = function_component[code]
            row["event_count"] += 1
            if sensor.get("decision_gate_triggered") is True:
                row["gate_count"] += 1

    biggest_losses: list[dict[str, Any]] = []
    settled_pnls: list[Decimal] = []

    for settlement in settlements:
        signal = str(settlement["signal_fingerprint"])
        decision = by_signal.get(signal)
        if decision is None:
            raise ValueError("settlement lacks matching decision")
        pnl = _decimal(settlement["realized_net_pnl_usd"])
        settled_pnls.append(pnl)

        _add_outcome(trader[str(decision["trader_id"])], pnl)
        _add_outcome(
            leverage[str(decision["adaptive_leverage_multiplier"])],
            pnl,
        )
        _add_outcome(sizing[str(decision["sizing_mode"])], pnl)
        _add_outcome(risk[str(decision["risk_decision"])], pnl)
        _add_outcome(
            disposition[str(decision["capital_disposition"])],
            pnl,
        )

        cognitive_gates = tuple(
            str(sensor["component_code"])
            for sensor in decision.get("cognitive_sensors", [])
            if sensor.get("constraint_or_gate_emitted") is True
        )
        function_gates = tuple(
            str(sensor["function_code"])
            for sensor in decision.get("function_sensors", [])
            if sensor.get("decision_gate_triggered") is True
        )

        for code in cognitive_gates:
            _add_outcome(cognitive_gate[code], pnl)
            row = cognitive_component[code]
            row["settled_gate_count"] += 1
            row["gate_net_pnl_usd"] += pnl
            if pnl < 0:
                row["gate_loser_count"] += 1
                row["gate_gross_loss_usd"] += -pnl
            elif pnl > 0:
                row["gate_winner_count"] += 1
                row["gate_gross_profit_usd"] += pnl

        for code in function_gates:
            _add_outcome(function_gate[code], pnl)
            row = function_component[code]
            row["settled_gate_count"] += 1
            row["gate_net_pnl_usd"] += pnl
            if pnl < 0:
                row["gate_loser_count"] += 1
                row["gate_gross_loss_usd"] += -pnl
            elif pnl > 0:
                row["gate_winner_count"] += 1
                row["gate_gross_profit_usd"] += pnl

        if pnl < 0:
            biggest_losses.append(
                {
                    "signal_fingerprint": signal,
                    "trader_id": decision["trader_id"],
                    "decision_epoch_id": decision["decision_epoch_id"],
                    "realized_net_pnl_usd": _money(pnl),
                    "loss_usd": _money(-pnl),
                    "adaptive_leverage_multiplier": (
                        decision["adaptive_leverage_multiplier"]
                    ),
                    "sizing_mode": decision["sizing_mode"],
                    "risk_decision": decision["risk_decision"],
                    "capital_disposition": decision[
                        "capital_disposition"
                    ],
                    "cognitive_gates": list(cognitive_gates),
                    "function_gates": list(function_gates),
                }
            )

    biggest_losses.sort(
        key=lambda item: _decimal(item["loss_usd"]),
        reverse=True,
    )

    cognitive_summary: dict[str, Any] = {}
    for code, row in cognitive_component.items():
        gate_settled = int(row["settled_gate_count"])
        cognitive_summary[code] = {
            "event_count": int(row["event_count"]),
            "gate_count": int(row["gate_count"]),
            "reached_capital_count": int(row["reached_capital_count"]),
            "settled_gate_count": gate_settled,
            "gate_winner_count": int(row["gate_winner_count"]),
            "gate_loser_count": int(row["gate_loser_count"]),
            "gate_net_pnl_usd": _money(row["gate_net_pnl_usd"]),
            "gate_gross_profit_usd": _money(
                row["gate_gross_profit_usd"]
            ),
            "gate_gross_loss_usd": _money(row["gate_gross_loss_usd"]),
            "gate_average_pnl_usd": (
                None
                if gate_settled == 0
                else _money(
                    row["gate_net_pnl_usd"] / Decimal(gate_settled)
                )
            ),
            "observed_decision_influence": (
                "GATE_OBSERVED"
                if row["gate_count"] > 0
                else "REACH_ONLY_ABLATION_REQUIRED"
            ),
            "causal_economic_contribution": "UNPROVEN",
        }

    function_summary: dict[str, Any] = {}
    for code, row in function_component.items():
        gate_settled = int(row["settled_gate_count"])
        function_summary[code] = {
            "event_count": int(row["event_count"]),
            "gate_count": int(row["gate_count"]),
            "settled_gate_count": gate_settled,
            "gate_winner_count": int(row["gate_winner_count"]),
            "gate_loser_count": int(row["gate_loser_count"]),
            "gate_net_pnl_usd": _money(row["gate_net_pnl_usd"]),
            "gate_gross_profit_usd": _money(
                row["gate_gross_profit_usd"]
            ),
            "gate_gross_loss_usd": _money(row["gate_gross_loss_usd"]),
            "gate_average_pnl_usd": (
                None
                if gate_settled == 0
                else _money(
                    row["gate_net_pnl_usd"] / Decimal(gate_settled)
                )
            ),
            "observed_decision_influence": (
                "GATE_OBSERVED"
                if row["gate_count"] > 0
                else "REACH_ONLY_ABLATION_REQUIRED"
            ),
            "causal_economic_contribution": "UNPROVEN",
        }

    gate_loss_candidates = sorted(
        (
            {
                "plane": "COGNITIVE",
                "component_code": code,
                "gate_count": row["gate_count"],
                "gate_loser_count": row["gate_loser_count"],
                "gate_gross_loss_usd": _money(
                    row["gate_gross_loss_usd"]
                ),
                "gate_net_pnl_usd": _money(row["gate_net_pnl_usd"]),
                "causal_status": "UNPROVEN_NEEDS_ISOLATED_ABLATION",
            }
            for code, row in cognitive_component.items()
            if row["gate_count"] > 0
        ),
        key=lambda item: _decimal(item["gate_gross_loss_usd"]),
        reverse=True,
    )
    gate_loss_candidates += sorted(
        (
            {
                "plane": "ECONOMIC",
                "component_code": code,
                "gate_count": row["gate_count"],
                "gate_loser_count": row["gate_loser_count"],
                "gate_gross_loss_usd": _money(
                    row["gate_gross_loss_usd"]
                ),
                "gate_net_pnl_usd": _money(row["gate_net_pnl_usd"]),
                "causal_status": "UNPROVEN_NEEDS_ISOLATED_ABLATION",
            }
            for code, row in function_component.items()
            if row["gate_count"] > 0
        ),
        key=lambda item: _decimal(item["gate_gross_loss_usd"]),
        reverse=True,
    )
    gate_loss_candidates.sort(
        key=lambda item: _decimal(item["gate_gross_loss_usd"]),
        reverse=True,
    )

    total_net = _sum(settled_pnls)
    total_gross_loss = _sum([-p for p in settled_pnls if p < 0])
    total_gross_profit = _sum([p for p in settled_pnls if p > 0])

    return {
        "schema": "qore.cibo.sensor-influence-loss-analysis.v1",
        "decision_count": len(decisions),
        "settlement_count": len(settlements),
        "economy": {
            "net_pnl_usd": _money(total_net),
            "gross_profit_usd": _money(total_gross_profit),
            "gross_loss_usd": _money(total_gross_loss),
            "winner_count": sum(p > 0 for p in settled_pnls),
            "loser_count": sum(p < 0 for p in settled_pnls),
        },
        "loss_concentration": {
            "by_trader": {
                key: _finalize_bucket(value)
                for key, value in sorted(trader.items())
            },
            "by_adaptive_leverage_multiplier": {
                key: _finalize_bucket(value)
                for key, value in sorted(leverage.items())
            },
            "by_sizing_mode": {
                key: _finalize_bucket(value)
                for key, value in sorted(sizing.items())
            },
            "by_risk_decision": {
                key: _finalize_bucket(value)
                for key, value in sorted(risk.items())
            },
            "by_capital_disposition": {
                key: _finalize_bucket(value)
                for key, value in sorted(disposition.items())
            },
        },
        "cognitive_components": cognitive_summary,
        "economic_components": function_summary,
        "gate_loss_ablation_priority": gate_loss_candidates,
        "largest_individual_losses": biggest_losses[:50],
        "interpretation_contract": {
            "reach_is_not_decision_influence": True,
            "gate_is_observed_influence_not_causal_pnl_proof": True,
            "causal_contribution_requires_frozen_isolated_ablation": True,
            "loss_cooccurrence_is_not_causation": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.replay.read_text(encoding="utf-8"))
    result = analyze(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "net_pnl_usd": result["economy"]["net_pnl_usd"],
                "gross_loss_usd": result["economy"]["gross_loss_usd"],
                "gate_loss_candidate_count": len(
                    result["gate_loss_ablation_priority"]
                ),
                "largest_loss_count": len(
                    result["largest_individual_losses"]
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
