"""
contracts — Interfaces fundamentales del Kernel de QORE.

Propósito:
    Definir contratos abstractos para publicación, manejo de eventos y repositorios.

Alcance:
    - ``EventPublisher``.
    - ``EventHandler``.
    - ``Repository[T_Entity, T_ID]``.

Dependencias:
    - Python 3.12.
    - ``qore.kernel.domain_event.DomainEvent``.

Restricciones:
    - Sin implementaciones concretas.
"""
from __future__ import annotations

from typing import Protocol

from qore.kernel.domain_event import DomainEvent


class EventPublisher(Protocol):
    """Contrato para publicar eventos de dominio."""

    def publish(self, event: DomainEvent) -> None:
        """Publicar un evento."""
        ...


class EventHandler(Protocol):
    """Contrato para manejar un evento de dominio."""

    def handle(self, event: DomainEvent) -> None:
        """Procesar un evento recibido."""
        ...


class Repository[T_Entity, T_ID](Protocol):
    """Contrato mínimo de repositorio para cargar y guardar entidades."""

    def load(self, id: T_ID) -> T_Entity | None:
        """Reconstruir una entidad a partir de su identificador."""
        ...

    def save(self, entity: T_Entity) -> None:
        """Persistir una entidad."""
        ...
