from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from qore.infrastructure import loan_credit_facility_semantics as s
from qore.infrastructure.fixed_income_economics import (
    DayCountConventionCode,
    FinancialTenor,
    FinancialTenorUnit,
    FixedIncomeBenchmarkReference,
    FixedIncomeReferenceRoleCode,
    FixedIncomeSpread,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def uid(value: int) -> UUID:
    return UUID(int=value)


def economic(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(uid(value))


def party(value: int) -> s.LoanPartyReferenceId:
    return s.LoanPartyReferenceId(uid(value))


def evidence(value: int = 900) -> s.LoanEvidenceRef:
    return s.LoanEvidenceRef(uid(value))


def tenor(months: int = 3) -> FinancialTenor:
    return FinancialTenor(months, FinancialTenorUnit.MONTH)


def benchmark() -> FixedIncomeBenchmarkReference:
    return FixedIncomeBenchmarkReference(
        economic(700),
        FixedIncomeReferenceRoleCode("loan-base-rate"),
        tenor(),
    )


def fixed_interest() -> s.FixedLoanInterestTerms:
    return s.FixedLoanInterestTerms(
        s.LoanInterestRate(Decimal("0.05")),
        DayCountConventionCode("act-360"),
        tenor(),
    )


def floating_interest() -> s.FloatingLoanInterestTerms:
    return s.FloatingLoanInterestTerms(
        benchmark(),
        FixedIncomeSpread(Decimal("0.0125")),
        DayCountConventionCode("act-360"),
        tenor(),
        tenor(),
    )


def facility() -> s.LoanFacilityTerms:
    schedule = s.LoanCommitmentSchedule(
        (
            s.LoanCommitmentChange(
                date(2028, 1, 1),
                s.LoanCommitmentAmount(Decimal("0")),
            ),
            s.LoanCommitmentChange(
                date(2027, 1, 1),
                s.LoanCommitmentAmount(Decimal("500000")),
            ),
        )
    )
    return s.LoanFacilityTerms(
        s.LoanFacilityId(uid(2)),
        s.LoanDealId(uid(1)),
        economic(10),
        (party(21), party(20)),
        economic(30),
        (economic(31), economic(30)),
        s.LoanFacilityTypeCode("revolving-credit"),
        date(2026, 1, 1),
        date(2030, 1, 1),
        s.LoanCommitmentAmount(Decimal("1000000")),
        schedule,
        evidence(1002),
    )


def amortization() -> s.LoanAmortizationSchedule:
    return s.LoanAmortizationSchedule(
        (
            s.LoanPrincipalRepayment(
                2,
                date(2029, 12, 31),
                s.LoanPrincipalAmount(Decimal("50000")),
            ),
            s.LoanPrincipalRepayment(
                1,
                date(2028, 12, 31),
                s.LoanPrincipalAmount(Decimal("50000")),
            ),
        )
    )


def loan_one() -> s.LoanContractTerms:
    return s.LoanContractTerms(
        s.LoanContractId(uid(3)),
        s.LoanFacilityId(uid(2)),
        economic(11),
        party(20),
        economic(30),
        s.LoanPrincipalAmount(Decimal("100000")),
        date(2026, 2, 1),
        date(2029, 12, 31),
        fixed_interest(),
        amortization(),
        evidence(1003),
    )


def loan_two() -> s.LoanContractTerms:
    return s.LoanContractTerms(
        s.LoanContractId(uid(4)),
        s.LoanFacilityId(uid(2)),
        economic(12),
        party(21),
        economic(31),
        s.LoanPrincipalAmount(Decimal("200000")),
        date(2026, 3, 1),
        date(2029, 6, 30),
        floating_interest(),
        s.LoanAmortizationSchedule(()),
        evidence(1004),
    )


def covenants() -> tuple[s.LoanCovenantTerms, ...]:
    return (
        s.LoanCovenantTerms(
            s.LoanCovenantId(uid(6)),
            s.LoanDealId(uid(1)),
            s.LoanCovenantKind.INFORMATION,
            s.LoanCovenantCode("quarterly-reporting"),
            tenor(),
            None,
            evidence(1006),
        ),
        s.LoanCovenantTerms(
            s.LoanCovenantId(uid(5)),
            s.LoanDealId(uid(1)),
            s.LoanCovenantKind.FINANCIAL,
            s.LoanCovenantCode("leverage-test"),
            tenor(),
            s.LoanFacilityId(uid(2)),
            evidence(1005),
        ),
    )


def syndication() -> s.LoanSyndicationTerms:
    return s.LoanSyndicationTerms(
        s.LoanSyndicationId(uid(7)),
        s.LoanDealId(uid(1)),
        s.LoanFacilityId(uid(2)),
        party(40),
        (
            s.OriginalLoanLenderShare(
                party(42),
                s.LoanParticipationShare(Decimal("0.4")),
            ),
            s.OriginalLoanLenderShare(
                party(41),
                s.LoanParticipationShare(Decimal("0.6")),
            ),
        ),
        evidence(1007),
    )


def valid_deal(*, reverse_contracts: bool = False) -> s.LoanCreditFacilityDeal:
    contracts = (
        (loan_two(), loan_one())
        if reverse_contracts
        else (loan_one(), loan_two())
    )
    return s.LoanCreditFacilityDeal(
        s.LoanDealId(uid(1)),
        economic(1),
        (facility(),),
        contracts,
        covenants(),
        (syndication(),),
        evidence(1001),
    )


def test_commitment_and_amortization_schedules_are_canonical() -> None:
    item = facility()
    schedule = item.commitment_schedule
    assert schedule is not None
    assert [change.effective_date for change in schedule.changes] == [
        date(2027, 1, 1),
        date(2028, 1, 1),
    ]
    assert [repayment.ordinal for repayment in amortization().repayments] == [1, 2]


def test_deal_contract_order_is_nonsemantic() -> None:
    assert valid_deal().logical_values() == valid_deal(
        reverse_contracts=True
    ).logical_values()


def test_deal_facility_and_loan_contract_are_distinct_semantics() -> None:
    deal = valid_deal()
    assert deal.deal_id.logical_values() == (str(uid(1)),)
    assert deal.facilities[0].facility_id.logical_values() == (str(uid(2)),)
    assert deal.loan_contracts[0].loan_contract_id.logical_values() != (
        deal.facilities[0].facility_id.logical_values()
    )


def test_party_reference_is_not_economic_identity() -> None:
    borrower = party(20)
    assert not isinstance(borrower, EconomicIdentityId)
    assert borrower.logical_values() == (str(uid(20)),)


def test_deal_facility_and_loan_economic_identities_cannot_conflate() -> None:
    deal = valid_deal()
    facility_identity = deal.facilities[0].facility_identity_id
    loan_identity = deal.loan_contracts[0].loan_identity_id

    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, deal_identity_id=facility_identity)
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, deal_identity_id=loan_identity)

    bad_loan = replace(
        deal.loan_contracts[0],
        loan_identity_id=facility_identity,
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, loan_contracts=(bad_loan, *deal.loan_contracts[1:]))

    duplicate_loan_identity = replace(
        deal.loan_contracts[1],
        loan_identity_id=loan_identity,
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            deal,
            loan_contracts=(
                deal.loan_contracts[0],
                duplicate_loan_identity,
            ),
        )

    duplicate_facility_identity = replace(
        deal.facilities[0],
        facility_id=s.LoanFacilityId(uid(888)),
        evidence_ref=evidence(888),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            deal,
            facilities=(deal.facilities[0], duplicate_facility_identity),
        )


def test_undrawn_facility_is_valid() -> None:
    deal = valid_deal()
    undrawn = replace(deal, loan_contracts=())
    assert undrawn.loan_contracts == ()


def test_foreign_facility_reference_fails_closed() -> None:
    deal = valid_deal()
    bad = replace(
        deal.loan_contracts[0],
        facility_id=s.LoanFacilityId(uid(999)),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, loan_contracts=(bad, *deal.loan_contracts[1:]))


def test_unpermitted_borrower_fails_closed() -> None:
    deal = valid_deal()
    bad = replace(deal.loan_contracts[0], borrower_party_ref=party(999))
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, loan_contracts=(bad, *deal.loan_contracts[1:]))


def test_unpermitted_draw_currency_fails_closed() -> None:
    deal = valid_deal()
    bad = replace(
        deal.loan_contracts[0],
        denomination_currency_identity_id=economic(999),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, loan_contracts=(bad, *deal.loan_contracts[1:]))


def test_loan_date_must_fit_facility_window() -> None:
    deal = valid_deal()
    bad_start = replace(deal.loan_contracts[0], start_date=date(2025, 12, 31))
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, loan_contracts=(bad_start, *deal.loan_contracts[1:]))
    bad_maturity = replace(deal.loan_contracts[0], maturity_date=date(2031, 1, 1))
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, loan_contracts=(bad_maturity, *deal.loan_contracts[1:]))


def test_repayment_date_must_fit_loan_window() -> None:
    loan = loan_one()
    bad_schedule = s.LoanAmortizationSchedule(
        (
            s.LoanPrincipalRepayment(
                1,
                date(2030, 1, 1),
                s.LoanPrincipalAmount(Decimal("1")),
            ),
        )
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(loan, amortization_schedule=bad_schedule)


def test_commitment_change_must_fit_facility_window() -> None:
    item = facility()
    bad = s.LoanCommitmentSchedule(
        (
            s.LoanCommitmentChange(
                date(2031, 1, 1),
                s.LoanCommitmentAmount(Decimal("1")),
            ),
        )
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(item, commitment_schedule=bad)


def test_duplicate_commitment_dates_fail_closed() -> None:
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanCommitmentSchedule(
            (
                s.LoanCommitmentChange(
                    date(2027, 1, 1),
                    s.LoanCommitmentAmount(Decimal("1")),
                ),
                s.LoanCommitmentChange(
                    date(2027, 1, 1),
                    s.LoanCommitmentAmount(Decimal("2")),
                ),
            )
        )


def test_original_commitment_positive_but_schedule_can_reduce_to_zero() -> None:
    schedule = facility().commitment_schedule
    assert schedule is not None
    assert schedule.changes[-1].commitment.logical_values() == ("0",)
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            facility(),
            original_commitment=s.LoanCommitmentAmount(Decimal("0")),
        )


def test_interest_rate_and_spread_are_not_conflated() -> None:
    fixed = fixed_interest()
    floating = floating_interest()
    assert fixed.logical_values()[0] == "fixed"
    assert floating.logical_values()[0] == "floating"
    assert fixed.logical_values() != floating.logical_values()
    assert isinstance(floating.spread, FixedIncomeSpread)
    assert not isinstance(fixed.rate, FixedIncomeSpread)


def test_negative_contractual_rate_is_representable_without_float() -> None:
    rate = s.LoanInterestRate(Decimal("-0.0025"))
    assert rate.logical_values() == ("-0.0025",)
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanInterestRate(Decimal("NaN"))


def test_syndication_shares_are_canonical_and_sum_exactly_one() -> None:
    terms = syndication()
    assert [
        item.lender_party_ref for item in terms.original_lender_shares
    ] == [party(41), party(42)]
    bad = (
        s.OriginalLoanLenderShare(
            party(41),
            s.LoanParticipationShare(Decimal("0.7")),
        ),
        s.OriginalLoanLenderShare(
            party(42),
            s.LoanParticipationShare(Decimal("0.4")),
        ),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(terms, original_lender_shares=bad)


def test_bilateral_deal_can_omit_syndication_terms() -> None:
    deal = valid_deal()
    bilateral = replace(deal, syndication_terms=())
    assert bilateral.syndication_terms == ()


def test_syndication_facility_reference_must_resolve() -> None:
    deal = valid_deal()
    bad = replace(
        deal.syndication_terms[0],
        facility_id=s.LoanFacilityId(uid(999)),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, syndication_terms=(bad,))


def test_duplicate_syndication_lenders_fail_closed() -> None:
    terms = syndication()
    first = terms.original_lender_shares[0]
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(terms, original_lender_shares=(first, first))


def test_covenant_facility_reference_must_resolve() -> None:
    deal = valid_deal()
    bad = replace(
        deal.covenants[0],
        facility_id=s.LoanFacilityId(uid(999)),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, covenants=(bad, *deal.covenants[1:]))


def test_covenant_is_contractual_qualification_not_evaluation() -> None:
    covenant = covenants()[1]
    assert covenant.kind is s.LoanCovenantKind.FINANCIAL
    assert covenant.covenant_code.logical_values() == ("leverage-test",)
    assert not hasattr(covenant, "evaluate")
    assert not hasattr(covenant, "breached")


def test_duplicate_ids_fail_closed() -> None:
    deal = valid_deal()
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, loan_contracts=(deal.loan_contracts[0], deal.loan_contracts[0]))
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, covenants=(deal.covenants[0], deal.covenants[0]))
    duplicate_facility = replace(
        deal.facilities[0],
        evidence_ref=evidence(9999),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, facilities=(deal.facilities[0], duplicate_facility))


def test_strict_int_date_decimal_uuid_and_code_validation() -> None:
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanDealId("x")  # type: ignore[arg-type]
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanPartyReferenceId("x")  # type: ignore[arg-type]
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanPrincipalRepayment(
            True,
            date(2027, 1, 1),
            s.LoanPrincipalAmount(Decimal("1")),
        )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanPrincipalRepayment(
            1,
            "2027-01-01",  # type: ignore[arg-type]
            s.LoanPrincipalAmount(Decimal("1")),
        )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanPrincipalAmount(Decimal("0"))
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanFacilityTypeCode("Revolver")


def test_public_values_are_frozen_and_slotted() -> None:
    sample = s.LoanFacilityTypeCode("term-loan")
    assert is_dataclass(sample)
    assert hasattr(type(sample), "__slots__")
    assert [field.name for field in fields(sample)] == ["value"]
    with pytest.raises(FrozenInstanceError):
        sample.value = "other"  # type: ignore[misc]


def test_source_has_no_operational_or_provider_authority() -> None:
    assert s.__file__ is not None
    source = Path(s.__file__).read_text(encoding="utf-8")
    forbidden = (
        "requests",
        "httpx",
        "sqlalchemy",
        "sqlite3",
        "threading",
        "asyncio",
        "uuid4",
        "datetime.now",
        "def execute",
        "def calculate",
        "def evaluate",
        "def settle",
        "def submit",
    )
    assert all(token not in source for token in forbidden)


def test_static_terms_do_not_expose_current_balance_or_lender_position() -> None:
    deal = valid_deal()
    assert not hasattr(deal, "current_balance")
    assert not hasattr(deal.loan_contracts[0], "outstanding_balance")
    assert not hasattr(deal.syndication_terms[0], "current_lender_position")


def test_deal_logical_material_retains_all_bounded_components() -> None:
    values = valid_deal().logical_values()
    facilities = values[2]
    contracts = values[3]
    covenant_values = values[4]
    assert values[0] == (str(uid(1)),)
    assert isinstance(facilities, tuple)
    assert isinstance(contracts, tuple)
    assert isinstance(covenant_values, tuple)
    assert len(facilities) == 1
    assert len(contracts) == 2
    assert len(covenant_values) == 2
    syndication_values = values[5]
    assert isinstance(syndication_values, tuple)
    assert len(syndication_values) == 1


def test_party_slots_reject_economic_identity_at_runtime() -> None:
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            facility(),
            borrower_party_refs=(economic(20),),  # type: ignore[arg-type]
        )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            loan_one(),
            borrower_party_ref=economic(20),  # type: ignore[arg-type]
        )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            syndication(),
            agent_party_ref=economic(40),  # type: ignore[arg-type]
        )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.OriginalLoanLenderShare(
            economic(41),  # type: ignore[arg-type]
            s.LoanParticipationShare(Decimal("1")),
        )


def test_parent_deal_bindings_fail_closed() -> None:
    deal = valid_deal()
    foreign_deal = s.LoanDealId(uid(999))

    bad_facility = replace(deal.facilities[0], deal_id=foreign_deal)
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, facilities=(bad_facility,))

    bad_covenant = replace(deal.covenants[0], deal_id=foreign_deal)
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, covenants=(bad_covenant, *deal.covenants[1:]))

    bad_syndication = replace(
        deal.syndication_terms[0],
        deal_id=foreign_deal,
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(deal, syndication_terms=(bad_syndication,))


def test_duplicate_syndication_definition_per_facility_fails_closed() -> None:
    deal = valid_deal()
    duplicate_scope = replace(
        deal.syndication_terms[0],
        syndication_id=s.LoanSyndicationId(uid(7001)),
        evidence_ref=evidence(7002),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            deal,
            syndication_terms=(deal.syndication_terms[0], duplicate_scope),
        )


def test_amortization_rejects_duplicate_ordinals_and_backward_dates() -> None:
    first = s.LoanPrincipalRepayment(
        1,
        date(2028, 1, 1),
        s.LoanPrincipalAmount(Decimal("1")),
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanAmortizationSchedule(
            (
                first,
                replace(first, principal_amount=s.LoanPrincipalAmount(Decimal("2"))),
            )
        )

    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanAmortizationSchedule(
            (
                s.LoanPrincipalRepayment(
                    1,
                    date(2029, 1, 1),
                    s.LoanPrincipalAmount(Decimal("1")),
                ),
                s.LoanPrincipalRepayment(
                    2,
                    date(2028, 1, 1),
                    s.LoanPrincipalAmount(Decimal("1")),
                ),
            )
        )


def test_commitment_and_participation_bounds_fail_closed() -> None:
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanCommitmentAmount(Decimal("-0.01"))
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanParticipationShare(Decimal("0"))
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanParticipationShare(Decimal("1.0001"))


def test_facility_and_loan_local_chronology_fail_closed() -> None:
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            facility(),
            maturity_date=date(2026, 1, 1),
        )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(
            loan_one(),
            maturity_date=date(2026, 2, 1),
        )


def test_commitment_change_cannot_predate_facility_start() -> None:
    bad = s.LoanCommitmentSchedule(
        (
            s.LoanCommitmentChange(
                date(2025, 12, 31),
                s.LoanCommitmentAmount(Decimal("1")),
            ),
        )
    )
    with pytest.raises(s.LoanCreditFacilityValidationError):
        replace(facility(), commitment_schedule=bad)


def test_canonicalizes_borrowers_currencies_and_covenants() -> None:
    item = facility()
    assert item.borrower_party_refs == (party(20), party(21))
    assert item.allowed_draw_currency_identity_ids == (
        economic(30),
        economic(31),
    )

    deal = valid_deal()
    assert [item.covenant_id for item in deal.covenants] == [
        s.LoanCovenantId(uid(5)),
        s.LoanCovenantId(uid(6)),
    ]


def test_empty_commitment_schedule_is_rejected_when_present() -> None:
    with pytest.raises(s.LoanCreditFacilityValidationError):
        s.LoanCommitmentSchedule(())
