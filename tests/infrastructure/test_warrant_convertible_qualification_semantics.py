from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativePriceQuoteBasisCode,
    DerivativeSettlementStyle,
    DerivativeStrike,
    DerivativeStrikeBasis,
    DerivativeTermsId,
    OptionContractTerms,
    OptionExerciseStyle,
    OptionExerciseTerms,
    OptionRight,
)
from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredContractLevel,
    StructuredContractLevelKind,
    StructuredConversionFeature,
    StructuredEvidenceRef,
    StructuredFeatureId,
    StructuredLevelUnitCode,
    StructuredPositiveRatio,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
)
from qore.infrastructure.warrant_convertible_qualification_semantics import (
    ConvertibleQualificationTerms,
    EquityWarrantQualificationTerms,
    WarrantConvertibleEvidenceRef,
    WarrantConvertibleQualification,
    WarrantConvertibleQualificationId,
    WarrantConvertibleQualificationKind,
    WarrantConvertibleQualificationValidationError,
)


class UUIDSubclass(UUID):
    pass


class StrSubclass(str):
    pass


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(
    value: int,
    family: str,
    *,
    kind: EconomicIdentityKind = EconomicIdentityKind.TRADABLE_INSTRUMENT,
    construction: IdentityConstructionKind = IdentityConstructionKind.NATIVE,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=EconomicIdentityId(_uuid(value)),
        kind=kind,
        family=IdentityFamilyCode(family),
        construction=construction,
        evidence_ref=IdentityEvidenceRef(_uuid(value + 10_000)),
    )


def _option(
    warrant_identity_id: EconomicIdentityId,
    target_identity_id: EconomicIdentityId,
    *,
    strike: Decimal = Decimal("12.50"),
) -> OptionContractTerms:
    settlement = EconomicIdentityId(_uuid(900))
    quote = EconomicIdentityId(_uuid(901))
    multiplier_unit = EconomicIdentityId(_uuid(902))
    return OptionContractTerms(
        terms_id=DerivativeTermsId(_uuid(903)),
        instrument_identity_id=warrant_identity_id,
        underlying_identity_id=target_identity_id,
        settlement_identity_id=settlement,
        right=OptionRight.CALL,
        strike=DerivativeStrike(
            value=strike,
            basis=DerivativeStrikeBasis.PRICE,
            quote_identity_id=quote,
            price_quote_basis=DerivativePriceQuoteBasisCode("currency-per-unit"),
        ),
        expiry_date=date(2030, 6, 30),
        exercise=OptionExerciseTerms(OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.PHYSICAL,
        evidence_ref=DerivativeEvidenceRef(_uuid(904)),
        multiplier=DerivativeContractMultiplier(
            Decimal("1"),
            multiplier_unit,
        ),
    )


def _conversion(
    target_identity_id: EconomicIdentityId,
    *,
    ratio: Decimal = Decimal("2.5"),
    with_level: bool = True,
) -> StructuredConversionFeature:
    level = (
        StructuredContractLevel(
            value=Decimal("25"),
            kind=StructuredContractLevelKind.PRICE,
            reference_identity_id=target_identity_id,
            unit=StructuredLevelUnitCode("currency-per-share"),
        )
        if with_level
        else None
    )
    return StructuredConversionFeature(
        feature_id=StructuredFeatureId(_uuid(950)),
        target_identity_id=target_identity_id,
        units_per_source_unit=StructuredPositiveRatio(ratio),
        evidence_ref=StructuredEvidenceRef(_uuid(951)),
        conversion_level=level,
    )


def _qualification(
    kind: WarrantConvertibleQualificationKind,
    terms: EquityWarrantQualificationTerms | ConvertibleQualificationTerms,
) -> WarrantConvertibleQualification:
    return WarrantConvertibleQualification(
        qualification_id=WarrantConvertibleQualificationId(_uuid(980)),
        kind=kind,
        terms=terms,
        evidence_ref=WarrantConvertibleEvidenceRef(_uuid(981)),
    )


def test_qualification_kind_set_is_exact() -> None:
    assert {item.value for item in WarrantConvertibleQualificationKind} == {
        "warrant",
        "convertible",
    }


def test_warrant_reuses_option_contract_and_binds_both_identities() -> None:
    warrant = _identity(1, "options")
    target = _identity(2, "equities")
    option = _option(warrant.identity_id, target.identity_id)
    terms = EquityWarrantQualificationTerms(warrant, target, option)
    qualification = _qualification(WarrantConvertibleQualificationKind.WARRANT, terms)

    values = qualification.logical_values()
    assert values[1] == "warrant"
    assert values[2][0] == "warrant"
    assert values[2][3][0] == "option"
    assert values[2][3][6][0] == "12.5"


def test_convertible_reuses_conversion_feature_and_optional_credit_leg() -> None:
    convertible = _identity(10, "structured-hybrid-products")
    target = _identity(11, "equities")
    credit_leg = _identity(12, "fixed-income-credit")
    conversion = _conversion(target.identity_id)
    terms = ConvertibleQualificationTerms(
        convertible,
        target,
        conversion,
        credit_leg_identity=credit_leg,
    )
    qualification = _qualification(WarrantConvertibleQualificationKind.CONVERTIBLE, terms)

    values = qualification.logical_values()
    assert values[1] == "convertible"
    assert values[2][0] == "convertible"
    assert values[2][3][0] == "conversion"
    assert values[2][4][2] == ("fixed-income-credit",)


def test_convertible_credit_leg_is_optional() -> None:
    convertible = _identity(20, "fixed-income-credit")
    target = _identity(21, "equities")
    terms = ConvertibleQualificationTerms(
        convertible,
        target,
        _conversion(target.identity_id, with_level=False),
    )
    assert terms.logical_values()[-1] is None


@pytest.mark.parametrize(
    ("kind", "terms_factory"),
    [
        (
            WarrantConvertibleQualificationKind.WARRANT,
            lambda: ConvertibleQualificationTerms(
                _identity(30, "fixed-income-credit"),
                _identity(31, "equities"),
                _conversion(EconomicIdentityId(_uuid(31))),
            ),
        ),
        (
            WarrantConvertibleQualificationKind.CONVERTIBLE,
            lambda: EquityWarrantQualificationTerms(
                _identity(32, "options"),
                _identity(33, "equities"),
                _option(EconomicIdentityId(_uuid(32)), EconomicIdentityId(_uuid(33))),
            ),
        ),
    ],
)
def test_kind_and_terms_variant_must_match_exactly(
    kind: WarrantConvertibleQualificationKind,
    terms_factory: object,
) -> None:
    factory = terms_factory
    assert callable(factory)
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="kind and terms variant",
    ):
        _qualification(kind, factory())


def test_target_identity_must_be_equity_family() -> None:
    warrant = _identity(40, "options")
    wrong_target = _identity(41, "indices-benchmarks")
    option = _option(warrant.identity_id, wrong_target.identity_id)
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="family must be equities",
    ):
        EquityWarrantQualificationTerms(warrant, wrong_target, option)


def test_warrant_option_instrument_must_match_warrant_identity() -> None:
    warrant = _identity(50, "options")
    other = _identity(51, "options")
    target = _identity(52, "equities")
    option = _option(other.identity_id, target.identity_id)
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="instrument identity must match warrant",
    ):
        EquityWarrantQualificationTerms(warrant, target, option)


def test_warrant_option_underlying_must_match_target_equity() -> None:
    warrant = _identity(60, "options")
    target = _identity(61, "equities")
    other_target = _identity(62, "equities")
    option = _option(warrant.identity_id, other_target.identity_id)
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="underlying identity must match target equity",
    ):
        EquityWarrantQualificationTerms(warrant, target, option)


def test_convertible_conversion_target_must_match_target_equity() -> None:
    convertible = _identity(70, "fixed-income-credit")
    target = _identity(71, "equities")
    other_target = _identity(72, "equities")
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="conversion target identity must match target equity",
    ):
        ConvertibleQualificationTerms(
            convertible,
            target,
            _conversion(other_target.identity_id),
        )


def test_optional_credit_leg_must_prove_fixed_income_credit_family() -> None:
    convertible = _identity(80, "structured-hybrid-products")
    target = _identity(81, "equities")
    wrong_leg = _identity(82, "loans-credit-facilities")
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="family must be fixed-income-credit",
    ):
        ConvertibleQualificationTerms(
            convertible,
            target,
            _conversion(target.identity_id),
            credit_leg_identity=wrong_leg,
        )


def test_root_identity_family_is_not_invented_from_registry_row() -> None:
    target = _identity(91, "equities")
    for family in ("options", "equities", "structured-hybrid-products"):
        warrant = _identity(90, family)
        EquityWarrantQualificationTerms(
            warrant,
            target,
            _option(warrant.identity_id, target.identity_id),
        )

    for family in ("fixed-income-credit", "structured-hybrid-products", "equities"):
        convertible = _identity(92, family)
        ConvertibleQualificationTerms(
            convertible,
            target,
            _conversion(target.identity_id),
        )


def test_continuous_reference_rule_is_reapplied() -> None:
    fabricated = object.__new__(EconomicIdentity)
    object.__setattr__(fabricated, "identity_id", EconomicIdentityId(_uuid(100)))
    object.__setattr__(fabricated, "kind", EconomicIdentityKind.TRADABLE_INSTRUMENT)
    object.__setattr__(fabricated, "family", IdentityFamilyCode("equities"))
    object.__setattr__(
        fabricated,
        "construction",
        IdentityConstructionKind.CONTINUOUS_REFERENCE,
    )
    object.__setattr__(fabricated, "evidence_ref", IdentityEvidenceRef(_uuid(101)))

    convertible = _identity(102, "fixed-income-credit")
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="continuous-reference identity",
    ):
        ConvertibleQualificationTerms(
            convertible,
            fabricated,
            _conversion(fabricated.identity_id),
        )


def test_post_construction_nested_identity_corruption_is_rejected() -> None:
    warrant = _identity(110, "options")
    target = _identity(111, "equities")
    qualification = _qualification(
        WarrantConvertibleQualificationKind.WARRANT,
        EquityWarrantQualificationTerms(
            warrant,
            target,
            _option(warrant.identity_id, target.identity_id),
        ),
    )
    object.__setattr__(target.identity_id, "value", "bad")
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="must be exact UUID",
    ):
        qualification.logical_values()


def test_post_construction_option_terms_id_corruption_is_rejected() -> None:
    warrant = _identity(120, "options")
    target = _identity(121, "equities")
    option = _option(warrant.identity_id, target.identity_id)
    qualification = _qualification(
        WarrantConvertibleQualificationKind.WARRANT,
        EquityWarrantQualificationTerms(warrant, target, option),
    )
    object.__setattr__(option.terms_id, "value", "bad")
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="option terms_id value must be exact UUID",
    ):
        qualification.logical_values()


def test_post_construction_option_strike_float_corruption_is_rejected() -> None:
    warrant = _identity(130, "options")
    target = _identity(131, "equities")
    option = _option(warrant.identity_id, target.identity_id)
    qualification = _qualification(
        WarrantConvertibleQualificationKind.WARRANT,
        EquityWarrantQualificationTerms(warrant, target, option),
    )
    object.__setattr__(option.strike, "value", 12.5)
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="exact finite Decimal",
    ):
        qualification.logical_values()


def test_post_construction_exercise_enum_laundering_is_rejected() -> None:
    warrant = _identity(140, "options")
    target = _identity(141, "equities")
    option = _option(warrant.identity_id, target.identity_id)
    qualification = _qualification(
        WarrantConvertibleQualificationKind.WARRANT,
        EquityWarrantQualificationTerms(warrant, target, option),
    )
    object.__setattr__(option.exercise, "style", "european")
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="exact OptionExerciseStyle",
    ):
        qualification.logical_values()


def test_post_construction_conversion_ratio_corruption_is_rejected() -> None:
    convertible = _identity(150, "fixed-income-credit")
    target = _identity(151, "equities")
    conversion = _conversion(target.identity_id)
    qualification = _qualification(
        WarrantConvertibleQualificationKind.CONVERTIBLE,
        ConvertibleQualificationTerms(convertible, target, conversion),
    )
    object.__setattr__(conversion.units_per_source_unit, "value", True)
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="exact finite Decimal",
    ):
        qualification.logical_values()


def test_uuid_subclass_laundering_is_rejected_on_imported_identity_id() -> None:
    target = _identity(160, "equities")
    object.__setattr__(
        target.identity_id,
        "value",
        UUIDSubclass(str(_uuid(160))),
    )
    convertible = _identity(161, "fixed-income-credit")
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="exact UUID",
    ):
        ConvertibleQualificationTerms(
            convertible,
            target,
            _conversion(target.identity_id),
        )


def test_str_subclass_laundering_is_rejected_on_family_code() -> None:
    target = _identity(170, "equities")
    object.__setattr__(target.family, "value", StrSubclass("equities"))
    convertible = _identity(171, "fixed-income-credit")
    with pytest.raises(
        WarrantConvertibleQualificationValidationError,
        match="canonical lowercase code",
    ):
        ConvertibleQualificationTerms(
            convertible,
            target,
            _conversion(target.identity_id),
        )


def test_extreme_option_strike_uses_compact_representation() -> None:
    warrant = _identity(180, "options")
    target = _identity(181, "equities")
    qualification = _qualification(
        WarrantConvertibleQualificationKind.WARRANT,
        EquityWarrantQualificationTerms(
            warrant,
            target,
            _option(
                warrant.identity_id,
                target.identity_id,
                strike=Decimal("1E+100000000"),
            ),
        ),
    )
    assert qualification.logical_values()[2][3][6][0] == "1e+100000000"


def test_extreme_conversion_ratio_uses_compact_representation() -> None:
    convertible = _identity(190, "fixed-income-credit")
    target = _identity(191, "equities")
    qualification = _qualification(
        WarrantConvertibleQualificationKind.CONVERTIBLE,
        ConvertibleQualificationTerms(
            convertible,
            target,
            _conversion(target.identity_id, ratio=Decimal("1E+100000000")),
        ),
    )
    assert qualification.logical_values()[2][3][3][0] == "1e+100000000"


def test_contract_has_no_implicit_clock_generated_identity_or_operational_authority() -> None:
    source = Path(
        "src/qore/infrastructure/warrant_convertible_qualification_semantics.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "datetime.now",
        "date.today",
        "uuid4(",
        "requests.",
        "httpx.",
        "submit_order",
        "place_order",
        "send_order",
        "execute_trade",
        "settle_trade",
    )
    for token in forbidden:
        assert token not in source
