from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import Never
from uuid import UUID

from qore.infrastructure.fixed_income_economics import (
    DayCountConventionCode,
    FinancialTenor,
    FixedIncomeBenchmarkReference,
    FixedIncomeSpread,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class LoanCreditFacilitySemanticsError(InfrastructureError):
    __slots__ = ()


class LoanCreditFacilityValidationError(LoanCreditFacilitySemanticsError):
    __slots__ = ()


def _fail(message: str) -> Never:
    raise LoanCreditFacilityValidationError(message)


def _exact(value: object, expected: type[object], name: str) -> None:
    if type(value) is not expected:
        _fail(f"{name} must be exact {expected.__name__}")


def _uuid(value: UUID, name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{name} must be UUID")


def _identity(value: EconomicIdentityId, name: str) -> None:
    if type(value) is not EconomicIdentityId:
        _fail(f"{name} must be exact EconomicIdentityId")


def _date(value: date, name: str) -> None:
    if type(value) is not date:
        _fail(f"{name} must be date")


def _decimal(
    value: Decimal,
    name: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> None:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{name} must be a finite Decimal")
    if positive and value <= 0:
        _fail(f"{name} must be positive")
    if nonnegative and value < 0:
        _fail(f"{name} must be non-negative")


def _code(value: str, name: str) -> None:
    valid = (
        type(value) is str
        and bool(value)
        and len(value) <= 64
        and fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", value) is not None
    )
    if not valid:
        _fail(f"{name} must use canonical lowercase code syntax")


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def _identity_key(value: EconomicIdentityId) -> tuple[str, ...]:
    return value.logical_values()


@dataclass(frozen=True, slots=True)
class _UuidValue:
    value: UUID

    def __post_init__(self) -> None:
        _uuid(self.value, f"{type(self).__name__}.value")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class LoanDealId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class LoanFacilityId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class LoanContractId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class LoanCovenantId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class LoanSyndicationId(_UuidValue):
    pass


@dataclass(frozen=True, slots=True)
class LoanPartyReferenceId(_UuidValue):
    """Contract-local legal-party reference; not UMI-02 economic identity."""


@dataclass(frozen=True, slots=True)
class LoanEvidenceRef(_UuidValue):
    """Opaque retained evidence identity; never evidence content or a secret."""


@dataclass(frozen=True, slots=True)
class LoanFacilityTypeCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "loan facility type code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class LoanCovenantCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "loan covenant code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class LoanCommitmentAmount:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "loan commitment amount", nonnegative=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class LoanPrincipalAmount:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "loan principal amount", positive=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class LoanInterestRate:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "loan interest rate")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class LoanParticipationShare:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "loan participation share", positive=True)
        if self.value > 1:
            _fail("loan participation share must not exceed one")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class LoanCommitmentChange:
    effective_date: date
    commitment: LoanCommitmentAmount

    def __post_init__(self) -> None:
        _date(self.effective_date, "commitment effective_date")
        _exact(self.commitment, LoanCommitmentAmount, "commitment")

    def logical_values(self) -> tuple[object, ...]:
        return (self.effective_date.isoformat(), self.commitment.logical_values())


@dataclass(frozen=True, slots=True)
class LoanCommitmentSchedule:
    changes: tuple[LoanCommitmentChange, ...]

    def __post_init__(self) -> None:
        if type(self.changes) is not tuple or not self.changes:
            _fail("commitment schedule changes must be a non-empty tuple")
        if any(type(item) is not LoanCommitmentChange for item in self.changes):
            _fail("commitment schedule contains a non-canonical change")
        dates = [item.effective_date for item in self.changes]
        if len(set(dates)) != len(dates):
            _fail("commitment schedule effective dates must be unique")
        object.__setattr__(
            self,
            "changes",
            tuple(sorted(self.changes, key=lambda item: item.effective_date)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return tuple(item.logical_values() for item in self.changes)


@dataclass(frozen=True, slots=True)
class FixedLoanInterestTerms:
    rate: LoanInterestRate
    day_count: DayCountConventionCode
    payment_tenor: FinancialTenor

    def __post_init__(self) -> None:
        _exact(self.rate, LoanInterestRate, "fixed loan rate")
        _exact(self.day_count, DayCountConventionCode, "fixed loan day_count")
        _exact(self.payment_tenor, FinancialTenor, "fixed loan payment_tenor")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed",
            self.rate.logical_values(),
            self.day_count.logical_values(),
            self.payment_tenor.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FloatingLoanInterestTerms:
    benchmark: FixedIncomeBenchmarkReference
    spread: FixedIncomeSpread
    day_count: DayCountConventionCode
    payment_tenor: FinancialTenor
    reset_tenor: FinancialTenor

    def __post_init__(self) -> None:
        _exact(
            self.benchmark,
            FixedIncomeBenchmarkReference,
            "floating loan benchmark",
        )
        _exact(self.spread, FixedIncomeSpread, "floating loan spread")
        _exact(self.day_count, DayCountConventionCode, "floating loan day_count")
        _exact(self.payment_tenor, FinancialTenor, "floating loan payment_tenor")
        _exact(self.reset_tenor, FinancialTenor, "floating loan reset_tenor")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "floating",
            self.benchmark.logical_values(),
            self.spread.logical_values(),
            self.day_count.logical_values(),
            self.payment_tenor.logical_values(),
            self.reset_tenor.logical_values(),
        )


type LoanInterestTerms = FixedLoanInterestTerms | FloatingLoanInterestTerms


@dataclass(frozen=True, slots=True)
class LoanPrincipalRepayment:
    ordinal: int
    due_date: date
    principal_amount: LoanPrincipalAmount

    def __post_init__(self) -> None:
        if type(self.ordinal) is not int or self.ordinal <= 0:
            _fail("loan repayment ordinal must be a positive int")
        _date(self.due_date, "loan repayment due_date")
        _exact(
            self.principal_amount,
            LoanPrincipalAmount,
            "loan repayment principal_amount",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.ordinal,
            self.due_date.isoformat(),
            self.principal_amount.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class LoanAmortizationSchedule:
    repayments: tuple[LoanPrincipalRepayment, ...]

    def __post_init__(self) -> None:
        if type(self.repayments) is not tuple:
            _fail("loan amortization repayments must be tuple")
        if any(type(item) is not LoanPrincipalRepayment for item in self.repayments):
            _fail("loan amortization contains a non-canonical repayment")
        ordinals = [item.ordinal for item in self.repayments]
        if len(set(ordinals)) != len(ordinals):
            _fail("loan repayment ordinals must be unique")
        ordered = tuple(sorted(self.repayments, key=lambda item: item.ordinal))
        if any(
            right.due_date < left.due_date
            for left, right in zip(ordered, ordered[1:], strict=False)
        ):
            _fail("loan repayment due dates must not move backward by ordinal")
        object.__setattr__(self, "repayments", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return tuple(item.logical_values() for item in self.repayments)


@dataclass(frozen=True, slots=True)
class LoanFacilityTerms:
    facility_id: LoanFacilityId
    deal_id: LoanDealId
    facility_identity_id: EconomicIdentityId
    borrower_party_refs: tuple[LoanPartyReferenceId, ...]
    commitment_currency_identity_id: EconomicIdentityId
    allowed_draw_currency_identity_ids: tuple[EconomicIdentityId, ...]
    facility_type: LoanFacilityTypeCode
    start_date: date
    maturity_date: date | None
    original_commitment: LoanCommitmentAmount
    commitment_schedule: LoanCommitmentSchedule | None
    evidence_ref: LoanEvidenceRef

    def __post_init__(self) -> None:
        _exact(self.facility_id, LoanFacilityId, "facility_id")
        _exact(self.deal_id, LoanDealId, "facility deal_id")
        _identity(self.facility_identity_id, "facility identity")
        if type(self.borrower_party_refs) is not tuple or not self.borrower_party_refs:
            _fail("facility borrower party refs must be a non-empty tuple")
        if any(
            type(item) is not LoanPartyReferenceId
            for item in self.borrower_party_refs
        ):
            _fail("facility borrower party refs must use exact local type")
        if len(set(self.borrower_party_refs)) != len(self.borrower_party_refs):
            _fail("facility borrower party refs must be unique")
        _identity(
            self.commitment_currency_identity_id,
            "facility commitment currency identity",
        )
        if (
            type(self.allowed_draw_currency_identity_ids) is not tuple
            or not self.allowed_draw_currency_identity_ids
        ):
            _fail("allowed draw currencies must be a non-empty tuple")
        if any(
            type(item) is not EconomicIdentityId
            for item in self.allowed_draw_currency_identity_ids
        ):
            _fail("allowed draw currencies must be exact EconomicIdentityId values")
        if len(set(self.allowed_draw_currency_identity_ids)) != len(
            self.allowed_draw_currency_identity_ids
        ):
            _fail("allowed draw currency identities must be unique")
        _exact(self.facility_type, LoanFacilityTypeCode, "facility_type")
        _date(self.start_date, "facility start_date")
        if self.maturity_date is not None:
            _date(self.maturity_date, "facility maturity_date")
            if self.maturity_date <= self.start_date:
                _fail("facility maturity_date must be after start_date")
        _exact(
            self.original_commitment,
            LoanCommitmentAmount,
            "original_commitment",
        )
        if self.original_commitment.value <= 0:
            _fail("facility original commitment must be positive")
        if self.commitment_schedule is not None:
            _exact(
                self.commitment_schedule,
                LoanCommitmentSchedule,
                "commitment_schedule",
            )
            for change in self.commitment_schedule.changes:
                if change.effective_date < self.start_date:
                    _fail("commitment change must not predate facility start")
                if (
                    self.maturity_date is not None
                    and change.effective_date > self.maturity_date
                ):
                    _fail("commitment change must not follow facility maturity")
        _exact(self.evidence_ref, LoanEvidenceRef, "facility evidence_ref")
        object.__setattr__(
            self,
            "borrower_party_refs",
            tuple(
                sorted(
                    self.borrower_party_refs,
                    key=lambda item: item.logical_values(),
                )
            ),
        )
        object.__setattr__(
            self,
            "allowed_draw_currency_identity_ids",
            tuple(sorted(self.allowed_draw_currency_identity_ids, key=_identity_key)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.facility_id.logical_values(),
            self.deal_id.logical_values(),
            self.facility_identity_id.logical_values(),
            tuple(item.logical_values() for item in self.borrower_party_refs),
            self.commitment_currency_identity_id.logical_values(),
            tuple(
                item.logical_values()
                for item in self.allowed_draw_currency_identity_ids
            ),
            self.facility_type.logical_values(),
            self.start_date.isoformat(),
            self.maturity_date.isoformat() if self.maturity_date is not None else None,
            self.original_commitment.logical_values(),
            self.commitment_schedule.logical_values()
            if self.commitment_schedule is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class LoanContractTerms:
    loan_contract_id: LoanContractId
    facility_id: LoanFacilityId
    loan_identity_id: EconomicIdentityId
    borrower_party_ref: LoanPartyReferenceId
    denomination_currency_identity_id: EconomicIdentityId
    original_principal: LoanPrincipalAmount
    start_date: date
    maturity_date: date
    interest_terms: LoanInterestTerms
    amortization_schedule: LoanAmortizationSchedule
    evidence_ref: LoanEvidenceRef

    def __post_init__(self) -> None:
        _exact(self.loan_contract_id, LoanContractId, "loan_contract_id")
        _exact(self.facility_id, LoanFacilityId, "loan facility_id")
        _identity(self.loan_identity_id, "loan identity")
        _exact(
            self.borrower_party_ref,
            LoanPartyReferenceId,
            "loan borrower party ref",
        )
        _identity(
            self.denomination_currency_identity_id,
            "loan denomination currency identity",
        )
        _exact(self.original_principal, LoanPrincipalAmount, "original_principal")
        _date(self.start_date, "loan start_date")
        _date(self.maturity_date, "loan maturity_date")
        if self.maturity_date <= self.start_date:
            _fail("loan maturity_date must be after start_date")
        if type(self.interest_terms) not in (
            FixedLoanInterestTerms,
            FloatingLoanInterestTerms,
        ):
            _fail("loan interest_terms must be exact fixed or floating loan terms")
        _exact(
            self.amortization_schedule,
            LoanAmortizationSchedule,
            "amortization_schedule",
        )
        for repayment in self.amortization_schedule.repayments:
            if not self.start_date < repayment.due_date <= self.maturity_date:
                _fail("loan repayment date must be after start and on/before maturity")
        _exact(self.evidence_ref, LoanEvidenceRef, "loan evidence_ref")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.loan_contract_id.logical_values(),
            self.facility_id.logical_values(),
            self.loan_identity_id.logical_values(),
            self.borrower_party_ref.logical_values(),
            self.denomination_currency_identity_id.logical_values(),
            self.original_principal.logical_values(),
            self.start_date.isoformat(),
            self.maturity_date.isoformat(),
            self.interest_terms.logical_values(),
            self.amortization_schedule.logical_values(),
            self.evidence_ref.logical_values(),
        )


class LoanCovenantKind(StrEnum):
    FINANCIAL = "financial"
    AFFIRMATIVE = "affirmative"
    NEGATIVE = "negative"
    INFORMATION = "information"


@dataclass(frozen=True, slots=True)
class LoanCovenantTerms:
    covenant_id: LoanCovenantId
    deal_id: LoanDealId
    kind: LoanCovenantKind
    covenant_code: LoanCovenantCode
    testing_tenor: FinancialTenor | None
    facility_id: LoanFacilityId | None
    evidence_ref: LoanEvidenceRef

    def __post_init__(self) -> None:
        _exact(self.covenant_id, LoanCovenantId, "covenant_id")
        _exact(self.deal_id, LoanDealId, "covenant deal_id")
        _exact(self.kind, LoanCovenantKind, "covenant kind")
        _exact(self.covenant_code, LoanCovenantCode, "covenant code")
        if self.testing_tenor is not None:
            _exact(self.testing_tenor, FinancialTenor, "covenant testing_tenor")
        if self.facility_id is not None:
            _exact(self.facility_id, LoanFacilityId, "covenant facility_id")
        _exact(self.evidence_ref, LoanEvidenceRef, "covenant evidence_ref")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.covenant_id.logical_values(),
            self.deal_id.logical_values(),
            self.kind.value,
            self.covenant_code.logical_values(),
            self.testing_tenor.logical_values() if self.testing_tenor else None,
            self.facility_id.logical_values() if self.facility_id else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class OriginalLoanLenderShare:
    lender_party_ref: LoanPartyReferenceId
    share: LoanParticipationShare

    def __post_init__(self) -> None:
        _exact(
            self.lender_party_ref,
            LoanPartyReferenceId,
            "lender party ref",
        )
        _exact(self.share, LoanParticipationShare, "lender share")

    def logical_values(self) -> tuple[object, ...]:
        return (self.lender_party_ref.logical_values(), self.share.logical_values())


@dataclass(frozen=True, slots=True)
class LoanSyndicationTerms:
    syndication_id: LoanSyndicationId
    deal_id: LoanDealId
    facility_id: LoanFacilityId
    agent_party_ref: LoanPartyReferenceId
    original_lender_shares: tuple[OriginalLoanLenderShare, ...]
    evidence_ref: LoanEvidenceRef

    def __post_init__(self) -> None:
        _exact(self.syndication_id, LoanSyndicationId, "syndication_id")
        _exact(self.deal_id, LoanDealId, "syndication deal_id")
        _exact(self.facility_id, LoanFacilityId, "syndication facility_id")
        _exact(
            self.agent_party_ref,
            LoanPartyReferenceId,
            "syndication agent party ref",
        )
        if (
            type(self.original_lender_shares) is not tuple
            or not self.original_lender_shares
        ):
            _fail("original lender shares must be a non-empty tuple")
        if any(
            type(item) is not OriginalLoanLenderShare
            for item in self.original_lender_shares
        ):
            _fail("syndication shares must use exact OriginalLoanLenderShare")
        lenders = [item.lender_party_ref for item in self.original_lender_shares]
        if len(set(lenders)) != len(lenders):
            _fail("original syndication lenders must be unique")
        total = sum(
            (item.share.value for item in self.original_lender_shares),
            Decimal(0),
        )
        if total != Decimal(1):
            _fail("original lender shares must sum exactly to one")
        _exact(self.evidence_ref, LoanEvidenceRef, "syndication evidence_ref")
        object.__setattr__(
            self,
            "original_lender_shares",
            tuple(
                sorted(
                    self.original_lender_shares,
                    key=lambda item: item.lender_party_ref.logical_values(),
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.syndication_id.logical_values(),
            self.deal_id.logical_values(),
            self.facility_id.logical_values(),
            self.agent_party_ref.logical_values(),
            tuple(item.logical_values() for item in self.original_lender_shares),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class LoanCreditFacilityDeal:
    deal_id: LoanDealId
    deal_identity_id: EconomicIdentityId
    facilities: tuple[LoanFacilityTerms, ...]
    loan_contracts: tuple[LoanContractTerms, ...]
    covenants: tuple[LoanCovenantTerms, ...]
    syndication_terms: tuple[LoanSyndicationTerms, ...]
    evidence_ref: LoanEvidenceRef

    def __post_init__(self) -> None:
        _exact(self.deal_id, LoanDealId, "deal_id")
        _identity(self.deal_identity_id, "deal identity")
        self._validate_container_types()
        _exact(self.evidence_ref, LoanEvidenceRef, "deal evidence_ref")

        facility_by_id = self._validate_facilities()
        self._validate_contracts(facility_by_id)
        self._validate_covenants(facility_by_id)
        self._validate_syndication(facility_by_id)
        self._canonicalize()

    def _validate_container_types(self) -> None:
        if type(self.facilities) is not tuple or not self.facilities:
            _fail("loan deal facilities must be a non-empty tuple")
        if any(type(item) is not LoanFacilityTerms for item in self.facilities):
            _fail("loan deal facilities contain a non-canonical value")
        if type(self.loan_contracts) is not tuple:
            _fail("loan deal loan_contracts must be tuple")
        if any(type(item) is not LoanContractTerms for item in self.loan_contracts):
            _fail("loan deal contracts contain a non-canonical value")
        if type(self.covenants) is not tuple:
            _fail("loan deal covenants must be tuple")
        if any(type(item) is not LoanCovenantTerms for item in self.covenants):
            _fail("loan deal covenants contain a non-canonical value")
        if type(self.syndication_terms) is not tuple:
            _fail("loan deal syndication_terms must be tuple")
        if any(
            type(item) is not LoanSyndicationTerms
            for item in self.syndication_terms
        ):
            _fail("loan deal syndication_terms contain a non-canonical value")

    def _validate_facilities(self) -> dict[LoanFacilityId, LoanFacilityTerms]:
        facility_ids = [item.facility_id for item in self.facilities]
        if len(set(facility_ids)) != len(facility_ids):
            _fail("loan facility ids must be unique inside deal")
        if any(item.deal_id != self.deal_id for item in self.facilities):
            _fail("every facility deal_id must match enclosing deal")
        facility_identity_ids = {
            item.facility_identity_id for item in self.facilities
        }
        if len(facility_identity_ids) != len(self.facilities):
            _fail("facility economic identities must be unique inside deal")
        if self.deal_identity_id in facility_identity_ids:
            _fail("deal economic identity must differ from facility identities")
        return {item.facility_id: item for item in self.facilities}

    def _validate_contracts(
        self,
        facility_by_id: dict[LoanFacilityId, LoanFacilityTerms],
    ) -> None:
        contract_ids = [item.loan_contract_id for item in self.loan_contracts]
        if len(set(contract_ids)) != len(contract_ids):
            _fail("loan contract ids must be unique inside deal")
        contract_identity_ids = {
            item.loan_identity_id for item in self.loan_contracts
        }
        if len(contract_identity_ids) != len(self.loan_contracts):
            _fail("loan economic identities must be unique inside deal")
        facility_identity_ids = {
            item.facility_identity_id for item in self.facilities
        }
        if self.deal_identity_id in contract_identity_ids:
            _fail("deal economic identity must differ from loan identities")
        if facility_identity_ids & contract_identity_ids:
            _fail("facility and loan economic identities must not conflate")
        for contract in self.loan_contracts:
            facility = facility_by_id.get(contract.facility_id)
            if facility is None:
                _fail("every loan contract facility_id must resolve inside deal")
            if contract.borrower_party_ref not in facility.borrower_party_refs:
                _fail("loan contract borrower must be permitted by its facility")
            if (
                contract.denomination_currency_identity_id
                not in facility.allowed_draw_currency_identity_ids
            ):
                _fail("loan contract denomination must be allowed by its facility")
            if contract.start_date < facility.start_date:
                _fail("loan contract must not start before its facility")
            if (
                facility.maturity_date is not None
                and contract.maturity_date > facility.maturity_date
            ):
                _fail("loan contract must not mature after its facility")

    def _validate_covenants(
        self,
        facility_by_id: dict[LoanFacilityId, LoanFacilityTerms],
    ) -> None:
        covenant_ids = [item.covenant_id for item in self.covenants]
        if len(set(covenant_ids)) != len(covenant_ids):
            _fail("loan covenant ids must be unique inside deal")
        for covenant in self.covenants:
            if covenant.deal_id != self.deal_id:
                _fail("every covenant deal_id must match enclosing deal")
            if (
                covenant.facility_id is not None
                and covenant.facility_id not in facility_by_id
            ):
                _fail("facility-scoped covenant must resolve to a facility in deal")

    def _validate_syndication(
        self,
        facility_by_id: dict[LoanFacilityId, LoanFacilityTerms],
    ) -> None:
        syndication_ids = [
            item.syndication_id for item in self.syndication_terms
        ]
        if len(set(syndication_ids)) != len(syndication_ids):
            _fail("loan syndication ids must be unique inside deal")
        syndicated_facilities = [
            item.facility_id for item in self.syndication_terms
        ]
        if len(set(syndicated_facilities)) != len(syndicated_facilities):
            _fail("only one original syndication definition is allowed per facility")
        for syndication in self.syndication_terms:
            if syndication.deal_id != self.deal_id:
                _fail("syndication deal_id must match enclosing deal")
            if syndication.facility_id not in facility_by_id:
                _fail("syndication facility_id must resolve inside deal")

    def _canonicalize(self) -> None:
        object.__setattr__(
            self,
            "facilities",
            tuple(
                sorted(
                    self.facilities,
                    key=lambda item: item.facility_id.logical_values(),
                )
            ),
        )
        object.__setattr__(
            self,
            "loan_contracts",
            tuple(
                sorted(
                    self.loan_contracts,
                    key=lambda item: item.loan_contract_id.logical_values(),
                )
            ),
        )
        object.__setattr__(
            self,
            "covenants",
            tuple(
                sorted(
                    self.covenants,
                    key=lambda item: item.covenant_id.logical_values(),
                )
            ),
        )
        object.__setattr__(
            self,
            "syndication_terms",
            tuple(
                sorted(
                    self.syndication_terms,
                    key=lambda item: item.facility_id.logical_values(),
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.deal_id.logical_values(),
            self.deal_identity_id.logical_values(),
            tuple(item.logical_values() for item in self.facilities),
            tuple(item.logical_values() for item in self.loan_contracts),
            tuple(item.logical_values() for item in self.covenants),
            tuple(item.logical_values() for item in self.syndication_terms),
            self.evidence_ref.logical_values(),
        )
