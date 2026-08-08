from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.execution_orchestration import ExecutionOrchestrationId
from qore.infrastructure.order_intent import OrderIntentId
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


class TradingSafetyEvidenceError(ExternalPortError):
    """Base error for deterministic trading safety evidence."""

    __slots__ = ()


class TradingSafetyEvidenceValidationError(TradingSafetyEvidenceError):
    """Violation of safety evidence invariants."""

    __slots__ = ()


class TradingSafetyCheck(StrEnum):
    AUTHORIZATION = "authorization"
    SWITCH = "switch"
    IDEMPOTENCY = "idempotency"
    RECONCILIATION = "reconciliation"
    CONTAINMENT = "containment"


class TradingSafetyCheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class TradingSafetyVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"


_REQUIRED_CHECKS: tuple[TradingSafetyCheck, ...] = (
    TradingSafetyCheck.AUTHORIZATION,
    TradingSafetyCheck.SWITCH,
    TradingSafetyCheck.IDEMPOTENCY,
    TradingSafetyCheck.RECONCILIATION,
    TradingSafetyCheck.CONTAINMENT,
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TradingSafetyEvidenceValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise TradingSafetyEvidenceValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str) -> None:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise TradingSafetyEvidenceValidationError(
            "safety evidence code must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise TradingSafetyEvidenceValidationError(
            "safety evidence code must not contain sensitive material"
        )


@dataclass(frozen=True, slots=True)
class TradingSafetyEvidenceRecord:
    check: TradingSafetyCheck
    status: TradingSafetyCheckStatus
    observed_at: datetime
    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.check, TradingSafetyCheck):
            raise TradingSafetyEvidenceValidationError(
                "safety evidence check must be TradingSafetyCheck"
            )
        if not isinstance(self.status, TradingSafetyCheckStatus):
            raise TradingSafetyEvidenceValidationError(
                "safety evidence status must be TradingSafetyCheckStatus"
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
class TradingSafetyEvidenceBundle:
    orchestration_id: ExecutionOrchestrationId
    intent_id: OrderIntentId
    evaluated_at: datetime
    records: tuple[TradingSafetyEvidenceRecord, ...]
    verdict: TradingSafetyVerdict

    def __post_init__(self) -> None:
        if not isinstance(self.orchestration_id, ExecutionOrchestrationId):
            raise TradingSafetyEvidenceValidationError(
                "orchestration_id must be ExecutionOrchestrationId"
            )
        if not isinstance(self.intent_id, OrderIntentId):
            raise TradingSafetyEvidenceValidationError(
                "intent_id must be OrderIntentId"
            )
        _validate_timestamp(self.evaluated_at, field_name="evaluated_at")
        if not isinstance(self.records, tuple):
            raise TradingSafetyEvidenceValidationError(
                "safety evidence records must be a tuple"
            )
        if not isinstance(self.verdict, TradingSafetyVerdict):
            raise TradingSafetyEvidenceValidationError(
                "safety evidence verdict must be TradingSafetyVerdict"
            )
        checks = tuple(record.check for record in self.records)
        if checks != _REQUIRED_CHECKS:
            raise TradingSafetyEvidenceValidationError(
                "safety evidence must contain every required check exactly once"
            )
        if any(record.observed_at > self.evaluated_at for record in self.records):
            raise TradingSafetyEvidenceValidationError(
                "safety evidence record must not postdate evaluation"
            )
        expected_verdict = (
            TradingSafetyVerdict.PASS
            if all(
                record.status is TradingSafetyCheckStatus.PASS
                for record in self.records
            )
            else TradingSafetyVerdict.FAIL
        )
        if self.verdict is not expected_verdict:
            raise TradingSafetyEvidenceValidationError(
                "safety evidence verdict does not match check statuses"
            )

    @property
    def passed(self) -> bool:
        return self.verdict is TradingSafetyVerdict.PASS

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.orchestration_id.logical_values(),
            self.intent_id.logical_values(),
            self.evaluated_at.isoformat(),
            tuple(record.logical_values() for record in self.records),
            self.verdict.value,
        )


def aggregate_trading_safety_evidence(
    orchestration_id: ExecutionOrchestrationId,
    intent_id: OrderIntentId,
    records: tuple[TradingSafetyEvidenceRecord, ...],
    *,
    evaluated_at: datetime,
) -> Result[TradingSafetyEvidenceBundle, TradingSafetyEvidenceError]:
    if not isinstance(records, tuple) or any(
        not isinstance(record, TradingSafetyEvidenceRecord) for record in records
    ):
        return Failure(
            TradingSafetyEvidenceValidationError(
                "records must be TradingSafetyEvidenceRecord values in a tuple"
            )
        )
    by_check: dict[TradingSafetyCheck, TradingSafetyEvidenceRecord] = {}
    for record in records:
        if record.check in by_check:
            return Failure(
                TradingSafetyEvidenceValidationError(
                    "duplicate safety evidence check is not allowed"
                )
            )
        by_check[record.check] = record
    if set(by_check) != set(_REQUIRED_CHECKS):
        return Failure(
            TradingSafetyEvidenceValidationError(
                "safety evidence is incomplete"
            )
        )
    ordered_records = tuple(by_check[check] for check in _REQUIRED_CHECKS)
    verdict = (
        TradingSafetyVerdict.PASS
        if all(
            record.status is TradingSafetyCheckStatus.PASS
            for record in ordered_records
        )
        else TradingSafetyVerdict.FAIL
    )
    try:
        return Success(
            TradingSafetyEvidenceBundle(
                orchestration_id=orchestration_id,
                intent_id=intent_id,
                evaluated_at=evaluated_at,
                records=ordered_records,
                verdict=verdict,
            )
        )
    except TradingSafetyEvidenceError as error:
        return Failure(error)
