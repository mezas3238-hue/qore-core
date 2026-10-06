"""Receipt-to-engine-efficiency evidence extraction for CIBO."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_engine_efficiency_sensor import (
    CiboEngineEfficiencyEvidence,
)


def _dec(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise CiboCapitalManagementError(
            "engine receipt numeric evidence must be finite"
        )
    return result


def build_engine_evidence_from_receipts(
    *,
    engine_id: str,
    receipts: tuple[dict[str, Any], ...],
    eligible_count: int,
    opportunity_value_available_usd: Decimal,
    marginal_value_usd: Decimal = Decimal(0),
    destructive_value_usd: Decimal = Decimal(0),
    unidentified_value_usd: Decimal = Decimal(0),
    latency_minutes_total: Decimal = Decimal(0),
    latency_observations: int = 0,
) -> CiboEngineEfficiencyEvidence:
    """Aggregate canonical runtime receipt payloads for one engine/tool."""

    if not engine_id:
        raise CiboCapitalManagementError(
            "engine receipt aggregation identity required"
        )
    selected = []
    for row in receipts:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "engine receipt payload must be dict"
            )
        identity = row.get("function_code") or row.get("tool_code")
        native_name = row.get("native_engine_name") or row.get("engine_name")
        if str(identity) == engine_id or str(native_name) == engine_id:
            selected.append(row)

    invoked = sum(
        bool(
            row.get(
                "native_engine_called",
                bool(row.get("engine_name")),
            )
        )
        for row in selected
    )
    consumed = sum(
        bool(
            row.get("downstream_consumer")
            and row.get("consumer_action")
        )
        for row in selected
    )
    changed = sum(bool(row.get("decision_changed")) for row in selected)
    effective = sum(
        bool(
            row.get("economic_effect_observable")
            or _dec(row.get("incremental_pnl_attribution_usd", "0")) != 0
            or _dec(row.get("risk_delta_usd", "0")) != 0
            or _dec(row.get("margin_delta_usd", "0")) != 0
        )
        for row in selected
        if bool(row.get("decision_changed"))
    )
    blocked = max(0, eligible_count - invoked)

    return CiboEngineEfficiencyEvidence(
        engine_id=engine_id,
        eligible_count=eligible_count,
        invoked_count=invoked,
        output_consumed_count=min(consumed, invoked),
        decision_changed_count=min(changed, consumed, invoked),
        economically_effective_count=min(
            effective,
            changed,
            consumed,
            invoked,
        ),
        blocked_count=blocked,
        marginal_value_usd=marginal_value_usd,
        opportunity_value_available_usd=opportunity_value_available_usd,
        latency_minutes_total=latency_minutes_total,
        latency_observations=latency_observations,
        destructive_value_usd=destructive_value_usd,
        unidentified_value_usd=unidentified_value_usd,
    )
