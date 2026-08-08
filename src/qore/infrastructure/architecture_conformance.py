from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password",
    "secret",
    "token",
)


class ArchitectureConformanceError(ExternalPortError):
    """Base error for PHASE-13 architecture conformance evidence."""

    __slots__ = ()


class ArchitectureConformanceValidationError(ArchitectureConformanceError):
    """Violation of architecture conformance evidence invariants."""

    __slots__ = ()


class ArchitectureConformanceCheck(StrEnum):
    CORE_ISOLATION = "core_isolation"
    DEPENDENCY_DIRECTION = "dependency_direction"
    IMMUTABLE_CONTRACTS = "immutable_contracts"
    DETERMINISTIC_TIME_IDENTITY = "deterministic_time_identity"
    TYPED_FAILURES = "typed_failures"
    EXECUTION_BOUNDARY = "execution_boundary"
    SECRET_SAFETY = "secret_safety"


class ArchitectureConformanceStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class ArchitectureConformanceVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"


_REQUIRED_CHECKS: tuple[ArchitectureConformanceCheck, ...] = tuple(
    ArchitectureConformanceCheck
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ArchitectureConformanceValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ArchitectureConformanceValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str) -> None:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ArchitectureConformanceValidationError(
            "architecture evidence code must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ArchitectureConformanceValidationError(
            "architecture evidence code must not contain sensitive material"
        )


@dataclass(frozen=True, slots=True)
class ArchitectureConformanceRecord:
    check: ArchitectureConformanceCheck
    status: ArchitectureConformanceStatus
    observed_at: datetime
    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.check, ArchitectureConformanceCheck):
            raise ArchitectureConformanceValidationError(
                "architecture check must be ArchitectureConformanceCheck"
            )
        if not isinstance(self.status, ArchitectureConformanceStatus):
            raise ArchitectureConformanceValidationError(
                "architecture status must be ArchitectureConformanceStatus"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        _validate_code(self.code)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.check.value,
            self.status.value,
            self.observed_at.isoformat(),
            self.code,
        )


@dataclass(frozen=True, slots=True)
class ArchitectureConformanceEvidence:
    evaluated_at: datetime
    records: tuple[ArchitectureConformanceRecord, ...]
    verdict: ArchitectureConformanceVerdict

    def __post_init__(self) -> None:
        _validate_timestamp(self.evaluated_at, field_name="evaluated_at")
        if not isinstance(self.records, tuple):
            raise ArchitectureConformanceValidationError(
                "architecture records must be a tuple"
            )
        if not isinstance(self.verdict, ArchitectureConformanceVerdict):
            raise ArchitectureConformanceValidationError(
                "architecture verdict must be ArchitectureConformanceVerdict"
            )
        checks = tuple(record.check for record in self.records)
        if checks != _REQUIRED_CHECKS:
            raise ArchitectureConformanceValidationError(
                "architecture evidence must contain every required check exactly once"
            )
        if any(record.observed_at > self.evaluated_at for record in self.records):
            raise ArchitectureConformanceValidationError(
                "architecture evidence must not postdate evaluation"
            )
        expected = (
            ArchitectureConformanceVerdict.PASS
            if all(
                record.status is ArchitectureConformanceStatus.PASS
                for record in self.records
            )
            else ArchitectureConformanceVerdict.FAIL
        )
        if self.verdict is not expected:
            raise ArchitectureConformanceValidationError(
                "architecture verdict does not match record statuses"
            )

    @property
    def passed(self) -> bool:
        return self.verdict is ArchitectureConformanceVerdict.PASS

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evaluated_at.isoformat(),
            tuple(record.logical_values() for record in self.records),
            self.verdict.value,
        )


def aggregate_architecture_conformance(
    records: tuple[ArchitectureConformanceRecord, ...],
    *,
    evaluated_at: datetime,
) -> Result[ArchitectureConformanceEvidence, ArchitectureConformanceError]:
    if not isinstance(records, tuple) or any(
        not isinstance(record, ArchitectureConformanceRecord) for record in records
    ):
        return Failure(
            ArchitectureConformanceValidationError(
                "records must be ArchitectureConformanceRecord values in a tuple"
            )
        )
    by_check: dict[ArchitectureConformanceCheck, ArchitectureConformanceRecord] = {}
    for record in records:
        if record.check in by_check:
            return Failure(
                ArchitectureConformanceValidationError(
                    "duplicate architecture conformance check is not allowed"
                )
            )
        by_check[record.check] = record
    if set(by_check) != set(_REQUIRED_CHECKS):
        return Failure(
            ArchitectureConformanceValidationError(
                "architecture conformance evidence is incomplete"
            )
        )
    ordered = tuple(by_check[check] for check in _REQUIRED_CHECKS)
    verdict = (
        ArchitectureConformanceVerdict.PASS
        if all(
            record.status is ArchitectureConformanceStatus.PASS
            for record in ordered
        )
        else ArchitectureConformanceVerdict.FAIL
    )
    try:
        return Success(
            ArchitectureConformanceEvidence(
                evaluated_at=evaluated_at,
                records=ordered,
                verdict=verdict,
            )
        )
    except ArchitectureConformanceError as error:
        return Failure(error)
