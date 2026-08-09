from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import ClientId, TradingAccountId
from qore.infrastructure.client_performance_ledger import ClientPerformanceRecordId
from qore.infrastructure.commercial_billing import (
    CommercialBillingLedger,
    CommercialInvoice,
    CommercialInvoiceId,
    CommercialInvoiceStatus,
    CommercialPaymentAllocationId,
    CommercialPaymentEvidenceReference,
    CommercialPaymentId,
    CommercialPaymentVerification,
    PerformanceFeeAssessment,
    PerformanceFeePolicyId,
)
from qore.infrastructure.commercial_products import CommercialProductKind
from qore.infrastructure.proprietary_accounts import MoneyAmount
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class CorporateProfitVaultError(InfrastructureError):
    """Base error for corporate profit-vault accounting facts."""

    __slots__ = ()


class CorporateProfitVaultValidationError(CorporateProfitVaultError):
    """Violation of a Corporate Profit Vault invariant."""

    __slots__ = ()


class CorporateProfitVaultConflictError(CorporateProfitVaultError):
    """A corporate accounting fact conflicts with existing immutable evidence."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise CorporateProfitVaultValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CorporateProfitVaultValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CorporateProfitVaultValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class CorporateVaultRecordId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="corporate vault record id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class CorporateRevenueSource(StrEnum):
    EA_SUBSCRIPTION = "ea_subscription"
    WIDGET_SUBSCRIPTION = "widget_subscription"
    CORE_SERVICES = "core_services"
    MANAGED_HOSTING = "managed_hosting"
    MANAGED_FUTURES = "managed_futures"
    CORE_PERFORMANCE_FEE = "core_performance_fee"


class CorporateReceivableState(StrEnum):
    OPEN = "open"
    PARTIALLY_SETTLED = "partially_settled"
    SETTLED = "settled"


def _source_for_product(kind: CommercialProductKind) -> CorporateRevenueSource:
    mapping = {
        CommercialProductKind.CLIENT_EXECUTION_AGENT: (
            CorporateRevenueSource.EA_SUBSCRIPTION
        ),
        CommercialProductKind.CLIENT_WIDGET: (
            CorporateRevenueSource.WIDGET_SUBSCRIPTION
        ),
        CommercialProductKind.CORE_SERVICES: CorporateRevenueSource.CORE_SERVICES,
        CommercialProductKind.MANAGED_HOSTING: CorporateRevenueSource.MANAGED_HOSTING,
        CommercialProductKind.MANAGED_FUTURES: CorporateRevenueSource.MANAGED_FUTURES,
    }
    return mapping[kind]


@dataclass(frozen=True, slots=True)
class CorporateRevenueAttribution:
    """Corporate revenue attribution; not proof of cash receipt."""

    record_id: CorporateVaultRecordId
    source: CorporateRevenueSource
    client_id: ClientId
    account_id: TradingAccountId | None
    invoice_id: CommercialInvoiceId | None
    product_kind: CommercialProductKind | None
    performance_fee_policy_id: PerformanceFeePolicyId | None
    eligible_paid_profit_record_id: ClientPerformanceRecordId | None
    period_started_at: datetime
    period_ended_at: datetime
    amount: MoneyAmount
    attributed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, CorporateVaultRecordId):
            raise CorporateProfitVaultValidationError(
                "revenue record_id must be CorporateVaultRecordId"
            )
        if not isinstance(self.source, CorporateRevenueSource):
            raise CorporateProfitVaultValidationError(
                "revenue source must be CorporateRevenueSource"
            )
        if not isinstance(self.client_id, ClientId):
            raise CorporateProfitVaultValidationError(
                "revenue client_id must be ClientId"
            )
        if self.account_id is not None and not isinstance(
            self.account_id, TradingAccountId
        ):
            raise CorporateProfitVaultValidationError(
                "revenue account_id must be TradingAccountId or None"
            )
        for field_name, value in (
            ("period_started_at", self.period_started_at),
            ("period_ended_at", self.period_ended_at),
            ("attributed_at", self.attributed_at),
        ):
            _validate_timestamp(value, field_name=f"revenue {field_name}")
        if self.period_ended_at <= self.period_started_at:
            raise CorporateProfitVaultValidationError(
                "revenue period must have positive duration"
            )
        if not isinstance(self.amount, MoneyAmount) or self.amount.amount <= 0:
            raise CorporateProfitVaultValidationError(
                "revenue amount must be positive MoneyAmount"
            )
        self._validate_lineage()

    def _validate_lineage(self) -> None:
        if self.source is CorporateRevenueSource.CORE_PERFORMANCE_FEE:
            if self.invoice_id is not None or self.product_kind is not None:
                raise CorporateProfitVaultValidationError(
                    "performance-fee revenue must not claim invoice product lineage"
                )
            if not isinstance(self.performance_fee_policy_id, PerformanceFeePolicyId):
                raise CorporateProfitVaultValidationError(
                    "performance-fee revenue requires policy lineage"
                )
            if not isinstance(
                self.eligible_paid_profit_record_id,
                ClientPerformanceRecordId,
            ):
                raise CorporateProfitVaultValidationError(
                    "performance-fee revenue requires eligible-paid lineage"
                )
            if self.account_id is None:
                raise CorporateProfitVaultValidationError(
                    "performance-fee revenue requires account attribution"
                )
            return
        if not isinstance(self.invoice_id, CommercialInvoiceId):
            raise CorporateProfitVaultValidationError(
                "non-performance revenue requires invoice lineage"
            )
        if not isinstance(self.product_kind, CommercialProductKind):
            raise CorporateProfitVaultValidationError(
                "non-performance revenue requires product lineage"
            )
        if (
            self.performance_fee_policy_id is not None
            or self.eligible_paid_profit_record_id is not None
        ):
            raise CorporateProfitVaultValidationError(
                "invoice revenue must not carry performance-fee lineage"
            )
        if self.source is not _source_for_product(self.product_kind):
            raise CorporateProfitVaultValidationError(
                "revenue source does not match product kind"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.source.value,
            self.client_id.logical_values(),
            self.account_id.logical_values() if self.account_id else None,
            self.invoice_id.logical_values() if self.invoice_id else None,
            self.product_kind.value if self.product_kind else None,
            (
                self.performance_fee_policy_id.logical_values()
                if self.performance_fee_policy_id
                else None
            ),
            (
                self.eligible_paid_profit_record_id.logical_values()
                if self.eligible_paid_profit_record_id
                else None
            ),
            self.period_started_at.isoformat(),
            self.period_ended_at.isoformat(),
            self.amount.logical_values(),
            self.attributed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CorporateAccountsReceivable:
    """Point-in-time corporate debt snapshot for one commercial invoice."""

    record_id: CorporateVaultRecordId
    invoice_id: CommercialInvoiceId
    client_id: ClientId
    account_id: TradingAccountId | None
    product_kind: CommercialProductKind
    amount_due: MoneyAmount
    outstanding: MoneyAmount
    state: CorporateReceivableState
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, CorporateVaultRecordId):
            raise CorporateProfitVaultValidationError(
                "receivable record_id must be CorporateVaultRecordId"
            )
        if not isinstance(self.invoice_id, CommercialInvoiceId):
            raise CorporateProfitVaultValidationError(
                "receivable invoice_id must be CommercialInvoiceId"
            )
        if not isinstance(self.client_id, ClientId):
            raise CorporateProfitVaultValidationError(
                "receivable client_id must be ClientId"
            )
        if self.account_id is not None and not isinstance(
            self.account_id, TradingAccountId
        ):
            raise CorporateProfitVaultValidationError(
                "receivable account_id must be TradingAccountId or None"
            )
        if not isinstance(self.product_kind, CommercialProductKind):
            raise CorporateProfitVaultValidationError(
                "receivable product_kind must be CommercialProductKind"
            )
        if not isinstance(self.amount_due, MoneyAmount) or self.amount_due.amount <= 0:
            raise CorporateProfitVaultValidationError(
                "receivable amount_due must be positive MoneyAmount"
            )
        if not isinstance(self.outstanding, MoneyAmount) or self.outstanding.amount < 0:
            raise CorporateProfitVaultValidationError(
                "receivable outstanding must be non-negative MoneyAmount"
            )
        if self.amount_due.currency != self.outstanding.currency:
            raise CorporateProfitVaultValidationError(
                "receivable amounts must use same currency"
            )
        if self.outstanding.amount > self.amount_due.amount:
            raise CorporateProfitVaultValidationError(
                "receivable outstanding cannot exceed amount due"
            )
        if not isinstance(self.state, CorporateReceivableState):
            raise CorporateProfitVaultValidationError(
                "receivable state must be CorporateReceivableState"
            )
        _validate_timestamp(self.recorded_at, field_name="receivable recorded_at")
        expected = (
            CorporateReceivableState.OPEN
            if self.outstanding.amount == self.amount_due.amount
            else CorporateReceivableState.SETTLED
            if self.outstanding.amount == 0
            else CorporateReceivableState.PARTIALLY_SETTLED
        )
        if self.state is not expected:
            raise CorporateProfitVaultValidationError(
                "receivable state does not match outstanding amount"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.invoice_id.logical_values(),
            self.client_id.logical_values(),
            self.account_id.logical_values() if self.account_id else None,
            self.product_kind.value,
            self.amount_due.logical_values(),
            self.outstanding.logical_values(),
            self.state.value,
            self.recorded_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CorporateCashReceived:
    """Corporate cash fact created only from verified payment allocation evidence."""

    record_id: CorporateVaultRecordId
    source: CorporateRevenueSource
    client_id: ClientId
    account_id: TradingAccountId | None
    invoice_id: CommercialInvoiceId
    product_kind: CommercialProductKind
    allocation_id: CommercialPaymentAllocationId
    payment_id: CommercialPaymentId
    amount: MoneyAmount
    payment_evidence_ref: CommercialPaymentEvidenceReference
    paid_at: datetime
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, CorporateVaultRecordId):
            raise CorporateProfitVaultValidationError(
                "cash record_id must be CorporateVaultRecordId"
            )
        if not isinstance(self.source, CorporateRevenueSource):
            raise CorporateProfitVaultValidationError(
                "cash source must be CorporateRevenueSource"
            )
        if not isinstance(self.client_id, ClientId):
            raise CorporateProfitVaultValidationError(
                "cash client_id must be ClientId"
            )
        if self.account_id is not None and not isinstance(
            self.account_id, TradingAccountId
        ):
            raise CorporateProfitVaultValidationError(
                "cash account_id must be TradingAccountId or None"
            )
        if not isinstance(self.invoice_id, CommercialInvoiceId):
            raise CorporateProfitVaultValidationError(
                "cash invoice_id must be CommercialInvoiceId"
            )
        if not isinstance(self.product_kind, CommercialProductKind):
            raise CorporateProfitVaultValidationError(
                "cash product_kind must be CommercialProductKind"
            )
        if self.source is not _source_for_product(self.product_kind):
            raise CorporateProfitVaultValidationError(
                "cash source does not match product kind"
            )
        if not isinstance(self.allocation_id, CommercialPaymentAllocationId):
            raise CorporateProfitVaultValidationError(
                "cash allocation_id must be CommercialPaymentAllocationId"
            )
        if not isinstance(self.payment_id, CommercialPaymentId):
            raise CorporateProfitVaultValidationError(
                "cash payment_id must be CommercialPaymentId"
            )
        if not isinstance(self.amount, MoneyAmount) or self.amount.amount <= 0:
            raise CorporateProfitVaultValidationError(
                "cash amount must be positive MoneyAmount"
            )
        if not isinstance(
            self.payment_evidence_ref,
            CommercialPaymentEvidenceReference,
        ):
            raise CorporateProfitVaultValidationError(
                "cash requires CommercialPaymentEvidenceReference"
            )
        _validate_timestamp(self.paid_at, field_name="cash paid_at")
        _validate_timestamp(self.recorded_at, field_name="cash recorded_at")
        if self.recorded_at < self.paid_at:
            raise CorporateProfitVaultValidationError(
                "cash recorded_at must not predate paid_at"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.source.value,
            self.client_id.logical_values(),
            self.account_id.logical_values() if self.account_id else None,
            self.invoice_id.logical_values(),
            self.product_kind.value,
            self.allocation_id.logical_values(),
            self.payment_id.logical_values(),
            self.amount.logical_values(),
            self.payment_evidence_ref.logical_values(),
            self.paid_at.isoformat(),
            self.recorded_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CorporateProfitVault:
    revenue_attributions: tuple[CorporateRevenueAttribution, ...] = ()
    receivables: tuple[CorporateAccountsReceivable, ...] = ()
    cash_received: tuple[CorporateCashReceived, ...] = ()

    def __post_init__(self) -> None:
        record_ids = [
            *(record.record_id for record in self.revenue_attributions),
            *(record.record_id for record in self.receivables),
            *(record.record_id for record in self.cash_received),
        ]
        if len(record_ids) != len(set(record_ids)):
            raise CorporateProfitVaultValidationError(
                "corporate vault record ids must be globally unique"
            )
        allocation_ids = [record.allocation_id for record in self.cash_received]
        if len(allocation_ids) != len(set(allocation_ids)):
            raise CorporateProfitVaultValidationError(
                "payment allocation can create cash received only once"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(record.logical_values() for record in self.revenue_attributions),
            tuple(record.logical_values() for record in self.receivables),
            tuple(record.logical_values() for record in self.cash_received),
        )


def attribute_invoice_revenue(
    invoice: CommercialInvoice,
    *,
    record_id: CorporateVaultRecordId,
    attributed_at: datetime,
) -> CorporateRevenueAttribution:
    if not isinstance(invoice, CommercialInvoice):
        raise CorporateProfitVaultValidationError("CommercialInvoice is required")
    return CorporateRevenueAttribution(
        record_id=record_id,
        source=_source_for_product(invoice.product_kind),
        client_id=invoice.client_id,
        account_id=invoice.account_id,
        invoice_id=invoice.invoice_id,
        product_kind=invoice.product_kind,
        performance_fee_policy_id=None,
        eligible_paid_profit_record_id=None,
        period_started_at=invoice.period_started_at,
        period_ended_at=invoice.period_ended_at,
        amount=invoice.amount,
        attributed_at=attributed_at,
    )


def attribute_performance_fee_revenue(
    assessment: PerformanceFeeAssessment,
    *,
    client_id: ClientId,
    record_id: CorporateVaultRecordId,
    period_started_at: datetime,
    period_ended_at: datetime,
    attributed_at: datetime,
) -> CorporateRevenueAttribution:
    if not isinstance(assessment, PerformanceFeeAssessment):
        raise CorporateProfitVaultValidationError(
            "PerformanceFeeAssessment is required"
        )
    return CorporateRevenueAttribution(
        record_id=record_id,
        source=CorporateRevenueSource.CORE_PERFORMANCE_FEE,
        client_id=client_id,
        account_id=assessment.client_account_id,
        invoice_id=None,
        product_kind=None,
        performance_fee_policy_id=assessment.policy_id,
        eligible_paid_profit_record_id=assessment.eligible_paid_profit_record_id,
        period_started_at=period_started_at,
        period_ended_at=period_ended_at,
        amount=assessment.fee_amount,
        attributed_at=attributed_at,
    )


def snapshot_accounts_receivable(
    ledger: CommercialBillingLedger,
    invoice_id: CommercialInvoiceId,
    *,
    record_id: CorporateVaultRecordId,
    recorded_at: datetime,
) -> CorporateAccountsReceivable:
    if not isinstance(ledger, CommercialBillingLedger):
        raise CorporateProfitVaultValidationError(
            "CommercialBillingLedger is required"
        )
    invoice = ledger.invoice(invoice_id)
    if invoice is None:
        raise CorporateProfitVaultValidationError("invoice not found in billing ledger")
    outstanding = ledger.outstanding(invoice_id)
    status = ledger.invoice_status(invoice_id)
    state = (
        CorporateReceivableState.OPEN
        if status is CommercialInvoiceStatus.DUE
        else CorporateReceivableState.SETTLED
        if status is CommercialInvoiceStatus.PAID
        else CorporateReceivableState.PARTIALLY_SETTLED
    )
    return CorporateAccountsReceivable(
        record_id=record_id,
        invoice_id=invoice.invoice_id,
        client_id=invoice.client_id,
        account_id=invoice.account_id,
        product_kind=invoice.product_kind,
        amount_due=invoice.amount,
        outstanding=outstanding,
        state=state,
        recorded_at=recorded_at,
    )


def cash_received_from_allocation(
    ledger: CommercialBillingLedger,
    allocation_id: CommercialPaymentAllocationId,
    *,
    record_id: CorporateVaultRecordId,
    recorded_at: datetime,
) -> CorporateCashReceived:
    if not isinstance(ledger, CommercialBillingLedger):
        raise CorporateProfitVaultValidationError(
            "CommercialBillingLedger is required"
        )
    allocation = next(
        (
            candidate
            for candidate in ledger.allocations
            if candidate.allocation_id == allocation_id
        ),
        None,
    )
    if allocation is None:
        raise CorporateProfitVaultValidationError(
            "cash requires existing payment allocation"
        )
    invoice = ledger.invoice(allocation.invoice_id)
    payment = ledger.payment(allocation.payment_id)
    if invoice is None or payment is None:
        raise CorporateProfitVaultValidationError(
            "cash allocation lineage is incomplete"
        )
    if payment.verification is not CommercialPaymentVerification.VERIFIED:
        raise CorporateProfitVaultValidationError(
            "cash requires VERIFIED payment evidence"
        )
    return CorporateCashReceived(
        record_id=record_id,
        source=_source_for_product(invoice.product_kind),
        client_id=invoice.client_id,
        account_id=invoice.account_id,
        invoice_id=invoice.invoice_id,
        product_kind=invoice.product_kind,
        allocation_id=allocation.allocation_id,
        payment_id=payment.payment_id,
        amount=allocation.amount,
        payment_evidence_ref=payment.evidence_ref,
        paid_at=payment.paid_at,
        recorded_at=recorded_at,
    )


def append_revenue_attribution(
    vault: CorporateProfitVault,
    record: CorporateRevenueAttribution,
) -> Result[CorporateProfitVault, CorporateProfitVaultError]:
    if not isinstance(vault, CorporateProfitVault):
        return Failure(CorporateProfitVaultValidationError("vault is required"))
    try:
        return Success(
            replace(
                vault,
                revenue_attributions=(*vault.revenue_attributions, record),
            )
        )
    except CorporateProfitVaultError as error:
        return Failure(error)


def append_receivable(
    vault: CorporateProfitVault,
    record: CorporateAccountsReceivable,
) -> Result[CorporateProfitVault, CorporateProfitVaultError]:
    if not isinstance(vault, CorporateProfitVault):
        return Failure(CorporateProfitVaultValidationError("vault is required"))
    try:
        return Success(replace(vault, receivables=(*vault.receivables, record)))
    except CorporateProfitVaultError as error:
        return Failure(error)


def append_cash_received(
    vault: CorporateProfitVault,
    record: CorporateCashReceived,
) -> Result[CorporateProfitVault, CorporateProfitVaultError]:
    if not isinstance(vault, CorporateProfitVault):
        return Failure(CorporateProfitVaultValidationError("vault is required"))
    try:
        return Success(replace(vault, cash_received=(*vault.cash_received, record)))
    except CorporateProfitVaultError as error:
        return Failure(error)
