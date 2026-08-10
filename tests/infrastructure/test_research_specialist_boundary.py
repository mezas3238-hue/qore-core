from __future__ import annotations

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
    ResearchSpecialistEvaluatorFamily,
    ResearchSpecialistEvaluatorIdentity,
    ResearchSpecialistEvaluatorSchemaVersion,
)
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.research_specialist_boundary import (
    ResearchAnalysisInputEvidence,
    ResearchAnalysisSpecification,
)
from qore.specialist.analysis import (
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
    SpecialistReasonCode,
)


def _decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(UUID("56000000-0000-0000-0000-000000000001")),
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        decision_type=DecisionType("research.test"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(
                UUID("56000000-0000-0000-0000-000000000002")
            ),
            attributes=MappingProxyType({}),
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.test"),
                summary="test decision",
                attributes=MappingProxyType({}),
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _reason(code: str) -> SpecialistReason:
    return SpecialistReason(
        code=SpecialistReasonCode(code),
        summary=code,
        attributes=MappingProxyType({}),
    )


def _identity(family: str = "test.specialist") -> ResearchSpecialistEvaluatorIdentity:
    return ResearchSpecialistEvaluatorIdentity(
        family=ResearchSpecialistEvaluatorFamily(family),
        schema_version=ResearchSpecialistEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("revision-1"),
    )


def test_analysis_specification_enforces_virtual_trader_namespace() -> None:
    specification = ResearchAnalysisSpecification(
        kind=SpecialistKind("virtual-trader.test"),
        confidence=SpecialistConfidence(0.75),
        reasons=(_reason("research.a"),),
    )
    assert specification.kind.value == "virtual-trader.test"
    with pytest.raises(ResearchLineageValidationError):
        ResearchAnalysisSpecification(
            kind=SpecialistKind("production.test"),
            confidence=SpecialistConfidence(0.75),
            reasons=(_reason("research.a"),),
        )


def test_analysis_specification_requires_nonempty_typed_reasons() -> None:
    with pytest.raises(ResearchLineageValidationError):
        ResearchAnalysisSpecification(
            kind=SpecialistKind("virtual-trader.test"),
            confidence=SpecialistConfidence(0.75),
            reasons=(),
        )


def test_reason_order_and_specialist_identity_are_fingerprint_material() -> None:
    decision = _decision()
    reasons_ab = (_reason("research.a"), _reason("research.b"))
    reasons_ba = tuple(reversed(reasons_ab))
    first = ResearchAnalysisInputEvidence(
        evaluator_identity=_identity(),
        source_decision=decision,
        analysis_specification=ResearchAnalysisSpecification(
            kind=SpecialistKind("virtual-trader.test"),
            confidence=SpecialistConfidence(0.75),
            reasons=reasons_ab,
        ),
    )
    reordered = ResearchAnalysisInputEvidence(
        evaluator_identity=_identity(),
        source_decision=decision,
        analysis_specification=ResearchAnalysisSpecification(
            kind=SpecialistKind("virtual-trader.test"),
            confidence=SpecialistConfidence(0.75),
            reasons=reasons_ba,
        ),
    )
    other_identity = ResearchAnalysisInputEvidence(
        evaluator_identity=_identity("test.other"),
        source_decision=decision,
        analysis_specification=first.analysis_specification,
    )
    assert first.evidence_fingerprint != reordered.evidence_fingerprint
    assert first.evidence_fingerprint != other_identity.evidence_fingerprint
