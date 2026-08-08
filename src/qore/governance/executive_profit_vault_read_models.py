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
    ExecutivePolicyVersionRef,
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
class ExecutiveVaultLedgerRef:
    """Opaque corporate ledger identity; never a client or broker account number."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "executive vault ledger ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveVaultSettlementPeriodRef:
    """Explicit identity of one Vault settlement period."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "executive vault settlement period ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveVaultCurrencyCode:
    """Currency code local to the Corporate Profit Vault executive surface."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[A-Z]{3}", self.value) is None:
            raise ExecutiveReadModelValidationError(
                "vault currency code must contain exactly three uppercase ASCII letters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveVaultMoneyAmount:
    """Finite Decimal amount isolated from CEO proprietary financial value objects."""

    currency: ExecutiveVaultCurrencyCode
    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.currency, ExecutiveVaultCurrencyCode):
            raise ExecutiveReadModelValidationError(
                "vault money currency must be ExecutiveVaultCurrencyCode"
            )
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise ExecutiveReadModelValidationError(
                "vault money amount must be a finite Decimal"
            )
        normalized = Decimal(0) if self.amount == 0 else self.amount.normalize()
        object.__setattr__(self, "amount", normalized)

    def logical_values(self) -> tuple[str, ...]:
        return (self.currency.value, format(self.amount, "f"))


@dataclass(frozen=True, slots=True)
class ExecutiveVaultProfitShareRateBps:
    """Explicit policy-projected profit-share rate in basis points."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or not 0 <= self.value <= 10_000:
            raise ExecutiveReadModelValidationError(
                "vault profit-share rate must be an integer between 0 and 10000 basis points"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


class ExecutiveVaultAccountPhase(StrEnum):
    EVALUATION = "evaluation"
    VERIFICATION = "verification"
    REWARD_ELIGIBLE = "reward-eligible"
    PAYOUT_ELIGIBLE = "payout-eligible"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class ExecutiveVaultSettlementState(StrEnum):
    OPEN = "open"
    CALCULATING = "calculating"
    READY = "ready"
    DUE = "due"
    PAID = "paid"
    PAST_DUE = "past-due"
    DISPUTED = "disputed"
    CORRECTED = "corrected"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class ExecutiveVaultEntitlementState(StrEnum):
    ACTIVE = "active"
    PAYMENT_DUE = "payment-due"
    GRACE = "grace"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REACTIVATED = "reactivated"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveVaultLedgerSummary:
    """Per-ledger corporate economics without client identity or trading state."""

    ledger_ref: ExecutiveVaultLedgerRef
    settlement_period_ref: ExecutiveVaultSettlementPeriodRef
    period_start: datetime
    period_end: datetime
    phase: ExecutiveVaultAccountPhase
    settlement_state: ExecutiveVaultSettlementState
    entitlement_state: ExecutiveVaultEntitlementState
    policy_version: ExecutivePolicyVersionRef
    positive_realized: ExecutiveVaultMoneyAmount
    negative_realized: ExecutiveVaultMoneyAmount
    net_realized: ExecutiveVaultMoneyAmount
    carryforward_balance: ExecutiveVaultMoneyAmount
    eligible_positive_base: ExecutiveVaultMoneyAmount
    profit_share_rate: ExecutiveVaultProfitShareRateBps
    amount_due: ExecutiveVaultMoneyAmount
    amount_paid: ExecutiveVaultMoneyAmount
    outstanding: ExecutiveVaultMoneyAmount
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.ledger_ref, ExecutiveVaultLedgerRef):
            raise ExecutiveReadModelValidationError(
                "vault ledger summary requires ExecutiveVaultLedgerRef"
            )
        if not isinstance(self.settlement_period_ref, ExecutiveVaultSettlementPeriodRef):
            raise ExecutiveReadModelValidationError(
                "vault ledger summary requires ExecutiveVaultSettlementPeriodRef"
            )
        if self.ledger_ref.value == self.settlement_period_ref.value:
            raise ExecutiveReadModelValidationError(
                "vault ledger and settlement period identities must differ"
            )
        _validate_timestamp(self.period_start, field_name="vault period_start")
        _validate_timestamp(self.period_end, field_name="vault period_end")
        if self.period_end <= self.period_start:
            raise ExecutiveReadModelValidationError(
                "vault period_end must be after period_start"
            )
        if not isinstance(self.phase, ExecutiveVaultAccountPhase):
            raise ExecutiveReadModelValidationError(
                "vault ledger phase must be ExecutiveVaultAccountPhase"
            )
        if not isinstance(self.settlement_state, ExecutiveVaultSettlementState):
            raise ExecutiveReadModelValidationError(
                "vault settlement state must be ExecutiveVaultSettlementState"
            )
        if not isinstance(self.entitlement_state, ExecutiveVaultEntitlementState):
            raise ExecutiveReadModelValidationError(
                "vault entitlement state must be ExecutiveVaultEntitlementState"
            )
        if not isinstance(self.policy_version, ExecutivePolicyVersionRef):
            raise ExecutiveReadModelValidationError(
                "vault ledger policy_version must be ExecutivePolicyVersionRef"
            )
        money_values = (
            self.positive_realized,
            self.negative_realized,
            self.net_realized,
            self.carryforward_balance,
            self.eligible_positive_base,
            self.amount_due,
            self.amount_paid,
            self.outstanding,
        )
        if any(not isinstance(item, ExecutiveVaultMoneyAmount) for item in money_values):
            raise ExecutiveReadModelValidationError(
                "vault ledger monetary fields must be ExecutiveVaultMoneyAmount"
            )
        currencies = {item.currency.value for item in money_values}
        if len(currencies) != 1:
            raise ExecutiveReadModelValidationError(
                "vault ledger monetary fields must use one currency"
            )
        if self.positive_realized.amount < 0:
            raise ExecutiveReadModelValidationError(
                "vault positive_realized must not be negative"
            )
        if self.negative_realized.amount > 0:
            raise ExecutiveReadModelValidationError(
                "vault negative_realized must not be positive"
            )
        if self.net_realized.amount != (
            self.positive_realized.amount + self.negative_realized.amount
        ):
            raise ExecutiveReadModelValidationError(
                "vault net_realized must equal positive_realized plus negative_realized"
            )
        if self.eligible_positive_base.amount < 0:
            raise ExecutiveReadModelValidationError(
                "vault eligible_positive_base must not be negative"
            )
        if any(
            item.amount < 0
            for item in (self.amount_due, self.amount_paid, self.outstanding)
        ):
            raise ExecutiveReadModelValidationError(
                "vault due, paid, and outstanding amounts must not be negative"
            )
        if not isinstance(self.profit_share_rate, ExecutiveVaultProfitShareRateBps):
            raise ExecutiveReadModelValidationError(
                "vault ledger profit_share_rate must be ExecutiveVaultProfitShareRateBps"
            )
        if self.net_realized.amount <= 0 and self.amount_due.amount != 0:
            raise ExecutiveReadModelValidationError(
                "vault non-positive net realized result must have zero amount_due"
            )
        if self.phase in {
            ExecutiveVaultAccountPhase.EVALUATION,
            ExecutiveVaultAccountPhase.VERIFICATION,
        } and self.amount_due.amount != 0:
            raise ExecutiveReadModelValidationError(
                "vault evaluation and verification phases must have zero amount_due"
            )
        if self.amount_due.amount > 0 and (
            self.eligible_positive_base.amount <= 0 or self.profit_share_rate.value <= 0
        ):
            raise ExecutiveReadModelValidationError(
                "vault positive amount_due requires positive eligible base and rate"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="vault ledger evidence refs",
            ),
        )

    @property
    def currency(self) -> ExecutiveVaultCurrencyCode:
        return self.net_realized.currency

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.ledger_ref.logical_values(),
            self.settlement_period_ref.logical_values(),
            self.period_start.isoformat(),
            self.period_end.isoformat(),
            self.phase.value,
            self.settlement_state.value,
            self.entitlement_state.value,
            self.policy_version.logical_values(),
            self.positive_realized.logical_values(),
            self.negative_realized.logical_values(),
            self.net_realized.logical_values(),
            self.carryforward_balance.logical_values(),
            self.eligible_positive_base.logical_values(),
            self.profit_share_rate.logical_values(),
            self.amount_due.logical_values(),
            self.amount_paid.logical_values(),
            self.outstanding.logical_values(),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveVaultLedgerCounts:
    """Current ledger result classifications for the corporate read snapshot."""

    total: int
    positive: int
    negative: int
    break_even: int

    def __post_init__(self) -> None:
        values = (self.total, self.positive, self.negative, self.break_even)
        if any(type(value) is not int or value < 0 for value in values):
            raise ExecutiveReadModelValidationError(
                "vault ledger counts must be non-negative integers"
            )
        if self.positive + self.negative + self.break_even != self.total:
            raise ExecutiveReadModelValidationError(
                "vault ledger result counts must sum to total"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.total, self.positive, self.negative, self.break_even)


@dataclass(frozen=True, slots=True)
class ExecutiveVaultCurrencySummary:
    """Corporate aggregate economics for one currency, never cross-currency converted."""

    currency: ExecutiveVaultCurrencyCode
    positive_realized_total: ExecutiveVaultMoneyAmount
    negative_realized_total: ExecutiveVaultMoneyAmount
    eligible_positive_base: ExecutiveVaultMoneyAmount
    receivable: ExecutiveVaultMoneyAmount
    collected: ExecutiveVaultMoneyAmount
    outstanding: ExecutiveVaultMoneyAmount
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.currency, ExecutiveVaultCurrencyCode):
            raise ExecutiveReadModelValidationError(
                "vault currency summary requires ExecutiveVaultCurrencyCode"
            )
        money_values = (
            self.positive_realized_total,
            self.negative_realized_total,
            self.eligible_positive_base,
            self.receivable,
            self.collected,
            self.outstanding,
        )
        if any(not isinstance(item, ExecutiveVaultMoneyAmount) for item in money_values):
            raise ExecutiveReadModelValidationError(
                "vault currency summary fields must be ExecutiveVaultMoneyAmount"
            )
        if any(item.currency != self.currency for item in money_values):
            raise ExecutiveReadModelValidationError(
                "vault currency summary amounts must match summary currency"
            )
        if self.positive_realized_total.amount < 0:
            raise ExecutiveReadModelValidationError(
                "vault positive realized aggregate must not be negative"
            )
        if self.negative_realized_total.amount > 0:
            raise ExecutiveReadModelValidationError(
                "vault negative realized aggregate must not be positive"
            )
        if any(
            item.amount < 0
            for item in (
                self.eligible_positive_base,
                self.receivable,
                self.collected,
                self.outstanding,
            )
        ):
            raise ExecutiveReadModelValidationError(
                "vault eligible/receivable/collected/outstanding aggregates must not be negative"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="vault currency summary evidence refs",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.currency.logical_values(),
            self.positive_realized_total.logical_values(),
            self.negative_realized_total.logical_values(),
            self.eligible_positive_base.logical_values(),
            self.receivable.logical_values(),
            self.collected.logical_values(),
            self.outstanding.logical_values(),
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveCorporateProfitVaultReadModel:
    """Isolated CORPORATE_PROFIT_VAULT read model for the CEO Command Center."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    ledger_counts: ExecutiveVaultLedgerCounts
    currency_summaries: tuple[ExecutiveVaultCurrencySummary, ...]
    ledgers: tuple[ExecutiveVaultLedgerSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "corporate Profit Vault read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.CORPORATE_PROFIT_VAULT:
            raise ExecutiveReadModelValidationError(
                "corporate Profit Vault projection requires CORPORATE_PROFIT_VAULT scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "corporate Profit Vault projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.ledger_counts, ExecutiveVaultLedgerCounts):
            raise ExecutiveReadModelValidationError(
                "corporate Profit Vault projection requires ExecutiveVaultLedgerCounts"
            )
        if not isinstance(self.currency_summaries, tuple) or any(
            not isinstance(item, ExecutiveVaultCurrencySummary)
            for item in self.currency_summaries
        ):
            raise ExecutiveReadModelValidationError(
                "vault currency summaries must be an immutable tuple"
            )
        currency_codes = tuple(item.currency.value for item in self.currency_summaries)
        if len(set(currency_codes)) != len(currency_codes):
            raise ExecutiveReadModelValidationError(
                "vault projection must not contain duplicate currency summaries"
            )
        object.__setattr__(
            self,
            "currency_summaries",
            tuple(sorted(self.currency_summaries, key=lambda item: item.currency.value)),
        )
        if not isinstance(self.ledgers, tuple) or any(
            not isinstance(item, ExecutiveVaultLedgerSummary) for item in self.ledgers
        ):
            raise ExecutiveReadModelValidationError(
                "vault ledgers must be an immutable tuple of ExecutiveVaultLedgerSummary"
            )
        ledger_ids = tuple(item.ledger_ref.value for item in self.ledgers)
        if len(set(ledger_ids)) != len(ledger_ids):
            raise ExecutiveReadModelValidationError(
                "vault projection must not contain duplicate ledger refs"
            )
        object.__setattr__(
            self,
            "ledgers",
            tuple(sorted(self.ledgers, key=lambda item: str(item.ledger_ref.value))),
        )
        positive = sum(item.net_realized.amount > 0 for item in self.ledgers)
        negative = sum(item.net_realized.amount < 0 for item in self.ledgers)
        break_even = sum(item.net_realized.amount == 0 for item in self.ledgers)
        expected_counts = ExecutiveVaultLedgerCounts(
            total=len(self.ledgers),
            positive=positive,
            negative=negative,
            break_even=break_even,
        )
        if self.ledger_counts != expected_counts:
            raise ExecutiveReadModelValidationError(
                "vault ledger counts must match the included ledger summaries"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            self.ledger_counts.logical_values(),
            tuple(item.logical_values() for item in self.currency_summaries),
            tuple(item.logical_values() for item in self.ledgers),
        )
