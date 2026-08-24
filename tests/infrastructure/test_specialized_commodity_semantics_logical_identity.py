from __future__ import annotations

from dataclasses import fields
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

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


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def _identity_expected(value: EconomicIdentityId) -> tuple[str, ...]:
    return (str(value.value),)


def _terms_id_expected(value: CommodityTermsId) -> tuple[str, ...]:
    return (str(value.value),)


def _evidence_expected(value: CommodityEvidenceRef) -> tuple[str, ...]:
    return (str(value.value),)


def _reference_expected(value: CommodityReferenceTerms) -> tuple[object, ...]:
    return (
        "commodity-reference",
        _terms_id_expected(value.terms_id),
        _identity_expected(value.reference_identity_id),
        (value.commodity_class.value,),
        _identity_expected(value.measurement_unit_identity_id),
        _evidence_expected(value.evidence_ref),
    )


def _physical_delivery_expected(
    value: CommodityPhysicalDeliveryTerms,
) -> tuple[object, ...]:
    alternatives = tuple(
        (
            (alternative.grade.value,),
            _identity_expected(alternative.location_identity_id),
            (alternative.method.value,),
            (
                alternative.window.start_date.isoformat(),
                alternative.window.end_date.isoformat(),
            ),
        )
        for alternative in value.alternatives
    )
    return (alternatives,)


def _profile_expected(value: ElectricityDeliveryProfile) -> tuple[object, ...]:
    return (
        value.load_type.value,
        tuple((period.value,) for period in value.settlement_periods),
        tuple(
            (
                step.effective_date.isoformat(),
                _canonical_decimal(step.quantity),
                _identity_expected(step.unit_identity_id),
            )
            for step in value.quantity_steps
        ),
    )


def _electricity_expected(value: ElectricityContractTerms) -> tuple[object, ...]:
    return (
        "electricity-contract",
        _terms_id_expected(value.terms_id),
        _reference_expected(value.commodity_reference),
        _physical_delivery_expected(value.physical_delivery),
        _profile_expected(value.delivery_profile),
        _evidence_expected(value.evidence_ref),
    )


def _freight_expected(value: FreightTerms) -> tuple[object, ...]:
    worldscale = (
        (_canonical_decimal(value.worldscale_points.value),)
        if value.worldscale_points is not None
        else None
    )
    contract_rate = (
        (
            _canonical_decimal(value.contract_rate.value),
            _identity_expected(value.contract_rate.quote_identity_id),
        )
        if value.contract_rate is not None
        else None
    )
    return (
        "freight-contract",
        _terms_id_expected(value.terms_id),
        _identity_expected(value.instrument_identity_id),
        _identity_expected(value.route_identity_id),
        value.kind.value,
        value.calculation_start_date.isoformat(),
        value.calculation_end_date.isoformat(),
        worldscale,
        contract_rate,
        _evidence_expected(value.evidence_ref),
    )


def _weather_expected(value: WeatherIndexTerms) -> tuple[object, ...]:
    return (
        "weather-index-contract",
        _terms_id_expected(value.terms_id),
        _identity_expected(value.instrument_identity_id),
        _identity_expected(value.station_identity_id),
        (value.index_code.value,),
        value.calculation_start_date.isoformat(),
        value.calculation_end_date.isoformat(),
        (
            _canonical_decimal(value.reference_level.value),
            (value.reference_level.unit.value,),
        ),
        (value.settlement_level.value,),
        (
            _canonical_decimal(value.notional_per_index_unit.value),
            _identity_expected(value.notional_per_index_unit.currency_identity_id),
        ),
        _evidence_expected(value.evidence_ref),
    )


def _vintage_expected(value: EnvironmentalVintageEligibility) -> tuple[object, ...]:
    return (value.kind.value, value.exact_vintages, value.contract_year)


def _environmental_expected(value: EnvironmentalProductTerms) -> tuple[object, ...]:
    return (
        "environmental-product",
        _terms_id_expected(value.terms_id),
        _reference_expected(value.commodity_reference),
        value.settlement_style.value,
        (value.product_type.value,),
        _vintage_expected(value.vintage_eligibility),
        (
            _physical_delivery_expected(value.physical_delivery)
            if value.physical_delivery is not None
            else None
        ),
        (
            (value.compliance_period.start_year, value.compliance_period.end_year)
            if value.compliance_period is not None
            else None
        ),
        (value.applicable_law.value,) if value.applicable_law is not None else None,
        (value.tracking_system.value,) if value.tracking_system is not None else None,
        _evidence_expected(value.evidence_ref),
    )


def _reference(
    *,
    terms: int,
    commodity: int,
    unit: int,
    evidence: int,
    commodity_class: str,
) -> CommodityReferenceTerms:
    return CommodityReferenceTerms(
        terms_id=_terms_id(terms),
        reference_identity_id=_identity(commodity),
        commodity_class=CommodityClassCode(commodity_class),
        measurement_unit_identity_id=_identity(unit),
        evidence_ref=_evidence(evidence),
    )


def _physical_delivery(*, location: int) -> CommodityPhysicalDeliveryTerms:
    return CommodityPhysicalDeliveryTerms(
        (
            CommodityDeliveryAlternative(
                grade=CommodityGradeCode("standard"),
                location_identity_id=_identity(location),
                method=CommodityDeliveryMethodCode("book-entry"),
                window=CommodityDeliveryWindow(date(2027, 1, 1), date(2027, 1, 31)),
            ),
        )
    )


def test_gateb_exact_specialized_commodity_field_surfaces_are_closed() -> None:
    surfaces: tuple[tuple[type[Any], tuple[str, ...]], ...] = (
        (ElectricitySettlementPeriodCode, ("value",)),
        (ElectricityQuantityStep, ("effective_date", "quantity", "unit_identity_id")),
        (ElectricityDeliveryProfile, ("load_type", "settlement_periods", "quantity_steps")),
        (
            ElectricityContractTerms,
            (
                "terms_id",
                "commodity_reference",
                "physical_delivery",
                "delivery_profile",
                "evidence_ref",
            ),
        ),
        (FreightWorldscalePoints, ("value",)),
        (FreightContractRate, ("value", "quote_identity_id")),
        (
            FreightTerms,
            (
                "terms_id",
                "instrument_identity_id",
                "route_identity_id",
                "kind",
                "calculation_start_date",
                "calculation_end_date",
                "evidence_ref",
                "worldscale_points",
                "contract_rate",
            ),
        ),
        (WeatherIndexCode, ("value",)),
        (WeatherLevelUnitCode, ("value",)),
        (WeatherSettlementLevelCode, ("value",)),
        (WeatherReferenceLevel, ("value", "unit")),
        (WeatherNotionalPerIndexUnit, ("value", "currency_identity_id")),
        (
            WeatherIndexTerms,
            (
                "terms_id",
                "instrument_identity_id",
                "station_identity_id",
                "index_code",
                "calculation_start_date",
                "calculation_end_date",
                "reference_level",
                "settlement_level",
                "notional_per_index_unit",
                "evidence_ref",
            ),
        ),
        (EnvironmentalProductTypeCode, ("value",)),
        (EnvironmentalApplicableLawCode, ("value",)),
        (EnvironmentalTrackingSystemCode, ("value",)),
        (EnvironmentalCompliancePeriod, ("start_year", "end_year")),
        (
            EnvironmentalVintageEligibility,
            ("kind", "exact_vintages", "contract_year"),
        ),
        (
            EnvironmentalProductTerms,
            (
                "terms_id",
                "commodity_reference",
                "settlement_style",
                "product_type",
                "vintage_eligibility",
                "evidence_ref",
                "physical_delivery",
                "compliance_period",
                "applicable_law",
                "tracking_system",
            ),
        ),
    )
    for cls, expected in surfaces:
        assert tuple(field.name for field in fields(cls)) == expected


def test_gateb_electricity_projection_is_independently_reconstructed() -> None:
    reference = _reference(
        terms=1,
        commodity=2,
        unit=3,
        evidence=4,
        commodity_class="energy",
    )
    delivery = _physical_delivery(location=5)
    terms = ElectricityContractTerms(
        terms_id=_terms_id(6),
        commodity_reference=reference,
        physical_delivery=delivery,
        delivery_profile=ElectricityDeliveryProfile(
            load_type=ElectricityLoadType.PEAK,
            settlement_periods=(
                ElectricitySettlementPeriodCode("weekday-peak"),
                ElectricitySettlementPeriodCode("weekend-all-day"),
            ),
            quantity_steps=(
                ElectricityQuantityStep(date(2027, 1, 1), Decimal("100.00"), _identity(3)),
                ElectricityQuantityStep(date(2027, 1, 15), Decimal("80.0"), _identity(3)),
            ),
        ),
        evidence_ref=_evidence(7),
    )
    assert terms.logical_values() == _electricity_expected(terms)


def test_gateb_wet_freight_projection_is_independently_reconstructed() -> None:
    terms = FreightTerms(
        terms_id=_terms_id(10),
        instrument_identity_id=_identity(11),
        route_identity_id=_identity(12),
        kind=FreightTransactionKind.WET_VOYAGE_CHARTER,
        calculation_start_date=date(2027, 2, 1),
        calculation_end_date=date(2027, 2, 28),
        evidence_ref=_evidence(13),
        worldscale_points=FreightWorldscalePoints(Decimal("125.00")),
    )
    assert terms.logical_values() == _freight_expected(terms)


def test_gateb_contract_rate_freight_projection_is_independently_reconstructed() -> None:
    terms = FreightTerms(
        terms_id=_terms_id(20),
        instrument_identity_id=_identity(21),
        route_identity_id=_identity(22),
        kind=FreightTransactionKind.TIME_CHARTER,
        calculation_start_date=date(2027, 3, 1),
        calculation_end_date=date(2027, 3, 31),
        evidence_ref=_evidence(23),
        contract_rate=FreightContractRate(Decimal("15.50"), _identity(24)),
    )
    assert terms.logical_values() == _freight_expected(terms)


def test_gateb_weather_projection_is_independently_reconstructed() -> None:
    terms = WeatherIndexTerms(
        terms_id=_terms_id(30),
        instrument_identity_id=_identity(31),
        station_identity_id=_identity(32),
        index_code=WeatherIndexCode("hdd"),
        calculation_start_date=date(2027, 1, 1),
        calculation_end_date=date(2027, 1, 31),
        reference_level=WeatherReferenceLevel(
            Decimal("65.00"), WeatherLevelUnitCode("degree-days")
        ),
        settlement_level=WeatherSettlementLevelCode("cumulative"),
        notional_per_index_unit=WeatherNotionalPerIndexUnit(
            Decimal("20.00"), _identity(33)
        ),
        evidence_ref=_evidence(34),
    )
    assert terms.logical_values() == _weather_expected(terms)


def test_gateb_environmental_physical_projection_is_independently_reconstructed() -> None:
    terms = EnvironmentalProductTerms(
        terms_id=_terms_id(40),
        commodity_reference=_reference(
            terms=41,
            commodity=42,
            unit=43,
            evidence=44,
            commodity_class="environmental",
        ),
        settlement_style=DerivativeSettlementStyle.PHYSICAL,
        product_type=EnvironmentalProductTypeCode("allowance"),
        vintage_eligibility=EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.EXACT_SET,
            exact_vintages=(2026, 2025),
        ),
        evidence_ref=_evidence(45),
        physical_delivery=_physical_delivery(location=46),
        compliance_period=EnvironmentalCompliancePeriod(2025, 2028),
        applicable_law=EnvironmentalApplicableLawCode("washington-cap-invest"),
        tracking_system=EnvironmentalTrackingSystemCode("citss"),
    )
    assert terms.logical_values() == _environmental_expected(terms)


def test_gateb_environmental_cash_projection_preserves_none_and_year_prior() -> None:
    terms = EnvironmentalProductTerms(
        terms_id=_terms_id(50),
        commodity_reference=_reference(
            terms=51,
            commodity=52,
            unit=53,
            evidence=54,
            commodity_class="environmental",
        ),
        settlement_style=DerivativeSettlementStyle.CASH,
        product_type=EnvironmentalProductTypeCode("allowance"),
        vintage_eligibility=EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.CONTRACT_YEAR_AND_PRIOR,
            contract_year=2027,
        ),
        evidence_ref=_evidence(55),
    )
    assert terms.logical_values() == _environmental_expected(terms)
