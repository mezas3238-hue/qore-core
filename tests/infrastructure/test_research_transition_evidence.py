from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
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
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageCanonicalValueError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.research_strategy_state import ResearchStrategyState
from qore.infrastructure.research_transition_evidence import ResearchStateTransitionEvidence


@dataclass(frozen=True, slots=True)
class _Content:
    value: int

    def logical_values(self) -> Mapping[str, object]:
        return {"value": self.value}


_IDENTITY = ResearchDecisionEvaluatorIdentity(
    family=ResearchDecisionEvaluatorFamily("test.reference"),
    schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
    software_revision=ResearchSoftwareRevision("revision-1"),
)


def _state(sequence: int, value: int) -> ResearchStrategyState:
    return ResearchStrategyState(
        evaluator_identity=_IDENTITY,
        evaluation_sequence_number=sequence,
        state_schema_version="v1",
        exact_content=_Content(value),
    )


def _decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(UUID("58000000-0000-0000-0000-000000000001")),
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        decision_type=DecisionType("research.test"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(
                UUID("58000000-0000-0000-0000-000000000002")
            ),
            attributes=MappingProxyType({}),
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.test"),
                summary="resolved for test",
                attributes=MappingProxyType({}),
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def test_transition_supports_zero_or_more_ordered_decisions() -> None:
    zero = ResearchStateTransitionEvidence(
        evaluation_sequence_number=0,
        evaluator_identity=_IDENTITY,
        simulated_now=datetime(2026, 1, 1, tzinfo=UTC),
        prior_state=_state(0, 0),
        newly_visible_inputs=(),
        next_state=_state(1, 1),
        decisions=(),
    )
    one = ResearchStateTransitionEvidence(
        evaluation_sequence_number=0,
        evaluator_identity=_IDENTITY,
        simulated_now=datetime(2026, 1, 1, tzinfo=UTC),
        prior_state=_state(0, 0),
        newly_visible_inputs=(),
        next_state=_state(1, 1),
        decisions=(_decision(),),
    )
    assert zero.decisions == ()
    assert len(one.decisions) == 1
    assert zero.transition_fingerprint != one.transition_fingerprint


def test_transition_enforces_state_sequence_and_runtime_types() -> None:
    with pytest.raises(ResearchLineageValidationError):
        ResearchStateTransitionEvidence(
            evaluation_sequence_number=0,
            evaluator_identity=_IDENTITY,
            simulated_now=datetime(2026, 1, 1, tzinfo=UTC),
            prior_state=_state(0, 0),
            newly_visible_inputs=(),
            next_state=_state(2, 1),
            decisions=(),
        )
    with pytest.raises(ResearchLineageValidationError):
        ResearchStateTransitionEvidence(
            evaluation_sequence_number=0,
            evaluator_identity=_IDENTITY,
            simulated_now=datetime(2026, 1, 1, tzinfo=UTC),
            prior_state=_state(0, 0),
            newly_visible_inputs=(),
            next_state=_state(1, 1),
            decisions=(object(),),  # type: ignore[arg-type]
        )


def test_transition_rejects_naive_simulated_time() -> None:
    with pytest.raises(ResearchLineageCanonicalValueError):
        ResearchStateTransitionEvidence(
            evaluation_sequence_number=0,
            evaluator_identity=_IDENTITY,
            simulated_now=datetime(2026, 1, 1),
            prior_state=_state(0, 0),
            newly_visible_inputs=(),
            next_state=_state(1, 1),
            decisions=(),
        )
