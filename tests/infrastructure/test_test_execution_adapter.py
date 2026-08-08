from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionCancellation,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentAuthorization,
    MarketTestEnvironmentPolicy,
    authorize_market_test_account,
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
    TestExecutionAdapterError,
    TestExecutionGatewayReceipt,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 10, 40, tzinfo=UTC)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("23000000-0000-0000-0000-000000000001"))
)
_IDEMPOTENCY = ExecutionIdempotencyKey(
    UUID("23000000-0000-0000-0000-000000000002")
)


def _authorized_intent() -> AuthorizedOrderIntent:
    intent = OrderIntent(
        intent_id=OrderIntentId(UUID("23000000-0000-0000-0000-000000000003")),
        idempotency_key=_IDEMPOTENCY,
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_NOW,
        metadata=_METADATA,
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("23000000-0000-0000-0000-000000000004")
        ),
        policy_id=PreTradePolicyId("risk.pretrade.test"),
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(seconds=20),
        reason="test execution approved",
    )
    return AuthorizedOrderIntent(
        intent=intent,
        authorization=authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=_NOW + timedelta(seconds=2),
            reason="test execution switch enabled",
        ),
        authorized_at=_NOW + timedelta(seconds=3),
    )


def _submission() -> ExecutionSubmission:
    return ExecutionSubmission(
        request_id=ExecutionRequestId(
            UUID("23000000-0000-0000-0000-000000000005")
        ),
        receipt_id=ExecutionReceiptId(
            UUID("23000000-0000-0000-0000-000000000006")
        ),
        authorized_intent=_authorized_intent(),
        submitted_at=_NOW + timedelta(seconds=4),
    )


def _environment_authorization(
    environment: MarketRuntimeEnvironment,
) -> MarketTestEnvironmentAuthorization:
    result = authorize_market_test_account(
        MarketTestAccountIdentity(
            provider_key="reference-provider",
            account_ref="demo-account-01",
            environment=environment,
        ),
        policy=MarketTestEnvironmentPolicy(policy_id="mission02.execution.test"),
        authorized_at=_NOW + timedelta(seconds=3),
    )
    assert isinstance(result, Success)
    return result.value


class _Gateway:
    def __init__(self, *, fail_submit: bool = False) -> None:
        self.fail_submit = fail_submit
        self.submit_calls: list[MarketTestAccountIdentity] = []
        self.cancel_calls: list[tuple[MarketTestAccountIdentity, str]] = []

    def submit(
        self,
        *,
        account: MarketTestAccountIdentity,
        submission: ExecutionSubmission,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        self.submit_calls.append(account)
        if self.fail_submit:
            return Failure(TestExecutionAdapterError("test gateway unavailable"))
        return Success(
            TestExecutionGatewayReceipt(
                provider_execution_ref="provider-demo-0001",
                status=ExecutionStatus.ACCEPTED,
                recorded_at=submission.submitted_at + timedelta(seconds=1),
            )
        )

    def cancel(
        self,
        *,
        account: MarketTestAccountIdentity,
        provider_execution_ref: str,
        cancelled_at: datetime,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        self.cancel_calls.append((account, provider_execution_ref))
        return Success(
            TestExecutionGatewayReceipt(
                provider_execution_ref=provider_execution_ref,
                status=ExecutionStatus.CANCELLED,
                recorded_at=cancelled_at,
            )
        )


def test_demo_submission_reaches_gateway_and_returns_canonical_receipt() -> None:
    gateway = _Gateway()
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(
            MarketRuntimeEnvironment.DEMO
        ),
        gateway=gateway,
    )

    result = adapter.submit(_submission())

    assert isinstance(result, Success)
    assert result.value.status is ExecutionStatus.ACCEPTED
    assert len(gateway.submit_calls) == 1
    assert gateway.submit_calls[0].environment is MarketRuntimeEnvironment.DEMO
    assert len(adapter.receipts) == 1


def test_exact_replay_does_not_duplicate_external_submission() -> None:
    gateway = _Gateway()
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(
            MarketRuntimeEnvironment.TEST
        ),
        gateway=gateway,
    )
    submission = _submission()

    first = adapter.submit(submission)
    replay = adapter.submit(submission)

    assert isinstance(first, Success)
    assert isinstance(replay, Success)
    assert replay.value is first.value
    assert len(gateway.submit_calls) == 1


def test_gateway_failure_creates_no_local_execution_receipt() -> None:
    gateway = _Gateway(fail_submit=True)
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(
            MarketRuntimeEnvironment.DEMO
        ),
        gateway=gateway,
    )

    result = adapter.submit(_submission())

    assert isinstance(result, Failure)
    assert isinstance(result.error, TestExecutionAdapterError)
    assert adapter.receipts == ()


def test_cancellation_routes_to_same_test_account_and_provider_reference() -> None:
    gateway = _Gateway()
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(
            MarketRuntimeEnvironment.DEMO
        ),
        gateway=gateway,
    )
    submission = _submission()
    submitted = adapter.submit(submission)
    assert isinstance(submitted, Success)

    cancelled = adapter.cancel(
        ExecutionCancellation(
            receipt_id=submission.receipt_id,
            cancelled_at=_NOW + timedelta(seconds=6),
        )
    )

    assert isinstance(cancelled, Success)
    assert cancelled.value.status is ExecutionStatus.CANCELLED
    assert gateway.cancel_calls == [
        (
            _environment_authorization(MarketRuntimeEnvironment.DEMO).account,
            "provider-demo-0001",
        )
    ]


def test_gateway_receipt_logical_values_are_sanitized() -> None:
    receipt = TestExecutionGatewayReceipt(
        provider_execution_ref="provider-demo-0001",
        status=ExecutionStatus.ACCEPTED,
        recorded_at=_NOW,
    )

    assert receipt.logical_values() == (
        "provider-demo-0001",
        "accepted",
        _NOW.isoformat(),
    )
