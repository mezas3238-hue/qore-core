from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.infrastructure.cibo_operational_supervision_evidence import (
    CiboOperationalSupervisionOutcome,
    CiboOperationalSupervisionReason,
    CiboOperationalSupervisionRecord,
)
from qore.infrastructure.execution_boundary import (
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionObservation,
    ExecutionReconciliationSnapshot,
    ExecutionReconciliationStatus,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    QuoteSnapshot,
)
from qore.infrastructure.market_test_observability import MarketTestObservationState
from qore.infrastructure.mission03_observability_composition import (
    Mission03ObservabilityCompositionValidationError,
    Mission03ObservabilityCycle,
    build_mission03_observability_preparation,
)
from qore.infrastructure.operational_safety_certification_preparation import (
    OperationalSafetyCertificationPreparationEvidence,
    OperationalSafetyEvidenceRef,
    OperationalSafetyPreparationCheck,
    OperationalSafetyPreparationCheckStatus,
    OperationalSafetyPreparationId,
    OperationalSafetyPreparationRecord,
    build_operational_safety_certification_preparation_evidence,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.real_market_decision_runtime import (
    RealMarketDecisionOutcome,
    RealMarketDecisionStatus,
)
from qore.kernel.result import Success

_NOW = datetime(2026, 8, 9, 0, 30, tzinfo=UTC)
_SNAPSHOT_ID = MarketDataSnapshotId(
    UUID("35000000-0000-0000-0000-000000000001")
)
_CORRELATION = CorrelationId(UUID("35000000-0000-0000-0000-000000000002"))
_INTENT_ID = OrderIntentId(UUID("35000000-0000-0000-0000-000000000003"))
_IDEMPOTENCY = ExecutionIdempotencyKey(
    UUID("35000000-0000-0000-0000-000000000004")
)
_RECEIPT_ID = ExecutionReceiptId(
    UUID("35000000-0000-0000-0000-000000000005")
)
_REQUEST_ID = ExecutionRequestId(
    UUID("35000000-0000-0000-0000-000000000006")
)


def _quote() -> QuoteSnapshot:
    return QuoteSnapshot(
        snapshot_id=_SNAPSHOT_ID,
        instrument=Instrument("EUR_USD"),
        source=ExternalSourceDescriptor(
            adapter_id=AdapterId(UUID("35000000-0000-0000-0000-000000000007")),
            source_id=SourceId(UUID("35000000-0000-0000-0000-000000000008")),
            port_name=PortName("market-data.oanda-practice"),
        ),
        observed_at=_NOW,
        bid=1.1,
        ask=1.1002,
    )


def _safety(
    *,
    failed: OperationalSafetyPreparationCheck | None = None,
) -> OperationalSafetyCertificationPreparationEvidence:
    records = tuple(
        OperationalSafetyPreparationRecord(
            check=check,
            status=(
                OperationalSafetyPreparationCheckStatus.FAIL
                if check is failed
                else OperationalSafetyPreparationCheckStatus.PASS
            ),
            observed_at=_NOW + timedelta(seconds=2),
            code=f"mission03.{check.value}.verified",
            evidence_refs=(
                OperationalSafetyEvidenceRef(f"dryrun:safety/{check.value}"),
            ),
        )
        for check in OperationalSafetyPreparationCheck
    )
    result = build_operational_safety_certification_preparation_evidence(
        OperationalSafetyPreparationId(
            UUID("35000000-0000-0000-0000-000000000009")
        ),
        records,
        provider_key="oanda-v20",
        environment="demo",
        account_fingerprint="sha256:0123456789abcdef01234567",
        evaluated_at=_NOW + timedelta(seconds=3),
    )
    assert isinstance(result, Success)
    return result.value


def _supervision(
    outcome: CiboOperationalSupervisionOutcome,
) -> CiboOperationalSupervisionRecord:
    reasons = {
        CiboOperationalSupervisionOutcome.BLOCKED: (
            CiboOperationalSupervisionReason.SUPERVISION_BLOCKED
        ),
        CiboOperationalSupervisionOutcome.NO_ACTION: (
            CiboOperationalSupervisionReason.DECISION_NO_ACTION
        ),
        CiboOperationalSupervisionOutcome.DELEGATED: (
            CiboOperationalSupervisionReason.DECISION_DELEGATED
        ),
        CiboOperationalSupervisionOutcome.FAILED: (
            CiboOperationalSupervisionReason.DELEGATE_FAILED
        ),
    }
    return CiboOperationalSupervisionRecord(
        attempt_ref="sha256:111111111111111111111111",
        supervisor_id="ceo.primary",
        provider_key="oanda-v20",
        environment="demo",
        account_fingerprint="sha256:0123456789abcdef01234567",
        market_snapshot_id=_SNAPSHOT_ID,
        instrument="EUR_USD",
        correlation_id=str(_CORRELATION.value),
        decided_at=_NOW + timedelta(seconds=1),
        supervision_expires_at=_NOW + timedelta(minutes=5),
        outcome=outcome,
        reason=reasons[outcome],
        intent_id=(
            _INTENT_ID
            if outcome is CiboOperationalSupervisionOutcome.DELEGATED
            else None
        ),
    )


def _intent() -> OrderIntent:
    return OrderIntent(
        intent_id=_INTENT_ID,
        idempotency_key=_IDEMPOTENCY,
        instrument=ExecutionInstrument("EUR_USD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("10")),
        created_at=_NOW + timedelta(seconds=1),
        metadata=ExternalRequestMetadata(correlation_id=_CORRELATION),
    )


def _receipt() -> ExecutionReceipt:
    return ExecutionReceipt(
        receipt_id=_RECEIPT_ID,
        request_id=_REQUEST_ID,
        idempotency_key=_IDEMPOTENCY,
        status=ExecutionStatus.ACCEPTED,
        recorded_at=_NOW + timedelta(seconds=2),
    )


def _matched_reconciliation() -> ExecutionReconciliationSnapshot:
    receipt = _receipt()
    observation = ExecutionObservation(
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        idempotency_key=receipt.idempotency_key,
        status=receipt.status,
        observed_at=_NOW + timedelta(seconds=3),
    )
    return ExecutionReconciliationSnapshot(
        status=ExecutionReconciliationStatus.MATCHED,
        reconciled_at=_NOW + timedelta(seconds=4),
        expected=receipt,
        observed=observation,
    )


def test_no_action_cycle_is_complete_healthy_and_explicitly_non_operational() -> None:
    quote = _quote()
    decision = RealMarketDecisionOutcome(
        status=RealMarketDecisionStatus.NO_ACTION,
        quote=quote,
        decided_at=_NOW + timedelta(seconds=1),
    )
    cycle = Mission03ObservabilityCycle(
        quote=quote,
        supervision=_supervision(CiboOperationalSupervisionOutcome.NO_ACTION),
        safety=_safety(),
        decision=decision,
    )

    result = build_mission03_observability_preparation(
        cycle,
        evaluated_at=_NOW + timedelta(seconds=5),
    )

    assert isinstance(result, Success)
    prepared = result.value
    assert prepared.operationally_observed is False
    assert prepared.evidence.state is MarketTestObservationState.HEALTHY
    messages = {item.category.value: item.message for item in prepared.evidence.observations}
    assert messages["decision"] == "decision.no-action"
    assert messages["execution"] == "execution.not-required-no-action"
    assert messages["reconciliation"] == "reconciliation.not-required-no-action"


def test_blocked_supervision_produces_complete_blocked_bundle_without_decision() -> None:
    cycle = Mission03ObservabilityCycle(
        quote=_quote(),
        supervision=_supervision(CiboOperationalSupervisionOutcome.BLOCKED),
        safety=_safety(),
    )

    result = build_mission03_observability_preparation(
        cycle,
        evaluated_at=_NOW + timedelta(seconds=5),
    )

    assert isinstance(result, Success)
    assert result.value.evidence.state is MarketTestObservationState.BLOCKED
    states = {
        item.category.value: item.state for item in result.value.evidence.observations
    }
    assert states["decision"] is MarketTestObservationState.BLOCKED
    assert states["supervision"] is MarketTestObservationState.BLOCKED
    assert states["execution"] is MarketTestObservationState.BLOCKED
    assert states["reconciliation"] is MarketTestObservationState.BLOCKED


def test_submitted_matched_cycle_is_healthy_and_receipt_bound() -> None:
    quote = _quote()
    decision = RealMarketDecisionOutcome(
        status=RealMarketDecisionStatus.SUBMITTED,
        quote=quote,
        decided_at=_NOW + timedelta(seconds=1),
        intent=_intent(),
        receipt=_receipt(),
    )
    cycle = Mission03ObservabilityCycle(
        quote=quote,
        supervision=_supervision(CiboOperationalSupervisionOutcome.DELEGATED),
        safety=_safety(),
        decision=decision,
        reconciliation=_matched_reconciliation(),
    )

    result = build_mission03_observability_preparation(
        cycle,
        evaluated_at=_NOW + timedelta(seconds=5),
    )

    assert isinstance(result, Success)
    assert result.value.evidence.state is MarketTestObservationState.HEALTHY
    observations = {
        item.category.value: item for item in result.value.evidence.observations
    }
    assert observations["execution"].message == "execution.accepted"
    assert observations["execution"].reference == str(_RECEIPT_ID.value)
    assert observations["reconciliation"].message == "reconciliation.matched"


def test_diverged_reconciliation_blocks_aggregate_state() -> None:
    quote = _quote()
    decision = RealMarketDecisionOutcome(
        status=RealMarketDecisionStatus.SUBMITTED,
        quote=quote,
        decided_at=_NOW + timedelta(seconds=1),
        intent=_intent(),
        receipt=_receipt(),
    )
    observed = ExecutionObservation(
        receipt_id=_RECEIPT_ID,
        request_id=_REQUEST_ID,
        idempotency_key=_IDEMPOTENCY,
        status=ExecutionStatus.CANCELLED,
        observed_at=_NOW + timedelta(seconds=3),
    )
    reconciliation = ExecutionReconciliationSnapshot(
        status=ExecutionReconciliationStatus.DIVERGED,
        reconciled_at=_NOW + timedelta(seconds=4),
        expected=_receipt(),
        observed=observed,
        issues=("status_mismatch",),
    )
    cycle = Mission03ObservabilityCycle(
        quote=quote,
        supervision=_supervision(CiboOperationalSupervisionOutcome.DELEGATED),
        safety=_safety(),
        decision=decision,
        reconciliation=reconciliation,
    )

    result = build_mission03_observability_preparation(
        cycle,
        evaluated_at=_NOW + timedelta(seconds=5),
    )

    assert isinstance(result, Success)
    assert result.value.evidence.state is MarketTestObservationState.BLOCKED


def test_blocked_safety_blocks_aggregate_even_when_no_action_is_valid() -> None:
    quote = _quote()
    decision = RealMarketDecisionOutcome(
        status=RealMarketDecisionStatus.NO_ACTION,
        quote=quote,
        decided_at=_NOW + timedelta(seconds=1),
    )
    cycle = Mission03ObservabilityCycle(
        quote=quote,
        supervision=_supervision(CiboOperationalSupervisionOutcome.NO_ACTION),
        safety=_safety(failed=OperationalSafetyPreparationCheck.KILL_SWITCH),
        decision=decision,
    )

    result = build_mission03_observability_preparation(
        cycle,
        evaluated_at=_NOW + timedelta(seconds=5),
    )

    assert isinstance(result, Success)
    assert result.value.evidence.state is MarketTestObservationState.BLOCKED


def test_missing_decision_requires_blocked_or_failed_supervision() -> None:
    with pytest.raises(Mission03ObservabilityCompositionValidationError):
        Mission03ObservabilityCycle(
            quote=_quote(),
            supervision=_supervision(CiboOperationalSupervisionOutcome.NO_ACTION),
            safety=_safety(),
        )


def test_submitted_cycle_requires_exact_reconciliation_receipt() -> None:
    quote = _quote()
    decision = RealMarketDecisionOutcome(
        status=RealMarketDecisionStatus.SUBMITTED,
        quote=quote,
        decided_at=_NOW + timedelta(seconds=1),
        intent=_intent(),
        receipt=_receipt(),
    )
    different_receipt = ExecutionReceipt(
        receipt_id=ExecutionReceiptId(
            UUID("35000000-0000-0000-0000-000000000010")
        ),
        request_id=_REQUEST_ID,
        idempotency_key=_IDEMPOTENCY,
        status=ExecutionStatus.ACCEPTED,
        recorded_at=_NOW + timedelta(seconds=2),
    )
    reconciliation = ExecutionReconciliationSnapshot(
        status=ExecutionReconciliationStatus.MATCHED,
        reconciled_at=_NOW + timedelta(seconds=4),
        expected=different_receipt,
        observed=ExecutionObservation(
            receipt_id=different_receipt.receipt_id,
            request_id=different_receipt.request_id,
            idempotency_key=different_receipt.idempotency_key,
            status=different_receipt.status,
            observed_at=_NOW + timedelta(seconds=3),
        ),
    )

    with pytest.raises(Mission03ObservabilityCompositionValidationError):
        Mission03ObservabilityCycle(
            quote=quote,
            supervision=_supervision(CiboOperationalSupervisionOutcome.DELEGATED),
            safety=_safety(),
            decision=decision,
            reconciliation=reconciliation,
        )
