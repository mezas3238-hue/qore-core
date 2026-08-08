from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.connectivity import ProviderEndpoint
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
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeOperationalLimits,
    OandaPracticeRuntimeConfiguration,
    oanda_practice_secret_requirements,
)
from qore.infrastructure.oanda_practice_execution_codec import (
    OandaPracticeOrderCreatePlan,
)
from qore.infrastructure.oanda_practice_execution_gateway import (
    OandaPracticeExecutionGateway,
    OandaPracticeExecutionGatewayValidationError,
    OandaPracticeExecutionTransportBoundary,
    OandaPracticeOrderCancelPlan,
    build_oanda_practice_order_cancel_plan,
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
    provider_key="oanda-v20",
    account_ref="practice-001",
    environment=MarketRuntimeEnvironment.DEMO,
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("32000000-0000-0000-0000-000000000001"))
)


def _configuration() -> OandaPracticeRuntimeConfiguration:
    return OandaPracticeRuntimeConfiguration(
        provider_key="oanda-v20",
        environment=MarketRuntimeEnvironment.DEMO,
        rest_endpoint=ProviderEndpoint(host="api-fxpractice.oanda.com"),
        streaming_endpoint=ProviderEndpoint(host="stream-fxpractice.oanda.com"),
        account=_ACCOUNT,
        symbols=("EUR_USD", "GBP_USD"),
        capabilities=(
            OandaPracticeCapability.ACCOUNT,
            OandaPracticeCapability.ORDERS,
            OandaPracticeCapability.PRICING,
            OandaPracticeCapability.TRANSACTIONS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        stream_connect_timeout=ExternalTransportTimeout(milliseconds=5000),
        limits=OandaPracticeOperationalLimits(
            rest_requests_per_second=1,
            active_streams=0,
            new_connections_per_second=1,
        ),
        secret_requirements=oanda_practice_secret_requirements(),
    )


def _submission(
    *,
    suffix: int = 2,
) -> ExecutionSubmission:
    intent = OrderIntent(
        intent_id=OrderIntentId(
            UUID(f"32000000-0000-0000-0000-{suffix:012d}")
        ),
        idempotency_key=ExecutionIdempotencyKey(
            UUID(f"32000000-0000-0000-1000-{suffix:012d}")
        ),
        instrument=ExecutionInstrument("EUR_USD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("10")),
        created_at=_NOW,
        metadata=_METADATA,
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID(f"32000000-0000-0000-2000-{suffix:012d}")
        ),
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
        request_id=ExecutionRequestId(
            UUID(f"32000000-0000-0000-3000-{suffix:012d}")
        ),
        receipt_id=ExecutionReceiptId(
            UUID(f"32000000-0000-0000-4000-{suffix:012d}")
        ),
        authorized_intent=authorized,
        submitted_at=_NOW + timedelta(seconds=4),
    )


def _create_response(
    *,
    provider_ref: str = "7001",
    fill_ref: str = "7002",
) -> ExternalTransportResponse:
    payload = {
        "lastTransactionID": fill_ref,
        "orderCreateTransaction": {
            "accountID": "practice-001",
            "id": provider_ref,
            "instrument": "EUR_USD",
            "positionFill": "DEFAULT",
            "time": "2026-08-08T23:30:05+00:00",
            "timeInForce": "FOK",
            "type": "MARKET_ORDER",
            "units": "10",
        },
        "orderFillTransaction": {
            "accountID": "practice-001",
            "id": fill_ref,
            "instrument": "EUR_USD",
            "orderID": provider_ref,
            "time": "2026-08-08T23:30:05.100000+00:00",
            "type": "ORDER_FILL",
            "units": "10",
        },
        "relatedTransactionIDs": [provider_ref, fill_ref],
    }
    return ExternalTransportResponse(
        status_code=201,
        received_at=_NOW + timedelta(seconds=6),
        payload=json.dumps(payload).encode("utf-8"),
    )


def _cancel_response(
    *,
    provider_ref: str = "7001",
    cancel_ref: str = "7003",
    timestamp: str = "2026-08-08T23:30:07+00:00",
) -> ExternalTransportResponse:
    payload = {
        "lastTransactionID": cancel_ref,
        "orderCancelTransaction": {
            "accountID": "practice-001",
            "id": cancel_ref,
            "orderID": provider_ref,
            "reason": "CLIENT_REQUEST",
            "time": timestamp,
            "type": "ORDER_CANCEL",
        },
        "relatedTransactionIDs": [cancel_ref],
    }
    return ExternalTransportResponse(
        status_code=200,
        received_at=_NOW + timedelta(seconds=8),
        payload=json.dumps(payload).encode("utf-8"),
    )


class _FakeExecutionTransport:
    def __init__(
        self,
        *,
        configuration: OandaPracticeRuntimeConfiguration,
        create_response: ExternalTransportResponse | None = None,
        cancel_response: ExternalTransportResponse | None = None,
        create_error: ExecutionBoundaryError | None = None,
        cancel_error: ExecutionBoundaryError | None = None,
    ) -> None:
        self._configuration = configuration
        self.create_response = create_response or _create_response()
        self.cancel_response = cancel_response or _cancel_response()
        self.create_error = create_error
        self.cancel_error = cancel_error
        self.create_calls: list[
            tuple[OandaPracticeOrderCreatePlan, ExternalRequestMetadata]
        ] = []
        self.cancel_calls: list[
            tuple[OandaPracticeOrderCancelPlan, ExternalRequestMetadata]
        ] = []

    @property
    def configuration(self) -> OandaPracticeRuntimeConfiguration:
        return self._configuration

    def create_order(
        self,
        plan: OandaPracticeOrderCreatePlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        self.create_calls.append((plan, metadata))
        if self.create_error is not None:
            return Failure(self.create_error)
        return Success(self.create_response)

    def cancel_order(
        self,
        plan: OandaPracticeOrderCancelPlan,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalTransportResponse, ExecutionBoundaryError]:
        self.cancel_calls.append((plan, metadata))
        if self.cancel_error is not None:
            return Failure(self.cancel_error)
        return Success(self.cancel_response)


def _accept_transport(port: OandaPracticeExecutionTransportBoundary) -> None:
    assert callable(port.create_order)
    assert callable(port.cancel_order)


def _accept_gateway(port: TestExecutionGatewayBoundary) -> None:
    assert callable(port.submit)
    assert callable(port.cancel)


def test_protocols_accept_fake_transport_and_gateway_composition() -> None:
    transport = _FakeExecutionTransport(configuration=_configuration())
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )

    _accept_transport(transport)
    _accept_gateway(gateway)


def test_submit_calls_transport_once_and_preserves_original_metadata() -> None:
    transport = _FakeExecutionTransport(configuration=_configuration())
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )
    submission = _submission()

    result = gateway.submit(account=_ACCOUNT, submission=submission)

    assert isinstance(result, Success)
    assert result.value.provider_execution_ref == "7001"
    assert result.value.status is ExecutionStatus.ACCEPTED
    assert len(transport.create_calls) == 1
    plan, metadata = transport.create_calls[0]
    assert metadata is submission.authorized_intent.intent.metadata
    assert plan.account == _ACCOUNT
    assert plan.endpoint_origin == "https://api-fxpractice.oanda.com"
    assert len(gateway.outcomes) == 1
    assert gateway.outcomes[0].provider_execution_ref == "7001"


def test_wrong_account_blocks_before_transport() -> None:
    transport = _FakeExecutionTransport(configuration=_configuration())
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )
    wrong_account = MarketTestAccountIdentity(
        provider_key="oanda-v20",
        account_ref="practice-other",
        environment=MarketRuntimeEnvironment.DEMO,
    )

    result = gateway.submit(account=wrong_account, submission=_submission())

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeExecutionGatewayValidationError)
    assert transport.create_calls == []
    assert gateway.outcomes == ()


def test_transport_failure_is_not_retried_or_recorded() -> None:
    error = OandaPracticeExecutionGatewayValidationError("provider unavailable")
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_error=error,
    )
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )

    result = gateway.submit(account=_ACCOUNT, submission=_submission())

    assert isinstance(result, Failure)
    assert result.error is error
    assert len(transport.create_calls) == 1
    assert gateway.outcomes == ()


def test_ambiguous_provider_payload_is_not_retried_or_recorded() -> None:
    ambiguous = ExternalTransportResponse(
        status_code=201,
        received_at=_NOW + timedelta(seconds=6),
        payload=b'{"lastTransactionID":"7002"}',
    )
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        create_response=ambiguous,
    )
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )

    result = gateway.submit(account=_ACCOUNT, submission=_submission())

    assert isinstance(result, Failure)
    assert len(transport.create_calls) == 1
    assert gateway.outcomes == ()


def test_cancel_requires_known_provider_ref_and_reuses_submit_metadata() -> None:
    transport = _FakeExecutionTransport(configuration=_configuration())
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )
    submission = _submission()
    submitted = gateway.submit(account=_ACCOUNT, submission=submission)
    assert isinstance(submitted, Success)

    cancelled_at = _NOW + timedelta(seconds=6)
    cancelled = gateway.cancel(
        account=_ACCOUNT,
        provider_execution_ref="7001",
        cancelled_at=cancelled_at,
    )

    assert isinstance(cancelled, Success)
    assert cancelled.value.status is ExecutionStatus.CANCELLED
    assert len(transport.cancel_calls) == 1
    plan, metadata = transport.cancel_calls[0]
    assert metadata is submission.authorized_intent.intent.metadata
    assert plan.provider_execution_ref == "7001"
    assert plan.requested_at == cancelled_at
    assert plan.path == "/v3/accounts/practice-001/orders/7001/cancel"
    assert "practice-001" not in repr(plan.sanitized_values())


def test_unknown_cancel_is_blocked_without_transport() -> None:
    transport = _FakeExecutionTransport(configuration=_configuration())
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )

    result = gateway.cancel(
        account=_ACCOUNT,
        provider_execution_ref="9999",
        cancelled_at=_NOW + timedelta(seconds=6),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutionBoundaryNotFoundError)
    assert transport.cancel_calls == []


def test_cancel_failure_is_not_retried() -> None:
    error = OandaPracticeExecutionGatewayValidationError("cancel unavailable")
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        cancel_error=error,
    )
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )
    submitted = gateway.submit(account=_ACCOUNT, submission=_submission())
    assert isinstance(submitted, Success)

    result = gateway.cancel(
        account=_ACCOUNT,
        provider_execution_ref="7001",
        cancelled_at=_NOW + timedelta(seconds=6),
    )

    assert isinstance(result, Failure)
    assert result.error is error
    assert len(transport.cancel_calls) == 1


def test_cancel_receipt_cannot_predate_cancel_request() -> None:
    stale_response = _cancel_response(timestamp="2026-08-08T23:30:05+00:00")
    transport = _FakeExecutionTransport(
        configuration=_configuration(),
        cancel_response=stale_response,
    )
    gateway = OandaPracticeExecutionGateway(
        configuration=_configuration(),
        transport=transport,
    )
    submitted = gateway.submit(account=_ACCOUNT, submission=_submission())
    assert isinstance(submitted, Success)

    result = gateway.cancel(
        account=_ACCOUNT,
        provider_execution_ref="7001",
        cancelled_at=_NOW + timedelta(seconds=6),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeExecutionGatewayValidationError)
    assert len(transport.cancel_calls) == 1


def test_cancel_plan_requires_practice_identity_and_is_deterministic() -> None:
    first = build_oanda_practice_order_cancel_plan(
        _configuration(),
        provider_execution_ref="7001",
        requested_at=_NOW + timedelta(seconds=6),
    )
    second = build_oanda_practice_order_cancel_plan(
        _configuration(),
        provider_execution_ref="7001",
        requested_at=_NOW + timedelta(seconds=6),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value == second.value
    assert first.value.logical_values() == second.value.logical_values()
    assert "practice-001" not in repr(first.value.sanitized_values())


def test_canonical_adapter_idempotency_prevents_second_gateway_transport_call() -> None:
    configuration = _configuration()
    transport = _FakeExecutionTransport(configuration=configuration)
    gateway = OandaPracticeExecutionGateway(
        configuration=configuration,
        transport=transport,
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
            allowed_instruments=(ExecutionInstrument("EUR_USD"),),
            max_order_quantity=Decimal("10"),
        ),
    )
    submission = _submission()

    first = safety.submit(submission)
    replay = safety.submit(submission)

    assert isinstance(first, Success)
    assert isinstance(replay, Success)
    assert replay.value == first.value
    assert len(transport.create_calls) == 1
