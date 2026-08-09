from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.functional.decisions as decisions
import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_multiaccount_read_model as read_model
import qore.infrastructure.client_position_lifecycle as lifecycle
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.commercial_billing as billing
import qore.infrastructure.order_intent as orders
import qore.infrastructure.proprietary_accounts as money

_NOW = datetime(2026, 8, 9, 14, 0, tzinfo=UTC)
_USD = money.CurrencyCode("USD")
_EUR = money.CurrencyCode("EUR")


def _uuid(suffix: int) -> UUID:
    return UUID(f"41000000-0000-0000-0000-{suffix:012d}")


def _amount(currency: money.CurrencyCode, value: str) -> money.MoneyAmount:
    return money.MoneyAmount(currency=currency, amount=Decimal(value))


def _pulse(account_suffix: int, position_suffix: int) -> read_model.ClientTradePulse:
    return read_model.ClientTradePulse(
        account_id=accounts.TradingAccountId(_uuid(account_suffix)),
        position_id=lifecycle.ClientPositionId(_uuid(position_suffix)),
        decision_id=decisions.DecisionId(_uuid(position_suffix + 1)),
        instrument=orders.ExecutionInstrument("EUR_USD"),
        side=orders.OrderSide.BUY,
        position_state=lifecycle.ClientPositionState.OPEN,
        occurred_at=_NOW - timedelta(minutes=5),
    )


def _account(
    *,
    account_suffix: int,
    currency: money.CurrencyCode = _USD,
    balance: str = "10000",
    today: str = "100",
    week: str = "250",
    pulse: bool = True,
    client_suffix: int = 1,
) -> read_model.ClientAccountReadSnapshot:
    pulses = (_pulse(account_suffix, account_suffix + 100),) if pulse else ()
    return read_model.ClientAccountReadSnapshot(
        client_id=accounts.ClientId(_uuid(client_suffix)),
        account_id=accounts.TradingAccountId(_uuid(account_suffix)),
        account_state=accounts.TradingAccountLifecycleState.ACTIVE,
        balance=_amount(currency, balance),
        generated_today=_amount(currency, today),
        generated_week=_amount(currency, week),
        service_status=read_model.ClientServiceStatus.ONLINE,
        license_state=licensing.ClientLicenseState.LICENSED,
        billing_state=billing.CommercialBillingStandingState.CURRENT,
        trade_pulses=pulses,
        captured_at=_NOW - timedelta(seconds=1),
    )


def _today() -> read_model.ClientPerformanceWindow:
    return read_model.ClientPerformanceWindow(
        started_at=_NOW - timedelta(hours=14),
        ended_at=_NOW,
    )


def _week() -> read_model.ClientPerformanceWindow:
    return read_model.ClientPerformanceWindow(
        started_at=_NOW - timedelta(days=6, hours=14),
        ended_at=_NOW,
    )


def test_multiple_accounts_aggregate_by_currency_for_presentation_only() -> None:
    first = _account(account_suffix=10, balance="10000", today="100", week="250")
    second = _account(account_suffix=20, balance="5000", today="-25", week="75")

    model = read_model.build_client_multiaccount_read_model(
        read_model_id=read_model.ClientReadModelId(_uuid(500)),
        client_id=accounts.ClientId(_uuid(1)),
        today_window=_today(),
        week_window=_week(),
        accounts=(second, first),
        generated_at=_NOW,
    )

    assert len(model.accounts) == 2
    assert len(model.currency_summaries) == 1
    summary = model.currency_summaries[0]
    assert summary.currency == _USD
    assert summary.account_count == 2
    assert summary.balance == _amount(_USD, "15000")
    assert summary.generated_today == _amount(_USD, "75")
    assert summary.generated_week == _amount(_USD, "325")


def test_different_currencies_are_never_mixed_into_one_total() -> None:
    usd = _account(account_suffix=30, currency=_USD, balance="10000")
    eur = _account(account_suffix=40, currency=_EUR, balance="8000")

    model = read_model.build_client_multiaccount_read_model(
        read_model_id=read_model.ClientReadModelId(_uuid(501)),
        client_id=accounts.ClientId(_uuid(1)),
        today_window=_today(),
        week_window=_week(),
        accounts=(usd, eur),
        generated_at=_NOW,
    )

    assert len(model.currency_summaries) == 2
    assert {summary.currency for summary in model.currency_summaries} == {_USD, _EUR}
    assert not hasattr(model, "total_balance")
    assert not hasattr(model, "aggregate_risk")


def test_trade_pulse_exposes_account_time_pair_and_position_state() -> None:
    account = _account(account_suffix=50)
    model = read_model.build_client_multiaccount_read_model(
        read_model_id=read_model.ClientReadModelId(_uuid(502)),
        client_id=accounts.ClientId(_uuid(1)),
        today_window=_today(),
        week_window=_week(),
        accounts=(account,),
        generated_at=_NOW,
    )

    pulse = model.trade_pulses[0]
    assert pulse.account_id == account.account_id
    assert pulse.occurred_at == _NOW - timedelta(minutes=5)
    assert pulse.instrument == orders.ExecutionInstrument("EUR_USD")
    assert pulse.position_state is lifecycle.ClientPositionState.OPEN


def test_client_accounts_remain_independent_and_cannot_cross_ownership() -> None:
    valid = _account(account_suffix=60)
    foreign = _account(account_suffix=70, client_suffix=2)

    with pytest.raises(read_model.ClientMultiAccountReadModelValidationError):
        read_model.build_client_multiaccount_read_model(
            read_model_id=read_model.ClientReadModelId(_uuid(503)),
            client_id=accounts.ClientId(_uuid(1)),
            today_window=_today(),
            week_window=_week(),
            accounts=(valid, foreign),
            generated_at=_NOW,
        )


def test_duplicate_account_snapshot_is_rejected() -> None:
    account = _account(account_suffix=80)

    with pytest.raises(read_model.ClientMultiAccountReadModelValidationError):
        read_model.build_client_multiaccount_read_model(
            read_model_id=read_model.ClientReadModelId(_uuid(504)),
            client_id=accounts.ClientId(_uuid(1)),
            today_window=_today(),
            week_window=_week(),
            accounts=(account, account),
            generated_at=_NOW,
        )


def test_today_and_week_windows_are_explicit_not_hidden_clock() -> None:
    account = _account(account_suffix=90)
    wrong_today = read_model.ClientPerformanceWindow(
        started_at=_NOW - timedelta(hours=10),
        ended_at=_NOW - timedelta(seconds=1),
    )

    with pytest.raises(read_model.ClientMultiAccountReadModelValidationError):
        read_model.build_client_multiaccount_read_model(
            read_model_id=read_model.ClientReadModelId(_uuid(505)),
            client_id=accounts.ClientId(_uuid(1)),
            today_window=wrong_today,
            week_window=_week(),
            accounts=(account,),
            generated_at=_NOW,
        )


def test_read_model_carries_service_license_and_billing_status_without_authority() -> None:
    account = _account(account_suffix=100)

    assert account.service_status is read_model.ClientServiceStatus.ONLINE
    assert account.license_state is licensing.ClientLicenseState.LICENSED
    assert account.billing_state is billing.CommercialBillingStandingState.CURRENT
    assert not hasattr(account, "activate_license")
    assert not hasattr(account, "mark_paid")
    assert not hasattr(account, "submit_order")


def test_read_model_has_no_broker_or_trading_authority() -> None:
    assert not hasattr(read_model.ClientMultiAccountReadModel, "broker")
    assert not hasattr(read_model.ClientMultiAccountReadModel, "execute")
    assert not hasattr(read_model.ClientMultiAccountReadModel, "set_risk")
    assert not hasattr(read_model.ClientTradePulse, "close_position")
