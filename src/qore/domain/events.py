from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any
from uuid import UUID

from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import ValidationError


@dataclass(frozen=True, slots=True)
class DomainEventId:
    """Identidad explícita de un evento de dominio."""

    value: UUID


@dataclass(frozen=True, slots=True)
class CorrelationId:
    """Identidad explícita que correlaciona una cadena de trabajo de dominio."""

    value: UUID


@dataclass(frozen=True, slots=True)
class CausationId:
    """Identidad explícita del mensaje que causó un evento de dominio."""

    value: UUID


@dataclass(frozen=True, slots=True)
class DomainEventVersion:
    """Versión lógica validada de un contrato de evento."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValidationError("domain event version must not be empty")


@dataclass(frozen=True, slots=True)
class DomainEventCategory:
    """Categoría estructurada y estable de un evento de negocio."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValidationError("domain event category must not be empty")


@dataclass(frozen=True, slots=True)
class DomainEventMetadata:
    """Metadata inmutable de correlación, causalidad y atributos de dominio."""

    category: DomainEventCategory
    correlation_id: CorrelationId
    causation_id: CausationId | None = None
    attributes: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if any(not key.strip() for key in self.attributes):
            raise ValidationError("domain event metadata keys must not be empty")
        ordered = {key: self.attributes[key] for key in sorted(self.attributes)}
        object.__setattr__(self, "attributes", MappingProxyType(ordered))

    def logical_values(self) -> tuple[object, ...]:
        """Representación lógica estable sin serialización de transporte."""
        return (
            self.category.value,
            str(self.correlation_id.value),
            str(self.causation_id.value) if self.causation_id is not None else None,
            tuple(self.attributes.items()),
        )


class BusinessDomainEvent(DomainEvent):
    """Evento de negocio explícito compatible con el DomainEvent del Kernel."""

    __slots__ = ("_domain_metadata",)

    def __init__(
        self,
        *,
        timestamp: datetime,
        event_name: str,
        event_id: DomainEventId,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
    ) -> None:
        if not event_name.strip():
            raise ValidationError("domain event name must not be empty")

        object.__setattr__(self, "_domain_metadata", metadata)
        super().__init__(
            timestamp=timestamp,
            event_name=event_name,
            event_id=event_id.value,
            event_version=event_version.value,
            metadata={
                "category": metadata.category.value,
                "correlation_id": str(metadata.correlation_id.value),
                "causation_id": (
                    str(metadata.causation_id.value)
                    if metadata.causation_id is not None
                    else None
                ),
                **metadata.attributes,
            },
        )

    @property
    def domain_event_id(self) -> DomainEventId:
        return DomainEventId(self.event_id)

    @property
    def domain_event_version(self) -> DomainEventVersion:
        return DomainEventVersion(self.event_version)

    @property
    def domain_metadata(self) -> DomainEventMetadata:
        return self._domain_metadata

    def logical_values(self) -> tuple[object, ...]:
        """Representación determinista por valores del contrato de dominio."""
        return (
            str(self.event_id),
            self.timestamp.isoformat(),
            self.event_name,
            self.event_version,
            *self._domain_metadata.logical_values(),
        )
