from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.cibo_operational_supervision_evidence import (
    CiboOperationalSupervisionOutcome,
    CiboOperationalSupervisionReason,
    ObservedSupervisedCiboDecisionBoundary,
)
from qore.infrastructure.cibo_supervised_runtime import (
    CiboSupervisionAuthorization,
    CiboSupervisionBlockedError,
    CiboSupervisionDecision,
    CiboSupervisorId,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    QuoteSnapshot,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
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
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.real_market_decision_runtime import (
    RealMarketDecisionBoundary,
    RealMarketDecisionContext,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="oanda-v20",
    account_ref="practice-001",
    environment=MarketRuntimeEnvironment.DEMO,
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("34000000-0000-0000-0000-000000000001"))
)


def _environment_authorization():
    result = authorize_market_test_account(
        _ACCOUNT,
        policy=MarketTestEnvironmentPolicy(policy_id="mission03.cibo.demo"),
        authorized_at=_NOW,
    )
    assert isinstance(result, Success)
    return result.value


def _supervision(
    *,
    decision: CiboSupervisionDecision = CiboSupervisionDecision.APPROVED,
    expires_at: datetime | None = None,
) -> CiboSupervisionAuthorization:
    return CiboSupervisionAuthorization(
        supervisor_id=CiboSupervisorId("ceo.primary"),
        environment_authorization=_environment_authorization(),
        decision=decision,
        authorized_at=_NOW + timedelta(seconds=1),
        expires_at=expires_at or _NOW + timedelta(minutes=5),
        reason="supervised demo decision window",
    )


def _context(*, decided_at: datetime | None = None) -> RealMarketDecisionContext:
    quote = QuoteSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID("34000000-0000-0000-0000-000000000002")
        ),
        instrument=Instrument("EUR_USD"),
        source=ExternalSourceDescriptor(
            adapter_id=AdapterId(UUID("34000000-0000-0000-0000-000000000003")),
            source_id=SourceId(UUID("34000000-0000-0000-0000-000000000004")),
            port_name=PortName("market-data.oanda-practice"),
        ),
        observed_at=_NOW + timedelta(seconds=1),
        bid=1.1,
        ask=1.1002,
    )
    return RealMarketDecisionContext(
        quote=quote,
        decided_at=decided_at or _NOW + timedelta(seconds=2),
    )


def _intent() -> OrderIntent:
    return OrderIntent(
        intent_id=OrderIntentId(UUID("34000000-0000-0000-0000-000000000005")),
        idempotency_key=ExecutionIdempotencyKey(
            UUID("34000000-0000-0000-0000-000000000006")
        ),
        instrument=ExecutionInstrument("EUR_USD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("10")),
        created_at=_NOW + timedelta(seconds=2),
        metadata=_METADATA,
    )


class _IntentDelegate:
    def __init__(self) -> None:
        self.calls = 0

    def decide(
        self,
        context: RealMarketDecisionContext,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OrderIntent | None, ExternalPortError]:
        self.calls += 1
        return Success(_intent())


class _NoActionDelegate:
    def decide(
        self,
        context: RealMarketDecisionContext,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OrderIntent | None, ExternalPortError]:
        return Success(None)


class _FailingDelegate:
    def decide(
        self,
        context: RealMarketDecisionContext,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OrderIntent | None, ExternalPortError]:
        return Failure(ExternalPortError("token=delegate-private-value"))


def _accept_decision_boundary(boundary: RealMarketDecisionBoundary) -> None:
    assert callable(boundary.decide)


def test_observed_boundary_structurally_preserves_decision_protocol() -> None:
    observed = ObservedSupervisedCiboDecisionBoundary(
        delegate=_NoActionDelegate(),
        supervision=_supervision(),
    )

    _accept_decision_boundary(observed)


def test_delegated_decision_records_sanitized_supervision_evidence() -> None:
    delegate = _IntentDelegate()
    observed = ObservedSupervisedCiboDecisionBoundary(
        delegate=delegate,
        supervision=_supervision(),
    )

    result = observed.decide(_context(), metadata=_METADATA)

    assert isinstance(result, Success)
    assert isinstance(result.value, OrderIntent)
    assert delegate.calls == 1
    assert len(observed.records) == 1
    record = observed.records[0]
    assert record.outcome is CiboOperationalSupervisionOutcome.DELEGATED
    assert record.reason is CiboOperationalSupervisionReason.DECISION_DELEGATED
    assert record.intent_id == result.value.intent_id
    assert record.supervisor_id == "ceo.primary"
    assert record.provider_key == "oanda-v20"
    assert record.environment == "demo"
    assert record.instrument == "EUR_USD"
    assert record.correlation_id == str(_METADATA.correlation_id.value)
    assert record.market_snapshot_id == _context().quote.snapshot_id
    assert "practice-001" not in repr(record.public_payload())
    assert "sha256:" in record.account_fingerprint
    assert "token" not in repr(record.public_payload()).lower()


def test_no_action_is_recorded_without_intent() -> None:
    observed = ObservedSupervisedCiboDecisionBoundary(
        delegate=_NoActionDelegate(),
        supervision=_supervision(),
    )

    result = observed.decide(_context(), metadata=_METADATA)

    assert isinstance(result, Success)
    assert result.value is None
    record = observed.records[0]
    assert record.outcome is CiboOperationalSupervisionOutcome.NO_ACTION
    assert record.reason is CiboOperationalSupervisionReason.DECISION_NO_ACTION
    assert record.intent_id is None


def test_blocked_supervision_records_block_and_does_not_call_delegate() -> None:
    delegate = _IntentDelegate()
    observed = ObservedSupervisedCiboDecisionBoundary(
        delegate=delegate,
        supervision=_supervision(decision=CiboSupervisionDecision.BLOCKED),
    )

    result = observed.decide(_context(), metadata=_METADATA)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboSupervisionBlockedError)
    assert delegate.calls == 0
    record = observed.records[0]
    assert record.outcome is CiboOperationalSupervisionOutcome.BLOCKED
    assert record.reason is CiboOperationalSupervisionReason.SUPERVISION_BLOCKED
    assert record.intent_id is None


def test_expired_supervision_records_block_and_does_not_call_delegate() -> None:
    delegate = _IntentDelegate()
    expires_at = _NOW + timedelta(seconds=3)
    observed = ObservedSupervisedCiboDecisionBoundary(
        delegate=delegate,
        supervision=_supervision(expires_at=expires_at),
    )

    result = observed.decide(
        _context(decided_at=_NOW + timedelta(seconds=4)),
        metadata=_METADATA,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboSupervisionBlockedError)
    assert delegate.calls == 0
    record = observed.records[0]
    assert record.outcome is CiboOperationalSupervisionOutcome.BLOCKED
    assert record.supervision_expires_at == expires_at


def test_delegate_failure_records_closed_reason_without_error_text() -> None:
    observed = ObservedSupervisedCiboDecisionBoundary(
        delegate=_FailingDelegate(),
        supervision=_supervision(),
    )

    result = observed.decide(_context(), metadata=_METADATA)

    assert isinstance(result, Failure)
    assert "delegate-private-value" in str(result.error)
    assert len(observed.records) == 1
    record = observed.records[0]
    assert record.outcome is CiboOperationalSupervisionOutcome.FAILED
    assert record.reason is CiboOperationalSupervisionReason.DELEGATE_FAILED
    public = repr(record.public_payload()).lower()
    assert "delegate-private-value" not in public
    assert "token=" not in public


def test_attempt_reference_is_deterministic_for_same_context_and_metadata() -> None:
    first = ObservedSupervisedCiboDecisionBoundary(
        delegate=_NoActionDelegate(),
        supervision=_supervision(),
    )
    second = ObservedSupervisedCiboDecisionBoundary(
        delegate=_NoActionDelegate(),
        supervision=_supervision(),
    )
    context = _context()

    first_result = first.decide(context, metadata=_METADATA)
    second_result = second.decide(context, metadata=_METADATA)

    assert isinstance(first_result, Success)
    assert isinstance(second_result, Success)
    assert first.records[0].attempt_ref == second.records[0].attempt_ref
    assert first.records[0].logical_values() == second.records[0].logical_values()


def test_supervision_record_exposes_no_provider_gateway_or_credentials() -> None:
    observed = ObservedSupervisedCiboDecisionBoundary(
        delegate=_NoActionDelegate(),
        supervision=_supervision(),
    )
    result = observed.decide(_context(), metadata=_METADATA)
    assert isinstance(result, Success)

    record = observed.records[0]
    assert not hasattr(record, "token")
    assert not hasattr(record, "credential")
    assert not hasattr(record, "gateway")
    assert not hasattr(record, "provider_client")
