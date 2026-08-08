from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata
from qore.kernel.result import Failure, Result, Success

_FORBIDDEN_ACTION_PARTS = ("broker", "execution", "order", "position", "trade")
_SENSITIVE_KEY_PARTS = (
    "api-key",
    "api_key",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)
_SENSITIVE_TEXT_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret=",
    "password=",
    "secret=",
    "token=",
)


class OperationsAuditError(ExternalPortError):
    """Base error for PHASE-10 operational audit contracts."""

    __slots__ = ()


class OperationsAuditValidationError(OperationsAuditError):
    """Violation of an operational audit invariant."""

    __slots__ = ()


class OperationsAuditConflictError(OperationsAuditError):
    """Typed conflict when an audit id is reused with different content."""

    __slots__ = ()


class OperationsAuditCategory(StrEnum):
    CONFIGURATION = "configuration"
    PERSISTENCE = "persistence"
    RUNTIME = "runtime"
    CONNECTIVITY = "connectivity"
    SECURITY = "security"


class OperationsAuditOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class OperationsAuditRecordId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise OperationsAuditValidationError(
                "operations audit record id must be UUID"
            )

    def logical_values(self) -> tuple[UUID, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class OperationsAuditAction:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.value
        ) is None:
            raise OperationsAuditValidationError(
                "operations audit action must use canonical lowercase syntax"
            )
        normalized = self.value.replace("-", ".")
        segments = tuple(part for part in normalized.split(".") if part)
        if any(part in segments for part in _FORBIDDEN_ACTION_PARTS):
            raise OperationsAuditValidationError(
                "PHASE-10 operations audit action must not describe trading execution"
            )
        if any(part in self.value for part in _SENSITIVE_KEY_PARTS):
            raise OperationsAuditValidationError(
                "operations audit action must not contain secret-like terms"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _validate_value(value: DomainMetadataValue) -> None:
    if value is None or isinstance(value, (bool, int, UUID)):
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise OperationsAuditValidationError(
                "operations audit floats must be finite"
            )
        return
    if isinstance(value, str):
        normalized = value.lower()
        if any(part in normalized for part in _SENSITIVE_TEXT_PARTS):
            raise OperationsAuditValidationError(
                "operations audit values must not contain sensitive material"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_value(item)
        return
    raise OperationsAuditValidationError(
        "operations audit values must be immutable metadata values"
    )


def _validated_attributes(
    attributes: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(attributes, Mapping):
        raise OperationsAuditValidationError(
            "operations audit attributes must be a mapping"
        )
    ordered: dict[str, DomainMetadataValue] = {}
    for key in sorted(attributes):
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise OperationsAuditValidationError(
                "operations audit attribute keys must use canonical lowercase syntax"
            )
        if any(part in key for part in _SENSITIVE_KEY_PARTS):
            raise OperationsAuditValidationError(
                "operations audit attributes must not contain secret-like keys"
            )
        value = attributes[key]
        _validate_value(value)
        ordered[key] = value
    return MappingProxyType(ordered)


@dataclass(frozen=True, slots=True)
class OperationsAuditRecord:
    """Immutable sanitized operational audit record."""

    record_id: OperationsAuditRecordId
    category: OperationsAuditCategory
    action: OperationsAuditAction
    outcome: OperationsAuditOutcome
    recorded_at: datetime
    metadata: ExternalRequestMetadata
    attributes: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, OperationsAuditRecordId):
            raise OperationsAuditValidationError(
                "operations audit record_id must be OperationsAuditRecordId"
            )
        if not isinstance(self.category, OperationsAuditCategory):
            raise OperationsAuditValidationError(
                "operations audit category must be OperationsAuditCategory"
            )
        if not isinstance(self.action, OperationsAuditAction):
            raise OperationsAuditValidationError(
                "operations audit action must be OperationsAuditAction"
            )
        if not isinstance(self.outcome, OperationsAuditOutcome):
            raise OperationsAuditValidationError(
                "operations audit outcome must be OperationsAuditOutcome"
            )
        if not isinstance(self.recorded_at, datetime):
            raise OperationsAuditValidationError(
                "operations audit recorded_at must be a datetime"
            )
        if self.recorded_at.tzinfo is None or self.recorded_at.utcoffset() is None:
            raise OperationsAuditValidationError(
                "operations audit recorded_at must be timezone-aware"
            )
        if not isinstance(self.metadata, ExternalRequestMetadata):
            raise OperationsAuditValidationError(
                "operations audit metadata must be ExternalRequestMetadata"
            )
        object.__setattr__(
            self,
            "attributes",
            _validated_attributes(self.attributes),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.category.value,
            self.action.logical_values(),
            self.outcome.value,
            self.recorded_at.isoformat(),
            self.metadata.logical_values(),
            tuple(self.attributes.items()),
        )


class OperationsAuditBoundary(Protocol):
    """Append-only operational audit sink boundary."""

    def append(
        self,
        record: OperationsAuditRecord,
    ) -> Result[OperationsAuditRecord, OperationsAuditError]: ...


class InMemoryOperationsAuditSink:
    """Deterministic append-only reference sink with instance-local state."""

    __slots__ = ("_records",)

    def __init__(self) -> None:
        self._records: dict[OperationsAuditRecordId, OperationsAuditRecord] = {}

    @property
    def records(self) -> tuple[OperationsAuditRecord, ...]:
        return tuple(
            self._records[key]
            for key in sorted(self._records, key=lambda item: str(item.value))
        )

    def append(
        self,
        record: OperationsAuditRecord,
    ) -> Result[OperationsAuditRecord, OperationsAuditError]:
        if not isinstance(record, OperationsAuditRecord):
            return Failure(
                OperationsAuditValidationError(
                    "operations audit append requires OperationsAuditRecord"
                )
            )
        prior = self._records.get(record.record_id)
        if prior is not None:
            if prior != record:
                return Failure(
                    OperationsAuditConflictError(
                        "operations audit record id reused with different content"
                    )
                )
            return Success(prior)
        self._records[record.record_id] = record
        return Success(record)
