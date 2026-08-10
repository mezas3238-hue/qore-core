from __future__ import annotations

from dataclasses import dataclass, field

from qore.functional.decisions import FunctionalDecision
from qore.infrastructure.research_evaluator_identity import (
    ResearchSpecialistEvaluatorIdentity,
)
from qore.infrastructure.research_lineage_canonical import (
    _cjson,
    _sha256,
    canonical_functional_decision,
    canonical_specialist_reason,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchLineageValidationError,
)
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchAnalysisInputEvidenceFingerprint,
)
from qore.specialist.analysis import (
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
)


@dataclass(frozen=True, slots=True)
class ResearchAnalysisSpecification:
    """Bound specialist output specification; not producer provenance."""

    kind: SpecialistKind
    confidence: SpecialistConfidence
    reasons: tuple[SpecialistReason, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SpecialistKind):
            raise ResearchLineageValidationError(
                "kind must be SpecialistKind"
            )
        if not self.kind.value.startswith("virtual-trader."):
            raise ResearchLineageValidationError(
                "kind must use virtual-trader.* namespace"
            )
        if not isinstance(self.confidence, SpecialistConfidence):
            raise ResearchLineageValidationError(
                "confidence must be SpecialistConfidence"
            )
        if not isinstance(self.reasons, tuple):
            raise ResearchLineageValidationError(
                "reasons must be tuple"
            )
        if not self.reasons:
            raise ResearchLineageValidationError(
                "reasons must be non-empty"
            )
        if any(
            not isinstance(reason, SpecialistReason)
            for reason in self.reasons
        ):
            raise ResearchLineageValidationError(
                "every reason must be SpecialistReason"
            )


@dataclass(frozen=True, slots=True)
class ResearchAnalysisInputEvidence:
    """Exact specialist-boundary evidence under P2; not producer proof."""

    evaluator_identity: ResearchSpecialistEvaluatorIdentity
    source_decision: FunctionalDecision
    analysis_specification: ResearchAnalysisSpecification
    evidence_fingerprint: ResearchAnalysisInputEvidenceFingerprint = field(
        init=False
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.evaluator_identity,
            ResearchSpecialistEvaluatorIdentity,
        ):
            raise ResearchLineageValidationError(
                "evaluator_identity must be ResearchSpecialistEvaluatorIdentity"
            )
        if not isinstance(self.source_decision, FunctionalDecision):
            raise ResearchLineageValidationError(
                "source_decision must be FunctionalDecision"
            )
        if not isinstance(
            self.analysis_specification,
            ResearchAnalysisSpecification,
        ):
            raise ResearchLineageValidationError(
                "analysis_specification must be ResearchAnalysisSpecification"
            )
        object.__setattr__(
            self,
            "evidence_fingerprint",
            _compute_analysis_input_evidence_fingerprint(self),
        )


def _compute_analysis_input_evidence_fingerprint(
    evidence: ResearchAnalysisInputEvidence,
) -> ResearchAnalysisInputEvidenceFingerprint:
    if not isinstance(evidence, ResearchAnalysisInputEvidence):
        raise ResearchLineageValidationError(
            "evidence must be ResearchAnalysisInputEvidence"
        )
    specification = evidence.analysis_specification
    return ResearchAnalysisInputEvidenceFingerprint(
        value=_sha256(
            _cjson(
                {
                    "schema": "qore.research-analysis-input-evidence.v1",
                    "evaluator_family": (
                        evidence.evaluator_identity.family.value
                    ),
                    "evaluator_schema_version": (
                        evidence.evaluator_identity.schema_version.value
                    ),
                    "software_revision": (
                        evidence.evaluator_identity.software_revision.value
                    ),
                    "source_decision": canonical_functional_decision(
                        evidence.source_decision
                    ),
                    "kind": specification.kind.value,
                    "confidence": specification.confidence.value.hex(),
                    "reasons": [
                        canonical_specialist_reason(reason)
                        for reason in specification.reasons
                    ],
                }
            )
        )
    )
