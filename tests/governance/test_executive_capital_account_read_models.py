from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.governance.executive_capital_account_read_models import (
    ExecutiveAccountEnvironment,
    ExecutiveAccountOperationalState,
    ExecutiveCapitalCurrencySummary,
    ExecutiveCapitalStateReadModel,
    ExecutiveCeoAccountSummary,
    ExecutiveCeoAccountsReadModel,
    ExecutiveCurrencyCode,
    ExecutiveDrawdownBps,
    ExecutiveMoneyAmount,
    ExecutiveProprietaryAccountRef,
    ExecutiveRealizedPerformanceSummary,
)
from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadModelValidationError,
    ExecutiveSourceFreshness,
)

_NOW = datetime(2026, 8, 8, 22, 30, tzinfo=UTC)
_USD = ExecutiveCurrencyCode("USD")
_EUR = ExecutiveCurrencyCode("EUR")


def _metadata(scope: ExecutiveReadScope) -> ExecutiveProjectionMetadata:
    return ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("2e000000-0000-0000-0000-000000000001")
        ),
        projection_version=ExecutiveProjectionVersion("executive-capital-account.v1"),
        scope=scope,
        source_observed_at=_NOW,
        projected_at=_NOW + timedelta(seconds=1),
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:capital-account/root-001"),),
    )


def _money(value: str, currency: ExecutiveCurrencyCode = _USD) -> ExecutiveMoneyAmount:
    return ExecutiveMoneyAmount(currency, Decimal(value))


def _performance(
    *,
    days: int,
    value: str,
    currency: ExecutiveCurrencyCode = _USD,
) -> ExecutiveRealizedPerformanceSummary:
    return ExecutiveRealizedPerformanceSummary(
        period_start=_NOW - timedelta(days=days),
        period_end=_NOW - timedelta(days=days - 1),
        observed_at=_NOW,
        realized_pnl=_money(value, currency),
        evidence_refs=(
            ExecutiveEvidenceRef(f"evidence:performance/window-{days}"),
        ),
    )


def _account(
    account_id: str = "2e000000-0000-0000-0000-000000000010",
) -> ExecutiveCeoAccountSummary:
    return ExecutiveCeoAccountSummary(
        account_ref=ExecutiveProprietaryAccountRef(UUID(account_id)),
        source_observed_at=_NOW,
        environment=ExecutiveAccountEnvironment.DEMO,
        state=ExecutiveAccountOperationalState.ACTIVE,
        balance=_money("10000"),
        equity=_money("10125.5"),
        unrealized_pnl=_money("125.5"),
        margin_used=_money("500"),
        drawdown=ExecutiveDrawdownBps(125),
        realized_performance=(
            _performance(days=7, value="300"),
            _performance(days=1, value="75"),
        ),
        evidence_refs=(ExecutiveEvidenceRef("evidence:account/current-001"),),
    )


def test_ceo_account_projection_is_scope_bound_opaque_and_deterministic() -> None:
    second = _account("2e000000-0000-0000-0000-000000000011")
    first = _account("2e000000-0000-0000-0000-000000000010")
    model = ExecutiveCeoAccountsReadModel(
        metadata=_metadata(ExecutiveReadScope.CEO_ACCOUNTS),
        attention=ExecutiveAttentionLevel.INFORMATION,
        accounts=(second, first),
    )

    assert model.accounts == (first, second)
    assert first.currency == _USD
    assert tuple(item.period_start for item in first.realized_performance) == tuple(
        sorted(item.period_start for item in first.realized_performance)
    )
    assert model.logical_values() == model.logical_values()
    assert not hasattr(first, "broker_account_number")
    assert not hasattr(first, "provider_account_id")
    assert not hasattr(first, "credentials")
    assert not hasattr(first, "client_profit_share")


def test_ceo_accounts_projection_rejects_wrong_scope_and_duplicate_accounts() -> None:
    account = _account()

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCeoAccountsReadModel(
            metadata=_metadata(ExecutiveReadScope.CAPITAL_STATE),
            attention=ExecutiveAttentionLevel.ATTENTION,
            accounts=(account,),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCeoAccountsReadModel(
            metadata=_metadata(ExecutiveReadScope.CEO_ACCOUNTS),
            attention=ExecutiveAttentionLevel.IMPORTANT,
            accounts=(account, account),
        )


def test_ceo_account_requires_single_currency_and_nonnegative_current_state() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCeoAccountSummary(
            account_ref=ExecutiveProprietaryAccountRef(
                UUID("2e000000-0000-0000-0000-000000000012")
            ),
            source_observed_at=_NOW,
            environment=ExecutiveAccountEnvironment.DEMO,
            state=ExecutiveAccountOperationalState.ACTIVE,
            balance=_money("1000"),
            equity=_money("1000", _EUR),
            unrealized_pnl=_money("0"),
            margin_used=_money("0"),
            drawdown=ExecutiveDrawdownBps(0),
            realized_performance=(),
            evidence_refs=(ExecutiveEvidenceRef("evidence:account/mixed-currency"),),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCeoAccountSummary(
            account_ref=ExecutiveProprietaryAccountRef(
                UUID("2e000000-0000-0000-0000-000000000013")
            ),
            source_observed_at=_NOW,
            environment=ExecutiveAccountEnvironment.DEMO,
            state=ExecutiveAccountOperationalState.ACTIVE,
            balance=_money("-1"),
            equity=_money("1000"),
            unrealized_pnl=_money("0"),
            margin_used=_money("0"),
            drawdown=ExecutiveDrawdownBps(0),
            realized_performance=(),
            evidence_refs=(ExecutiveEvidenceRef("evidence:account/negative-balance"),),
        )


def test_realized_performance_requires_explicit_valid_window_and_account_currency() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveRealizedPerformanceSummary(
            period_start=_NOW,
            period_end=_NOW,
            observed_at=_NOW,
            realized_pnl=_money("10"),
            evidence_refs=(ExecutiveEvidenceRef("evidence:performance/invalid-window"),),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCeoAccountSummary(
            account_ref=ExecutiveProprietaryAccountRef(
                UUID("2e000000-0000-0000-0000-000000000014")
            ),
            source_observed_at=_NOW,
            environment=ExecutiveAccountEnvironment.PRACTICE,
            state=ExecutiveAccountOperationalState.RESTRICTED,
            balance=_money("1000"),
            equity=_money("1000"),
            unrealized_pnl=_money("0"),
            margin_used=_money("0"),
            drawdown=ExecutiveDrawdownBps(0),
            realized_performance=(_performance(days=1, value="10", currency=_EUR),),
            evidence_refs=(ExecutiveEvidenceRef("evidence:account/performance-currency"),),
        )


def test_capital_state_groups_by_currency_without_implicit_fx_aggregation() -> None:
    usd = ExecutiveCapitalCurrencySummary(
        currency=_USD,
        account_count=2,
        total_balance=_money("20000"),
        total_equity=_money("20200"),
        total_unrealized_pnl=_money("200"),
        total_margin_used=_money("1000"),
        worst_account_drawdown=ExecutiveDrawdownBps(250),
    )
    eur = ExecutiveCapitalCurrencySummary(
        currency=_EUR,
        account_count=1,
        total_balance=_money("5000", _EUR),
        total_equity=_money("4900", _EUR),
        total_unrealized_pnl=_money("-100", _EUR),
        total_margin_used=_money("300", _EUR),
        worst_account_drawdown=ExecutiveDrawdownBps(500),
    )
    model = ExecutiveCapitalStateReadModel(
        metadata=_metadata(ExecutiveReadScope.CAPITAL_STATE),
        attention=ExecutiveAttentionLevel.ATTENTION,
        currencies=(usd, eur),
    )

    assert tuple(item.currency.value for item in model.currencies) == ("EUR", "USD")
    assert len(model.currencies) == 2
    assert not hasattr(model, "converted_total")
    assert not hasattr(model, "fx_rate")
    assert model.logical_values() == model.logical_values()


def test_capital_state_rejects_wrong_scope_duplicate_currency_and_mixed_money() -> None:
    usd = ExecutiveCapitalCurrencySummary(
        currency=_USD,
        account_count=1,
        total_balance=_money("1000"),
        total_equity=_money("1000"),
        total_unrealized_pnl=_money("0"),
        total_margin_used=_money("0"),
        worst_account_drawdown=ExecutiveDrawdownBps(0),
    )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCapitalStateReadModel(
            metadata=_metadata(ExecutiveReadScope.CEO_ACCOUNTS),
            attention=ExecutiveAttentionLevel.INFORMATION,
            currencies=(usd,),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCapitalStateReadModel(
            metadata=_metadata(ExecutiveReadScope.CAPITAL_STATE),
            attention=ExecutiveAttentionLevel.INFORMATION,
            currencies=(usd, usd),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCapitalCurrencySummary(
            currency=_USD,
            account_count=1,
            total_balance=_money("1000"),
            total_equity=_money("1000", _EUR),
            total_unrealized_pnl=_money("0"),
            total_margin_used=_money("0"),
            worst_account_drawdown=ExecutiveDrawdownBps(0),
        )


def test_capital_account_counts_and_drawdown_are_strict_integers() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveCapitalCurrencySummary(
            currency=_USD,
            account_count=0,
            total_balance=_money("1000"),
            total_equity=_money("1000"),
            total_unrealized_pnl=_money("0"),
            total_margin_used=_money("0"),
            worst_account_drawdown=ExecutiveDrawdownBps(0),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveDrawdownBps(True)


def test_production_environment_is_descriptive_not_execution_authority() -> None:
    assert ExecutiveAccountEnvironment.PRODUCTION.value == "production"
    assert not hasattr(ExecutiveAccountEnvironment.PRODUCTION, "submit_order")
    assert not hasattr(ExecutiveAccountEnvironment.PRODUCTION, "authorized")
