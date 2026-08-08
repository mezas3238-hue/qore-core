from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_profit_vault_read_models import (
    ExecutiveCorporateProfitVaultReadModel,
    ExecutiveVaultAccountPhase,
    ExecutiveVaultCurrencyCode,
    ExecutiveVaultCurrencySummary,
    ExecutiveVaultEntitlementState,
    ExecutiveVaultLedgerCounts,
    ExecutiveVaultLedgerRef,
    ExecutiveVaultLedgerSummary,
    ExecutiveVaultMoneyAmount,
    ExecutiveVaultProfitShareRateBps,
    ExecutiveVaultSettlementPeriodRef,
    ExecutiveVaultSettlementState,
)
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutivePolicyVersionRef,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadModelValidationError,
    ExecutiveSourceFreshness,
)

_NOW = datetime(2026, 8, 8, 22, 45, tzinfo=UTC)
_USD = ExecutiveVaultCurrencyCode("USD")
_EUR = ExecutiveVaultCurrencyCode("EUR")


def _metadata() -> ExecutiveProjectionMetadata:
    return ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("2f000000-0000-0000-0000-000000000001")
        ),
        projection_version=ExecutiveProjectionVersion("executive-profit-vault.v1"),
        scope=ExecutiveReadScope.CORPORATE_PROFIT_VAULT,
        source_observed_at=_NOW,
        projected_at=_NOW + timedelta(seconds=1),
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:vault/root-001"),),
    )


def _money(
    value: str,
    currency: ExecutiveVaultCurrencyCode = _USD,
) -> ExecutiveVaultMoneyAmount:
    return ExecutiveVaultMoneyAmount(currency, Decimal(value))


def _ledger(
    *,
    ledger_id: str = "2f000000-0000-0000-0000-000000000010",
    period_id: str = "2f000000-0000-0000-0000-000000000020",
    positive: str = "5000",
    negative: str = "-2000",
    eligible: str = "3000",
    due: str = "600",
    paid: str = "200",
    outstanding: str = "400",
    phase: ExecutiveVaultAccountPhase = ExecutiveVaultAccountPhase.PAYOUT_ELIGIBLE,
) -> ExecutiveVaultLedgerSummary:
    net = Decimal(positive) + Decimal(negative)
    return ExecutiveVaultLedgerSummary(
        ledger_ref=ExecutiveVaultLedgerRef(UUID(ledger_id)),
        settlement_period_ref=ExecutiveVaultSettlementPeriodRef(UUID(period_id)),
        period_start=_NOW - timedelta(days=30),
        period_end=_NOW,
        phase=phase,
        settlement_state=ExecutiveVaultSettlementState.DUE,
        entitlement_state=ExecutiveVaultEntitlementState.PAYMENT_DUE,
        policy_version=ExecutivePolicyVersionRef("vault-policy.v1"),
        positive_realized=_money(positive),
        negative_realized=_money(negative),
        net_realized=_money(str(net)),
        carryforward_balance=_money("0"),
        eligible_positive_base=_money(eligible),
        profit_share_rate=ExecutiveVaultProfitShareRateBps(2000),
        amount_due=_money(due),
        amount_paid=_money(paid),
        outstanding=_money(outstanding),
        evidence_refs=(ExecutiveEvidenceRef(f"evidence:vault/{ledger_id[-3:]}"),),
    )


def _currency_summary(
    currency: ExecutiveVaultCurrencyCode = _USD,
) -> ExecutiveVaultCurrencySummary:
    return ExecutiveVaultCurrencySummary(
        currency=currency,
        positive_realized_total=_money("5000", currency),
        negative_realized_total=_money("-2000", currency),
        eligible_positive_base=_money("3000", currency),
        receivable=_money("600", currency),
        collected=_money("200", currency),
        outstanding=_money("400", currency),
        evidence_refs=(
            ExecutiveEvidenceRef(
                f"evidence:vault/aggregate-{currency.value.lower()}"
            ),
        ),
    )


def test_vault_ledger_preserves_positive_and_negative_history() -> None:
    ledger = _ledger()

    assert ledger.positive_realized.amount == Decimal("5000")
    assert ledger.negative_realized.amount == Decimal("-2000")
    assert ledger.net_realized.amount == Decimal("3000")
    assert ledger.amount_due.amount == Decimal("600")
    assert ledger.profit_share_rate.value == 2000
    assert ledger.logical_values() == ledger.logical_values()


def test_vault_non_positive_net_result_cannot_have_amount_due() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        _ledger(
            positive="1000",
            negative="-1500",
            eligible="0",
            due="1",
            paid="0",
            outstanding="1",
        )


def test_vault_evaluation_and_verification_are_non_billable() -> None:
    for phase in (
        ExecutiveVaultAccountPhase.EVALUATION,
        ExecutiveVaultAccountPhase.VERIFICATION,
    ):
        with pytest.raises(ExecutiveReadModelValidationError):
            _ledger(phase=phase, due="600")

        ledger = _ledger(
            phase=phase,
            eligible="0",
            due="0",
            paid="0",
            outstanding="0",
        )
        assert ledger.amount_due.amount == 0


def test_vault_ledger_rejects_inconsistent_net_and_mixed_currency() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveVaultLedgerSummary(
            ledger_ref=ExecutiveVaultLedgerRef(
                UUID("2f000000-0000-0000-0000-000000000011")
            ),
            settlement_period_ref=ExecutiveVaultSettlementPeriodRef(
                UUID("2f000000-0000-0000-0000-000000000021")
            ),
            period_start=_NOW - timedelta(days=30),
            period_end=_NOW,
            phase=ExecutiveVaultAccountPhase.REWARD_ELIGIBLE,
            settlement_state=ExecutiveVaultSettlementState.READY,
            entitlement_state=ExecutiveVaultEntitlementState.ACTIVE,
            policy_version=ExecutivePolicyVersionRef("vault-policy.v1"),
            positive_realized=_money("1000"),
            negative_realized=_money("-100"),
            net_realized=_money("1000"),
            carryforward_balance=_money("0"),
            eligible_positive_base=_money("900"),
            profit_share_rate=ExecutiveVaultProfitShareRateBps(2000),
            amount_due=_money("180"),
            amount_paid=_money("0"),
            outstanding=_money("180"),
            evidence_refs=(ExecutiveEvidenceRef("evidence:vault/inconsistent-net"),),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveVaultLedgerSummary(
            ledger_ref=ExecutiveVaultLedgerRef(
                UUID("2f000000-0000-0000-0000-000000000012")
            ),
            settlement_period_ref=ExecutiveVaultSettlementPeriodRef(
                UUID("2f000000-0000-0000-0000-000000000022")
            ),
            period_start=_NOW - timedelta(days=30),
            period_end=_NOW,
            phase=ExecutiveVaultAccountPhase.PAYOUT_ELIGIBLE,
            settlement_state=ExecutiveVaultSettlementState.DUE,
            entitlement_state=ExecutiveVaultEntitlementState.PAYMENT_DUE,
            policy_version=ExecutivePolicyVersionRef("vault-policy.v1"),
            positive_realized=_money("1000"),
            negative_realized=_money("0"),
            net_realized=_money("1000"),
            carryforward_balance=_money("0"),
            eligible_positive_base=_money("1000"),
            profit_share_rate=ExecutiveVaultProfitShareRateBps(2000),
            amount_due=_money("200", _EUR),
            amount_paid=_money("0"),
            outstanding=_money("200"),
            evidence_refs=(ExecutiveEvidenceRef("evidence:vault/mixed-currency"),),
        )


def test_vault_currency_summary_never_crosses_currency_boundary() -> None:
    usd = _currency_summary(_USD)
    eur = _currency_summary(_EUR)
    model = ExecutiveCorporateProfitVaultReadModel(
        metadata=_metadata(),
        attention=ExecutiveAttentionLevel.INFORMATION,
        ledger_counts=ExecutiveVaultLedgerCounts(1, 1, 0, 0),
        currency_summaries=(usd, eur),
        ledgers=(_ledger(),),
    )

    assert tuple(item.currency.value for item in model.currency_summaries) == (
        "EUR",
        "USD",
    )
    assert not hasattr(model, "converted_total")
    assert not hasattr(model, "fx_rate")


def test_vault_read_model_is_scope_bound_and_count_consistent() -> None:
    positive = _ledger()
    negative = _ledger(
        ledger_id="2f000000-0000-0000-0000-000000000013",
        period_id="2f000000-0000-0000-0000-000000000023",
        positive="100",
        negative="-200",
        eligible="0",
        due="0",
        paid="0",
        outstanding="0",
    )
    model = ExecutiveCorporateProfitVaultReadModel(
        metadata=_metadata(),
        attention=ExecutiveAttentionLevel.ATTENTION,
        ledger_counts=ExecutiveVaultLedgerCounts(2, 1, 1, 0),
        currency_summaries=(_currency_summary(),),
        ledgers=(negative, positive),
    )

    assert model.metadata.scope is ExecutiveReadScope.CORPORATE_PROFIT_VAULT
    assert model.ledgers == (positive, negative)
    assert model.logical_values() == model.logical_values()

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCorporateProfitVaultReadModel(
            metadata=_metadata(),
            attention=ExecutiveAttentionLevel.IMPORTANT,
            ledger_counts=ExecutiveVaultLedgerCounts(2, 2, 0, 0),
            currency_summaries=(_currency_summary(),),
            ledgers=(positive, negative),
        )


def test_vault_read_model_rejects_wrong_scope() -> None:
    metadata = ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("2f000000-0000-0000-0000-000000000002")
        ),
        projection_version=ExecutiveProjectionVersion("executive-profit-vault.v1"),
        scope=ExecutiveReadScope.CEO_ACCOUNTS,
        source_observed_at=_NOW,
        projected_at=_NOW,
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:vault/wrong-scope"),),
    )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCorporateProfitVaultReadModel(
            metadata=metadata,
            attention=ExecutiveAttentionLevel.CRITICAL,
            ledger_counts=ExecutiveVaultLedgerCounts(0, 0, 0, 0),
            currency_summaries=(),
            ledgers=(),
        )


def test_vault_projection_contains_no_client_or_proprietary_account_state() -> None:
    ledger = _ledger()

    assert not hasattr(ledger, "client_name")
    assert not hasattr(ledger, "broker_account_number")
    assert not hasattr(ledger, "balance")
    assert not hasattr(ledger, "equity")
    assert not hasattr(ledger, "drawdown")
    assert not hasattr(ledger, "positions")
    assert not hasattr(ledger, "cibo")
    assert not hasattr(ledger, "strategy")


def test_vault_read_model_has_no_trading_authority() -> None:
    model = ExecutiveCorporateProfitVaultReadModel(
        metadata=_metadata(),
        attention=ExecutiveAttentionLevel.INFORMATION,
        ledger_counts=ExecutiveVaultLedgerCounts(0, 0, 0, 0),
        currency_summaries=(),
        ledgers=(),
    )

    assert not hasattr(model, "buy")
    assert not hasattr(model, "sell")
    assert not hasattr(model, "submit_order")
    assert not hasattr(model, "close_position")
    assert not hasattr(model, "risk_bypass")


def test_vault_profit_share_rate_is_strict_basis_points() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveVaultProfitShareRateBps(10_001)

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveVaultProfitShareRateBps(True)
