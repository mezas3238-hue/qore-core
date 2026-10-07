"""Aggregate VT31 cognitive sensor diagnostics from prepared causal ledgers.

Read-only consumed-evidence attribution. No trading authority.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

SCHEMA = "qore.vt31.nas100.cognitive_sensor_audit.v1"
PREPARED_SCHEMA = "qore.vt31.nas100.comp009.causal_trace_prepared.v1"


def _parse_fold(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("fold must be NAME=PATH")
    name, raw = value.split("=", 1)
    return name, Path(raw)


def _sorted(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def audit(paths: dict[str, Path]) -> dict[str, object]:
    missing: Counter[str] = Counter()
    unresolved: Counter[str] = Counter()
    blockers: Counter[str] = Counter()
    reasoning: Counter[str] = Counter()
    outputs: Counter[str] = Counter()
    output_reasons: Counter[str] = Counter()
    routing: Counter[str] = Counter()
    output_to_routing: Counter[str] = Counter()
    observation_only: Counter[str] = Counter()

    fold_calls: dict[str, int] = {}
    calls_per_trade: list[int] = []
    trades = 0
    full_accounting_calls = 0
    maximum_cognition_calls = 0
    missing_sensor_calls = 0
    zero_call_trades = 0

    for fold, path in sorted(paths.items()):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != PREPARED_SCHEMA:
            raise ValueError(f"{fold}: unexpected prepared schema")

        rows = cast(list[dict[str, object]], payload["control_rows"])
        fold_count = 0
        for row in rows:
            trades += 1
            events = cast(
                list[dict[str, object]],
                row.get("cognitive_exit_evaluations", []),
            )
            calls_per_trade.append(len(events))
            fold_count += len(events)
            if not events:
                zero_call_trades += 1

            for event in events:
                sensor = cast(
                    dict[str, object],
                    event.get("cognitive_sensor", {}),
                )
                if not sensor:
                    missing_sensor_calls += 1
                    continue

                missing.update(
                    cast(list[str], sensor.get("missing_inputs", []))
                )
                unresolved.update(
                    cast(list[str], sensor.get("unresolved_inputs", []))
                )
                blockers.update(
                    cast(
                        list[str],
                        sensor.get("maximum_intelligence_blockers", []),
                    )
                )
                observation_only.update(
                    cast(
                        list[str],
                        sensor.get(
                            "observation_only_situation_fields",
                            [],
                        ),
                    )
                )
                reasoning[str(sensor["current_reasoning_action"])] += 1
                action = str(sensor["output_action"])
                outputs[action] += 1
                output_reasons[str(sensor["output_reason"])] += 1
                if sensor.get("full_cognitive_accounting_verified") is True:
                    full_accounting_calls += 1
                if sensor.get("maximum_cognition_verified") is True:
                    maximum_cognition_calls += 1

                route = cast(
                    dict[str, object],
                    event.get("actuation_sensor", {}),
                )
                if route:
                    status = str(route["status"])
                    routing[status] += 1
                    output_to_routing[f"{action}->{status}"] += 1

        fold_calls[fold] = fold_count

    total_calls = sum(fold_calls.values())
    avg = (
        Decimal(total_calls) / Decimal(trades)
        if trades
        else Decimal(0)
    )

    return {
        "schema": SCHEMA,
        "folds": sorted(paths),
        "trade_count": trades,
        "cognitive_call_count": total_calls,
        "cognitive_calls_by_fold": fold_calls,
        "average_cognitive_calls_per_trade": format(avg, "f"),
        "minimum_calls_per_trade": min(calls_per_trade, default=0),
        "maximum_calls_per_trade": max(calls_per_trade, default=0),
        "zero_call_trade_count": zero_call_trades,
        "input_sensor": {
            "missing_field_counts": _sorted(missing),
            "unresolved_field_counts": _sorted(unresolved),
        },
        "cognition_sensor": {
            "full_accounting_verified_calls": full_accounting_calls,
            "maximum_cognition_verified_calls": maximum_cognition_calls,
            "maximum_intelligence_blocker_counts": _sorted(blockers),
            "observation_only_field_counts": _sorted(observation_only),
        },
        "reasoning_sensor": {
            "current_action_counts": _sorted(reasoning),
        },
        "output_sensor": {
            "position_action_counts": _sorted(outputs),
            "position_reason_counts": _sorted(output_reasons),
        },
        "actuation_sensor": {
            "status_counts": _sorted(routing),
            "output_to_status_counts": _sorted(output_to_routing),
        },
        "sensor_integrity": {
            "missing_sensor_call_count": missing_sensor_calls,
            "required_action_unobserved_count": routing[
                "ROUTED_EXECUTION_UNOBSERVED"
            ],
            "required_action_not_executed_count": routing[
                "ROUTED_NOT_EXECUTED"
            ],
            "required_action_not_routed_count": routing[
                "OUTPUT_NOT_ROUTED"
            ],
        },
        "governance": {
            "read_only": True,
            "consumed_evidence_only": True,
            "policy_authority": False,
            "terminal_outcome_runtime_authority": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", action="append", type=_parse_fold, required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    paths = dict(args.fold)
    if len(paths) != len(args.fold):
        raise SystemExit("duplicate fold name")

    payload = audit(paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
