from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.commodity_contract_delivery_semantics import (
    CommodityClassCode,
    CommodityDeliveryAlternative,
    CommodityDeliveryMethodCode,
    CommodityDeliveryWindow,
    CommodityEvidenceRef,
    CommodityGradeCode,
    CommodityPhysicalDeliveryTerms,
    CommodityReferenceTerms,
    CommodityTermsId,
)
from qore.infrastructure.derivative_contract_semantics import DerivativeSettlementStyle
from qore.infrastructure.specialized_commodity_semantics import (
    ElectricityContractTerms,
    ElectricityDeliveryProfile,
    ElectricityLoadType,
    ElectricityQuantityStep,
    ElectricitySettlementPeriodCode,
    EnvironmentalApplicableLawCode,
    EnvironmentalCompliancePeriod,
    EnvironmentalProductTerms,
    EnvironmentalProductTypeCode,
    EnvironmentalTrackingSystemCode,
    EnvironmentalVintageEligibility,
    EnvironmentalVintageEligibilityKind,
    FreightContractRate,
    FreightTerms,
    FreightTransactionKind,
    FreightWorldscalePoints,
    SpecializedCommodityValidationError,
    WeatherIndexCode,
    WeatherIndexTerms,
    WeatherLevelUnitCode,
    WeatherNotionalPerIndexUnit,
    WeatherReferenceLevel,
    WeatherSettlementLevelCode,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _terms_id(value: int) -> CommodityTermsId:
    return CommodityTermsId(_uuid(value))


def _evidence(value: int) -> CommodityEvidenceRef:
    return CommodityEvidenceRef(_uuid(value))


def _reference() -> CommodityReferenceTerms:
    return CommodityReferenceTerms(
        terms_id=_terms_id(10),
        reference_identity_id=_identity(11),
        commodity_class=CommodityClassCode("energy"),
        measurement_unit_identity_id=_identity(12),
        evidence_ref=_evidence(13),
    )


def _delivery() -> CommodityPhysicalDeliveryTerms:
    return CommodityPhysicalDeliveryTerms(
        (
            CommodityDeliveryAlternative(
                grade=CommodityGradeCode("standard"),
                location_identity_id=_identity(20),
                method=CommodityDeliveryMethodCode("book-entry"),
                window=CommodityDeliveryWindow(
                    date(2027, 1, 1),
                    date(2027, 1, 31),
                ),
            ),
        )
    )


def _profile() -> ElectricityDeliveryProfile:
    return ElectricityDeliveryProfile(
        ElectricityLoadType.BASE,
        (ElectricitySettlementPeriodCode("all-hours"),),
    )


def _eligibility() -> EnvironmentalVintageEligibility:
    return EnvironmentalVintageEligibility(
        EnvironmentalVintageEligibilityKind.EXACT_SET,
        exact_vintages=(2026,),
    )


def _assert_invalid(*factories: Any) -> None:
    for factory in factories:
        with pytest.raises(SpecializedCommodityValidationError):
            factory()


def test_worldscale_points_require_non_negative_finite_decimal() -> None:
    assert FreightWorldscalePoints(Decimal("0")).value == Decimal("0")
    for value in (
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        1,
        1.0,
        True,
    ):
        with pytest.raises(SpecializedCommodityValidationError):
            FreightWorldscalePoints(cast(Decimal, value))


def test_electricity_quantity_steps_reject_duplicate_dates_and_mixed_units() -> None:
    with pytest.raises(SpecializedCommodityValidationError, match="dates must be unique"):
        ElectricityDeliveryProfile(
            ElectricityLoadType.BASE,
            (ElectricitySettlementPeriodCode("all-hours"),),
            (
                ElectricityQuantityStep(
                    date(2027, 1, 1), Decimal("100"), _identity(12)
                ),
                ElectricityQuantityStep(
                    date(2027, 1, 1), Decimal("80"), _identity(12)
                ),
            ),
        )
    with pytest.raises(SpecializedCommodityValidationError, match="one unit identity"):
        ElectricityDeliveryProfile(
            ElectricityLoadType.BASE,
            (ElectricitySettlementPeriodCode("all-hours"),),
            (
                ElectricityQuantityStep(
                    date(2027, 1, 1), Decimal("100"), _identity(12)
                ),
                ElectricityQuantityStep(
                    date(2027, 1, 15), Decimal("80"), _identity(99)
                ),
            ),
        )


def test_electricity_structural_guards_are_mutation_protected() -> None:
    period = ElectricitySettlementPeriodCode("all-hours")
    step = ElectricityQuantityStep(date(2027, 1, 1), Decimal("1"), _identity(12))
    reference = _reference()
    delivery = _delivery()
    profile = _profile()
    _assert_invalid(
        lambda: ElectricityDeliveryProfile(cast(ElectricityLoadType, "base"), (period,)),
        lambda: ElectricityDeliveryProfile(
            ElectricityLoadType.BASE,
            cast(tuple[ElectricitySettlementPeriodCode, ...], [period]),
        ),
        lambda: ElectricityDeliveryProfile(
            ElectricityLoadType.BASE,
            (cast(ElectricitySettlementPeriodCode, object()),),
        ),
        lambda: ElectricityDeliveryProfile(
            ElectricityLoadType.BASE,
            (period,),
            cast(tuple[ElectricityQuantityStep, ...], [step]),
        ),
        lambda: ElectricityDeliveryProfile(
            ElectricityLoadType.BASE,
            (period,),
            (cast(ElectricityQuantityStep, object()),),
        ),
        lambda: ElectricityQuantityStep(
            date(2027, 1, 1),
            Decimal("1"),
            cast(EconomicIdentityId, object()),
        ),
        lambda: ElectricityContractTerms(
            cast(CommodityTermsId, object()),
            reference,
            delivery,
            profile,
            _evidence(31),
        ),
        lambda: ElectricityContractTerms(
            _terms_id(30),
            cast(CommodityReferenceTerms, object()),
            delivery,
            profile,
            _evidence(31),
        ),
        lambda: ElectricityContractTerms(
            _terms_id(30),
            reference,
            cast(CommodityPhysicalDeliveryTerms, object()),
            profile,
            _evidence(31),
        ),
        lambda: ElectricityContractTerms(
            _terms_id(30),
            reference,
            delivery,
            cast(ElectricityDeliveryProfile, object()),
            _evidence(31),
        ),
        lambda: ElectricityContractTerms(
            _terms_id(30),
            reference,
            delivery,
            profile,
            cast(CommodityEvidenceRef, object()),
        ),
    )


def test_freight_structural_guards_are_mutation_protected() -> None:
    worldscale = FreightWorldscalePoints(Decimal("100"))
    rate = FreightContractRate(Decimal("15"), _identity(44))
    _assert_invalid(
        lambda: FreightContractRate(Decimal("15"), cast(EconomicIdentityId, object())),
        lambda: FreightContractRate(Decimal("-1"), _identity(44)),
        lambda: FreightTerms(
            cast(CommodityTermsId, object()),
            _identity(41),
            _identity(42),
            FreightTransactionKind.WET_VOYAGE_CHARTER,
            date(2027, 2, 1),
            date(2027, 2, 28),
            _evidence(43),
            worldscale_points=worldscale,
        ),
        lambda: FreightTerms(
            _terms_id(40),
            cast(EconomicIdentityId, object()),
            _identity(42),
            FreightTransactionKind.WET_VOYAGE_CHARTER,
            date(2027, 2, 1),
            date(2027, 2, 28),
            _evidence(43),
            worldscale_points=worldscale,
        ),
        lambda: FreightTerms(
            _terms_id(40),
            _identity(41),
            cast(EconomicIdentityId, object()),
            FreightTransactionKind.WET_VOYAGE_CHARTER,
            date(2027, 2, 1),
            date(2027, 2, 28),
            _evidence(43),
            worldscale_points=worldscale,
        ),
        lambda: FreightTerms(
            _terms_id(40),
            _identity(41),
            _identity(42),
            cast(FreightTransactionKind, "wet-voyage-charter"),
            date(2027, 2, 1),
            date(2027, 2, 28),
            _evidence(43),
            worldscale_points=worldscale,
        ),
        lambda: FreightTerms(
            _terms_id(40),
            _identity(41),
            _identity(42),
            FreightTransactionKind.WET_VOYAGE_CHARTER,
            date(2027, 2, 1),
            date(2027, 2, 28),
            _evidence(43),
            worldscale_points=cast(FreightWorldscalePoints, object()),
        ),
        lambda: FreightTerms(
            _terms_id(40),
            _identity(41),
            _identity(42),
            FreightTransactionKind.DRY_VOYAGE_CHARTER,
            date(2027, 2, 1),
            date(2027, 2, 28),
            _evidence(43),
            contract_rate=cast(FreightContractRate, object()),
        ),
        lambda: FreightTerms(
            _terms_id(40),
            _identity(41),
            _identity(42),
            FreightTransactionKind.DRY_VOYAGE_CHARTER,
            date(2027, 2, 1),
            date(2027, 2, 28),
            cast(CommodityEvidenceRef, object()),
            contract_rate=rate,
        ),
    )


def test_weather_structural_guards_are_mutation_protected() -> None:
    reference_level = WeatherReferenceLevel(
        Decimal("65"), WeatherLevelUnitCode("degree-days")
    )
    notional = WeatherNotionalPerIndexUnit(Decimal("20"), _identity(53))
    _assert_invalid(
        lambda: WeatherReferenceLevel(
            Decimal("65"), cast(WeatherLevelUnitCode, object())
        ),
        lambda: WeatherReferenceLevel(
            cast(Decimal, 65), WeatherLevelUnitCode("degree-days")
        ),
        lambda: WeatherNotionalPerIndexUnit(
            Decimal("20"), cast(EconomicIdentityId, object())
        ),
        lambda: WeatherIndexTerms(
            cast(CommodityTermsId, object()),
            _identity(51),
            _identity(52),
            WeatherIndexCode("hdd"),
            date(2027, 1, 1),
            date(2027, 1, 31),
            reference_level,
            WeatherSettlementLevelCode("cumulative"),
            notional,
            _evidence(54),
        ),
        lambda: WeatherIndexTerms(
            _terms_id(50),
            cast(EconomicIdentityId, object()),
            _identity(52),
            WeatherIndexCode("hdd"),
            date(2027, 1, 1),
            date(2027, 1, 31),
            reference_level,
            WeatherSettlementLevelCode("cumulative"),
            notional,
            _evidence(54),
        ),
        lambda: WeatherIndexTerms(
            _terms_id(50),
            _identity(51),
            cast(EconomicIdentityId, object()),
            WeatherIndexCode("hdd"),
            date(2027, 1, 1),
            date(2027, 1, 31),
            reference_level,
            WeatherSettlementLevelCode("cumulative"),
            notional,
            _evidence(54),
        ),
        lambda: WeatherIndexTerms(
            _terms_id(50),
            _identity(51),
            _identity(52),
            cast(WeatherIndexCode, object()),
            date(2027, 1, 1),
            date(2027, 1, 31),
            reference_level,
            WeatherSettlementLevelCode("cumulative"),
            notional,
            _evidence(54),
        ),
        lambda: WeatherIndexTerms(
            _terms_id(50),
            _identity(51),
            _identity(52),
            WeatherIndexCode("hdd"),
            date(2027, 1, 1),
            date(2027, 1, 31),
            cast(WeatherReferenceLevel, object()),
            WeatherSettlementLevelCode("cumulative"),
            notional,
            _evidence(54),
        ),
        lambda: WeatherIndexTerms(
            _terms_id(50),
            _identity(51),
            _identity(52),
            WeatherIndexCode("hdd"),
            date(2027, 1, 1),
            date(2027, 1, 31),
            reference_level,
            cast(WeatherSettlementLevelCode, object()),
            notional,
            _evidence(54),
        ),
        lambda: WeatherIndexTerms(
            _terms_id(50),
            _identity(51),
            _identity(52),
            WeatherIndexCode("hdd"),
            date(2027, 1, 1),
            date(2027, 1, 31),
            reference_level,
            WeatherSettlementLevelCode("cumulative"),
            cast(WeatherNotionalPerIndexUnit, object()),
            _evidence(54),
        ),
        lambda: WeatherIndexTerms(
            _terms_id(50),
            _identity(51),
            _identity(52),
            WeatherIndexCode("hdd"),
            date(2027, 1, 1),
            date(2027, 1, 31),
            reference_level,
            WeatherSettlementLevelCode("cumulative"),
            notional,
            cast(CommodityEvidenceRef, object()),
        ),
    )


def test_environmental_structural_guards_are_mutation_protected() -> None:
    eligibility = _eligibility()
    reference = _reference()
    _assert_invalid(
        lambda: EnvironmentalCompliancePeriod(cast(int, True), 2028),
        lambda: EnvironmentalCompliancePeriod(0, 2028),
        lambda: EnvironmentalCompliancePeriod(2026, 10000),
        lambda: EnvironmentalVintageEligibility(
            cast(EnvironmentalVintageEligibilityKind, "exact-set"),
            (2026,),
        ),
        lambda: EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.EXACT_SET,
            cast(tuple[int, ...], [2026]),
        ),
        lambda: EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.EXACT_SET,
            exact_vintages=(0,),
        ),
        lambda: EnvironmentalProductTerms(
            cast(CommodityTermsId, object()),
            reference,
            DerivativeSettlementStyle.CASH,
            EnvironmentalProductTypeCode("allowance"),
            eligibility,
            _evidence(63),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            cast(CommodityReferenceTerms, object()),
            DerivativeSettlementStyle.CASH,
            EnvironmentalProductTypeCode("allowance"),
            eligibility,
            _evidence(63),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            reference,
            cast(DerivativeSettlementStyle, "cash"),
            EnvironmentalProductTypeCode("allowance"),
            eligibility,
            _evidence(63),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            reference,
            DerivativeSettlementStyle.CASH,
            cast(EnvironmentalProductTypeCode, object()),
            eligibility,
            _evidence(63),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            reference,
            DerivativeSettlementStyle.CASH,
            EnvironmentalProductTypeCode("allowance"),
            cast(EnvironmentalVintageEligibility, object()),
            _evidence(63),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            reference,
            DerivativeSettlementStyle.PHYSICAL,
            EnvironmentalProductTypeCode("allowance"),
            eligibility,
            _evidence(63),
            physical_delivery=cast(CommodityPhysicalDeliveryTerms, object()),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            reference,
            DerivativeSettlementStyle.CASH,
            EnvironmentalProductTypeCode("allowance"),
            eligibility,
            _evidence(63),
            compliance_period=cast(EnvironmentalCompliancePeriod, object()),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            reference,
            DerivativeSettlementStyle.CASH,
            EnvironmentalProductTypeCode("allowance"),
            eligibility,
            _evidence(63),
            applicable_law=cast(EnvironmentalApplicableLawCode, object()),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            reference,
            DerivativeSettlementStyle.CASH,
            EnvironmentalProductTypeCode("allowance"),
            eligibility,
            _evidence(63),
            tracking_system=cast(EnvironmentalTrackingSystemCode, object()),
        ),
        lambda: EnvironmentalProductTerms(
            _terms_id(60),
            reference,
            DerivativeSettlementStyle.CASH,
            EnvironmentalProductTypeCode("allowance"),
            eligibility,
            cast(CommodityEvidenceRef, object()),
        ),
    )


def test_environmental_optional_qualifications_project_independently() -> None:
    reference_expected = (
        "commodity-reference",
        (str(_uuid(10)),),
        (str(_uuid(11)),),
        ("energy",),
        (str(_uuid(12)),),
        (str(_uuid(13)),),
    )
    physical_expected = (
        (
            (
                ("standard",),
                (str(_uuid(20)),),
                ("book-entry",),
                ("2027-01-01", "2027-01-31"),
            ),
        ),
    )
    eligibility = _eligibility()
    law_only = EnvironmentalProductTerms(
        terms_id=_terms_id(70),
        commodity_reference=_reference(),
        settlement_style=DerivativeSettlementStyle.CASH,
        product_type=EnvironmentalProductTypeCode("allowance"),
        vintage_eligibility=eligibility,
        evidence_ref=_evidence(71),
        applicable_law=EnvironmentalApplicableLawCode("washington-cap-invest"),
    )
    assert law_only.logical_values() == (
        "environmental-product",
        (str(_uuid(70)),),
        reference_expected,
        "cash",
        ("allowance",),
        ("exact-set", (2026,), None),
        None,
        None,
        ("washington-cap-invest",),
        None,
        (str(_uuid(71)),),
    )
    compliance_tracking = EnvironmentalProductTerms(
        terms_id=_terms_id(72),
        commodity_reference=_reference(),
        settlement_style=DerivativeSettlementStyle.CASH,
        product_type=EnvironmentalProductTypeCode("allowance"),
        vintage_eligibility=eligibility,
        evidence_ref=_evidence(73),
        compliance_period=EnvironmentalCompliancePeriod(2025, 2028),
        tracking_system=EnvironmentalTrackingSystemCode("citss"),
    )
    assert compliance_tracking.logical_values() == (
        "environmental-product",
        (str(_uuid(72)),),
        reference_expected,
        "cash",
        ("allowance",),
        ("exact-set", (2026,), None),
        None,
        (2025, 2028),
        None,
        ("citss",),
        (str(_uuid(73)),),
    )
    physical_only = EnvironmentalProductTerms(
        terms_id=_terms_id(74),
        commodity_reference=_reference(),
        settlement_style=DerivativeSettlementStyle.PHYSICAL,
        product_type=EnvironmentalProductTypeCode("allowance"),
        vintage_eligibility=eligibility,
        evidence_ref=_evidence(75),
        physical_delivery=_delivery(),
    )
    assert physical_only.logical_values() == (
        "environmental-product",
        (str(_uuid(74)),),
        reference_expected,
        "physical",
        ("allowance",),
        ("exact-set", (2026,), None),
        physical_expected,
        None,
        None,
        None,
        (str(_uuid(75)),),
    )
