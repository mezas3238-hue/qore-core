from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.domain.events import (
    CausationId,
    CorrelationId,
    DomainEventCategory,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.functional.decisions import DecisionId
from qore.modules.trader.contracts import (
    TraderAnalysisProducedEvent,
    TraderValidationError,
)
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistMetadata,
    SpecialistReason,
    SpecialistReasonCode,
)

_TIMESTAMP = datetime(2026, 8, 7, 22, 30, tzinfo=UTC)
_SOURCE_ID = DecisionId(UUID("92000000-0000-0000-0000-000000000001"))
_CORRELATION = CorrelationId(UUID("92000000-0000-0000-0000-000000000002"))
_CAUSATION = CausationId(_SOURCE_ID.value)
_EVENT_ID = DomainEventId(UUID("92000000-0000-0000-0000-000000000003"))


def _reason() -> SpecialistReason:
    return SpecialistReason(
        code=SpecialistReasonCode("virtual-trader.explicit"),
        summary="Explicit internal evidence",
    )


def _analysis(
    *,
    analysis_id: SpecialistAnalysisId | None = None,
    kind: SpecialistKind | None = None,
    status: SpecialistAnalysisStatus = SpecialistAnalysisStatus.COMPLETED,
) -> SpecialistAnalysis:
    completed = status is SpecialistAnalysisStatus.COMPLETED
    return SpecialistAnalysis(
        analysis_id=analysis_id
        or SpecialistAnalysisId(UUID("92000000-0000-0000-0000-000000000004")),
        timestamp=_TIMESTAMP,
        kind=kind or SpecialistKind("virtual-trader.structure"),
        status=status,
        metadata=SpecialistMetadata(
            correlation_id=_CORRELATION,
            causation_id=_CAUSATION,
        ),
        confidence=SpecialistConfidence(0.7) if completed else None,
        reasons=(_reason(),) if completed else (),
    )


def _event_metadata() -> DomainEventMetadata:
    return DomainEventMetadata(
        category=DomainEventCategory("virtual-trader"),
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def test_event_rejects_non_virtual_trader_analysis_kind() -> None:
    analysis = _analysis(kind=SpecialistKind("validation.review"))

    with pytest.raises(TraderValidationError, match="analysis kind"):
        TraderAnalysisProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=_event_metadata(),
            analysis=analysis,
            source_decision_id=_SOURCE_ID,
        )


def test_event_rejects_analysis_identity_reusing_source_uuid() -> None:
    analysis = _analysis(analysis_id=SpecialistAnalysisId(_SOURCE_ID.value))

    with pytest.raises(TraderValidationError, match="identity must differ"):
        TraderAnalysisProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=_event_metadata(),
            analysis=analysis,
            source_decision_id=_SOURCE_ID,
        )


def test_event_rejects_pending_analysis() -> None:
    analysis = _analysis(status=SpecialistAnalysisStatus.PENDING)

    with pytest.raises(TraderValidationError, match="completed analysis"):
        TraderAnalysisProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=_event_metadata(),
            analysis=analysis,
            source_decision_id=_SOURCE_ID,
        )
