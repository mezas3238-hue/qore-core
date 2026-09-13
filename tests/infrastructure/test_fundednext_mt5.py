from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import (
    RiskAuthorization,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.fundednext_mt5 import (
    ExecutionMode,
    FundedNextMt5Adapter,
    Mt5AccountState,
    Mt5ExecutionError,
    Mt5OrderIntent,
    Mt5SymbolSpecification,
    ProviderSubmission,
    SubmissionStatus,
)
from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantRuleVerification,
)

_NOW = datetime(2026, 9, 13, 18, 0, tzinfo=UTC)


class FakeGateway:
    def __init__(self) -> None:
        self.is_connected = True
        self.missing_symbol = False
        self.unknown_submit = False
        self.reconcile_result: ProviderSubmission | None = None
        self.submit_calls = 0
        self.spec_observed_at = _NOW

    def connected(self) -> bool:
        return self.is_connected

    def account_state(self) -> Mt5AccountState | None:
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

    def submit(self, intent: Mt5OrderIntent) -> ProviderSubmission:
        self.submit_calls += 1
        if self.unknown_submit:
            return ProviderSubmission(
                status=SubmissionStatus.UNKNOWN_RECONCILE_REQUIRED,
                idempotency_key=intent.idempotency_key,
                provider_order_id=None,
                message="provider-timeout",
            )
        return ProviderSubmission(
            status=SubmissionStatus.ACKNOWLEDGED,
            idempotency_key=intent.idempotency_key,
            provider_order_id="ticket-1",
            message="accepted",
        )

    def reconcile(self, idempotency_key: str) -> ProviderSubmission | None:
        if self.reconcile_result is not None:
            return self.reconcile_result
        return ProviderSubmission(
            status=SubmissionStatus.ACKNOWLEDGED,
            idempotency_key=idempotency_key,
            provider_order_id="ticket-reconciled",
            message="found-after-timeout",
        )


def _rules() -> StellarInstantRuleVerification:
    return StellarInstantRuleVerification(
        rules_verified_at=_NOW - timedelta(minutes=1),
        rules_valid_until=_NOW + timedelta(hours=1),
        verification_state=RuleVerificationState.CURRENT,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )


def _authorization(
    fingerprint: str = "a" * 64,
    *,
    volume: str = "1.0",
    stop: str = "99",
) -> RiskAuthorization:
    return RiskAuthorization(
        authorization_id=f"risk-{fingerprint[:24]}",
        account_binding_id="fn-si-opaque-001",
        trader_id=TraderLineage.VT08_FOREX,
        request_id=f"request-{fingerprint[:8]}",
        signal_fingerprint=f"signal-{fingerprint[:8]}",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
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


def test_read_only_constructs_but_never_submits_and_duplicate_is_blocked() -> None:
    gateway = FakeGateway()
    adapter = FundedNextMt5Adapter(gateway)
    intent = adapter.build_intent(_authorization(), now=_NOW)
    first = adapter.execute(intent, mode=ExecutionMode.READ_ONLY, rule_verification=_rules(), now=_NOW)
    second = adapter.execute(intent, mode=ExecutionMode.READ_ONLY, rule_verification=_rules(), now=_NOW)
    assert first.status is SubmissionStatus.NOT_SUBMITTED
    assert second.status is SubmissionStatus.DUPLICATE_BLOCKED
    assert gateway.submit_calls == 0


def test_missing_or_stale_symbol_info_fails_closed() -> None:
    gateway = FakeGateway()
    gateway.missing_symbol = True
    adapter = FundedNextMt5Adapter(gateway)
    with pytest.raises(Mt5ExecutionError, match="symbol-info-missing"):
        adapter.build_intent(_authorization(), now=_NOW)

    gateway.missing_symbol = False
    gateway.spec_observed_at = _NOW - timedelta(minutes=1)
    with pytest.raises(Mt5ExecutionError, match="symbol-info-stale"):
        adapter.build_intent(_authorization(), now=_NOW)


def test_invalid_volume_step_and_stop_distance_fail_closed() -> None:
    gateway = FakeGateway()
    adapter = FundedNextMt5Adapter(gateway)
    with pytest.raises(Mt5ExecutionError, match="volume-not-on-broker-step"):
        adapter.build_intent(_authorization(volume="0.15"), now=_NOW)
    with pytest.raises(Mt5ExecutionError, match="stop-inside-broker-minimum-distance"):
        adapter.build_intent(_authorization(stop="99.97"), now=_NOW)


def test_live_submission_requires_explicit_owner_runtime_enable() -> None:
    gateway = FakeGateway()
    adapter = FundedNextMt5Adapter(gateway, live_submission_enabled=False)
    intent = adapter.build_intent(_authorization(), now=_NOW)
    with pytest.raises(Mt5ExecutionError, match="owner-order-submission-authorization-disabled"):
        adapter.execute(intent, mode=ExecutionMode.LIVE, rule_verification=_rules(), now=_NOW)
    assert gateway.submit_calls == 0


def test_unknown_submit_requires_reconciliation_before_any_new_order() -> None:
    gateway = FakeGateway()
    gateway.unknown_submit = True
    adapter = FundedNextMt5Adapter(gateway, live_submission_enabled=True)
    first = adapter.build_intent(_authorization("a" * 64), now=_NOW)
    outcome = adapter.execute(first, mode=ExecutionMode.LIVE, rule_verification=_rules(), now=_NOW)
    assert outcome.status is SubmissionStatus.UNKNOWN_RECONCILE_REQUIRED
    assert adapter.reconciliation_required is True

    second = adapter.build_intent(_authorization("b" * 64), now=_NOW)
    with pytest.raises(Mt5ExecutionError, match="unresolved-provider-state"):
        adapter.execute(second, mode=ExecutionMode.LIVE, rule_verification=_rules(), now=_NOW)

    reconciled = adapter.reconcile_unknown(first.idempotency_key)
    assert reconciled.status is SubmissionStatus.ACKNOWLEDGED
    assert adapter.reconciliation_required is False
