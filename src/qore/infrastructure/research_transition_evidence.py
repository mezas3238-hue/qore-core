from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from qore.functional.decisions import FunctionalDecision
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.infrastructure.research_execution_session import (
    QualifiedReplayObservation,
    order_qualified_replay_observations,
)
from qore.infrastructure.research_lineage_canonical import (
    _cjson,
    _sha256,
    _utc_iso,
    canonical_functional_decision,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageValidationError,
)
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchStateTransitionFingerprint,
)
from qore.infrastructure.research_strategy_state import ResearchStrategyState


@dataclass(frozen=True, slots=True)
class ResearchStateTransitionEvidence:
    evaluation_sequence_number: int
    evaluator_identity: ResearchDecisionEvaluatorIdentity
    simulated_now: datetime
    prior_state: ResearchStrategyState
    newly_visible_inputs: tuple[QualifiedReplayObservation, ...]
    next_state: ResearchStrategyState
    decisions: tuple[FunctionalDecision, ...]
    transition_fingerprint: ResearchStateTransitionFingerprint = field(
        init=False
    )

    def __post_init__(self) -> None:
        if (
            isinstance(self.evaluation_sequence_number, bool)
            or type(self.evaluation_sequence_number) is not int
            or self.evaluation_sequence_number < 0
        ):
            raise ResearchLineageValidationError(
                "evaluation_sequence_number must be non-negative int; bool rejected"
            )
        if not isinstance(
            self.evaluator_identity,
            ResearchDecisionEvaluatorIdentity,
        ):
            raise ResearchLineageValidationError(
                "evaluator_identity must be ResearchDecisionEvaluatorIdentity"
            )
        _utc_iso(self.simulated_now, field_name="transition simulated_now")
        if not isinstance(self.prior_state, ResearchStrategyState):
            raise ResearchLineageValidationError(
                "prior_state must be ResearchStrategyState"
            )
        if self.prior_state.evaluator_identity != self.evaluator_identity:
            raise ResearchLineageValidationError(
                "prior_state evaluator identity mismatch"
            )
        if (
            self.prior_state.evaluation_sequence_number
            != self.evaluation_sequence_number
        ):
            raise ResearchLineageValidationError(
                "prior_state sequence must equal transition sequence"
            )
        if not isinstance(self.next_state, ResearchStrategyState):
            raise ResearchLineageValidationError(
                "next_state must be ResearchStrategyState"
            )
        if self.next_state.evaluator_identity != self.evaluator_identity:
            raise ResearchLineageValidationError(
                "next_state evaluator identity mismatch"
            )
        if (
            self.next_state.evaluation_sequence_number
            != self.evaluation_sequence_number + 1
        ):
            raise ResearchLineageValidationError(
                "next_state sequence must equal transition sequence + 1"
            )
        if not isinstance(self.newly_visible_inputs, tuple) or any(
            not isinstance(item, QualifiedReplayObservation)
            for item in self.newly_visible_inputs
        ):
            raise ResearchLineageValidationError(
                "newly_visible_inputs must be QualifiedReplayObservation tuple"
            )
        if (
            self.newly_visible_inputs
            != order_qualified_replay_observations(
                self.newly_visible_inputs
            )
        ):
            raise ResearchLineageValidationError(
                "newly_visible_inputs must use canonical qualified ordering"
            )
        if not isinstance(self.decisions, tuple) or any(
            not isinstance(item, FunctionalDecision)
            for item in self.decisions
        ):
            raise ResearchLineageValidationError(
                "decisions must be an immutable FunctionalDecision tuple"
            )
        object.__setattr__(
            self,
            "transition_fingerprint",
            _compute_transition_fingerprint(self),
        )


def _compute_transition_fingerprint(
    transition: ResearchStateTransitionEvidence,
) -> ResearchStateTransitionFingerprint:
    if not isinstance(transition, ResearchStateTransitionEvidence):
        raise ResearchLineageValidationError(
            "transition fingerprint requires ResearchStateTransitionEvidence"
        )
    return ResearchStateTransitionFingerprint(
        value=_sha256(
            _cjson(
                {
                    "schema": "qore.research-state-transition.v1",
                    "evaluation_sequence_number": (
                        transition.evaluation_sequence_number
                    ),
                    "evaluator_family": (
                        transition.evaluator_identity.family.value
                    ),
                    "evaluator_schema_version": (
                        transition.evaluator_identity.schema_version.value
                    ),
                    "software_revision": (
                        transition.evaluator_identity.software_revision.value
                    ),
                    "simulated_now": _utc_iso(
                        transition.simulated_now,
                        field_name="transition simulated_now",
                    ),
                    "prior_state_fingerprint": (
                        transition.prior_state.state_fingerprint.value
                    ),
                    "newly_visible_inputs": [
                        qualified.canonical_projection()
                        for qualified in transition.newly_visible_inputs
                    ],
                    "next_state_fingerprint": (
                        transition.next_state.state_fingerprint.value
                    ),
                    "decisions": [
                        canonical_functional_decision(decision)
                        for decision in transition.decisions
                    ],
                }
            )
        )
    )
