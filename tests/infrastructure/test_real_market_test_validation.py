from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CorrelationId
from qore.infrastructure.cibo_supervised_runtime import (
    CiboSupervisionAuthorization,
    CiboSupervisionDecision,
    CiboSupervisorId,
    SupervisedCiboDecisionBoundary,
)
from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
    ExecutionSubmission,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionReconciliationStatus,
    observe_execution_receipt,
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
    MarketTestEnvironmentBlockedError,
    MarketTestEnvironmentPolicy,
    authorize_market_test_account,
)
from qore.infrastructure.market_test_observability import (
    MarketTestObservation,
    MarketTestObservationCategory,
    MarketTestObservationState,
    build_market_test_observability_evidence,
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
    RealMarketDecisionStatus,
    compose_real_market_decision_runtime,
)
from qore.infrastructure.real_market_test_validation import (
    RealMarketTestCheck,
    RealMarketTestCheckStatus,
    RealMarketTestEvidenceRecord,
    RealMarketTestValidationInvariantError,
    validate_real_market_test_evidence,
)
from qore.infrastructure.test_execution_adapter import (
    AuthorizedTestExecutionAdapter,
    TestExecutionGatewayReceipt,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 11, 50, tzinfo=UTC)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("27000000-0000-0000-0000-000000000001"))
)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("27000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("27000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.real-test"),
)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="reference-provider",
    account_ref="demo-account-01",
    environment=MarketRuntimeEnvironment.DEMO,
)
_INTENT_ID = OrderIntentId(UUID("27000000-0000-0000-0000-000000000004"))
_REQUEST_ID = ExecutionRequestId(UUID("27000000-0000-0000-0000-000000000005"))
_RECEIPT_ID = ExecutionReceiptId(UUID("27000000-0000-0000-0000-000000000006"))


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-real-market-test-e2e"))
    assert isinstance(result, Success)
    return result.value


def _environment_authorization() -> MarketTestEnvironmentAuthorization:
    result = authorize_market_test_account(
        _ACCOUNT,
        policy=MarketTestEnvironmentPolicy(policy_id="mission02.environment"),
        authorized_at=_NOW,
    )
    assert isinstance(result, Success)
    return result.value


def _intent() -> OrderIntent:
    return OrderIntent(
        intent_id=_INTENT_ID,
        idempotency_key=ExecutionIdempotencyKey(
            UUID("27000000-0000-0000-0000-000000000007")
        ),
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_NOW + timedelta(seconds=2),
        metadata=_METADATA,
    )


def _authorization() -> PreTradeAuthorization:
    return PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("27000000-0000-0000-0000-000000000008")
        ),
        policy_id=PreTradePolicyId("risk.pretrade.market-test-e2e"),
        intent_id=_INTENT_ID,
        decision=PreTradeDecision.APPROVED,
        evaluated_at=_NOW + timedelta(seconds=3),
        expires_at=_NOW + timedelta(seconds=30),
        reason="market test end-to-end authorization",
    )


def _switch() -> ExecutionSafetySwitchSnapshot:
    return ExecutionSafetySwitchSnapshot(
        state=ExecutionSwitchState.ENABLED,
        observed_at=_NOW + timedelta(seconds=3),
        reason="market test end-to-end execution enabled",
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
                observed_at=_NOW + timedelta(seconds=1),
                bid=1.1,
                ask=1.1002,
            )
        )


class _CiboDecision:
    def __init__(self) -> None:
        self.calls = 0

    def decide(
        self,
        context: RealMarketDecisionContext,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OrderIntent | None, ExternalPortError]:
        assert context.quote.instrument.symbol == "EURUSD"
        assert metadata == _METADATA
        self.calls += 1
        return Success(_intent())


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
                provider_execution_ref="mission02-demo-execution-001",
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


def _observability() -> tuple[MarketTestObservation, ...]:
    return tuple(
        MarketTestObservation(
            category=category,
            state=MarketTestObservationState.HEALTHY,
            observed_at=_NOW + timedelta(seconds=9),
            message=f"{category.value} end-to-end evidence recorded",
            reference=f"mission02:e2e:{category.value}",
        )
        for category in MarketTestObservationCategory
    )


def _records(
    status: RealMarketTestCheckStatus = RealMarketTestCheckStatus.PASS,
) -> tuple[RealMarketTestEvidenceRecord, ...]:
    return tuple(
        RealMarketTestEvidenceRecord(
            check=check,
            status=status,
            evaluated_at=_NOW + timedelta(seconds=10),
            evidence=f"{check.value} verified by deterministic end-to-end harness",
        )
        for check in RealMarketTestCheck
    )


def test_real_market_test_e2e_nominal_flow_is_supervised_safe_and_reconciled() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()
    environment = _environment_authorization()
    gateway = _Gateway()
    cibo = _CiboDecision()
    supervised = SupervisedCiboDecisionBoundary(
        delegate=cibo,
        supervision=CiboSupervisionAuthorization(
            supervisor_id=CiboSupervisorId("ceo.supervisor"),
            environment_authorization=environment,
            decision=CiboSupervisionDecision.APPROVED,
            authorized_at=_NOW + timedelta(seconds=1),
            expires_at=_NOW + timedelta(minutes=5),
            reason="explicit end-to-end supervision window",
        ),
    )
    execution = SafetyGuardedTestExecutionBoundary(
        adapter=AuthorizedTestExecutionAdapter(
            environment_authorization=environment,
            gateway=gateway,
        ),
        policy=MarketTestSafetyPolicy(
            policy_id="mission02.e2e-safety",
            allowed_accounts=(_ACCOUNT,),
            allowed_instruments=(ExecutionInstrument("EURUSD"),),
            max_order_quantity=Decimal("2"),
        ),
    )
    composed = compose_real_market_decision_runtime(
        core=core,
        market_data=_MarketData(),
        decision=supervised,
        execution=execution,
    )
    assert isinstance(composed, Success)

    outcome = composed.value.decide_and_submit_quote(
        QuoteRequest(Instrument("EURUSD")),
        snapshot_id=MarketDataSnapshotId(
            UUID("27000000-0000-0000-0000-000000000009")
        ),
        metadata=_METADATA,
        decided_at=_NOW + timedelta(seconds=2),
        authorization=_authorization(),
        switch=_switch(),
        request_id=_REQUEST_ID,
        receipt_id=_RECEIPT_ID,
        authorized_at=_NOW + timedelta(seconds=4),
        submitted_at=_NOW + timedelta(seconds=5),
    )
    assert isinstance(outcome, Success)
    assert outcome.value.status is RealMarketDecisionStatus.SUBMITTED
    assert outcome.value.receipt is not None
    assert cibo.calls == 1
    assert gateway.submit_calls == 1
    assert len(execution.permits) == 1

    replay = composed.value.decide_and_submit_quote(
        QuoteRequest(Instrument("EURUSD")),
        snapshot_id=MarketDataSnapshotId(
            UUID("27000000-0000-0000-0000-000000000009")
        ),
        metadata=_METADATA,
        decided_at=_NOW + timedelta(seconds=2),
        authorization=_authorization(),
        switch=_switch(),
        request_id=_REQUEST_ID,
        receipt_id=_RECEIPT_ID,
        authorized_at=_NOW + timedelta(seconds=4),
        submitted_at=_NOW + timedelta(seconds=5),
    )
    assert isinstance(replay, Success)
    assert gateway.submit_calls == 1

    observed = observe_execution_receipt(
        outcome.value.receipt,
        observed_at=_NOW + timedelta(seconds=7),
    )
    assert isinstance(observed, Success)
    reconciliation = composed.value.execution.reconcile(
        outcome.value.receipt,
        observed.value,
        reconciled_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(reconciliation, Success)
    assert reconciliation.value.status is ExecutionReconciliationStatus.MATCHED

    observability = build_market_test_observability_evidence(
        _observability(),
        evaluated_at=_NOW + timedelta(seconds=10),
    )
    assert isinstance(observability, Success)
    assert observability.value.state is MarketTestObservationState.HEALTHY

    validation = validate_real_market_test_evidence(
        _records(),
        validated_at=_NOW + timedelta(seconds=11),
    )
    assert isinstance(validation, Success)
    assert validation.value.passed is True
    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health


def test_production_environment_fails_before_any_execution_gateway_exists() -> None:
    result = authorize_market_test_account(
        MarketTestAccountIdentity(
            provider_key="reference-provider",
            account_ref="production-account-01",
            environment=MarketRuntimeEnvironment.PRODUCTION,
        ),
        policy=MarketTestEnvironmentPolicy(policy_id="mission02.environment"),
        authorized_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestEnvironmentBlockedError)


def test_validation_fails_when_any_required_check_fails() -> None:
    records = list(_records())
    target = next(
        index
        for index, record in enumerate(records)
        if record.check is RealMarketTestCheck.PRODUCTION_DISABLED
    )
    records[target] = RealMarketTestEvidenceRecord(
        check=RealMarketTestCheck.PRODUCTION_DISABLED,
        status=RealMarketTestCheckStatus.FAIL,
        evaluated_at=_NOW + timedelta(seconds=10),
        evidence="production boundary validation failed",
    )

    result = validate_real_market_test_evidence(
        tuple(records),
        validated_at=_NOW + timedelta(seconds=11),
    )

    assert isinstance(result, Success)
    assert result.value.passed is False


def test_validation_rejects_missing_or_duplicate_checks() -> None:
    records = _records()
    missing = validate_real_market_test_evidence(
        records[:-1],
        validated_at=_NOW + timedelta(seconds=11),
    )
    duplicate = validate_real_market_test_evidence(
        records + (records[0],),
        validated_at=_NOW + timedelta(seconds=11),
    )

    assert isinstance(missing, Failure)
    assert isinstance(missing.error, RealMarketTestValidationInvariantError)
    assert isinstance(duplicate, Failure)
    assert isinstance(duplicate.error, RealMarketTestValidationInvariantError)


def test_validation_evidence_rejects_secret_like_text() -> None:
    with pytest.raises(RealMarketTestValidationInvariantError):
        RealMarketTestEvidenceRecord(
            check=RealMarketTestCheck.SECRET_SAFE_OBSERVABILITY,
            status=RealMarketTestCheckStatus.PASS,
            evaluated_at=_NOW,
            evidence="token=hidden",
        )
