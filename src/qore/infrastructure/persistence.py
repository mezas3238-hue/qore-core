from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch
from typing import Protocol

from qore.infrastructure.ports import (
    ExternalPort,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.kernel.result import Result


class PersistenceError(ExternalPortError):
    """Base error for persistence infrastructure boundaries."""

    __slots__ = ()


class PersistenceValidationError(PersistenceError):
    """Violation of a persistence contract invariant."""

    __slots__ = ()


class PersistenceConflictError(PersistenceError):
    """Typed optimistic-concurrency conflict at a persistence boundary."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class PersistenceKey:
    """Canonical typed key for one persisted internal value."""

    namespace: str
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.namespace, str) or fullmatch(
            r"[a-z][a-z0-9.-]*", self.namespace
        ) is None:
            raise PersistenceValidationError(
                "persistence key namespace must use lowercase letters, digits, dots, or hyphens"
            )
        if not isinstance(self.value, str) or fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:/-]*", self.value
        ) is None:
            raise PersistenceValidationError(
                "persistence key value must be a non-empty canonical token"
            )

    def logical_values(self) -> tuple[str, str]:
        return (self.namespace, self.value)


@dataclass(frozen=True, slots=True, order=True)
class PersistenceVersion:
    """Explicit zero-based version for persisted values."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 0:
            raise PersistenceValidationError(
                "persistence version must be a non-negative int"
            )

    def next(self) -> PersistenceVersion:
        """Return the deterministic successor without mutating this version."""
        return PersistenceVersion(self.value + 1)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise PersistenceValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise PersistenceValidationError(f"{field_name} must be timezone-aware")


def _validate_persistence_source(
    source: ExternalSourceDescriptor,
    *,
    field_name: str,
) -> None:
    if not isinstance(source, ExternalSourceDescriptor):
        raise PersistenceValidationError(
            f"{field_name} source must be ExternalSourceDescriptor"
        )
    name = source.port_name.value
    if name != "persistence" and not name.startswith("persistence."):
        raise PersistenceValidationError(
            f"{field_name} source port must use the persistence namespace"
        )


@dataclass(frozen=True, slots=True)
class StoredRecord[ValueT]:
    """Typed persisted record with explicit source, time, key and version."""

    key: PersistenceKey
    version: PersistenceVersion
    value: ValueT
    source: ExternalSourceDescriptor
    stored_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.key, PersistenceKey):
            raise PersistenceValidationError(
                "stored record key must be PersistenceKey"
            )
        if not isinstance(self.version, PersistenceVersion):
            raise PersistenceValidationError(
                "stored record version must be PersistenceVersion"
            )
        _validate_persistence_source(self.source, field_name="stored record")
        _validate_timestamp(self.stored_at, field_name="stored record stored_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.key.logical_values(),
            self.version.value,
            self.source.logical_values(),
            self.stored_at.isoformat(),
            self.value,
        )


@dataclass(frozen=True, slots=True)
class LoadPersistenceRequest:
    """Typed request for one persisted value by canonical key."""

    key: PersistenceKey

    def __post_init__(self) -> None:
        if not isinstance(self.key, PersistenceKey):
            raise PersistenceValidationError(
                "load request key must be PersistenceKey"
            )


@dataclass(frozen=True, slots=True)
class SavePersistenceRequest[ValueT]:
    """Typed create/update request with explicit optimistic version semantics."""

    record: StoredRecord[ValueT]
    expected_version: PersistenceVersion | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.record, StoredRecord):
            raise PersistenceValidationError(
                "save request record must be StoredRecord"
            )
        if self.expected_version is not None and not isinstance(
            self.expected_version, PersistenceVersion
        ):
            raise PersistenceValidationError(
                "save request expected_version must be PersistenceVersion or None"
            )
        if self.expected_version is None:
            if self.record.version.value != 0:
                raise PersistenceValidationError(
                    "create save request must use record version 0"
                )
            return
        if self.record.version != self.expected_version.next():
            raise PersistenceValidationError(
                "update record version must equal expected_version + 1"
            )


class PersistencePort[ValueT](ExternalPort, Protocol):
    """Provider-neutral typed persistence store boundary."""

    def load(
        self,
        request: LoadPersistenceRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[StoredRecord[ValueT] | None, ExternalPortError]:
        """Load a value or return Success(None) when the key is absent."""
        ...

    def save(
        self,
        request: SavePersistenceRequest[ValueT],
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[PersistenceVersion, ExternalPortError]:
        """Persist exactly the explicit record version or return a typed failure."""
        ...
