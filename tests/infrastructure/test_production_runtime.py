from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.operational_persistence import (
    InMemoryOperationalPersistence,
    OperationalIdempotencyKey,
    OperationalRecordKey,
    OperationalWriteRequest,
)
from qore.infrastructure.operations_audit import (
    InMemoryOperationsAuditSink,
    OperationsAuditAction,
    OperationsAuditCategory,
    OperationsAuditOutcome,
    OperationsAuditRecord,
    OperationsAuditRecordId,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.production_configuration import (
    MappingProductionConfigurationSource,
    ProductionConfigurationSnapshot,
    ProductionEnvironment,
    ProductionRegion,
    ProductionRuntimeMode,
    load_production_configuration,
)
from qore.infrastructure.production_runtime import (
    ProductionOperationalRuntimeConfiguration,
    ProductionOperationalRuntimeValidationError,
    compose_production_operational_runtime,
)
from qore.infrastructure.runtime_operations import (
    RuntimeOperationActor,
    RuntimeOperationalState,
    RuntimeOperationReason,
    RuntimeOperationsSnapshot,
    RuntimeOperationTransitionRequest,
    apply_runtime_operation_transition,
    declare_runtime_operations,
)
from qore.kernel.result import Success

_NOW = datetime(2026, 8, 8, 6, 20, tzinfo=UTC)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("ad000000-0000-0000-0000-000000000001")),
    causation_id=CausationId(UUID("ad000000-0000-0000-0000-000000000002")),
)


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-production-operations"))
    assert isinstance(result, Success)
    return result.value


def _configuration_snapshot() -> ProductionConfigurationSnapshot:
    source = MappingProductionConfigurationSource(
        environment=ProductionEnvironment.PRODUCTION,
        region=ProductionRegion("sa-east-1"),
        runtime_mode=ProductionRuntimeMode.SERVICE,
        values={"health.readiness_required": True},
    )
    result = load_production_configuration(source, loaded_at=_NOW)
    assert isinstance(result, Success)
    return result.value


def _operations_ready() -> RuntimeOperationsSnapshot:
    actor = RuntimeOperationActor("operations.supervisor")
    declared = declare_runtime_operations(declared_at=_NOW, actor=actor)
    assert isinstance(declared, Success)
    starting = apply_runtime_operation_transition(
        declared.value,
        RuntimeOperationTransitionRequest(
            to_state=RuntimeOperationalState.STARTING,
            transitioned_at=_NOW + timedelta(seconds=1),
            actor=actor,
            reason=RuntimeOperationReason.START_REQUESTED,
        ),
    )
    assert isinstance(starting, Success)
    ready = apply_runtime_operation_transition(
        starting.value,
        RuntimeOperationTransitionRequest(
            to_state=RuntimeOperationalState.READY,
            transitioned_at=_NOW + timedelta(seconds=2),
            actor=actor,
            reason=RuntimeOperationReason.READINESS_CONFIRMED,
        ),
    )
    assert isinstance(ready, Success)
    return ready.value


def _write() -> OperationalWriteRequest:
    return OperationalWriteRequest(
        key=OperationalRecordKey("runtime.production.readiness"),
        idempotency_key=OperationalIdempotencyKey(
            UUID("ad000000-0000-0000-0000-000000000003")
        ),
        expected_version=0,
        persisted_at=_NOW + timedelta(seconds=3),
        values={"runtime.state": "ready"},
    )


def _audit() -> OperationsAuditRecord:
    return OperationsAuditRecord(
        record_id=OperationsAuditRecordId(
            UUID("ad000000-0000-0000-0000-000000000004")
        ),
        category=OperationsAuditCategory.RUNTIME,
        action=OperationsAuditAction("runtime.production.ready"),
        outcome=OperationsAuditOutcome.SUCCEEDED,
        recorded_at=_NOW + timedelta(seconds=4),
        metadata=_METADATA,
    )


def _runtime_configuration(
    *,
    operations: RuntimeOperationsSnapshot | None = None,
) -> ProductionOperationalRuntimeConfiguration:
    return ProductionOperationalRuntimeConfiguration(
        configuration=_configuration_snapshot(),
        operations=_operations_ready() if operations is None else operations,
        persistence=InMemoryOperationalPersistence(),
        audit=InMemoryOperationsAuditSink(),
    )


def test_production_runtime_preserves_core_and_is_ready() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    result = compose_production_operational_runtime(core, _runtime_configuration())

    assert isinstance(result, Success)
    assert result.value.is_ready is True
    assert result.value.core is core
    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health


def test_production_runtime_delegates_only_operational_persistence_and_audit() -> None:
    result = compose_production_operational_runtime(_core(), _runtime_configuration())
    assert isinstance(result, Success)

    written = result.value.persist_operational_state(_write())
    audited = result.value.append_operational_audit(_audit())

    assert isinstance(written, Success)
    assert written.value.record.version == 1
    assert isinstance(audited, Success)
    assert audited.value.action == OperationsAuditAction("runtime.production.ready")
    assert not hasattr(result.value, "execute_order")
    assert not hasattr(result.value, "write_position")


def test_non_ready_operations_fail_closed_for_runtime_readiness() -> None:
    actor = RuntimeOperationActor("operations.supervisor")
    declared = declare_runtime_operations(declared_at=_NOW, actor=actor)
    assert isinstance(declared, Success)
    result = compose_production_operational_runtime(
        _core(),
        _runtime_configuration(operations=declared.value),
    )

    assert isinstance(result, Success)
    assert result.value.is_ready is False


def test_required_live_runtime_cannot_be_missing() -> None:
    with pytest.raises(ProductionOperationalRuntimeValidationError):
        ProductionOperationalRuntimeConfiguration(
            configuration=_configuration_snapshot(),
            operations=_operations_ready(),
            persistence=InMemoryOperationalPersistence(),
            audit=InMemoryOperationsAuditSink(),
            require_live_runtime=True,
        )
