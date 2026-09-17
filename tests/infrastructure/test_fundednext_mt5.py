from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import (
    RiskAuthorization,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.execution_boundary import (
    ExecutionCancellation,
    ExecutionSubmission,
)
from qore.infrastructure.fundednext_execution_bridge import (
    build_fundednext_execution_submission,
)
from qore.infrastructure.fundednext_mt5 import (
    FundedNextMt5ExecutionGateway,
    FundedNextMt5OrderPlan,
    FundedNextMt5TransportReceipt,
    Mt5AccountState,
    Mt5ExecutionBlockedError,
    Mt5ExecutionOutcomeUnknownError,
    Mt5ProviderOutcome,
    Mt5SymbolSpecification,
)
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    InMemoryFundedNextMt5MutationLedger,
)
from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantRuleVerification,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
    MarketTestEnvironmentAuthorization,
)
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
)
from qore.infrastructure.test_execution_adapter import AuthorizedTestExecutionAdapter
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 9, 13, 18, 0, tzinfo=UTC)


class FakeTransport:
    def __init__(self) -> None:
        self.is_connected = True
        self.missing_symbol = False
        self.spec_observed_at = _NOW
        self.submit_outcome = Mt5ProviderOutcome.ACCEPTED
        self.cancel_outcome = Mt5ProviderOutcome.CANCELLED
        self.discovery: dict[str, FundedNextMt5TransportReceipt] = {}
        self.submit_calls = 0
        self.cancel_calls = 0
        self.discover_calls = 0
        self.last_plan: FundedNextMt5OrderPlan | None = None

    def connected(self) -> bool:
        return self.is_connected

    def account_state(self, account_ref: str) -> Mt5AccountState | None:
        assert account_ref == "fn-si-opaque-001"
        return Mt5AccountState(
            balance=Decimal("2000"),
            equity=Decimal("2000"),
            margin=Decimal("0"),
            free_margin=Decimal("2000"),
            observed_at=_NOW,
        )

    def symbol_info(self, provider_symbol: str) -> Mt5SymbolSpecification | None:
        if self.missing_symbol:
            return None
        return Mt5SymbolSpecification(
            provider_symbol=provider_symbol,
            bid=Decimal("99.99"),
            ask=Decimal("100.01"),
            spread_points=Decimal("2"),
            digits=2,
            point=Decimal("0.01"),
            contract_size=Decimal("100000"),
            tick_size=Decimal("0.01"),
            tick_value=Decimal("1"),
            minimum_volume=Decimal("0.1"),
            maximum_volume=Decimal("100"),
            volume_step=Decimal("0.1"),
            minimum_stop_distance_points=Decimal("5"),
            freeze_level_points=Decimal("0"),
            margin_per_volume=Decimal("50"),
            trade_enabled=True,
            session_open=True,
            observed_at=self.spec_observed_at,
        )

    def submit_order(
        self,
        plan: FundedNextMt5OrderPlan,
    ) -> FundedNextMt5TransportReceipt:
        self.submit_calls += 1
        self.last_plan = plan
        provider_ref = (
            "ticket-1" if self.submit_outcome is Mt5ProviderOutcome.ACCEPTED else None
        )
        return FundedNextMt5TransportReceipt(
            client_order_id=plan.client_order_id,
            outcome=self.submit_outcome,
            recorded_at=_NOW,
            provider_order_ref=provider_ref,
            reason=(
                "provider-timeout"
                if self.submit_outcome is Mt5ProviderOutcome.UNKNOWN
                else None
            ),
        )

    def cancel_order(
        self,
        provider_order_ref: str,
        *,
        client_order_id: str,
        cancelled_at: datetime,
    ) -> FundedNextMt5TransportReceipt:
        self.cancel_calls += 1
        return FundedNextMt5TransportReceipt(
            client_order_id=client_order_id,
            outcome=self.cancel_outcome,
            recorded_at=cancelled_at,
            provider_order_ref=(
                provider_order_ref
                if self.cancel_outcome is Mt5ProviderOutcome.CANCELLED
                else None
            ),
            reason=(
                "cancel-timeout"
                if self.cancel_outcome is Mt5ProviderOutcome.UNKNOWN
                else None
            ),
        )

    def discover_order(
        self,
        client_order_id: str,
    ) -> FundedNextMt5TransportReceipt | None:
        self.discover_calls += 1
        return self.discovery.get(client_order_id)


def _rules() -> StellarInstantRuleVerification:
    return StellarInstantRuleVerification(
        verification_state=RuleVerificationState.CURRENT,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )


def _account() -> MarketTestAccountIdentity:
    return MarketTestAccountIdentity(
        provider_key="fundednext-stellar-instant-mt5",
        account_ref="fn-si-opaque-001",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _environment_authorization() -> MarketTestEnvironmentAuthorization:
    return MarketTestEnvironmentAuthorization(
        account=_account(),
        policy_id="qore.fundednext.stellar-instant.demo",
        authorized_at=_NOW - timedelta(minutes=1),
    )


def _risk_authorization(
    fingerprint: str = "a" * 64,
    *,
    volume: str = "1.0",
    stop: str = "99",
    qore_symbol: str = "GBPUSD",
    provider_symbol: str = "GBPUSD",
) -> RiskAuthorization:
    return RiskAuthorization(
        authorization_id=f"risk-{fingerprint[:24]}",
        account_binding_id="fn-si-opaque-001",
        trader_id=(
            TraderLineage.VT08_INDEX
            if qore_symbol in {"NAS100", "SP500", "US30"}
            else TraderLineage.VT08_FOREX
        ),
        request_id=f"request-{fingerprint[:8]}",
        signal_fingerprint=f"signal-{fingerprint[:8]}",
        qore_symbol=qore_symbol,
        provider_symbol=provider_symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal(stop),
        take_profit=Decimal("102"),
        requested_volume=Decimal(volume),
        authorized_volume=Decimal(volume),
        monetary_stop_loss=Decimal("20"),
        aggregate_pre_order_worst_case=Decimal("0"),
        aggregate_post_order_worst_case=Decimal("20"),
        provider_headroom=Decimal("120"),
        internal_qore_headroom=Decimal("25"),
        margin_reserved=Decimal("50"),
        decision=RiskDecision.ALLOW,
        reason="test",
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=2),
        authorization_fingerprint=fingerprint,
    )


def _submission(
    fingerprint: str = "a" * 64,
    *,
    volume: str = "1.0",
    stop: str = "99",
    qore_symbol: str = "GBPUSD",
    provider_symbol: str = "GBPUSD",
) -> ExecutionSubmission:
    authorization = _risk_authorization(
        fingerprint,
        volume=volume,
        stop=stop,
        qore_symbol=qore_symbol,
        provider_symbol=provider_symbol,
    )
    switch = ExecutionSafetySwitchSnapshot(
        state=ExecutionSwitchState.ENABLED,
        observed_at=_NOW,
        reason="fundednext demo execution switch enabled",
    )
    return build_fundednext_execution_submission(
        authorization,
        switch=switch,
        authorized_at=_NOW,
        submitted_at=_NOW,
    )


def _gateway(
    transport: FakeTransport,
    ledger: InMemoryFundedNextMt5MutationLedger,
    *,
    owner_enabled: bool,
) -> FundedNextMt5ExecutionGateway:
    return FundedNextMt5ExecutionGateway(
        account=_account(),
        transport=transport,
        mutation_ledger=ledger,
        rule_verification=_rules(),
        owner_submission_enabled=owner_enabled,
    )


def test_read_only_shadow_plan_uses_canonical_submission_without_mutation() -> None:
    transport = FakeTransport()
    gateway = _gateway(
        transport,
        InMemoryFundedNextMt5MutationLedger(),
        owner_enabled=False,
    )
    plan = gateway.plan_submission(
        _submission(
            qore_symbol="NAS100",
            provider_symbol="NDX100",
        ),
        now=_NOW,
    )
    assert plan.qore_symbol == "NAS100"
    assert plan.provider_symbol == "NDX100"
    assert plan.client_order_id.startswith("qore-")
    assert transport.submit_calls == 0


def test_missing_stale_symbol_and_invalid_broker_geometry_fail_closed() -> None:
    transport = FakeTransport()
    gateway = _gateway(
        transport,
        InMemoryFundedNextMt5MutationLedger(),
        owner_enabled=False,
    )
    transport.missing_symbol = True
    with pytest.raises(Mt5ExecutionBlockedError, match="symbol-info-missing"):
        gateway.plan_submission(_submission(), now=_NOW)

    transport.missing_symbol = False
    transport.spec_observed_at = _NOW - timedelta(minutes=1)
    with pytest.raises(Mt5ExecutionBlockedError, match="symbol-info-stale"):
        gateway.plan_submission(_submission(), now=_NOW)

    transport.spec_observed_at = _NOW
    with pytest.raises(Mt5ExecutionBlockedError, match="volume-not-on-broker-step"):
        gateway.plan_submission(_submission(volume="0.15"), now=_NOW)
    with pytest.raises(Mt5ExecutionBlockedError, match="stop-inside-broker-minimum-distance"):
        gateway.plan_submission(_submission(stop="99.97"), now=_NOW)


def test_canonical_adapter_cannot_mutate_without_owner_enable() -> None:
    transport = FakeTransport()
    gateway = _gateway(
        transport,
        InMemoryFundedNextMt5MutationLedger(),
        owner_enabled=False,
    )
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(),
        gateway=gateway,
    )
    result = adapter.submit(_submission())
    assert isinstance(result, Failure)
    assert isinstance(result.error, Mt5ExecutionBlockedError)
    assert "owner-order-submission" in str(result.error)
    assert transport.submit_calls == 0


def test_accepted_submission_is_durable_and_restart_does_not_resubmit() -> None:
    transport = FakeTransport()
    ledger = InMemoryFundedNextMt5MutationLedger()
    submission = _submission()
    gateway = _gateway(transport, ledger, owner_enabled=True)
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(),
        gateway=gateway,
    )
    first = adapter.submit(submission)
    assert isinstance(first, Success)
    assert first.value.status.value == "accepted"
    assert transport.submit_calls == 1

    restarted = _gateway(transport, ledger, owner_enabled=True)
    restarted_adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(),
        gateway=restarted,
    )
    replay = restarted_adapter.submit(submission)
    assert isinstance(replay, Success)
    assert replay.value == first.value
    assert transport.submit_calls == 1


def test_unknown_submission_blocks_new_risk_until_discovered_never_resubmits() -> None:
    transport = FakeTransport()
    transport.submit_outcome = Mt5ProviderOutcome.UNKNOWN
    ledger = InMemoryFundedNextMt5MutationLedger()
    first_submission = _submission("a" * 64)
    gateway = _gateway(transport, ledger, owner_enabled=True)
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(),
        gateway=gateway,
    )
    first = adapter.submit(first_submission)
    assert isinstance(first, Failure)
    assert isinstance(first.error, Mt5ExecutionOutcomeUnknownError)
    assert gateway.has_unresolved_mutations is True
    assert transport.submit_calls == 1

    second = adapter.submit(_submission("b" * 64))
    assert isinstance(second, Failure)
    assert isinstance(second.error, Mt5ExecutionOutcomeUnknownError)
    assert transport.submit_calls == 1

    plan = gateway.plan_submission(first_submission, now=_NOW)
    transport.discovery[plan.client_order_id] = FundedNextMt5TransportReceipt(
        client_order_id=plan.client_order_id,
        outcome=Mt5ProviderOutcome.ACCEPTED,
        recorded_at=_NOW + timedelta(seconds=1),
        provider_order_ref="ticket-recovered",
    )
    recovered = gateway.discover_unknown_outcome(first_submission)
    assert isinstance(recovered, Success)
    assert recovered.value.provider_execution_ref == "ticket-recovered"
    assert gateway.has_unresolved_mutations is False
    assert transport.submit_calls == 1
    assert transport.discover_calls == 1


def test_cancel_uses_same_provider_reference_and_adapter_lifecycle() -> None:
    transport = FakeTransport()
    ledger = InMemoryFundedNextMt5MutationLedger()
    submission = _submission()
    gateway = _gateway(transport, ledger, owner_enabled=True)
    adapter = AuthorizedTestExecutionAdapter(
        environment_authorization=_environment_authorization(),
        gateway=gateway,
    )
    accepted = adapter.submit(submission)
    assert isinstance(accepted, Success)
    cancelled = adapter.cancel(
        ExecutionCancellation(
            receipt_id=accepted.value.receipt_id,
            cancelled_at=_NOW + timedelta(seconds=2),
        )
    )
    assert isinstance(cancelled, Success)
    assert cancelled.value.status.value == "cancelled"
    assert transport.cancel_calls == 1
