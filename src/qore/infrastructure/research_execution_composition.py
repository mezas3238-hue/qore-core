from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import TYPE_CHECKING

from qore.functional.decisions import DecisionStatus, FunctionalDecision
from qore.infrastructure.research_analysis_lineage import (
    ResearchAnalysisLineageRecord,
    construct_research_trader_command,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
    ResearchSpecialistEvaluatorIdentity,
)
from qore.infrastructure.research_execution_session import (
    derive_schedule_a_instants,
    order_qualified_replay_observations,
)
from qore.infrastructure.research_execution_trace import (
    ResearchExecutionTrace,
    verify_trace_reproducibility,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchEvaluatorIdentityMismatchError,
    ResearchExecutionTraceValidationError,
    ResearchLineageError,
    ResearchLineageFingerprintError,
    ResearchLineageValidationError,
    ResearchSpecialistEvaluatorIdentityMismatchError,
)
from qore.infrastructure.research_schedule import SCHEDULE_A_V1, W1_NO_WARMUP_V1
from qore.infrastructure.research_specialist_boundary import (
    ResearchAnalysisInputEvidence,
    ResearchAnalysisSpecification,
)
from qore.infrastructure.research_strategy_state import ResearchStrategyState
from qore.infrastructure.research_transition_evidence import (
    ResearchStateTransitionEvidence,
)

from .research_producer_admission import (
    ResearchProducerAdmissionEvidence,
    _compute_admission_fingerprint,
)

if TYPE_CHECKING:
    from datetime import datetime

    from qore.infrastructure.research_evaluator_protocols import (
        ResearchDecisionEvaluatorProtocol,
        ResearchSpecialistEvaluatorProtocol,
    )
    from qore.infrastructure.research_execution_session import (
        QualifiedReplayObservation,
        ResearchExecutionSession,
    )
    from qore.infrastructure.research_lineage_fingerprints import (
        ResearchExecutionTraceFingerprint,
    )
    from qore.infrastructure.research_schedule import ResearchStartPolicy
    from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding

    from .research_producer_admission import ResearchProducerAdmissionFingerprint


class ResearchProducerCoverageError(ResearchLineageValidationError):
    """RESOLVED decision coverage is incomplete, duplicated, or reordered."""

    __slots__ = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ResearchProducerLineageOutcomeFingerprint:
    """Canonical SHA-256 digest of one complete Phase 1B producer outcome."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise ResearchLineageFingerprintError(
                f"producer outcome fingerprint value must be str, got "
                f"{type(self.value).__qualname__}"
            )
        if len(self.value) != 64 or any(
            character not in "0123456789abcdef" for character in self.value
        ):
            raise ResearchLineageFingerprintError(
                "producer outcome fingerprint must be 64 lowercase hex characters"
            )

    @classmethod
    def from_canonical_bytes(
        cls,
        data: bytes,
    ) -> ResearchProducerLineageOutcomeFingerprint:
        if not isinstance(data, bytes):
            raise ResearchLineageFingerprintError(
                "producer outcome canonical material must be bytes"
            )
        return cls(hashlib.sha256(data).hexdigest())


@dataclasses.dataclass(frozen=True, slots=True)
class ResearchProducerLineageOutcome:
    """Immutable producer-composition evidence retaining exact computational identities."""

    admission_evidence: ResearchProducerAdmissionEvidence
    decision_evaluator_identity: ResearchDecisionEvaluatorIdentity
    specialist_evaluator_identity: ResearchSpecialistEvaluatorIdentity
    trace: ResearchExecutionTrace
    lineage_records: tuple[ResearchAnalysisLineageRecord, ...]
    outcome_fingerprint: ResearchProducerLineageOutcomeFingerprint = dataclasses.field(
        init=False
    )

    def __post_init__(self) -> None:
        _validate_outcome_field_types(self)
        _validate_outcome_graph(self)
        fingerprint = _compute_outcome_fingerprint(
            self.admission_evidence.admission_fingerprint,
            self.decision_evaluator_identity,
            self.specialist_evaluator_identity,
            self.trace.trace_fingerprint,
            self.lineage_records,
        )
        object.__setattr__(self, "outcome_fingerprint", fingerprint)


def _validate_outcome_field_types(outcome: ResearchProducerLineageOutcome) -> None:
    if not isinstance(outcome.admission_evidence, ResearchProducerAdmissionEvidence):
        raise ResearchLineageValidationError(
            "admission_evidence must be ResearchProducerAdmissionEvidence"
        )
    if not isinstance(
        outcome.decision_evaluator_identity,
        ResearchDecisionEvaluatorIdentity,
    ):
        raise ResearchLineageValidationError(
            "decision_evaluator_identity must be ResearchDecisionEvaluatorIdentity"
        )
    if not isinstance(
        outcome.specialist_evaluator_identity,
        ResearchSpecialistEvaluatorIdentity,
    ):
        raise ResearchLineageValidationError(
            "specialist_evaluator_identity must be ResearchSpecialistEvaluatorIdentity"
        )
    if not isinstance(outcome.trace, ResearchExecutionTrace):
        raise ResearchLineageValidationError("trace must be ResearchExecutionTrace")
    if not isinstance(outcome.lineage_records, tuple):
        raise ResearchLineageValidationError("lineage_records must be tuple")
    for index, record in enumerate(outcome.lineage_records):
        if not isinstance(record, ResearchAnalysisLineageRecord):
            raise ResearchLineageValidationError(
                f"lineage_records[{index}] must be ResearchAnalysisLineageRecord"
            )


def _revalidate_retained_lineage_record(
    record: ResearchAnalysisLineageRecord,
) -> None:
    if not isinstance(record, ResearchAnalysisLineageRecord):
        raise ResearchLineageValidationError(
            "retained lineage record must be ResearchAnalysisLineageRecord"
        )
    try:
        reconstructed = ResearchAnalysisLineageRecord(
            trace=record.trace,
            decision_transition_index=record.decision_transition_index,
            decision_index_within_transition=record.decision_index_within_transition,
            analysis_input_evidence=record.analysis_input_evidence,
            trader_command=record.trader_command,
            analysis=record.analysis,
        )
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            "retained lineage record structural revalidation raised unexpected error"
        ) from exc
    if reconstructed != record:
        raise ResearchLineageValidationError(
            "retained lineage record differs from deterministic reconstruction"
        )


def _enforce_coverage_bijection(
    trace: ResearchExecutionTrace,
    lineage_records: tuple[ResearchAnalysisLineageRecord, ...],
) -> None:
    expected_keys = tuple(
        (transition.evaluation_sequence_number, decision_index)
        for transition in trace.transitions
        for decision_index, decision in enumerate(transition.decisions)
        if decision.status is DecisionStatus.RESOLVED
    )
    actual_keys = tuple(
        (
            record.decision_transition_index,
            record.decision_index_within_transition,
        )
        for record in lineage_records
    )
    if actual_keys != expected_keys:
        raise ResearchProducerCoverageError(
            "RESOLVED decision coverage mismatch"
        )


def _validate_outcome_graph(outcome: ResearchProducerLineageOutcome) -> None:
    if outcome.trace.execution_session != outcome.admission_evidence.execution_session:
        raise ResearchLineageValidationError(
            "trace.execution_session must equal admission execution_session"
        )
    if outcome.decision_evaluator_identity != outcome.trace.evaluator_identity:
        raise ResearchLineageValidationError(
            "decision evaluator identity must equal trace evaluator identity"
        )

    for record in outcome.lineage_records:
        _revalidate_retained_lineage_record(record)
        if record.trace != outcome.trace:
            raise ResearchLineageValidationError(
                "record trace must equal outcome trace"
            )

        transition_index = record.decision_transition_index
        decision_index = record.decision_index_within_transition
        if (
            isinstance(transition_index, bool)
            or type(transition_index) is not int
            or transition_index < 0
        ):
            raise ResearchLineageValidationError(
                "decision_transition_index must be non-negative int; bool rejected"
            )
        if (
            isinstance(decision_index, bool)
            or type(decision_index) is not int
            or decision_index < 0
        ):
            raise ResearchLineageValidationError(
                "decision_index_within_transition must be non-negative int; bool rejected"
            )
        if transition_index >= len(outcome.trace.transitions):
            raise ResearchLineageValidationError(
                "decision_transition_index outside retained trace"
            )
        transition = outcome.trace.transitions[transition_index]
        if decision_index >= len(transition.decisions):
            raise ResearchLineageValidationError(
                "decision_index_within_transition outside retained transition"
            )
        expected_decision = transition.decisions[decision_index]
        if record.analysis_input_evidence.source_decision != expected_decision:
            raise ResearchLineageValidationError(
                "analysis input source decision must equal exact retained decision"
            )
        if (
            record.analysis_input_evidence.evaluator_identity
            != outcome.specialist_evaluator_identity
        ):
            raise ResearchLineageValidationError(
                "analysis input evaluator identity must equal retained specialist identity"
            )

    _enforce_coverage_bijection(outcome.trace, outcome.lineage_records)


def _project_evaluator_identity(
    identity: ResearchDecisionEvaluatorIdentity | ResearchSpecialistEvaluatorIdentity,
) -> dict[str, str]:
    return {
        "family": identity.family.value,
        "schema_version": identity.schema_version.value,
        "software_revision": identity.software_revision.value,
    }


def _compute_outcome_fingerprint(
    admission_fingerprint: ResearchProducerAdmissionFingerprint,
    decision_evaluator_identity: ResearchDecisionEvaluatorIdentity,
    specialist_evaluator_identity: ResearchSpecialistEvaluatorIdentity,
    trace_fingerprint: ResearchExecutionTraceFingerprint,
    lineage_records: tuple[ResearchAnalysisLineageRecord, ...],
) -> ResearchProducerLineageOutcomeFingerprint:
    projection = {
        "schema": "qore.research.producer.lineage.v1",
        "admission_fingerprint": admission_fingerprint.value,
        "decision_evaluator_identity": _project_evaluator_identity(
            decision_evaluator_identity
        ),
        "specialist_evaluator_identity": _project_evaluator_identity(
            specialist_evaluator_identity
        ),
        "trace_fingerprint": trace_fingerprint.value,
        "lineage_record_fingerprints": [
            record.lineage_fingerprint.value for record in lineage_records
        ],
    }
    canonical_bytes = json.dumps(
        projection,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchProducerLineageOutcomeFingerprint.from_canonical_bytes(
        canonical_bytes
    )


def _safe_resolve_decision_identity(
    evaluator: ResearchDecisionEvaluatorProtocol,
) -> ResearchDecisionEvaluatorIdentity:
    try:
        identity = evaluator.identity
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            "decision evaluator identity resolution failed"
        ) from exc
    if not isinstance(identity, ResearchDecisionEvaluatorIdentity):
        raise ResearchLineageValidationError(
            "decision evaluator identity must be ResearchDecisionEvaluatorIdentity"
        )
    return identity


def _validate_decision_revision(
    session: ResearchExecutionSession,
    decision_identity: ResearchDecisionEvaluatorIdentity,
) -> None:
    run_revision_value = session.strategy_binding.run.software_revision.value
    if decision_identity.software_revision.value != run_revision_value:
        raise ResearchExecutionTraceValidationError(
            "decision evaluator software revision must equal retained run revision"
        )


def _safe_create_initial_state(
    decision_evaluator: ResearchDecisionEvaluatorProtocol,
    strategy_binding: ResearchRunStrategyBinding,
    start_policy: ResearchStartPolicy,
    production_start_identity: ResearchDecisionEvaluatorIdentity,
) -> ResearchStrategyState:
    pre_identity = _safe_resolve_decision_identity(decision_evaluator)
    if pre_identity != production_start_identity:
        raise ResearchEvaluatorIdentityMismatchError(
            "decision evaluator identity changed before initial-state creation"
        )
    try:
        state = decision_evaluator.create_initial_state(
            strategy_binding=strategy_binding,
            start_policy=start_policy,
        )
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            "create_initial_state raised unexpected error"
        ) from exc
    post_identity = _safe_resolve_decision_identity(decision_evaluator)
    if post_identity != production_start_identity:
        raise ResearchEvaluatorIdentityMismatchError(
            "decision evaluator identity changed during initial-state creation"
        )
    if not isinstance(state, ResearchStrategyState):
        raise ResearchLineageValidationError(
            "create_initial_state must return ResearchStrategyState"
        )
    return state


def _safe_evaluate_decision(
    decision_evaluator: ResearchDecisionEvaluatorProtocol,
    strategy_binding: ResearchRunStrategyBinding,
    prior_state: ResearchStrategyState,
    newly_visible_inputs: tuple[QualifiedReplayObservation, ...],
    simulated_now: datetime,
    production_start_identity: ResearchDecisionEvaluatorIdentity,
) -> tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]]:
    pre_identity = _safe_resolve_decision_identity(decision_evaluator)
    if pre_identity != production_start_identity:
        raise ResearchEvaluatorIdentityMismatchError(
            "decision evaluator identity changed before evaluation"
        )
    try:
        result = decision_evaluator.evaluate(
            strategy_binding=strategy_binding,
            prior_state=prior_state,
            newly_visible_inputs=newly_visible_inputs,
            simulated_now=simulated_now,
        )
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            "decision evaluator raised unexpected error"
        ) from exc
    post_identity = _safe_resolve_decision_identity(decision_evaluator)
    if post_identity != production_start_identity:
        raise ResearchEvaluatorIdentityMismatchError(
            "decision evaluator identity changed during evaluation"
        )
    if not isinstance(result, tuple) or len(result) != 2:
        raise ResearchLineageValidationError(
            "evaluate must return a two-item tuple"
        )
    next_state, decisions = result
    if not isinstance(next_state, ResearchStrategyState):
        raise ResearchLineageValidationError(
            "evaluate next_state must be ResearchStrategyState"
        )
    if not isinstance(decisions, tuple):
        raise ResearchLineageValidationError("evaluate decisions must be tuple")
    if any(not isinstance(decision, FunctionalDecision) for decision in decisions):
        raise ResearchLineageValidationError(
            "every evaluate decision must be FunctionalDecision"
        )
    return next_state, decisions


def _safe_resolve_specialist_identity(
    specialist: ResearchSpecialistEvaluatorProtocol,
) -> ResearchSpecialistEvaluatorIdentity:
    try:
        identity = specialist.identity
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            "specialist evaluator identity resolution failed"
        ) from exc
    if not isinstance(identity, ResearchSpecialistEvaluatorIdentity):
        raise ResearchLineageValidationError(
            "specialist evaluator identity must be ResearchSpecialistEvaluatorIdentity"
        )
    return identity


def _safe_evaluate_specialist(
    specialist_evaluator: ResearchSpecialistEvaluatorProtocol,
    source_decision: FunctionalDecision,
    production_start_identity: ResearchSpecialistEvaluatorIdentity,
) -> ResearchAnalysisSpecification:
    pre_identity = _safe_resolve_specialist_identity(specialist_evaluator)
    if pre_identity != production_start_identity:
        raise ResearchSpecialistEvaluatorIdentityMismatchError(
            "specialist evaluator identity changed before evaluation"
        )
    try:
        specification = specialist_evaluator.evaluate(source_decision=source_decision)
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            "specialist evaluator raised unexpected error"
        ) from exc
    post_identity = _safe_resolve_specialist_identity(specialist_evaluator)
    if post_identity != production_start_identity:
        raise ResearchSpecialistEvaluatorIdentityMismatchError(
            "specialist evaluator identity changed during evaluation"
        )
    if not isinstance(specification, ResearchAnalysisSpecification):
        raise ResearchLineageValidationError(
            "specialist evaluator must return ResearchAnalysisSpecification"
        )
    return specification


class ResearchExecutionComposition:
    """Approved Phase 1B composition shell; it contains no concrete methodology."""

    __slots__ = (
        "_admission_evidence",
        "_decision_evaluator",
        "_specialist_evaluator",
    )

    def __init__(
        self,
        *,
        admission_evidence: ResearchProducerAdmissionEvidence,
        decision_evaluator: ResearchDecisionEvaluatorProtocol,
        specialist_evaluator: ResearchSpecialistEvaluatorProtocol,
    ) -> None:
        if not isinstance(admission_evidence, ResearchProducerAdmissionEvidence):
            raise ResearchLineageValidationError(
                "admission_evidence must be ResearchProducerAdmissionEvidence"
            )
        self._admission_evidence = admission_evidence
        self._decision_evaluator = decision_evaluator
        self._specialist_evaluator = specialist_evaluator

    def produce(self) -> ResearchProducerLineageOutcome:
        session = self._admission_evidence.execution_session
        decision_identity = _safe_resolve_decision_identity(self._decision_evaluator)
        _validate_decision_revision(session, decision_identity)
        specialist_identity = _safe_resolve_specialist_identity(
            self._specialist_evaluator
        )

        initial_state = _safe_create_initial_state(
            self._decision_evaluator,
            session.strategy_binding,
            W1_NO_WARMUP_V1,
            decision_identity,
        )
        current_state = initial_state
        transitions: list[ResearchStateTransitionEvidence] = []

        for sequence, simulated_now in enumerate(derive_schedule_a_instants(session)):
            observations_at_now = tuple(
                item
                for item in session.qualified_observations
                if item.observation.available_at == simulated_now
            )
            newly_visible_inputs = order_qualified_replay_observations(
                observations_at_now
            )
            next_state, decisions = _safe_evaluate_decision(
                self._decision_evaluator,
                session.strategy_binding,
                current_state,
                newly_visible_inputs,
                simulated_now,
                decision_identity,
            )
            transitions.append(
                ResearchStateTransitionEvidence(
                    evaluation_sequence_number=sequence,
                    evaluator_identity=decision_identity,
                    simulated_now=simulated_now,
                    prior_state=current_state,
                    newly_visible_inputs=newly_visible_inputs,
                    next_state=next_state,
                    decisions=decisions,
                )
            )
            current_state = next_state

        trace = ResearchExecutionTrace(
            execution_session=session,
            evaluator_identity=decision_identity,
            start_policy=W1_NO_WARMUP_V1,
            schedule_semantics=SCHEDULE_A_V1,
            initial_state=initial_state,
            transitions=tuple(transitions),
            final_state=current_state,
        )

        lineage_records: list[ResearchAnalysisLineageRecord] = []
        for transition_index, transition in enumerate(trace.transitions):
            for decision_index, decision in enumerate(transition.decisions):
                if decision.status is not DecisionStatus.RESOLVED:
                    continue
                analysis_specification = _safe_evaluate_specialist(
                    self._specialist_evaluator,
                    decision,
                    specialist_identity,
                )
                analysis_input_evidence = ResearchAnalysisInputEvidence(
                    evaluator_identity=specialist_identity,
                    source_decision=decision,
                    analysis_specification=analysis_specification,
                )
                command = construct_research_trader_command(
                    trace,
                    transition_index,
                    decision_index,
                    analysis_input_evidence,
                )
                lineage_records.append(
                    ResearchAnalysisLineageRecord(
                        trace=trace,
                        decision_transition_index=transition_index,
                        decision_index_within_transition=decision_index,
                        analysis_input_evidence=analysis_input_evidence,
                        trader_command=command,
                        analysis=command.to_analysis(),
                    )
                )

        retained_records = tuple(lineage_records)
        _enforce_coverage_bijection(trace, retained_records)

        final_specialist_identity = _safe_resolve_specialist_identity(
            self._specialist_evaluator
        )
        if final_specialist_identity != specialist_identity:
            raise ResearchSpecialistEvaluatorIdentityMismatchError(
                "specialist evaluator identity drifted during composition"
            )
        final_decision_identity = _safe_resolve_decision_identity(
            self._decision_evaluator
        )
        if final_decision_identity != decision_identity:
            raise ResearchEvaluatorIdentityMismatchError(
                "decision evaluator identity drifted during composition"
            )

        return ResearchProducerLineageOutcome(
            admission_evidence=self._admission_evidence,
            decision_evaluator_identity=decision_identity,
            specialist_evaluator_identity=specialist_identity,
            trace=trace,
            lineage_records=retained_records,
        )


def _verify_decision_side(
    outcome: ResearchProducerLineageOutcome,
    decision_evaluator: ResearchDecisionEvaluatorProtocol,
) -> bool:
    retained_identity = outcome.decision_evaluator_identity
    start_identity = _safe_resolve_decision_identity(decision_evaluator)
    if start_identity != retained_identity:
        raise ResearchEvaluatorIdentityMismatchError(
            "decision evaluator does not match retained producer identity"
        )
    try:
        decision_reproduces = verify_trace_reproducibility(
            outcome.trace,
            decision_evaluator,
        )
    except ResearchLineageError:
        raise
    except Exception as exc:
        raise ResearchLineageValidationError(
            "trace reproducibility verification raised unexpected error"
        ) from exc
    final_identity = _safe_resolve_decision_identity(decision_evaluator)
    if final_identity != start_identity:
        raise ResearchEvaluatorIdentityMismatchError(
            "decision evaluator identity drifted during verification"
        )
    return decision_reproduces


def _verify_specialist_side(
    outcome: ResearchProducerLineageOutcome,
    specialist_evaluator: ResearchSpecialistEvaluatorProtocol,
) -> bool:
    retained_identity = outcome.specialist_evaluator_identity
    start_identity = _safe_resolve_specialist_identity(specialist_evaluator)
    if start_identity != retained_identity:
        raise ResearchSpecialistEvaluatorIdentityMismatchError(
            "specialist evaluator does not match retained producer identity"
        )

    specialist_reproduces = True
    for record_index, record in enumerate(outcome.lineage_records):
        _revalidate_retained_lineage_record(record)
        source_decision = record.analysis_input_evidence.source_decision
        reproduced_specification = _safe_evaluate_specialist(
            specialist_evaluator,
            source_decision,
            retained_identity,
        )
        if (
            reproduced_specification
            != record.analysis_input_evidence.analysis_specification
        ):
            specialist_reproduces = False

        reproduced_evidence = ResearchAnalysisInputEvidence(
            evaluator_identity=retained_identity,
            source_decision=source_decision,
            analysis_specification=reproduced_specification,
        )
        if reproduced_evidence != record.analysis_input_evidence:
            specialist_reproduces = False

        try:
            reproduced_command = construct_research_trader_command(
                outcome.trace,
                record.decision_transition_index,
                record.decision_index_within_transition,
                reproduced_evidence,
            )
            reproduced_analysis = reproduced_command.to_analysis()
        except ResearchLineageError:
            raise
        except Exception as exc:
            raise ResearchLineageValidationError(
                f"record {record_index} artifact reconstruction raised unexpected error"
            ) from exc

        if reproduced_command != record.trader_command:
            specialist_reproduces = False
        if reproduced_analysis != record.analysis:
            specialist_reproduces = False

    final_identity = _safe_resolve_specialist_identity(specialist_evaluator)
    if final_identity != start_identity:
        raise ResearchSpecialistEvaluatorIdentityMismatchError(
            "specialist evaluator identity drifted during verification"
        )
    return specialist_reproduces


class ResearchProducerLineageVerifier:
    """Independently reproduce both producer computation boundaries."""

    @staticmethod
    def verify(
        outcome: ResearchProducerLineageOutcome,
        decision_evaluator: ResearchDecisionEvaluatorProtocol,
        specialist_evaluator: ResearchSpecialistEvaluatorProtocol,
    ) -> bool:
        if not isinstance(outcome, ResearchProducerLineageOutcome):
            raise ResearchLineageValidationError(
                "outcome must be ResearchProducerLineageOutcome"
            )

        _validate_outcome_field_types(outcome)
        _validate_outcome_graph(outcome)

        computed_admission = _compute_admission_fingerprint(
            outcome.admission_evidence.integrity_qualified_run.fingerprint,
            outcome.admission_evidence.strategy_binding.binding_fingerprint,
            outcome.admission_evidence.execution_session.session_fingerprint,
        )
        if computed_admission != outcome.admission_evidence.admission_fingerprint:
            raise ResearchLineageFingerprintError(
                "producer admission fingerprint mismatch"
            )

        computed_outcome = _compute_outcome_fingerprint(
            outcome.admission_evidence.admission_fingerprint,
            outcome.decision_evaluator_identity,
            outcome.specialist_evaluator_identity,
            outcome.trace.trace_fingerprint,
            outcome.lineage_records,
        )
        if computed_outcome != outcome.outcome_fingerprint:
            raise ResearchLineageFingerprintError(
                "producer outcome fingerprint mismatch"
            )

        decision_reproduces = _verify_decision_side(outcome, decision_evaluator)
        specialist_reproduces = _verify_specialist_side(
            outcome,
            specialist_evaluator,
        )
        return decision_reproduces and specialist_reproduces
