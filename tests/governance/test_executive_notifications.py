from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.governance.executive_notifications import (
    ExecutiveInterruptionMode,
    ExecutiveNotification,
    ExecutiveNotificationId,
    ExecutiveNotificationOrigin,
    ExecutiveNotificationPolicy,
    ExecutiveNotificationRule,
    ExecutiveNotificationValidationError,
    evaluate_executive_notification,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import ExecutiveAttentionLevel
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)


def _policy() -> ExecutiveNotificationPolicy:
    return ExecutiveNotificationPolicy(
        rules=(
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.INFORMATION,
                ExecutiveInterruptionMode.PASSIVE,
                False,
                False,
            ),
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.ATTENTION,
                ExecutiveInterruptionMode.AMBIENT,
                False,
                False,
            ),
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.IMPORTANT,
                ExecutiveInterruptionMode.PROMINENT,
                True,
                False,
            ),
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.DECISION_REQUIRED,
                ExecutiveInterruptionMode.DECISION,
                True,
                True,
            ),
            ExecutiveNotificationRule(
                ExecutiveAttentionLevel.CRITICAL,
                ExecutiveInterruptionMode.CRITICAL,
                True,
                True,
            ),
        )
    )


def _notification(
    level: ExecutiveAttentionLevel = ExecutiveAttentionLevel.CRITICAL,
) -> ExecutiveNotification:
    return ExecutiveNotification(
        notification_id=ExecutiveNotificationId(
            UUID("55000000-0000-0000-0000-000000000001")
        ),
        origin=ExecutiveNotificationOrigin.RISK,
        level=level,
        subject_code="risk.drawdown",
        reason_codes=("risk.threshold", "capital.protection"),
        observed_at=_NOW,
        evidence_refs=(
            ExecutiveEvidenceRef("audit:risk/002"),
            ExecutiveEvidenceRef("audit:risk/001"),
        ),
    )


def test_complete_policy_deterministically_maps_notification_level() -> None:
    result = evaluate_executive_notification(
        _notification(),
        _policy(),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.rule.interruption_mode is ExecutiveInterruptionMode.CRITICAL
    assert result.value.rule.may_interrupt is True
    assert result.value.rule.requires_acknowledgement is True
    assert result.value.logical_values() == result.value.logical_values()


def test_policy_requires_every_attention_level_exactly_once() -> None:
    rules = _policy().rules
    with pytest.raises(ExecutiveNotificationValidationError):
        ExecutiveNotificationPolicy(rules=rules[:-1])
    with pytest.raises(ExecutiveNotificationValidationError):
        ExecutiveNotificationPolicy(rules=rules + (rules[0],))


def test_notification_normalizes_reasons_and_evidence_deterministically() -> None:
    notification = _notification()
    assert notification.reason_codes == ("capital.protection", "risk.threshold")
    assert tuple(item.value for item in notification.evidence_refs) == (
        "audit:risk/001",
        "audit:risk/002",
    )
    with pytest.raises(FrozenInstanceError):
        notification.__setattr__("origin", ExecutiveNotificationOrigin.SYSTEM)


def test_notification_requires_explicit_evidence_safe_codes_and_types() -> None:
    with pytest.raises(ExecutiveNotificationValidationError):
        ExecutiveNotification(
            notification_id=ExecutiveNotificationId(UUID(int=2)),
            origin=ExecutiveNotificationOrigin.SYSTEM,
            level=ExecutiveAttentionLevel.ATTENTION,
            subject_code="System Alert",
            reason_codes=("system.alert",),
            observed_at=_NOW,
        )
    with pytest.raises(ExecutiveNotificationValidationError):
        ExecutiveNotification(
            notification_id=ExecutiveNotificationId(UUID(int=3)),
            origin=ExecutiveNotificationOrigin.SYSTEM,
            level=ExecutiveAttentionLevel.ATTENTION,
            subject_code="system.alert",
            reason_codes=(),
            observed_at=_NOW,
        )


def test_notification_exposes_no_command_execution_surface() -> None:
    notification = _notification()
    presentation = evaluate_executive_notification(
        notification,
        _policy(),
        evaluated_at=_NOW,
    )
    assert isinstance(presentation, Success)
    assert not hasattr(notification, "command")
    assert not hasattr(notification, "execute")
    assert not hasattr(notification, "order")
    assert not hasattr(presentation.value, "dispatch")


def test_evaluation_before_observation_fails_closed() -> None:
    result = evaluate_executive_notification(
        _notification(),
        _policy(),
        evaluated_at=_NOW - timedelta(microseconds=1),
    )
    assert isinstance(result, Failure)


def test_types_fail_closed_without_string_or_bool_coercion() -> None:
    with pytest.raises(ExecutiveNotificationValidationError):
        ExecutiveNotificationId(cast(UUID, "notification"))
    with pytest.raises(ExecutiveNotificationValidationError):
        ExecutiveNotificationRule(
            ExecutiveAttentionLevel.INFORMATION,
            ExecutiveInterruptionMode.PASSIVE,
            cast(bool, 1),
            False,
        )
    result = evaluate_executive_notification(
        cast(ExecutiveNotification, object()),
        _policy(),
        evaluated_at=_NOW,
    )
    assert isinstance(result, Failure)
