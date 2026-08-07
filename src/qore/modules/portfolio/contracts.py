from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch
from uuid import UUID

from qore.domain.commands import Command
from qore.domain.events import (
    BusinessDomainEvent,
    CausationId,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.functional.decisions import DecisionId, DecisionOutcome, DecisionStatus, FunctionalDecision
from qore.kernel.errors import DomainError


class PortfolioError(DomainError):
    """Error base de los contratos funcionales del Portfolio Manager."""

    __slots__ = ()


class PortfolioValidationError(PortfolioError):
    """Violación explícita de una invariante del Portfolio Manager."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class AllocationIntentId:
    """Identidad explícita de una intención lógica de asignación."""

    value: UUID


@dataclass(frozen=True, slots=True)
class PortfolioTarget:
    """Objetivo lógico de asignación expresado en basis points."""

    name: str
    weight_bps: int

    def __post_init__(self) -> None:
        if fullmatch(r"[a-z][a-z0-9.-]*", self.name) is None:
            raise PortfolioValidationError(
                "portfolio target name must use lowercase letters, digits, dots, or hyphens"
            )
        if not 0 < self.weight_bps <= 10_000:
            raise PortfolioValidationError(
                "portfolio target weight must be between 1 and 10000 basis points"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.name, self.weight_bps)


@dataclass(frozen=True, slots=True)
class AllocationIntent:
    """Estado lógico e inmutable de asignación, sin posiciones ni ejecución real."""

    intent_id: AllocationIntentId
    source_decision_id: DecisionId
    timestamp: datetime
    targets: tuple[PortfolioTarget, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.targets, tuple) or not self.targets:
            raise PortfolioValidationError(
                "allocation intent targets must be a non-empty immutable tuple"
            )
        if any(not isinstance(target, PortfolioTarget) for target in self.targets):
            raise PortfolioValidationError(
                "allocation intent targets must contain only PortfolioTarget values"
            )
        names = tuple(target.name for target in self.targets)
        if len(set(names)) != len(names):
            raise PortfolioValidationError("allocation intent targets must be unique")
        if sum(target.weight_bps for target in self.targets) != 10_000:
            raise PortfolioValidationError(
                "allocation intent target weights must sum to 10000 basis points"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.intent_id.value),
            str(self.source_decision_id.value),
            self.timestamp.isoformat(),
            tuple(target.logical_values() for target in self.targets),
        )


@dataclass(frozen=True, slots=True)
class CreateAllocationIntentCommand(Command):
    """Solicitud para proyectar una decisión aprobada a una intención de asignación."""

    intent_id: AllocationIntentId
    source_decision: FunctionalDecision
    targets: tuple[PortfolioTarget, ...]

    def __post_init__(self) -> None:
        if self.source_decision.status is not DecisionStatus.RESOLVED:
            raise PortfolioValidationError(
                "portfolio allocation requires a resolved source decision"
            )
        if self.source_decision.outcome is not DecisionOutcome.APPROVED:
            raise PortfolioValidationError(
                "portfolio allocation requires an approved source decision"
            )
        if self.metadata.correlation_id != self.source_decision.metadata.correlation_id:
            raise PortfolioValidationError(
                "portfolio command correlation must match the source decision"
            )
        expected_causation = CausationId(self.source_decision.decision_id.value)
        if self.metadata.causation_id != expected_causation:
            raise PortfolioValidationError(
                "portfolio command causation must match the source decision"
            )
        AllocationIntent(
            intent_id=self.intent_id,
            source_decision_id=self.source_decision.decision_id,
            timestamp=self.timestamp,
            targets=self.targets,
        )

    def to_intent(self) -> AllocationIntent:
        """Proyectar el comando a estado lógico sin side effects."""
        return AllocationIntent(
            intent_id=self.intent_id,
            source_decision_id=self.source_decision.decision_id,
            timestamp=self.timestamp,
            targets=self.targets,
        )


class AllocationIntentCreatedEvent(BusinessDomainEvent):
    """Evento explícito que representa una intención lógica de asignación creada."""

    __slots__ = ("_intent",)
    _intent: AllocationIntent

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        intent: AllocationIntent,
    ) -> None:
        expected_causation = CausationId(intent.source_decision_id.value)
        if metadata.causation_id != expected_causation:
            raise PortfolioValidationError(
                "allocation event causation must match the source decision"
            )
        object.__setattr__(self, "_intent", intent)
        super().__init__(
            timestamp=timestamp,
            event_name="portfolio.allocation-intent-created",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def intent(self) -> AllocationIntent:
        return self._intent

    def logical_values(self) -> tuple[object, ...]:
        return (*super().logical_values(), self._intent.logical_values())
