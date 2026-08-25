from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Never
from uuid import UUID

from qore.infrastructure.supply_chain_finance_semantics import (
    ReceivablePaymentObligationTerms,
    ScfEvidenceRef,
    ScfPartyReferenceId,
)
from qore.kernel.errors import InfrastructureError


class AdvancedPayableScfSemanticsError(InfrastructureError):
    """Base error for bounded Advanced Payable SCF semantics."""

    __slots__ = ()


class AdvancedPayableScfValidationError(AdvancedPayableScfSemanticsError):
    """Violation of a static Advanced Payable semantic invariant."""

    __slots__ = ()


def _fail(message: str) -> Never:
    raise AdvancedPayableScfValidationError(message)


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{field_name} must be exact UUID")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        _fail(f"{field_name} must be exact date")


def _validate_party(value: ScfPartyReferenceId, *, field_name: str) -> None:
    if type(value) is not ScfPartyReferenceId:
        _fail(f"{field_name} must be exact ScfPartyReferenceId")
    value.__post_init__()


def _validate_evidence(value: ScfEvidenceRef, *, field_name: str) -> None:
    if type(value) is not ScfEvidenceRef:
        _fail(f"{field_name} must be exact ScfEvidenceRef")
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class AdvancedPayableQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="Advanced Payable qualification ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class AdvancedPayableUndertakingReferenceId:
    """Opaque contractual undertaking reference; never payment-execution authority."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="Advanced Payable undertaking reference ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class AdvancedPayableNetworkReferenceId:
    """Opaque matched-network reference; never network/DLT implementation authority."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="Advanced Payable network reference ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class AdvancedPayableApprovedObligation:
    """Buyer-approved payment obligation reused from retained SCF obligation semantics."""

    obligation: ReceivablePaymentObligationTerms
    approval_evidence_ref: ScfEvidenceRef

    def __post_init__(self) -> None:
        if type(self.obligation) is not ReceivablePaymentObligationTerms:
            _fail(
                "Advanced Payable obligation must be exact "
                "ReceivablePaymentObligationTerms"
            )
        _validate_evidence(
            self.approval_evidence_ref,
            field_name="Advanced Payable approval evidence",
        )
        self.obligation.__post_init__()
        if self.obligation.obligation_kind.value != "payment-obligation":
            _fail("Advanced Payable requires payment-obligation kind")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.obligation.logical_values(),
            self.approval_evidence_ref.logical_values(),
        )


class DynamicDiscountRateSetter(StrEnum):
    BUYER = "buyer"
    SELLER = "seller"


class DynamicDiscountTimingBasis(StrEnum):
    DAYS_BEFORE_ORIGINAL_DUE_DATE = "days-before-original-due-date"


@dataclass(frozen=True, slots=True)
class DynamicDiscountConvention:
    """Static discount convention only; no discount or payment calculation."""

    rate_setter: DynamicDiscountRateSetter
    timing_basis: DynamicDiscountTimingBasis
    evidence_ref: ScfEvidenceRef

    def __post_init__(self) -> None:
        if type(self.rate_setter) is not DynamicDiscountRateSetter:
            _fail("dynamic discount rate setter must be exact DynamicDiscountRateSetter")
        if type(self.timing_basis) is not DynamicDiscountTimingBasis:
            _fail(
                "dynamic discount timing basis must be exact "
                "DynamicDiscountTimingBasis"
            )
        _validate_evidence(
            self.evidence_ref,
            field_name="dynamic discount convention evidence",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.rate_setter.value,
            self.timing_basis.value,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CorporatePaymentUndertakingTerms:
    """Buyer undertaking + finance-provider early-payment relationship, no purchase."""

    approved_obligation: AdvancedPayableApprovedObligation
    finance_provider_reference_id: ScfPartyReferenceId
    undertaking_reference_id: AdvancedPayableUndertakingReferenceId
    undertaking_evidence_ref: ScfEvidenceRef

    def __post_init__(self) -> None:
        if type(self.approved_obligation) is not AdvancedPayableApprovedObligation:
            _fail(
                "CPU approved obligation must be exact AdvancedPayableApprovedObligation"
            )
        self.approved_obligation.__post_init__()
        _validate_party(
            self.finance_provider_reference_id,
            field_name="CPU finance-provider reference",
        )
        if type(self.undertaking_reference_id) is not AdvancedPayableUndertakingReferenceId:
            _fail(
                "CPU undertaking reference must be exact "
                "AdvancedPayableUndertakingReferenceId"
            )
        self.undertaking_reference_id.__post_init__()
        _validate_evidence(
            self.undertaking_evidence_ref,
            field_name="CPU undertaking evidence",
        )

        obligation = self.approved_obligation.obligation
        if self.finance_provider_reference_id in {
            obligation.creditor_reference_id,
            obligation.debtor_reference_id,
        }:
            _fail("CPU finance provider must differ from buyer and seller")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.approved_obligation.logical_values(),
            self.finance_provider_reference_id.logical_values(),
            self.undertaking_reference_id.logical_values(),
            self.undertaking_evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DynamicDiscountingTerms:
    """Buyer-funded optional early-payment terms; no third-party financing authority."""

    approved_obligation: AdvancedPayableApprovedObligation
    discount_convention: DynamicDiscountConvention
    evidence_ref: ScfEvidenceRef

    def __post_init__(self) -> None:
        if type(self.approved_obligation) is not AdvancedPayableApprovedObligation:
            _fail(
                "DD approved obligation must be exact AdvancedPayableApprovedObligation"
            )
        if type(self.discount_convention) is not DynamicDiscountConvention:
            _fail("DD discount convention must be exact DynamicDiscountConvention")
        self.approved_obligation.__post_init__()
        self.discount_convention.__post_init__()
        _validate_evidence(self.evidence_ref, field_name="DD evidence")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.approved_obligation.logical_values(),
            "buyer-own-funds",
            self.discount_convention.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class BankPaymentUndertakingTerms:
    """Independent bank undertaking after matched-network context; no network I/O."""

    approved_obligation: AdvancedPayableApprovedObligation
    issuing_bank_reference_id: ScfPartyReferenceId
    beneficiary_reference_id: ScfPartyReferenceId
    undertaking_reference_id: AdvancedPayableUndertakingReferenceId
    network_reference_id: AdvancedPayableNetworkReferenceId
    undertaking_evidence_ref: ScfEvidenceRef

    def __post_init__(self) -> None:
        if type(self.approved_obligation) is not AdvancedPayableApprovedObligation:
            _fail(
                "BPU approved obligation must be exact AdvancedPayableApprovedObligation"
            )
        self.approved_obligation.__post_init__()
        _validate_party(
            self.issuing_bank_reference_id,
            field_name="BPU issuing-bank reference",
        )
        _validate_party(
            self.beneficiary_reference_id,
            field_name="BPU beneficiary reference",
        )
        if type(self.undertaking_reference_id) is not AdvancedPayableUndertakingReferenceId:
            _fail(
                "BPU undertaking reference must be exact "
                "AdvancedPayableUndertakingReferenceId"
            )
        if type(self.network_reference_id) is not AdvancedPayableNetworkReferenceId:
            _fail(
                "BPU network reference must be exact AdvancedPayableNetworkReferenceId"
            )
        self.undertaking_reference_id.__post_init__()
        self.network_reference_id.__post_init__()
        _validate_evidence(
            self.undertaking_evidence_ref,
            field_name="BPU undertaking evidence",
        )

        obligation = self.approved_obligation.obligation
        buyer = obligation.debtor_reference_id
        seller = obligation.creditor_reference_id
        if self.issuing_bank_reference_id in {
            buyer,
            seller,
            self.beneficiary_reference_id,
        }:
            _fail("BPU issuing bank must differ from buyer, seller, and beneficiary")
        if self.beneficiary_reference_id == buyer:
            _fail("BPU beneficiary must differ from buyer")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.approved_obligation.logical_values(),
            self.issuing_bank_reference_id.logical_values(),
            self.beneficiary_reference_id.logical_values(),
            "issuing-bank-primary-obligor",
            self.undertaking_reference_id.logical_values(),
            self.network_reference_id.logical_values(),
            self.undertaking_evidence_ref.logical_values(),
        )


class AdvancedPayableTechniqueKind(StrEnum):
    CORPORATE_PAYMENT_UNDERTAKING = "corporate-payment-undertaking"
    DYNAMIC_DISCOUNTING = "dynamic-discounting"
    BANK_PAYMENT_UNDERTAKING = "bank-payment-undertaking"


AdvancedPayableTerms = (
    CorporatePaymentUndertakingTerms
    | DynamicDiscountingTerms
    | BankPaymentUndertakingTerms
)


@dataclass(frozen=True, slots=True)
class AdvancedPayableQualification:
    qualification_id: AdvancedPayableQualificationId
    technique: AdvancedPayableTechniqueKind
    terms: AdvancedPayableTerms
    effective_date: date
    evidence_ref: ScfEvidenceRef
    end_date: date | None = None

    def __post_init__(self) -> None:
        if type(self.qualification_id) is not AdvancedPayableQualificationId:
            _fail(
                "Advanced Payable qualification ID must be exact "
                "AdvancedPayableQualificationId"
            )
        if type(self.technique) is not AdvancedPayableTechniqueKind:
            _fail("Advanced Payable technique must be exact AdvancedPayableTechniqueKind")
        self.qualification_id.__post_init__()
        _validate_date(
            self.effective_date,
            field_name="Advanced Payable qualification effective date",
        )
        _validate_evidence(
            self.evidence_ref,
            field_name="Advanced Payable qualification evidence",
        )
        if self.end_date is not None:
            _validate_date(
                self.end_date,
                field_name="Advanced Payable qualification end date",
            )
            if self.end_date < self.effective_date:
                _fail(
                    "Advanced Payable qualification end date must not precede "
                    "effective date"
                )

        if self.technique is AdvancedPayableTechniqueKind.CORPORATE_PAYMENT_UNDERTAKING:
            if type(self.terms) is not CorporatePaymentUndertakingTerms:
                _fail("CPU technique requires exact CorporatePaymentUndertakingTerms")
            self.terms.__post_init__()
            return
        if self.technique is AdvancedPayableTechniqueKind.DYNAMIC_DISCOUNTING:
            if type(self.terms) is not DynamicDiscountingTerms:
                _fail("DD technique requires exact DynamicDiscountingTerms")
            self.terms.__post_init__()
            return
        if self.technique is not AdvancedPayableTechniqueKind.BANK_PAYMENT_UNDERTAKING:
            _fail("Advanced Payable technique is outside versioned scope")
        if type(self.terms) is not BankPaymentUndertakingTerms:
            _fail("BPU technique requires exact BankPaymentUndertakingTerms")
        self.terms.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "advanced-payable-scf.v1",
            self.qualification_id.logical_values(),
            self.technique.value,
            self.terms.logical_values(),
            self.effective_date.isoformat(),
            self.evidence_ref.logical_values(),
            None if self.end_date is None else self.end_date.isoformat(),
        )
