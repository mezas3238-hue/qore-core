from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.functional.decisions import DecisionId
from qore.infrastructure.client_accounts import (
    ClientId,
    TradingAccountId,
    TradingAccountLifecycleState,
)
from qore.infrastructure.client_position_lifecycle import (
    ClientPositionId,
    ClientPositionState,
)
from qore.infrastructure.client_trial_licensing import ClientLicenseState
from qore.infrastructure.commercial_billing import CommercialBillingStandingState
from qore.infrastructure.order_intent import ExecutionInstrument, OrderSide
from qore.infrastructure.proprietary_accounts import CurrencyCode, MoneyAmount
from qore.kernel.errors import InfrastructureError


class ClientMultiAccountReadModelError(InfrastructureError):
    """Base error for client-facing multi-account read contracts."""

    __slots__ = ()


class ClientMultiAccountReadModelValidationError(ClientMultiAccountReadModelError):
    """Violation of a client read-model invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ClientMultiAccountReadModelValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ClientMultiAccountReadModelValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ClientReadModelId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ClientMultiAccountReadModelValidationError(
                "client read model id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ClientPerformanceWindow:
    started_at: datetime
    ended_at: datetime

    def __post_init__(self) -> None:
        _validate_timestamp(self.started_at, field_name="performance window started_at")
        _validate_timestamp(self.ended_at, field_name="performance window ended_at")
        if self.ended_at <= self.started_at:
            raise ClientMultiAccountReadModelValidationError(
                "performance window must have positive duration"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.started_at.isoformat(), self.ended_at.isoformat())


class ClientServiceStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ClientTradePulse:
    account_id: TradingAccountId
    position_id: ClientPositionId
    decision_id: DecisionId
    instrument: ExecutionInstrument
    side: OrderSide
    position_state: ClientPositionState
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientMultiAccountReadModelValidationError(
                "trade pulse account_id must be TradingAccountId"
            )
        if not isinstance(self.position_id, ClientPositionId):
            raise ClientMultiAccountReadModelValidationError(
                "trade pulse position_id must be ClientPositionId"
            )
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise ClientMultiAccountReadModelValidationError(
                "trade pulse decision_id must be UUID-backed DecisionId"
            )
        if not isinstance(self.instrument, ExecutionInstrument):
            raise ClientMultiAccountReadModelValidationError(
                "trade pulse instrument must be ExecutionInstrument"
            )
        if not isinstance(self.side, OrderSide):
            raise ClientMultiAccountReadModelValidationError(
                "trade pulse side must be OrderSide"
            )
        if not isinstance(self.position_state, ClientPositionState):
            raise ClientMultiAccountReadModelValidationError(
                "trade pulse position_state must be ClientPositionState"
            )
        _validate_timestamp(self.occurred_at, field_name="trade pulse occurred_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.position_id.logical_values(),
            str(self.decision_id.value),
            self.instrument.logical_values(),
            self.side.value,
            self.position_state.value,
            self.occurred_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ClientAccountReadSnapshot:
    client_id: ClientId
    account_id: TradingAccountId
    account_state: TradingAccountLifecycleState
    balance: MoneyAmount
    generated_today: MoneyAmount
    generated_week: MoneyAmount
    service_status: ClientServiceStatus
    license_state: ClientLicenseState
    billing_state: CommercialBillingStandingState
    trade_pulses: tuple[ClientTradePulse, ...]
    captured_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.client_id, ClientId):
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot client_id must be ClientId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot account_id must be TradingAccountId"
            )
        if not isinstance(self.account_state, TradingAccountLifecycleState):
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot account_state must be TradingAccountLifecycleState"
            )
        amounts = (self.balance, self.generated_today, self.generated_week)
        if any(not isinstance(amount, MoneyAmount) for amount in amounts):
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot money fields must be MoneyAmount"
            )
        currencies = {amount.currency for amount in amounts}
        if len(currencies) != 1:
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot money fields must use one currency"
            )
        if not isinstance(self.service_status, ClientServiceStatus):
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot service_status must be ClientServiceStatus"
            )
        if not isinstance(self.license_state, ClientLicenseState):
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot license_state must be ClientLicenseState"
            )
        if not isinstance(self.billing_state, CommercialBillingStandingState):
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot billing_state must be CommercialBillingStandingState"
            )
        if not isinstance(self.trade_pulses, tuple):
            raise ClientMultiAccountReadModelValidationError(
                "trade_pulses must be immutable tuple"
            )
        if any(
            not isinstance(pulse, ClientTradePulse)
            or pulse.account_id != self.account_id
            for pulse in self.trade_pulses
        ):
            raise ClientMultiAccountReadModelValidationError(
                "trade pulses must bind exact account snapshot"
            )
        ordered_pulses = tuple(
            sorted(
                self.trade_pulses,
                key=lambda pulse: (
                    pulse.occurred_at,
                    str(pulse.position_id.value),
                ),
                reverse=True,
            )
        )
        object.__setattr__(self, "trade_pulses", ordered_pulses)
        _validate_timestamp(self.captured_at, field_name="account snapshot captured_at")
        if any(pulse.occurred_at > self.captured_at for pulse in self.trade_pulses):
            raise ClientMultiAccountReadModelValidationError(
                "trade pulse must not be later than snapshot capture"
            )

    @property
    def currency(self) -> CurrencyCode:
        return self.balance.currency

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.client_id.logical_values(),
            self.account_id.logical_values(),
            self.account_state.value,
            self.balance.logical_values(),
            self.generated_today.logical_values(),
            self.generated_week.logical_values(),
            self.service_status.value,
            self.license_state.value,
            self.billing_state.value,
            tuple(pulse.logical_values() for pulse in self.trade_pulses),
            self.captured_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ClientCurrencySummary:
    currency: CurrencyCode
    account_count: int
    balance: MoneyAmount
    generated_today: MoneyAmount
    generated_week: MoneyAmount

    def __post_init__(self) -> None:
        if not isinstance(self.currency, CurrencyCode):
            raise ClientMultiAccountReadModelValidationError(
                "currency summary currency must be CurrencyCode"
            )
        if type(self.account_count) is not int or self.account_count <= 0:
            raise ClientMultiAccountReadModelValidationError(
                "currency summary account_count must be positive integer"
            )
        for amount in (self.balance, self.generated_today, self.generated_week):
            if not isinstance(amount, MoneyAmount) or amount.currency != self.currency:
                raise ClientMultiAccountReadModelValidationError(
                    "currency summary money must use summary currency"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.currency.logical_values(),
            self.account_count,
            self.balance.logical_values(),
            self.generated_today.logical_values(),
            self.generated_week.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ClientMultiAccountReadModel:
    read_model_id: ClientReadModelId
    client_id: ClientId
    today_window: ClientPerformanceWindow
    week_window: ClientPerformanceWindow
    accounts: tuple[ClientAccountReadSnapshot, ...]
    currency_summaries: tuple[ClientCurrencySummary, ...]
    generated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.read_model_id, ClientReadModelId):
            raise ClientMultiAccountReadModelValidationError(
                "read model id must be ClientReadModelId"
            )
        if not isinstance(self.client_id, ClientId):
            raise ClientMultiAccountReadModelValidationError(
                "read model client_id must be ClientId"
            )
        if not isinstance(self.today_window, ClientPerformanceWindow) or not isinstance(
            self.week_window, ClientPerformanceWindow
        ):
            raise ClientMultiAccountReadModelValidationError(
                "read model requires explicit today/week windows"
            )
        _validate_timestamp(self.generated_at, field_name="read model generated_at")
        if self.today_window.ended_at != self.generated_at:
            raise ClientMultiAccountReadModelValidationError(
                "today window must end at generated_at"
            )
        if self.week_window.ended_at != self.generated_at:
            raise ClientMultiAccountReadModelValidationError(
                "week window must end at generated_at"
            )
        account_ids = [account.account_id for account in self.accounts]
        if len(account_ids) != len(set(account_ids)):
            raise ClientMultiAccountReadModelValidationError(
                "read model accounts must be unique"
            )
        if any(account.client_id != self.client_id for account in self.accounts):
            raise ClientMultiAccountReadModelValidationError(
                "read model accounts must belong to exact client"
            )
        if any(account.captured_at > self.generated_at for account in self.accounts):
            raise ClientMultiAccountReadModelValidationError(
                "account snapshot cannot be newer than read model"
            )
        expected = _summaries_for(self.accounts)
        if self.currency_summaries != expected:
            raise ClientMultiAccountReadModelValidationError(
                "currency summaries must equal deterministic account aggregation"
            )
        object.__setattr__(
            self,
            "accounts",
            tuple(sorted(self.accounts, key=lambda account: str(account.account_id.value))),
        )

    @property
    def trade_pulses(self) -> tuple[ClientTradePulse, ...]:
        return tuple(
            sorted(
                (
                    pulse
                    for account in self.accounts
                    for pulse in account.trade_pulses
                ),
                key=lambda pulse: (
                    pulse.occurred_at,
                    str(pulse.account_id.value),
                    str(pulse.position_id.value),
                ),
                reverse=True,
            )
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.read_model_id.logical_values(),
            self.client_id.logical_values(),
            self.today_window.logical_values(),
            self.week_window.logical_values(),
            tuple(account.logical_values() for account in self.accounts),
            tuple(summary.logical_values() for summary in self.currency_summaries),
            self.generated_at.isoformat(),
        )


def _summaries_for(
    accounts: tuple[ClientAccountReadSnapshot, ...],
) -> tuple[ClientCurrencySummary, ...]:
    currencies = sorted({account.currency for account in accounts}, key=lambda item: item.value)
    summaries: list[ClientCurrencySummary] = []
    for currency in currencies:
        selected = tuple(account for account in accounts if account.currency == currency)
        balance = sum((account.balance.amount for account in selected), start=0)
        today = sum((account.generated_today.amount for account in selected), start=0)
        week = sum((account.generated_week.amount for account in selected), start=0)
        summaries.append(
            ClientCurrencySummary(
                currency=currency,
                account_count=len(selected),
                balance=MoneyAmount(currency=currency, amount=balance),
                generated_today=MoneyAmount(currency=currency, amount=today),
                generated_week=MoneyAmount(currency=currency, amount=week),
            )
        )
    return tuple(summaries)


def build_client_multiaccount_read_model(
    *,
    read_model_id: ClientReadModelId,
    client_id: ClientId,
    today_window: ClientPerformanceWindow,
    week_window: ClientPerformanceWindow,
    accounts: tuple[ClientAccountReadSnapshot, ...],
    generated_at: datetime,
) -> ClientMultiAccountReadModel:
    """Build deterministic presentation-only aggregate without cross-currency mixing."""

    ordered_accounts = tuple(
        sorted(accounts, key=lambda account: str(account.account_id.value))
    )
    return ClientMultiAccountReadModel(
        read_model_id=read_model_id,
        client_id=client_id,
        today_window=today_window,
        week_window=week_window,
        accounts=ordered_accounts,
        currency_summaries=_summaries_for(ordered_accounts),
        generated_at=generated_at,
    )
