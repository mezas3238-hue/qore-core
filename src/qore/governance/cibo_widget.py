from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.governance.cibo_executive_dialogue import CiboExecutiveAnswer
from qore.governance.executive_client_surface import ExecutiveClientSurfaceId
from qore.governance.executive_notifications import (
    ExecutiveInterruptionMode,
    ExecutiveNotificationPresentation,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class CiboWidgetError(DomainError):
    """Base error for cross-platform CIBO widget state contracts."""

    __slots__ = ()


class CiboWidgetValidationError(CiboWidgetError):
    """A CIBO widget state violates a deterministic presentation invariant."""

    __slots__ = ()


class CiboWidgetMode(StrEnum):
    COLLAPSED = "collapsed"
    AMBIENT = "ambient"
    ATTENTION = "attention"
    EXPANDED = "expanded"
    FULL_CONVERSATION = "full-conversation"
    EVIDENCE_REVIEW = "evidence-review"
    CRITICAL_INTERRUPTION = "critical-interruption"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CiboWidgetValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboWidgetValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CiboWidgetStateId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise CiboWidgetValidationError("CIBO widget state id must be UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CiboWidgetState:
    """One logical widget state shared by Desktop, iOS and Android."""

    state_id: CiboWidgetStateId
    surface_id: ExecutiveClientSurfaceId
    mode: CiboWidgetMode
    observed_at: datetime
    answer: CiboExecutiveAnswer | None = None
    notification: ExecutiveNotificationPresentation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state_id, CiboWidgetStateId):
            raise CiboWidgetValidationError(
                "CIBO widget state requires CiboWidgetStateId"
            )
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise CiboWidgetValidationError(
                "CIBO widget state requires ExecutiveClientSurfaceId"
            )
        if not isinstance(self.mode, CiboWidgetMode):
            raise CiboWidgetValidationError("CIBO widget state requires CiboWidgetMode")
        _validate_timestamp(self.observed_at, field_name="observed_at")
        if self.answer is not None and not isinstance(self.answer, CiboExecutiveAnswer):
            raise CiboWidgetValidationError(
                "CIBO widget answer must be CiboExecutiveAnswer"
            )
        if self.notification is not None and not isinstance(
            self.notification,
            ExecutiveNotificationPresentation,
        ):
            raise CiboWidgetValidationError(
                "CIBO widget notification must be ExecutiveNotificationPresentation"
            )
        if self.answer is not None and self.observed_at < self.answer.answered_at:
            raise CiboWidgetValidationError(
                "CIBO widget observation cannot predate answer"
            )
        if (
            self.notification is not None
            and self.observed_at < self.notification.evaluated_at
        ):
            raise CiboWidgetValidationError(
                "CIBO widget observation cannot predate notification presentation"
            )
        if self.mode in (
            CiboWidgetMode.FULL_CONVERSATION,
            CiboWidgetMode.EVIDENCE_REVIEW,
        ) and self.answer is None:
            raise CiboWidgetValidationError(
                "conversation/evidence widget mode requires CIBO answer"
            )
        if self.mode is CiboWidgetMode.ATTENTION and self.notification is None:
            raise CiboWidgetValidationError(
                "attention widget mode requires notification"
            )
        if self.mode is CiboWidgetMode.CRITICAL_INTERRUPTION:
            if self.notification is None:
                raise CiboWidgetValidationError(
                    "critical widget mode requires notification"
                )
            if (
                self.notification.rule.interruption_mode
                is not ExecutiveInterruptionMode.CRITICAL
            ):
                raise CiboWidgetValidationError(
                    "critical widget mode requires critical interruption rule"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.state_id.logical_values(),
            self.surface_id.logical_values(),
            self.mode.value,
            self.observed_at.isoformat(),
            None if self.answer is None else self.answer.logical_values(),
            None
            if self.notification is None
            else self.notification.logical_values(),
        )


def build_cibo_widget_state(
    *,
    state_id: CiboWidgetStateId,
    surface_id: ExecutiveClientSurfaceId,
    mode: CiboWidgetMode,
    observed_at: datetime,
    answer: CiboExecutiveAnswer | None = None,
    notification: ExecutiveNotificationPresentation | None = None,
) -> Result[CiboWidgetState, CiboWidgetError]:
    try:
        return Success(
            CiboWidgetState(
                state_id=state_id,
                surface_id=surface_id,
                mode=mode,
                observed_at=observed_at,
                answer=answer,
                notification=notification,
            )
        )
    except CiboWidgetError as error:
        return Failure(error)
