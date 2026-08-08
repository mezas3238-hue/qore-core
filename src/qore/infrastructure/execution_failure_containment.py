from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.execution_reconciliation import (
    ExecutionReconciliationSnapshot,
    ExecutionReconciliationStatus,
)
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


class ExecutionFailureContainmentError(ExternalPortError):
    """Base error for PHASE-12 execution failure containment."""

    __slots__ = ()


class ExecutionFailureContainmentValidationError(ExecutionFailureContainmentError):
    """Violation of failure-containment invariants."""

    __slots__ = ()


class ExecutionFailureStage(StrEnum):
    PRE_TRADE = "pre_trade"
    SUBMIT = "submit"
    OBSERVATION = "observation"
    RECONCILIATION = "reconciliation"


class ExecutionFailureKind(StrEnum):
    SAFETY_BLOCKED = "safety_blocked"
    SUBMISSION_FAILURE = "submission_failure"
    OBSERVATION_FAILURE = "observation_failure"
    RECONCILIATION_DIVERGED = "reconciliation_diverged"
    RECONCILIATION_MISSING = "reconciliation_missing"
    RECONCILIATION_UNEXPECTED = "reconciliation_unexpected"


class ExecutionContainmentDecision(StrEnum):
    ALLOW_CONTINUE = "allow_continue"
    CONTAIN = "contain"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutionFailureContainmentValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutionFailureContainmentValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ExecutionFailureContainmentValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ExecutionFailureContainmentValidationError(
            f"{field_name} must not contain sensitive material"
        )


@dataclass(frozen=True, slots=True)
class ExecutionFailureSignal:
    stage: ExecutionFailureStage
    kind: ExecutionFailureKind
    observed_at: datetime
    code: str

    def __post_init__(self) -> None:
        if not isinstance(self.stage, ExecutionFailureStage):
            raise ExecutionFailureContainmentValidationError(
                "failure stage must be ExecutionFailureStage"
            )
        if not isinstance(self.kind, ExecutionFailureKind):
            raise ExecutionFailureContainmentValidationError(
                "failure kind must be ExecutionFailureKind"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        _validate_code(self.code, field_name="failure code")
        expected_stage = _EXPECTED_STAGE[self.kind]
        if self.stage is not expected_stage:
            raise ExecutionFailureContainmentValidationError(
                "failure stage does not match failure kind"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.stage.value,
            self.kind.value,
            self.observed_at.isoformat(),
            self.code,
        )


@dataclass(frozen=True, slots=True)
class ExecutionContainmentSnapshot:
    decision: ExecutionContainmentDecision
    evaluated_at: datetime
    reasons: tuple[str, ...]
    source_stage: ExecutionFailureStage | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, ExecutionContainmentDecision):
            raise ExecutionFailureContainmentValidationError(
                "containment decision must be ExecutionContainmentDecision"
            )
        _validate_timestamp(self.evaluated_at, field_name="evaluated_at")
        if not isinstance(self.reasons, tuple):
            raise ExecutionFailureContainmentValidationError(
                "containment reasons must be a tuple"
            )
        for reason in self.reasons:
            _validate_code(reason, field_name="containment reason")
        if self.source_stage is not None and not isinstance(
            self.source_stage, ExecutionFailureStage
        ):
            raise ExecutionFailureContainmentValidationError(
                "source_stage must be ExecutionFailureStage or None"
            )
        if self.decision is ExecutionContainmentDecision.ALLOW_CONTINUE:
            if self.reasons or self.source_stage is not None:
                raise ExecutionFailureContainmentValidationError(
                    "allow-continue containment must carry no failure evidence"
                )
        elif not self.reasons:
            raise ExecutionFailureContainmentValidationError(
                "contain decision requires at least one reason"
            )

    @property
    def contained(self) -> bool:
        return self.decision is ExecutionContainmentDecision.CONTAIN

    @property
    def requires_manual_action(self) -> bool:
        return self.contained

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.decision.value,
            self.evaluated_at.isoformat(),
            self.reasons,
            self.source_stage.value if self.source_stage is not None else None,
        )


_EXPECTED_STAGE: dict[ExecutionFailureKind, ExecutionFailureStage] = {
    ExecutionFailureKind.SAFETY_BLOCKED: ExecutionFailureStage.PRE_TRADE,
    ExecutionFailureKind.SUBMISSION_FAILURE: ExecutionFailureStage.SUBMIT,
    ExecutionFailureKind.OBSERVATION_FAILURE: ExecutionFailureStage.OBSERVATION,
    ExecutionFailureKind.RECONCILIATION_DIVERGED: ExecutionFailureStage.RECONCILIATION,
    ExecutionFailureKind.RECONCILIATION_MISSING: ExecutionFailureStage.RECONCILIATION,
    ExecutionFailureKind.RECONCILIATION_UNEXPECTED: ExecutionFailureStage.RECONCILIATION,
}

_RECONCILIATION_KIND: dict[ExecutionReconciliationStatus, ExecutionFailureKind] = {
    ExecutionReconciliationStatus.DIVERGED: ExecutionFailureKind.RECONCILIATION_DIVERGED,
    ExecutionReconciliationStatus.MISSING: ExecutionFailureKind.RECONCILIATION_MISSING,
    ExecutionReconciliationStatus.UNEXPECTED: ExecutionFailureKind.RECONCILIATION_UNEXPECTED,
}


def contain_execution_failure(
    signal: ExecutionFailureSignal,
    *,
    evaluated_at: datetime,
) -> Result[ExecutionContainmentSnapshot, ExecutionFailureContainmentError]:
    if not isinstance(signal, ExecutionFailureSignal):
        return Failure(
            ExecutionFailureContainmentValidationError(
                "signal must be ExecutionFailureSignal"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="evaluated_at")
    except ExecutionFailureContainmentError as error:
        return Failure(error)
    if evaluated_at < signal.observed_at:
        return Failure(
            ExecutionFailureContainmentValidationError(
                "containment evaluation must not predate failure observation"
            )
        )
    try:
        return Success(
            ExecutionContainmentSnapshot(
                decision=ExecutionContainmentDecision.CONTAIN,
                evaluated_at=evaluated_at,
                reasons=(f"{signal.stage.value}.{signal.kind.value}", signal.code),
                source_stage=signal.stage,
            )
        )
    except ExecutionFailureContainmentError as error:
        return Failure(error)


def evaluate_reconciliation_containment(
    reconciliation: ExecutionReconciliationSnapshot,
    *,
    evaluated_at: datetime,
) -> Result[ExecutionContainmentSnapshot, ExecutionFailureContainmentError]:
    if not isinstance(reconciliation, ExecutionReconciliationSnapshot):
        return Failure(
            ExecutionFailureContainmentValidationError(
                "reconciliation must be ExecutionReconciliationSnapshot"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="evaluated_at")
    except ExecutionFailureContainmentError as error:
        return Failure(error)
    if evaluated_at < reconciliation.reconciled_at:
        return Failure(
            ExecutionFailureContainmentValidationError(
                "containment evaluation must not predate reconciliation"
            )
        )
    if reconciliation.status is ExecutionReconciliationStatus.MATCHED:
        return Success(
            ExecutionContainmentSnapshot(
                decision=ExecutionContainmentDecision.ALLOW_CONTINUE,
                evaluated_at=evaluated_at,
                reasons=(),
            )
        )

    kind = _RECONCILIATION_KIND[reconciliation.status]
    reasons = (
        f"reconciliation.{kind.value}",
        *tuple(f"reconciliation.issue.{issue}" for issue in reconciliation.issues),
    )
    try:
        return Success(
            ExecutionContainmentSnapshot(
                decision=ExecutionContainmentDecision.CONTAIN,
                evaluated_at=evaluated_at,
                reasons=reasons,
                source_stage=ExecutionFailureStage.RECONCILIATION,
            )
        )
    except ExecutionFailureContainmentError as error:
        return Failure(error)
