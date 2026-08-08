from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionMetadata,
    ExecutiveReadModelValidationError,
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveReadModelValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveReadModelValidationError(f"{field_name} must be timezone-aware")


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or not values or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be a non-empty immutable tuple of ExecutiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutiveCurrencyCode:
    """Stable currency code in the executive projection surface."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[A-Z]{3}", self.value) is None:
            raise ExecutiveReadModelValidationError(
                "executive currency code must contain exactly three uppercase ASCII letters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveMoneyAmount:
    """Executive-safe decimal monetary projection with explicit currency."""

    currency: ExecutiveCurrencyCode
    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.currency, ExecutiveCurrencyCode):
            raise ExecutiveReadModelValidationError(
                "executive money currency must be ExecutiveCurrencyCode"
            )
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise ExecutiveReadModelValidationError(
                "executive money amount must be a finite Decimal"
            )
        normalized = Decimal(0) if self.amount == 0 else self.amount.normalize()
        object.__setattr__(self, "amount", normalized)

    def logical_values(self) -> tuple[str, ...]:
        return (self.currency.value, format(self.amount, "f"))


@dataclass(frozen=True, slots=True)
class ExecutiveDrawdownBps:
    """Executive drawdown ratio in integer basis points."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 0 <= self.value <= 10_000:
            raise ExecutiveReadModelValidationError(
                "executive drawdown must be an integer between 0 and 10000 basis points"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveProprietaryAccountRef:
    """Opaque account identity in the executive surface; never a broker account number."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "executive proprietary account ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class ExecutiveAccountEnvironment(StrEnum):
    PRACTICE = "practice"
    DEMO = "demo"
    PRODUCTION = "production"
    UNKNOWN = "unknown"


class ExecutiveAccountOperationalState(StrEnum):
    ACTIVE = "active"
    RESTRICTED = "restricted"
    PAUSED = "paused"
    CLOSED = "closed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveRealizedPerformanceSummary:
    """Realized PnL over one explicit executive reporting window."""

    period_start: datetime
    period_end: datetime
    observed_at: datetime
    realized_pnl: ExecutiveMoneyAmount
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        _validate_timestamp(self.period_start, field_name="performance period_start")
        _validate_timestamp(self.period_end, field_name="performance period_end")
        _validate_timestamp(self.observed_at, field_name="performance observed_at")
        if self.period_end <= self.period_start:
            raise ExecutiveReadModelValidationError(
                "performance period_end must be after period_start"
            )
        if self.observed_at < self.period_end:
            raise ExecutiveReadModelValidationError(
                "performance observed_at must not predate period_end"
            )
        if not isinstance(self.realized_pnl, ExecutiveMoneyAmount):
            raise ExecutiveReadModelValidationError(
                "performance realized_pnl must be ExecutiveMoneyAmount"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="performance evidence refs",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.period_start.isoformat(),
            self.period_end.isoformat(),
            self.observed_at.isoformat(),
            self.realized_pnl.logical_values(),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveCeoAccountSummary:
    """Stable CEO-account projection built from normalized proprietary snapshots."""

    account_ref: ExecutiveProprietaryAccountRef
    source_observed_at: datetime
    environment: ExecutiveAccountEnvironment
    state: ExecutiveAccountOperationalState
    balance: ExecutiveMoneyAmount
    equity: ExecutiveMoneyAmount
    unrealized_pnl: ExecutiveMoneyAmount
    margin_used: ExecutiveMoneyAmount
    drawdown: ExecutiveDrawdownBps
    realized_performance: tuple[ExecutiveRealizedPerformanceSummary, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.account_ref, ExecutiveProprietaryAccountRef):
            raise ExecutiveReadModelValidationError(
                "CEO account summary requires ExecutiveProprietaryAccountRef"
            )
        _validate_timestamp(self.source_observed_at, field_name="account source_observed_at")
        if not isinstance(self.environment, ExecutiveAccountEnvironment):
            raise ExecutiveReadModelValidationError(
                "CEO account environment must be ExecutiveAccountEnvironment"
            )
        if not isinstance(self.state, ExecutiveAccountOperationalState):
            raise ExecutiveReadModelValidationError(
                "CEO account state must be ExecutiveAccountOperationalState"
            )
        current_values = (self.balance, self.equity, self.unrealized_pnl, self.margin_used)
        if any(not isinstance(item, ExecutiveMoneyAmount) for item in current_values):
            raise ExecutiveReadModelValidationError(
                "CEO account current money fields must be ExecutiveMoneyAmount"
            )
        currencies = {item.currency.value for item in current_values}
        if len(currencies) != 1:
            raise ExecutiveReadModelValidationError(
                "CEO account current money fields must use one currency"
            )
        if self.balance.amount < 0 or self.equity.amount < 0 or self.margin_used.amount < 0:
            raise ExecutiveReadModelValidationError(
                "CEO account balance, equity, and margin_used must not be negative"
            )
        if not isinstance(self.drawdown, ExecutiveDrawdownBps):
            raise ExecutiveReadModelValidationError(
                "CEO account drawdown must be ExecutiveDrawdownBps"
            )
        if not isinstance(self.realized_performance, tuple) or any(
            not isinstance(item, ExecutiveRealizedPerformanceSummary)
            for item in self.realized_performance
        ):
            raise ExecutiveReadModelValidationError(
                "realized performance must be an immutable tuple of summaries"
            )
        currency = self.balance.currency.value
        if any(item.realized_pnl.currency.value != currency for item in self.realized_performance):
            raise ExecutiveReadModelValidationError(
                "realized performance currency must match account currency"
            )
        windows = tuple(
            (item.period_start, item.period_end) for item in self.realized_performance
        )
        if len(set(windows)) != len(windows):
            raise ExecutiveReadModelValidationError(
                "realized performance windows must not contain duplicates"
            )
        object.__setattr__(
            self,
            "realized_performance",
            tuple(
                sorted(
                    self.realized_performance,
                    key=lambda item: (item.period_start, item.period_end),
                )
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="CEO account evidence refs",
            ),
        )

    @property
    def currency(self) -> ExecutiveCurrencyCode:
        return self.balance.currency

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_ref.logical_values(),
            self.source_observed_at.isoformat(),
            self.environment.value,
            self.state.value,
            self.balance.logical_values(),
            self.equity.logical_values(),
            self.unrealized_pnl.logical_values(),
            self.margin_used.logical_values(),
            self.drawdown.logical_values(),
            tuple(item.logical_values() for item in self.realized_performance),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveCeoAccountsReadModel:
    """Stable CEO_ACCOUNTS projection; proprietary accounts only."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    accounts: tuple[ExecutiveCeoAccountSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "CEO accounts read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.CEO_ACCOUNTS:
            raise ExecutiveReadModelValidationError(
                "CEO accounts projection requires CEO_ACCOUNTS scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "CEO accounts projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.accounts, tuple) or any(
            not isinstance(item, ExecutiveCeoAccountSummary) for item in self.accounts
        ):
            raise ExecutiveReadModelValidationError(
                "CEO accounts must be an immutable tuple of summaries"
            )
        account_ids = tuple(item.account_ref.value for item in self.accounts)
        if len(set(account_ids)) != len(account_ids):
            raise ExecutiveReadModelValidationError(
                "CEO accounts projection must not contain duplicate account refs"
            )
        object.__setattr__(
            self,
            "accounts",
            tuple(sorted(self.accounts, key=lambda item: str(item.account_ref.value))),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.accounts),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveCapitalCurrencySummary:
    """Currency-isolated proprietary capital totals without implicit FX conversion."""

    currency: ExecutiveCurrencyCode
    account_count: int
    total_balance: ExecutiveMoneyAmount
    total_equity: ExecutiveMoneyAmount
    total_unrealized_pnl: ExecutiveMoneyAmount
    total_margin_used: ExecutiveMoneyAmount
    worst_account_drawdown: ExecutiveDrawdownBps

    def __post_init__(self) -> None:
        if not isinstance(self.currency, ExecutiveCurrencyCode):
            raise ExecutiveReadModelValidationError(
                "capital summary currency must be ExecutiveCurrencyCode"
            )
        if type(self.account_count) is not int or self.account_count <= 0:
            raise ExecutiveReadModelValidationError(
                "capital summary account_count must be a positive integer"
            )
        values = (
            self.total_balance,
            self.total_equity,
            self.total_unrealized_pnl,
            self.total_margin_used,
        )
        if any(not isinstance(item, ExecutiveMoneyAmount) for item in values):
            raise ExecutiveReadModelValidationError(
                "capital summary money fields must be ExecutiveMoneyAmount"
            )
        if any(item.currency != self.currency for item in values):
            raise ExecutiveReadModelValidationError(
                "capital summary money fields must match summary currency"
            )
        if (
            self.total_balance.amount < 0
            or self.total_equity.amount < 0
            or self.total_margin_used.amount < 0
        ):
            raise ExecutiveReadModelValidationError(
                "capital balance, equity, and margin totals must not be negative"
            )
        if not isinstance(self.worst_account_drawdown, ExecutiveDrawdownBps):
            raise ExecutiveReadModelValidationError(
                "capital worst drawdown must be ExecutiveDrawdownBps"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.currency.logical_values(),
            self.account_count,
            self.total_balance.logical_values(),
            self.total_equity.logical_values(),
            self.total_unrealized_pnl.logical_values(),
            self.total_margin_used.logical_values(),
            self.worst_account_drawdown.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveCapitalStateReadModel:
    """Stable CAPITAL_STATE projection grouped by currency."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    currencies: tuple[ExecutiveCapitalCurrencySummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "capital state read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.CAPITAL_STATE:
            raise ExecutiveReadModelValidationError(
                "capital state projection requires CAPITAL_STATE scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "capital state projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.currencies, tuple) or any(
            not isinstance(item, ExecutiveCapitalCurrencySummary)
            for item in self.currencies
        ):
            raise ExecutiveReadModelValidationError(
                "capital currencies must be an immutable tuple of summaries"
            )
        currency_codes = tuple(item.currency.value for item in self.currencies)
        if len(set(currency_codes)) != len(currency_codes):
            raise ExecutiveReadModelValidationError(
                "capital state must not contain duplicate currency summaries"
            )
        object.__setattr__(
            self,
            "currencies",
            tuple(sorted(self.currencies, key=lambda item: item.currency.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.currencies),
        )
