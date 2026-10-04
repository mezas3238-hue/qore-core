#!/usr/bin/env python3
"""Build a high-resolution CIBO function-utilization dossier.

This sensor is diagnostic-only. It separates runtime health, eligibility,
consumption, decision actuation, and economic actuation so that a healthy
advisory/no-change path is not confused with a broken or unobservable path.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

EXPECTED_FUNCTIONS = 53
REPAIR_SEVERITY = {
    "UNOBSERVABLE": 0,
    "BLOCKED": 1,
    "DEGRADED": 2,
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"non-decimal numeric value: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"non-finite numeric value: {value!r}")
    return result


def _top_reason(row: dict[str, Any]) -> str | None:
    for field in (
        "reason_distribution",
        "native_engine_status_distribution",
        "dispositions",
    ):
        raw = row.get(field)
        if not isinstance(raw, dict) or not raw:
            continue
        ordered = sorted(
            ((str(key), int(value)) for key, value in raw.items()),
            key=lambda item: (-item[1], item[0]),
        )
        key, count = ordered[0]
        return f"{field}:{key} ({count})"
    diagnosis = row.get("diagnosis")
    return str(diagnosis) if diagnosis else None


def _classify(row: dict[str, Any]) -> tuple[str, bool, str]:
    diagnosis = str(row.get("diagnosis", "UNKNOWN"))
    stage = str(row.get("stage", "UNKNOWN"))

    if diagnosis in {
        "INPUT_OUTPUT_CONSUMER_ACTUATION_OBSERVED",
        "OUTPUT_AND_ECONOMIC_EFFECT_OBSERVED",
    }:
        return "ACTUATING", False, "verified consumed output with observable actuation"
    if diagnosis in {
        "JUSTIFIED_NOT_APPLICABLE",
        "JUSTIFIED_NOT_APPLICABLE_PREDECISION",
    }:
        return "JUSTIFIED_NOT_APPLICABLE", False, (
            "predecision context did not require this capability"
        )
    if diagnosis == "NATIVE_ENGINE_SUCCESS_CONSUMED_NO_ECONOMIC_ACTUATION":
        return (
            "ADVISORY_USED",
            False,
            "native cognitive output was consumed inside its advisory authority boundary",
        )
    if diagnosis == "INPUT_OUTPUT_CONSUMER_OBSERVED_NO_CHANGE":
        return (
            "USED_NO_CHANGE",
            False,
            "runtime input/output and consumer were observed; this call legitimately made no change",
        )

    if diagnosis in {
        "OBSERVABILITY_GAP",
        "NATIVE_ENGINE_TELEMETRY_GAP",
        "AGGREGATE_ONLY_PER_CALL_IO_MISSING",
        "NO_PER_CALL_RUNTIME_RECEIPTS",
        "INPUT_OUTPUT_INCOMPLETE",
        "CONSUMER_BINDING_INCOMPLETE",
    }:
        return "UNOBSERVABLE", True, (
            "per-call evidence is insufficient to prove runtime use"
        )

    if diagnosis in {
        "NATIVE_ENGINE_FAIL_CLOSED",
        "NATIVE_ENGINE_DEPENDENCY_BLOCKED",
        "ALL_CALLS_FAIL_CLOSED",
        "FAIL_CLOSED_OR_UNAVAILABLE",
    }:
        return "BLOCKED", True, (
            "runtime is fail-closed, dependency-blocked, or unavailable"
        )

    if diagnosis in {
        "APPLIED_WITHOUT_OBSERVABLE_ACTUATION",
        "OUTPUT_OBSERVED_NO_ECONOMIC_EFFECT",
        "MIXED_NATIVE_ENGINE_RUNTIME_STATUS",
    }:
        return "DEGRADED", True, (
            "runtime exists but full downstream actuation is not proven"
        )

    return "UNOBSERVABLE", True, (
        f"unclassified {stage} diagnosis: {diagnosis}"
    )


def _row_probe(row: dict[str, Any]) -> dict[str, Any]:
    state, repair_required, explanation = _classify(row)
    stage = str(row.get("stage", "UNKNOWN"))
    diagnosis = str(row.get("diagnosis", "UNKNOWN"))

    if stage == "COGNITIVE":
        invocation_count = int(row.get("call_count") or 0)
        expected_count = int(row.get("expected_trace_rows") or 0)
        input_observed = bool(row.get("per_function_input_observable"))
        output_observed = bool(row.get("per_function_output_observable"))
        consumer_observed = bool(row.get("downstream_consumer_observable"))
        decision_changed = bool(row.get("decision_change_observable"))
        economic_effect = bool(row.get("economic_effect_observable"))
        native_called_count = sum(
            int(value)
            for key, value in dict(
                row.get("native_engine_status_distribution") or {}
            ).items()
            if str(key) != "JUSTIFIED_NOT_APPLICABLE"
        )
    elif stage == "CE2I":
        invocation_count = max(
            int(row.get("runtime_receipt_count") or 0),
            int(row.get("advanced_call_count") or 0),
            int(row.get("applied_count") or 0),
        )
        expected_count = int(row.get("enabled_epochs") or 0)
        input_observed = bool(row.get("per_call_input_observable"))
        output_observed = bool(row.get("per_call_output_observable"))
        consumer_observed = bool(row.get("downstream_consumer_observable"))
        decision_changed = bool(row.get("decision_change_observable"))
        economic_effect = bool(row.get("economic_effect_observable"))
        native_called_count = int(row.get("runtime_receipt_count") or 0)
    else:
        invocation_count = int(row.get("call_count") or 0)
        expected_count = invocation_count
        input_observed = bool(row.get("input_output_complete"))
        output_observed = bool(row.get("input_output_complete"))
        consumer_observed = int(row.get("consumer_bound_count") or 0) > 0
        decision_changed = int(row.get("decision_changed_count") or 0) > 0
        economic_effect = int(row.get("economic_delta_field_count") or 0) > 0
        native_called_count = int(row.get("native_engine_called_count") or 0)

    return {
        "function_code": str(row.get("function_code")),
        "stage": stage,
        "utilization_state": state,
        "repair_required": repair_required,
        "diagnosis": diagnosis,
        "primary_reason": _top_reason(row),
        "explanation": explanation,
        "invocation_count": invocation_count,
        "expected_or_enabled_count": expected_count,
        "native_called_count": native_called_count,
        "input_observed": input_observed,
        "output_observed": output_observed,
        "consumer_observed": consumer_observed,
        "decision_change_observed": decision_changed,
        "economic_effect_observed": economic_effect,
    }


def _stage_summary(probes: list[dict[str, Any]]) -> dict[str, Any]:
    by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for probe in probes:
        by_stage[str(probe["stage"])].append(probe)
    result: dict[str, Any] = {}
    for stage, rows in sorted(by_stage.items()):
        states = Counter(str(row["utilization_state"]) for row in rows)
        result[stage] = {
            "function_count": len(rows),
            "repair_required_count": sum(
                bool(row["repair_required"]) for row in rows
            ),
            "states": dict(sorted(states.items())),
            "invocation_count": sum(
                int(row["invocation_count"]) for row in rows
            ),
            "native_called_count": sum(
                int(row["native_called_count"]) for row in rows
            ),
        }
    return result


def _economic_probe(
    group: dict[str, Any],
    probes: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates = group.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("group-result candidates missing")

    by_multiplier: dict[str, Any] = {}
    best: tuple[Decimal, str] | None = None
    dynamic_present = False
    dynamic_activity = False
    compound_activity = False
    portfolio_activity = False
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        config = candidate.get("configuration")
        measurements = candidate.get("measurements")
        if not isinstance(config, dict) or not isinstance(measurements, dict):
            continue
        multiplier = str(config.get("compound_seed_multiplier"))
        compound = measurements.get("compound") or {}
        portfolio = measurements.get("compound_portfolio") or {}
        ending = _decimal(
            measurements.get("final_ending_capital_usd", "0")
        )
        compound_settled = int(compound.get("settled_count") or 0)
        portfolio_settled = int(portfolio.get("settled_count") or 0)
        compound_activity = compound_activity or compound_settled > 0
        portfolio_activity = portfolio_activity or portfolio_settled > 0
        if multiplier == "DYNAMIC":
            dynamic_present = True
            dynamic_activity = (
                compound_settled > 0 or portfolio_settled > 0
            )
        by_multiplier[multiplier] = {
            "final_ending_capital_usd": format(ending, "f"),
            "compound_incremental_pnl_usd": str(
                compound.get("incremental_pnl_usd")
            ),
            "compound_settled_count": compound_settled,
            "compound_portfolio_incremental_pnl_usd": str(
                portfolio.get("incremental_pnl_usd")
            ),
            "compound_portfolio_settled_count": portfolio_settled,
            "compound_portfolio_value_add_usd": str(
                portfolio.get("value_add_vs_compound_usd")
            ),
            "dynamic_leverage": bool(config.get("dynamic_leverage")),
        }
        if best is None or ending > best[0]:
            best = (ending, multiplier)

    by_code = {str(row["function_code"]): row for row in probes}
    t02 = by_code.get("T02")
    return {
        "shared_initial_capital_usd": str(
            group.get("shared_initial_capital_usd")
        ),
        "sizing_authority": {
            "t02_present": t02 is not None,
            "t02_utilization_state": (
                None if t02 is None else t02["utilization_state"]
            ),
            "t02_repair_required": (
                None if t02 is None else t02["repair_required"]
            ),
            "qore_risk_sovereign": all(
                bool(
                    (candidate.get("measurements") or {}).get(
                        "qore_risk_sovereign"
                    )
                )
                for candidate in candidates
                if isinstance(candidate, dict)
            ),
        },
        "compound_activity_observed": compound_activity,
        "compound_portfolio_activity_observed": portfolio_activity,
        "dynamic_leverage_candidate_present": dynamic_present,
        "dynamic_leverage_activity_observed": dynamic_activity,
        "best_observed_multiplier": None if best is None else best[1],
        "best_observed_ending_capital_usd": (
            None if best is None else format(best[0], "f")
        ),
        "by_multiplier": by_multiplier,
        "note": (
            "Economic activity proves use, not scientific adequacy. "
            "Profitability and robustness remain separate gates."
        ),
    }


def build(
    function_io: dict[str, Any],
    group: dict[str, Any],
) -> dict[str, Any]:
    functions = function_io.get("functions")
    if not isinstance(functions, list):
        raise ValueError("function-io functions missing")
    probes = [
        _row_probe(row)
        for row in functions
        if isinstance(row, dict)
    ]
    if len(probes) != EXPECTED_FUNCTIONS:
        raise ValueError(
            f"expected {EXPECTED_FUNCTIONS} CIBO functions, "
            f"observed {len(probes)}"
        )

    states = Counter(
        str(row["utilization_state"]) for row in probes
    )
    repair = [
        row for row in probes if bool(row["repair_required"])
    ]
    repair.sort(
        key=lambda row: (
            REPAIR_SEVERITY.get(
                str(row["utilization_state"]), 9
            ),
            str(row["stage"]),
            str(row["function_code"]),
        )
    )
    accounted = sum(
        state
        in {
            "ACTUATING",
            "ADVISORY_USED",
            "USED_NO_CHANGE",
            "JUSTIFIED_NOT_APPLICABLE",
        }
        for state in (
            str(row["utilization_state"]) for row in probes
        )
    )
    summary = {
        "function_count": len(probes),
        "verified_accounted_for_count": accounted,
        "verified_accounted_for_pct": round(
            accounted * 100.0 / len(probes), 2
        ),
        "repair_required_count": len(repair),
        "states": dict(sorted(states.items())),
        "stage_summary": _stage_summary(probes),
        "full_functionality_observability": not repair,
    }
    return {
        "schema": "qore.cibo.function-utilization-sensor.v1",
        "group_id": group.get("group_id"),
        "summary": summary,
        "functions": probes,
        "repair_queue": [
            {
                "function_code": row["function_code"],
                "stage": row["stage"],
                "utilization_state": row["utilization_state"],
                "diagnosis": row["diagnosis"],
                "primary_reason": row["primary_reason"],
                "explanation": row["explanation"],
            }
            for row in repair
        ],
        "economic_capability_probe": _economic_probe(group, probes),
        "interpretation_contract": {
            "ACTUATING": "used and downstream actuation observed",
            "ADVISORY_USED": (
                "used inside an advisory-only authority boundary"
            ),
            "USED_NO_CHANGE": (
                "used correctly; current context required no change"
            ),
            "JUSTIFIED_NOT_APPLICABLE": (
                "not used because predecision eligibility was absent"
            ),
            "DEGRADED": (
                "runtime present but expected downstream effect is not proven"
            ),
            "BLOCKED": (
                "runtime attempted but fail-closed, unavailable, "
                "or dependency-blocked"
            ),
            "UNOBSERVABLE": (
                "insufficient per-call evidence to prove use"
            ),
        },
        "governance": {
            "diagnostic_only": True,
            "outcome_aware_tuning": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--function-io", type=Path, required=True)
    parser.add_argument("--group-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build(
        _load(args.function_io),
        _load(args.group_result),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "group_id": payload["group_id"],
                "verified_accounted_for_pct": payload[
                    "summary"
                ]["verified_accounted_for_pct"],
                "repair_required_count": payload[
                    "summary"
                ]["repair_required_count"],
                "states": payload["summary"]["states"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
