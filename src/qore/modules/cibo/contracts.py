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


def _validate_functional_decision(
    decision: FunctionalDecision,
    *,
    field_name: str,
) -> None:
    """Re-enter the exact-runtime and lifecycle invariants of a retained decision.

    ``FunctionalDecision`` is a widely used public value record (frozen, slots),
    so a subclass or a reflectively corrupted value can otherwise launder through
    permissive ``isinstance`` acceptance. Every nested field is re-validated with
    its exact runtime type and the decision's own lifecycle invariants are
    re-checked before the value is trusted at this boundary.
    """
    if type(decision.decision_id) is not DecisionId:
        raise CiboValidationError(f"{field_name} decision id must be an exact DecisionId")
    if type(decision.timestamp) is not datetime:
        raise CiboValidationError(f"{field_name} timestamp must be an exact datetime")
    if decision.timestamp.tzinfo is None or decision.timestamp.utcoffset() is None:
        raise CiboValidationError(f"{field_name} timestamp must be timezone-aware")
    if type(decision.decision_type) is not DecisionType:
        raise CiboValidationError(
            f"{field_name} decision type must be an exact DecisionType"
        )
    if type(decision.status) is not DecisionStatus:
        raise CiboValidationError(f"{field_name} status must be an exact DecisionStatus")
    if type(decision.priority) is not DecisionPriority:
        raise CiboValidationError(
            f"{field_name} priority must be an exact DecisionPriority"
        )
    if type(decision.metadata) is not DecisionMetadata:
        raise CiboValidationError(
            f"{field_name} metadata must be an exact DecisionMetadata"
        )
    if type(decision.reasons) is not tuple or any(
        type(reason) is not DecisionReason for reason in decision.reasons
    ):
        raise CiboValidationError(
            f"{field_name} reasons must be an immutable tuple of exact DecisionReason"
        )
    if decision.outcome is not None and type(decision.outcome) is not DecisionOutcome:
        raise CiboValidationError(
            f"{field_name} outcome must be an exact DecisionOutcome"
        )
    if decision.status is DecisionStatus.PENDING and decision.outcome is not None:
        raise CiboValidationError(
            f"{field_name} pending decision must not have an outcome"
        )
    if decision.status is DecisionStatus.RESOLVED and decision.outcome is None:
        raise CiboValidationError(
            f"{field_name} resolved decision must have an outcome"
        )
    if decision.status is DecisionStatus.RESOLVED and not decision.reasons:
        raise CiboValidationError(
            f"{field_name} resolved decision must include a reason"
        )


@dataclass(frozen=True, slots=True)
class ReviewFunctionalDecisionCommand(Command):
    """Solicitud explícita para que CIBO revise una decisión funcional previa."""

    decision_id: DecisionId
    source_decision: FunctionalDecision
    priority: DecisionPriority
    reasons: tuple[DecisionReason, ...] = ()
    requested_outcome: DecisionOutcome | None = None

    def __post_init__(self) -> None:
        Command.__post_init__(self)
        # Exact runtime type: a FunctionalDecision subclass or a value-equal
        # StrEnum subclass must not launder into a review the handler projects.
        if type(self.source_decision) is not FunctionalDecision:
            raise CiboValidationError(
                "source decision must be an exact FunctionalDecision"
            )
        _validate_functional_decision(self.source_decision, field_name="source")
        if type(self.decision_id) is not DecisionId:
            raise CiboValidationError("decision id must be an exact DecisionId")
        if type(self.priority) is not DecisionPriority:
            raise CiboValidationError("priority must be an exact DecisionPriority")
        if (
            self.requested_outcome is not None
            and type(self.requested_outcome) is not DecisionOutcome
        ):
            raise CiboValidationError(
                "requested outcome must be an exact DecisionOutcome"
            )
        if not isinstance(self.reasons, tuple) or any(
            type(reason) is not DecisionReason for reason in self.reasons
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
        expected_causation = CausationId(self.source_decision.decision_id.value)
        if self.metadata.causation_id != expected_causation:
            raise CiboValidationError(
                "CIBO command causation must match the source decision"
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
        # Exact runtime type at the event boundary: a subclass or value-equal
        # StrEnum must not launder into the represented decision or its source.
        if type(decision) is not FunctionalDecision:
            raise CiboValidationError(
                "event decision must be an exact FunctionalDecision"
            )
        _validate_functional_decision(decision, field_name="event decision")
        if type(source_decision_id) is not DecisionId:
            raise CiboValidationError(
                "source decision id must be an exact DecisionId"
            )
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
