from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from types import MappingProxyType
from uuid import UUID

from qore.kernel.domain_event import DomainEvent
from qore.kernel.errors import ValidationError
from qore.kernel.temporal import canonical_instant

type DomainMetadataScalar = str | int | float | bool | UUID | None
type DomainMetadataValue = DomainMetadataScalar | tuple[DomainMetadataValue, ...]
_RESERVED_METADATA_KEYS = frozenset({"category", "correlation_id", "causation_id"})


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


def _validate_metadata_value(value: object) -> None:
    """Aceptar únicamente valores profundamente inmutables y deterministas."""
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValidationError("domain event metadata floats must be finite")
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise ValidationError(
        "domain event metadata values must be immutable scalars or tuples"
    )


@dataclass(frozen=True, slots=True)
class DomainEventMetadata:
    """Metadata inmutable de correlación, causalidad y atributos de dominio."""

    category: DomainEventCategory
    correlation_id: CorrelationId
    causation_id: CausationId | None = None
    attributes: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if any(not key.strip() for key in self.attributes):
            raise ValidationError("domain event metadata keys must not be empty")
        reserved = _RESERVED_METADATA_KEYS.intersection(self.attributes)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise ValidationError(f"reserved domain event metadata keys: {names}")
        for value in self.attributes.values():
            _validate_metadata_value(value)
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
    _domain_metadata: DomainEventMetadata

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
            canonical_instant(self.timestamp),
            self.event_name,
            self.event_version,
            *self._domain_metadata.logical_values(),
        )
