from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from uuid import UUID

from qore.domain.commands import Command
from qore.domain.events import (
    BusinessDomainEvent,
    CausationId,
    CorrelationId,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.kernel.errors import DomainError
from qore.kernel.temporal import is_timezone_aware_datetime
from qore.modules.knowledge.contracts import KnowledgeRecord, KnowledgeRecordId


class OptimizationError(DomainError):
    """Base error for Optimization Service contracts."""

    __slots__ = ()


class OptimizationInvariantError(OptimizationError):
    """Explicit violation of an Optimization Service invariant."""

    __slots__ = ()


class OptimizationAction(StrEnum):
    """Closed action set for one optimization proposal."""

    KEEP = "keep"
    ADJUST = "adjust"


@dataclass(frozen=True, slots=True)
class OptimizationPolicy:
    """Explicit deterministic policy used to derive an optimization proposal."""

    target_pass_rate: float
    adjustment_step_bps: int

    def __post_init__(self) -> None:
        if type(self.target_pass_rate) is not float or not isfinite(self.target_pass_rate):
            raise OptimizationInvariantError("target_pass_rate must be a finite float")
        if not 0.0 <= self.target_pass_rate <= 1.0:
            raise OptimizationInvariantError("target_pass_rate must be between 0 and 1")
        if type(self.adjustment_step_bps) is not int:
            raise OptimizationInvariantError("adjustment_step_bps must be an int")
        if not 1 <= self.adjustment_step_bps <= 10_000:
            raise OptimizationInvariantError(
                "adjustment_step_bps must be between 1 and 10000"
            )


@dataclass(frozen=True, slots=True)
class OptimizationProposalId:
    """Explicit identity of one immutable optimization proposal."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise OptimizationInvariantError("optimization proposal id must be a UUID")


@dataclass(frozen=True, slots=True)
class OptimizationProposal:
    """Immutable proposal derived exactly from one knowledge record and policy."""

    proposal_id: OptimizationProposalId
    timestamp: datetime
    source_knowledge: KnowledgeRecord
    correlation_id: CorrelationId
    causation_id: CausationId
    policy: OptimizationPolicy
    action: OptimizationAction
    suggested_delta_bps: int

    def __post_init__(self) -> None:
        if not isinstance(self.proposal_id, OptimizationProposalId):
            raise OptimizationInvariantError("proposal_id must be OptimizationProposalId")
        if not is_timezone_aware_datetime(self.timestamp):
            raise OptimizationInvariantError(
                "optimization timestamp must be a timezone-aware datetime"
            )
        if not isinstance(self.source_knowledge, KnowledgeRecord):
            raise OptimizationInvariantError("source_knowledge must be KnowledgeRecord")
        if not isinstance(self.correlation_id, CorrelationId):
            raise OptimizationInvariantError("correlation_id must be CorrelationId")
        if not isinstance(self.causation_id, CausationId):
            raise OptimizationInvariantError("causation_id must be CausationId")
        if not isinstance(self.policy, OptimizationPolicy):
            raise OptimizationInvariantError("policy must be OptimizationPolicy")
        if not isinstance(self.action, OptimizationAction):
            raise OptimizationInvariantError("action must be OptimizationAction")
        if type(self.suggested_delta_bps) is not int:
            raise OptimizationInvariantError("suggested_delta_bps must be an int")

        source = self.source_knowledge
        if self.correlation_id != source.correlation_id:
            raise OptimizationInvariantError(
                "optimization correlation must match source knowledge"
            )
        if self.causation_id != CausationId(source.record_id.value):
            raise OptimizationInvariantError(
                "optimization causation must match source knowledge record"
            )
        if self.proposal_id.value == source.record_id.value:
            raise OptimizationInvariantError(
                "optimization proposal identity must differ from source knowledge"
            )

        expected_action = (
            OptimizationAction.KEEP
            if source.pass_rate >= self.policy.target_pass_rate
            else OptimizationAction.ADJUST
        )
        expected_delta = (
            0 if expected_action is OptimizationAction.KEEP else self.policy.adjustment_step_bps
        )
        if self.action is not expected_action:
            raise OptimizationInvariantError(
                "optimization action must match source evidence and policy"
            )
        if self.suggested_delta_bps != expected_delta:
            raise OptimizationInvariantError(
                "suggested_delta_bps must match derived optimization action"
            )

    @property
    def source_knowledge_id(self) -> KnowledgeRecordId:
        return self.source_knowledge.record_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.proposal_id.value),
            self.timestamp.isoformat(),
            self.source_knowledge.logical_values(),
            str(self.correlation_id.value),
            str(self.causation_id.value),
            self.policy.target_pass_rate,
            self.policy.adjustment_step_bps,
            self.action.value,
            self.suggested_delta_bps,
        )


@dataclass(frozen=True, slots=True)
class ProposeKnowledgeOptimizationCommand(Command):
    """Request a deterministic proposal from explicit structured knowledge."""

    proposal_id: OptimizationProposalId
    source_knowledge: KnowledgeRecord
    policy: OptimizationPolicy

    def __post_init__(self) -> None:
        Command.__post_init__(self)
        if not isinstance(self.proposal_id, OptimizationProposalId):
            raise OptimizationInvariantError("proposal_id must be OptimizationProposalId")
        if not isinstance(self.source_knowledge, KnowledgeRecord):
            raise OptimizationInvariantError("source_knowledge must be KnowledgeRecord")
        if not isinstance(self.policy, OptimizationPolicy):
            raise OptimizationInvariantError("policy must be OptimizationPolicy")
        if self.metadata.correlation_id != self.source_knowledge.correlation_id:
            raise OptimizationInvariantError(
                "optimization command correlation must match source knowledge"
            )
        expected_causation = CausationId(self.source_knowledge.record_id.value)
        if self.metadata.causation_id != expected_causation:
            raise OptimizationInvariantError(
                "optimization command causation must match source knowledge"
            )
        if self.proposal_id.value == self.source_knowledge.record_id.value:
            raise OptimizationInvariantError(
                "optimization proposal identity must differ from source knowledge"
            )

    def to_proposal(self) -> OptimizationProposal:
        causation = self.metadata.causation_id
        if causation is None:
            raise OptimizationInvariantError(
                "optimization command causation must match source knowledge"
            )
        action = (
            OptimizationAction.KEEP
            if self.source_knowledge.pass_rate >= self.policy.target_pass_rate
            else OptimizationAction.ADJUST
        )
        delta = 0 if action is OptimizationAction.KEEP else self.policy.adjustment_step_bps
        return OptimizationProposal(
            proposal_id=self.proposal_id,
            timestamp=self.timestamp,
            source_knowledge=self.source_knowledge,
            correlation_id=self.metadata.correlation_id,
            causation_id=causation,
            policy=self.policy,
            action=action,
            suggested_delta_bps=delta,
        )


class OptimizationProposalProducedEvent(BusinessDomainEvent):
    """Event representing an optimization proposal already produced."""

    __slots__ = ("_proposal",)
    _proposal: OptimizationProposal

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        proposal: OptimizationProposal,
    ) -> None:
        if not isinstance(proposal, OptimizationProposal):
            raise OptimizationInvariantError(
                "optimization event proposal must be OptimizationProposal"
            )
        if metadata.correlation_id != proposal.correlation_id:
            raise OptimizationInvariantError(
                "optimization event correlation must match proposal"
            )
        if metadata.causation_id != proposal.causation_id:
            raise OptimizationInvariantError(
                "optimization event causation must match proposal"
            )
        object.__setattr__(self, "_proposal", proposal)
        super().__init__(
            timestamp=timestamp,
            event_name="optimization.proposal-produced",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def proposal(self) -> OptimizationProposal:
        return self._proposal

    def logical_values(self) -> tuple[object, ...]:
        return (*super().logical_values(), self._proposal.logical_values())
