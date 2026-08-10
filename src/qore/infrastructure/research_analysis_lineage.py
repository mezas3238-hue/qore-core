from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from types import MappingProxyType

from qore.domain.commands import CommandId, CommandMetadata, CommandName
from qore.domain.events import CausationId
from qore.functional.decisions import DecisionStatus, FunctionalDecision
from qore.infrastructure.research_execution_trace import ResearchExecutionTrace
from qore.infrastructure.research_lineage_canonical import (
    _cjson,
    _sha256,
    _utc_iso,
    canonical_command_metadata,
    canonical_functional_decision,
    canonical_specialist_analysis,
    canonical_specialist_reason,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageValidationError,
)
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchAnalysisLineageFingerprint,
    ResearchAnalysisInputEvidenceFingerprint,
    ResearchExecutionTraceFingerprint,
    ResearchTraderCommandFingerprint,
)
from qore.infrastructure.research_specialist_boundary import (
    ResearchAnalysisInputEvidence,
)
from qore.modules.trader.contracts import ProduceVirtualTraderAnalysisCommand
from qore.specialist.analysis import SpecialistAnalysis, SpecialistAnalysisId


_CMD_ID_DOMAIN = b"qore.research-trader-command-id.v1"
_ANALYSIS_ID_DOMAIN = b"qore.research-specialist-analysis-id.v1"


def _validate_index(index: int, length: int, name: str) -> None:
    if isinstance(index, bool) or type(index) is not int:
        raise ResearchLineageValidationError(f"{name} must be int; bool rejected")
    if not 0 <= index < length:
        raise ResearchLineageValidationError(
            f"{name}={index} outside valid range [0, {length})"
        )


def _derive_uuid(
    domain: bytes,
    trace_fingerprint: ResearchExecutionTraceFingerprint,
    transition_index: int,
    decision_index: int,
    evidence_fingerprint: ResearchAnalysisInputEvidenceFingerprint,
) -> uuid.UUID:
    if not isinstance(domain, bytes) or not domain:
        raise ResearchLineageValidationError("ID domain must be non-empty bytes")
    if not isinstance(
        trace_fingerprint,
        ResearchExecutionTraceFingerprint,
    ):
        raise ResearchLineageValidationError(
            "trace_fingerprint must be ResearchExecutionTraceFingerprint"
        )
    if not isinstance(
        evidence_fingerprint,
        ResearchAnalysisInputEvidenceFingerprint,
    ):
        raise ResearchLineageValidationError(
            "evidence_fingerprint must be ResearchAnalysisInputEvidenceFingerprint"
        )
    if (
        isinstance(transition_index, bool)
        or type(transition_index) is not int
        or transition_index < 0
    ):
        raise ResearchLineageValidationError(
            "transition_index must be non-negative int; bool rejected"
        )
    if (
        isinstance(decision_index, bool)
        or type(decision_index) is not int
        or decision_index < 0
    ):
        raise ResearchLineageValidationError(
            "decision_index must be non-negative int; bool rejected"
        )
    digest = hashlib.sha256(
        domain
        + b"|"
        + trace_fingerprint.value.encode("ascii")
        + b"|"
        + str(transition_index).encode("ascii")
        + b"|"
        + str(decision_index).encode("ascii")
        + b"|"
        + evidence_fingerprint.value.encode("ascii")
    ).digest()
    return uuid.UUID(bytes=digest[:16])


def derive_research_trader_command_id(
    trace_fingerprint: ResearchExecutionTraceFingerprint,
    transition_index: int,
    decision_index: int,
    evidence_fingerprint: ResearchAnalysisInputEvidenceFingerprint,
) -> CommandId:
    return CommandId(
        value=_derive_uuid(
            _CMD_ID_DOMAIN,
            trace_fingerprint,
            transition_index,
            decision_index,
            evidence_fingerprint,
        )
    )


def derive_research_specialist_analysis_id(
    trace_fingerprint: ResearchExecutionTraceFingerprint,
    transition_index: int,
    decision_index: int,
    evidence_fingerprint: ResearchAnalysisInputEvidenceFingerprint,
    selected_decision: FunctionalDecision,
) -> SpecialistAnalysisId:
    if not isinstance(selected_decision, FunctionalDecision):
        raise ResearchLineageValidationError(
            "selected_decision must be FunctionalDecision"
        )
    analysis_id = SpecialistAnalysisId(
        value=_derive_uuid(
            _ANALYSIS_ID_DOMAIN,
            trace_fingerprint,
            transition_index,
            decision_index,
            evidence_fingerprint,
        )
    )
    if analysis_id.value == selected_decision.decision_id.value:
        raise ResearchLineageValidationError(
            "derived SpecialistAnalysisId collides with source DecisionId"
        )
    return analysis_id


def construct_research_trader_command(
    trace: ResearchExecutionTrace,
    transition_index: int,
    decision_index: int,
    analysis_input_evidence: ResearchAnalysisInputEvidence,
) -> ProduceVirtualTraderAnalysisCommand:
    if not isinstance(trace, ResearchExecutionTrace):
        raise ResearchLineageValidationError(
            "trace must be ResearchExecutionTrace"
        )
    if not isinstance(
        analysis_input_evidence,
        ResearchAnalysisInputEvidence,
    ):
        raise ResearchLineageValidationError(
            "analysis_input_evidence must be ResearchAnalysisInputEvidence"
        )
    _validate_index(
        transition_index,
        len(trace.transitions),
        "transition_index",
    )
    transition = trace.transitions[transition_index]
    _validate_index(
        decision_index,
        len(transition.decisions),
        "decision_index",
    )
    selected = transition.decisions[decision_index]
    if selected.status is not DecisionStatus.RESOLVED:
        raise ResearchLineageValidationError(
            "only RESOLVED FunctionalDecision may enter analysis lineage"
        )
    if analysis_input_evidence.source_decision != selected:
        raise ResearchLineageValidationError(
            "specialist boundary evidence does not bind exact selected decision"
        )
    evidence_fingerprint = analysis_input_evidence.evidence_fingerprint
    specification = analysis_input_evidence.analysis_specification
    return ProduceVirtualTraderAnalysisCommand(
        command_id=derive_research_trader_command_id(
            trace.trace_fingerprint,
            transition_index,
            decision_index,
            evidence_fingerprint,
        ),
        timestamp=transition.simulated_now,
        name=CommandName("virtual-trader.produce-analysis"),
        metadata=CommandMetadata(
            correlation_id=selected.metadata.correlation_id,
            causation_id=CausationId(selected.decision_id.value),
            idempotency_key=None,
            attributes=MappingProxyType({}),
        ),
        analysis_id=derive_research_specialist_analysis_id(
            trace.trace_fingerprint,
            transition_index,
            decision_index,
            evidence_fingerprint,
            selected,
        ),
        source_decision=selected,
        kind=specification.kind,
        confidence=specification.confidence,
        reasons=specification.reasons,
    )


def verify_command_reproducibility(
    retained_command: ProduceVirtualTraderAnalysisCommand,
    trace: ResearchExecutionTrace,
    transition_index: int,
    decision_index: int,
    analysis_input_evidence: ResearchAnalysisInputEvidence,
) -> bool:
    if not isinstance(
        retained_command,
        ProduceVirtualTraderAnalysisCommand,
    ):
        raise ResearchLineageValidationError(
            "retained_command must be ProduceVirtualTraderAnalysisCommand"
        )
    reproduced = construct_research_trader_command(
        trace,
        transition_index,
        decision_index,
        analysis_input_evidence,
    )
    return retained_command == reproduced


def compute_research_trader_command_fingerprint(
    command: ProduceVirtualTraderAnalysisCommand,
) -> ResearchTraderCommandFingerprint:
    if not isinstance(
        command,
        ProduceVirtualTraderAnalysisCommand,
    ):
        raise ResearchLineageValidationError(
            "command must be ProduceVirtualTraderAnalysisCommand"
        )
    return ResearchTraderCommandFingerprint(
        value=_sha256(
            _cjson(
                {
                    "schema": "qore.research-trader-command.v1",
                    "command_id": str(command.command_id.value),
                    "timestamp": _utc_iso(
                        command.timestamp,
                        field_name="research trader command timestamp",
                    ),
                    "name": command.name.value,
                    "metadata": canonical_command_metadata(command.metadata),
                    "analysis_id": str(command.analysis_id.value),
                    "source_decision": canonical_functional_decision(
                        command.source_decision
                    ),
                    "kind": command.kind.value,
                    "confidence": command.confidence.value.hex(),
                    "reasons": [
                        canonical_specialist_reason(reason)
                        for reason in command.reasons
                    ],
                }
            )
        )
    )


@dataclass(frozen=True, slots=True)
class ResearchAnalysisLineageRecord:
    trace: ResearchExecutionTrace
    decision_transition_index: int
    decision_index_within_transition: int
    analysis_input_evidence: ResearchAnalysisInputEvidence
    trader_command: ProduceVirtualTraderAnalysisCommand
    analysis: SpecialistAnalysis
    lineage_fingerprint: ResearchAnalysisLineageFingerprint = field(
        init=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.trace, ResearchExecutionTrace):
            raise ResearchLineageValidationError(
                "trace must be ResearchExecutionTrace"
            )
        if not isinstance(
            self.analysis_input_evidence,
            ResearchAnalysisInputEvidence,
        ):
            raise ResearchLineageValidationError(
                "analysis_input_evidence must be ResearchAnalysisInputEvidence"
            )
        if not isinstance(
            self.trader_command,
            ProduceVirtualTraderAnalysisCommand,
        ):
            raise ResearchLineageValidationError(
                "trader_command must be ProduceVirtualTraderAnalysisCommand"
            )
        if not isinstance(self.analysis, SpecialistAnalysis):
            raise ResearchLineageValidationError(
                "analysis must be SpecialistAnalysis"
            )
        _validate_index(
            self.decision_transition_index,
            len(self.trace.transitions),
            "decision_transition_index",
        )
        transition = self.trace.transitions[
            self.decision_transition_index
        ]
        _validate_index(
            self.decision_index_within_transition,
            len(transition.decisions),
            "decision_index_within_transition",
        )
        selected = transition.decisions[
            self.decision_index_within_transition
        ]
        if selected.status is not DecisionStatus.RESOLVED:
            raise ResearchLineageValidationError(
                "only RESOLVED FunctionalDecision may enter lineage"
            )
        if self.analysis_input_evidence.source_decision != selected:
            raise ResearchLineageValidationError(
                "analysis input evidence source decision mismatch"
            )
        expected_command = construct_research_trader_command(
            self.trace,
            self.decision_transition_index,
            self.decision_index_within_transition,
            self.analysis_input_evidence,
        )
        if self.trader_command != expected_command:
            raise ResearchLineageValidationError(
                "trader_command differs from deterministic reconstruction"
            )
        specification = self.analysis_input_evidence.analysis_specification
        if self.trader_command.kind != specification.kind:
            raise ResearchLineageValidationError(
                "trader command kind differs from specialist specification"
            )
        if self.trader_command.confidence != specification.confidence:
            raise ResearchLineageValidationError(
                "trader command confidence differs from specialist specification"
            )
        if self.trader_command.reasons != specification.reasons:
            raise ResearchLineageValidationError(
                "trader command reasons differ from specialist specification"
            )
        if self.analysis != self.trader_command.to_analysis():
            raise ResearchLineageValidationError(
                "analysis differs from trader_command.to_analysis()"
            )
        object.__setattr__(
            self,
            "lineage_fingerprint",
            _compute_lineage_fingerprint(self),
        )


def _compute_lineage_fingerprint(
    record: ResearchAnalysisLineageRecord,
) -> ResearchAnalysisLineageFingerprint:
    if not isinstance(record, ResearchAnalysisLineageRecord):
        raise ResearchLineageValidationError(
            "lineage fingerprint requires ResearchAnalysisLineageRecord"
        )
    return ResearchAnalysisLineageFingerprint(
        value=_sha256(
            _cjson(
                {
                    "schema": "qore.research-analysis-lineage.v1",
                    "trace_fingerprint": record.trace.trace_fingerprint.value,
                    "decision_transition_index": (
                        record.decision_transition_index
                    ),
                    "decision_index_within_transition": (
                        record.decision_index_within_transition
                    ),
                    "analysis_input_evidence_fingerprint": (
                        record.analysis_input_evidence.evidence_fingerprint.value
                    ),
                    "trader_command_fingerprint": (
                        compute_research_trader_command_fingerprint(
                            record.trader_command
                        ).value
                    ),
                    "analysis": canonical_specialist_analysis(record.analysis),
                }
            )
        )
    )
