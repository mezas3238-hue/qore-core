from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from re import fullmatch
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from qore.domain.events import DomainMetadataValue
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_FORBIDDEN_KEY_PARTS = (
    "broker",
    "execution",
    "order",
    "position",
    "trade",
)
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


class OperationalPersistenceError(ExternalPortError):
    """Base error for PHASE-10 operational persistence."""

    __slots__ = ()


class OperationalPersistenceValidationError(OperationalPersistenceError):
    """Violation of an operational persistence contract invariant."""

    __slots__ = ()


class OperationalPersistenceConflictError(OperationalPersistenceError):
    """Typed conflict for version or idempotency mismatches."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class OperationalRecordKey:
    """Non-trading namespace/key for persisted operational state."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]*", self.value
        ) is None:
            raise OperationalPersistenceValidationError(
                "operational record key must use canonical lowercase syntax"
            )
        segments = tuple(part for part in self.value.replace("-", ".").split(".") if part)
        if any(forbidden in segments for forbidden in _FORBIDDEN_KEY_PARTS):
            raise OperationalPersistenceValidationError(
                "operational persistence must not use trading namespaces"
            )
        if any(part in self.value for part in _SENSITIVE_KEY_PARTS):
            raise OperationalPersistenceValidationError(
                "operational record key must not contain secret-like terms"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class OperationalIdempotencyKey:
    """Explicit stable identity for one operational write intent."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise OperationalPersistenceValidationError(
                "operational idempotency key must be UUID"
            )

    def logical_values(self) -> tuple[UUID, ...]:
        return (self.value,)


def _validate_value(value: DomainMetadataValue) -> None:
    if value is None or isinstance(value, (bool, int, UUID)):
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise OperationalPersistenceValidationError(
                "operational persistence floats must be finite"
            )
        return
    if isinstance(value, str):
        normalized = value.lower()
        if any(part in normalized for part in _SENSITIVE_TEXT_PARTS):
            raise OperationalPersistenceValidationError(
                "operational persistence values must not contain sensitive material"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_value(item)
        return
    raise OperationalPersistenceValidationError(
        "operational persistence values must be immutable metadata values"
    )


def _validated_values(
    values: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(values, Mapping):
        raise OperationalPersistenceValidationError(
            "operational persistence values must be a mapping"
        )
    ordered: dict[str, DomainMetadataValue] = {}
    for key in sorted(values):
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise OperationalPersistenceValidationError(
                "operational persistence value keys must use canonical lowercase syntax"
            )
        if any(part in key for part in _SENSITIVE_KEY_PARTS):
            raise OperationalPersistenceValidationError(
                "operational persistence values must not contain secret-like keys"
            )
        value = values[key]
        _validate_value(value)
        ordered[key] = value
    return MappingProxyType(ordered)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise OperationalPersistenceValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise OperationalPersistenceValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class OperationalWriteRequest:
    """Versioned idempotent write intent for non-trading operational state."""

    key: OperationalRecordKey
    idempotency_key: OperationalIdempotencyKey
    expected_version: int
    persisted_at: datetime
    values: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.key, OperationalRecordKey):
            raise OperationalPersistenceValidationError(
                "operational write key must be OperationalRecordKey"
            )
        if not isinstance(self.idempotency_key, OperationalIdempotencyKey):
            raise OperationalPersistenceValidationError(
                "operational write idempotency_key must be OperationalIdempotencyKey"
            )
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise OperationalPersistenceValidationError(
                "operational write expected_version must be a non-negative int"
            )
        _validate_timestamp(self.persisted_at, field_name="persisted_at")
        object.__setattr__(self, "values", _validated_values(self.values))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.key.logical_values(),
            self.idempotency_key.logical_values(),
            self.expected_version,
            self.persisted_at.isoformat(),
            tuple(self.values.items()),
        )


@dataclass(frozen=True, slots=True)
class OperationalRecordSnapshot:
    key: OperationalRecordKey
    version: int
    persisted_at: datetime
    values: Mapping[str, DomainMetadataValue] = field(compare=True, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.key, OperationalRecordKey):
            raise OperationalPersistenceValidationError(
                "operational snapshot key must be OperationalRecordKey"
            )
        if type(self.version) is not int or self.version < 1:
            raise OperationalPersistenceValidationError(
                "operational snapshot version must be a positive int"
            )
        _validate_timestamp(self.persisted_at, field_name="persisted_at")
        object.__setattr__(self, "values", _validated_values(self.values))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.key.logical_values(),
            self.version,
            self.persisted_at.isoformat(),
            tuple(self.values.items()),
        )


@dataclass(frozen=True, slots=True)
class OperationalWriteReceipt:
    """Stable receipt returned for both first application and idempotent replay."""

    idempotency_key: OperationalIdempotencyKey
    record: OperationalRecordSnapshot

    def logical_values(self) -> tuple[object, ...]:
        return (self.idempotency_key.logical_values(), self.record.logical_values())


class OperationalPersistenceBoundary(Protocol):
    """Side-effect boundary for operational state; concrete storage remains injected."""

    def write(
        self,
        request: OperationalWriteRequest,
    ) -> Result[OperationalWriteReceipt, OperationalPersistenceError]: ...

    def read(
        self,
        key: OperationalRecordKey,
    ) -> Result[OperationalRecordSnapshot | None, OperationalPersistenceError]: ...


class InMemoryOperationalPersistence:
    """Deterministic reference store with no global state or external IO."""

    __slots__ = ("_idempotency", "_records")

    def __init__(self) -> None:
        self._records: dict[OperationalRecordKey, OperationalRecordSnapshot] = {}
        self._idempotency: dict[
            OperationalIdempotencyKey,
            tuple[tuple[object, ...], OperationalWriteReceipt],
        ] = {}

    def write(
        self,
        request: OperationalWriteRequest,
    ) -> Result[OperationalWriteReceipt, OperationalPersistenceError]:
        if not isinstance(request, OperationalWriteRequest):
            return Failure(
                OperationalPersistenceValidationError(
                    "operational persistence write requires OperationalWriteRequest"
                )
            )
        prior = self._idempotency.get(request.idempotency_key)
        if prior is not None:
            logical_request, receipt = prior
            if logical_request != request.logical_values():
                return Failure(
                    OperationalPersistenceConflictError(
                        "operational idempotency key reused with different write intent"
                    )
                )
            return Success(receipt)

        current = self._records.get(request.key)
        current_version = 0 if current is None else current.version
        if request.expected_version != current_version:
            return Failure(
                OperationalPersistenceConflictError(
                    "operational persistence expected_version does not match current version"
                )
            )
        snapshot = OperationalRecordSnapshot(
            key=request.key,
            version=current_version + 1,
            persisted_at=request.persisted_at,
            values=request.values,
        )
        receipt = OperationalWriteReceipt(
            idempotency_key=request.idempotency_key,
            record=snapshot,
        )
        self._records[request.key] = snapshot
        self._idempotency[request.idempotency_key] = (
            request.logical_values(),
            receipt,
        )
        return Success(receipt)

    def read(
        self,
        key: OperationalRecordKey,
    ) -> Result[OperationalRecordSnapshot | None, OperationalPersistenceError]:
        if not isinstance(key, OperationalRecordKey):
            return Failure(
                OperationalPersistenceValidationError(
                    "operational persistence read key must be OperationalRecordKey"
                )
            )
        return Success(self._records.get(key))
