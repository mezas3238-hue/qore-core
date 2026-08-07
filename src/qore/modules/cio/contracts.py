from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.domain.commands import Command, CommandMetadata
from qore.domain.events import (
    BusinessDomainEvent,
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
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)


@dataclass(frozen=True, slots=True)
class CreateCioDecisionCommand(Command):
    """Solicitud explícita para producir una decisión funcional del CIO."""

    decision_id: DecisionId
    decision_type: DecisionType
    priority: DecisionPriority
    reasons: tuple[DecisionReason, ...] = ()
    requested_outcome: DecisionOutcome | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(reason, DecisionReason) for reason in self.reasons
        ):
            raise TypeError("reasons must be an immutable tuple of DecisionReason values")
        if self.requested_outcome is not None and not self.reasons:
            raise ValueError("resolved CIO decision request requires at least one reason")

    def to_decision(self) -> FunctionalDecision:
        """Project the command into the shared decision contract deterministically."""
        status = (
            DecisionStatus.PENDING
            if self.requested_outcome is None
            else DecisionStatus.RESOLVED
        )
        return FunctionalDecision(
            decision_id=self.decision_id,
            timestamp=self.timestamp,
            decision_type=self.decision_type,
            status=status,
            priority=self.priority,
            metadata=DecisionMetadata(
                correlation_id=self.metadata.correlation_id,
                causation_id=self.metadata.causation_id,
                attributes=self.metadata.attributes,
            ),
            reasons=self.reasons,
            outcome=self.requested_outcome,
        )


class CioDecisionProducedEvent(BusinessDomainEvent):
    """Evento explícito que representa una decisión ya producida por CIO."""

    __slots__ = ("_decision",)
    _decision: FunctionalDecision

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        decision: FunctionalDecision,
    ) -> None:
        object.__setattr__(self, "_decision", decision)
        super().__init__(
            timestamp=timestamp,
            event_name="cio.decision-produced",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def decision(self) -> FunctionalDecision:
        return self._decision

    def logical_values(self) -> tuple[object, ...]:
        return (*super().logical_values(), self._decision.logical_values())


def decision_command_metadata(
    metadata: CommandMetadata,
) -> DecisionMetadata:
    """Adapt command metadata into shared decision metadata without side effects."""
    return DecisionMetadata(
        correlation_id=metadata.correlation_id,
        causation_id=metadata.causation_id,
        attributes=metadata.attributes,
    )
