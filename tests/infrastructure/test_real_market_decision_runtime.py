from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CorrelationId
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    QuoteRequest,
    QuoteSnapshot,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentAuthorization,
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
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
)
from qore.infrastructure.real_market_decision_runtime import (
    RealMarketDecisionContext,
    RealMarketDecisionOutcome,
    RealMarketDecisionRuntimeValidationError,
    RealMarketDecisionStatus,
    compose_real_market_decision_runtime,
)
from qore.infrastructure.test_execution_adapter import (
    AuthorizedTestExecutionAdapter,
    TestExecutionGatewayReceipt,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 11, 0, tzinfo=UTC)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("25000000-0000-0000-0000-000000000001"))
)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("25000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("25000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.real-test"),
)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="reference-provider",
    account_ref="demo-account-01",
    environment=MarketRuntimeEnvironment.DEMO,
)
_INTENT_ID = OrderIntentId(UUID("25000000-0000-0000-0000-000000000004"))
_REQUEST_ID = ExecutionRequestId(UUID("25000000-0000-0000-0000-000000000005"))
_RECEIPT_ID = ExecutionReceiptId(UUID("25000000-0000-0000-0000-000000000006"))


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-real-market-decision"))
    assert isinstance(result, Success)
    return result.value


def _environment_authorization() -> MarketTestEnvironmentAuthorization:
    result = authorize_market_test_account(
        _ACCOUNT,
        policy=MarketTestEnvironmentPolicy(policy_id="mission02.environment"),
        authorized_at=_NOW - timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    return result.value


def _intent(instrument: str = "EURUSD") -> OrderIntent:
    return OrderIntent(
        intent_id=_INTENT_ID,
        idempotency_key=ExecutionIdempotencyKey(
            UUID("25000000-0000-0000-0000-000000000007")
        ),
        instrument=ExecutionInstrument(instrument),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_NOW + timedelta(seconds=1),
        metadata=_METADATA,
    )


def _authorization() -> PreTradeAuthorization:
    return PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("25000000-0000-0000-0000-000000000008")
        ),
        policy_id=PreTradePolicyId("risk.pretrade.real-market-test"),
        intent_id=_INTENT_ID,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=2),
        expires_at=_NOW + timedelta(seconds=20),
        reason="real market test pre-trade approved",
    )


def _switch() -> ExecutionSafetySwitchSnapshot:
    return ExecutionSafetySwitchSnapshot(
        state=ExecutionSwitchState.ENABLED,
        observed_at=_NOW + timedelta(seconds=2),
        reason="real market test execution enabled",
    )


class _MarketData:
    def read_quote(
        self,
        request: QuoteRequest,
        *,
        snapshot_id: MarketDataSnapshotId,
        metadata: ExternalRequestMetadata,
    ) -> Result[QuoteSnapshot, ExternalPortError]:
        assert metadata == _METADATA
        return Success(
            QuoteSnapshot(
                snapshot_id=snapshot_id,
                instrument=request.instrument,
                source=_SOURCE,
                observed_at=_NOW,
                bid=1.1,
                ask=1.1002,
            )
        )


class _Decision:
    def __init__(self, intent: OrderIntent | None) -> None:
        self.intent = intent
        self.calls = 0

    def decide(
        self,
        context: RealMarketDecisionContext,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OrderIntent | None, ExternalPortError]:
        assert context.quote.instrument == Instrument("EURUSD")
        assert metadata == _METADATA
        self.calls += 1
        return Success(self.intent)


class _Gateway:
    def __init__(self) -> None:
        self.submit_calls = 0

    def submit(
        self,
        *,
        account: MarketTestAccountIdentity,
        submission: ExecutionSubmission,
    ) -> Result[TestExecutionGatewayReceipt, ExecutionBoundaryError]:
        assert account == _ACCOUNT
        self.submit_calls += 1
        return Success(
            TestExecutionGatewayReceipt(
                provider_execution_ref="decision-demo-0001",
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
        assert account == _ACCOUNT
        return Success(
            TestExecutionGatewayReceipt(
                provider_execution_ref=provider_execution_ref,
                status=ExecutionStatus.CANCELLED,
                recorded_at=cancelled_at,
            )
        )


def _execution(gateway: _Gateway) -> SafetyGuardedTestExecutionBoundary:
    return SafetyGuardedTestExecutionBoundary(
        adapter=AuthorizedTestExecutionAdapter(
            environment_authorization=_environment_authorization(),
            gateway=gateway,
        ),
        policy=MarketTestSafetyPolicy(
            policy_id="mission02.execution-safety",
            allowed_accounts=(_ACCOUNT,),
            allowed_instruments=(ExecutionInstrument("EURUSD"),),
            max_order_quantity=Decimal("2"),
        ),
    )


def _run(
    decision: _Decision,
    gateway: _Gateway,
) -> Result[RealMarketDecisionOutcome, ExternalPortError]:
    composed = compose_real_market_decision_runtime(
        core=_core(),
        market_data=_MarketData(),
        decision=decision,
        execution=_execution(gateway),
    )
    assert isinstance(composed, Success)
    return composed.value.decide_and_submit_quote(
        QuoteRequest(Instrument("EURUSD")),
        snapshot_id=MarketDataSnapshotId(
            UUID("25000000-0000-0000-0000-000000000009")
        ),
        metadata=_METADATA,
        decided_at=_NOW + timedelta(seconds=1),
        authorization=_authorization(),
        switch=_switch(),
        request_id=_REQUEST_ID,
        receipt_id=_RECEIPT_ID,
        authorized_at=_NOW + timedelta(seconds=3),
        submitted_at=_NOW + timedelta(seconds=4),
    )


def test_real_market_decision_flows_to_test_execution() -> None:
    gateway = _Gateway()
    result = _run(_Decision(_intent()), gateway)

    assert isinstance(result, Success)
    assert result.value.status is RealMarketDecisionStatus.SUBMITTED
    assert result.value.receipt is not None
    assert result.value.receipt.status is ExecutionStatus.ACCEPTED
    assert gateway.submit_calls == 1


def test_no_action_decision_creates_zero_execution_calls() -> None:
    gateway = _Gateway()
    result = _run(_Decision(None), gateway)

    assert isinstance(result, Success)
    assert result.value.status is RealMarketDecisionStatus.NO_ACTION
    assert result.value.intent is None
    assert result.value.receipt is None
    assert gateway.submit_calls == 0


def test_mismatched_decision_instrument_is_blocked_before_execution() -> None:
    gateway = _Gateway()
    result = _run(_Decision(_intent("GBPUSD")), gateway)

    assert isinstance(result, Failure)
    assert isinstance(result.error, RealMarketDecisionRuntimeValidationError)
    assert gateway.submit_calls == 0


def test_real_market_decision_composition_preserves_core_state() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    result = compose_real_market_decision_runtime(
        core=core,
        market_data=_MarketData(),
        decision=_Decision(None),
        execution=_execution(_Gateway()),
    )

    assert isinstance(result, Success)
    assert result.value.core is core
    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health
