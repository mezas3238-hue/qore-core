from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from re import fullmatch
from types import MappingProxyType
from uuid import UUID

from qore.domain.events import CausationId, CorrelationId, DomainMetadataValue
from qore.kernel.errors import DomainError

_RESERVED_DECISION_METADATA_KEYS = frozenset({"correlation_id", "causation_id"})


class DecisionError(DomainError):
    """Error base de los contratos funcionales de decisión."""

    __slots__ = ()


class DecisionValidationError(DecisionError):
    """Violación de una invariante de decisión funcional."""

    __slots__ = ()


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise DecisionValidationError("decision metadata floats must be finite")
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise DecisionValidationError(
        "decision metadata values must be immutable scalars or tuples"
    )


@dataclass(frozen=True, slots=True)
class DecisionId:
    """Identidad explícita de una decisión funcional."""

    value: UUID


@dataclass(frozen=True, slots=True)
class DecisionType:
    """Clasificación extensible y validada de una decisión."""

    value: str

    def __post_init__(self) -> None:
        if fullmatch(r"[a-z][a-z0-9.-]*", self.value) is None:
            raise DecisionValidationError(
                "decision type must use lowercase letters, digits, dots, or hyphens"
            )


class DecisionStatus(StrEnum):
    """Estado de lifecycle de una decisión."""

    PENDING = "pending"
    RESOLVED = "resolved"


class DecisionPriority(StrEnum):
    """Prioridad explícita sin implicar ejecución externa."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionOutcome(StrEnum):
    """Resultado cerrado de una decisión resuelta."""

    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class DecisionMetadata:
    """Contexto inmutable de correlación, causalidad y atributos funcionales."""

    correlation_id: CorrelationId
    causation_id: CausationId | None = None
    attributes: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if any(not key.strip() for key in self.attributes):
            raise DecisionValidationError("decision metadata keys must not be empty")
        reserved = _RESERVED_DECISION_METADATA_KEYS.intersection(self.attributes)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise DecisionValidationError(f"reserved decision metadata keys: {names}")
        for value in self.attributes.values():
            _validate_metadata_value(value)
        ordered = {key: self.attributes[key] for key in sorted(self.attributes)}
        object.__setattr__(self, "attributes", MappingProxyType(ordered))

    def logical_values(self) -> tuple[object, ...]:
        """Representación determinista del contexto de decisión."""
        return (
            str(self.correlation_id.value),
            str(self.causation_id.value) if self.causation_id is not None else None,
            tuple(self.attributes.items()),
        )


@dataclass(frozen=True, slots=True)
class DecisionReasonCode:
    """Código estructurado y estable de una razón."""

    value: str

    def __post_init__(self) -> None:
        if fullmatch(r"[a-z][a-z0-9.-]*", self.value) is None:
            raise DecisionValidationError(
                "decision reason code must use lowercase letters, digits, dots, or hyphens"
            )


@dataclass(frozen=True, slots=True)
class DecisionReason:
    """Razón estructurada de una decisión, sin semántica específica de módulo."""

    code: DecisionReasonCode
    summary: str
    attributes: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise DecisionValidationError("decision reason summary must not be empty")
        if any(not key.strip() for key in self.attributes):
            raise DecisionValidationError("decision reason attribute keys must not be empty")
        for value in self.attributes.values():
            _validate_metadata_value(value)
        ordered = {key: self.attributes[key] for key in sorted(self.attributes)}
        object.__setattr__(self, "attributes", MappingProxyType(ordered))

    def logical_values(self) -> tuple[object, ...]:
        """Representación determinista de la razón."""
        return (self.code.value, self.summary, tuple(self.attributes.items()))


@dataclass(frozen=True, slots=True)
class FunctionalDecision:
    """Decisión funcional común, explícita, inmutable y determinista."""

    decision_id: DecisionId
    timestamp: datetime
    decision_type: DecisionType
    status: DecisionStatus
    priority: DecisionPriority
    metadata: DecisionMetadata
    reasons: tuple[DecisionReason, ...] = ()
    outcome: DecisionOutcome | None = None

    def __post_init__(self) -> None:
        if self.status is DecisionStatus.PENDING and self.outcome is not None:
            raise DecisionValidationError("pending decision must not have an outcome")
        if self.status is DecisionStatus.RESOLVED and self.outcome is None:
            raise DecisionValidationError("resolved decision must have an outcome")
        if self.status is DecisionStatus.RESOLVED and not self.reasons:
            raise DecisionValidationError("resolved decision must include at least one reason")

    def logical_values(self) -> tuple[object, ...]:
        """Representación lógica estable por valores."""
        return (
            str(self.decision_id.value),
            self.timestamp.isoformat(),
            self.decision_type.value,
            self.status.value,
            self.priority.value,
            self.metadata.logical_values(),
            tuple(reason.logical_values() for reason in self.reasons),
            self.outcome.value if self.outcome is not None else None,
        )
