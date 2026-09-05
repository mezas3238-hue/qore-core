"""Adversarial closure for the D1 exact-runtime finding.

``ReviewFunctionalDecisionCommand`` accepted permissive runtime material: a
``FunctionalDecision`` subclass, a ``DecisionId`` subclass, a value-equal StrEnum
for ``priority``/``requested_outcome``, or a ``DecisionReason`` subclass could
launder into a review the handler would then project into a ``FunctionalDecision``.

These tests prove the command and its produced event now enforce exact runtime
types and recursively revalidate the retained source decision, while preserving
valid exact-type callers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

import pytest

from qore.domain.commands import CommandId, CommandMetadata, CommandName
from qore.domain.events import (
    CausationId,
    CorrelationId,
    DomainEventCategory,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.modules.cibo.contracts import (
    CiboDecisionProducedEvent,
    CiboValidationError,
    ReviewFunctionalDecisionCommand,
)

_SOURCE_DECISION_ID = DecisionId(UUID("20000000-0000-0000-0000-000000000001"))
_CIBO_DECISION_ID = DecisionId(UUID("20000000-0000-0000-0000-000000000002"))
_COMMAND_ID = CommandId(UUID("20000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("20000000-0000-0000-0000-000000000004"))
_EVENT_ID = DomainEventId(UUID("20000000-0000-0000-0000-000000000006"))
_TIMESTAMP = datetime(2026, 8, 7, 20, 0, tzinfo=UTC)

_SOURCE_REASON = DecisionReason(
    code=DecisionReasonCode("cio.context-accepted"),
    summary="Strategic context accepted",
)
_REVIEW_REASON = DecisionReason(
    code=DecisionReasonCode("cibo.business-accepted"),
    summary="Business review accepted",
)


def _source_decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=_SOURCE_DECISION_ID,
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("cio.strategic-review"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.HIGH,
        metadata=DecisionMetadata(correlation_id=_CORRELATION_ID),
        reasons=(_SOURCE_REASON,),
        outcome=DecisionOutcome.APPROVED,
    )


def _command(
    *,
    source_decision: FunctionalDecision | None = None,
    decision_id: DecisionId | None = None,
    priority: DecisionPriority | None = None,
) -> ReviewFunctionalDecisionCommand:
    return ReviewFunctionalDecisionCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("cibo.review-functional-decision"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION_ID,
            causation_id=CausationId(_SOURCE_DECISION_ID.value),
        ),
        decision_id=decision_id if decision_id is not None else _CIBO_DECISION_ID,
        source_decision=source_decision if source_decision is not None else _source_decision(),
        priority=priority if priority is not None else DecisionPriority.NORMAL,
        reasons=(),
        requested_outcome=None,
    )


def _resolved_command(outcome: DecisionOutcome) -> ReviewFunctionalDecisionCommand:
    return ReviewFunctionalDecisionCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("cibo.review-functional-decision"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION_ID,
            causation_id=CausationId(_SOURCE_DECISION_ID.value),
        ),
        decision_id=_CIBO_DECISION_ID,
        source_decision=_source_decision(),
        priority=DecisionPriority.NORMAL,
        reasons=(_REVIEW_REASON,),
        requested_outcome=outcome,
    )


def _corrupt_source_decision(**overrides: object) -> FunctionalDecision:
    corrupted = object.__new__(FunctionalDecision)
    object.__setattr__(corrupted, "decision_id", _SOURCE_DECISION_ID)
    object.__setattr__(corrupted, "timestamp", _TIMESTAMP)
    object.__setattr__(corrupted, "decision_type", DecisionType("cio.strategic-review"))
    object.__setattr__(corrupted, "status", DecisionStatus.RESOLVED)
    object.__setattr__(corrupted, "priority", DecisionPriority.HIGH)
    object.__setattr__(
        corrupted,
        "metadata",
        DecisionMetadata(correlation_id=_CORRELATION_ID),
    )
    object.__setattr__(corrupted, "reasons", (_SOURCE_REASON,))
    object.__setattr__(corrupted, "outcome", DecisionOutcome.APPROVED)
    for name, value in overrides.items():
        object.__setattr__(corrupted, name, value)
    return corrupted


# --- valid exact-type callers are preserved ---


def test_valid_exact_type_caller_is_preserved() -> None:
    decision = _resolved_command(DecisionOutcome.APPROVED).to_decision()
    assert decision.decision_id == _CIBO_DECISION_ID
    assert decision.status is DecisionStatus.RESOLVED
    assert decision.outcome is DecisionOutcome.APPROVED
    assert decision.reasons == (_REVIEW_REASON,)


def test_pending_review_accepts_exact_types() -> None:
    command = _command()
    assert command.to_decision().status is DecisionStatus.PENDING


# --- subclass / value-equal / wrong-runtime laundering is rejected ---


def test_functional_decision_subclass_rejected() -> None:
    class FakeDecision(FunctionalDecision):
        pass

    forged = FakeDecision(
        decision_id=_SOURCE_DECISION_ID,
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("cio.strategic-review"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.HIGH,
        metadata=DecisionMetadata(correlation_id=_CORRELATION_ID),
        reasons=(_SOURCE_REASON,),
        outcome=DecisionOutcome.APPROVED,
    )
    with pytest.raises(CiboValidationError, match="exact FunctionalDecision"):
        _command(source_decision=forged)


def test_decision_id_subclass_rejected() -> None:
    class FakeDecisionId(DecisionId):
        pass

    with pytest.raises(CiboValidationError, match="exact DecisionId"):
        _command(decision_id=FakeDecisionId(_CIBO_DECISION_ID.value))


def test_value_equal_priority_enum_rejected() -> None:
    class OtherPriority(StrEnum):
        NORMAL = "normal"

    with pytest.raises(CiboValidationError, match="exact DecisionPriority"):
        _command(priority=OtherPriority.NORMAL)  # type: ignore[arg-type]


def test_value_equal_outcome_enum_rejected() -> None:
    class OtherOutcome(StrEnum):
        APPROVED = "approved"

    with pytest.raises(CiboValidationError, match="exact DecisionOutcome"):
        _resolved_command(OtherOutcome.APPROVED)  # type: ignore[arg-type]


def test_decision_reason_subclass_rejected() -> None:
    class FakeReason(DecisionReason):
        pass

    forged_reason = FakeReason(
        code=DecisionReasonCode("cibo.business-accepted"),
        summary="Business review accepted",
    )
    with pytest.raises(CiboValidationError, match="DecisionReason"):
        ReviewFunctionalDecisionCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("cibo.review-functional-decision"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(_SOURCE_DECISION_ID.value),
            ),
            decision_id=_CIBO_DECISION_ID,
            source_decision=_source_decision(),
            priority=DecisionPriority.NORMAL,
            reasons=(forged_reason,),
            requested_outcome=DecisionOutcome.APPROVED,
        )


# --- recursive revalidation of retained source decision ---


def test_reflectively_corrupted_source_status_fails_closed() -> None:
    corrupted = _corrupt_source_decision(status="resolved")
    with pytest.raises(CiboValidationError, match="status"):
        _command(source_decision=corrupted)


def test_reflectively_corrupted_source_decision_id_fails_closed() -> None:
    corrupted = _corrupt_source_decision(decision_id="not-a-decision-id")
    with pytest.raises(CiboValidationError, match="decision id"):
        _command(source_decision=corrupted)


def test_reflectively_corrupted_source_reason_fails_closed() -> None:
    corrupted = _corrupt_source_decision(reasons=(_SOURCE_REASON, "raw-reason"))
    with pytest.raises(CiboValidationError, match="DecisionReason"):
        _command(source_decision=corrupted)


# --- produced event boundary ---


def test_event_rejects_subclassed_decision() -> None:
    class FakeDecision(FunctionalDecision):
        pass

    forged = FakeDecision(
        decision_id=_CIBO_DECISION_ID,
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("cibo.business-review"),
        status=DecisionStatus.PENDING,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=_CORRELATION_ID,
            causation_id=CausationId(_SOURCE_DECISION_ID.value),
        ),
    )
    with pytest.raises(CiboValidationError, match="exact FunctionalDecision"):
        CiboDecisionProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("cibo"),
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(_SOURCE_DECISION_ID.value),
            ),
            decision=forged,
            source_decision_id=_SOURCE_DECISION_ID,
        )


def test_event_rejects_non_decision_id_source() -> None:
    decision = _resolved_command(DecisionOutcome.APPROVED).to_decision()
    with pytest.raises(CiboValidationError, match="exact DecisionId"):
        CiboDecisionProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("cibo"),
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(_SOURCE_DECISION_ID.value),
            ),
            decision=decision,
            source_decision_id="not-a-decision-id",  # type: ignore[arg-type]
        )
