from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.domain.commands import Command
from qore.domain.events import (
    BusinessDomainEvent,
    CausationId,
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
from qore.kernel.errors import DomainError


class CiboError(DomainError):
    """Error base de los contratos funcionales de CIBO."""

    __slots__ = ()


class CiboValidationError(CiboError):
    """Violación explícita de una invariante de CIBO."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ReviewFunctionalDecisionCommand(Command):
    """Solicitud explícita para que CIBO revise una decisión funcional previa."""

    decision_id: DecisionId
    source_decision: FunctionalDecision
    priority: DecisionPriority
    reasons: tuple[DecisionReason, ...] = ()
    requested_outcome: DecisionOutcome | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(reason, DecisionReason) for reason in self.reasons
        ):
            raise CiboValidationError(
                "reasons must be an immutable tuple of DecisionReason values"
            )
        if self.source_decision.status is not DecisionStatus.RESOLVED:
            raise CiboValidationError(
                "CIBO can only review a resolved source decision"
            )
        if self.decision_id == self.source_decision.decision_id:
            raise CiboValidationError(
                "CIBO decision identity must differ from its source decision"
            )
        if self.metadata.correlation_id != self.source_decision.metadata.correlation_id:
            raise CiboValidationError(
                "CIBO command correlation must match the source decision"
            )
        if self.requested_outcome is not None and not self.reasons:
            raise CiboValidationError(
                "resolved CIBO review requires at least one reason"
            )

    def to_decision(self) -> FunctionalDecision:
        """Proyectar la revisión a FunctionalDecision sin side effects."""
        status = (
            DecisionStatus.PENDING
            if self.requested_outcome is None
            else DecisionStatus.RESOLVED
        )
        return FunctionalDecision(
            decision_id=self.decision_id,
            timestamp=self.timestamp,
            decision_type=DecisionType("cibo.business-review"),
            status=status,
            priority=self.priority,
            metadata=DecisionMetadata(
                correlation_id=self.source_decision.metadata.correlation_id,
                causation_id=CausationId(self.source_decision.decision_id.value),
                attributes=self.metadata.attributes,
            ),
            reasons=self.reasons,
            outcome=self.requested_outcome,
        )


class CiboDecisionProducedEvent(BusinessDomainEvent):
    """Evento explícito que representa una decisión ya producida por CIBO."""

    __slots__ = ("_decision", "_source_decision_id")
    _decision: FunctionalDecision
    _source_decision_id: DecisionId

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        decision: FunctionalDecision,
        source_decision_id: DecisionId,
    ) -> None:
        expected_causation = CausationId(source_decision_id.value)
        if metadata.correlation_id != decision.metadata.correlation_id:
            raise CiboValidationError(
                "CIBO decision event correlation must match the represented decision"
            )
        if decision.metadata.causation_id != expected_causation:
            raise CiboValidationError(
                "CIBO decision event source must match decision causation"
            )
        if metadata.causation_id != expected_causation:
            raise CiboValidationError(
                "CIBO decision event causation must match the source decision"
            )
        object.__setattr__(self, "_decision", decision)
        object.__setattr__(self, "_source_decision_id", source_decision_id)
        super().__init__(
            timestamp=timestamp,
            event_name="cibo.decision-produced",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def decision(self) -> FunctionalDecision:
        return self._decision

    @property
    def source_decision_id(self) -> DecisionId:
        return self._source_decision_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            *super().logical_values(),
            str(self._source_decision_id.value),
            self._decision.logical_values(),
        )
