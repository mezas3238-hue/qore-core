from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_TEXT_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret=",
    "password=",
    "secret=",
    "token=",
)


class RealMarketTestValidationError(ExternalPortError):
    """Base error for MISSION-02 end-to-end validation evidence."""

    __slots__ = ()


class RealMarketTestValidationInvariantError(RealMarketTestValidationError):
    """Violation of deterministic MISSION-02 closure evidence invariants."""

    __slots__ = ()


class RealMarketTestCheck(StrEnum):
    CORE_ISOLATION = "core_isolation"
    ENVIRONMENT_SEPARATION = "environment_separation"
    MARKET_DATA_FLOW = "market_data_flow"
    TEST_DEMO_EXECUTION = "test_demo_execution"
    IDEMPOTENCY = "idempotency"
    PRE_EXECUTION_BLOCKING = "pre_execution_blocking"
    FAILURE_CONTAINMENT = "failure_containment"
    RECONCILIATION_SAFETY = "reconciliation_safety"
    CIBO_SUPERVISION = "cibo_supervision"
    SECRET_SAFE_OBSERVABILITY = "secret_safe_observability"
    PRODUCTION_DISABLED = "production_disabled"


class RealMarketTestCheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


_REQUIRED_CHECKS = tuple(sorted(RealMarketTestCheck, key=lambda item: item.value))


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise RealMarketTestValidationInvariantError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise RealMarketTestValidationInvariantError(
            f"{field_name} must be timezone-aware"
        )


def _validate_public_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RealMarketTestValidationInvariantError(
            f"{field_name} must be non-empty"
        )
    lowered = value.lower()
    if any(part in lowered for part in _SENSITIVE_TEXT_PARTS):
        raise RealMarketTestValidationInvariantError(
            f"{field_name} must not contain sensitive material"
        )


@dataclass(frozen=True, slots=True)
class RealMarketTestEvidenceRecord:
    check: RealMarketTestCheck
    status: RealMarketTestCheckStatus
    evaluated_at: datetime
    evidence: str

    def __post_init__(self) -> None:
        if not isinstance(self.check, RealMarketTestCheck):
            raise RealMarketTestValidationInvariantError(
                "evidence check must be RealMarketTestCheck"
            )
        if not isinstance(self.status, RealMarketTestCheckStatus):
            raise RealMarketTestValidationInvariantError(
                "evidence status must be RealMarketTestCheckStatus"
            )
        _validate_timestamp(self.evaluated_at, field_name="evaluated_at")
        _validate_public_text(self.evidence, field_name="evidence")

    def logical_values(self) -> tuple[str, str, str, str]:
        return (
            self.check.value,
            self.status.value,
            self.evaluated_at.isoformat(),
            self.evidence,
        )


@dataclass(frozen=True, slots=True)
class RealMarketTestValidationResult:
    records: tuple[RealMarketTestEvidenceRecord, ...]
    validated_at: datetime
    status: RealMarketTestCheckStatus

    def __post_init__(self) -> None:
        _validate_timestamp(self.validated_at, field_name="validated_at")
        if not isinstance(self.status, RealMarketTestCheckStatus):
            raise RealMarketTestValidationInvariantError(
                "validation status must be RealMarketTestCheckStatus"
            )
        if not isinstance(self.records, tuple):
            raise RealMarketTestValidationInvariantError(
                "validation records must be a tuple"
            )
        checks = tuple(record.check for record in self.records)
        if checks != _REQUIRED_CHECKS:
            raise RealMarketTestValidationInvariantError(
                "validation requires every MISSION-02 check exactly once in stable order"
            )
        if any(record.evaluated_at > self.validated_at for record in self.records):
            raise RealMarketTestValidationInvariantError(
                "validation records must not postdate validated_at"
            )
        expected = (
            RealMarketTestCheckStatus.PASS
            if all(
                record.status is RealMarketTestCheckStatus.PASS
                for record in self.records
            )
            else RealMarketTestCheckStatus.FAIL
        )
        if self.status is not expected:
            raise RealMarketTestValidationInvariantError(
                "validation status must equal aggregate record status"
            )

    @property
    def passed(self) -> bool:
        return self.status is RealMarketTestCheckStatus.PASS

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(record.logical_values() for record in self.records),
            self.validated_at.isoformat(),
            self.status.value,
        )


def validate_real_market_test_evidence(
    records: tuple[RealMarketTestEvidenceRecord, ...],
    *,
    validated_at: datetime,
) -> Result[RealMarketTestValidationResult, RealMarketTestValidationError]:
    if not isinstance(records, tuple):
        return Failure(
            RealMarketTestValidationInvariantError(
                "real-market test validation requires a tuple of records"
            )
        )
    if any(not isinstance(record, RealMarketTestEvidenceRecord) for record in records):
        return Failure(
            RealMarketTestValidationInvariantError(
                "real-market test records must be RealMarketTestEvidenceRecord"
            )
        )
    ordered = tuple(sorted(records, key=lambda record: record.check.value))
    status = (
        RealMarketTestCheckStatus.PASS
        if all(record.status is RealMarketTestCheckStatus.PASS for record in ordered)
        else RealMarketTestCheckStatus.FAIL
    )
    try:
        result = RealMarketTestValidationResult(
            records=ordered,
            validated_at=validated_at,
            status=status,
        )
    except RealMarketTestValidationError as error:
        return Failure(error)
    return Success(result)
