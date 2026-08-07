from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from qore.domain.events import CausationId, CorrelationId, DomainMetadataValue
from qore.kernel.errors import DomainError, ValidationError
from qore.kernel.result import Result


@dataclass(frozen=True, slots=True)
class CommandId:
    """Identidad explícita de un comando."""

    value: UUID


@dataclass(frozen=True, slots=True)
class CommandName:
    """Nombre lógico validado de un comando."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValidationError("command name must not be empty")


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """Clave explícita para comandos que requieren deduplicación."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValidationError("idempotency key must not be empty")


@dataclass(frozen=True, slots=True)
class CommandMetadata:
    """Contexto inmutable de correlación, causalidad e idempotencia."""

    correlation_id: CorrelationId
    causation_id: CausationId | None = None
    idempotency_key: IdempotencyKey | None = None
    attributes: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __post_init__(self) -> None:
        if any(not key.strip() for key in self.attributes):
            raise ValidationError("command metadata keys must not be empty")
        ordered = {key: self.attributes[key] for key in sorted(self.attributes)}
        object.__setattr__(self, "attributes", MappingProxyType(ordered))

    def logical_values(self) -> tuple[object, ...]:
        """Representación lógica estable del contexto del comando."""
        return (
            str(self.correlation_id.value),
            str(self.causation_id.value) if self.causation_id is not None else None,
            self.idempotency_key.value if self.idempotency_key is not None else None,
            tuple(self.attributes.items()),
        )


@dataclass(frozen=True, slots=True)
class Command:
    """Envelope base inmutable para comandos de PHASE-03."""

    command_id: CommandId
    timestamp: datetime
    name: CommandName
    metadata: CommandMetadata

    def logical_values(self) -> tuple[object, ...]:
        """Representación determinista por valores del comando."""
        return (
            str(self.command_id.value),
            self.timestamp.isoformat(),
            self.name.value,
            *self.metadata.logical_values(),
        )


class CommandError(DomainError):
    """Error uniforme producido al validar o manejar un comando."""

    __slots__ = ()


class CommandValidationError(CommandError):
    """Error uniforme de validación de comandos."""

    __slots__ = ()


type CommandResult[T] = Result[T, DomainError]


class CommandHandler[C: Command, R](Protocol):
    """Puerto tipado para manejar un comando sin definir infraestructura."""

    def handle(self, command: C) -> CommandResult[R]:
        """Procesar un comando y devolver un resultado explícito."""
        ...
