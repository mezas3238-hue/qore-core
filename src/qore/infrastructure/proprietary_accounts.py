from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import Protocol
from uuid import UUID

from qore.infrastructure.ports import (
    ExternalPort,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.kernel.result import Result


class ProprietaryAccountError(ExternalPortError):
    """Base error for canonical CEO proprietary-account boundaries."""

    __slots__ = ()


class ProprietaryAccountValidationError(ProprietaryAccountError):
    """Violation of a provider-neutral proprietary-account invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ProprietaryAccountValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProprietaryAccountValidationError(f"{field_name} must be timezone-aware")


def _validate_source(source: ExternalSourceDescriptor, *, field_name: str) -> None:
    if not isinstance(source, ExternalSourceDescriptor):
        raise ProprietaryAccountValidationError(
            f"{field_name} source must be ExternalSourceDescriptor"
        )
    name = source.port_name.value
    if name != "proprietary-account" and not name.startswith("proprietary-account."):
        raise ProprietaryAccountValidationError(
            f"{field_name} source port must use the proprietary-account namespace"
        )


def _validate_same_currency(
    values: tuple[MoneyAmount, ...],
    *,
    field_name: str,
) -> None:
    currencies = {item.currency.value for item in values}
    if len(currencies) != 1:
        raise ProprietaryAccountValidationError(
            f"{field_name} money values must use one canonical currency"
        )


@dataclass(frozen=True, slots=True)
class ProprietaryAccountId:
    """Opaque QORE identity for one CEO-controlled account.

    This is deliberately not a broker account number or provider credential.
    """

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ProprietaryAccountValidationError(
                "proprietary account id must be a UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ProprietaryAccountSnapshotId:
    """Explicit identity of one immutable proprietary-account snapshot."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ProprietaryAccountValidationError(
                "proprietary account snapshot id must be a UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CurrencyCode:
    """Canonical three-letter currency code used by financial snapshots."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[A-Z]{3}", self.value) is None:
            raise ProprietaryAccountValidationError(
                "currency code must contain exactly three uppercase ASCII letters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class MoneyAmount:
    """Finite decimal monetary value with explicit currency."""

    currency: CurrencyCode
    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.currency, CurrencyCode):
            raise ProprietaryAccountValidationError(
                "money currency must be CurrencyCode"
            )
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise ProprietaryAccountValidationError(
                "money amount must be a finite Decimal"
            )
        normalized = Decimal(0) if self.amount == 0 else self.amount.normalize()
        object.__setattr__(self, "amount", normalized)

    def logical_values(self) -> tuple[str, ...]:
        return (self.currency.value, format(self.amount, "f"))


@dataclass(frozen=True, slots=True)
class DrawdownBps:
    """Drawdown ratio expressed as an integer in basis points."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 0 <= self.value <= 10_000:
            raise ProprietaryAccountValidationError(
                "drawdown basis points must be an integer between 0 and 10000"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


class ProprietaryAccountEnvironment(StrEnum):
    PRACTICE = "practice"
    DEMO = "demo"
    PRODUCTION = "production"
    UNKNOWN = "unknown"


class ProprietaryAccountOperationalState(StrEnum):
    ACTIVE = "active"
    RESTRICTED = "restricted"
    PAUSED = "paused"
    CLOSED = "closed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProprietaryAccountFinancialSnapshot:
    """Canonical provider-neutral financial state for one CEO proprietary account."""

    snapshot_id: ProprietaryAccountSnapshotId
    account_id: ProprietaryAccountId
    source: ExternalSourceDescriptor
    observed_at: datetime
    environment: ProprietaryAccountEnvironment
    state: ProprietaryAccountOperationalState
    balance: MoneyAmount
    equity: MoneyAmount
    unrealized_pnl: MoneyAmount
    margin_used: MoneyAmount
    drawdown: DrawdownBps

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, ProprietaryAccountSnapshotId):
            raise ProprietaryAccountValidationError(
                "financial snapshot_id must be ProprietaryAccountSnapshotId"
            )
        if not isinstance(self.account_id, ProprietaryAccountId):
            raise ProprietaryAccountValidationError(
                "financial account_id must be ProprietaryAccountId"
            )
        if self.snapshot_id.value == self.account_id.value:
            raise ProprietaryAccountValidationError(
                "financial snapshot and account identities must differ"
            )
        _validate_source(self.source, field_name="financial snapshot")
        _validate_timestamp(self.observed_at, field_name="financial observed_at")
        if not isinstance(self.environment, ProprietaryAccountEnvironment):
            raise ProprietaryAccountValidationError(
                "financial environment must be ProprietaryAccountEnvironment"
            )
        if not isinstance(self.state, ProprietaryAccountOperationalState):
            raise ProprietaryAccountValidationError(
                "financial state must be ProprietaryAccountOperationalState"
            )
        values = (self.balance, self.equity, self.unrealized_pnl, self.margin_used)
        if any(not isinstance(item, MoneyAmount) for item in values):
            raise ProprietaryAccountValidationError(
                "financial monetary fields must contain only MoneyAmount values"
            )
        _validate_same_currency(values, field_name="financial snapshot")
        if self.balance.amount < 0:
            raise ProprietaryAccountValidationError(
                "financial balance must not be negative"
            )
        if self.equity.amount < 0:
            raise ProprietaryAccountValidationError(
                "financial equity must not be negative"
            )
        if self.margin_used.amount < 0:
            raise ProprietaryAccountValidationError(
                "financial margin_used must not be negative"
            )
        if not isinstance(self.drawdown, DrawdownBps):
            raise ProprietaryAccountValidationError(
                "financial drawdown must be DrawdownBps"
            )

    @property
    def currency(self) -> CurrencyCode:
        return self.balance.currency

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.account_id.logical_values(),
            self.source.logical_values(),
            self.observed_at.isoformat(),
            self.environment.value,
            self.state.value,
            self.balance.logical_values(),
            self.equity.logical_values(),
            self.unrealized_pnl.logical_values(),
            self.margin_used.logical_values(),
            self.drawdown.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ProprietaryAccountPerformanceSnapshot:
    """Canonical realized performance over one explicit closed time window."""

    snapshot_id: ProprietaryAccountSnapshotId
    account_id: ProprietaryAccountId
    source: ExternalSourceDescriptor
    observed_at: datetime
    period_start: datetime
    period_end: datetime
    realized_pnl: MoneyAmount

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, ProprietaryAccountSnapshotId):
            raise ProprietaryAccountValidationError(
                "performance snapshot_id must be ProprietaryAccountSnapshotId"
            )
        if not isinstance(self.account_id, ProprietaryAccountId):
            raise ProprietaryAccountValidationError(
                "performance account_id must be ProprietaryAccountId"
            )
        if self.snapshot_id.value == self.account_id.value:
            raise ProprietaryAccountValidationError(
                "performance snapshot and account identities must differ"
            )
        _validate_source(self.source, field_name="performance snapshot")
        _validate_timestamp(self.observed_at, field_name="performance observed_at")
        _validate_timestamp(self.period_start, field_name="performance period_start")
        _validate_timestamp(self.period_end, field_name="performance period_end")
        if self.period_end <= self.period_start:
            raise ProprietaryAccountValidationError(
                "performance period_end must be after period_start"
            )
        if self.observed_at < self.period_end:
            raise ProprietaryAccountValidationError(
                "performance observed_at must not predate period_end"
            )
        if not isinstance(self.realized_pnl, MoneyAmount):
            raise ProprietaryAccountValidationError(
                "performance realized_pnl must be MoneyAmount"
            )

    @property
    def currency(self) -> CurrencyCode:
        return self.realized_pnl.currency

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.account_id.logical_values(),
            self.source.logical_values(),
            self.observed_at.isoformat(),
            self.period_start.isoformat(),
            self.period_end.isoformat(),
            self.realized_pnl.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ProprietaryAccountSnapshotRequest:
    """Provider-neutral request for current financial state of one opaque account."""

    account_id: ProprietaryAccountId

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, ProprietaryAccountId):
            raise ProprietaryAccountValidationError(
                "financial request account_id must be ProprietaryAccountId"
            )


@dataclass(frozen=True, slots=True)
class ProprietaryAccountPerformanceRequest:
    """Provider-neutral request for realized performance over an explicit window."""

    account_id: ProprietaryAccountId
    period_start: datetime
    period_end: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, ProprietaryAccountId):
            raise ProprietaryAccountValidationError(
                "performance request account_id must be ProprietaryAccountId"
            )
        _validate_timestamp(self.period_start, field_name="performance request period_start")
        _validate_timestamp(self.period_end, field_name="performance request period_end")
        if self.period_end <= self.period_start:
            raise ProprietaryAccountValidationError(
                "performance request period_end must be after period_start"
            )


class ProprietaryAccountReadPort(ExternalPort, Protocol):
    """Provider-neutral read boundary for CEO proprietary-account financial state."""

    def read_financial_snapshot(
        self,
        request: ProprietaryAccountSnapshotRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ProprietaryAccountFinancialSnapshot, ExternalPortError]:
        """Read current normalized financial state without exposing provider credentials."""
        ...

    def read_performance_snapshot(
        self,
        request: ProprietaryAccountPerformanceRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ProprietaryAccountPerformanceSnapshot, ExternalPortError]:
        """Read normalized realized performance over the explicitly requested window."""
        ...
