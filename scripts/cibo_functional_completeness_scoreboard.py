#!/usr/bin/env python3
"""Build the canonical CIBO functional-completeness scoreboard.

The scoreboard is diagnostic-only. It reconciles function-specific authority
semantics so advisory/protective/no-change paths are not falsely treated as
economic failures, while preserving real runtime/causal blockers.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

FUNCTIONAL_CLASSES = {
    "PRODUCTIVE_UNIQUE",
    "PRODUCTIVE_COOPERATIVE",
    "PROTECTIVE_UNIQUE",
    "INFORMATIONAL_USEFUL",
    "REDUNDANT",
    "NO_MEASURABLE_EFFECT",
    "DESTRUCTIVE",
    "DEPENDENCY_BLOCKED",
    "INSTRUMENTATION_INCOMPLETE",
    "NOT_APPLICABLE",
    "UNPROVEN",
}

REPAIR_TO_CLASS = {
    "UNOBSERVABLE": "INSTRUMENTATION_INCOMPLETE",
    "SHADOW_ONLY": "INSTRUMENTATION_INCOMPLETE",
    "AUTHORITY_LOCKED": "DEPENDENCY_BLOCKED",
    "SCIENCE_LOCKED": "DEPENDENCY_BLOCKED",
    "BLOCKED": "DEPENDENCY_BLOCKED",
    "DEGRADED": "UNPROVEN",
}

SYSTEM_COMPONENTS = (
    "CMA",
    "QORE_RISK_BRIDGE",
    "EXECUTION_BRIDGE",
    "SETTLEMENT",
    "RELEASE",
    "ACCOUNTING",
    "PROVIDER_INTERACTION",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _classify(probe: dict[str, Any]) -> str:
    state = str(probe["utilization_state"])
    stage = str(probe["stage"])
    code = str(probe["function_code"])
    if state in REPAIR_TO_CLASS:
        return REPAIR_TO_CLASS[state]
    if state == "JUSTIFIED_NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if state == "SAFETY_LOCKED":
        return "PROTECTIVE_UNIQUE"
    if state == "ADVISORY_USED":
        return "INFORMATIONAL_USEFUL"
    if state == "USED_NO_CHANGE":
        # T13/T15 are intended to alter reserve/optionality economics when
        # applicable. Wiring-only no-change is not sufficient to prove their
        # protective function; Architect-1 owns their economic closure.
        if stage == "CE2I" and code in {"T13", "T15"}:
            return "UNPROVEN"
        return "INFORMATIONAL_USEFUL"
    if state == "ACTUATING":
        return "PRODUCTIVE_COOPERATIVE"
    raise ValueError(f"unmapped utilization state: {stage}:{state}")


def _authority(probe: dict[str, Any]) -> str:
    stage = str(probe["stage"])
    state = str(probe["utilization_state"])
    if stage == "COGNITIVE":
        return "OBSERVATION_ADVISORY__NO_SIZING_RISK_EXECUTION_AUTHORITY"
    if stage == "CE2I":
        if state == "ACTUATING":
            return "CE2I_TOOL_RUNTIME__BOUND_BY_CMA_AND_QORE_RISK"
        return "CE2I_CONTEXTUAL_OR_PROTECTIVE__NO_INFERRED_AUTHORITY"
    return "CAPITAL_SCIENCE_RUNTIME_ROLE__AUTHORITY_RECONCILE_WITH_ARCHITECT1"


def _engine_summary(row: dict[str, Any], probe: dict[str, Any]) -> object:
    if row.get("native_engine_distribution"):
        return sorted(str(k) for k in row["native_engine_distribution"])
    count = int(probe.get("native_called_count") or 0)
    return {"native_called_count": count}


def _runtime_signature(row: dict[str, Any]) -> tuple[object, ...]:
    stage = str(row["stage"])
    if stage == "COGNITIVE":
        return (
            stage,
            tuple(sorted(str(k) for k in row.get("native_engine_distribution", {}))),
            tuple(sorted(str(k) for k in row.get("function_output_distribution", {}))),
        )
    if stage == "CE2I":
        return (
            stage,
            str(row.get("coverage_reason")),
            str(row.get("coverage_status")),
            tuple(sorted(str(k) for k in row.get("dispositions", {}))),
        )
    return (
        stage,
        tuple(sorted(str(k) for k in row.get("consumer_action_distribution", {}))),
        tuple(sorted(str(k) for k in row.get("stage_distribution", {}))),
    )


def _function_row(
    row: dict[str, Any],
    probe: dict[str, Any],
    *,
    outcome_used: bool,
    duplicate: str,
) -> dict[str, Any]:
    code = str(row["function_code"])
    stage = str(row["stage"])
    classification = _classify(probe)
    protective_candidate = code in {"T13", "T14", "T15"}
    protective_observed = bool(
        protective_candidate
        and (
            probe.get("decision_change_observed")
            or probe.get("economic_effect_observed")
            or probe.get("utilization_state") == "SAFETY_LOCKED"
        )
    )
    evidence = {
        "diagnosis": row.get("diagnosis"),
        "utilization_state": probe.get("utilization_state"),
        "invocation_count": probe.get("invocation_count"),
        "expected_or_enabled_count": probe.get("expected_or_enabled_count"),
        "primary_reason": probe.get("primary_reason"),
    }
    result = {
        "Function": code,
        "Stage": stage,
        "Input": bool(probe.get("input_observed")),
        "Native Engine": _engine_summary(row, probe),
        "Output": bool(probe.get("output_observed")),
        "Consumer": bool(probe.get("consumer_observed")),
        "Decision Change": bool(probe.get("decision_change_observed")),
        "Economic Effect": bool(probe.get("economic_effect_observed")),
        "Protective Effect": protective_observed,
        "Timing Valid": not bool(probe.get("repair_required")),
        "Outcome Used": outcome_used,
        "Outcome Usage Valid": not outcome_used,
        "Duplicate": duplicate,
        "Authority": _authority(probe),
        "Classification": classification,
        "Evidence": evidence,
    }
    if classification not in FUNCTIONAL_CLASSES:
        raise ValueError(f"invalid functional classification: {classification}")
    return result


def _all(trace_rows: list[dict[str, Any]], key: str, predicate) -> bool:
    values = [row.get(key) for row in trace_rows]
    return bool(values) and all(predicate(value) for value in values)


def _system_rows(trace: dict[str, Any]) -> list[dict[str, Any]]:
    rows = trace.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise ValueError("decision trace opportunities missing")
    governance = trace.get("governance") or {}
    no_outcome = governance.get("outcome_aware_tuning_used") is False

    cma_ok = all(
        isinstance(row.get("cma"), dict)
        and isinstance(row.get("allocation"), dict)
        and row["cma"].get("sizing_authority") == "CIBO_CMA"
        and (
            row["cma"].get("risk_request_emitted")
            is row["allocation"].get("selected_by_cibo_policy")
        )
        for row in rows
    )
    risk_ok = _all(
        rows,
        "qore_risk",
        lambda v: isinstance(v, dict) and v.get("sovereign") is True,
    )
    provider_ok = _all(
        rows,
        "provider_economics_and_execution",
        lambda v: isinstance(v, dict)
        and bool(v.get("provider_evidence_id"))
        and "executed" in v,
    )
    settled = [row for row in rows if isinstance(row.get("settlement"), dict)]
    released = [row for row in rows if isinstance(row.get("capital_release"), dict)]
    settlement_ok = bool(settled) and all(
        item["settlement"].get("observed_at")
        and item["settlement"].get("evidence_id")
        for item in settled
    )
    release_ok = bool(released) and all(
        item["capital_release"].get("released_at")
        and item["capital_release"].get("evidence_id")
        for item in released
    )
    accounting_ok = settlement_ok and release_ok

    specs = (
        (
            "CMA",
            cma_ok,
            "TraderOpportunity/CE2I-adjusted capital request",
            "CIBO_CMA",
            "QORE Risk request",
            "PRODUCTIVE_UNIQUE",
            "SIZING_AUTHORITY",
        ),
        (
            "QORE_RISK_BRIDGE",
            risk_ok,
            "CMA risk request",
            "QORE Risk sovereign decision",
            "Execution eligibility",
            "PROTECTIVE_UNIQUE",
            "QORE_RISK_SOVEREIGN",
        ),
        (
            "EXECUTION_BRIDGE",
            provider_ok,
            "QORE Risk authorization + provider model",
            "provider execution binding",
            "settlement lifecycle",
            "PRODUCTIVE_COOPERATIVE",
            "EXECUTION_BRIDGE_ONLY",
        ),
        (
            "SETTLEMENT",
            settlement_ok,
            "executed position lifecycle",
            "settlement evidence",
            "capital accounting/release",
            "PRODUCTIVE_COOPERATIVE",
            "POSTDECISION_SETTLEMENT",
        ),
        (
            "RELEASE",
            release_ok,
            "settled position",
            "released risk/margin capacity",
            "capital availability",
            "PRODUCTIVE_COOPERATIVE",
            "CAPITAL_RELEASE",
        ),
        (
            "ACCOUNTING",
            accounting_ok,
            "settlement + release evidence",
            "capital ledger state",
            "next capital decision state",
            "PRODUCTIVE_COOPERATIVE",
            "ACCOUNTING_NO_SIZING_AUTHORITY",
        ),
        (
            "PROVIDER_INTERACTION",
            provider_ok,
            "normalized provider economics",
            "execution observation",
            "execution/settlement bridge",
            "INFORMATIONAL_USEFUL",
            "PROVIDER_EVIDENCE__NO_CAPITAL_AUTHORITY",
        ),
    )
    result: list[dict[str, Any]] = []
    for code, ok, input_name, output_name, consumer, classification, authority in specs:
        result.append(
            {
                "Function": code,
                "Stage": "SYSTEM",
                "Input": ok,
                "Native Engine": output_name,
                "Output": ok,
                "Consumer": ok,
                "Decision Change": (
                    ok and code in {"CMA", "QORE_RISK_BRIDGE", "EXECUTION_BRIDGE"}
                ),
                "Economic Effect": (
                    ok and code in {"CMA", "EXECUTION_BRIDGE", "SETTLEMENT", "RELEASE"}
                ),
                "Protective Effect": ok and code == "QORE_RISK_BRIDGE",
                "Timing Valid": ok,
                "Outcome Used": (
                    code in {"SETTLEMENT", "RELEASE", "ACCOUNTING"}
                ),
                "Outcome Usage Valid": (
                    no_outcome
                    if code not in {"SETTLEMENT", "RELEASE", "ACCOUNTING"}
                    else True
                ),
                "Duplicate": "NOT_PROVEN",
                "Authority": authority,
                "Classification": classification if ok else "INSTRUMENTATION_INCOMPLETE",
                "Evidence": {
                    "input_contract": input_name,
                    "consumer_contract": consumer,
                    "trace_opportunity_count": len(rows),
                    "settlement_count": len(settled),
                    "release_count": len(released),
                },
            }
        )
    return result


def build(
    function_io: dict[str, Any],
    utilization: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    function_rows = function_io.get("functions")
    probes = utilization.get("functions")
    if not isinstance(function_rows, list) or len(function_rows) != 53:
        raise ValueError("function-io must contain exactly 53 function rows")
    if not isinstance(probes, list) or len(probes) != 53:
        raise ValueError("utilization must contain exactly 53 function probes")
    by_probe = {str(row["function_code"]): row for row in probes}
    if len(by_probe) != 53:
        raise ValueError("utilization function codes must be unique")

    signatures: dict[tuple[object, ...], list[str]] = {}
    for row in function_rows:
        signatures.setdefault(_runtime_signature(row), []).append(
            str(row["function_code"])
        )
    exact_collisions = {
        signature: tuple(codes)
        for signature, codes in signatures.items()
        if len(codes) > 1
    }

    governance = trace.get("governance") or {}
    outcome_used = governance.get("outcome_aware_tuning_used") is not False
    rows = []
    for row in function_rows:
        code = str(row["function_code"])
        collision = exact_collisions.get(_runtime_signature(row), ())
        duplicate = (
            "NO_EXACT_RUNTIME_SIGNATURE_COLLISION"
            if not collision
            else "POTENTIAL_EXACT_RUNTIME_SIGNATURE_COLLISION:"
            + ",".join(item for item in collision if item != code)
        )
        rows.append(
            _function_row(
                row,
                by_probe[code],
                outcome_used=outcome_used,
                duplicate=duplicate,
            )
        )
    rows.extend(_system_rows(trace))

    classifications = Counter(str(row["Classification"]) for row in rows)
    mandatory_gaps = [
        row
        for row in rows
        if row["Classification"]
        in {"DEPENDENCY_BLOCKED", "INSTRUMENTATION_INCOMPLETE", "UNPROVEN"}
        or row["Outcome Usage Valid"] is False
        or row["Timing Valid"] is False
    ]
    return {
        "schema": "CIBO_FUNCTIONAL_COMPLETENESS_SCOREBOARD_V1",
        "group_id": function_io.get("group_id"),
        "row_count": len(rows),
        "function_rows": 53,
        "system_rows": len(SYSTEM_COMPONENTS),
        "functional_completeness": not mandatory_gaps,
        "mandatory_gap_count": len(mandatory_gaps),
        "classification_counts": dict(sorted(classifications.items())),
        "exact_runtime_signature_collision_count": len(exact_collisions),
        "exact_runtime_signature_collisions": [
            list(codes) for codes in exact_collisions.values()
        ],
        "rows": rows,
        "mandatory_gaps": mandatory_gaps,
        "governance": {
            "diagnostic_only": True,
            "outcome_aware_tuning": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
            "authority_note": (
                "GEN-C/Compound/Leverage/Portfolio/Sizing economic authority remains "
                "Architect-1 domain; this artifact classifies functional use only."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--function-io", type=Path, required=True)
    parser.add_argument("--utilization", type=Path, required=True)
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(
        _load(args.function_io),
        _load(args.utilization),
        _load(args.decision_trace),
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
                "row_count": payload["row_count"],
                "functional_completeness": payload["functional_completeness"],
                "mandatory_gap_count": payload["mandatory_gap_count"],
                "classification_counts": payload["classification_counts"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())