"""Causal per-call runtime receipts for CE2I native engines.

Receipts bind actual engine input/output to a downstream consumer.  They are
observability contracts only: they grant no allocation, Risk, execution, broker,
LIVE, Production, real-capital, certification, or merge authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _sha256(payload: dict[str, object]) -> str:
    raw = json.dumps(
        _canonical(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CiboCe2iRuntimeReceipt:
    tool_code: str
    engine_name: str
    stage: str
    scope_id: str
    input_payload: dict[str, object]
    output_payload: dict[str, object]
    input_sha256: str
    output_sha256: str
    downstream_consumer: str
    consumer_action: str
    status: str
    decision_changed: bool
    economic_effect_observable: bool
    native_engine_called: bool = True
    outcome_used: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    productive_authority: bool = False
    broker_mutation: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.tool_code, str)
            or not self.tool_code.startswith("T")
            or len(self.tool_code) != 3
            or not self.tool_code[1:].isdigit()
            or not 1 <= int(self.tool_code[1:]) <= 20
        ):
            raise CiboCapitalManagementError("CE2I runtime receipt tool code invalid")
        if not self.engine_name or not self.scope_id:
            raise CiboCapitalManagementError(
                "CE2I runtime receipt engine/scope required"
            )
        if self.stage not in {"PREDECISION", "POST_SETTLEMENT"}:
            raise CiboCapitalManagementError("CE2I runtime receipt stage invalid")
        if not self.input_payload or not self.output_payload:
            raise CiboCapitalManagementError(
                "CE2I runtime receipt requires input/output payloads"
            )
        if self.input_sha256 != _sha256(self.input_payload):
            raise CiboCapitalManagementError(
                "CE2I runtime receipt input digest drift"
            )
        if self.output_sha256 != _sha256(self.output_payload):
            raise CiboCapitalManagementError(
                "CE2I runtime receipt output digest drift"
            )
        if not self.downstream_consumer or not self.consumer_action:
            raise CiboCapitalManagementError(
                "CE2I runtime receipt downstream binding required"
            )
        if self.status not in {
            "APPLIED",
            "FAIL_CLOSED",
            "JUSTIFIED_NOT_APPLICABLE",
        }:
            raise CiboCapitalManagementError(
                "CE2I runtime receipt status invalid"
            )
        for name in (
            "decision_changed",
            "economic_effect_observable",
            "native_engine_called",
            "outcome_used",
            "allocation_authority",
            "risk_authority",
            "execution_authority",
            "productive_authority",
            "broker_mutation",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"CE2I runtime receipt {name} must be bool"
                )
        if (
            self.allocation_authority
            or self.risk_authority
            or self.execution_authority
            or self.productive_authority
            or self.broker_mutation
        ):
            raise CiboCapitalManagementError(
                "CE2I runtime receipt authority boundary violated"
            )
        if self.stage == "PREDECISION" and self.outcome_used:
            raise CiboCapitalManagementError(
                "CE2I predecision runtime receipt cannot use outcome"
            )


def build_ce2i_runtime_receipt(
    *,
    tool_code: str,
    engine_name: str,
    stage: str,
    scope_id: str,
    input_payload: Mapping[str, object],
    output_payload: Mapping[str, object],
    downstream_consumer: str,
    consumer_action: str,
    status: str = "APPLIED",
    decision_changed: bool = False,
    economic_effect_observable: bool = False,
    outcome_used: bool = False,
) -> CiboCe2iRuntimeReceipt:
    return CiboCe2iRuntimeReceipt(
        tool_code=tool_code,
        engine_name=engine_name,
        stage=stage,
        scope_id=scope_id,
        input_payload=dict(input_payload),
        output_payload=dict(output_payload),
        input_sha256=_sha256(dict(input_payload)),
        output_sha256=_sha256(dict(output_payload)),
        downstream_consumer=downstream_consumer,
        consumer_action=consumer_action,
        status=status,
        decision_changed=decision_changed,
        economic_effect_observable=economic_effect_observable,
        outcome_used=outcome_used,
    )
