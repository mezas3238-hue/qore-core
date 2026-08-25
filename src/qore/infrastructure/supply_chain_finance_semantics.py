from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import Never
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class SupplyChainFinanceSemanticsError(InfrastructureError):
    """Base error for bounded supply-chain-finance contract semantics."""

    __slots__ = ()


class SupplyChainFinanceValidationError(SupplyChainFinanceSemanticsError):
    """Violation of a static supply-chain-finance semantic invariant."""

    __slots__ = ()


def _fail(message: str) -> Never:
    raise SupplyChainFinanceValidationError(message)


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{field_name} must be exact UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if type(value) is not EconomicIdentityId:
        _fail(f"{field_name} must be exact EconomicIdentityId")
    _validate_uuid(value.value, field_name=f"{field_name}.value")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        _fail(f"{field_name} must be exact date")


def _validate_code(value: str, *, field_name: str) -> None:
    valid = (
        type(value) is str
        and bool(value)
        and len(value) <= 64
        and fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", value) is not None
    )
    if not valid:
        _fail(f"{field_name} must use canonical lowercase code syntax")


def _validate_decimal(value: Decimal, *, field_name: str, positive: bool = False) -> None:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{field_name} must be a finite exact Decimal")
    if positive and value <= 0:
        _fail(f"{field_name} must be positive")


def _canonical_decimal(value: Decimal) -> str:
    """Context-independent compact finite-Decimal representation."""

    parts = value.as_tuple()
    digits = list(parts.digits)
    if not any(digits):
        return "0"

    exponent = int(parts.exponent)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1

    digit_text = "".join(str(digit) for digit in digits)
    sign = "-" if parts.sign else ""
    adjusted_exponent = exponent + len(digits) - 1
    mantissa = digit_text[0]
    if len(digit_text) > 1:
        mantissa += "." + digit_text[1:]
    exponent_sign = "+" if adjusted_exponent >= 0 else ""
    compact = f"{sign}{mantissa}e{exponent_sign}{adjusted_exponent}"

    if exponent >= 0:
        fixed_length = len(sign) + len(digit_text) + exponent
    else:
        point = len(digit_text) + exponent
        if point > 0:
            fixed_length = len(sign) + len(digit_text) + 1
        else:
            fixed_length = len(sign) + 2 + (-point) + len(digit_text)

    if fixed_length > len(compact) + 1:
        return compact

    if exponent >= 0:
        fixed = digit_text + ("0" * exponent)
    else:
        point = len(digit_text) + exponent
        if point > 0:
            fixed = digit_text[:point] + "." + digit_text[point:]
        else:
            fixed = "0." + ("0" * (-point)) + digit_text
    return sign + fixed


def _identity_values(value: EconomicIdentityId, *, field_name: str) -> tuple[str, ...]:
    _validate_identity(value, field_name=field_name)
    return (str(value.value),)


@dataclass(frozen=True, slots=True)
class SupplyChainFinanceQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SCF qualification ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ScfEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SCF evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ScfPartyReferenceId:
    """Opaque contract-local party reference; never legal/KYC identity authority."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SCF party reference ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ScfTradeObjectReferenceId:
    """Opaque contractual trade-object reference; never title or provider authority."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SCF trade-object reference ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ScfTradeObjectKindCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SCF trade-object kind code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ScfObligationFormCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SCF obligation-form code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ScfAssignmentQualificationCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SCF assignment qualification code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ScfRecourseQualificationCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SCF recourse qualification code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ScfFundingRuleCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SCF funding-rule code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ScfContractualAmount:
    value: Decimal
    currency_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="SCF contractual amount", positive=True)
        _validate_identity(
            self.currency_identity_id,
            field_name="SCF contractual amount currency identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            _canonical_decimal(self.value),
            _identity_values(
                self.currency_identity_id,
                field_name="SCF contractual amount currency identity",
            ),
        )


@dataclass(frozen=True, slots=True)
class ScfFundingTerms:
    rule: ScfFundingRuleCode
    fixed_amount: ScfContractualAmount | None = None

    def __post_init__(self) -> None:
        if type(self.rule) is not ScfFundingRuleCode:
            _fail("SCF funding rule must be exact ScfFundingRuleCode")
        self.rule.__post_init__()
        if self.fixed_amount is not None:
            if type(self.fixed_amount) is not ScfContractualAmount:
                _fail("SCF fixed funding amount must be exact ScfContractualAmount")
            self.fixed_amount.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.rule.logical_values(),
            None if self.fixed_amount is None else self.fixed_amount.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ReceivablePaymentObligationTerms:
    obligation_reference_id: ScfTradeObjectReferenceId
    obligation_kind: ScfTradeObjectKindCode
    creditor_reference_id: ScfPartyReferenceId
    debtor_reference_id: ScfPartyReferenceId
    face_amount: ScfContractualAmount
    due_date: date
    obligation_form: ScfObligationFormCode
    evidence_ref: ScfEvidenceRef
    economic_identity_id: EconomicIdentityId | None = None

    def __post_init__(self) -> None:
        if type(self.obligation_reference_id) is not ScfTradeObjectReferenceId:
            _fail("SCF obligation reference must be exact ScfTradeObjectReferenceId")
        if type(self.obligation_kind) is not ScfTradeObjectKindCode:
            _fail("SCF obligation kind must be exact ScfTradeObjectKindCode")
        if type(self.creditor_reference_id) is not ScfPartyReferenceId:
            _fail("SCF creditor reference must be exact ScfPartyReferenceId")
        if type(self.debtor_reference_id) is not ScfPartyReferenceId:
            _fail("SCF debtor reference must be exact ScfPartyReferenceId")
        if type(self.face_amount) is not ScfContractualAmount:
            _fail("SCF face amount must be exact ScfContractualAmount")
        if type(self.obligation_form) is not ScfObligationFormCode:
            _fail("SCF obligation form must be exact ScfObligationFormCode")
        if type(self.evidence_ref) is not ScfEvidenceRef:
            _fail("SCF obligation evidence must be exact ScfEvidenceRef")

        self.obligation_reference_id.__post_init__()
        self.obligation_kind.__post_init__()
        self.creditor_reference_id.__post_init__()
        self.debtor_reference_id.__post_init__()
        self.face_amount.__post_init__()
        _validate_date(self.due_date, field_name="SCF obligation due date")
        self.obligation_form.__post_init__()
        self.evidence_ref.__post_init__()

        if self.obligation_kind.value not in {"receivable", "payment-obligation"}:
            _fail(
                "SCF purchased obligation kind must be receivable or payment-obligation"
            )
        if self.economic_identity_id is not None:
            _validate_identity(
                self.economic_identity_id,
                field_name="SCF obligation economic identity",
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.obligation_reference_id.logical_values(),
            self.obligation_kind.logical_values(),
            self.creditor_reference_id.logical_values(),
            self.debtor_reference_id.logical_values(),
            self.face_amount.logical_values(),
            self.due_date.isoformat(),
            self.obligation_form.logical_values(),
            self.evidence_ref.logical_values(),
            None
            if self.economic_identity_id is None
            else _identity_values(
                self.economic_identity_id,
                field_name="SCF obligation economic identity",
            ),
        )


@dataclass(frozen=True, slots=True)
class ScfTradeObjectBinding:
    reference_id: ScfTradeObjectReferenceId
    kind: ScfTradeObjectKindCode
    evidence_ref: ScfEvidenceRef
    economic_identity_id: EconomicIdentityId | None = None

    def __post_init__(self) -> None:
        if type(self.reference_id) is not ScfTradeObjectReferenceId:
            _fail("SCF trade-object reference must be exact ScfTradeObjectReferenceId")
        if type(self.kind) is not ScfTradeObjectKindCode:
            _fail("SCF trade-object kind must be exact ScfTradeObjectKindCode")
        if type(self.evidence_ref) is not ScfEvidenceRef:
            _fail("SCF trade-object evidence must be exact ScfEvidenceRef")
        self.reference_id.__post_init__()
        self.kind.__post_init__()
        self.evidence_ref.__post_init__()
        if self.economic_identity_id is not None:
            _validate_identity(
                self.economic_identity_id,
                field_name="SCF trade-object economic identity",
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.reference_id.logical_values(),
            self.kind.logical_values(),
            self.evidence_ref.logical_values(),
            None
            if self.economic_identity_id is None
            else _identity_values(
                self.economic_identity_id,
                field_name="SCF trade-object economic identity",
            ),
        )


@dataclass(frozen=True, slots=True)
class ReceivablesPurchaseTerms:
    obligations: tuple[ReceivablePaymentObligationTerms, ...]
    transferor_reference_id: ScfPartyReferenceId
    financier_reference_id: ScfPartyReferenceId
    assignment_qualification: ScfAssignmentQualificationCode
    recourse_qualification: ScfRecourseQualificationCode
    funding: ScfFundingTerms
    purchase_date: date
    evidence_ref: ScfEvidenceRef

    def __post_init__(self) -> None:
        if type(self.obligations) is not tuple or not self.obligations:
            _fail("SCF purchase obligations must be a non-empty exact tuple")
        if any(type(item) is not ReceivablePaymentObligationTerms for item in self.obligations):
            _fail("SCF purchase obligations must contain exact obligation terms")
        for item in self.obligations:
            item.__post_init__()

        reference_ids = [item.obligation_reference_id.value for item in self.obligations]
        if len(set(reference_ids)) != len(reference_ids):
            _fail("SCF purchase obligation references must be unique")

        if type(self.transferor_reference_id) is not ScfPartyReferenceId:
            _fail("SCF transferor reference must be exact ScfPartyReferenceId")
        if type(self.financier_reference_id) is not ScfPartyReferenceId:
            _fail("SCF financier reference must be exact ScfPartyReferenceId")
        if type(self.assignment_qualification) is not ScfAssignmentQualificationCode:
            _fail(
                "SCF assignment qualification must be exact ScfAssignmentQualificationCode"
            )
        if type(self.recourse_qualification) is not ScfRecourseQualificationCode:
            _fail(
                "SCF recourse qualification must be exact ScfRecourseQualificationCode"
            )
        if type(self.funding) is not ScfFundingTerms:
            _fail("SCF purchase funding must be exact ScfFundingTerms")
        if type(self.evidence_ref) is not ScfEvidenceRef:
            _fail("SCF purchase evidence must be exact ScfEvidenceRef")

        self.transferor_reference_id.__post_init__()
        self.financier_reference_id.__post_init__()
        self.assignment_qualification.__post_init__()
        self.recourse_qualification.__post_init__()
        self.funding.__post_init__()
        _validate_date(self.purchase_date, field_name="SCF purchase date")
        self.evidence_ref.__post_init__()

        object.__setattr__(
            self,
            "obligations",
            tuple(sorted(self.obligations, key=lambda item: item.logical_values())),
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            tuple(item.logical_values() for item in self.obligations),
            self.transferor_reference_id.logical_values(),
            self.financier_reference_id.logical_values(),
            self.assignment_qualification.logical_values(),
            self.recourse_qualification.logical_values(),
            self.funding.logical_values(),
            self.purchase_date.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class AdvanceBasedFinanceTerms:
    borrower_reference_id: ScfPartyReferenceId
    financier_reference_id: ScfPartyReferenceId
    trade_objects: tuple[ScfTradeObjectBinding, ...]
    funding: ScfFundingTerms
    start_date: date
    evidence_ref: ScfEvidenceRef
    maturity_date: date | None = None
    credit_leg_identity_id: EconomicIdentityId | None = None

    def __post_init__(self) -> None:
        if type(self.borrower_reference_id) is not ScfPartyReferenceId:
            _fail("SCF borrower reference must be exact ScfPartyReferenceId")
        if type(self.financier_reference_id) is not ScfPartyReferenceId:
            _fail("SCF financier reference must be exact ScfPartyReferenceId")
        if type(self.trade_objects) is not tuple or not self.trade_objects:
            _fail("SCF advance trade objects must be a non-empty exact tuple")
        if any(type(item) is not ScfTradeObjectBinding for item in self.trade_objects):
            _fail("SCF advance trade objects must contain exact bindings")
        if type(self.funding) is not ScfFundingTerms:
            _fail("SCF advance funding must be exact ScfFundingTerms")
        if type(self.evidence_ref) is not ScfEvidenceRef:
            _fail("SCF advance evidence must be exact ScfEvidenceRef")

        self.borrower_reference_id.__post_init__()
        self.financier_reference_id.__post_init__()
        for item in self.trade_objects:
            item.__post_init__()
        reference_ids = [item.reference_id.value for item in self.trade_objects]
        if len(set(reference_ids)) != len(reference_ids):
            _fail("SCF advance trade-object references must be unique")
        self.funding.__post_init__()
        _validate_date(self.start_date, field_name="SCF advance start date")
        self.evidence_ref.__post_init__()

        if self.maturity_date is not None:
            _validate_date(self.maturity_date, field_name="SCF advance maturity date")
            if self.maturity_date < self.start_date:
                _fail("SCF advance maturity date must not precede start date")
        if self.credit_leg_identity_id is not None:
            _validate_identity(
                self.credit_leg_identity_id,
                field_name="SCF credit-leg economic identity",
            )

        object.__setattr__(
            self,
            "trade_objects",
            tuple(sorted(self.trade_objects, key=lambda item: item.logical_values())),
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.borrower_reference_id.logical_values(),
            self.financier_reference_id.logical_values(),
            tuple(item.logical_values() for item in self.trade_objects),
            self.funding.logical_values(),
            self.start_date.isoformat(),
            self.evidence_ref.logical_values(),
            None if self.maturity_date is None else self.maturity_date.isoformat(),
            None
            if self.credit_leg_identity_id is None
            else _identity_values(
                self.credit_leg_identity_id,
                field_name="SCF credit-leg economic identity",
            ),
        )


class SupplyChainFinanceTechniqueKind(StrEnum):
    """Versioned technique set retained by the UMI-13 / ICC-2017 scope."""

    RECEIVABLES_DISCOUNTING = "receivables-discounting"
    FACTORING = "factoring"
    FORFAITING = "forfaiting"
    PAYABLES_FINANCE = "payables-finance"
    LOAN_OR_ADVANCE_AGAINST_RECEIVABLES = "loan-or-advance-against-receivables"
    DISTRIBUTOR_FINANCE = "distributor-finance"
    LOAN_OR_ADVANCE_AGAINST_INVENTORY = "loan-or-advance-against-inventory"
    PRE_SHIPMENT_FINANCE = "pre-shipment-finance"


_PURCHASE_TECHNIQUES = frozenset(
    {
        SupplyChainFinanceTechniqueKind.RECEIVABLES_DISCOUNTING,
        SupplyChainFinanceTechniqueKind.FACTORING,
        SupplyChainFinanceTechniqueKind.FORFAITING,
        SupplyChainFinanceTechniqueKind.PAYABLES_FINANCE,
    }
)
_ADVANCE_TECHNIQUES = frozenset(
    {
        SupplyChainFinanceTechniqueKind.LOAN_OR_ADVANCE_AGAINST_RECEIVABLES,
        SupplyChainFinanceTechniqueKind.DISTRIBUTOR_FINANCE,
        SupplyChainFinanceTechniqueKind.LOAN_OR_ADVANCE_AGAINST_INVENTORY,
        SupplyChainFinanceTechniqueKind.PRE_SHIPMENT_FINANCE,
    }
)


@dataclass(frozen=True, slots=True)
class SupplyChainFinanceQualification:
    qualification_id: SupplyChainFinanceQualificationId
    technique: SupplyChainFinanceTechniqueKind
    terms: ReceivablesPurchaseTerms | AdvanceBasedFinanceTerms
    effective_date: date
    evidence_ref: ScfEvidenceRef
    end_date: date | None = None

    def __post_init__(self) -> None:
        if type(self.qualification_id) is not SupplyChainFinanceQualificationId:
            _fail(
                "SCF qualification ID must be exact SupplyChainFinanceQualificationId"
            )
        if type(self.technique) is not SupplyChainFinanceTechniqueKind:
            _fail("SCF technique must be exact SupplyChainFinanceTechniqueKind")
        if type(self.evidence_ref) is not ScfEvidenceRef:
            _fail("SCF qualification evidence must be exact ScfEvidenceRef")

        self.qualification_id.__post_init__()
        _validate_date(self.effective_date, field_name="SCF qualification effective date")
        self.evidence_ref.__post_init__()
        if self.end_date is not None:
            _validate_date(self.end_date, field_name="SCF qualification end date")
            if self.end_date < self.effective_date:
                _fail("SCF qualification end date must not precede effective date")

        if self.technique in _PURCHASE_TECHNIQUES:
            if type(self.terms) is not ReceivablesPurchaseTerms:
                _fail("SCF purchase technique requires exact ReceivablesPurchaseTerms")
            self.terms.__post_init__()
            if (
                self.technique is SupplyChainFinanceTechniqueKind.FORFAITING
                and self.terms.recourse_qualification.value != "without-recourse"
            ):
                _fail("SCF forfaiting requires without-recourse qualification")
            return

        if self.technique not in _ADVANCE_TECHNIQUES:
            _fail("SCF technique is outside the retained versioned scope")
        if type(self.terms) is not AdvanceBasedFinanceTerms:
            _fail("SCF advance technique requires exact AdvanceBasedFinanceTerms")
        self.terms.__post_init__()

        object_kinds = {item.kind.value for item in self.terms.trade_objects}
        if self.technique is SupplyChainFinanceTechniqueKind.LOAN_OR_ADVANCE_AGAINST_RECEIVABLES:
            if not object_kinds.issubset({"receivable", "payment-obligation"}):
                _fail(
                    "SCF receivables advance requires receivable/payment-obligation objects"
                )
        elif self.technique is SupplyChainFinanceTechniqueKind.LOAN_OR_ADVANCE_AGAINST_INVENTORY:
            if object_kinds != {"inventory"}:
                _fail("SCF inventory advance requires inventory trade objects")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.qualification_id.logical_values(),
            self.technique.value,
            self.terms.logical_values(),
            self.effective_date.isoformat(),
            self.evidence_ref.logical_values(),
            None if self.end_date is None else self.end_date.isoformat(),
        )
