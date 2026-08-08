from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.operations_audit import (
    InMemoryOperationsAuditSink,
    OperationsAuditAction,
    OperationsAuditCategory,
    OperationsAuditConflictError,
    OperationsAuditOutcome,
    OperationsAuditRecord,
    OperationsAuditRecordId,
    OperationsAuditValidationError,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 6, 10, tzinfo=UTC)
_RECORD_ID = OperationsAuditRecordId(
    UUID("ac000000-0000-0000-0000-000000000001")
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("ac000000-0000-0000-0000-000000000002")),
    causation_id=CausationId(UUID("ac000000-0000-0000-0000-000000000003")),
)


def _record(
    *,
    outcome: OperationsAuditOutcome = OperationsAuditOutcome.SUCCEEDED,
) -> OperationsAuditRecord:
    return OperationsAuditRecord(
        record_id=_RECORD_ID,
        category=OperationsAuditCategory.RUNTIME,
        action=OperationsAuditAction("runtime.readiness.transition"),
        outcome=outcome,
        recorded_at=_NOW,
        metadata=_METADATA,
        attributes={"runtime.state": "ready", "runtime.sequence": 2},
    )


def test_audit_sink_appends_and_exposes_stable_records() -> None:
    sink = InMemoryOperationsAuditSink()

    result = sink.append(_record())

    assert isinstance(result, Success)
    assert sink.records == (result.value,)


def test_identical_audit_replay_is_idempotent() -> None:
    sink = InMemoryOperationsAuditSink()
    record = _record()

    first = sink.append(record)
    replay = sink.append(record)

    assert isinstance(first, Success)
    assert isinstance(replay, Success)
    assert replay.value is first.value
    assert len(sink.records) == 1


def test_audit_id_collision_with_different_content_fails() -> None:
    sink = InMemoryOperationsAuditSink()
    first = sink.append(_record())
    collision = sink.append(_record(outcome=OperationsAuditOutcome.FAILED))

    assert isinstance(first, Success)
    assert isinstance(collision, Failure)
    assert isinstance(collision.error, OperationsAuditConflictError)


def test_audit_action_rejects_trading_execution_terms() -> None:
    for action in (
        "order.submitted",
        "position.changed",
        "trade.executed",
        "broker.connected",
        "execution.accepted",
    ):
        with pytest.raises(OperationsAuditValidationError):
            OperationsAuditAction(action)


def test_audit_attributes_reject_secret_like_keys_and_values() -> None:
    with pytest.raises(OperationsAuditValidationError):
        OperationsAuditRecord(
            record_id=_RECORD_ID,
            category=OperationsAuditCategory.SECURITY,
            action=OperationsAuditAction("security.reference.checked"),
            outcome=OperationsAuditOutcome.BLOCKED,
            recorded_at=_NOW,
            metadata=_METADATA,
            attributes={"provider.api_token": "redacted"},
        )
    with pytest.raises(OperationsAuditValidationError):
        OperationsAuditRecord(
            record_id=_RECORD_ID,
            category=OperationsAuditCategory.SECURITY,
            action=OperationsAuditAction("security.reference.checked"),
            outcome=OperationsAuditOutcome.BLOCKED,
            recorded_at=_NOW,
            metadata=_METADATA,
            attributes={"provider.header": "Bearer must-not-appear"},
        )


def test_audit_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(OperationsAuditValidationError):
        OperationsAuditRecord(
            record_id=_RECORD_ID,
            category=OperationsAuditCategory.RUNTIME,
            action=OperationsAuditAction("runtime.started"),
            outcome=OperationsAuditOutcome.SUCCEEDED,
            recorded_at=datetime(2026, 8, 8, 6, 10),
            metadata=_METADATA,
        )


def test_logical_values_preserve_trace_without_secret_material() -> None:
    record = _record()
    values = record.logical_values()

    assert values[0] == _RECORD_ID.logical_values()
    assert values[1:4] == (
        "runtime",
        ("runtime.readiness.transition",),
        "succeeded",
    )
    assert "secret" not in repr(values).lower()
