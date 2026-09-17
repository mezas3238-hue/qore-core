from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import (
    RiskAuthorization,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.infrastructure.fundednext_mt5 import (
    FundedNextMt5OrderPlan,
    FundedNextMt5TransportReceipt,
    Mt5AccountState,
    Mt5ExecutionBlockedError,
    Mt5ProviderOutcome,
    Mt5SymbolSpecification,
)
from qore.infrastructure.fundednext_mt5_mutation_ledger import (
    InMemoryFundedNextMt5MutationLedger,
)
from qore.infrastructure.fundednext_operational import (
    FundedNextAccountBoundMt5Gateway,
    OperationalSafetyController,
    build_account_bound_submission,
    resolve_account_provider_symbol,
)
from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantRuleVerification,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
)

_NOW = datetime(2026, 9, 14, 4, 0, tzinfo=UTC)


class AccountCatalogTransport:
    def __init__(
        self,
        symbols: tuple[str, ...] = ("AUDJPY.a", "GBPUSD.a", "GBPJPY.a"),
    ) -> None:
        self.symbols = symbols
        self.submissions = 0

    def connected(self) -> bool:
        return True

    def available_symbols(self) -> tuple[str, ...]:
        return self.symbols

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
        if provider_symbol not in self.symbols:
            return None
        return Mt5SymbolSpecification(
            provider_symbol=provider_symbol,
            bid=Decimal("1.2499"),
            ask=Decimal("1.2501"),
            spread_points=Decimal("2"),
            digits=4,
            point=Decimal("0.0001"),
            contract_size=Decimal("100000"),
            tick_size=Decimal("0.0001"),
            tick_value=Decimal("10"),
            minimum_volume=Decimal("0.01"),
            maximum_volume=Decimal("100"),
            volume_step=Decimal("0.01"),
            minimum_stop_distance_points=Decimal("5"),
            freeze_level_points=Decimal("0"),
            margin_per_volume=Decimal("50"),
            trade_enabled=True,
            session_open=True,
            observed_at=_NOW,
        )

    def submit_order(
        self,
        plan: FundedNextMt5OrderPlan,
    ) -> FundedNextMt5TransportReceipt:
        self.submissions += 1
        return FundedNextMt5TransportReceipt(
            client_order_id=plan.client_order_id,
            outcome=Mt5ProviderOutcome.ACCEPTED,
            provider_order_ref="ticket-1",
            recorded_at=_NOW,
        )

    def cancel_order(
        self,
        provider_order_ref: str,
        *,
        client_order_id: str,
        cancelled_at: datetime,
    ) -> FundedNextMt5TransportReceipt:
        return FundedNextMt5TransportReceipt(
            client_order_id=client_order_id,
            outcome=Mt5ProviderOutcome.CANCELLED,
            provider_order_ref=provider_order_ref,
            recorded_at=cancelled_at,
        )

    def discover_order(
        self,
        client_order_id: str,
    ) -> FundedNextMt5TransportReceipt | None:
        return None


def _authorization(provider_symbol: str = "GBPUSD.a") -> RiskAuthorization:
    return RiskAuthorization(
        authorization_id="risk-account-bound-test",
        account_binding_id="fn-si-opaque-001",
        trader_id=TraderLineage.VT08_FOREX,
        request_id="request-test",
        signal_fingerprint="signal-test",
        qore_symbol="GBPUSD",
        provider_symbol=provider_symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.2500"),
        stop_loss=Decimal("1.2450"),
        take_profit=Decimal("1.2600"),
        requested_volume=Decimal("0.10"),
        authorized_volume=Decimal("0.10"),
        monetary_stop_loss=Decimal("5"),
        aggregate_pre_order_worst_case=Decimal("0"),
        aggregate_post_order_worst_case=Decimal("5"),
        provider_headroom=Decimal("120"),
        internal_qore_headroom=Decimal("25"),
        margin_reserved=Decimal("5"),
        decision=RiskDecision.ALLOW,
        reason="test",
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=2),
        authorization_fingerprint="a" * 64,
    )


def _rules() -> StellarInstantRuleVerification:
    return StellarInstantRuleVerification(
        verification_state=RuleVerificationState.CURRENT,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )


def _gateway(
    transport: AccountCatalogTransport,
    safety: OperationalSafetyController,
) -> FundedNextAccountBoundMt5Gateway:
    return FundedNextAccountBoundMt5Gateway(
        account=MarketTestAccountIdentity(
            provider_key="fundednext-stellar-instant-mt5",
            account_ref="fn-si-opaque-001",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        transport=transport,
        mutation_ledger=InMemoryFundedNextMt5MutationLedger(),
        rule_verification=_rules(),
        owner_submission_enabled=False,
        safety=safety,
    )


def _submission(provider_symbol: str = "GBPUSD.a") -> ExecutionSubmission:
    switch = ExecutionSafetySwitchSnapshot(
        state=ExecutionSwitchState.ENABLED,
        observed_at=_NOW,
        reason="shadow-only test",
    )
    return build_account_bound_submission(
        _authorization(provider_symbol),
        switch=switch,
        authorized_at=_NOW,
        submitted_at=_NOW,
    )


def test_account_symbol_resolution_uses_unique_terminal_identity() -> None:
    assert resolve_account_provider_symbol(
        "GBPUSD",
        ("EURUSD.a", "GBPUSD.a", "AUDJPY.a"),
    ) == "GBPUSD.a"
    assert resolve_account_provider_symbol(
        "GBPUSD",
        ("GBPUSD", "GBPUSD.a"),
    ) == "GBPUSD"
    with pytest.raises(Mt5ExecutionBlockedError, match="ambiguous"):
        resolve_account_provider_symbol("GBPUSD", ("GBPUSD.a", "GBPUSD.b"))
    with pytest.raises(Mt5ExecutionBlockedError, match="missing"):
        resolve_account_provider_symbol("GBPUSD", ("EURUSD.a",))
    with pytest.raises(Mt5ExecutionBlockedError, match="outside-approved-forex"):
        resolve_account_provider_symbol("NAS100", ("NDX100",))


def test_risk_provider_symbol_must_match_account_discovery() -> None:
    transport = AccountCatalogTransport()
    gateway = _gateway(transport, OperationalSafetyController())
    plan = gateway.plan_submission(_submission(), now=_NOW)
    assert plan.qore_symbol == "GBPUSD"
    assert plan.provider_symbol == "GBPUSD.a"
    assert transport.submissions == 0

    with pytest.raises(
        Mt5ExecutionBlockedError,
        match="risk-provider-symbol-account-mismatch",
    ):
        gateway.plan_submission(_submission("GBPUSD"), now=_NOW)


def test_scoped_kill_switches_block_new_orders_fail_closed() -> None:
    transport = AccountCatalogTransport()
    safety = OperationalSafetyController()
    gateway = _gateway(transport, safety)
    submission = _submission()

    safety.set_account_enabled(False)
    with pytest.raises(Mt5ExecutionBlockedError, match="account-kill-switch"):
        gateway.plan_submission(submission, now=_NOW)
    safety.set_account_enabled(True)

    safety.set_gateway_enabled(False)
    with pytest.raises(Mt5ExecutionBlockedError, match="gateway-kill-switch"):
        gateway.plan_submission(submission, now=_NOW)
    safety.set_gateway_enabled(True)

    safety.set_trader_enabled("VT08_FOREX", False)
    with pytest.raises(Mt5ExecutionBlockedError, match="trader-kill-switch"):
        gateway.plan_submission(submission, now=_NOW)
    safety.set_trader_enabled("VT08_FOREX", True)

    safety.set_market_enabled("GBPUSD", False)
    with pytest.raises(Mt5ExecutionBlockedError, match="market-kill-switch"):
        gateway.plan_submission(submission, now=_NOW)

    assert transport.submissions == 0
