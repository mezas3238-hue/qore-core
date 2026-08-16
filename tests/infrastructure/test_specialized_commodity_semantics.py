from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal
from typing import cast
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


def _reference(
    commodity_identity: EconomicIdentityId | None = None,
    unit_identity: EconomicIdentityId | None = None,
) -> CommodityReferenceTerms:
    return CommodityReferenceTerms(
        terms_id=_terms_id(10),
        reference_identity_id=commodity_identity or _identity(11),
        commodity_class=CommodityClassCode("energy"),
        measurement_unit_identity_id=unit_identity or _identity(12),
        evidence_ref=_evidence(13),
    )


def _physical_delivery(
    *,
    start: date = date(2027, 1, 1),
    end: date = date(2027, 1, 31),
) -> CommodityPhysicalDeliveryTerms:
    return CommodityPhysicalDeliveryTerms(
        (
            CommodityDeliveryAlternative(
                grade=CommodityGradeCode("standard"),
                location_identity_id=_identity(20),
                method=CommodityDeliveryMethodCode("book-entry"),
                window=CommodityDeliveryWindow(start, end),
            ),
        )
    )


def _profile(
    *,
    load_type: ElectricityLoadType = ElectricityLoadType.BASE,
    periods: tuple[ElectricitySettlementPeriodCode, ...] | None = None,
    steps: tuple[ElectricityQuantityStep, ...] = (),
) -> ElectricityDeliveryProfile:
    return ElectricityDeliveryProfile(
        load_type=load_type,
        settlement_periods=periods or (ElectricitySettlementPeriodCode("all-hours"),),
        quantity_steps=steps,
    )


def _electricity(
    *,
    profile: ElectricityDeliveryProfile | None = None,
    reference: CommodityReferenceTerms | None = None,
) -> ElectricityContractTerms:
    commodity_reference = reference or _reference()
    return ElectricityContractTerms(
        terms_id=_terms_id(30),
        commodity_reference=commodity_reference,
        physical_delivery=_physical_delivery(),
        delivery_profile=profile or _profile(),
        evidence_ref=_evidence(31),
    )


def _freight(
    kind: FreightTransactionKind,
    *,
    worldscale: FreightWorldscalePoints | None = None,
    contract_rate: FreightContractRate | None = None,
) -> FreightTerms:
    return FreightTerms(
        terms_id=_terms_id(40),
        instrument_identity_id=_identity(41),
        route_identity_id=_identity(42),
        kind=kind,
        calculation_start_date=date(2027, 2, 1),
        calculation_end_date=date(2027, 2, 28),
        worldscale_points=worldscale,
        contract_rate=contract_rate,
        evidence_ref=_evidence(43),
    )


def _weather() -> WeatherIndexTerms:
    return WeatherIndexTerms(
        terms_id=_terms_id(50),
        instrument_identity_id=_identity(51),
        station_identity_id=_identity(52),
        index_code=WeatherIndexCode("hdd"),
        calculation_start_date=date(2027, 1, 1),
        calculation_end_date=date(2027, 1, 31),
        reference_level=WeatherReferenceLevel(
            Decimal("65"),
            WeatherLevelUnitCode("degree-days"),
        ),
        settlement_level=WeatherSettlementLevelCode("cumulative"),
        notional_per_index_unit=WeatherNotionalPerIndexUnit(
            Decimal("20"),
            _identity(53),
        ),
        evidence_ref=_evidence(54),
    )


def _environmental(
    eligibility: EnvironmentalVintageEligibility,
    *,
    settlement_style: DerivativeSettlementStyle = DerivativeSettlementStyle.PHYSICAL,
    physical_delivery: CommodityPhysicalDeliveryTerms | None = None,
) -> EnvironmentalProductTerms:
    return EnvironmentalProductTerms(
        terms_id=_terms_id(60),
        commodity_reference=_reference(
            commodity_identity=_identity(61),
            unit_identity=_identity(62),
        ),
        settlement_style=settlement_style,
        product_type=EnvironmentalProductTypeCode("allowance"),
        vintage_eligibility=eligibility,
        physical_delivery=(
            _physical_delivery()
            if settlement_style is DerivativeSettlementStyle.PHYSICAL
            and physical_delivery is None
            else physical_delivery
        ),
        compliance_period=EnvironmentalCompliancePeriod(2026, 2028),
        applicable_law=EnvironmentalApplicableLawCode("washington-cap-invest"),
        tracking_system=EnvironmentalTrackingSystemCode("citss"),
        evidence_ref=_evidence(63),
    )


def test_electricity_load_types_are_distinct_logical_material() -> None:
    base = _electricity(profile=_profile(load_type=ElectricityLoadType.BASE))
    peak = _electricity(profile=_profile(load_type=ElectricityLoadType.PEAK))
    off_peak = _electricity(profile=_profile(load_type=ElectricityLoadType.OFF_PEAK))
    assert len({base.logical_values(), peak.logical_values(), off_peak.logical_values()}) == 3


def test_electricity_settlement_period_codes_are_required_and_canonicalized() -> None:
    with pytest.raises(SpecializedCommodityValidationError, match="non-empty"):
        ElectricityDeliveryProfile(ElectricityLoadType.CUSTOM, ())
    first = _profile(
        load_type=ElectricityLoadType.CUSTOM,
        periods=(
            ElectricitySettlementPeriodCode("weekend-all-day"),
            ElectricitySettlementPeriodCode("weekday-off-peak"),
        ),
    )
    second = _profile(
        load_type=ElectricityLoadType.CUSTOM,
        periods=(
            ElectricitySettlementPeriodCode("weekday-off-peak"),
            ElectricitySettlementPeriodCode("weekend-all-day"),
        ),
    )
    assert first.logical_values() == second.logical_values()


def test_electricity_rejects_duplicate_settlement_period_codes() -> None:
    with pytest.raises(SpecializedCommodityValidationError, match="must be unique"):
        _profile(
            periods=(
                ElectricitySettlementPeriodCode("all-hours"),
                ElectricitySettlementPeriodCode("all-hours"),
            )
        )


def test_electricity_shaped_quantity_is_retained_and_canonicalized() -> None:
    unit = _identity(12)
    left = ElectricityQuantityStep(date(2027, 1, 15), Decimal("80"), unit)
    right = ElectricityQuantityStep(date(2027, 1, 1), Decimal("100"), unit)
    terms = _electricity(profile=_profile(steps=(left, right)))
    assert terms.delivery_profile.quantity_steps[0].effective_date == date(2027, 1, 1)


def test_electricity_quantity_requires_positive_decimal() -> None:
    for value in (Decimal("0"), Decimal("-1"), Decimal("NaN"), 1, 1.0, True):
        with pytest.raises(SpecializedCommodityValidationError):
            ElectricityQuantityStep(
                date(2027, 1, 1),
                cast(Decimal, value),
                _identity(12),
            )


def test_electricity_quantity_unit_must_match_generic_commodity_reference() -> None:
    profile = _profile(
        steps=(
            ElectricityQuantityStep(
                date(2027, 1, 1),
                Decimal("100"),
                _identity(999),
            ),
        )
    )
    with pytest.raises(SpecializedCommodityValidationError, match="measurement unit"):
        _electricity(profile=profile)


def test_electricity_quantity_dates_must_fit_delivery_window() -> None:
    profile = _profile(
        steps=(
            ElectricityQuantityStep(
                date(2027, 2, 1),
                Decimal("100"),
                _identity(12),
            ),
        )
    )
    with pytest.raises(SpecializedCommodityValidationError, match="delivery alternatives"):
        _electricity(profile=profile)


def test_wet_voyage_freight_requires_worldscale_only() -> None:
    terms = _freight(
        FreightTransactionKind.WET_VOYAGE_CHARTER,
        worldscale=FreightWorldscalePoints(Decimal("125")),
    )
    assert terms.worldscale_points is not None
    with pytest.raises(SpecializedCommodityValidationError, match="Worldscale"):
        _freight(
            FreightTransactionKind.WET_VOYAGE_CHARTER,
            contract_rate=FreightContractRate(Decimal("15"), _identity(44)),
        )


def test_dry_and_time_charter_require_contract_rate_only() -> None:
    for kind in (
        FreightTransactionKind.DRY_VOYAGE_CHARTER,
        FreightTransactionKind.TIME_CHARTER,
    ):
        terms = _freight(
            kind,
            contract_rate=FreightContractRate(Decimal("15"), _identity(44)),
        )
        assert terms.contract_rate is not None
        with pytest.raises(SpecializedCommodityValidationError, match="contract rate"):
            _freight(kind, worldscale=FreightWorldscalePoints(Decimal("100")))


def test_worldscale_and_contract_rate_cannot_collapse() -> None:
    wet = _freight(
        FreightTransactionKind.WET_VOYAGE_CHARTER,
        worldscale=FreightWorldscalePoints(Decimal("100")),
    )
    dry = _freight(
        FreightTransactionKind.DRY_VOYAGE_CHARTER,
        contract_rate=FreightContractRate(Decimal("100"), _identity(44)),
    )
    assert wet.logical_values() != dry.logical_values()


def test_freight_route_is_explicit_logical_material() -> None:
    left = _freight(
        FreightTransactionKind.WET_VOYAGE_CHARTER,
        worldscale=FreightWorldscalePoints(Decimal("100")),
    )
    right = FreightTerms(
        terms_id=left.terms_id,
        instrument_identity_id=left.instrument_identity_id,
        route_identity_id=_identity(999),
        kind=left.kind,
        calculation_start_date=left.calculation_start_date,
        calculation_end_date=left.calculation_end_date,
        worldscale_points=left.worldscale_points,
        contract_rate=None,
        evidence_ref=left.evidence_ref,
    )
    assert left.logical_values() != right.logical_values()


def test_freight_period_must_be_chronological() -> None:
    with pytest.raises(SpecializedCommodityValidationError, match="must not precede"):
        FreightTerms(
            terms_id=_terms_id(40),
            instrument_identity_id=_identity(41),
            route_identity_id=_identity(42),
            kind=FreightTransactionKind.WET_VOYAGE_CHARTER,
            calculation_start_date=date(2027, 3, 1),
            calculation_end_date=date(2027, 2, 28),
            worldscale_points=FreightWorldscalePoints(Decimal("100")),
            evidence_ref=_evidence(43),
        )


def test_weather_contract_preserves_index_station_period_and_notional() -> None:
    terms = _weather()
    logical = terms.logical_values()
    assert logical[0] == "weather-index-contract"
    assert terms.index_code.value == "hdd"
    assert terms.station_identity_id == _identity(52)


def test_weather_index_kind_is_material() -> None:
    left = _weather()
    right = WeatherIndexTerms(
        terms_id=left.terms_id,
        instrument_identity_id=left.instrument_identity_id,
        station_identity_id=left.station_identity_id,
        index_code=WeatherIndexCode("cdd"),
        calculation_start_date=left.calculation_start_date,
        calculation_end_date=left.calculation_end_date,
        reference_level=left.reference_level,
        settlement_level=left.settlement_level,
        notional_per_index_unit=left.notional_per_index_unit,
        evidence_ref=left.evidence_ref,
    )
    assert left.logical_values() != right.logical_values()


def test_weather_station_must_differ_from_instrument_identity() -> None:
    with pytest.raises(SpecializedCommodityValidationError, match="must differ"):
        WeatherIndexTerms(
            terms_id=_terms_id(50),
            instrument_identity_id=_identity(51),
            station_identity_id=_identity(51),
            index_code=WeatherIndexCode("hdd"),
            calculation_start_date=date(2027, 1, 1),
            calculation_end_date=date(2027, 1, 31),
            reference_level=WeatherReferenceLevel(
                Decimal("65"),
                WeatherLevelUnitCode("degree-days"),
            ),
            settlement_level=WeatherSettlementLevelCode("cumulative"),
            notional_per_index_unit=WeatherNotionalPerIndexUnit(
                Decimal("20"),
                _identity(53),
            ),
            evidence_ref=_evidence(54),
        )


def test_weather_notional_requires_positive_decimal() -> None:
    for value in (Decimal("0"), Decimal("-1"), Decimal("NaN"), 1, 1.0, True):
        with pytest.raises(SpecializedCommodityValidationError):
            WeatherNotionalPerIndexUnit(cast(Decimal, value), _identity(53))


def test_weather_period_rejects_reverse_chronology() -> None:
    base = _weather()
    with pytest.raises(SpecializedCommodityValidationError, match="must not precede"):
        WeatherIndexTerms(
            terms_id=base.terms_id,
            instrument_identity_id=base.instrument_identity_id,
            station_identity_id=base.station_identity_id,
            index_code=base.index_code,
            calculation_start_date=date(2027, 2, 1),
            calculation_end_date=date(2027, 1, 31),
            reference_level=base.reference_level,
            settlement_level=base.settlement_level,
            notional_per_index_unit=base.notional_per_index_unit,
            evidence_ref=base.evidence_ref,
        )


def test_environmental_specific_vintage_and_year_plus_prior_are_distinct() -> None:
    specific = _environmental(
        EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.EXACT_SET,
            exact_vintages=(2026,),
        )
    )
    standard = _environmental(
        EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.CONTRACT_YEAR_AND_PRIOR,
            contract_year=2026,
        )
    )
    assert specific.logical_values() != standard.logical_values()


def test_environmental_exact_vintages_are_unique_and_canonicalized() -> None:
    eligibility = EnvironmentalVintageEligibility(
        EnvironmentalVintageEligibilityKind.EXACT_SET,
        exact_vintages=(2026, 2024, 2025),
    )
    assert eligibility.exact_vintages == (2024, 2025, 2026)
    with pytest.raises(SpecializedCommodityValidationError, match="must be unique"):
        EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.EXACT_SET,
            exact_vintages=(2026, 2026),
        )


def test_environmental_exact_set_requires_vintages_only() -> None:
    with pytest.raises(SpecializedCommodityValidationError, match="requires vintages"):
        EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.EXACT_SET,
            exact_vintages=(),
        )
    with pytest.raises(SpecializedCommodityValidationError, match="forbids"):
        EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.EXACT_SET,
            exact_vintages=(2026,),
            contract_year=2026,
        )


def test_environmental_year_and_prior_requires_contract_year_only() -> None:
    with pytest.raises(SpecializedCommodityValidationError, match="requires contract_year"):
        EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.CONTRACT_YEAR_AND_PRIOR
        )
    with pytest.raises(SpecializedCommodityValidationError, match="contract_year only"):
        EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.CONTRACT_YEAR_AND_PRIOR,
            exact_vintages=(2025,),
            contract_year=2026,
        )


def test_environmental_compliance_period_is_chronological() -> None:
    with pytest.raises(SpecializedCommodityValidationError, match="must not precede"):
        EnvironmentalCompliancePeriod(2028, 2026)


def test_environmental_physical_requires_generic_umi07_delivery() -> None:
    eligibility = EnvironmentalVintageEligibility(
        EnvironmentalVintageEligibilityKind.EXACT_SET,
        exact_vintages=(2026,),
    )
    with pytest.raises(SpecializedCommodityValidationError, match="requires physical"):
        EnvironmentalProductTerms(
            terms_id=_terms_id(60),
            commodity_reference=_reference(),
            settlement_style=DerivativeSettlementStyle.PHYSICAL,
            product_type=EnvironmentalProductTypeCode("allowance"),
            vintage_eligibility=eligibility,
            evidence_ref=_evidence(63),
        )


def test_environmental_cash_forbids_physical_delivery() -> None:
    eligibility = EnvironmentalVintageEligibility(
        EnvironmentalVintageEligibilityKind.EXACT_SET,
        exact_vintages=(2026,),
    )
    with pytest.raises(SpecializedCommodityValidationError, match="must not carry"):
        _environmental(
            eligibility,
            settlement_style=DerivativeSettlementStyle.CASH,
            physical_delivery=_physical_delivery(),
        )


def test_environmental_tracking_system_and_law_are_static_material() -> None:
    terms = _environmental(
        EnvironmentalVintageEligibility(
            EnvironmentalVintageEligibilityKind.EXACT_SET,
            exact_vintages=(2026,),
        )
    )
    assert terms.tracking_system == EnvironmentalTrackingSystemCode("citss")
    assert terms.applicable_law == EnvironmentalApplicableLawCode(
        "washington-cap-invest"
    )


def test_codes_require_canonical_lowercase_syntax() -> None:
    constructors = (
        ElectricitySettlementPeriodCode,
        WeatherIndexCode,
        WeatherLevelUnitCode,
        WeatherSettlementLevelCode,
        EnvironmentalProductTypeCode,
        EnvironmentalApplicableLawCode,
        EnvironmentalTrackingSystemCode,
    )
    for constructor in constructors:
        with pytest.raises(SpecializedCommodityValidationError):
            constructor("Invalid Code")


def test_dates_reject_datetime_values() -> None:
    with pytest.raises(SpecializedCommodityValidationError):
        ElectricityQuantityStep(
            cast(date, datetime(2027, 1, 1)),
            Decimal("1"),
            _identity(12),
        )


def test_values_are_frozen_and_slotted() -> None:
    value = ElectricitySettlementPeriodCode("all-hours")
    with pytest.raises(FrozenInstanceError):
        value.__setattr__("value", "peak")
    assert not hasattr(value, "__dict__")


def test_static_terms_expose_no_operational_methods() -> None:
    prohibited = {
        "execute",
        "submit",
        "settle",
        "price",
        "calculate",
        "observe",
        "dispatch",
        "deliver",
        "mutate_registry",
        "fetch",
    }
    for contract_type in (
        ElectricityContractTerms,
        FreightTerms,
        WeatherIndexTerms,
        EnvironmentalProductTerms,
    ):
        assert prohibited.isdisjoint(contract_type.__dict__)
