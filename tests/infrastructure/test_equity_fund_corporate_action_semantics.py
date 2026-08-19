from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativePriceQuoteBasisCode,
    DerivativeStrike,
    DerivativeStrikeBasis,
)
from qore.infrastructure.equity_fund_corporate_action_semantics import (
    BenchmarkReturnBasisCode,
    CashDividendTerms,
    CorporateActionCashAmount,
    CorporateActionId,
    CorporateActionRevision,
    DepositaryReceiptProgramCode,
    DepositaryReceiptTerms,
    EquityFundCorporateActionValidationError,
    EquityFundEvidenceRef,
    EquityFundTermsId,
    EquitySecurityKind,
    EquitySecurityTerms,
    EquityShareClassCode,
    EquityUnitRatio,
    FundBenchmarkRelationshipTerms,
    FundBenchmarkRoleCode,
    FundNavBasis,
    FundNavBasisCode,
    FundVehicleKind,
    FundVehicleTerms,
    RightsDistributionTerms,
    SplitTerms,
    StockDividendTerms,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityRelationshipId,
)


def _economic_id(seed: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=seed))


def _relationship_id(seed: int = 80) -> IdentityRelationshipId:
    return IdentityRelationshipId(UUID(int=seed))


def _terms_id(seed: int = 100) -> EquityFundTermsId:
    return EquityFundTermsId(UUID(int=seed))


def _action_id(seed: int = 200) -> CorporateActionId:
    return CorporateActionId(UUID(int=seed))


def _evidence(seed: int = 300) -> EquityFundEvidenceRef:
    return EquityFundEvidenceRef(UUID(int=seed))


def _revision(value: int = 1) -> CorporateActionRevision:
    return CorporateActionRevision(value)


def _price_strike(value: str = "25.00") -> DerivativeStrike:
    return DerivativeStrike(
        value=Decimal(value),
        basis=DerivativeStrikeBasis.PRICE,
        quote_identity_id=_economic_id(900),
        price_quote_basis=DerivativePriceQuoteBasisCode("currency-per-unit"),
    )


def test_local_ids_are_uuid_backed_and_not_economic_identity() -> None:
    terms_id = _terms_id()
    action_id = _action_id()
    evidence = _evidence()

    assert terms_id.logical_values() == (str(UUID(int=100)),)
    assert action_id.logical_values() == (str(UUID(int=200)),)
    assert evidence.logical_values() == (str(UUID(int=300)),)
    assert not isinstance(terms_id, EconomicIdentityId)
    assert not isinstance(action_id, EconomicIdentityId)


@pytest.mark.parametrize(
    ("factory", "bad_value"),
    [
        (EquityFundTermsId, "not-a-uuid"),
        (CorporateActionId, "not-a-uuid"),
        (EquityFundEvidenceRef, "not-a-uuid"),
    ],
)
def test_local_uuid_wrappers_reject_raw_text(
    factory: type[Any],
    bad_value: str,
) -> None:
    with pytest.raises(EquityFundCorporateActionValidationError):
        factory(cast(Any, bad_value))


@pytest.mark.parametrize("value", [0, -1, True])
def test_corporate_action_revision_requires_positive_strict_int(value: object) -> None:
    with pytest.raises(EquityFundCorporateActionValidationError):
        CorporateActionRevision(cast(int, value))


def test_equity_common_and_preferred_semantics_do_not_collapse() -> None:
    common = EquitySecurityTerms(
        terms_id=_terms_id(101),
        instrument_identity_id=_economic_id(1),
        issuer_identity_id=_economic_id(2),
        security_kind=EquitySecurityKind.COMMON,
        share_class=EquityShareClassCode("class-a"),
        evidence_ref=_evidence(301),
    )
    preferred = EquitySecurityTerms(
        terms_id=_terms_id(102),
        instrument_identity_id=_economic_id(1),
        issuer_identity_id=_economic_id(2),
        security_kind=EquitySecurityKind.PREFERRED,
        share_class=EquityShareClassCode("class-a"),
        evidence_ref=_evidence(302),
    )

    assert common.logical_values()[4] == "common"
    assert preferred.logical_values()[4] == "preferred"
    assert common.logical_values() != preferred.logical_values()
    assert common.logical_values() == (
        "equity-security",
        (str(UUID(int=101)),),
        (str(UUID(int=1)),),
        (str(UUID(int=2)),),
        "common",
        ("class-a",),
        (str(UUID(int=301)),),
    )
    assert preferred.logical_values() == (
        "equity-security",
        (str(UUID(int=102)),),
        (str(UUID(int=1)),),
        (str(UUID(int=2)),),
        "preferred",
        ("class-a",),
        (str(UUID(int=302)),),
    )


def test_equity_security_terms_absent_share_class_projects_none() -> None:
    terms = EquitySecurityTerms(
        terms_id=_terms_id(103),
        instrument_identity_id=_economic_id(3),
        issuer_identity_id=_economic_id(4),
        security_kind=EquitySecurityKind.PREFERRED,
        share_class=None,
        evidence_ref=_evidence(303),
    )

    assert terms.logical_values() == (
        "equity-security",
        (str(UUID(int=103)),),
        (str(UUID(int=3)),),
        (str(UUID(int=4)),),
        "preferred",
        None,
        (str(UUID(int=303)),),
    )


def test_equity_security_terms_common_absent_share_class_projects_none() -> None:
    terms = EquitySecurityTerms(
        terms_id=_terms_id(104),
        instrument_identity_id=_economic_id(5),
        issuer_identity_id=_economic_id(6),
        security_kind=EquitySecurityKind.COMMON,
        share_class=None,
        evidence_ref=_evidence(304),
    )

    assert terms.logical_values() == (
        "equity-security",
        (str(UUID(int=104)),),
        (str(UUID(int=5)),),
        (str(UUID(int=6)),),
        "common",
        None,
        (str(UUID(int=304)),),
    )


def test_equity_terms_reject_identity_authority_laundering() -> None:
    with pytest.raises(
        EquityFundCorporateActionValidationError,
        match="issuer identity",
    ):
        EquitySecurityTerms(
            terms_id=_terms_id(),
            instrument_identity_id=_economic_id(1),
            issuer_identity_id=cast(Any, UUID(int=2)),
            security_kind=EquitySecurityKind.COMMON,
            evidence_ref=_evidence(),
        )

    with pytest.raises(
        EquityFundCorporateActionValidationError,
        match="must differ",
    ):
        EquitySecurityTerms(
            terms_id=_terms_id(),
            instrument_identity_id=_economic_id(1),
            issuer_identity_id=_economic_id(1),
            security_kind=EquitySecurityKind.COMMON,
            evidence_ref=_evidence(),
        )


def test_equity_terms_reject_raw_security_kind_and_share_class() -> None:
    with pytest.raises(EquityFundCorporateActionValidationError):
        EquitySecurityTerms(
            terms_id=_terms_id(),
            instrument_identity_id=_economic_id(1),
            issuer_identity_id=_economic_id(2),
            security_kind=cast(Any, "common"),
            evidence_ref=_evidence(),
        )

    with pytest.raises(EquityFundCorporateActionValidationError):
        EquitySecurityTerms(
            terms_id=_terms_id(),
            instrument_identity_id=_economic_id(1),
            issuer_identity_id=_economic_id(2),
            security_kind=EquitySecurityKind.COMMON,
            share_class=cast(Any, "class-a"),
            evidence_ref=_evidence(),
        )


@pytest.mark.parametrize(
    "value",
    [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("Infinity")],
)
def test_equity_unit_ratio_is_positive_and_finite(value: Decimal) -> None:
    with pytest.raises(EquityFundCorporateActionValidationError):
        EquityUnitRatio(value)


def test_depositary_receipt_retains_program_underlying_and_exact_ratio() -> None:
    adr = DepositaryReceiptTerms(
        terms_id=_terms_id(),
        receipt_identity_id=_economic_id(10),
        underlying_identity_id=_economic_id(11),
        program=DepositaryReceiptProgramCode("adr"),
        underlying_units_per_receipt=EquityUnitRatio(Decimal("2.0000")),
        evidence_ref=_evidence(),
    )
    gdr = DepositaryReceiptTerms(
        terms_id=_terms_id(101),
        receipt_identity_id=_economic_id(10),
        underlying_identity_id=_economic_id(11),
        program=DepositaryReceiptProgramCode("gdr"),
        underlying_units_per_receipt=EquityUnitRatio(Decimal("2")),
        evidence_ref=_evidence(301),
    )

    assert adr.underlying_units_per_receipt.logical_values() == ("2",)
    assert adr.logical_values()[4] == ("adr",)
    assert gdr.logical_values()[4] == ("gdr",)
    assert adr.logical_values() != gdr.logical_values()
    assert adr.logical_values() == (
        "depositary-receipt",
        (str(UUID(int=100)),),
        (str(UUID(int=10)),),
        (str(UUID(int=11)),),
        ("adr",),
        ("2",),
        (str(UUID(int=300)),),
    )


def test_depositary_receipt_rejects_self_reference() -> None:
    with pytest.raises(EquityFundCorporateActionValidationError, match="must differ"):
        DepositaryReceiptTerms(
            terms_id=_terms_id(),
            receipt_identity_id=_economic_id(10),
            underlying_identity_id=_economic_id(10),
            program=DepositaryReceiptProgramCode("adr"),
            underlying_units_per_receipt=EquityUnitRatio(Decimal("1")),
            evidence_ref=_evidence(),
        )


def test_fund_nav_basis_is_structural_and_contains_no_nav_value_engine() -> None:
    nav_basis = FundNavBasis(
        currency_identity_id=_economic_id(20),
        unit_identity_id=_economic_id(21),
        basis=FundNavBasisCode("per-share"),
        evidence_ref=_evidence(),
    )
    fund = FundVehicleTerms(
        terms_id=_terms_id(),
        instrument_identity_id=_economic_id(21),
        vehicle_kind=FundVehicleKind.ETF,
        share_class=EquityShareClassCode("class-a"),
        nav_basis=nav_basis,
        evidence_ref=_evidence(301),
    )

    assert fund.logical_values()[3] == "etf"
    assert nav_basis.logical_values()[2] == ("per-share",)
    assert not hasattr(nav_basis, "value")
    assert not hasattr(nav_basis, "calculate")
    assert not hasattr(nav_basis, "observe")
    assert not hasattr(fund, "nav")


def test_fund_vehicle_terms_share_class_present_nav_basis_none() -> None:
    terms = FundVehicleTerms(
        terms_id=_terms_id(120),
        instrument_identity_id=_economic_id(121),
        vehicle_kind=FundVehicleKind.ETF,
        share_class=EquityShareClassCode("retail"),
        nav_basis=None,
        evidence_ref=_evidence(122),
    )

    assert terms.logical_values() == (
        "fund-vehicle",
        (str(UUID(int=120)),),
        (str(UUID(int=121)),),
        "etf",
        ("retail",),
        None,
        (str(UUID(int=122)),),
    )


def test_fund_vehicle_terms_share_class_none_nav_basis_present() -> None:
    nav_basis = FundNavBasis(
        currency_identity_id=_economic_id(133),
        unit_identity_id=_economic_id(134),
        basis=FundNavBasisCode("per-share"),
        evidence_ref=_evidence(135),
    )
    terms = FundVehicleTerms(
        terms_id=_terms_id(130),
        instrument_identity_id=_economic_id(131),
        vehicle_kind=FundVehicleKind.ETF,
        share_class=None,
        nav_basis=nav_basis,
        evidence_ref=_evidence(132),
    )

    assert terms.logical_values() == (
        "fund-vehicle",
        (str(UUID(int=130)),),
        (str(UUID(int=131)),),
        "etf",
        None,
        (
            (str(UUID(int=133)),),
            (str(UUID(int=134)),),
            ("per-share",),
            (str(UUID(int=135)),),
        ),
        (str(UUID(int=132)),),
    )


def test_fund_nav_basis_rejects_same_currency_and_unit_identity() -> None:
    with pytest.raises(EquityFundCorporateActionValidationError, match="must differ"):
        FundNavBasis(
            currency_identity_id=_economic_id(20),
            unit_identity_id=_economic_id(20),
            basis=FundNavBasisCode("per-share"),
            evidence_ref=_evidence(),
        )


def test_fund_vehicle_kind_does_not_flatten_etn_or_structured_products() -> None:
    reit = FundVehicleTerms(
        terms_id=_terms_id(),
        instrument_identity_id=_economic_id(30),
        vehicle_kind=FundVehicleKind.REIT,
        evidence_ref=_evidence(),
    )

    assert reit.logical_values()[3] == "reit"
    with pytest.raises(ValueError):
        FundVehicleKind("etn")
    with pytest.raises(ValueError):
        FundVehicleKind("index-linked-product")


def test_fund_benchmark_relationship_binds_umi02_relationship_and_return_basis() -> None:
    relationship_id = _relationship_id()
    price_return = FundBenchmarkRelationshipTerms(
        terms_id=_terms_id(110),
        relationship_id=relationship_id,
        role=FundBenchmarkRoleCode("tracking-index"),
        return_basis=BenchmarkReturnBasisCode("price-return"),
        evidence_ref=_evidence(310),
    )
    total_return = FundBenchmarkRelationshipTerms(
        terms_id=_terms_id(111),
        relationship_id=relationship_id,
        role=FundBenchmarkRoleCode("tracking-index"),
        return_basis=BenchmarkReturnBasisCode("gross-total-return"),
        evidence_ref=_evidence(311),
    )

    assert price_return.logical_values()[2] == relationship_id.logical_values()
    assert price_return.logical_values()[4] == ("price-return",)
    assert total_return.logical_values()[4] == ("gross-total-return",)
    assert price_return.logical_values() != total_return.logical_values()
    assert not hasattr(price_return, "fund_identity_id")
    assert not hasattr(price_return, "benchmark_identity_id")
    assert not hasattr(price_return, "level")
    assert not hasattr(price_return, "calculate")
    assert price_return.logical_values() == (
        "fund-benchmark-relationship",
        (str(UUID(int=110)),),
        (str(UUID(int=80)),),
        ("tracking-index",),
        ("price-return",),
        (str(UUID(int=310)),),
    )


def test_fund_benchmark_relationship_rejects_raw_relationship_id() -> None:
    with pytest.raises(
        EquityFundCorporateActionValidationError,
        match="IdentityRelationshipId",
    ):
        FundBenchmarkRelationshipTerms(
            terms_id=_terms_id(),
            relationship_id=cast(Any, UUID(int=80)),
            role=FundBenchmarkRoleCode("primary-benchmark"),
            return_basis=BenchmarkReturnBasisCode("price-return"),
            evidence_ref=_evidence(),
        )


@pytest.mark.parametrize(
    "amount",
    [Decimal("0"), Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")],
)
def test_corporate_action_cash_amount_is_positive_and_finite(amount: Decimal) -> None:
    with pytest.raises(EquityFundCorporateActionValidationError):
        CorporateActionCashAmount(
            amount=amount,
            currency_identity_id=_economic_id(40),
        )


def test_cash_dividend_retains_exact_amount_and_does_not_invent_date_ordering() -> None:
    terms = CashDividendTerms(
        action_id=_action_id(),
        revision=_revision(),
        instrument_identity_id=_economic_id(41),
        amount=CorporateActionCashAmount(
            amount=Decimal("1.2500"),
            currency_identity_id=_economic_id(40),
        ),
        declared_date=date(2026, 1, 1),
        ex_date=date(2026, 3, 1),
        record_date=date(2026, 1, 15),
        payable_date=date(2026, 2, 1),
        evidence_ref=_evidence(),
    )

    assert terms.amount.logical_values()[0] == "1.25"
    assert terms.logical_values()[5:9] == (
        "2026-01-01",
        "2026-03-01",
        "2026-01-15",
        "2026-02-01",
    )
    assert not hasattr(terms, "pay")
    assert not hasattr(terms, "settle")
    assert not hasattr(terms, "apply")
    assert terms.logical_values() == (
        "cash-dividend",
        (str(UUID(int=200)),),
        (1,),
        (str(UUID(int=41)),),
        (
            "1.25",
            (str(UUID(int=40)),),
        ),
        "2026-01-01",
        "2026-03-01",
        "2026-01-15",
        "2026-02-01",
        (str(UUID(int=300)),),
    )


def test_cash_dividend_date_fields_reject_datetime_laundering() -> None:
    with pytest.raises(
        EquityFundCorporateActionValidationError,
        match="declared_date must be date",
    ):
        CashDividendTerms(
            action_id=_action_id(),
            revision=_revision(),
            instrument_identity_id=_economic_id(41),
            amount=CorporateActionCashAmount(
                amount=Decimal("1"),
                currency_identity_id=_economic_id(40),
            ),
            declared_date=cast(date, datetime(2026, 1, 1, tzinfo=UTC)),
            ex_date=date(2026, 1, 2),
            record_date=date(2026, 1, 3),
            payable_date=date(2026, 1, 4),
            evidence_ref=_evidence(),
        )


def test_stock_dividend_retains_distribution_identity_and_ratio() -> None:
    terms = StockDividendTerms(
        action_id=_action_id(),
        revision=_revision(2),
        instrument_identity_id=_economic_id(50),
        distribution_identity_id=_economic_id(51),
        units_per_existing_unit=EquityUnitRatio(Decimal("0.1000")),
        ex_date=date(2026, 2, 1),
        record_date=date(2026, 2, 2),
        payable_date=date(2026, 2, 10),
        evidence_ref=_evidence(),
    )

    assert terms.revision.logical_values() == (2,)
    assert terms.units_per_existing_unit.logical_values() == ("0.1",)
    assert not hasattr(terms, "apply")
    assert terms.logical_values() == (
        "stock-dividend",
        (str(UUID(int=200)),),
        (2,),
        (str(UUID(int=50)),),
        (str(UUID(int=51)),),
        ("0.1",),
        "2026-02-01",
        "2026-02-02",
        "2026-02-10",
        (str(UUID(int=300)),),
    )


def test_split_allows_reverse_split_ratio_below_one_without_position_mutation() -> None:
    reverse_split = SplitTerms(
        action_id=_action_id(),
        revision=_revision(),
        instrument_identity_id=_economic_id(60),
        new_units_per_old_unit=EquityUnitRatio(Decimal("0.1000")),
        effective_date=date(2026, 4, 1),
        evidence_ref=_evidence(),
    )
    forward_split = SplitTerms(
        action_id=_action_id(201),
        revision=_revision(),
        instrument_identity_id=_economic_id(60),
        new_units_per_old_unit=EquityUnitRatio(Decimal("4")),
        effective_date=date(2026, 5, 1),
        evidence_ref=_evidence(301),
    )

    assert reverse_split.new_units_per_old_unit.logical_values() == ("0.1",)
    assert forward_split.new_units_per_old_unit.logical_values() == ("4",)
    assert reverse_split.logical_values() != forward_split.logical_values()
    assert not hasattr(reverse_split, "apply")
    assert not hasattr(reverse_split, "adjust_position")
    assert reverse_split.logical_values() == (
        "split",
        (str(UUID(int=200)),),
        (1,),
        (str(UUID(int=60)),),
        ("0.1",),
        "2026-04-01",
        (str(UUID(int=300)),),
    )


def test_rights_distribution_reuses_umi05_price_strike_semantics() -> None:
    rights = RightsDistributionTerms(
        action_id=_action_id(),
        revision=_revision(),
        instrument_identity_id=_economic_id(70),
        rights_identity_id=_economic_id(71),
        entitlement_units_per_source_unit=EquityUnitRatio(Decimal("0.25")),
        subscription_strike=_price_strike("17.500"),
        ex_date=date(2026, 5, 1),
        record_date=date(2026, 5, 2),
        expiration_date=date(2026, 5, 31),
        evidence_ref=_evidence(),
    )

    assert rights.subscription_strike.basis is DerivativeStrikeBasis.PRICE
    assert rights.subscription_strike.logical_values()[0] == "17.5"
    assert not hasattr(rights, "execute")
    assert not hasattr(rights, "exercise")
    assert not hasattr(rights, "settle")
    assert rights.logical_values() == (
        "rights-distribution",
        (str(UUID(int=200)),),
        (1,),
        (str(UUID(int=70)),),
        (str(UUID(int=71)),),
        ("0.25",),
        (
            "17.5",
            "price",
            (str(UUID(int=900)),),
            ("currency-per-unit",),
            None,
        ),
        "2026-05-01",
        "2026-05-02",
        "2026-05-31",
        (str(UUID(int=300)),),
    )


def test_rights_distribution_rejects_non_price_strike() -> None:
    spread_strike = DerivativeStrike(
        value=Decimal("0.01"),
        basis=DerivativeStrikeBasis.SPREAD,
    )

    with pytest.raises(
        EquityFundCorporateActionValidationError,
        match="PRICE strike semantics",
    ):
        RightsDistributionTerms(
            action_id=_action_id(),
            revision=_revision(),
            instrument_identity_id=_economic_id(70),
            rights_identity_id=_economic_id(71),
            entitlement_units_per_source_unit=EquityUnitRatio(Decimal("0.25")),
            subscription_strike=spread_strike,
            ex_date=date(2026, 5, 1),
            record_date=date(2026, 5, 2),
            expiration_date=date(2026, 5, 31),
            evidence_ref=_evidence(),
        )


def test_rights_distribution_rejects_source_self_reference_and_bad_expiry() -> None:
    with pytest.raises(EquityFundCorporateActionValidationError, match="must differ"):
        RightsDistributionTerms(
            action_id=_action_id(),
            revision=_revision(),
            instrument_identity_id=_economic_id(70),
            rights_identity_id=_economic_id(70),
            entitlement_units_per_source_unit=EquityUnitRatio(Decimal("0.25")),
            subscription_strike=_price_strike(),
            ex_date=date(2026, 5, 1),
            record_date=date(2026, 5, 2),
            expiration_date=date(2026, 5, 31),
            evidence_ref=_evidence(),
        )

    with pytest.raises(
        EquityFundCorporateActionValidationError,
        match="must not be before record_date",
    ):
        RightsDistributionTerms(
            action_id=_action_id(201),
            revision=_revision(),
            instrument_identity_id=_economic_id(70),
            rights_identity_id=_economic_id(71),
            entitlement_units_per_source_unit=EquityUnitRatio(Decimal("0.25")),
            subscription_strike=_price_strike(),
            ex_date=date(2026, 5, 1),
            record_date=date(2026, 5, 20),
            expiration_date=date(2026, 5, 19),
            evidence_ref=_evidence(301),
        )


def test_terms_and_actions_are_frozen() -> None:
    terms = EquitySecurityTerms(
        terms_id=_terms_id(),
        instrument_identity_id=_economic_id(1),
        issuer_identity_id=_economic_id(2),
        security_kind=EquitySecurityKind.COMMON,
        evidence_ref=_evidence(),
    )
    split = SplitTerms(
        action_id=_action_id(),
        revision=_revision(),
        instrument_identity_id=_economic_id(60),
        new_units_per_old_unit=EquityUnitRatio(Decimal("2")),
        effective_date=date(2026, 4, 1),
        evidence_ref=_evidence(),
    )
    terms_field = "security_kind"
    split_field = "effective_date"

    with pytest.raises(FrozenInstanceError):
        setattr(terms, terms_field, EquitySecurityKind.PREFERRED)
    with pytest.raises(FrozenInstanceError):
        setattr(split, split_field, date(2026, 5, 1))


def test_no_candidate_type_exposes_provider_valuation_execution_or_mutation_engine() -> None:
    objects = (
        EquitySecurityTerms(
            terms_id=_terms_id(120),
            instrument_identity_id=_economic_id(1),
            issuer_identity_id=_economic_id(2),
            security_kind=EquitySecurityKind.COMMON,
            evidence_ref=_evidence(320),
        ),
        FundVehicleTerms(
            terms_id=_terms_id(121),
            instrument_identity_id=_economic_id(21),
            vehicle_kind=FundVehicleKind.ETF,
            evidence_ref=_evidence(321),
        ),
        CashDividendTerms(
            action_id=_action_id(220),
            revision=_revision(),
            instrument_identity_id=_economic_id(41),
            amount=CorporateActionCashAmount(
                amount=Decimal("1"),
                currency_identity_id=_economic_id(40),
            ),
            declared_date=date(2026, 1, 1),
            ex_date=date(2026, 1, 2),
            record_date=date(2026, 1, 3),
            payable_date=date(2026, 1, 4),
            evidence_ref=_evidence(322),
        ),
    )

    forbidden = (
        "price",
        "value",
        "calculate_nav",
        "observe_nav",
        "execute",
        "settle",
        "apply",
        "adjust_position",
        "adjust_balance",
        "reserve_risk",
        "provider",
    )
    for obj in objects:
        for name in forbidden:
            assert not hasattr(obj, name)


def test_logical_values_are_repeatable_and_secret_free() -> None:
    terms = FundBenchmarkRelationshipTerms(
        terms_id=_terms_id(),
        relationship_id=_relationship_id(),
        role=FundBenchmarkRoleCode("tracking-index"),
        return_basis=BenchmarkReturnBasisCode("net-total-return"),
        evidence_ref=_evidence(),
    )

    first = repr(terms.logical_values())
    second = repr(terms.logical_values())

    assert first == second
    lowered = first.lower()
    for marker in ("token=", "secret=", "password=", "bearer "):
        assert marker not in lowered
