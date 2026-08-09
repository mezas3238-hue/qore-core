from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import get_type_hints
from uuid import UUID

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_ibkr_adapter as ibkr
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
from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_execution_lease import (
    HostingExecutionAuthorityAttestation,
    HostingExecutionLeaseId,
    HostingFencingGeneration,
    HostingLeaseEvidenceReference,
)
from qore.infrastructure.market_data import Instrument

_NOW = datetime(2026, 8, 9, 15, 0, tzinfo=UTC)
_ACCOUNT = TradingAccountId(UUID("68000000-0000-0000-0000-000000000001"))
_RUNTIME = ExecutionRuntimeReference(UUID("68000000-0000-0000-0000-000000000002"))
_CONTRACT_ID = ibkr.IBKRContractId(123456789)
_MAPPING = futures.FuturesContractMapping(
    provider=ibkr.IBKR_PROVIDER,
    provider_contract_id=futures.FuturesProviderContractId(str(_CONTRACT_ID.value)),
    instrument=Instrument("ESZ6"),
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"68000000-0000-0000-0000-{suffix:012d}")


def _decision(*, suffix: int) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid(suffix)),
        timestamp=_NOW,
        decision_type=DecisionType("futures.paper.entry"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=CorrelationId(_uuid(suffix + 1))),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("paper-e2e-authorized"),
                summary="Deterministic non-production Paper Futures E2E decision.",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _authority() -> HostingExecutionAuthorityAttestation:
    return HostingExecutionAuthorityAttestation(
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        lease_id=HostingExecutionLeaseId(_uuid(20)),
        generation=HostingFencingGeneration(11),
        evaluated_at=_NOW,
        evidence_ref=HostingLeaseEvidenceReference(_uuid(21)),
    )


def _request(*, suffix: int, quantity: int = 2) -> futures.FuturesExecutionRequest:
    decision = _decision(suffix=suffix + 100)
    return futures.FuturesExecutionRequest(
        request_id=futures.FuturesExecutionRequestId(_uuid(suffix)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        decision_id=decision.decision_id,
        authority=_authority(),
        environment=futures.FuturesExecutionEnvironment.PAPER,
        mapping=_MAPPING,
        side=futures.FuturesOrderSide.BUY,
        quantity=quantity,
        order_type=futures.FuturesOrderType.MARKET,
        time_in_force=futures.FuturesTimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        idempotency_key=futures.FuturesIdempotencyKey(_uuid(suffix + 200)),
        requested_at=_NOW + timedelta(seconds=1),
    )


def _event(
    request: futures.FuturesExecutionRequest,
    *,
    event_type: ibkr.IBKRExecutionEventType,
    filled: int,
    suffix: int,
    provider_order_id: str | None,
) -> futures.FuturesExecutionObservation:
    normalized = ibkr.normalize_ibkr_execution_event(
        request,
        ibkr.IBKRExecutionEventPayload(
            request_id=request.request_id,
            event_type=event_type,
            provider_order_id=provider_order_id,
            cumulative_filled_quantity=filled,
            observed_at=request.requested_at + timedelta(milliseconds=suffix),
            evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(suffix + 300)),
        ),
        observation_id=futures.FuturesExecutionObservationId(_uuid(suffix + 400)),
    )
    assert isinstance(normalized, result.Success)
    return normalized.value


def test_paper_futures_e2e_decision_to_ack_partial_fill_fill_and_reconciliation() -> None:
    decision = _decision(suffix=1000)
    request = futures.FuturesExecutionRequest(
        request_id=futures.FuturesExecutionRequestId(_uuid(1001)),
        account_id=_ACCOUNT,
        runtime_ref=_RUNTIME,
        decision_id=decision.decision_id,
        authority=_authority(),
        environment=futures.FuturesExecutionEnvironment.PAPER,
        mapping=_MAPPING,
        side=futures.FuturesOrderSide.BUY,
        quantity=2,
        order_type=futures.FuturesOrderType.MARKET,
        time_in_force=futures.FuturesTimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        idempotency_key=futures.FuturesIdempotencyKey(_uuid(1002)),
        requested_at=_NOW + timedelta(seconds=1),
    )

    translated = ibkr.translate_ibkr_paper_order(
        request,
        account_ref=ibkr.IBKRPaperAccountReference(_uuid(1003)),
    )
    assert isinstance(translated, result.Success)
    assert translated.value.request_id == request.request_id
    assert translated.value.order_ref == request.idempotency_key.value
    assert request.decision_id == decision.decision_id
    assert request.authority.account_id == request.account_id
    assert request.authority.runtime_ref == request.runtime_ref

    acknowledged = _event(
        request,
        event_type=ibkr.IBKRExecutionEventType.ACKNOWLEDGED,
        filled=0,
        suffix=1010,
        provider_order_id="paper-order-1001",
    )
    partial = _event(
        request,
        event_type=ibkr.IBKRExecutionEventType.PARTIAL_FILL,
        filled=1,
        suffix=1020,
        provider_order_id="paper-order-1001",
    )
    filled = _event(
        request,
        event_type=ibkr.IBKRExecutionEventType.FILL,
        filled=2,
        suffix=1030,
        provider_order_id="paper-order-1001",
    )

    assert acknowledged.state is futures.FuturesExecutionState.ACKNOWLEDGED
    assert partial.state is futures.FuturesExecutionState.PARTIALLY_FILLED
    assert filled.state is futures.FuturesExecutionState.FILLED
    assert partial.cumulative_filled_quantity == 1
    assert filled.cumulative_filled_quantity == request.quantity

    reconciled = ibkr.normalize_ibkr_reconciliation(
        ibkr.IBKRReconciliationPayload(
            request_id=request.request_id,
            status=ibkr.IBKRReconciliationStatus.MATCHED,
            reconciled_at=request.requested_at + timedelta(seconds=2),
            evidence_refs=(
                futures.FuturesExecutionEvidenceReference(_uuid(1040)),
                futures.FuturesExecutionEvidenceReference(_uuid(1041)),
            ),
        )
    )
    assert isinstance(reconciled, result.Success)
    assert reconciled.value.status is (
        futures.FuturesExecutionReconciliationStatus.MATCHED
    )


def test_lost_or_unknown_ack_is_contained_and_reconciled_without_second_order() -> None:
    request = _request(suffix=1100)
    translated = ibkr.translate_ibkr_paper_order(
        request,
        account_ref=ibkr.IBKRPaperAccountReference(_uuid(1101)),
    )
    assert isinstance(translated, result.Success)

    ambiguous = _event(
        request,
        event_type=ibkr.IBKRExecutionEventType.UNKNOWN,
        filled=0,
        suffix=1110,
        provider_order_id=None,
    )
    assert ambiguous.state is futures.FuturesExecutionState.AMBIGUOUS

    reconciliation = ibkr.normalize_ibkr_reconciliation(
        ibkr.IBKRReconciliationPayload(
            request_id=request.request_id,
            status=ibkr.IBKRReconciliationStatus.UNKNOWN,
            reconciled_at=request.requested_at + timedelta(seconds=2),
            evidence_refs=(futures.FuturesExecutionEvidenceReference(_uuid(1120)),),
        )
    )
    assert isinstance(reconciliation, result.Success)
    assert reconciliation.value.status is (
        futures.FuturesExecutionReconciliationStatus.AMBIGUOUS
    )

    replay = futures.classify_futures_request_replay(request, request)
    assert replay is futures.FuturesReplayDisposition.DUPLICATE_ALREADY_KNOWN
    assert translated.value.order_ref == request.idempotency_key.value

    forbidden = {"retry", "retry_order", "redispatch", "redispatch_order", "resend"}
    assert forbidden.isdisjoint(set(dir(ambiguous)))
    assert forbidden.isdisjoint(set(dir(reconciliation.value)))
    assert forbidden.isdisjoint(set(dir(ibkr.IBKRPaperOrderIntent)))


def test_paper_rejection_is_terminal_evidence_not_automatic_retry() -> None:
    request = _request(suffix=1200)
    rejected = _event(
        request,
        event_type=ibkr.IBKRExecutionEventType.REJECTED,
        filled=0,
        suffix=1210,
        provider_order_id=None,
    )

    assert rejected.state is futures.FuturesExecutionState.REJECTED
    assert rejected.cumulative_filled_quantity == 0
    assert not hasattr(rejected, "retry")
    assert not hasattr(rejected, "redispatch")


def test_paper_e2e_requires_explicit_core_decision_and_writer_authority_types() -> None:
    hints = get_type_hints(futures.FuturesExecutionRequest)

    assert hints["decision_id"] is DecisionId
    assert hints["authority"] is HostingExecutionAuthorityAttestation

    request = _request(suffix=1300)
    assert isinstance(request.decision_id, DecisionId)
    assert isinstance(request.authority, HostingExecutionAuthorityAttestation)
    assert request.authority.account_id == _ACCOUNT
    assert request.authority.runtime_ref == _RUNTIME


def test_paper_e2e_has_no_production_execution_environment_or_provider_sdk_surface() -> None:
    environments = {item.name for item in futures.FuturesExecutionEnvironment}
    assert environments == {"PAPER", "SIMULATION"}
    assert "PRODUCTION" not in environments
    assert "LIVE" not in environments

    prohibited = {
        "http_client",
        "oauth_client",
        "submit_order",
        "retry_order",
        "redispatch_order",
        "production_account",
        "authorization_header",
    }
    assert prohibited.isdisjoint(set(dir(ibkr.IBKRPaperOrderIntent)))
