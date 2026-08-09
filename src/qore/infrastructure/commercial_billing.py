from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import ClientId, TradingAccountId
from qore.infrastructure.client_performance_ledger import (
    ClientPerformanceRecordId,
    EligibleClientPaidProfitRecord,
)
from qore.infrastructure.client_trial_licensing import CommercialPaymentStanding
from qore.infrastructure.commercial_products import (
    CommercialBillingUnit,
    CommercialPlan,
    CommercialPlanId,
    CommercialPlanVersion,
    CommercialProductKind,
)
from qore.infrastructure.proprietary_accounts import CurrencyCode, MoneyAmount
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_PERFORMANCE_FEE_BPS = 2000
_BPS_DENOMINATOR = Decimal(10_000)


class CommercialBillingError(InfrastructureError):
    """Base error for QORE commercial billing/payment contracts."""

    __slots__ = ()


class CommercialBillingValidationError(CommercialBillingError):
    """Violation of a commercial billing/payment invariant."""

    __slots__ = ()


class CommercialBillingConflictError(CommercialBillingError):
    """A billing/payment append conflicts with existing evidence."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise CommercialBillingValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CommercialBillingValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CommercialBillingValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class CommercialInvoiceId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commercial invoice id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CommercialPaymentId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commercial payment id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CommercialPaymentAllocationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commercial payment allocation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CommercialPaymentEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commercial payment evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CommercialBillingEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="commercial billing evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class PerformanceFeePolicyId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="performance fee policy id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class PerformanceFeePolicyVersion:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise CommercialBillingValidationError(
                "performance fee policy version must be positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


class CommercialInvoiceStatus(StrEnum):
    DUE = "due"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"


class CommercialPaymentVerification(StrEnum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class CommercialBillingStandingState(StrEnum):
    CURRENT = "current"
    PAYMENT_FAILED = "payment_failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CommercialInvoice:
    """Immutable amount due under one exact product plan version."""

    invoice_id: CommercialInvoiceId
    client_id: ClientId
    account_id: TradingAccountId | None
    plan_id: CommercialPlanId
    plan_version: CommercialPlanVersion
    product_kind: CommercialProductKind
    billing_unit: CommercialBillingUnit
    amount: MoneyAmount
    period_started_at: datetime
    period_ended_at: datetime
    issued_at: datetime
    due_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.invoice_id, CommercialInvoiceId):
            raise CommercialBillingValidationError(
                "invoice_id must be CommercialInvoiceId"
            )
        if not isinstance(self.client_id, ClientId):
            raise CommercialBillingValidationError("invoice client_id must be ClientId")
        if self.account_id is not None and not isinstance(
            self.account_id, TradingAccountId
        ):
            raise CommercialBillingValidationError(
                "invoice account_id must be TradingAccountId or None"
            )
        if not isinstance(self.plan_id, CommercialPlanId):
            raise CommercialBillingValidationError(
                "invoice plan_id must be CommercialPlanId"
            )
        if not isinstance(self.plan_version, CommercialPlanVersion):
            raise CommercialBillingValidationError(
                "invoice plan_version must be CommercialPlanVersion"
            )
        if not isinstance(self.product_kind, CommercialProductKind):
            raise CommercialBillingValidationError(
                "invoice product_kind must be CommercialProductKind"
            )
        if not isinstance(self.billing_unit, CommercialBillingUnit):
            raise CommercialBillingValidationError(
                "invoice billing_unit must be CommercialBillingUnit"
            )
        if not isinstance(self.amount, MoneyAmount) or self.amount.amount <= 0:
            raise CommercialBillingValidationError(
                "invoice amount must be positive MoneyAmount"
            )
        for field_name, value in (
            ("period_started_at", self.period_started_at),
            ("period_ended_at", self.period_ended_at),
            ("issued_at", self.issued_at),
            ("due_at", self.due_at),
        ):
            _validate_timestamp(value, field_name=f"invoice {field_name}")
        if self.period_ended_at <= self.period_started_at:
            raise CommercialBillingValidationError(
                "invoice period must have positive duration"
            )
        if self.due_at < self.issued_at:
            raise CommercialBillingValidationError(
                "invoice due_at must not predate issued_at"
            )
        if self.billing_unit is CommercialBillingUnit.ACCOUNT:
            if self.account_id is None:
                raise CommercialBillingValidationError(
                    "account-scoped invoice requires account_id"
                )
        elif self.billing_unit is CommercialBillingUnit.CLIENT:
            if self.account_id is not None:
                raise CommercialBillingValidationError(
                    "client-scoped invoice must not carry account_id"
                )

    @classmethod
    def from_plan(
        cls,
        *,
        invoice_id: CommercialInvoiceId,
        client_id: ClientId,
        account_id: TradingAccountId | None,
        plan: CommercialPlan,
        period_started_at: datetime,
        period_ended_at: datetime,
        issued_at: datetime,
        due_at: datetime,
    ) -> CommercialInvoice:
        if not isinstance(plan, CommercialPlan) or plan.price is None:
            raise CommercialBillingValidationError(
                "invoice requires priced CommercialPlan"
            )
        return cls(
            invoice_id=invoice_id,
            client_id=client_id,
            account_id=account_id,
            plan_id=plan.plan_id,
            plan_version=plan.version,
            product_kind=plan.product.kind,
            billing_unit=plan.billing_unit,
            amount=plan.price,
            period_started_at=period_started_at,
            period_ended_at=period_ended_at,
            issued_at=issued_at,
            due_at=due_at,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.invoice_id.logical_values(),
            self.client_id.logical_values(),
            self.account_id.logical_values() if self.account_id else None,
            self.plan_id.logical_values(),
            self.plan_version.logical_values(),
            self.product_kind.value,
            self.billing_unit.value,
            self.amount.logical_values(),
            self.period_started_at.isoformat(),
            self.period_ended_at.isoformat(),
            self.issued_at.isoformat(),
            self.due_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class VerifiedCommercialPayment:
    payment_id: CommercialPaymentId
    client_id: ClientId
    amount: MoneyAmount
    paid_at: datetime
    verification: CommercialPaymentVerification
    evidence_ref: CommercialPaymentEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.payment_id, CommercialPaymentId):
            raise CommercialBillingValidationError(
                "payment_id must be CommercialPaymentId"
            )
        if not isinstance(self.client_id, ClientId):
            raise CommercialBillingValidationError("payment client_id must be ClientId")
        if not isinstance(self.amount, MoneyAmount) or self.amount.amount <= 0:
            raise CommercialBillingValidationError(
                "payment amount must be positive MoneyAmount"
            )
        _validate_timestamp(self.paid_at, field_name="payment paid_at")
        if not isinstance(self.verification, CommercialPaymentVerification):
            raise CommercialBillingValidationError(
                "payment verification must be CommercialPaymentVerification"
            )
        if not isinstance(self.evidence_ref, CommercialPaymentEvidenceReference):
            raise CommercialBillingValidationError(
                "payment evidence_ref must be CommercialPaymentEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.payment_id.logical_values(),
            self.client_id.logical_values(),
            self.amount.logical_values(),
            self.paid_at.isoformat(),
            self.verification.value,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CommercialPaymentAllocation:
    allocation_id: CommercialPaymentAllocationId
    invoice_id: CommercialInvoiceId
    payment_id: CommercialPaymentId
    amount: MoneyAmount
    allocated_at: datetime
    evidence_ref: CommercialBillingEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.allocation_id, CommercialPaymentAllocationId):
            raise CommercialBillingValidationError(
                "allocation_id must be CommercialPaymentAllocationId"
            )
        if not isinstance(self.invoice_id, CommercialInvoiceId):
            raise CommercialBillingValidationError(
                "allocation invoice_id must be CommercialInvoiceId"
            )
        if not isinstance(self.payment_id, CommercialPaymentId):
            raise CommercialBillingValidationError(
                "allocation payment_id must be CommercialPaymentId"
            )
        if not isinstance(self.amount, MoneyAmount) or self.amount.amount <= 0:
            raise CommercialBillingValidationError(
                "allocation amount must be positive MoneyAmount"
            )
        _validate_timestamp(self.allocated_at, field_name="allocation allocated_at")
        if not isinstance(self.evidence_ref, CommercialBillingEvidenceReference):
            raise CommercialBillingValidationError(
                "allocation evidence_ref must be CommercialBillingEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.allocation_id.logical_values(),
            self.invoice_id.logical_values(),
            self.payment_id.logical_values(),
            self.amount.logical_values(),
            self.allocated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CommercialBillingLedger:
    invoices: tuple[CommercialInvoice, ...] = ()
    payments: tuple[VerifiedCommercialPayment, ...] = ()
    allocations: tuple[CommercialPaymentAllocation, ...] = ()

    def __post_init__(self) -> None:
        invoice_ids = [invoice.invoice_id for invoice in self.invoices]
        payment_ids = [payment.payment_id for payment in self.payments]
        allocation_ids = [allocation.allocation_id for allocation in self.allocations]
        if len(invoice_ids) != len(set(invoice_ids)):
            raise CommercialBillingValidationError("invoice ids must be unique")
        if len(payment_ids) != len(set(payment_ids)):
            raise CommercialBillingValidationError("payment ids must be unique")
        if len(allocation_ids) != len(set(allocation_ids)):
            raise CommercialBillingValidationError("allocation ids must be unique")
        invoices = {invoice.invoice_id: invoice for invoice in self.invoices}
        payments = {payment.payment_id: payment for payment in self.payments}
        for allocation in self.allocations:
            invoice = invoices.get(allocation.invoice_id)
            payment = payments.get(allocation.payment_id)
            if invoice is None or payment is None:
                raise CommercialBillingValidationError(
                    "allocation must reference existing invoice and payment"
                )
            if payment.verification is not CommercialPaymentVerification.VERIFIED:
                raise CommercialBillingValidationError(
                    "only VERIFIED payment may be allocated"
                )
            if invoice.client_id != payment.client_id:
                raise CommercialBillingValidationError(
                    "invoice/payment client binding mismatch"
                )
            if (
                allocation.amount.currency != invoice.amount.currency
                or allocation.amount.currency != payment.amount.currency
            ):
                raise CommercialBillingValidationError(
                    "allocation currency must match invoice and payment"
                )
            if allocation.allocated_at < payment.paid_at:
                raise CommercialBillingValidationError(
                    "allocation must not predate verified payment"
                )
        self._validate_allocation_totals()

    def _validate_allocation_totals(self) -> None:
        for invoice in self.invoices:
            allocated = self.allocated_to_invoice(invoice.invoice_id)
            if allocated.amount > invoice.amount.amount:
                raise CommercialBillingValidationError(
                    "invoice payment allocations cannot exceed amount due"
                )
        for payment in self.payments:
            allocated = self.allocated_from_payment(payment.payment_id)
            if allocated.amount > payment.amount.amount:
                raise CommercialBillingValidationError(
                    "payment allocations cannot exceed verified payment amount"
                )

    def invoice(self, invoice_id: CommercialInvoiceId) -> CommercialInvoice | None:
        return next(
            (invoice for invoice in self.invoices if invoice.invoice_id == invoice_id),
            None,
        )

    def payment(
        self,
        payment_id: CommercialPaymentId,
    ) -> VerifiedCommercialPayment | None:
        return next(
            (payment for payment in self.payments if payment.payment_id == payment_id),
            None,
        )

    def allocated_to_invoice(self, invoice_id: CommercialInvoiceId) -> MoneyAmount:
        invoice = self.invoice(invoice_id)
        if invoice is None:
            raise CommercialBillingValidationError("invoice not found")
        amount = sum(
            (
                allocation.amount.amount
                for allocation in self.allocations
                if allocation.invoice_id == invoice_id
            ),
            start=Decimal(0),
        )
        return MoneyAmount(currency=invoice.amount.currency, amount=amount)

    def allocated_from_payment(self, payment_id: CommercialPaymentId) -> MoneyAmount:
        payment = self.payment(payment_id)
        if payment is None:
            raise CommercialBillingValidationError("payment not found")
        amount = sum(
            (
                allocation.amount.amount
                for allocation in self.allocations
                if allocation.payment_id == payment_id
            ),
            start=Decimal(0),
        )
        return MoneyAmount(currency=payment.amount.currency, amount=amount)

    def invoice_status(self, invoice_id: CommercialInvoiceId) -> CommercialInvoiceStatus:
        invoice = self.invoice(invoice_id)
        if invoice is None:
            raise CommercialBillingValidationError("invoice not found")
        paid = self.allocated_to_invoice(invoice_id).amount
        if paid == 0:
            return CommercialInvoiceStatus.DUE
        if paid < invoice.amount.amount:
            return CommercialInvoiceStatus.PARTIALLY_PAID
        return CommercialInvoiceStatus.PAID

    def outstanding(self, invoice_id: CommercialInvoiceId) -> MoneyAmount:
        invoice = self.invoice(invoice_id)
        if invoice is None:
            raise CommercialBillingValidationError("invoice not found")
        allocated = self.allocated_to_invoice(invoice_id)
        return MoneyAmount(
            currency=invoice.amount.currency,
            amount=invoice.amount.amount - allocated.amount,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(invoice.logical_values() for invoice in self.invoices),
            tuple(payment.logical_values() for payment in self.payments),
            tuple(allocation.logical_values() for allocation in self.allocations),
        )


def append_invoice(
    ledger: CommercialBillingLedger,
    invoice: CommercialInvoice,
) -> Result[CommercialBillingLedger, CommercialBillingError]:
    if not isinstance(ledger, CommercialBillingLedger):
        return Failure(CommercialBillingValidationError("billing ledger is required"))
    try:
        return Success(replace(ledger, invoices=(*ledger.invoices, invoice)))
    except CommercialBillingError as error:
        return Failure(error)


def append_verified_payment(
    ledger: CommercialBillingLedger,
    payment: VerifiedCommercialPayment,
) -> Result[CommercialBillingLedger, CommercialBillingError]:
    if not isinstance(ledger, CommercialBillingLedger):
        return Failure(CommercialBillingValidationError("billing ledger is required"))
    if payment.verification is not CommercialPaymentVerification.VERIFIED:
        return Failure(
            CommercialBillingValidationError(
                "only VERIFIED payment may enter billing ledger"
            )
        )
    try:
        return Success(replace(ledger, payments=(*ledger.payments, payment)))
    except CommercialBillingError as error:
        return Failure(error)


def allocate_verified_payment(
    ledger: CommercialBillingLedger,
    allocation: CommercialPaymentAllocation,
) -> Result[CommercialBillingLedger, CommercialBillingError]:
    if not isinstance(ledger, CommercialBillingLedger):
        return Failure(CommercialBillingValidationError("billing ledger is required"))
    try:
        return Success(replace(ledger, allocations=(*ledger.allocations, allocation)))
    except CommercialBillingError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class PerformanceFeePolicy:
    policy_id: PerformanceFeePolicyId
    version: PerformanceFeePolicyVersion
    fee_bps: int = _PERFORMANCE_FEE_BPS

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, PerformanceFeePolicyId):
            raise CommercialBillingValidationError(
                "performance fee policy_id must be PerformanceFeePolicyId"
            )
        if not isinstance(self.version, PerformanceFeePolicyVersion):
            raise CommercialBillingValidationError(
                "performance fee version must be PerformanceFeePolicyVersion"
            )
        if type(self.fee_bps) is not int or self.fee_bps != _PERFORMANCE_FEE_BPS:
            raise CommercialBillingValidationError(
                "current Core performance fee policy must equal 20 percent"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id.logical_values(),
            self.version.logical_values(),
            self.fee_bps,
        )


@dataclass(frozen=True, slots=True)
class PerformanceFeeAssessment:
    policy_id: PerformanceFeePolicyId
    policy_version: PerformanceFeePolicyVersion
    eligible_paid_profit_record_id: ClientPerformanceRecordId
    client_account_id: TradingAccountId
    eligible_paid_profit: MoneyAmount
    fee_amount: MoneyAmount

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_id.logical_values(),
            self.policy_version.logical_values(),
            self.eligible_paid_profit_record_id.logical_values(),
            self.client_account_id.logical_values(),
            self.eligible_paid_profit.logical_values(),
            self.fee_amount.logical_values(),
        )


def calculate_performance_fee(
    policy: PerformanceFeePolicy,
    eligible_paid_profit: EligibleClientPaidProfitRecord,
) -> PerformanceFeeAssessment:
    """Calculate Core fee only from verified Eligible Client Paid Profit."""

    if not isinstance(policy, PerformanceFeePolicy):
        raise CommercialBillingValidationError("PerformanceFeePolicy is required")
    if not isinstance(eligible_paid_profit, EligibleClientPaidProfitRecord):
        raise CommercialBillingValidationError(
            "performance fee requires EligibleClientPaidProfitRecord"
        )
    fee = (
        eligible_paid_profit.amount.amount
        * Decimal(policy.fee_bps)
        / _BPS_DENOMINATOR
    )
    return PerformanceFeeAssessment(
        policy_id=policy.policy_id,
        policy_version=policy.version,
        eligible_paid_profit_record_id=eligible_paid_profit.record_id,
        client_account_id=eligible_paid_profit.account_id,
        eligible_paid_profit=eligible_paid_profit.amount,
        fee_amount=MoneyAmount(
            currency=eligible_paid_profit.amount.currency,
            amount=fee,
        ),
    )


@dataclass(frozen=True, slots=True)
class CommercialBillingStanding:
    client_id: ClientId
    account_id: TradingAccountId | None
    state: CommercialBillingStandingState
    evaluated_at: datetime
    evidence_ref: CommercialBillingEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.client_id, ClientId):
            raise CommercialBillingValidationError(
                "billing standing client_id must be ClientId"
            )
        if self.account_id is not None and not isinstance(
            self.account_id, TradingAccountId
        ):
            raise CommercialBillingValidationError(
                "billing standing account_id must be TradingAccountId or None"
            )
        if not isinstance(self.state, CommercialBillingStandingState):
            raise CommercialBillingValidationError(
                "billing standing state must be CommercialBillingStandingState"
            )
        _validate_timestamp(self.evaluated_at, field_name="billing standing evaluated_at")
        if not isinstance(self.evidence_ref, CommercialBillingEvidenceReference):
            raise CommercialBillingValidationError(
                "billing standing evidence_ref must be CommercialBillingEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.client_id.logical_values(),
            self.account_id.logical_values() if self.account_id else None,
            self.state.value,
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def project_license_payment_standing(
    standing: CommercialBillingStanding,
) -> CommercialPaymentStanding:
    if not isinstance(standing, CommercialBillingStanding):
        raise CommercialBillingValidationError(
            "CommercialBillingStanding is required"
        )
    if standing.state is CommercialBillingStandingState.CURRENT:
        return CommercialPaymentStanding.CURRENT
    if standing.state is CommercialBillingStandingState.PAYMENT_FAILED:
        return CommercialPaymentStanding.PAYMENT_FAILED
    return CommercialPaymentStanding.UNKNOWN
