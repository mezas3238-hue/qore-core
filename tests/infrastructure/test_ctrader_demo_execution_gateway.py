from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_codec import (
    CTraderOrderCancelPlan,
    CTraderOrderCreatePlan,
)
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoAttemptState,
    CTraderDemoExecutionConflictError,
    CTraderDemoExecutionNotAcceptedError,
    CTraderDemoExecutionUnknownOutcomeError,
    CTraderDemoFillReconciliationStatus,
)
from qore.infrastructure.ctrader_demo_execution_gateway import (
    CTraderDemoExecutionGateway,
    CTraderDemoExecutionGatewayValidationError,
    CTraderDemoExecutionTransportBoundary,
)
from qore.infrastructure.ctrader_demo_mutation_ledger import (
    InMemoryCTraderDemoMutationLedger,
    JsonFileCTraderDemoMutationLedger,
)
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionBoundaryNotFoundError,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentPolicy,
    authorize_market_test_account,
)
from qore.infrastructure.market_test_safety_guard import (
    MarketTestSafetyPolicy,
    SafetyGuardedTestExecutionBoundary,
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
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.pretrade_safety import (
    AuthorizedOrderIntent,
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
)
from qore.infrastructure.test_execution_adapter import (
    AuthorizedTestExecutionAdapter,
    TestExecutionGatewayBoundary,
)
from qore.infrastructure.transport import (
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 23, 30, tzinfo=UTC)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="demo-001",
    environment=MarketRuntimeEnvironment.DEMO,
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("32000000-0000-0000-0000-000000000001"))
)


def _configuration() -> CTraderDemoRuntimeConfiguration:
    return CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=_ACCOUNT,
        symbol_mappings=(
            CTraderSymbolMapping(
                instrument=ExecutionInstrument("EURUSD"),
                symbol_id=1234,
                symbol_name="EURUSD",
                digits=5,
                volume_step=Decimal("1"),
                min_volume_units=1,
                max_volume_units=1_000_000,
                step_volume_units=1,
            ),
        ),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )


def _submission(
    *,
    suffix: int = 2,
    quantity: str = "10",
    instrument: str = "EURUSD",
) -> ExecutionSubmission:
    intent = OrderIntent(
        intent_id=OrderIntentId(UUID(f"32000000-0000-0000-0000-{suffix:012d}")),
        idempotency_key=ExecutionIdempotencyKey(UUID(f"32000000-0000-0000-1000-{suffix:012d}")),
        instrument=ExecutionInstrument(instrument),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal(quantity)),
        created_at=_NOW,
        metadata=_METADATA,
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(UUID(f"32000000-0000-0000-2000-{suffix:012d}")),
        policy_id=PreTradePolicyId("mission03.demo.pretrade"),
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(minutes=1),
        reason="bounded demo execution approved",
    )
    authorized = AuthorizedOrderIntent(
        intent=intent,
        authorization=authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=_NOW + timedelta(seconds=2),
            reason="demo execution switch enabled",
        ),
        authorized_at=_NOW + timedelta(seconds=3),
    )
    return ExecutionSubmission(
        request_id=ExecutionRequestId(UUID(f"32000000-0000-0000-3000-{suffix:012d}")),
        receipt_id=ExecutionReceiptId(UUID(f"32000000-0000-0000-4000-{suffix:012d}")),
        authorized_intent=authorized,
        submitted_at=_NOW + timedelta(seconds=4),
    )


def _create_response(
    *,
    submission: ExecutionSubmission,
    provider_ref: str = "70001",
    status: str = "accepted",
) -> ExternalTransportResponse:
    payload = {
        "orderId": provider_ref,
        "clientMsgId": str(submission.idempotency_key.value),
        "symbolId": 1234,
        "status": status,
        "createdAt": "2026-08-08T23:30:05+00:00",
    }
    return ExternalTransportResponse(
        status_code=200,
        received_at=_NOW + timedelta(seconds=6),
        payload=json.dumps(payload).encode("utf-8"),
    )


def _fill_payload(
    *,
    fill_ref: str = "90001",
    order_ref: str = "70001",
    filled_volume: int = 4,
    cumulative_volume: int = 4,
    is_complete: bool = False,
    timestamp: str = "2026-08-08T23:30:06+00:00",
    price: str = "1.23456",
) -> bytes:
    return json.dumps(
        {
            "orderId": order_ref,
            "fillId": fill_ref,
            "symbolId": 1234,
            "filledVolume": filled_volume,
            "cumulativeVolume": cumulative_volume,
            "price": price,
            "timestamp": timestamp,
            "isComplete": is_complete,
        }
    ).encode("utf-8")


class _FakeExecutionTransport:
    def __init__(
        self,
        *,
        configuration: CTraderDemoRuntimeConfiguration,
        create_response: ExternalTransportResponse | None = None,
        submit_error: ExecutionBoundaryError | None = None,
        cancel_response: ExternalTransportResponse | None = None,
        query_response: ExternalTransportResponse | None = None,
        discover_response: ExternalTransportResponse | None = None,
        discover_error: ExecutionBoundaryError | None = None,
    ) -> None:
        self._configuration = configuration
        self.create_response = create_response
        self.submit_error = submit_error
        self.cancel_response = cancel_response
        self.query_response = query_response
        self.discover_response = discover_response
        self.discover_error = discover_error
        self.submit_calls: list[tuple[CTraderOrderCreatePlan, ExternalRequestMetadata]] = []
        self.cancel_calls: list[tuple[CTraderOrderCancelPlan, ExternalRequestMetadata]] = []
        self.query_calls: list[tuple[str, ExternalRequestMetadata]] = []
        self.discover_calls: list[
            tuple[CTraderOrderCreatePlan, datetime, datetime, ExternalRequestMetadata]
        ] = []

    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration:
        return self._configuration

    def submit_order(
        self,
        plan: CTraderOrderCreatePlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        self.submit_calls.append((plan, metadata))
        if self.submit_error is not None:
            return Failure(self.submit_error)
        assert self.create_response is not None
        return Success(self.create_response)

    def cancel_order(
        self,
        plan: CTraderOrderCancelPlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        self.cancel_calls.append((plan, metadata))
        if self.cancel_response is None:
            return Failure(CTraderDemoExecutionGatewayValidationError("cancel unavailable"))
        return Success(self.cancel_response)

    def query_order(
        self,
        provider_order_ref: str,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        self.query_calls.append((provider_order_ref, metadata))
        if self.query_response is None:
            return Failure(CTraderDemoExecutionGatewayValidationError("query unavailable"))
        return Success(self.query_response)

    def discover_order(
        self,
        plan: CTraderOrderCreatePlan,
        *,
        from_timestamp: datetime,
        to_timestamp: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        self.discover_calls.append((plan, from_timestamp, to_timestamp, metadata))
        if self.discover_error is not None:
            return Failure(self.discover_error)
        if self.discover_response is None:
            return Failure(CTraderDemoExecutionGatewayValidationError("discovery unavailable"))
        return Success(self.discover_response)


def _gateway(
    *,
    transport: _FakeExecutionTransport,
) -> CTraderDemoExecutionGateway:
    return CTraderDemoExecutionGateway(
        configuration=_configuration(),
        transport=transport,
        mutation_ledger=InMemoryCTraderDemoMutationLedger(),
    )


def test_protocols_accept_fake_transport_and_gateway() -> None:
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=_submission()),
    )
    gateway = _gateway(transport=transport)
    port: CTraderDemoExecutionTransportBoundary = transport
    boundary: TestExecutionGatewayBoundary = gateway
    assert callable(port.submit_order)
    assert callable(boundary.submit)
    assert callable(boundary.cancel)


def test_submit_calls_transport_once_and_records_outcome() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)

    result = gateway.submit(account=_ACCOUNT, submission=submission)

    assert isinstance(result, Success)
    assert result.value.provider_execution_ref == "70001"
    assert result.value.status is ExecutionStatus.ACCEPTED
    assert len(transport.submit_calls) == 1
    assert len(gateway.outcomes) == 1
    assert gateway.outcomes[0].provider_order_ref == "70001"


def test_wrong_account_blocks_before_transport() -> None:
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=_submission()),
    )
    gateway = _gateway(transport=transport)
    wrong = MarketTestAccountIdentity(
        provider_key="ctrader-demo",
        account_ref="demo-other",
        environment=MarketRuntimeEnvironment.DEMO,
    )

    result = gateway.submit(account=wrong, submission=_submission())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoExecutionGatewayValidationError)
    assert transport.submit_calls == []


def test_transport_failure_is_unknown_outcome_and_never_retried() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("provider timeout after wire send"),
    )
    gateway = _gateway(transport=transport)

    first = gateway.submit(account=_ACCOUNT, submission=submission)
    replay = gateway.submit(account=_ACCOUNT, submission=submission)

    assert isinstance(first, Failure)
    assert isinstance(first.error, CTraderDemoExecutionUnknownOutcomeError)
    assert isinstance(replay, Failure)
    assert isinstance(replay.error, CTraderDemoExecutionUnknownOutcomeError)
    assert len(transport.submit_calls) == 1
    assert gateway.attempts[0].state is CTraderDemoAttemptState.OUTCOME_UNKNOWN


def test_idempotency_duplicate_returns_same_receipt_without_second_call() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)

    first = gateway.submit(account=_ACCOUNT, submission=submission)
    replay = gateway.submit(account=_ACCOUNT, submission=submission)

    assert isinstance(first, Success)
    assert isinstance(replay, Success)
    assert replay.value == first.value
    assert len(transport.submit_calls) == 1


def test_idempotency_conflict_when_same_key_different_payload() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)
    first = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(first, Success)

    different = _submission(suffix=2, quantity="20")
    result = gateway.submit(account=_ACCOUNT, submission=different)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoExecutionConflictError)


def test_provider_reject_is_not_accepted() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission, status="rejected"),
    )
    gateway = _gateway(transport=transport)

    result = gateway.submit(account=_ACCOUNT, submission=submission)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoExecutionNotAcceptedError)


def test_fill_observation_is_idempotent_and_handles_out_of_order() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)

    first = gateway.observe_fill(
        submission,
        _fill_payload(fill_ref="f1", cumulative_volume=4),
        received_at=_NOW + timedelta(seconds=7),
    )
    duplicate = gateway.observe_fill(
        submission,
        _fill_payload(fill_ref="f1", cumulative_volume=4),
        received_at=_NOW + timedelta(seconds=8),
    )
    late = gateway.observe_fill(
        submission,
        _fill_payload(
            fill_ref="f2",
            filled_volume=2,
            cumulative_volume=2,
            timestamp="2026-08-08T23:30:04+00:00",
        ),
        received_at=_NOW + timedelta(seconds=9),
    )

    assert isinstance(first, Success)
    assert isinstance(duplicate, Success)
    assert duplicate.value == first.value
    assert isinstance(late, Success)


def test_fill_observation_rejects_overfill() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)

    result = gateway.observe_fill(
        submission,
        _fill_payload(cumulative_volume=11),
        received_at=_NOW + timedelta(seconds=7),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoExecutionConflictError)


def test_reconcile_fills_matched_and_diverged() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission, status="filled"),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)

    matched_observation = gateway.observe_fill(
        submission,
        _fill_payload(cumulative_volume=10, is_complete=True),
        received_at=_NOW + timedelta(seconds=7),
    )
    assert isinstance(matched_observation, Success)
    matched = gateway.reconcile_fills(
        submission.receipt_id,
        reconciled_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(matched, Success)
    assert matched.value.status is CTraderDemoFillReconciliationStatus.MATCHED

    diverged_submission = _submission(suffix=3)
    diverged_transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(
            submission=diverged_submission, provider_ref="70002", status="filled"
        ),
    )
    diverged_gateway = _gateway(transport=diverged_transport)
    diverged = diverged_gateway.submit(account=_ACCOUNT, submission=diverged_submission)
    assert isinstance(diverged, Success)
    diverged_gateway.observe_fill(
        diverged_submission,
        _fill_payload(
            fill_ref="f1",
            order_ref="70002",
            cumulative_volume=8,
            is_complete=True,
        ),
        received_at=_NOW + timedelta(seconds=7),
    )
    reconciliation = diverged_gateway.reconcile_fills(
        diverged_submission.receipt_id,
        reconciled_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(reconciliation, Success)
    assert reconciliation.value.status is CTraderDemoFillReconciliationStatus.DIVERGED


def test_cancel_requires_known_provider_ref() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)

    result = gateway.cancel(
        account=_ACCOUNT,
        provider_execution_ref="99999",
        cancelled_at=_NOW + timedelta(seconds=6),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutionBoundaryNotFoundError)


def test_resolve_unknown_outcome_not_found_without_scope_is_contained() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("disconnect"),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Failure)

    transport.query_response = ExternalTransportResponse(
        status_code=404,
        received_at=_NOW + timedelta(seconds=10),
        payload=b"{}",
    )
    contained = gateway.resolve_unknown_outcome(
        receipt_id=submission.receipt_id,
        provider_order_ref="70001",
        queried_at=_NOW + timedelta(seconds=9),
    )
    assert isinstance(contained, Success)
    assert contained.value.state is CTraderDemoAttemptState.CONTAINED


def test_resolve_unknown_outcome_not_found_with_complete_scope_is_resolved() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("disconnect"),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Failure)

    transport.query_response = ExternalTransportResponse(
        status_code=404,
        received_at=_NOW + timedelta(seconds=10),
        payload=b"{}",
    )
    resolved = gateway.resolve_unknown_outcome(
        receipt_id=submission.receipt_id,
        provider_order_ref="70001",
        queried_at=_NOW + timedelta(seconds=9),
        scope_complete=True,
    )
    assert isinstance(resolved, Success)
    assert resolved.value.state is CTraderDemoAttemptState.RESOLVED


def test_resolve_unknown_outcome_recovers_definitive_state() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("disconnect"),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Failure)

    transport.query_response = ExternalTransportResponse(
        status_code=200,
        received_at=_NOW + timedelta(seconds=10),
        payload=json.dumps(
            {
                "orderId": "70001",
                "status": "filled",
                "createdAt": "2026-08-08T23:30:05+00:00",
            }
        ).encode("utf-8"),
    )
    resolved = gateway.resolve_unknown_outcome(
        receipt_id=submission.receipt_id,
        provider_order_ref="70001",
        queried_at=_NOW + timedelta(seconds=9),
    )
    assert isinstance(resolved, Success)
    assert resolved.value.state is CTraderDemoAttemptState.RESOLVED
    assert resolved.value.provider_order_ref == "70001"


def test_discover_unknown_outcome_binds_unique_match_then_reconciles() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("disconnect"),
        discover_response=ExternalTransportResponse(
            status_code=200,
            received_at=_NOW + timedelta(seconds=9),
            payload=b'{"orderId":"70001","status":"accepted"}',
        ),
        query_response=ExternalTransportResponse(
            status_code=200,
            received_at=_NOW + timedelta(seconds=10),
            payload=(
                b'{"orderId":"70001","status":"filled",'
                b'"createdAt":"2026-08-08T23:30:05+00:00"}'
            ),
        ),
    )
    gateway = _gateway(transport=transport)
    assert isinstance(gateway.submit(account=_ACCOUNT, submission=submission), Failure)

    result = gateway.discover_unknown_outcome(
        receipt_id=submission.receipt_id,
        from_timestamp=_NOW,
        to_timestamp=_NOW + timedelta(minutes=1),
        searched_at=_NOW + timedelta(seconds=8),
    )

    assert isinstance(result, Success)
    assert result.value.state is CTraderDemoAttemptState.RESOLVED
    assert result.value.provider_order_ref == "70001"
    assert len(transport.discover_calls) == 1
    assert transport.query_calls == [("70001", _METADATA)]
    assert len(transport.submit_calls) == 1


def test_discover_unknown_outcome_complete_zero_match_resolves_without_retry() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("disconnect"),
        discover_response=ExternalTransportResponse(
            status_code=404,
            received_at=_NOW + timedelta(seconds=9),
            payload=b'{"reason":"complete search found no match"}',
        ),
    )
    gateway = _gateway(transport=transport)
    assert isinstance(gateway.submit(account=_ACCOUNT, submission=submission), Failure)

    result = gateway.discover_unknown_outcome(
        receipt_id=submission.receipt_id,
        from_timestamp=_NOW,
        to_timestamp=_NOW + timedelta(minutes=1),
        searched_at=_NOW + timedelta(seconds=8),
    )

    assert isinstance(result, Success)
    assert result.value.state is CTraderDemoAttemptState.RESOLVED
    assert result.value.provider_order_ref is None
    assert transport.query_calls == []
    assert len(transport.submit_calls) == 1


def test_discover_unknown_outcome_ambiguous_or_incomplete_is_contained() -> None:
    for response in (
        ExternalTransportResponse(
            status_code=409,
            received_at=_NOW + timedelta(seconds=9),
            payload=b'{"reason":"multiple matches"}',
        ),
        None,
    ):
        submission = _submission(suffix=40 if response is not None else 41)
        transport = _FakeExecutionTransport(
            configuration=_configuration(),
            submit_error=CTraderDemoExecutionGatewayValidationError("disconnect"),
            discover_response=response,
            discover_error=(
                None
                if response is not None
                else CTraderDemoExecutionGatewayValidationError("incomplete search")
            ),
        )
        gateway = _gateway(transport=transport)
        assert isinstance(gateway.submit(account=_ACCOUNT, submission=submission), Failure)

        result = gateway.discover_unknown_outcome(
            receipt_id=submission.receipt_id,
            from_timestamp=_NOW,
            to_timestamp=_NOW + timedelta(minutes=1),
            searched_at=_NOW + timedelta(seconds=8),
        )

        assert isinstance(result, Success)
        assert result.value.state is CTraderDemoAttemptState.CONTAINED
        assert transport.query_calls == []
        assert len(transport.submit_calls) == 1


def test_discover_unknown_outcome_contradictory_query_is_contained() -> None:
    submission = _submission(suffix=42)
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("disconnect"),
        discover_response=ExternalTransportResponse(
            status_code=200,
            received_at=_NOW + timedelta(seconds=9),
            payload=b'{"orderId":"70001"}',
        ),
        query_response=ExternalTransportResponse(
            status_code=404,
            received_at=_NOW + timedelta(seconds=10),
            payload=b"{}",
        ),
    )
    gateway = _gateway(transport=transport)
    assert isinstance(gateway.submit(account=_ACCOUNT, submission=submission), Failure)

    result = gateway.discover_unknown_outcome(
        receipt_id=submission.receipt_id,
        from_timestamp=_NOW,
        to_timestamp=_NOW + timedelta(minutes=1),
        searched_at=_NOW + timedelta(seconds=8),
    )

    assert isinstance(result, Success)
    assert result.value.state is CTraderDemoAttemptState.CONTAINED
    assert len(transport.submit_calls) == 1


def test_discover_unknown_outcome_query_failure_is_contained() -> None:
    submission = _submission(suffix=46)
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("disconnect"),
        discover_response=ExternalTransportResponse(
            status_code=200,
            received_at=_NOW + timedelta(seconds=9),
            payload=b'{"orderId":"70001"}',
        ),
    )
    gateway = _gateway(transport=transport)
    assert isinstance(gateway.submit(account=_ACCOUNT, submission=submission), Failure)

    result = gateway.discover_unknown_outcome(
        receipt_id=submission.receipt_id,
        from_timestamp=_NOW,
        to_timestamp=_NOW + timedelta(minutes=1),
        searched_at=_NOW + timedelta(seconds=8),
    )

    assert isinstance(result, Success)
    assert result.value.state is CTraderDemoAttemptState.CONTAINED
    assert len(transport.submit_calls) == 1


def test_durable_unknown_restart_blocks_create_and_recovers_by_discovery(
    tmp_path: Path,
) -> None:
    submission = _submission(suffix=43)
    path = tmp_path / "ctrader-mutations.json"
    first_transport = _FakeExecutionTransport(
        configuration=_configuration(),
        submit_error=CTraderDemoExecutionGatewayValidationError("lost response"),
    )
    first = CTraderDemoExecutionGateway(
        configuration=_configuration(),
        transport=first_transport,
        mutation_ledger=JsonFileCTraderDemoMutationLedger(path),
    )
    assert isinstance(first.submit(account=_ACCOUNT, submission=submission), Failure)
    assert len(first_transport.submit_calls) == 1

    recovery_transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
        discover_response=ExternalTransportResponse(
            status_code=200,
            received_at=_NOW + timedelta(seconds=9),
            payload=b'{"orderId":"70001"}',
        ),
        query_response=ExternalTransportResponse(
            status_code=200,
            received_at=_NOW + timedelta(seconds=10),
            payload=(
                b'{"orderId":"70001","status":"accepted",'
                b'"createdAt":"2026-08-08T23:30:05+00:00"}'
            ),
        ),
    )
    recovered = CTraderDemoExecutionGateway(
        configuration=_configuration(),
        transport=recovery_transport,
        mutation_ledger=JsonFileCTraderDemoMutationLedger(path),
    )
    blocked = recovered.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(blocked, Failure)
    assert isinstance(blocked.error, CTraderDemoExecutionUnknownOutcomeError)
    assert recovery_transport.submit_calls == []
    assert isinstance(recovered.restore_submission(submission), Success)

    resolved = recovered.discover_unknown_outcome(
        receipt_id=submission.receipt_id,
        from_timestamp=_NOW,
        to_timestamp=_NOW + timedelta(minutes=1),
        searched_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(resolved, Success)
    assert resolved.value.state is CTraderDemoAttemptState.RESOLVED
    assert resolved.value.provider_order_ref == "70001"
    assert recovery_transport.submit_calls == []


def test_restart_after_risk_fence_treats_attempt_as_unknown_and_never_sends(
    tmp_path: Path,
) -> None:
    submission = _submission(suffix=44)
    path = tmp_path / "ctrader-risk-fence.json"
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    first = CTraderDemoExecutionGateway(
        configuration=_configuration(),
        transport=transport,
        mutation_ledger=JsonFileCTraderDemoMutationLedger(path),
    )
    fenced = first.stage_risk_fence(
        submission,
        risk_authorization_id="risk-auth-1",
        risk_authorization_fingerprint="a" * 64,
        risk_reservation_id="risk-reservation-1",
    )
    assert isinstance(fenced, Success)

    recovered = CTraderDemoExecutionGateway(
        configuration=_configuration(),
        transport=transport,
        mutation_ledger=JsonFileCTraderDemoMutationLedger(path),
    )
    assert recovered.attempts[0].state is CTraderDemoAttemptState.OUTCOME_UNKNOWN
    assert isinstance(recovered.submit(account=_ACCOUNT, submission=submission), Failure)
    assert transport.submit_calls == []


def test_durable_fill_identity_survives_restart_and_preserves_real_conflict(
    tmp_path: Path,
) -> None:
    submission = _submission(suffix=45)
    path = tmp_path / "ctrader-fills.json"
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission, status="filled"),
    )
    first = CTraderDemoExecutionGateway(
        configuration=_configuration(),
        transport=transport,
        mutation_ledger=JsonFileCTraderDemoMutationLedger(path),
    )
    assert isinstance(first.submit(account=_ACCOUNT, submission=submission), Success)
    assert isinstance(
        first.observe_fill(
            submission,
            _fill_payload(cumulative_volume=10, filled_volume=10, is_complete=True),
            received_at=_NOW + timedelta(seconds=7),
        ),
        Success,
    )

    recovered = CTraderDemoExecutionGateway(
        configuration=_configuration(),
        transport=transport,
        mutation_ledger=JsonFileCTraderDemoMutationLedger(path),
    )
    assert isinstance(recovered.restore_submission(submission), Success)
    conflict = recovered.observe_fill(
        submission,
        _fill_payload(
            cumulative_volume=10,
            filled_volume=10,
            is_complete=True,
            price="1.99999",
        ),
        received_at=_NOW + timedelta(seconds=20),
    )
    assert isinstance(conflict, Failure)
    assert isinstance(conflict.error, CTraderDemoExecutionConflictError)


def test_fill_for_different_order_reference_is_rejected() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)

    result = gateway.observe_fill(
        submission,
        _fill_payload(order_ref="99999", cumulative_volume=4),
        received_at=_NOW + timedelta(seconds=7),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoExecutionConflictError)


def test_async_complete_fill_reconciles_matched() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission, status="accepted"),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)

    gateway.observe_fill(
        submission,
        _fill_payload(
            filled_volume=10,
            cumulative_volume=10,
            is_complete=True,
        ),
        received_at=_NOW + timedelta(seconds=7),
    )
    reconciliation = gateway.reconcile_fills(
        submission.receipt_id,
        reconciled_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(reconciliation, Success)
    assert reconciliation.value.status is CTraderDemoFillReconciliationStatus.MATCHED


def test_rejected_submission_replays_with_consistent_error() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission, status="rejected"),
    )
    gateway = _gateway(transport=transport)
    first = gateway.submit(account=_ACCOUNT, submission=submission)
    replay = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(first, Failure)
    assert isinstance(replay, Failure)
    assert isinstance(first.error, CTraderDemoExecutionNotAcceptedError)
    assert isinstance(replay.error, CTraderDemoExecutionNotAcceptedError)
    assert len(transport.submit_calls) == 1


def test_project_execution_observation_composes_canonical_reconciliation() -> None:
    from qore.infrastructure.execution_reconciliation import (
        reconcile_execution,
    )

    submission = _submission()
    configuration = _configuration()
    transport = _FakeExecutionTransport(
        configuration=configuration,
        create_response=_create_response(submission=submission),
    )
    gateway = CTraderDemoExecutionGateway(
        configuration=configuration,
        transport=transport,
        mutation_ledger=InMemoryCTraderDemoMutationLedger(),
    )
    environment_result = authorize_market_test_account(
        _ACCOUNT,
        policy=MarketTestEnvironmentPolicy(policy_id="mission03.demo.execution"),
        authorized_at=_NOW + timedelta(seconds=3),
    )
    assert isinstance(environment_result, Success)
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=environment_result.value,
        gateway=gateway,
    )
    safety = SafetyGuardedTestExecutionBoundary(
        adapter=adapter,
        policy=MarketTestSafetyPolicy(
            policy_id="mission03.demo.execution-safety",
            allowed_accounts=(_ACCOUNT,),
            allowed_instruments=(ExecutionInstrument("EURUSD"),),
            max_order_quantity=Decimal("10"),
        ),
    )
    submitted = safety.submit(submission)
    assert isinstance(submitted, Success)

    observation = gateway.project_execution_observation(
        submission.receipt_id,
        observed_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(observation, Success)
    snapshot = reconcile_execution(
        submitted.value,
        observation.value,
        reconciled_at=_NOW + timedelta(seconds=9),
    )
    assert isinstance(snapshot, Success)
    assert snapshot.value.status.value == "matched"


def test_no_secret_leakage_in_outcome_and_plan_sanitization() -> None:
    submission = _submission()
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=_create_response(submission=submission),
    )
    gateway = _gateway(transport=transport)
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)

    outcome = gateway.outcomes[0]
    assert "demo-001" not in repr(outcome.sanitized_values())
    assert outcome.account_fingerprint.startswith("sha256:")
    assert "token" not in repr(outcome.sanitized_values()).lower()


def test_full_boundary_composition_idempotency() -> None:
    submission = _submission()
    configuration = _configuration()
    transport = _FakeExecutionTransport(
        configuration=configuration,
        create_response=_create_response(submission=submission),
    )
    gateway = CTraderDemoExecutionGateway(
        configuration=configuration,
        transport=transport,
        mutation_ledger=InMemoryCTraderDemoMutationLedger(),
    )
    environment_result = authorize_market_test_account(
        _ACCOUNT,
        policy=MarketTestEnvironmentPolicy(policy_id="mission03.demo.execution"),
        authorized_at=_NOW + timedelta(seconds=3),
    )
    assert isinstance(environment_result, Success)
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=environment_result.value,
        gateway=gateway,
    )
    safety = SafetyGuardedTestExecutionBoundary(
        adapter=adapter,
        policy=MarketTestSafetyPolicy(
            policy_id="mission03.demo.execution-safety",
            allowed_accounts=(_ACCOUNT,),
            allowed_instruments=(ExecutionInstrument("EURUSD"),),
            max_order_quantity=Decimal("10"),
        ),
    )

    first = safety.submit(submission)
    replay = safety.submit(submission)

    assert isinstance(first, Success)
    assert isinstance(replay, Success)
    assert replay.value == first.value
    assert len(transport.submit_calls) == 1
