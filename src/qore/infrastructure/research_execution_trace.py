from __future__ import annotations

from dataclasses import dataclass, field

from qore.functional.decisions import FunctionalDecision
from qore.infrastructure.replay_clock import ReplayClock
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.infrastructure.research_evaluator_protocols import (
    ResearchDecisionEvaluatorProtocol,
)
from qore.infrastructure.research_execution_session import (
    ResearchExecutionSession,
    derive_schedule_a_instants,
    order_qualified_replay_observations,
)
from qore.infrastructure.research_lineage_canonical import _cjson, _sha256
from qore.infrastructure.research_lineage_errors import (
    ResearchEvaluatorIdentityMismatchError,
    ResearchExecutionTraceValidationError,
    ResearchLineageError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchExecutionTraceFingerprint,
)
from qore.infrastructure.research_schedule import (
    SCHEDULE_A_V1,
    W1_NO_WARMUP_V1,
    ResearchScheduleSemantics,
    ResearchStartPolicy,
)
from qore.infrastructure.research_strategy_state import ResearchStrategyState
from qore.infrastructure.research_transition_evidence import (
    ResearchStateTransitionEvidence,
)


def _enforce_schedule_a_membership(trace: ResearchExecutionTrace) -> None:
    if trace.schedule_semantics != SCHEDULE_A_V1:
        raise ResearchExecutionTraceValidationError(
            "Phase 1A supports Schedule A only"
        )
    if trace.start_policy != W1_NO_WARMUP_V1:
        raise ResearchExecutionTraceValidationError(
            "Phase 1A supports W1 no-warmup only"
        )
    expected_instants = derive_schedule_a_instants(trace.execution_session)
    if len(trace.transitions) != len(expected_instants):
        raise ResearchExecutionTraceValidationError(
            "transition count does not equal exact Schedule A instant count"
        )
    for index, (transition, expected_now) in enumerate(
        zip(trace.transitions, expected_instants, strict=True)
    ):
        if transition.simulated_now != expected_now:
            raise ResearchExecutionTraceValidationError(
                f"transition {index} simulated_now does not equal Schedule A instant"
            )
        expected_inputs = order_qualified_replay_observations(
            tuple(
                qualified
                for qualified in trace.execution_session.qualified_observations
                if qualified.observation.available_at == expected_now
            )
        )
        if transition.newly_visible_inputs != expected_inputs:
            raise ResearchExecutionTraceValidationError(
                f"transition {index} newly_visible_inputs do not equal "
                "session-derived newly visible evidence"
            )


@dataclass(frozen=True, slots=True)
class ResearchExecutionTrace:
    execution_session: ResearchExecutionSession
    evaluator_identity: ResearchDecisionEvaluatorIdentity
    start_policy: ResearchStartPolicy
    schedule_semantics: ResearchScheduleSemantics
    initial_state: ResearchStrategyState
    transitions: tuple[ResearchStateTransitionEvidence, ...]
    final_state: ResearchStrategyState
    trace_fingerprint: ResearchExecutionTraceFingerprint = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.execution_session, ResearchExecutionSession):
            raise ResearchExecutionTraceValidationError(
                "execution_session must be ResearchExecutionSession"
            )
        if not isinstance(
            self.evaluator_identity,
            ResearchDecisionEvaluatorIdentity,
        ):
            raise ResearchExecutionTraceValidationError(
                "evaluator_identity must be ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.start_policy, ResearchStartPolicy):
            raise ResearchExecutionTraceValidationError(
                "start_policy must be ResearchStartPolicy"
            )
        if not isinstance(
            self.schedule_semantics,
            ResearchScheduleSemantics,
        ):
            raise ResearchExecutionTraceValidationError(
                "schedule_semantics must be ResearchScheduleSemantics"
            )
        if not isinstance(self.initial_state, ResearchStrategyState):
            raise ResearchExecutionTraceValidationError(
                "initial_state must be ResearchStrategyState"
            )
        if not isinstance(self.final_state, ResearchStrategyState):
            raise ResearchExecutionTraceValidationError(
                "final_state must be ResearchStrategyState"
            )
        run_revision = (
            self.execution_session.strategy_binding.run.software_revision.value
        )
        if self.evaluator_identity.software_revision.value != run_revision:
            raise ResearchExecutionTraceValidationError(
                "evaluator software revision must equal retained run revision"
            )
        if self.initial_state.evaluation_sequence_number != 0:
            raise ResearchExecutionTraceValidationError(
                "initial_state sequence must be zero"
            )
        if self.initial_state.evaluator_identity != self.evaluator_identity:
            raise ResearchExecutionTraceValidationError(
                "initial_state evaluator identity mismatch"
            )
        if not isinstance(self.transitions, tuple):
            raise ResearchExecutionTraceValidationError(
                "transitions must be tuple"
            )
        for index, transition in enumerate(self.transitions):
            if not isinstance(
                transition,
                ResearchStateTransitionEvidence,
            ):
                raise ResearchExecutionTraceValidationError(
                    f"transition {index} has wrong type"
                )
            if transition.evaluation_sequence_number != index:
                raise ResearchExecutionTraceValidationError(
                    f"transition {index} has non-canonical sequence"
                )
            if transition.evaluator_identity != self.evaluator_identity:
                raise ResearchExecutionTraceValidationError(
                    f"transition {index} evaluator identity mismatch"
                )
            expected_prior = (
                self.initial_state
                if index == 0
                else self.transitions[index - 1].next_state
            )
            if transition.prior_state != expected_prior:
                raise ResearchExecutionTraceValidationError(
                    f"transition {index} prior_state breaks trace continuity"
                )
        expected_final = (
            self.transitions[-1].next_state
            if self.transitions
            else self.initial_state
        )
        if self.final_state != expected_final:
            raise ResearchExecutionTraceValidationError(
                "final_state does not equal exact trace terminal state"
            )
        _enforce_schedule_a_membership(self)
        object.__setattr__(
            self,
            "trace_fingerprint",
            _compute_trace_fingerprint(self),
        )


def _compute_trace_fingerprint(
    trace: ResearchExecutionTrace,
) -> ResearchExecutionTraceFingerprint:
    if not isinstance(trace, ResearchExecutionTrace):
        raise ResearchExecutionTraceValidationError(
            "trace fingerprint requires ResearchExecutionTrace"
        )
    return ResearchExecutionTraceFingerprint(
        value=_sha256(
            _cjson(
                {
                    "schema": "qore.research-execution-trace.v1",
                    "execution_session_fingerprint": (
                        trace.execution_session.session_fingerprint.value
                    ),
                    "evaluator_family": trace.evaluator_identity.family.value,
                    "evaluator_schema_version": (
                        trace.evaluator_identity.schema_version.value
                    ),
                    "software_revision": (
                        trace.evaluator_identity.software_revision.value
                    ),
                    "schedule_semantics": trace.schedule_semantics.identity,
                    "start_policy": trace.start_policy.identity,
                    "initial_state_fingerprint": (
                        trace.initial_state.state_fingerprint.value
                    ),
                    "transition_fingerprints": [
                        transition.transition_fingerprint.value
                        for transition in trace.transitions
                    ],
                    "final_state_fingerprint": (
                        trace.final_state.state_fingerprint.value
                    ),
                }
            )
        )
    )


def _evaluator_identity(
    evaluator: ResearchDecisionEvaluatorProtocol,
) -> ResearchDecisionEvaluatorIdentity:
    try:
        identity = evaluator.identity
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            f"evaluator.identity raised unexpected error: {exc!r}"
        ) from exc
    if not isinstance(identity, ResearchDecisionEvaluatorIdentity):
        raise ResearchLineageValidationError(
            "evaluator.identity must be ResearchDecisionEvaluatorIdentity"
        )
    return identity


def verify_trace_reproducibility(
    trace: ResearchExecutionTrace,
    evaluator: ResearchDecisionEvaluatorProtocol,
) -> bool:
    if not isinstance(trace, ResearchExecutionTrace):
        raise ResearchLineageValidationError(
            "trace must be ResearchExecutionTrace"
        )
    identity = _evaluator_identity(evaluator)
    if identity != trace.evaluator_identity:
        raise ResearchEvaluatorIdentityMismatchError(
            "evaluator identity does not equal retained trace identity"
        )
    create_initial_state = getattr(evaluator, "create_initial_state", None)
    if not callable(create_initial_state):
        raise ResearchLineageValidationError(
            "evaluator must expose callable create_initial_state()"
        )
    evaluate = getattr(evaluator, "evaluate", None)
    if not callable(evaluate):
        raise ResearchLineageValidationError(
            "evaluator must expose callable evaluate()"
        )
    try:
        reproduced_initial = create_initial_state(
            strategy_binding=trace.execution_session.strategy_binding,
            start_policy=trace.start_policy,
        )
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            f"create_initial_state() raised unexpected error: {exc!r}"
        ) from exc
    if not isinstance(reproduced_initial, ResearchStrategyState):
        raise ResearchLineageValidationError(
            "create_initial_state() must return ResearchStrategyState"
        )
    if reproduced_initial != trace.initial_state:
        return False

    clock = ReplayClock(
        trace.execution_session.strategy_binding.run.simulated_start
    )
    reproduced_state = reproduced_initial
    for transition in trace.transitions:
        if transition.prior_state != reproduced_state:
            return False
        clock.advance_to(transition.simulated_now)
        try:
            result = evaluate(
                strategy_binding=trace.execution_session.strategy_binding,
                prior_state=reproduced_state,
                newly_visible_inputs=transition.newly_visible_inputs,
                simulated_now=transition.simulated_now,
            )
        except ResearchLineageError:
            raise
        except Exception as exc:
            raise ResearchLineageValidationError(
                f"evaluate() raised unexpected error: {exc!r}"
            ) from exc
        if not isinstance(result, tuple) or len(result) != 2:
            raise ResearchLineageValidationError(
                "evaluate() must return "
                "tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]]"
            )
        reproduced_next_state, reproduced_decisions = result
        if not isinstance(reproduced_next_state, ResearchStrategyState):
            raise ResearchLineageValidationError(
                "evaluate() next_state must be ResearchStrategyState"
            )
        if not isinstance(reproduced_decisions, tuple):
            raise ResearchLineageValidationError(
                "evaluate() decisions must be tuple"
            )
        if any(
            not isinstance(decision, FunctionalDecision)
            for decision in reproduced_decisions
        ):
            raise ResearchLineageValidationError(
                "every evaluate() decision must be FunctionalDecision"
            )
        if reproduced_next_state != transition.next_state:
            return False
        if reproduced_decisions != transition.decisions:
            return False
        reproduced_state = reproduced_next_state
    return reproduced_state == trace.final_state
