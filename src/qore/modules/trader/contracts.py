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
from qore.functional.decisions import DecisionStatus, FunctionalDecision
from qore.kernel.errors import DomainError
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistMetadata,
    SpecialistReason,
)


class TraderError(DomainError):
    """Base error for Virtual Trader contracts."""

    __slots__ = ()


class TraderValidationError(TraderError):
    """Explicit violation of a Virtual Trader invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ProduceVirtualTraderAnalysisCommand(Command):
    """Request a deterministic Virtual Trader analysis from explicit internal input."""

    analysis_id: SpecialistAnalysisId
    source_decision: FunctionalDecision
    kind: SpecialistKind
    confidence: SpecialistConfidence
    reasons: tuple[SpecialistReason, ...]

    def __post_init__(self) -> None:
        if self.source_decision.status is not DecisionStatus.RESOLVED:
            raise TraderValidationError(
                "virtual trader analysis requires a resolved source decision"
            )
        if self.metadata.correlation_id != self.source_decision.metadata.correlation_id:
            raise TraderValidationError(
                "virtual trader command correlation must match the source decision"
            )
        expected_causation = CausationId(self.source_decision.decision_id.value)
        if self.metadata.causation_id != expected_causation:
            raise TraderValidationError(
                "virtual trader command causation must match the source decision"
            )
        if self.analysis_id.value == self.source_decision.decision_id.value:
            raise TraderValidationError(
                "virtual trader analysis identity must differ from its source decision"
            )
        if not self.kind.value.startswith("virtual-trader."):
            raise TraderValidationError(
                "virtual trader kind must use the virtual-trader.* namespace"
            )
        if not isinstance(self.reasons, tuple) or not self.reasons or any(
            not isinstance(reason, SpecialistReason) for reason in self.reasons
        ):
            raise TraderValidationError(
                "virtual trader analysis requires an immutable non-empty reason tuple"
            )

    def to_analysis(self) -> SpecialistAnalysis:
        return SpecialistAnalysis(
            analysis_id=self.analysis_id,
            timestamp=self.timestamp,
            kind=self.kind,
            status=SpecialistAnalysisStatus.COMPLETED,
            metadata=SpecialistMetadata(
                correlation_id=self.metadata.correlation_id,
                causation_id=self.metadata.causation_id,
                attributes=self.metadata.attributes,
            ),
            confidence=self.confidence,
            reasons=self.reasons,
        )


class TraderAnalysisProducedEvent(BusinessDomainEvent):
    """Event representing a Virtual Trader analysis that has already been produced."""

    __slots__ = ("_analysis", "_source_decision_id")
    _analysis: SpecialistAnalysis
    _source_decision_id: object

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        analysis: SpecialistAnalysis,
        source_decision_id: object,
    ) -> None:
        if metadata.correlation_id != analysis.metadata.correlation_id:
            raise TraderValidationError(
                "virtual trader event correlation must match the represented analysis"
            )
        if metadata.causation_id != analysis.metadata.causation_id:
            raise TraderValidationError(
                "virtual trader event causation must match the represented analysis"
            )
        if not hasattr(source_decision_id, "value"):
            raise TraderValidationError("source_decision_id must expose a value")
        expected_causation = CausationId(source_decision_id.value)
        if analysis.metadata.causation_id != expected_causation:
            raise TraderValidationError(
                "virtual trader analysis causation must match source_decision_id"
            )
        object.__setattr__(self, "_analysis", analysis)
        object.__setattr__(self, "_source_decision_id", source_decision_id)
        super().__init__(
            timestamp=timestamp,
            event_name="virtual-trader.analysis-produced",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def analysis(self) -> SpecialistAnalysis:
        return self._analysis

    @property
    def source_decision_id(self) -> object:
        return self._source_decision_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            *super().logical_values(),
            str(self._source_decision_id.value),
            self._analysis.logical_values(),
        )
