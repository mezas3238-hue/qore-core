from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

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
    SftDayCountCode,
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
        day_count=SftDayCountCode("act-360"),
    )


def _floating_rate(value: str = "0.001") -> SftRateTerms:
    return SftRateTerms(
        kind=SftRateKind.FLOATING,
        contractual_rate_or_spread=Decimal(value),
        day_count=SftDayCountCode("act-360"),
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
        transferred_securities=(_security(401), _security(402, "50")),
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
        collateral=(_cash("500000", 301), _security(411, "75")),
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
        eligible_collateral_identity_ids=(_identity(420), _identity(421)),
        margin_terms=SftMarginTerms(haircut_ratio=Decimal("0.25")),
        evidence_ref=_evidence(203),
    )


def test_uuid_wrappers_are_explicit_and_deterministic() -> None:
    values = (SftTermsId(_uuid(1)), SftEvidenceRef(_uuid(2)), _party(3))
    assert [item.logical_values() for item in values] == [
        (str(_uuid(1)),),
        (str(_uuid(2)),),
        (str(_uuid(3)),),
    ]


@pytest.mark.parametrize("factory", [SftTermsId, SftEvidenceRef, SftPartyReferenceId])
def test_uuid_wrappers_reject_raw_strings(factory: Any) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        factory(cast(Any, str(_uuid(1))))


@pytest.mark.parametrize("factory", [SftDayCountCode, SftCollateralEligibilityCode])
@pytest.mark.parametrize("value", ["", "UPPER", "bad code", "a" * 65, 7])
def test_code_wrappers_fail_closed(factory: Any, value: object) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        factory(cast(Any, value))


def test_cash_amount_preserves_amount_and_currency() -> None:
    value = _cash("1000.00", 300)
    assert value.logical_values() == ("1000", _identity(300).logical_values())


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity"])
def test_cash_amount_requires_positive_finite_decimal(value: str) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftCashAmount(Decimal(value), _identity(300))


def test_cash_amount_rejects_raw_currency_and_non_decimal() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftCashAmount(Decimal("1"), cast(Any, _uuid(300)))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftCashAmount(cast(Any, 1.0), _identity(300))


def test_security_quantity_preserves_reference_and_quantity() -> None:
    value = _security(400, "12.500")
    assert value.logical_values() == (_identity(400).logical_values(), "12.5")


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity"])
def test_security_quantity_requires_positive_finite_decimal(value: str) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftSecurityQuantity(_identity(400), Decimal(value))


def test_security_quantity_rejects_raw_identity_and_non_decimal() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftSecurityQuantity(cast(Any, _uuid(400)), Decimal("1"))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftSecurityQuantity(_identity(400), cast(Any, 1.0))


def test_fixed_rate_retains_negative_contractual_rate_without_reference() -> None:
    value = _fixed_rate("-0.001")
    assert value.logical_values() == ("fixed", "-0.001", ("act-360",), None)


def test_floating_rate_requires_reference_and_preserves_spread() -> None:
    value = _floating_rate("0.00125")
    assert value.logical_values() == (
        "floating",
        "0.00125",
        ("act-360",),
        _identity(500).logical_values(),
    )


def test_fixed_rate_forbids_floating_reference() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftRateTerms(
            SftRateKind.FIXED,
            Decimal("0.01"),
            SftDayCountCode("act-360"),
            _identity(500),
        )


def test_floating_rate_requires_typed_reference() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftRateTerms(
            SftRateKind.FLOATING,
            Decimal("0.01"),
            SftDayCountCode("act-360"),
        )
    with pytest.raises(SecuritiesFinancingValidationError):
        SftRateTerms(
            SftRateKind.FLOATING,
            Decimal("0.01"),
            SftDayCountCode("act-360"),
            cast(Any, _uuid(500)),
        )


def test_rate_terms_reject_raw_kind_day_count_and_nonfinite_value() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftRateTerms(cast(Any, "fixed"), Decimal("0.01"), SftDayCountCode("a"))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftRateTerms(SftRateKind.FIXED, Decimal("0.01"), cast(Any, "act-360"))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftRateTerms(SftRateKind.FIXED, Decimal("NaN"), SftDayCountCode("a"))


def test_duration_modes_preserve_distinct_contracts() -> None:
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


def test_term_duration_requires_end_and_forbids_notice() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(SftDurationMode.TERM, date(2026, 1, 1))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(
            SftDurationMode.TERM,
            date(2026, 1, 1),
            date(2026, 2, 1),
            1,
        )


def test_open_duration_forbids_termination_but_allows_notice() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(
            SftDurationMode.OPEN,
            date(2026, 1, 1),
            date(2026, 2, 1),
        )
    value = SftDurationTerms(SftDurationMode.OPEN, date(2026, 1, 1), notice_days=3)
    assert value.notice_days == 3


def test_callable_requires_notice_and_may_omit_contractual_end() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(SftDurationMode.CALLABLE, date(2026, 1, 1))
    value = SftDurationTerms(
        SftDurationMode.CALLABLE,
        date(2026, 1, 1),
        notice_days=2,
    )
    assert value.termination_date is None


@pytest.mark.parametrize("notice", [0, -1, True, 1.5, "2"])
def test_notice_days_are_strict_positive_int(notice: object) -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(
            SftDurationMode.OPEN,
            date(2026, 1, 1),
            notice_days=cast(Any, notice),
        )


def test_duration_rejects_raw_mode_raw_date_and_nonforward_end() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(cast(Any, "open"), date(2026, 1, 1))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(SftDurationMode.OPEN, cast(Any, "2026-01-01"))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftDurationTerms(
            SftDurationMode.TERM,
            date(2026, 2, 1),
            date(2026, 2, 1),
        )


def test_bilateral_and_tri_party_are_distinct() -> None:
    assert _bilateral().logical_values() == ("bilateral", None)
    assert _tri_party().logical_values() == (
        "tri-party",
        _party(50).logical_values(),
    )


def test_bilateral_forbids_agent_and_tri_party_requires_agent() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftArrangementTerms(SftArrangementMode.BILATERAL, _party(50))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftArrangementTerms(SftArrangementMode.TRI_PARTY)
    with pytest.raises(SecuritiesFinancingValidationError):
        SftArrangementTerms(
            SftArrangementMode.TRI_PARTY,
            cast(Any, _uuid(50)),
        )


def test_arrangement_rejects_raw_mode() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftArrangementTerms(cast(Any, "bilateral"))


def test_margin_terms_preserve_ratios_without_universal_one_cap() -> None:
    value = SftMarginTerms(
        initial_margin_ratio=Decimal("1.05"),
        haircut_ratio=Decimal("0.0250"),
    )
    assert value.logical_values() == ("1.05", "0.025")


def test_margin_terms_require_at_least_one_nonnegative_finite_ratio() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SftMarginTerms()
    with pytest.raises(SecuritiesFinancingValidationError):
        SftMarginTerms(initial_margin_ratio=Decimal("-0.1"))
    with pytest.raises(SecuritiesFinancingValidationError):
        SftMarginTerms(haircut_ratio=Decimal("NaN"))


def test_repo_far_leg_preserves_optional_supplied_cash_without_calculation() -> None:
    no_cash = RepoFarLegTerms(date(2026, 2, 1))
    with_cash = RepoFarLegTerms(date(2026, 2, 1), _cash("1010"))
    assert no_cash.logical_values() == ("2026-02-01", None)
    assert with_cash.logical_values()[1] == _cash("1010").logical_values()


def test_repo_far_leg_rejects_raw_date_or_cash() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        RepoFarLegTerms(cast(Any, "2026-02-01"))
    with pytest.raises(SecuritiesFinancingValidationError):
        RepoFarLegTerms(date(2026, 2, 1), cast(Any, Decimal("100")))


def test_term_repo_preserves_near_far_security_rate_and_margin() -> None:
    repo = _term_repo()
    logical = repo.logical_values()
    assert logical[0] == "repo"
    assert logical[6] == _cash().logical_values()
    assert len(repo.transferred_securities) == 2
    assert logical[10] == RepoFarLegTerms(
        date(2026, 2, 2),
        _cash("1002500"),
    ).logical_values()
    assert logical[11] == (None, "0.02")


def test_term_repo_requires_far_leg_matching_termination() -> None:
    base = _term_repo()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, far_leg=None)
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, far_leg=RepoFarLegTerms(date(2026, 2, 3)))


def test_open_repo_forbids_invented_far_leg() -> None:
    base = _term_repo()
    opened = replace(base, duration=_open_duration(), far_leg=None)
    assert opened.logical_values()[10] is None
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(opened, far_leg=RepoFarLegTerms(date(2026, 2, 2)))


def test_callable_repo_without_contractual_end_forbids_far_leg() -> None:
    base = _term_repo()
    duration = SftDurationTerms(
        SftDurationMode.CALLABLE,
        date(2026, 1, 2),
        notice_days=2,
    )
    callable_repo = replace(base, duration=duration, far_leg=None)
    assert callable_repo.far_leg is None
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(callable_repo, far_leg=RepoFarLegTerms(date(2026, 2, 2)))


def test_callable_repo_with_contractual_end_allows_matching_far_leg() -> None:
    base = _term_repo()
    callable_repo = replace(base, duration=_callable_duration(), far_leg=None)
    with_far = replace(
        callable_repo,
        far_leg=RepoFarLegTerms(date(2026, 6, 2)),
    )
    assert with_far.far_leg is not None
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(
            callable_repo,
            far_leg=RepoFarLegTerms(date(2026, 6, 3)),
        )


def test_repo_parties_must_be_typed_and_distinct() -> None:
    base = _term_repo()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, seller_reference_id=cast(Any, _uuid(1)))
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, buyer_reference_id=cast(Any, _uuid(2)))
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, buyer_reference_id=base.seller_reference_id)


def test_repo_requires_typed_common_material() -> None:
    base = _term_repo()
    invalid = (
        {"terms_id": cast(Any, _uuid(101))},
        {"instrument_identity_id": cast(Any, _uuid(10))},
        {"duration": cast(Any, "term")},
        {"near_cash": cast(Any, Decimal("1"))},
        {"financing_rate": cast(Any, Decimal("0.01"))},
        {"arrangement": cast(Any, "bilateral")},
        {"evidence_ref": cast(Any, _uuid(201))},
        {"margin_terms": cast(Any, Decimal("0.1"))},
    )
    for changes in invalid:
        with pytest.raises(SecuritiesFinancingValidationError):
            replace(base, **changes)


def test_repo_security_basket_must_be_nonempty_tuple_of_unique_typed_refs() -> None:
    base = _term_repo()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, transferred_securities=())
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, transferred_securities=cast(Any, [_security(401)]))
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, transferred_securities=cast(Any, ("bad",)))
    duplicate = (_security(401, "10"), _security(401, "20"))
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, transferred_securities=duplicate)


def test_repo_instrument_must_not_be_transferred_security() -> None:
    base = _term_repo()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, instrument_identity_id=_identity(401))


def test_securities_lending_fee_and_rebate_remain_distinct() -> None:
    compensation = SecuritiesLendingCompensationTerms(
        lending_fee_rate=Decimal("0.01"),
        cash_collateral_rebate_rate=Decimal("-0.002"),
    )
    assert compensation.logical_values() == ("0.01", "-0.002")


def test_securities_lending_compensation_allows_fee_only_or_rebate_only() -> None:
    assert SecuritiesLendingCompensationTerms(
        lending_fee_rate=Decimal("0")
    ).logical_values() == ("0", None)
    assert SecuritiesLendingCompensationTerms(
        cash_collateral_rebate_rate=Decimal("-0.001")
    ).logical_values() == (None, "-0.001")


def test_securities_lending_compensation_requires_material_and_valid_decimals() -> None:
    with pytest.raises(SecuritiesFinancingValidationError):
        SecuritiesLendingCompensationTerms()
    with pytest.raises(SecuritiesFinancingValidationError):
        SecuritiesLendingCompensationTerms(lending_fee_rate=Decimal("-0.01"))
    with pytest.raises(SecuritiesFinancingValidationError):
        SecuritiesLendingCompensationTerms(
            cash_collateral_rebate_rate=Decimal("NaN")
        )


def test_securities_lending_principal_and_collateral_are_structurally_distinct() -> None:
    loan = _securities_loan()
    logical = loan.logical_values()
    assert logical[0] == "securities-lending"
    assert logical[6] == _security(410, "250").logical_values()
    assert logical[8] == (
        _cash("500000", 301).logical_values(),
        _security(411, "75").logical_values(),
    )


def test_securities_lending_allows_empty_static_collateral_tuple() -> None:
    loan = replace(_securities_loan(), collateral=())
    assert loan.logical_values()[8] == ()


def test_securities_lending_rejects_invalid_collateral_container_or_item() -> None:
    base = _securities_loan()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, collateral=cast(Any, [_cash()]))
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, collateral=cast(Any, ("bad",)))


def test_securities_lending_parties_and_wrappers_fail_closed() -> None:
    base = _securities_loan()
    invalid = (
        {"terms_id": cast(Any, _uuid(102))},
        {"instrument_identity_id": cast(Any, _uuid(20))},
        {"lender_reference_id": cast(Any, _uuid(3))},
        {"borrower_reference_id": cast(Any, _uuid(4))},
        {"duration": cast(Any, "open")},
        {"principal_security": cast(Any, _identity(410))},
        {"compensation": cast(Any, Decimal("0.01"))},
        {"arrangement": cast(Any, "tri-party")},
        {"evidence_ref": cast(Any, _uuid(202))},
        {"margin_terms": cast(Any, Decimal("0.1"))},
    )
    for changes in invalid:
        with pytest.raises(SecuritiesFinancingValidationError):
            replace(base, **changes)
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, borrower_reference_id=base.lender_reference_id)


def test_securities_lending_instrument_differs_from_principal_security() -> None:
    base = _securities_loan()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, instrument_identity_id=base.principal_security.security_identity_id)


def test_margin_lending_retains_limit_not_current_availability() -> None:
    terms = _margin_loan()
    logical = terms.logical_values()
    assert logical[0] == "margin-lending"
    assert logical[6] == _cash("2500000", 302).logical_values()
    assert logical[8] == ("prime-broker-approved",)
    assert logical[9] == (
        _identity(420).logical_values(),
        _identity(421).logical_values(),
    )


def test_margin_lending_allows_scheme_without_enumerated_collateral_ids() -> None:
    terms = replace(_margin_loan(), eligible_collateral_identity_ids=())
    assert terms.logical_values()[9] == ()


def test_margin_lending_requires_tuple_unique_typed_collateral_identities() -> None:
    base = _margin_loan()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, eligible_collateral_identity_ids=cast(Any, [_identity(420)]))
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, eligible_collateral_identity_ids=cast(Any, (_uuid(420),)))
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(
            base,
            eligible_collateral_identity_ids=(_identity(420), _identity(420)),
        )


def test_margin_lending_facility_instrument_not_eligible_collateral() -> None:
    base = _margin_loan()
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(
            base,
            eligible_collateral_identity_ids=(base.instrument_identity_id,),
        )


def test_margin_lending_common_wrappers_fail_closed() -> None:
    base = _margin_loan()
    invalid = (
        {"terms_id": cast(Any, _uuid(103))},
        {"instrument_identity_id": cast(Any, _uuid(30))},
        {"lender_reference_id": cast(Any, _uuid(5))},
        {"borrower_reference_id": cast(Any, _uuid(6))},
        {"duration": cast(Any, "callable")},
        {"credit_limit": cast(Any, Decimal("100"))},
        {"financing_rate": cast(Any, Decimal("0.01"))},
        {"collateral_eligibility": cast(Any, "approved")},
        {"evidence_ref": cast(Any, _uuid(203))},
        {"margin_terms": cast(Any, Decimal("0.1"))},
    )
    for changes in invalid:
        with pytest.raises(SecuritiesFinancingValidationError):
            replace(base, **changes)
    with pytest.raises(SecuritiesFinancingValidationError):
        replace(base, borrower_reference_id=base.lender_reference_id)


def test_repo_securities_lending_and_margin_lending_do_not_collapse() -> None:
    assert {
        _term_repo().logical_values()[0],
        _securities_loan().logical_values()[0],
        _margin_loan().logical_values()[0],
    } == {"repo", "securities-lending", "margin-lending"}


def test_values_are_frozen() -> None:
    value = SftDayCountCode("act-360")
    with pytest.raises(FrozenInstanceError):
        value.__setattr__("value", "mutated")


@pytest.mark.parametrize("factory", [_term_repo, _securities_loan, _margin_loan])
def test_logical_values_are_repeatable(factory: Any) -> None:
    value = factory()
    assert value.logical_values() == value.logical_values()


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
        "datetime.now(",
        "uuid4(",
        "time.time(",
        "random.",
        "current_margin",
        "current_collateral",
        "available_to_borrow",
        "current_utilization",
        "margin_call",
        "provider_symbol",
        "private_key",
    ],
)
def test_source_contains_no_current_or_secret_material(forbidden: str) -> None:
    source_path = (
        Path(__file__).parents[2]
        / "src/qore/infrastructure/securities_financing_semantics.py"
    )
    assert forbidden not in source_path.read_text(encoding="utf-8")
