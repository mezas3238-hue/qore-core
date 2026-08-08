from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.infrastructure.cibo_supervised_runtime import (
    CiboSupervisedRuntimeValidationError,
    CiboSupervisionAuthorization,
    CiboSupervisionBlockedError,
    CiboSupervisionDecision,
    CiboSupervisorId,
    SupervisedCiboDecisionBoundary,
)
from qore.infrastructure.market_data import Instrument, MarketDataSnapshotId, QuoteSnapshot
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentAuthorization,
    MarketTestEnvironmentPolicy,
    authorize_market_test_account,
)
from qore.infrastructure.order_intent import OrderIntent
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.real_market_decision_runtime import RealMarketDecisionContext
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 11, 20, tzinfo=UTC)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("26000000-0000-0000-0000-000000000001"))
)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("26000000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("26000000-0000-0000-0000-000000000003")),
    port_name=PortName("market-data.real-test"),
)


def _environment_authorization() -> MarketTestEnvironmentAuthorization:
    result = authorize_market_test_account(
        MarketTestAccountIdentity(
            provider_key="reference-provider",
            account_ref="demo-account-01",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        policy=MarketTestEnvironmentPolicy(policy_id="mission02.environment"),
        authorized_at=_NOW,
    )
    assert isinstance(result, Success)
    return result.value


def _supervision(
    decision: CiboSupervisionDecision = CiboSupervisionDecision.APPROVED,
) -> CiboSupervisionAuthorization:
    return CiboSupervisionAuthorization(
        supervisor_id=CiboSupervisorId("ceo.supervisor"),
        environment_authorization=_environment_authorization(),
        decision=decision,
        authorized_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(minutes=5),
        reason="explicit supervised market test window",
    )


def _context(*, decided_at: datetime | None = None) -> RealMarketDecisionContext:
    return RealMarketDecisionContext(
        quote=QuoteSnapshot(
            snapshot_id=MarketDataSnapshotId(
                UUID("26000000-0000-0000-0000-000000000004")
            ),
            instrument=Instrument("EURUSD"),
            source=_SOURCE,
            observed_at=_NOW,
            bid=1.1,
            ask=1.1002,
        ),
        decided_at=_NOW + timedelta(seconds=2) if decided_at is None else decided_at,
    )


class _Delegate:
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
        return Success(None)


def test_approved_supervision_allows_cibo_decision_call() -> None:
    delegate = _Delegate()
    boundary = SupervisedCiboDecisionBoundary(
        delegate=delegate,
        supervision=_supervision(),
    )

    result = boundary.decide(_context(), metadata=_METADATA)

    assert isinstance(result, Success)
    assert result.value is None
    assert delegate.calls == 1


def test_blocked_supervision_fails_before_delegate() -> None:
    delegate = _Delegate()
    boundary = SupervisedCiboDecisionBoundary(
        delegate=delegate,
        supervision=_supervision(CiboSupervisionDecision.BLOCKED),
    )

    result = boundary.decide(_context(), metadata=_METADATA)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboSupervisionBlockedError)
    assert delegate.calls == 0


def test_expired_supervision_fails_before_delegate() -> None:
    delegate = _Delegate()
    boundary = SupervisedCiboDecisionBoundary(
        delegate=delegate,
        supervision=_supervision(),
    )

    result = boundary.decide(
        _context(decided_at=_NOW + timedelta(minutes=6)),
        metadata=_METADATA,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboSupervisionBlockedError)
    assert delegate.calls == 0


def test_supervision_cannot_predate_environment_authorization() -> None:
    with pytest.raises(CiboSupervisedRuntimeValidationError):
        CiboSupervisionAuthorization(
            supervisor_id=CiboSupervisorId("ceo.supervisor"),
            environment_authorization=_environment_authorization(),
            decision=CiboSupervisionDecision.APPROVED,
            authorized_at=_NOW - timedelta(seconds=1),
            expires_at=_NOW + timedelta(minutes=5),
            reason="invalid chronology",
        )


def test_cibo_boundary_exposes_only_decision_surface() -> None:
    boundary = SupervisedCiboDecisionBoundary(
        delegate=_Delegate(),
        supervision=_supervision(),
    )

    assert callable(boundary.decide)
    assert not hasattr(boundary, "submit")
    assert not hasattr(boundary, "cancel")
