from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import ExecutiveAttentionLevel
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveNotificationError(DomainError):
    """Base error for executive notification and interruption contracts."""

    __slots__ = ()


class ExecutiveNotificationValidationError(ExecutiveNotificationError):
    """A notification value violates a deterministic public invariant."""

    __slots__ = ()


class ExecutiveNotificationOrigin(StrEnum):
    CIBO_CORE = "cibo-core"
    RISK = "risk"
    SYSTEM = "system"
    CORPORATE = "corporate"
    GOVERNANCE = "governance"


class ExecutiveInterruptionMode(StrEnum):
    PASSIVE = "passive"
    AMBIENT = "ambient"
    PROMINENT = "prominent"
    DECISION = "decision"
    CRITICAL = "critical"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveNotificationValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveNotificationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ExecutiveNotificationValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveNotificationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveNotificationValidationError(
                "executive notification id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveNotification:
    """Secret-free evidence-backed notification; it carries no command authority."""

    notification_id: ExecutiveNotificationId
    origin: ExecutiveNotificationOrigin
    level: ExecutiveAttentionLevel
    subject_code: str
    reason_codes: tuple[str, ...]
    observed_at: datetime
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.notification_id, ExecutiveNotificationId):
            raise ExecutiveNotificationValidationError(
                "notification requires ExecutiveNotificationId"
            )
        if not isinstance(self.origin, ExecutiveNotificationOrigin):
            raise ExecutiveNotificationValidationError(
                "notification requires ExecutiveNotificationOrigin"
            )
        if not isinstance(self.level, ExecutiveAttentionLevel):
            raise ExecutiveNotificationValidationError(
                "notification requires ExecutiveAttentionLevel"
            )
        object.__setattr__(
            self,
            "subject_code",
            _validate_code(self.subject_code, field_name="notification subject code"),
        )
        if not isinstance(self.reason_codes, tuple) or not self.reason_codes:
            raise ExecutiveNotificationValidationError(
                "notification requires at least one immutable reason code"
            )
        normalized_reasons = tuple(
            _validate_code(value, field_name="notification reason code")
            for value in self.reason_codes
        )
        if len(set(normalized_reasons)) != len(normalized_reasons):
            raise ExecutiveNotificationValidationError(
                "notification reason codes must not contain duplicates"
            )
        object.__setattr__(self, "reason_codes", tuple(sorted(normalized_reasons)))
        _validate_timestamp(self.observed_at, field_name="observed_at")
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(item, ExecutiveEvidenceRef) for item in self.evidence_refs
        ):
            raise ExecutiveNotificationValidationError(
                "notification evidence refs must be ExecutiveEvidenceRef tuple"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ExecutiveNotificationValidationError(
                "notification evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.notification_id.logical_values(),
            self.origin.value,
            self.level.value,
            self.subject_code,
            self.reason_codes,
            self.observed_at.isoformat(),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveNotificationRule:
    level: ExecutiveAttentionLevel
    interruption_mode: ExecutiveInterruptionMode
    may_interrupt: bool
    requires_acknowledgement: bool

    def __post_init__(self) -> None:
        if not isinstance(self.level, ExecutiveAttentionLevel):
            raise ExecutiveNotificationValidationError(
                "notification rule requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.interruption_mode, ExecutiveInterruptionMode):
            raise ExecutiveNotificationValidationError(
                "notification rule requires ExecutiveInterruptionMode"
            )
        if not isinstance(self.may_interrupt, bool):
            raise ExecutiveNotificationValidationError(
                "notification rule may_interrupt must be bool"
            )
        if not isinstance(self.requires_acknowledgement, bool):
            raise ExecutiveNotificationValidationError(
                "notification rule requires_acknowledgement must be bool"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.level.value,
            self.interruption_mode.value,
            self.may_interrupt,
            self.requires_acknowledgement,
        )


@dataclass(frozen=True, slots=True)
class ExecutiveNotificationPolicy:
    """Complete explicit interruption policy for every executive attention level."""

    rules: tuple[ExecutiveNotificationRule, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rules, tuple) or any(
            not isinstance(item, ExecutiveNotificationRule) for item in self.rules
        ):
            raise ExecutiveNotificationValidationError(
                "notification policy rules must be ExecutiveNotificationRule tuple"
            )
        levels = tuple(item.level for item in self.rules)
        if len(set(levels)) != len(levels):
            raise ExecutiveNotificationValidationError(
                "notification policy must not duplicate attention levels"
            )
        if set(levels) != set(ExecutiveAttentionLevel):
            raise ExecutiveNotificationValidationError(
                "notification policy must define every attention level exactly once"
            )
        object.__setattr__(
            self,
            "rules",
            tuple(sorted(self.rules, key=lambda item: item.level.value)),
        )

    def rule_for(self, level: ExecutiveAttentionLevel) -> ExecutiveNotificationRule:
        if not isinstance(level, ExecutiveAttentionLevel):
            raise ExecutiveNotificationValidationError(
                "notification policy lookup requires ExecutiveAttentionLevel"
            )
        for rule in self.rules:
            if rule.level is level:
                return rule
        raise ExecutiveNotificationValidationError(
            "notification policy is missing required attention level"
        )

    def logical_values(self) -> tuple[object, ...]:
        return tuple(rule.logical_values() for rule in self.rules)


@dataclass(frozen=True, slots=True)
class ExecutiveNotificationPresentation:
    notification: ExecutiveNotification
    rule: ExecutiveNotificationRule
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.notification, ExecutiveNotification):
            raise ExecutiveNotificationValidationError(
                "notification presentation requires ExecutiveNotification"
            )
        if not isinstance(self.rule, ExecutiveNotificationRule):
            raise ExecutiveNotificationValidationError(
                "notification presentation requires ExecutiveNotificationRule"
            )
        _validate_timestamp(self.evaluated_at, field_name="evaluated_at")
        if self.rule.level is not self.notification.level:
            raise ExecutiveNotificationValidationError(
                "notification presentation rule level must match notification"
            )
        if self.evaluated_at < self.notification.observed_at:
            raise ExecutiveNotificationValidationError(
                "notification evaluation cannot predate observation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.notification.logical_values(),
            self.rule.logical_values(),
            self.evaluated_at.isoformat(),
        )


def evaluate_executive_notification(
    notification: ExecutiveNotification,
    policy: ExecutiveNotificationPolicy,
    *,
    evaluated_at: datetime,
) -> Result[ExecutiveNotificationPresentation, ExecutiveNotificationError]:
    if not isinstance(notification, ExecutiveNotification):
        return Failure(
            ExecutiveNotificationValidationError(
                "notification evaluation requires ExecutiveNotification"
            )
        )
    if not isinstance(policy, ExecutiveNotificationPolicy):
        return Failure(
            ExecutiveNotificationValidationError(
                "notification evaluation requires ExecutiveNotificationPolicy"
            )
        )
    try:
        return Success(
            ExecutiveNotificationPresentation(
                notification=notification,
                rule=policy.rule_for(notification.level),
                evaluated_at=evaluated_at,
            )
        )
    except ExecutiveNotificationError as error:
        return Failure(error)
