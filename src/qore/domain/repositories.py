from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from qore.domain.aggregates import AggregateRoot, AggregateVersion, EntityId
from qore.domain.events import BusinessDomainEvent
from qore.kernel.errors import DomainError
from qore.kernel.result import Result


@dataclass(frozen=True, slots=True)
class AggregateSnapshot[StateT]:
    """Snapshot inmutable de estado de agregado sin contrato de persistencia."""

    aggregate_id: EntityId
    version: AggregateVersion
    state: StateT


class Repository[AggregateT: AggregateRoot](Protocol):
    """Puerto de carga y guardado de agregados."""

    def get(self, aggregate_id: EntityId) -> Result[AggregateT | None, DomainError]:
        """Obtener un agregado o ausencia explícita."""
        ...

    def save(
        self,
        aggregate: AggregateT,
        *,
        expected_version: AggregateVersion | None = None,
    ) -> Result[None, DomainError]:
        """Guardar un agregado con control de versión opcional."""
        ...


class UnitOfWork(Protocol):
    """Puerto de frontera transaccional sin implementación de infraestructura."""

    def commit(self) -> Result[None, DomainError]:
        """Confirmar cambios pendientes."""
        ...

    def rollback(self) -> Result[None, DomainError]:
        """Revertir cambios pendientes."""
        ...


class SnapshotStore[StateT](Protocol):
    """Puerto para snapshots de agregados."""

    def load(
        self,
        aggregate_id: EntityId,
    ) -> Result[AggregateSnapshot[StateT] | None, DomainError]:
        """Cargar el último snapshot disponible."""
        ...

    def save(
        self,
        snapshot: AggregateSnapshot[StateT],
    ) -> Result[None, DomainError]:
        """Guardar un snapshot inmutable."""
        ...


class EventStore(Protocol):
    """Puerto para streams de eventos de dominio sin backend concreto."""

    def load(
        self,
        aggregate_id: EntityId,
        *,
        after_version: AggregateVersion | None = None,
    ) -> Result[tuple[BusinessDomainEvent, ...], DomainError]:
        """Cargar eventos en orden estable."""
        ...

    def append(
        self,
        aggregate_id: EntityId,
        events: tuple[BusinessDomainEvent, ...],
        *,
        expected_version: AggregateVersion,
    ) -> Result[AggregateVersion, DomainError]:
        """Añadir eventos y devolver la versión resultante."""
        ...
