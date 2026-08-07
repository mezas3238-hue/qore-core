from __future__ import annotations

from qore.kernel.contracts import EventHandler
from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import KernelError
from qore.kernel.result import Failure, Result, Success


class EventBus:
    """Bus de eventos síncrono en memoria."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def publish(self, event: DomainEvent) -> Result[None, KernelError]:
        """Publicar a todos los handlers y preservar el primer error."""
        handlers = self._handlers.get(type(event), [])
        first_error: KernelError | None = None

        for handler in handlers:
            try:
                handler.handle(event)
            except Exception as exc:
                if first_error is None:
                    first_error = KernelError(str(exc))

        if first_error is not None:
            return Failure(first_error)
        return Success(None)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Suscribir un handler a un tipo de evento."""
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Eliminar una suscripción existente; si no existe, no hacer nada."""
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)
