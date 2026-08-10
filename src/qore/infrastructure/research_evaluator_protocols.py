from __future__ import annotations

from datetime import datetime
from typing import Protocol

from qore.functional.decisions import FunctionalDecision
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
    ResearchSpecialistEvaluatorIdentity,
)
from qore.infrastructure.research_execution_session import QualifiedReplayObservation
from qore.infrastructure.research_schedule import ResearchStartPolicy
from qore.infrastructure.research_specialist_boundary import ResearchAnalysisSpecification
from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding
from qore.infrastructure.research_strategy_state import ResearchStrategyState


class ResearchDecisionEvaluatorProtocol(Protocol):
    """Computation boundary only; it does not identify a concrete QORE producer."""

    @property
    def identity(self) -> ResearchDecisionEvaluatorIdentity: ...

    def create_initial_state(
        self,
        *,
        strategy_binding: ResearchRunStrategyBinding,
        start_policy: ResearchStartPolicy,
    ) -> ResearchStrategyState: ...

    def evaluate(
        self,
        *,
        strategy_binding: ResearchRunStrategyBinding,
        prior_state: ResearchStrategyState,
        newly_visible_inputs: tuple[QualifiedReplayObservation, ...],
        simulated_now: datetime,
    ) -> tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]]: ...


class ResearchSpecialistEvaluatorProtocol(Protocol):
    """Specialist computation boundary only; producer provenance remains unproven."""

    @property
    def identity(self) -> ResearchSpecialistEvaluatorIdentity: ...

    def evaluate(
        self,
        *,
        source_decision: FunctionalDecision,
    ) -> ResearchAnalysisSpecification: ...
