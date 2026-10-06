#!/usr/bin/env python3
# ruff: noqa: I001
"""Postdecision coherence audit for CIBO cognitive/function telemetry.

This tool consumes an already-completed burned/research replay. It never
participates in a decision and never opens a holdout. Its purpose is to prove
whether cognitive and economic function outputs actually reach, agree with,
or bind the final capital path.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EXPECTED_NON_PREDECISION_FACULTIES = frozenset({"CF08", "CF18", "CF19"})
SELECTED_RISK_DECISIONS = frozenset({"ALLOW", "REDUCE"})


def _pairs(value: object) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    if not isinstance(value, (list, tuple)):
        return {}
    result: dict[str, str] = {}
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        result[str(item[0])] = str(item[1])
    return result


def _counter_payload(value: Counter[str]) -> dict[str, int]:
    return dict(sorted(value.items()))


def audit(replay: dict[str, Any]) -> dict[str, Any]:
    decisions = replay.get("decision_receipts")
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("coherence audit requires replay decision receipts")

    cognitive: dict[str, Counter[str]] = defaultdict(Counter)
    functions: dict[str, Counter[str]] = defaultdict(Counter)
    consumer_actions: dict[str, Counter[str]] = defaultdict(Counter)
    blockers: dict[str, Counter[str]] = defaultdict(Counter)
    violations: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for decision in decisions:
        selected = str(decision.get("risk_decision")) in SELECTED_RISK_DECISIONS
        cognitive_rows = decision.get("cognitive_sensors")
        function_rows = decision.get("function_sensors")
        if not isinstance(cognitive_rows, list) or not isinstance(function_rows, list):
            raise ValueError("replay decision is missing sensor surfaces")

        by_function = {
            str(row["function_code"]): row
            for row in function_rows
            if isinstance(row, dict) and row.get("function_code")
        }

        for row in cognitive_rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("component_code"))
            c = cognitive[code]
            c["events"] += 1
            c["applicable"] += int(bool(row.get("applicable")))
            c["native_engine_called"] += int(bool(row.get("native_engine_called")))
            c["downstream_consumed"] += int(bool(row.get("downstream_consumed")))
            c["constraint_or_gate_emitted"] += int(
                bool(row.get("constraint_or_gate_emitted"))
            )
            if "native_output_consumed" in row:
                c["native_output_consumed"] += int(
                    bool(row.get("native_output_consumed"))
                )
            if "semantic_payload_consumed" in row:
                c["semantic_payload_consumed"] += int(
                    bool(row.get("semantic_payload_consumed"))
                )
            if (
                row.get("native_output_consumed")
                and not row.get("native_engine_called")
            ):
                violations["native_output_consumed_without_native_call"] += 1

        for row in function_rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("function_code"))
            c = functions[code]
            c["events"] += 1
            c["called"] += int(bool(row.get("called")))
            c["downstream_consumed"] += int(bool(row.get("downstream_consumed")))
            c["local_change"] += int(bool(row.get("decision_gate_triggered")))
            if "final_capital_binding" in row:
                c["final_capital_binding"] += int(
                    bool(row.get("final_capital_binding"))
                )
                c["local_change_without_final_binding"] += int(
                    bool(row.get("decision_gate_triggered"))
                    and not bool(row.get("final_capital_binding"))
                )
            output = _pairs(row.get("output_metrics"))
            action = output.get("consumer_action")
            if action:
                consumer_actions[code][action] += 1
            raw_blockers = output.get("blocker_codes", "")
            for blocker in filter(None, raw_blockers.split(",")):
                blockers[code][blocker] += 1

        cognition = by_function.get("COGNITION")
        if cognition is not None and bool(cognition.get("decision_gate_triggered")) and selected:
            violations["cognition_block_but_risk_authorized"] += 1

        portfolio = by_function.get("COMPOUND_PORTFOLIO")
        if portfolio is not None:
            multiplier = _pairs(portfolio.get("output_metrics")).get("multiplier")
            if multiplier == "0" and selected:
                violations["portfolio_zero_but_risk_authorized"] += 1

        competition = by_function.get("POSITION_COMPETITION")
        if competition is not None:
            admitted = _pairs(competition.get("output_metrics")).get(
                "admit_opportunity"
            )
            if admitted == "False" and selected:
                violations["competition_reject_but_risk_authorized"] += 1

        genc12 = by_function.get("CAPITAL_SCIENCE:GEN-C12")
        if genc12 is not None:
            action = _pairs(genc12.get("output_metrics")).get("consumer_action")
            if action == "PAUSE_NEW_CAPITAL" and selected:
                violations["genc12_pause_but_risk_authorized"] += 1

        sizing = by_function.get("SIZING")
        source = ""
        if sizing is not None:
            source = _pairs(sizing.get("output_metrics")).get("capital_source", "")
            source_counts[source] += 1

        genc7 = by_function.get("CAPITAL_SCIENCE:GEN-C7")
        if source == "REALIZED_PROFIT" and genc7 is not None:
            output = _pairs(genc7.get("output_metrics"))
            if output.get("consumer_action") == "UNAVAILABLE_MISSING_EVIDENCE":
                violations["realized_profit_request_missing_genc7_evidence"] += 1
            native = output.get("native_engine_called")
            if native == "False":
                violations["realized_profit_request_genc7_not_called"] += 1

    repair_queue: list[dict[str, object]] = []

    def add(priority: str, code: str, count: int, finding: str) -> None:
        if count <= 0:
            return
        repair_queue.append(
            {
                "priority": priority,
                "code": code,
                "event_count": count,
                "finding": finding,
            }
        )

    add(
        "P0",
        "RISK_AFTER_COGNITIVE_BLOCK",
        violations["cognition_block_but_risk_authorized"],
        "Risk authorization exists after a binding cognitive abstention.",
    )
    add(
        "P0",
        "RISK_AFTER_PORTFOLIO_ZERO",
        violations["portfolio_zero_but_risk_authorized"],
        "Risk authorization exists despite a zero Portfolio multiplier.",
    )
    add(
        "P0",
        "RISK_AFTER_COMPETITION_REJECT",
        violations["competition_reject_but_risk_authorized"],
        "Risk authorization exists despite opportunity-competition rejection.",
    )
    add(
        "P0",
        "RISK_AFTER_GENC12_PAUSE",
        violations["genc12_pause_but_risk_authorized"],
        "New capital reached Risk while GEN-C12 requested PAUSE_NEW_CAPITAL.",
    )
    add(
        "P0",
        "REALIZED_PROFIT_GENC7_MISSING",
        violations["realized_profit_request_missing_genc7_evidence"],
        "Realized-profit capital reached the Compound path without GEN-C7 proposal evidence.",
    )
    add(
        "P0",
        "REALIZED_PROFIT_GENC7_NOT_CALLED",
        violations["realized_profit_request_genc7_not_called"],
        "Realized-profit capital was proposed while the native GEN-C7 engine was not called.",
    )
    add(
        "P0",
        "FAKE_NATIVE_CONSUMPTION",
        violations["native_output_consumed_without_native_call"],
        "Telemetry claims native output consumption without a native engine call.",
    )

    for code, counts in sorted(cognitive.items()):
        if code in EXPECTED_NON_PREDECISION_FACULTIES:
            continue
        if counts["applicable"] > 0 and counts["native_engine_called"] == 0:
            repair_queue.append(
                {
                    "priority": "P1",
                    "code": "COGNITIVE_NATIVE_ENGINE_NEVER_CALLED:" + code,
                    "event_count": counts["applicable"],
                    "finding": (
                        "Applicable cognitive component never invoked its native engine."
                    ),
                }
            )

    for code, counts in sorted(functions.items()):
        if (
            counts["events"] > 0
            and counts["local_change"] > 0
            and "final_capital_binding" in counts
            and counts["final_capital_binding"] == 0
        ):
            repair_queue.append(
                {
                    "priority": "P1",
                    "code": "LOCAL_CHANGE_NEVER_BINDS:" + code,
                    "event_count": counts["local_change"],
                    "finding": (
                        "Function changes local state but no observed change reaches "
                        "the final capital plan."
                    ),
                }
            )

    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    repair_queue.sort(
        key=lambda row: (
            priority_order[str(row["priority"])],
            -int(row["event_count"]),
            str(row["code"]),
        )
    )

    return {
        "schema": "qore.cibo.cognitive-function-coherence-audit.v1",
        "source_replay_schema": replay.get("schema"),
        "decision_count": len(decisions),
        "cognitive_component_count": len(cognitive),
        "function_count": len(functions),
        "capital_source_counts": _counter_payload(source_counts),
        "coherence_violations": _counter_payload(violations),
        "cognitive_components": {
            code: _counter_payload(counts)
            for code, counts in sorted(cognitive.items())
        },
        "functions": {
            code: {
                **_counter_payload(counts),
                "consumer_actions": _counter_payload(
                    consumer_actions.get(code, Counter())
                ),
                "blocker_codes": _counter_payload(
                    blockers.get(code, Counter())
                ),
            }
            for code, counts in sorted(functions.items())
        },
        "expected_non_predecision_faculties": sorted(
            EXPECTED_NON_PREDECISION_FACULTIES
        ),
        "repair_queue": repair_queue,
        "p0_count": sum(row["priority"] == "P0" for row in repair_queue),
        "p1_count": sum(row["priority"] == "P1" for row in repair_queue),
        "governance": {
            "postdecision_diagnostic_only": True,
            "decision_inputs_mutated": False,
            "holdout_opened": False,
            "outcome_aware_tuning": False,
            "certification_claimed": False,
            "productive_authority": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    report = audit(replay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision_count": report["decision_count"],
                "cognitive_component_count": report[
                    "cognitive_component_count"
                ],
                "function_count": report["function_count"],
                "p0_count": report["p0_count"],
                "p1_count": report["p1_count"],
                "repair_queue": report["repair_queue"][:10],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
