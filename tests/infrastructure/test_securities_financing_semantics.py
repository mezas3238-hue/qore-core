from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.fixed_income_economics import DayCountConventionCode
from qore.infrastructure.securities_financing_semantics import (
    MarginLendingTerms,
    RepoFarLegTerms,
    RepoTerms,
    SecuritiesFinancingValidationError,
    SecuritiesLendingCompensationTerms,
    SecuritiesLendingTerms,
    SftArrangementMode,
    SftArrangementTerms,
    SftCashAmount,
    SftCollateralEligibilityCode,
    SftDurationMode,
    SftDurationTerms,
    SftEvidenceRef,
    SftMarginTerms,
    SftPartyReferenceId,
    SftRateKind,
    SftRateTerms,
    SftSecurityQuantity,
    SftTermsId,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _terms_id(value: int = 100) -> SftTermsId:
    return SftTermsId(_uuid(value))


def _evidence(value: int = 200) -> SftEvidenceRef:
    return SftEvidenceRef(_uuid(value))


def _party(value: int) -> SftPartyReferenceId:
    return SftPartyReferenceId(_uuid(value))


def _cash(amount: str = "1000000", currency: int = 300) -> SftCashAmount:
    return SftCashAmount(Decimal(amount), _identity(currency))


def _security(identity: int = 400, quantity: str = "100") -> SftSecurityQuantity:
    return SftSecurityQuantity(_identity(identity), Decimal(quantity))


def _fixed_rate(value: str = "0.03") -> SftRateTerms:
    return SftRateTerms(
        kind=SftRateKind.FIXED,
        contractual_rate_or_spread=Decimal(value),
        day_count=DayCountConventionCode("act-360"),
    )


def _floating_rate(value: str = "0.001") -> SftRateTerms:
    return SftRateTerms(
        kind=SftRateKind.FLOATING,
        contractual_rate_or_spread=Decimal(value),
        day_count=DayCountConventionCode("act-360"),
        floating_reference_identity_id=_identity(500),
    )


def _term_duration() -> SftDurationTerms:
    return SftDurationTerms(
        mode=SftDurationMode.TERM,
        start_date=date(2026, 1, 2),
        termination_date=date(2026, 2, 2),
    )


def _open_duration() -> SftDurationTerms:
    return SftDurationTerms(
        mode=SftDurationMode.OPEN,
        start_date=date(2026, 1, 2),
        notice_days=1,
    )


def _callable_duration() -> SftDurationTerms:
    return SftDurationTerms(
        mode=SftDurationMode.CALLABLE,
        start_date=date(2026, 1, 2),
        termination_date=date(2026, 6, 2),
        notice_days=2,
    )


def _bilateral() -> SftArrangementTerms:
    return SftArrangementTerms(SftArrangementMode.BILATERAL)


def _tri_party() -> SftArrangementTerms:
    return SftArrangementTerms(
        SftArrangementMode.TRI_PARTY,
        tri_party_agent_reference_id=_party(50),
    )


def _term_repo() -> RepoTerms:
    return RepoTerms(
        terms_id=_terms_id(101),
        instrument_identity_id=_identity(10),
        seller_reference_id=_party(1),
        buyer_reference_id=_party(2),
        duration=_term_duration(),
        near_cash=_cash(),
        transferred_securities=(_security(402, "50"), _security(401)),
        financing_rate=_fixed_rate(),
        arrangement=_bilateral(),
        far_leg=RepoFarLegTerms(
            repurchase_date=date(2026, 2, 2),
            repurchase_cash=_cash("1002500"),
        ),
        margin_terms=SftMarginTerms(haircut_ratio=Decimal("0.02")),
        evidence_ref=_evidence(201),
    )


def _securities_loan() -> SecuritiesLendingTerms:
    return SecuritiesLendingTerms(
        terms_id=_terms_id(102),
        instrument_identity_id=_identity(20),
        lender_reference_id=_party(3),
        borrower_reference_id=_party(4),
        duration=_open_duration(),
        principal_security=_security(410, "250"),
        compensation=SecuritiesLendingCompensationTerms(
            lending_fee_rate=Decimal("0.0025"),
            cash_collateral_rebate_rate=Decimal("-0.001"),
        ),
        collateral=(_security(411, "75"), _cash("500000", 301)),
        arrangement=_tri_party(),
        margin_terms=SftMarginTerms(initial_margin_ratio=Decimal("1.05")),
        evidence_ref=_evidence(202),
    )


def _margin_loan() -> MarginLendingTerms:
    return MarginLendingTerms(
        terms_id=_terms_id(103),
        instrument_identity_id=_identity(30),
        lender_reference_id=_party(5),
        borrower_reference_id=_party(6),
        duration=_callable_duration(),
        credit_limit=_cash("2500000", 302),
        financing_rate=_floating_rate("0.015"),
        collateral_eligibility=SftCollateralEligibilityCode("prime-broker-approved"),
        eligible_collateral_identity_ids=(_identity(421), _identity(420)),
        arrangement=_bilateral(),
        margin_terms=SftMarginTerms(haircut_ratio=Decimal("0.25")),
        evidence_ref=_evidence(203),
    )


class _HostileDecimal(Decimal):
    def is_finite(self) -> bool:
        return True


class _HostileUUID(UUID):
    def __str__(self) -> str:
        return "spoofed-uuid"


class _IdentitySubclass(EconomicIdentityId):
    __slots__ = ()


class _DayCountSubclass(DayCountConventionCode):
    __slots__ = ()


class _CashSubclass(SftCashAmount):
    __slots__ = ()


class _DurationSubclass(SftDurationTerms):
    __slots__ = ()


def _malformed_identity() -> EconomicIdentityId:
    return EconomicIdentityId(cast(Any, _HostileUUID(int=99)))


def _malformed_terms_id() -> SftTermsId:
    value = object.__new__(SftTermsId)
    object.__setattr__(value, "value", cast(Any, _HostileUUID(int=101)))
    return value


def _malformed_party() -> SftPartyReferenceId:
    value = object.__new__(SftPartyReferenceId)
    object.__setattr__(value, "value", cast(Any, _HostileUUID(int=1)))
    return value


def test_owner_ids_are_exact_uuid_backed_and_repeatable() -> None:
    values = (SftTermsId(_uuid(1)), SftEvidenceRef(_uuid(2)), _party(3))
    assert [item.logical_values() for item in values] == [
        (str(_uuid(1)),),
        (str(_uuid(2)),),
        (str(_uuid(3)),),
    ]
    for item in values:
        assert item.logical_values() == item.logical_values()


@pytest.mark.parametrize("factory", [SftTermsId, SftEvidenceRef, SftPartyReferenceId])
def test_owner_ids_reject_raw_and_uuid_subclass(factory: Any) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        factory(cast(Any, str(_uuid(1))))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        factory(cast(Any, _HostileUUID(int=1)))


@pytest.mark.parametrize(
    "value",
    ["", "UPPER", "bad code", "a" * 65, cast(Any, 7), cast(Any, True)],
)
def test_collateral_eligibility_code_fails_closed(value: object) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftCollateralEligibilityCode(cast(Any, value))


def test_cash_amount_preserves_amount_and_currency_without_virtual_identity_trust() -> None:
    value = _cash("1000.00", 300)
    assert value.logical_values() == ("1000", (str(_uuid(300)),))


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity"])
def test_cash_amount_requires_positive_finite_decimal(value: str) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftCashAmount(Decimal(value), _identity(300))


def test_cash_amount_rejects_decimal_and_identity_subclasses() -> None:
    with pytest.raises(SecuritiesFinancingValidationError, match="exact Decimal"):
        SftCashAmount(cast(Any, _HostileDecimal("1")), _identity(300))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact EconomicIdentityId"):
        SftCashAmount(Decimal("1"), _IdentitySubclass(_uuid(300)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        SftCashAmount(Decimal("1"), _malformed_identity())


def test_security_quantity_preserves_reference_and_quantity() -> None:
    assert _security(400, "12.500").logical_values() == (
        (str(_uuid(400)),),
        "12.5",
    )


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity"])
def test_security_quantity_requires_positive_finite_decimal(value: str) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftSecurityQuantity(_identity(400), Decimal(value))


def test_rate_terms_reuse_and_revalidate_certified_day_count() -> None:
    fixed = _fixed_rate("-0.001")
    assert fixed.logical_values() == ("fixed", "-0.001", ("act-360",), None)
    floating = _floating_rate("0.00125")
    assert floating.logical_values() == (
        "floating",
        "0.00125",
        ("act-360",),
        (str(_uuid(500)),),
    )


def test_rate_terms_fixed_and_floating_reference_rules() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftRateTerms(
            SftRateKind.FIXED,
            Decimal("0.01"),
            DayCountConventionCode("act-360"),
            _identity(500),
        )
    with pytest.raises(SecuritiesFinancingValidationError):
        SftRateTerms(
            SftRateKind.FLOATING,
            Decimal("0.01"),
            DayCountConventionCode("act-360"),
        )


def test_rate_terms_reject_imported_subclasses_and_malformed_exact_children() -> None:
    with pytest.raises(SecuritiesFinancingValidationError, match="exact DayCountConventionCode"):
        SftRateTerms(
            SftRateKind.FIXED,
            Decimal("0.01"),
            _DayCountSubclass("act-360"),
        )
    malformed = object.__new__(DayCountConventionCode)
    object.__setattr__(malformed, "value", "INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        SftRateTerms(SftRateKind.FIXED, Decimal("0.01"), malformed)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact EconomicIdentityId"):
        SftRateTerms(
            SftRateKind.FLOATING,
            Decimal("0.01"),
            DayCountConventionCode("act-360"),
            _IdentitySubclass(_uuid(500)),
        )


def test_duration_modes_are_distinct_and_strict() -> None:
    assert _term_duration().logical_values() == (
        "term",
        "2026-01-02",
        "2026-02-02",
        None,
    )
    assert _open_duration().logical_values() == (
        "open",
        "2026-01-02",
        None,
        1,
    )
    assert _callable_duration().logical_values() == (
        "callable",
        "2026-01-02",
        "2026-06-02",
        2,
    )


def test_duration_mode_contracts_fail_closed() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(SftDurationMode.TERM, date(2026, 1, 1))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(
            SftDurationMode.TERM,
            date(2026, 1, 1),
            date(2026, 2, 1),
            1,
        )
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(
            SftDurationMode.OPEN,
            date(2026, 1, 1),
            date(2026, 2, 1),
        )
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(SftDurationMode.CALLABLE, date(2026, 1, 1))


@pytest.mark.parametrize("notice", [0, -1, True, 1.5, "2"])
def test_notice_days_are_strict_positive_int(notice: object) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(
            SftDurationMode.OPEN,
            date(2026, 1, 1),
            notice_days=cast(Any, notice),
        )


def test_arrangement_modes_are_distinct_and_agent_is_deeply_validated() -> None:
    assert _bilateral().logical_values() == ("bilateral", None)
    assert _tri_party().logical_values() == (
        "tri-party",
        (str(_uuid(50)),),
    )
    with pytest.raises(SecuritiesFinancingValidationError):
        SftArrangementTerms(SftArrangementMode.BILATERAL, _party(50))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftArrangementTerms(SftArrangementMode.TRI_PARTY)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        SftArrangementTerms(SftArrangementMode.TRI_PARTY, _malformed_party())


def test_margin_terms_retain_unbounded_nonnegative_contractual_ratios() -> None:
    value = SftMarginTerms(
        initial_margin_ratio=Decimal("1.05"),
        haircut_ratio=Decimal("0.0250"),
    )
    assert value.logical_values() == ("1.05", "0.025")
    with pytest.raises(SecuritiesFinancingValidationError):
        SftMarginTerms()
    with pytest.raises(SecuritiesFinancingValidationError):
        SftMarginTerms(initial_margin_ratio=Decimal("-0.1"))


def test_repo_far_leg_preserves_supplied_cash_without_calculation() -> None:
    no_cash = RepoFarLegTerms(date(2026, 2, 1))
    with_cash = RepoFarLegTerms(date(2026, 2, 1), _cash("1010"))
    assert no_cash.logical_values() == ("2026-02-01", None)
    assert with_cash.logical_values() == (
        "2026-02-01",
        ("1010", (str(_uuid(300)),)),
    )


def test_term_open_and_callable_repo_far_leg_rules() -> None:
    base = _term_repo()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, far_leg=None)
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, far_leg=RepoFarLegTerms(date(2026, 2, 3)))

    opened = replace(base, duration=_open_duration(), far_leg=None)
    assert opened.far_leg is None
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(opened, far_leg=RepoFarLegTerms(date(2026, 2, 2)))

    callable_without_end = SftDurationTerms(
        SftDurationMode.CALLABLE,
        date(2026, 1, 2),
        notice_days=2,
    )
    callable_repo = replace(base, duration=callable_without_end, far_leg=None)
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(callable_repo, far_leg=RepoFarLegTerms(date(2026, 2, 2)))


def test_repo_supplied_far_cash_currency_must_match_near_cash() -> None:
    base = _term_repo()
    with pytest.raises(SecuritiesFinancingValidationError, match="currencies must match"):
        replace(
            base,
            far_leg=RepoFarLegTerms(
                date(2026, 2, 2),
                _cash("1002500", 999),
            ),
        )


def test_repo_security_basket_is_unique_canonical_and_order_invariant() -> None:
    base = _term_repo()
    ids = tuple(item.security_identity_id.value for item in base.transferred_securities)
    assert ids == tuple(sorted(ids, key=str))
    reversed_repo = replace(
        base,
        transferred_securities=tuple(reversed(base.transferred_securities)),
    )
    assert reversed_repo.logical_values() == base.logical_values()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, transferred_securities=())
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(
            base,
            transferred_securities=(_security(401, "1"), _security(401, "2")),
        )


def test_repo_product_logical_identity_uses_primitive_expected_oracle() -> None:
    repo = _term_repo()
    expected = (
        "repo",
        (str(_uuid(101)),),
        (str(_uuid(10)),),
        (str(_uuid(1)),),
        (str(_uuid(2)),),
        ("term", "2026-01-02", "2026-02-02", None),
        ("1000000", (str(_uuid(300)),)),
        (
            ((str(_uuid(401)),), "100"),
            ((str(_uuid(402)),), "50"),
        ),
        ("fixed", "0.03", ("act-360",), None),
        ("bilateral", None),
        ("2026-02-02", ("1002500", (str(_uuid(300)),))),
        (None, "0.02"),
        (str(_uuid(201)),),
    )
    assert repo.logical_values() == expected


def test_repo_parent_revalidates_malformed_exact_local_children() -> None:
    base = _term_repo()

    bad_cash = object.__new__(SftCashAmount)
    object.__setattr__(bad_cash, "amount", Decimal("0"))
    object.__setattr__(bad_cash, "currency_identity_id", _identity(300))
    with pytest.raises(SecuritiesFinancingValidationError, match="positive"):
        replace(base, near_cash=bad_cash)

    bad_duration = object.__new__(SftDurationTerms)
    object.__setattr__(bad_duration, "mode", SftDurationMode.TERM)
    object.__setattr__(bad_duration, "start_date", date(2026, 2, 2))
    object.__setattr__(bad_duration, "termination_date", date(2026, 1, 2))
    object.__setattr__(bad_duration, "notice_days", None)
    with pytest.raises(SecuritiesFinancingValidationError, match="after start"):
        replace(base, duration=bad_duration)

    bad_security = object.__new__(SftSecurityQuantity)
    object.__setattr__(bad_security, "security_identity_id", _identity(401))
    object.__setattr__(bad_security, "quantity", Decimal("-1"))
    with pytest.raises(SecuritiesFinancingValidationError, match="positive"):
        replace(base, transferred_securities=(bad_security,))


def test_repo_rejects_local_subclasses_and_malformed_exact_ids() -> None:
    base = _term_repo()
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftCashAmount"):
        replace(base, near_cash=_CashSubclass(Decimal("1"), _identity(300)))
    with pytest.raises(SecuritiesFinancingValidationError, match="exact SftDurationTerms"):
        replace(
            base,
            duration=_DurationSubclass(
                SftDurationMode.TERM,
                date(2026, 1, 2),
                date(2026, 2, 2),
            ),
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        replace(base, terms_id=_malformed_terms_id())


def test_securities_lending_fee_and_rebate_remain_distinct() -> None:
    compensation = SecuritiesLendingCompensationTerms(
        lending_fee_rate=Decimal("0.01"),
        cash_collateral_rebate_rate=Decimal("-0.002"),
    )
    assert compensation.logical_values() == ("0.01", "-0.002")
    assert SecuritiesLendingCompensationTerms(
        lending_fee_rate=Decimal("0")
    ).logical_values() == ("0", None)
    assert SecuritiesLendingCompensationTerms(
        cash_collateral_rebate_rate=Decimal("-0.001")
    ).logical_values() == (None, "-0.001")


def test_securities_lending_compensation_fails_closed() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SecuritiesLendingCompensationTerms()
    with pytest.raises(SecuritiesFinancingValidationError):
        SecuritiesLendingCompensationTerms(lending_fee_rate=Decimal("-0.01"))
    with pytest.raises(SecuritiesFinancingValidationError):
        SecuritiesLendingCompensationTerms(
            cash_collateral_rebate_rate=Decimal("NaN")
        )


def test_securities_lending_collateral_role_is_canonical_and_order_invariant() -> None:
    loan = _securities_loan()
    reversed_loan = replace(loan, collateral=tuple(reversed(loan.collateral)))
    assert reversed_loan.logical_values() == loan.logical_values()
    assert loan.collateral[0] == _cash("500000", 301)
    assert loan.collateral[1] == _security(411, "75")
    assert replace(loan, collateral=()).collateral == ()


def test_securities_lending_rejects_duplicate_collateral_role_identity() -> None:
    loan = _securities_loan()
    with pytest.raises(SecuritiesFinancingValidationError, match="duplicate"):
        replace(
            loan,
            collateral=(_cash("1", 301), _cash("2", 301)),
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="duplicate"):
        replace(
            loan,
            collateral=(_security(411, "1"), _security(411, "2")),
        )


def test_securities_lending_product_logical_identity_uses_primitive_expected_oracle() -> None:
    loan = _securities_loan()
    expected = (
        "securities-lending",
        (str(_uuid(102)),),
        (str(_uuid(20)),),
        (str(_uuid(3)),),
        (str(_uuid(4)),),
        ("open", "2026-01-02", None, 1),
        ((str(_uuid(410)),), "250"),
        ("0.0025", "-0.001"),
        (
            ("500000", (str(_uuid(301)),)),
            ((str(_uuid(411)),), "75"),
        ),
        ("tri-party", (str(_uuid(50)),)),
        ("1.05", None),
        (str(_uuid(202)),),
    )
    assert loan.logical_values() == expected


def test_securities_lending_parent_revalidates_malformed_compensation() -> None:
    loan = _securities_loan()
    bad = object.__new__(SecuritiesLendingCompensationTerms)
    object.__setattr__(bad, "lending_fee_rate", Decimal("-1"))
    object.__setattr__(bad, "cash_collateral_rebate_rate", None)
    with pytest.raises(SecuritiesFinancingValidationError, match="non-negative"):
        replace(loan, compensation=bad)


def test_margin_lending_has_arrangement_and_canonical_eligible_collateral() -> None:
    terms = _margin_loan()
    assert terms.arrangement.logical_values() == ("bilateral", None)
    assert tuple(identity.value for identity in terms.eligible_collateral_identity_ids) == (
        _uuid(420),
        _uuid(421),
    )
    reversed_terms = replace(
        terms,
        eligible_collateral_identity_ids=tuple(
            reversed(terms.eligible_collateral_identity_ids)
        ),
    )
    assert reversed_terms.logical_values() == terms.logical_values()


def test_margin_lending_eligible_collateral_constraints() -> None:
    base = _margin_loan()
    assert replace(base, eligible_collateral_identity_ids=()).logical_values()[9] == ()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(
            base,
            eligible_collateral_identity_ids=(_identity(420), _identity(420)),
        )
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(
            base,
            eligible_collateral_identity_ids=(base.instrument_identity_id,),
        )
    with pytest.raises(SecuritiesFinancingValidationError, match="exact EconomicIdentityId"):
        replace(
            base,
            eligible_collateral_identity_ids=(
                _IdentitySubclass(_uuid(420)),
            ),
        )


def test_margin_lending_product_logical_identity_uses_primitive_expected_oracle() -> None:
    terms = _margin_loan()
    expected = (
        "margin-lending",
        (str(_uuid(103)),),
        (str(_uuid(30)),),
        (str(_uuid(5)),),
        (str(_uuid(6)),),
        ("callable", "2026-01-02", "2026-06-02", 2),
        ("2500000", (str(_uuid(302)),)),
        ("floating", "0.015", ("act-360",), (str(_uuid(500)),)),
        ("prime-broker-approved",),
        ((str(_uuid(420)),), (str(_uuid(421)),)),
        ("bilateral", None),
        (None, "0.25"),
        (str(_uuid(203)),),
    )
    assert terms.logical_values() == expected


def test_margin_lending_parent_revalidates_malformed_eligibility_and_margin() -> None:
    base = _margin_loan()
    bad_code = object.__new__(SftCollateralEligibilityCode)
    object.__setattr__(bad_code, "value", "INVALID CODE")
    with pytest.raises(SecuritiesFinancingValidationError, match="canonical lowercase"):
        replace(base, collateral_eligibility=bad_code)

    bad_margin = object.__new__(SftMarginTerms)
    object.__setattr__(bad_margin, "initial_margin_ratio", None)
    object.__setattr__(bad_margin, "haircut_ratio", Decimal("-0.1"))
    with pytest.raises(SecuritiesFinancingValidationError, match="non-negative"):
        replace(base, margin_terms=bad_margin)


def test_three_product_families_do_not_collapse() -> None:
    logical = {
        _term_repo().logical_values()[0],
        _securities_loan().logical_values()[0],
        _margin_loan().logical_values()[0],
    }
    assert logical == {"repo", "securities-lending", "margin-lending"}


def test_parties_are_exact_distinct_and_deeply_validated() -> None:
    repo = _term_repo()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(repo, buyer_reference_id=repo.seller_reference_id)
    with pytest.raises(SecuritiesFinancingValidationError, match="exact UUID"):
        replace(repo, seller_reference_id=_malformed_party())


def test_decimal_canonicalization_is_context_independent_and_scalable() -> None:
    ordinary = SftCashAmount(Decimal("1000.000"), _identity(300))
    with localcontext() as context:
        context.prec = 2
        assert ordinary.logical_values()[0] == "1000"
        huge_positive = SftCashAmount(Decimal("1E+1000000"), _identity(300))
        huge_negative = SftCashAmount(Decimal("1E-1000000"), _identity(300))
        positive_text = cast(str, huge_positive.logical_values()[0])
        negative_text = cast(str, huge_negative.logical_values()[0])
    assert positive_text == "1e+1000000"
    assert negative_text == "1e-1000000"
    assert len(positive_text) == 10
    assert len(negative_text) == 10
    assert Decimal(positive_text) == Decimal("1E+1000000")
    assert Decimal(negative_text) == Decimal("1E-1000000")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", "0"),
        ("-0", "0"),
        ("1.2300", "1.23"),
        ("1000.00", "1000"),
        ("0.00100", "0.001"),
        ("1E+20", "1e+20"),
        ("1E-20", "1e-20"),
    ],
)
def test_decimal_canonical_equivalence(raw: str, expected: str) -> None:
    assert SftCashAmount(Decimal(raw), _identity(300)).logical_values()[0] == expected


def test_logical_values_revalidate_after_reflective_post_construction_mutation() -> None:
    cash = _cash("1")
    object.__setattr__(cash, "amount", Decimal("0"))
    with pytest.raises(SecuritiesFinancingValidationError, match="positive"):
        cash.logical_values()

    repo = _term_repo()
    object.__setattr__(repo.duration, "termination_date", date(2025, 1, 1))
    with pytest.raises(SecuritiesFinancingValidationError, match="after start"):
        repo.logical_values()


def test_all_public_semantic_values_are_frozen_and_slotted() -> None:
    values: tuple[object, ...] = (
        _terms_id(),
        _evidence(),
        _party(1),
        SftCollateralEligibilityCode("approved"),
        _cash(),
        _security(),
        _fixed_rate(),
        _term_duration(),
        _bilateral(),
        SftMarginTerms(haircut_ratio=Decimal("0.1")),
        RepoFarLegTerms(date(2026, 2, 2)),
        SecuritiesLendingCompensationTerms(lending_fee_rate=Decimal("0.1")),
        _term_repo(),
        _securities_loan(),
        _margin_loan(),
    )
    assert all(not hasattr(value, "__dict__") for value in values)
    with pytest.raises(FrozenInstanceError):
        cast(Any, values[4]).amount = Decimal("2")


def test_top_level_field_surfaces_do_not_expose_current_state() -> None:
    repo_fields = {field.name for field in fields(RepoTerms)}
    loan_fields = {field.name for field in fields(SecuritiesLendingTerms)}
    margin_fields = {field.name for field in fields(MarginLendingTerms)}
    forbidden = {
        "current_margin",
        "current_collateral",
        "current_utilization",
        "available_credit",
        "margin_call",
        "position",
        "valuation",
        "provider_symbol",
        "settled",
    }
    assert not repo_fields.intersection(forbidden)
    assert not loan_fields.intersection(forbidden)
    assert not margin_fields.intersection(forbidden)


def test_source_has_exact_type_and_no_context_sensitive_decimal_regression() -> None:
    source = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/securities_financing_semantics.py"
    ).read_text(encoding="utf-8")
    assert "isinstance(" not in source
    assert ".normalize(" not in source
    assert "datetime.now(" not in source
    assert "date.today(" not in source
    assert "uuid4(" not in source
    assert "random." not in source
    assert "secrets." not in source


def test_source_has_no_runtime_financing_or_settlement_authority() -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/securities_financing_semantics.py"
    )
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "asyncio",
        "httpx",
        "numpy",
        "pandas",
        "requests",
        "socket",
        "subprocess",
        "threading",
    }
    imported_names = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not (imported_names | imported_modules).intersection(
        forbidden_import_roots
    )

    forbidden_calls = {
        "calculate",
        "connect",
        "execute",
        "fetch",
        "liquidate",
        "recall",
        "settle",
        "submit",
        "transfer",
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called_names.intersection(forbidden_calls)


@pytest.mark.parametrize(
    "forbidden",
    [
        "current_margin",
        "current_collateral",
        "available_to_borrow",
        "current_utilization",
        "margin_call",
        "provider_symbol",
        "private_key",
        "password",
        "access_token",
    ],
)
def test_source_contains_no_current_or_secret_material(forbidden: str) -> None:
    source = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/securities_financing_semantics.py"
    ).read_text(encoding="utf-8")
    assert forbidden not in source
