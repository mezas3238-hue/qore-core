from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
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
from qore.infrastructure.market_test_safety_guard import (
    MarketTestSafetyBlockedError,
    MarketTestSafetyPolicy,
    MarketTestSafetyValidationError,
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
    TestExecutionGatewayReceipt,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 10, 50, tzinfo=UTC)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="reference-provider",
    account_ref="demo-account-01",
    environment=MarketRuntimeEnvironment.DEMO,
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("24000000-0000-0000-0000-000000000001"))
)


def _environment_authorization() -> MarketTestEnvironmentAuthorization:
    result = authorize_market_test_account(
        _ACCOUNT,
        policy=MarketTestEnvironmentPolicy(policy_id="mission02.environment"),
        authorized_at=_NOW + timedelta(seconds=2),
    )
    assert isinstance(result, Success)
    return result.value


def _submission(
    *,
    instrument: str = "EURUSD",
    quantity: str = "1",
) -> ExecutionSubmission:
    intent = OrderIntent(
        intent_id=OrderIntentId(UUID("24000000-0000-0000-0000-000000000002")),
        idempotency_key=ExecutionIdempotencyKey(
            UUID("24000000-0000-0000-0000-000000000003")
        ),
        instrument=ExecutionInstrument(instrument),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal(quantity)),
        created_at=_NOW,
        metadata=_METADATA,
    )
    authorization = PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("24000000-0000-0000-0000-000000000004")
        ),
        policy_id=PreTradePolicyId("risk.pretrade.market-test"),
        intent_id=intent.intent_id,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(seconds=30),
        reason="market test pre-trade approved",
    )
    authorized = AuthorizedOrderIntent(
        intent=intent,
        authorization=authorization,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=_NOW + timedelta(seconds=1),
            reason="market test execution switch enabled",
        ),
        authorized_at=_NOW + timedelta(seconds=2),
    )
    return ExecutionSubmission(
        request_id=ExecutionRequestId(
            UUID("24000000-0000-0000-0000-000000000005")
        ),
        receipt_id=ExecutionReceiptId(
            UUID("24000000-0000-0000-0000-000000000006")
        ),
        authorized_intent=authorized,
        submitted_at=_NOW + timedelta(seconds=3),
    )


def _policy(
    *,
    accounts: tuple[MarketTestAccountIdentity, ...] = (_ACCOUNT,),
    instruments: tuple[ExecutionInstrument, ...] = (ExecutionInstrument("EURUSD"),),
    max_quantity: str = "2",
) -> MarketTestSafetyPolicy:
    return MarketTestSafetyPolicy(
        policy_id="mission02.execution-safety",
        allowed_accounts=accounts,
        allowed_instruments=instruments,
        max_order_quantity=Decimal(max_quantity),
    )


class _Gateway:
    def __init__(self) -> None:
        self.submit_calls: list[MarketTestAccountIdentity] = []

    def submit(
        self,
        *,
        account: MarketTestAccountIdentity,
        submission: ExecutionSubmission,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        self.submit_calls.append(account)
        return Success(
            TestExecutionGatewayReceipt(
                provider_execution_ref="safe-demo-0001",
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
        del account
        return Success(
            TestExecutionGatewayReceipt(
                provider_execution_ref=provider_execution_ref,
                status=ExecutionStatus.CANCELLED,
                recorded_at=cancelled_at,
            )
        )


def _boundary(
    gateway: _Gateway,
    *,
    policy: MarketTestSafetyPolicy | None = None,
) -> SafetyGuardedTestExecutionBoundary:
    return SafetyGuardedTestExecutionBoundary(
        adapter=AuthorizedTestExecutionAdapter(
            environment_authorization=_environment_authorization(),
            gateway=gateway,
        ),
        policy=_policy() if policy is None else policy,
    )


def test_allowlisted_demo_order_reaches_gateway_once() -> None:
    gateway = _Gateway()
    boundary = _boundary(gateway)

    result = boundary.submit(_submission())

    assert isinstance(result, Success)
    assert result.value.status is ExecutionStatus.ACCEPTED
    assert len(gateway.submit_calls) == 1
    assert len(boundary.permits) == 1
    assert boundary.permits[0].account == _ACCOUNT


def test_non_allowlisted_instrument_is_blocked_before_gateway() -> None:
    gateway = _Gateway()
    boundary = _boundary(gateway)

    result = boundary.submit(_submission(instrument="GBPUSD"))

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestSafetyBlockedError)
    assert gateway.submit_calls == []
    assert boundary.permits == ()


def test_quantity_above_limit_is_blocked_before_gateway() -> None:
    gateway = _Gateway()
    boundary = _boundary(gateway)

    result = boundary.submit(_submission(quantity="3"))

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestSafetyBlockedError)
    assert gateway.submit_calls == []


def test_non_allowlisted_account_is_blocked_before_gateway() -> None:
    other = MarketTestAccountIdentity(
        provider_key="reference-provider",
        account_ref="demo-account-02",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    gateway = _Gateway()
    boundary = _boundary(gateway, policy=_policy(accounts=(other,)))

    result = boundary.submit(_submission())

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestSafetyBlockedError)
    assert gateway.submit_calls == []


def test_policy_cannot_allow_production_account() -> None:
    production = MarketTestAccountIdentity(
        provider_key="reference-provider",
        account_ref="live-account-01",
        environment=MarketRuntimeEnvironment.PRODUCTION,
    )

    with pytest.raises(MarketTestSafetyValidationError):
        _policy(accounts=(production,))


def test_exact_replay_preserves_single_gateway_call_and_single_permit() -> None:
    gateway = _Gateway()
    boundary = _boundary(gateway)
    submission = _submission()

    first = boundary.submit(submission)
    replay = boundary.submit(submission)

    assert isinstance(first, Success)
    assert isinstance(replay, Success)
    assert replay.value == first.value
    assert len(gateway.submit_calls) == 1
    assert len(boundary.permits) == 1
