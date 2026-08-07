from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.domain.commands import CommandId, CommandMetadata, CommandName
from qore.domain.events import CausationId, CorrelationId
from qore.domain.message_bus import MessageBus
from qore.functional.decisions import FunctionalDecision
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success
from qore.modules.knowledge.contracts import (
    CaptureStatisticsKnowledgeCommand,
    KnowledgeRecord,
    KnowledgeRecordId,
)
from qore.modules.optimization.contracts import (
    OptimizationPolicy,
    OptimizationProposal,
    OptimizationProposalId,
    ProposeKnowledgeOptimizationCommand,
)
from qore.modules.statistics.contracts import (
    StatisticsSnapshot,
    StatisticsSnapshotId,
    SummarizeValidationAssessmentsCommand,
)
from qore.modules.trader.contracts import ProduceVirtualTraderAnalysisCommand
from qore.modules.validation.contracts import (
    ValidateSpecialistAnalysisCommand,
    ValidationAssessment,
    ValidationAssessmentId,
    ValidationPolicy,
)
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
)


class SpecializedGovernanceError(DomainError):
    """Base error for the specialized-services decision flow."""

    __slots__ = ()


class SpecializedGovernanceValidationError(SpecializedGovernanceError):
    """Explicit violation of a specialized flow invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class SpecializedServicesDecisionFlowPlan:
    """Explicit deterministic inputs for Trader→Validation→Statistics→Knowledge→Optimization."""

    correlation_id: CorrelationId
    timestamp: datetime
    source_decision: FunctionalDecision
    trader_command_id: CommandId
    analysis_id: SpecialistAnalysisId
    analysis_kind: SpecialistKind
    analysis_confidence: SpecialistConfidence
    analysis_reasons: tuple[SpecialistReason, ...]
    validation_command_id: CommandId
    assessment_id: ValidationAssessmentId
    validation_policy: ValidationPolicy
    statistics_command_id: CommandId
    snapshot_id: StatisticsSnapshotId
    knowledge_command_id: CommandId
    knowledge_record_id: KnowledgeRecordId
    optimization_command_id: CommandId
    proposal_id: OptimizationProposalId
    optimization_policy: OptimizationPolicy

    def __post_init__(self) -> None:
        if self.source_decision.metadata.correlation_id != self.correlation_id:
            raise SpecializedGovernanceValidationError(
                "source decision correlation must match specialized flow correlation"
            )
        if not isinstance(self.analysis_reasons, tuple) or not self.analysis_reasons:
            raise SpecializedGovernanceValidationError(
                "specialized flow requires immutable non-empty analysis reasons"
            )
        causal_ids = (
            self.source_decision.decision_id.value,
            self.analysis_id.value,
            self.assessment_id.value,
            self.snapshot_id.value,
            self.knowledge_record_id.value,
            self.proposal_id.value,
        )
        if len(set(causal_ids)) != len(causal_ids):
            raise SpecializedGovernanceValidationError(
                "specialized flow causal object identities must be unique"
            )


@dataclass(frozen=True, slots=True)
class SpecializedServicesDecisionFlowResult:
    """Immutable snapshot of the complete specialized-services flow."""

    correlation_id: CorrelationId
    source_decision: FunctionalDecision
    analysis: SpecialistAnalysis
    validation: ValidationAssessment
    statistics: StatisticsSnapshot
    knowledge: KnowledgeRecord
    optimization: OptimizationProposal

    def __post_init__(self) -> None:
        expected = self.correlation_id
        if self.source_decision.metadata.correlation_id != expected:
            raise SpecializedGovernanceValidationError("source decision correlation mismatch")
        if self.analysis.metadata.correlation_id != expected:
            raise SpecializedGovernanceValidationError("analysis correlation mismatch")
        if self.validation.correlation_id != expected:
            raise SpecializedGovernanceValidationError("validation correlation mismatch")
        if self.statistics.correlation_id != expected:
            raise SpecializedGovernanceValidationError("statistics correlation mismatch")
        if self.knowledge.correlation_id != expected:
            raise SpecializedGovernanceValidationError("knowledge correlation mismatch")
        if self.optimization.correlation_id != expected:
            raise SpecializedGovernanceValidationError("optimization correlation mismatch")
        if self.analysis.metadata.causation_id != CausationId(
            self.source_decision.decision_id.value
        ):
            raise SpecializedGovernanceValidationError("analysis causation mismatch")
        if self.validation.causation_id != CausationId(self.analysis.analysis_id.value):
            raise SpecializedGovernanceValidationError("validation causation mismatch")
        if self.statistics.source_assessment_ids != (self.validation.assessment_id.value,):
            raise SpecializedGovernanceValidationError("statistics source assessment mismatch")
        if self.knowledge.source_snapshot is not self.statistics:
            raise SpecializedGovernanceValidationError("knowledge source snapshot mismatch")
        if self.optimization.source_knowledge is not self.knowledge:
            raise SpecializedGovernanceValidationError("optimization source knowledge mismatch")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.correlation_id.value),
            self.source_decision.logical_values(),
            self.analysis.logical_values(),
            self.validation.logical_values(),
            self.statistics.logical_values(),
            self.knowledge.logical_values(),
            self.optimization.logical_values(),
        )


class SpecializedServicesDecisionFlow:
    """Synchronous orchestrator using only the official MessageBus."""

    def __init__(self, *, message_bus: MessageBus) -> None:
        self._message_bus = message_bus

    def execute(
        self,
        plan: SpecializedServicesDecisionFlowPlan,
    ) -> Result[SpecializedServicesDecisionFlowResult, DomainError]:
        try:
            return self._execute(plan)
        except DomainError as error:
            return Failure(error)

    def _execute(
        self,
        plan: SpecializedServicesDecisionFlowPlan,
    ) -> Result[SpecializedServicesDecisionFlowResult, DomainError]:
        analysis_result: Result[SpecialistAnalysis, DomainError] = (
            self._message_bus.dispatch_command(
                ProduceVirtualTraderAnalysisCommand(
                    command_id=plan.trader_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("virtual-trader.produce-analysis"),
                    metadata=CommandMetadata(
                        correlation_id=plan.correlation_id,
                        causation_id=CausationId(plan.source_decision.decision_id.value),
                    ),
                    analysis_id=plan.analysis_id,
                    source_decision=plan.source_decision,
                    kind=plan.analysis_kind,
                    confidence=plan.analysis_confidence,
                    reasons=plan.analysis_reasons,
                )
            )
        )
        if isinstance(analysis_result, Failure):
            return Failure(analysis_result.error)
        analysis = analysis_result.value
        if analysis.analysis_id != plan.analysis_id:
            return Failure(SpecializedGovernanceValidationError("analysis identity mismatch"))
        if analysis.metadata.correlation_id != plan.correlation_id:
            return Failure(SpecializedGovernanceValidationError("analysis correlation mismatch"))
        if analysis.metadata.causation_id != CausationId(plan.source_decision.decision_id.value):
            return Failure(SpecializedGovernanceValidationError("analysis causation mismatch"))

        validation_result: Result[ValidationAssessment, DomainError] = (
            self._message_bus.dispatch_command(
                ValidateSpecialistAnalysisCommand(
                    command_id=plan.validation_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("validation.validate-specialist-analysis"),
                    metadata=CommandMetadata(
                        correlation_id=plan.correlation_id,
                        causation_id=CausationId(analysis.analysis_id.value),
                    ),
                    assessment_id=plan.assessment_id,
                    source_analysis=analysis,
                    policy=plan.validation_policy,
                )
            )
        )
        if isinstance(validation_result, Failure):
            return Failure(validation_result.error)
        validation = validation_result.value
        if validation.assessment_id != plan.assessment_id:
            return Failure(SpecializedGovernanceValidationError("validation identity mismatch"))
        if validation.source_analysis_id != analysis.analysis_id:
            return Failure(SpecializedGovernanceValidationError("validation source mismatch"))
        if validation.correlation_id != plan.correlation_id:
            return Failure(SpecializedGovernanceValidationError("validation correlation mismatch"))

        statistics_result: Result[StatisticsSnapshot, DomainError] = (
            self._message_bus.dispatch_command(
                SummarizeValidationAssessmentsCommand(
                    command_id=plan.statistics_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("statistics.summarize-validation-assessments"),
                    metadata=CommandMetadata(
                        correlation_id=plan.correlation_id,
                        causation_id=CausationId(validation.assessment_id.value),
                    ),
                    snapshot_id=plan.snapshot_id,
                    assessments=(validation,),
                )
            )
        )
        if isinstance(statistics_result, Failure):
            return Failure(statistics_result.error)
        statistics = statistics_result.value
        if statistics.snapshot_id != plan.snapshot_id:
            return Failure(SpecializedGovernanceValidationError("statistics identity mismatch"))
        if statistics.source_assessment_ids != (validation.assessment_id.value,):
            return Failure(SpecializedGovernanceValidationError("statistics source mismatch"))
        if statistics.correlation_id != plan.correlation_id:
            return Failure(SpecializedGovernanceValidationError("statistics correlation mismatch"))

        knowledge_result: Result[KnowledgeRecord, DomainError] = (
            self._message_bus.dispatch_command(
                CaptureStatisticsKnowledgeCommand(
                    command_id=plan.knowledge_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("knowledge.capture-statistics"),
                    metadata=CommandMetadata(
                        correlation_id=plan.correlation_id,
                        causation_id=CausationId(statistics.snapshot_id.value),
                    ),
                    record_id=plan.knowledge_record_id,
                    source_snapshot=statistics,
                )
            )
        )
        if isinstance(knowledge_result, Failure):
            return Failure(knowledge_result.error)
        knowledge = knowledge_result.value
        if knowledge.record_id != plan.knowledge_record_id:
            return Failure(SpecializedGovernanceValidationError("knowledge identity mismatch"))
        if knowledge.source_snapshot is not statistics:
            return Failure(SpecializedGovernanceValidationError("knowledge source mismatch"))
        if knowledge.correlation_id != plan.correlation_id:
            return Failure(SpecializedGovernanceValidationError("knowledge correlation mismatch"))

        optimization_result: Result[OptimizationProposal, DomainError] = (
            self._message_bus.dispatch_command(
                ProposeKnowledgeOptimizationCommand(
                    command_id=plan.optimization_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("optimization.propose-knowledge"),
                    metadata=CommandMetadata(
                        correlation_id=plan.correlation_id,
                        causation_id=CausationId(knowledge.record_id.value),
                    ),
                    proposal_id=plan.proposal_id,
                    source_knowledge=knowledge,
                    policy=plan.optimization_policy,
                )
            )
        )
        if isinstance(optimization_result, Failure):
            return Failure(optimization_result.error)
        optimization = optimization_result.value
        if optimization.proposal_id != plan.proposal_id:
            return Failure(SpecializedGovernanceValidationError("optimization identity mismatch"))
        if optimization.source_knowledge is not knowledge:
            return Failure(SpecializedGovernanceValidationError("optimization source mismatch"))
        if optimization.correlation_id != plan.correlation_id:
            return Failure(SpecializedGovernanceValidationError("optimization correlation mismatch"))

        return Success(
            SpecializedServicesDecisionFlowResult(
                correlation_id=plan.correlation_id,
                source_decision=plan.source_decision,
                analysis=analysis,
                validation=validation,
                statistics=statistics,
                knowledge=knowledge,
                optimization=optimization,
            )
        )
