from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from qore.domain.events import BusinessDomainEvent
from qore.kernel.errors import DomainError, ValidationError


@dataclass(frozen=True, slots=True)
class EntityId:
    """Identidad explícita de una entidad de dominio."""

    value: UUID


@dataclass(frozen=True, slots=True)
class AggregateVersion:
    """Versión monotónica validada de un agregado."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValidationError("aggregate version must be non-negative")

    def next(self) -> AggregateVersion:
        return AggregateVersion(self.value + 1)


class AggregateInvariantError(DomainError):
    """Violación explícita de una invariante de agregado."""

    __slots__ = ()


class Entity:
    """Entidad identificada por identidad estable, no por todos sus atributos."""

    __slots__ = ("_entity_id",)

    def __init__(self, *, entity_id: EntityId) -> None:
        self._entity_id = entity_id

    @property
    def entity_id(self) -> EntityId:
        return self._entity_id

    def __eq__(self, other: object) -> bool:
        if other is self:
            return True
        if type(self) is not type(other):
            return NotImplemented
        return self.entity_id == other.entity_id

    def __hash__(self) -> int:
        return hash((type(self), self.entity_id))


class ValueObject(Protocol):
    """Contrato estructural para valores de dominio comparables por valor."""

    def logical_values(self) -> tuple[object, ...]:
        """Devolver la representación lógica determinista del valor."""
        ...


class DomainService[ResultT](Protocol):
    """Contrato estructural para servicios de dominio puros."""

    def execute(self) -> ResultT:
        """Ejecutar una operación de dominio sin infraestructura."""
        ...


class AggregateRoot(Entity):
    """Raíz de agregado con versión y eventos pendientes controlados."""

    __slots__ = ("_version", "_pending_events")

    def __init__(
        self,
        *,
        aggregate_id: EntityId,
        version: AggregateVersion = AggregateVersion(0),
    ) -> None:
        super().__init__(entity_id=aggregate_id)
        self._version = version
        self._pending_events: list[BusinessDomainEvent] = []

    @property
    def aggregate_id(self) -> EntityId:
        return self.entity_id

    @property
    def version(self) -> AggregateVersion:
        return self._version

    @property
    def pending_events(self) -> tuple[BusinessDomainEvent, ...]:
        return tuple(self._pending_events)

    def record_event(self, event: BusinessDomainEvent) -> None:
        """Registrar un evento y avanzar exactamente una versión."""
        self._pending_events.append(event)
        self._version = self._version.next()

    def pull_events(self) -> tuple[BusinessDomainEvent, ...]:
        """Extraer los eventos pendientes en orden y vaciar el buffer."""
        events = tuple(self._pending_events)
        self._pending_events.clear()
        return events

    def ensure(self, condition: bool, message: str) -> None:
        """Aplicar una invariante explícita del agregado."""
        if not condition:
            raise AggregateInvariantError(message)
