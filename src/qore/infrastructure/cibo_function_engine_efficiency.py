"""Build per-function engine efficiency reports from Trader Lab telemetry."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_engine_efficiency_sensor import (
    CiboEngineEfficiencyEvidence,
    CiboEngineEfficiencyReport,
    measure_engine_efficiency,
    rank_engine_efficiency,
)


def build_function_engine_efficiency_reports(
    utilization_sensor: Mapping[str, Any],
    *,
    marginal_value_usd: Mapping[str, Decimal] | None = None,
    available_value_usd: Mapping[str, Decimal] | None = None,
    destructive_value_usd: Mapping[str, Decimal] | None = None,
) -> tuple[CiboEngineEfficiencyReport, ...]:
    """Convert Trader Lab 53-function telemetry into ranked engine reports."""

    values = marginal_value_usd or {}
    available = available_value_usd or {}
    destructive = destructive_value_usd or {}
    rows = utilization_sensor.get("functions")
    if not isinstance(rows, list):
        raise CiboCapitalManagementError(
            "function engine sensor requires telemetry functions list"
        )

    reports = []
    for row in rows:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "function engine telemetry row must be dict"
            )
        code = str(row.get("function_code", ""))
        if not code:
            raise CiboCapitalManagementError(
                "function engine telemetry identity required"
            )
        eligible = int(row.get("expected_or_enabled_count", 0))
        invocation = int(row.get("invocation_count", 0))
        direct = int(row.get("direct_trace_evidence_count", 0))
        consumed = invocation if bool(row.get("consumer_observed")) else 0
        changed = min(
            direct if bool(row.get("decision_change_observed")) else 0,
            consumed,
        )
        effective = min(
            direct if bool(row.get("economic_effect_observed")) else 0,
            changed,
        )
        known_value = code in values and code in available
        evidence = CiboEngineEfficiencyEvidence(
            engine_id=code,
            eligible_count=max(eligible, invocation),
            invoked_count=invocation,
            output_consumed_count=consumed,
            decision_changed_count=changed,
            economically_effective_count=effective,
            blocked_count=max(0, eligible - invocation),
            marginal_value_usd=values.get(code, Decimal(0)),
            opportunity_value_available_usd=available.get(
                code,
                values.get(code, Decimal(0)),
            ),
            destructive_value_usd=destructive.get(code, Decimal(0)),
            value_identified=known_value,
        )
        reports.append(measure_engine_efficiency(evidence))

    return rank_engine_efficiency(tuple(reports))
