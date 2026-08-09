from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.governance.cibo_executive_dialogue import (
    CiboExecutiveAnswer,
    CiboExecutiveDialogueTurnId,
    CiboExecutiveJudgmentState,
    CiboExecutivePromptRef,
    CiboExecutiveQuestion,
    build_cibo_executive_answer,
)
from qore.governance.cibo_widget import (
    CiboWidgetMode,
    CiboWidgetState,
    CiboWidgetStateId,
    CiboWidgetValidationError,
    build_cibo_widget_state,
)
from qore.governance.executive_client_surface import ExecutiveClientSurfaceId
from qore.governance.executive_control import ExecutivePrincipalId, ExecutiveReadScope
from qore.governance.executive_notifications import (
    ExecutiveInterruptionMode,
    ExecutiveNotification,
    ExecutiveNotificationId,
    ExecutiveNotificationOrigin,
    ExecutiveNotificationPolicy,
    ExecutiveNotificationPresentation,
    ExecutiveNotificationRule,
    evaluate_executive_notification,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import ExecutiveAttentionLevel
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 14, 0, tzinfo=UTC)
_SURFACE_ID = ExecutiveClientSurfaceId(
    UUID("57000000-0000-0000-0000-000000000001")
)


def _answer() -> CiboExecutiveAnswer:
    question = CiboExecutiveQuestion(
        turn_id=CiboExecutiveDialogueTurnId(UUID(int=2)),
        principal_id=ExecutivePrincipalId("ceo.primary"),
        prompt_ref=CiboExecutivePromptRef("prompt:risk-review"),
        requested_scope=ExecutiveReadScope.RISK,
        asked_at=_NOW,
        correlation_id=CorrelationId(UUID(int=3)),
    )
    result = build_cibo_executive_answer(
        question,
        judgment_state=CiboExecutiveJudgmentState.CONCERNED,
        summary_code="risk.restricted",
        reason_codes=("risk.limit",),
        evidence_refs=(ExecutiveEvidenceRef("audit:risk/001"),),
        answered_at=_NOW + timedelta(seconds=1),
        navigation_scope=ExecutiveReadScope.RISK,
    )
    assert isinstance(result, Success)
    return result.value


def _critical_notification() -> ExecutiveNotificationPresentation:
    policy = ExecutiveNotificationPolicy(
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
    notification = ExecutiveNotification(
        notification_id=ExecutiveNotificationId(UUID(int=4)),
        origin=ExecutiveNotificationOrigin.RISK,
        level=ExecutiveAttentionLevel.CRITICAL,
        subject_code="risk.critical",
        reason_codes=("risk.threshold",),
        observed_at=_NOW,
        evidence_refs=(ExecutiveEvidenceRef("audit:risk/002"),),
    )
    result = evaluate_executive_notification(
        notification,
        policy,
        evaluated_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    return result.value


def test_ambient_state_is_cross_platform_logical_state_only() -> None:
    result = build_cibo_widget_state(
        state_id=CiboWidgetStateId(UUID(int=5)),
        surface_id=_SURFACE_ID,
        mode=CiboWidgetMode.AMBIENT,
        observed_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.logical_values() == result.value.logical_values()
    assert not hasattr(result.value, "android_view")
    assert not hasattr(result.value, "ios_view")
    assert not hasattr(result.value, "desktop_window")
    with pytest.raises(FrozenInstanceError):
        result.value.__setattr__("mode", CiboWidgetMode.EXPANDED)


def test_conversation_and_evidence_review_require_answer() -> None:
    for mode in (
        CiboWidgetMode.FULL_CONVERSATION,
        CiboWidgetMode.EVIDENCE_REVIEW,
    ):
        missing = build_cibo_widget_state(
            state_id=CiboWidgetStateId(UUID(int=6)),
            surface_id=_SURFACE_ID,
            mode=mode,
            observed_at=_NOW + timedelta(seconds=2),
        )
        valid = build_cibo_widget_state(
            state_id=CiboWidgetStateId(UUID(int=7)),
            surface_id=_SURFACE_ID,
            mode=mode,
            observed_at=_NOW + timedelta(seconds=2),
            answer=_answer(),
        )
        assert isinstance(missing, Failure)
        assert isinstance(valid, Success)


def test_attention_requires_notification() -> None:
    result = build_cibo_widget_state(
        state_id=CiboWidgetStateId(UUID(int=8)),
        surface_id=_SURFACE_ID,
        mode=CiboWidgetMode.ATTENTION,
        observed_at=_NOW,
    )
    assert isinstance(result, Failure)


def test_critical_interruption_requires_critical_policy_result() -> None:
    notification = _critical_notification()
    valid = build_cibo_widget_state(
        state_id=CiboWidgetStateId(UUID(int=9)),
        surface_id=_SURFACE_ID,
        mode=CiboWidgetMode.CRITICAL_INTERRUPTION,
        observed_at=_NOW + timedelta(seconds=2),
        notification=notification,
    )
    assert isinstance(valid, Success)

    noncritical_policy = ExecutiveNotificationPolicy(
        rules=tuple(
            ExecutiveNotificationRule(
                level,
                ExecutiveInterruptionMode.PASSIVE,
                False,
                False,
            )
            for level in ExecutiveAttentionLevel
        )
    )
    notification_value = notification.notification
    noncritical = evaluate_executive_notification(
        notification_value,
        noncritical_policy,
        evaluated_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(noncritical, Success)
    rejected = build_cibo_widget_state(
        state_id=CiboWidgetStateId(UUID(int=10)),
        surface_id=_SURFACE_ID,
        mode=CiboWidgetMode.CRITICAL_INTERRUPTION,
        observed_at=_NOW + timedelta(seconds=2),
        notification=noncritical.value,
    )
    assert isinstance(rejected, Failure)


def test_widget_cannot_observe_answer_or_notification_before_they_exist() -> None:
    with pytest.raises(CiboWidgetValidationError):
        CiboWidgetState(
            state_id=CiboWidgetStateId(UUID(int=11)),
            surface_id=_SURFACE_ID,
            mode=CiboWidgetMode.FULL_CONVERSATION,
            observed_at=_NOW,
            answer=_answer(),
        )


def test_widget_exposes_no_command_or_trade_authority() -> None:
    result = build_cibo_widget_state(
        state_id=CiboWidgetStateId(UUID(int=12)),
        surface_id=_SURFACE_ID,
        mode=CiboWidgetMode.EXPANDED,
        observed_at=_NOW + timedelta(seconds=2),
        answer=_answer(),
        notification=_critical_notification(),
    )
    assert isinstance(result, Success)
    for name in ("execute", "dispatch", "order", "force_buy", "force_sell"):
        assert not hasattr(result.value, name)
