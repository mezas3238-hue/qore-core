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
from qore.kernel.temporal import canonical_instant, is_timezone_aware_datetime

_RESERVED_SPECIALIST_METADATA_KEYS = frozenset({"correlation_id", "causation_id"})


class SpecialistError(DomainError):
    """Error base de los contratos de análisis especializado."""

    __slots__ = ()


class SpecialistValidationError(SpecialistError):
    """Violación explícita de una invariante de análisis especializado."""

    __slots__ = ()


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise SpecialistValidationError(
                "specialist metadata floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise SpecialistValidationError(
        "specialist metadata values must be immutable scalars or tuples"
    )


@dataclass(frozen=True, slots=True)
class SpecialistAnalysisId:
    """Identidad explícita de un análisis especializado."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise SpecialistValidationError("specialist analysis id must be a UUID")


@dataclass(frozen=True, slots=True)
class SpecialistKind:
    """Clasificación extensible y validada del productor especializado."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9.-]*", self.value
        ) is None:
            raise SpecialistValidationError(
                "specialist kind must use lowercase letters, digits, dots, or hyphens"
            )


class SpecialistAnalysisStatus(StrEnum):
    """Estado cerrado del lifecycle de un análisis especializado."""

    PENDING = "pending"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class SpecialistConfidence:
    """Confianza explícita y finita, normalizada en el intervalo [0.0, 1.0]."""

    value: float

    def __post_init__(self) -> None:
        if type(self.value) is not float or not isfinite(self.value):
            raise SpecialistValidationError(
                "specialist confidence must be a finite float"
            )
        if not 0.0 <= self.value <= 1.0:
            raise SpecialistValidationError(
                "specialist confidence must be between 0.0 and 1.0"
            )


@dataclass(frozen=True, slots=True)
class SpecialistMetadata:
    """Contexto inmutable de correlation, causation y atributos especializados."""

    correlation_id: CorrelationId
    causation_id: CausationId | None = None
    attributes: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.correlation_id, CorrelationId):
            raise SpecialistValidationError(
                "specialist metadata correlation_id must be a CorrelationId"
            )
        if self.causation_id is not None and not isinstance(
            self.causation_id, CausationId
        ):
            raise SpecialistValidationError(
                "specialist metadata causation_id must be a CausationId or None"
            )
        if not isinstance(self.attributes, Mapping):
            raise SpecialistValidationError(
                "specialist metadata attributes must be a mapping"
            )
        if any(not isinstance(key, str) or not key.strip() for key in self.attributes):
            raise SpecialistValidationError(
                "specialist metadata keys must be non-empty strings"
            )
        reserved = _RESERVED_SPECIALIST_METADATA_KEYS.intersection(self.attributes)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise SpecialistValidationError(
                f"reserved specialist metadata keys: {names}"
            )
        for value in self.attributes.values():
            _validate_metadata_value(value)
        ordered = {key: self.attributes[key] for key in sorted(self.attributes)}
        object.__setattr__(self, "attributes", MappingProxyType(ordered))

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.correlation_id.value),
            str(self.causation_id.value) if self.causation_id is not None else None,
            tuple(self.attributes.items()),
        )


@dataclass(frozen=True, slots=True)
class SpecialistReasonCode:
    """Código estructurado y estable de una razón especializada."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9.-]*", self.value
        ) is None:
            raise SpecialistValidationError(
                "specialist reason code must use lowercase letters, digits, dots, or hyphens"
            )


@dataclass(frozen=True, slots=True)
class SpecialistReason:
    """Razón estructurada de un análisis especializado."""

    code: SpecialistReasonCode
    summary: str
    attributes: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.code, SpecialistReasonCode):
            raise SpecialistValidationError(
                "specialist reason code must be a SpecialistReasonCode"
            )
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise SpecialistValidationError(
                "specialist reason summary must not be empty"
            )
        if not isinstance(self.attributes, Mapping):
            raise SpecialistValidationError(
                "specialist reason attributes must be a mapping"
            )
        if any(not isinstance(key, str) or not key.strip() for key in self.attributes):
            raise SpecialistValidationError(
                "specialist reason attribute keys must be non-empty strings"
            )
        for value in self.attributes.values():
            _validate_metadata_value(value)
        ordered = {key: self.attributes[key] for key in sorted(self.attributes)}
        object.__setattr__(self, "attributes", MappingProxyType(ordered))

    def logical_values(self) -> tuple[object, ...]:
        return (self.code.value, self.summary, tuple(self.attributes.items()))


@dataclass(frozen=True, slots=True)
class SpecialistAnalysis:
    """Resultado especializado común, explícito, inmutable y determinista."""

    analysis_id: SpecialistAnalysisId
    timestamp: datetime
    kind: SpecialistKind
    status: SpecialistAnalysisStatus
    metadata: SpecialistMetadata
    confidence: SpecialistConfidence | None = None
    reasons: tuple[SpecialistReason, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.analysis_id, SpecialistAnalysisId):
            raise SpecialistValidationError(
                "specialist analysis_id must be a SpecialistAnalysisId"
            )
        if not is_timezone_aware_datetime(self.timestamp):
            raise SpecialistValidationError(
                "specialist timestamp must be a timezone-aware datetime"
            )
        if not isinstance(self.kind, SpecialistKind):
            raise SpecialistValidationError("specialist kind must be a SpecialistKind")
        if not isinstance(self.status, SpecialistAnalysisStatus):
            raise SpecialistValidationError(
                "specialist status must be a SpecialistAnalysisStatus"
            )
        if not isinstance(self.metadata, SpecialistMetadata):
            raise SpecialistValidationError(
                "specialist metadata must be SpecialistMetadata"
            )
        if self.confidence is not None and not isinstance(
            self.confidence, SpecialistConfidence
        ):
            raise SpecialistValidationError(
                "specialist confidence must be SpecialistConfidence or None"
            )
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(reason, SpecialistReason) for reason in self.reasons
        ):
            raise SpecialistValidationError(
                "specialist reasons must be an immutable tuple of SpecialistReason values"
            )
        if self.status is SpecialistAnalysisStatus.PENDING:
            if self.confidence is not None:
                raise SpecialistValidationError(
                    "pending specialist analysis must not have confidence"
                )
            if self.reasons:
                raise SpecialistValidationError(
                    "pending specialist analysis must not have final reasons"
                )
        if self.status is SpecialistAnalysisStatus.COMPLETED:
            if self.confidence is None:
                raise SpecialistValidationError(
                    "completed specialist analysis must have confidence"
                )
            if not self.reasons:
                raise SpecialistValidationError(
                    "completed specialist analysis must include at least one reason"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.analysis_id.value),
            canonical_instant(self.timestamp),
            self.kind.value,
            self.status.value,
            self.metadata.logical_values(),
            self.confidence.value if self.confidence is not None else None,
            tuple(reason.logical_values() for reason in self.reasons),
        )
