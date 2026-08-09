from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from uuid import UUID

import pytest

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_cross_provider_certification as cross
import qore.infrastructure.futures_shadow_core as shadow
import qore.kernel.result as result
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
from qore.infrastructure.hosting_latency_safety import HostingLatencyDuration
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)

_NOW = datetime(2026, 8, 10, 14, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"66000000-0000-0000-0000-{suffix:012d}")


def _source(provider: str, *, suffix: int) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(suffix)),
        source_id=SourceId(_uuid(suffix + 1)),
        port_name=PortName(f"market-data.{provider}-shadow"),
    )


def _provider_evidence(
    provider: futures.FuturesProviderName,
    *,
    suffix: int,
    delayed: bool = False,
) -> cross.FuturesProviderCertificationEvidence:
    ohlc = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(suffix + 10)),
        instrument=Instrument("ESZ6"),
        source=_source(provider.value, suffix=suffix),
        timeframe=Timeframe(60),
        opened_at=_NOW - timedelta(minutes=2),
        closed_at=_NOW - timedelta(minutes=1),
        open=5000.0,
        high=5005.0,
        low=4995.0,
        close=5001.0,
    )
    return cross.FuturesProviderCertificationEvidence(
        provider=provider,
        ohlc=ohlc,
        market_data_status=(
            cross.FuturesMarketDataCertificationStatus.CERTIFIED_DELAYED
            if delayed
            else cross.FuturesMarketDataCertificationStatus.CERTIFIED_REALTIME
        ),
        execution_status=(
            cross.FuturesExecutionCertificationStatus.CERTIFIED_PAPER_SIMULATION
        ),
        execution_reconciliation=futures.FuturesExecutionReconciliationStatus.MATCHED,
        ingress_latency=HostingLatencyDuration.from_milliseconds(
            900_000 if delayed else 20
        ),
        observed_at=_NOW - timedelta(seconds=30),
        evidence_refs=(
            cross.FuturesProviderCertificationEvidenceReference(_uuid(suffix + 20)),
        ),
    )


def _cross_assessment(
    state: cross.FuturesCrossProviderState = cross.FuturesCrossProviderState.DELAY_AWARE_CERTIFIED,
) -> cross.FuturesCrossProviderAssessment:
    evidence = (
        _provider_evidence(cross.TRADESTATION_PROVIDER, suffix=100),
        _provider_evidence(cross.IBKR_PROVIDER, suffix=200),
        _provider_evidence(cross.TASTYTRADE_PROVIDER, suffix=300, delayed=True),
    )
    return cross.FuturesCrossProviderAssessment(
        assessment_id=cross.FuturesCrossProviderAssessmentId(_uuid(400)),
        state=state,
        reason=(
            cross.FuturesCrossProviderReason.ALIGNED_WITH_DELAYED_PROVIDER
            if state is cross.FuturesCrossProviderState.DELAY_AWARE_CERTIFIED
            else cross.FuturesCrossProviderReason.OHLC_DISAGREEMENT
        ),
        provider_evidence=evidence,
        spread_evidence=None,
        evaluated_at=_NOW - timedelta(seconds=20),
        evidence_ref=cross.FuturesProviderCertificationEvidenceReference(_uuid(401)),
    )


def _input_certification() -> shadow.FuturesShadowInputCertification:
    return shadow.FuturesShadowInputCertification(
        cross_provider_assessment=_cross_assessment(),
        accepted_at=_NOW - timedelta(seconds=10),
        evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(500)),
    )


def _decision(
    *,
    suffix: int,
    outcome: DecisionOutcome = DecisionOutcome.APPROVED,
    status: DecisionStatus = DecisionStatus.RESOLVED,
) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid(suffix)),
        timestamp=_NOW,
        decision_type=DecisionType("core.trade"),
        status=status,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(_uuid(suffix + 1)),
            attributes=MappingProxyType({"instrument": "ESZ6"}),
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("shadow.test"),
                summary="deterministic Shadow Core decision evidence",
            ),
        )
        if status is DecisionStatus.RESOLVED
        else (),
        outcome=outcome if status is DecisionStatus.RESOLVED else None,
    )


def test_shadow_input_accepts_delay_aware_cross_provider_evidence() -> None:
    certification = _input_certification()

    assert certification.cross_provider_assessment.state is (
        cross.FuturesCrossProviderState.DELAY_AWARE_CERTIFIED
    )


def test_shadow_input_rejects_disagreement_or_blocked_evidence() -> None:
    with pytest.raises(shadow.FuturesShadowCoreValidationError):
        shadow.FuturesShadowInputCertification(
            cross_provider_assessment=_cross_assessment(
                cross.FuturesCrossProviderState.DISAGREEMENT
            ),
            accepted_at=_NOW,
            evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(510)),
        )


def test_approved_core_decision_is_recorded_but_never_emits_trading_action() -> None:
    recorded = shadow.record_futures_shadow_decision(
        _decision(suffix=520, outcome=DecisionOutcome.APPROVED),
        _input_certification(),
        record_id=shadow.FuturesShadowDecisionRecordId(_uuid(521)),
        processed_at=_NOW + timedelta(milliseconds=1),
        evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(522)),
    )

    assert isinstance(recorded, result.Success)
    assert recorded.value.core_outcome is DecisionOutcome.APPROVED
    assert recorded.value.sink is shadow.FuturesShadowSink.NULL_SHADOW_SINK
    assert recorded.value.trading_action_emitted is False


def test_rejected_core_decision_is_preserved_at_same_null_sink() -> None:
    recorded = shadow.record_futures_shadow_decision(
        _decision(suffix=530, outcome=DecisionOutcome.REJECTED),
        _input_certification(),
        record_id=shadow.FuturesShadowDecisionRecordId(_uuid(531)),
        processed_at=_NOW + timedelta(milliseconds=1),
        evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(532)),
    )

    assert isinstance(recorded, result.Success)
    assert recorded.value.core_outcome is DecisionOutcome.REJECTED
    assert recorded.value.sink is shadow.FuturesShadowSink.NULL_SHADOW_SINK


def test_pending_decision_cannot_be_shadow_certified_as_completed_core_work() -> None:
    recorded = shadow.record_futures_shadow_decision(
        _decision(suffix=540, status=DecisionStatus.PENDING),
        _input_certification(),
        record_id=shadow.FuturesShadowDecisionRecordId(_uuid(541)),
        processed_at=_NOW + timedelta(milliseconds=1),
        evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(542)),
    )

    assert isinstance(recorded, result.Failure)
    assert isinstance(recorded.error, shadow.FuturesShadowCoreValidationError)


def test_offline_session_report_cannot_claim_operational_evidence() -> None:
    decision = shadow.record_futures_shadow_decision(
        _decision(suffix=550),
        _input_certification(),
        record_id=shadow.FuturesShadowDecisionRecordId(_uuid(551)),
        processed_at=_NOW + timedelta(milliseconds=1),
        evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(552)),
    )
    assert isinstance(decision, result.Success)

    report = shadow.FuturesShadowSessionReport(
        session_id=shadow.FuturesShadowSessionId(_uuid(553)),
        mode=shadow.FuturesShadowSessionMode.DETERMINISTIC_OFFLINE,
        input_certification=_input_certification(),
        decisions=(decision.value,),
        started_at=_NOW - timedelta(seconds=1),
        ended_at=_NOW + timedelta(seconds=1),
        reported_at=_NOW + timedelta(seconds=2),
        operational_evidence_ref=None,
        evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(554)),
    )

    assert report.certification_status is (
        shadow.FuturesShadowCertificationStatus.CERTIFIED_OFFLINE
    )
    assert report.trading_actions_emitted == 0


def test_operational_mode_requires_explicit_operational_evidence_reference() -> None:
    decision = shadow.record_futures_shadow_decision(
        _decision(suffix=560),
        _input_certification(),
        record_id=shadow.FuturesShadowDecisionRecordId(_uuid(561)),
        processed_at=_NOW + timedelta(milliseconds=1),
        evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(562)),
    )
    assert isinstance(decision, result.Success)

    with pytest.raises(shadow.FuturesShadowCoreValidationError):
        shadow.FuturesShadowSessionReport(
            session_id=shadow.FuturesShadowSessionId(_uuid(563)),
            mode=shadow.FuturesShadowSessionMode.READ_ONLY_OPERATIONAL,
            input_certification=_input_certification(),
            decisions=(decision.value,),
            started_at=_NOW - timedelta(seconds=1),
            ended_at=_NOW + timedelta(seconds=1),
            reported_at=_NOW + timedelta(seconds=2),
            operational_evidence_ref=None,
            evidence_ref=shadow.FuturesShadowEvidenceReference(_uuid(564)),
        )


def test_shadow_boundary_exposes_no_order_submission_retry_or_provider_client() -> None:
    prohibited = {
        "submit_order",
        "retry_order",
        "redispatch",
        "provider_client",
        "broker_client",
        "execution_request",
        "send_order",
    }
    for surface in (
        shadow.FuturesShadowInputCertification,
        shadow.FuturesShadowDecisionRecord,
        shadow.FuturesShadowSessionReport,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
