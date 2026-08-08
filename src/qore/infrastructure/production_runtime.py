from __future__ import annotations

from dataclasses import dataclass

from qore.core.application import CoreApplication
from qore.infrastructure.operational_persistence import (
    OperationalPersistenceBoundary,
    OperationalPersistenceError,
    OperationalRecordSnapshot,
    OperationalWriteReceipt,
    OperationalWriteRequest,
)
from qore.infrastructure.operations_audit import (
    OperationsAuditBoundary,
    OperationsAuditError,
    OperationsAuditRecord,
)
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.production_configuration import ProductionConfigurationSnapshot
from qore.infrastructure.runtime_operations import (
    RuntimeOperationalState,
    RuntimeOperationsSnapshot,
)
from qore.infrastructure.supervised_live_runtime import SupervisedLiveRuntimeComposition
from qore.kernel.result import Failure, Result, Success


class ProductionOperationalRuntimeError(ExternalPortError):
    """Base error for PHASE-10 operational runtime composition."""

    __slots__ = ()


class ProductionOperationalRuntimeValidationError(ProductionOperationalRuntimeError):
    """Violation of a production operational runtime invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ProductionOperationalRuntimeConfiguration:
    """Explicit operational dependencies kept outside the Core object graph."""

    configuration: ProductionConfigurationSnapshot
    operations: RuntimeOperationsSnapshot
    persistence: OperationalPersistenceBoundary
    audit: OperationsAuditBoundary
    live_runtime: SupervisedLiveRuntimeComposition | None = None
    require_live_runtime: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, ProductionConfigurationSnapshot):
            raise ProductionOperationalRuntimeValidationError(
                "production runtime configuration snapshot must be explicit"
            )
        if not isinstance(self.operations, RuntimeOperationsSnapshot):
            raise ProductionOperationalRuntimeValidationError(
                "production runtime operations snapshot must be explicit"
            )
        if not isinstance(self.require_live_runtime, bool):
            raise ProductionOperationalRuntimeValidationError(
                "production runtime require_live_runtime must be bool"
            )
        if self.live_runtime is not None and not isinstance(
            self.live_runtime, SupervisedLiveRuntimeComposition
        ):
            raise ProductionOperationalRuntimeValidationError(
                "production runtime live_runtime must be SupervisedLiveRuntimeComposition"
            )
        if self.require_live_runtime and self.live_runtime is None:
            raise ProductionOperationalRuntimeValidationError(
                "required supervised live runtime is missing"
            )


@dataclass(frozen=True, slots=True)
class ProductionOperationalRuntime:
    """Operational facade above an unchanged CoreApplication."""

    core: CoreApplication
    configuration: ProductionOperationalRuntimeConfiguration

    def __post_init__(self) -> None:
        if not isinstance(self.core, CoreApplication):
            raise ProductionOperationalRuntimeValidationError(
                "production operational runtime core must be CoreApplication"
            )
        if not isinstance(
            self.configuration, ProductionOperationalRuntimeConfiguration
        ):
            raise ProductionOperationalRuntimeValidationError(
                "production operational runtime configuration must be explicit"
            )

    @property
    def is_ready(self) -> bool:
        if self.configuration.operations.state is not RuntimeOperationalState.READY:
            return False
        live_runtime = self.configuration.live_runtime
        if self.configuration.require_live_runtime:
            return live_runtime is not None and live_runtime.market_data is not None
        if live_runtime is not None and live_runtime.market_data is None:
            return False
        return True

    def persist_operational_state(
        self,
        request: OperationalWriteRequest,
    ) -> Result[OperationalWriteReceipt, OperationalPersistenceError]:
        """Delegate only non-trading operational writes to the configured boundary."""
        return self.configuration.persistence.write(request)

    def read_operational_state(
        self,
        request: OperationalWriteRequest,
    ) -> Result[OperationalRecordSnapshot | None, OperationalPersistenceError]:
        """Read the operational key identified by an existing validated request."""
        return self.configuration.persistence.read(request.key)

    def append_operational_audit(
        self,
        record: OperationsAuditRecord,
    ) -> Result[OperationsAuditRecord, OperationsAuditError]:
        """Append a sanitized operational audit record."""
        return self.configuration.audit.append(record)


def compose_production_operational_runtime(
    core: CoreApplication,
    configuration: ProductionOperationalRuntimeConfiguration,
) -> Result[ProductionOperationalRuntime, ExternalPortError]:
    """Compose production operations while proving Core state is unchanged."""
    if not isinstance(core, CoreApplication):
        return Failure(
            ProductionOperationalRuntimeValidationError(
                "production operational runtime core must be CoreApplication"
            )
        )
    if not isinstance(configuration, ProductionOperationalRuntimeConfiguration):
        return Failure(
            ProductionOperationalRuntimeValidationError(
                "production operational runtime configuration must be explicit"
            )
        )

    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    try:
        composition = ProductionOperationalRuntime(
            core=core,
            configuration=configuration,
        )
    except ExternalPortError as error:
        return Failure(error)

    if core.event_bus is not event_bus:
        return Failure(
            ProductionOperationalRuntimeValidationError(
                "production runtime must preserve Core EventBus"
            )
        )
    if core.runtime_plan != runtime_plan:
        return Failure(
            ProductionOperationalRuntimeValidationError(
                "production runtime must not mutate Core RuntimePlan"
            )
        )
    if core.runtime_snapshot() != runtime_snapshot:
        return Failure(
            ProductionOperationalRuntimeValidationError(
                "production runtime must not mutate Core RuntimeSnapshot"
            )
        )
    if core.runtime_health() != runtime_health:
        return Failure(
            ProductionOperationalRuntimeValidationError(
                "production runtime must not mutate Core RuntimeHealth"
            )
        )
    return Success(composition)
