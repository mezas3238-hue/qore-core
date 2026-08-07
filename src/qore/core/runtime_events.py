from __future__ import annotations

from datetime import datetime

from qore.core.runtime import RuntimeContext
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import KernelError


class RuntimeStartedEvent(DomainEvent):
    """Evento emitido cuando una ejecución del runtime entra en RUNNING."""

    def __init__(self, *, timestamp: datetime, context: RuntimeContext) -> None:
        super().__init__(
            timestamp=timestamp,
            event_name="qore.runtime.started",
            metadata={
                "execution_id": str(context.execution_id),
                "runtime_version": context.runtime_version,
            },
        )


class RuntimeStoppedEvent(DomainEvent):
    """Evento emitido cuando una ejecución del runtime entra en STOPPED."""

    def __init__(self, *, timestamp: datetime, context: RuntimeContext) -> None:
        super().__init__(
            timestamp=timestamp,
            event_name="qore.runtime.stopped",
            metadata={
                "execution_id": str(context.execution_id),
                "runtime_version": context.runtime_version,
            },
        )


class RuntimeFailedEvent(DomainEvent):
    """Evento emitido cuando una ejecución del runtime entra en ERROR."""

    def __init__(
        self,
        *,
        timestamp: datetime,
        context: RuntimeContext,
        error: KernelError,
    ) -> None:
        super().__init__(
            timestamp=timestamp,
            event_name="qore.runtime.failed",
            metadata={
                "execution_id": str(context.execution_id),
                "runtime_version": context.runtime_version,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )
