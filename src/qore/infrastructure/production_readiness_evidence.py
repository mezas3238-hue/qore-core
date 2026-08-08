from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success


class ProductionReadinessEvidenceError(ExternalPortError):
    """Base error for PHASE-13 production readiness evidence."""

    __slots__ = ()


class ProductionReadinessEvidenceValidationError(ProductionReadinessEvidenceError):
    """Violation of readiness evidence invariants."""

    __slots__ = ()


class ProductionReadinessCheck(StrEnum):
    CORE_RUNTIME = "core_runtime"
    GOVERNANCE = "governance"
    PROVIDER_BOUNDARY = "provider_boundary"
    OPERATIONS = "operations"
    SANDBOX_EXECUTION = "sandbox_execution"
    SAFETY_VALIDATION = "safety_validation"


class ProductionReadinessStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class ProductionReadinessVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"


_REQUIRED_CHECKS: tuple[ProductionReadinessCheck, ...] = tuple(
    ProductionReadinessCheck
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ProductionReadinessEvidenceValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProductionReadinessEvidenceValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str) -> None:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ProductionReadinessEvidenceValidationError(
            "readiness evidence code must use canonical lowercase syntax"
        )


@dataclass(frozen=True, slots=True)
class ProductionReadinessRecord:
    check: ProductionReadinessCheck
    status: ProductionReadinessStatus
    observed_at: datetime
    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.check, ProductionReadinessCheck):
            raise ProductionReadinessEvidenceValidationError(
                "readiness check must be ProductionReadinessCheck"
            )
        if not isinstance(self.status, ProductionReadinessStatus):
            raise ProductionReadinessEvidenceValidationError(
                "readiness status must be ProductionReadinessStatus"
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
class ProductionReadinessEvidence:
    evaluated_at: datetime
    records: tuple[ProductionReadinessRecord, ...]
    verdict: ProductionReadinessVerdict

    def __post_init__(self) -> None:
        _validate_timestamp(self.evaluated_at, field_name="evaluated_at")
        if not isinstance(self.records, tuple):
            raise ProductionReadinessEvidenceValidationError(
                "readiness records must be a tuple"
            )
        if not isinstance(self.verdict, ProductionReadinessVerdict):
            raise ProductionReadinessEvidenceValidationError(
                "readiness verdict must be ProductionReadinessVerdict"
            )
        checks = tuple(record.check for record in self.records)
        if checks != _REQUIRED_CHECKS:
            raise ProductionReadinessEvidenceValidationError(
                "readiness evidence must contain every required check exactly once"
            )
        if any(record.observed_at > self.evaluated_at for record in self.records):
            raise ProductionReadinessEvidenceValidationError(
                "readiness evidence must not postdate evaluation"
            )
        expected = (
            ProductionReadinessVerdict.PASS
            if all(
                record.status is ProductionReadinessStatus.PASS
                for record in self.records
            )
            else ProductionReadinessVerdict.FAIL
        )
        if self.verdict is not expected:
            raise ProductionReadinessEvidenceValidationError(
                "readiness verdict does not match record statuses"
            )

    @property
    def passed(self) -> bool:
        return self.verdict is ProductionReadinessVerdict.PASS

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evaluated_at.isoformat(),
            tuple(record.logical_values() for record in self.records),
            self.verdict.value,
        )


def aggregate_production_readiness(
    records: tuple[ProductionReadinessRecord, ...],
    *,
    evaluated_at: datetime,
) -> Result[ProductionReadinessEvidence, ProductionReadinessEvidenceError]:
    if not isinstance(records, tuple) or any(
        not isinstance(record, ProductionReadinessRecord) for record in records
    ):
        return Failure(
            ProductionReadinessEvidenceValidationError(
                "records must be ProductionReadinessRecord values in a tuple"
            )
        )
    by_check: dict[ProductionReadinessCheck, ProductionReadinessRecord] = {}
    for record in records:
        if record.check in by_check:
            return Failure(
                ProductionReadinessEvidenceValidationError(
                    "duplicate production readiness check is not allowed"
                )
            )
        by_check[record.check] = record
    if set(by_check) != set(_REQUIRED_CHECKS):
        return Failure(
            ProductionReadinessEvidenceValidationError(
                "production readiness evidence is incomplete"
            )
        )
    ordered = tuple(by_check[check] for check in _REQUIRED_CHECKS)
    verdict = (
        ProductionReadinessVerdict.PASS
        if all(record.status is ProductionReadinessStatus.PASS for record in ordered)
        else ProductionReadinessVerdict.FAIL
    )
    try:
        return Success(
            ProductionReadinessEvidence(
                evaluated_at=evaluated_at,
                records=ordered,
                verdict=verdict,
            )
        )
    except ProductionReadinessEvidenceError as error:
        return Failure(error)
