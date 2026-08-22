from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.commodity_contract_delivery_semantics import (
    CommodityEvidenceRef,
    CommodityTermsId,
)
from qore.infrastructure.specialized_commodity_semantics import (
    ElectricityDeliveryProfile,
    ElectricityLoadType,
    ElectricitySettlementPeriodCode,
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


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(f"00000000-0000-0000-0000-{value:012d}"))


def _terms_id(value: int) -> CommodityTermsId:
    return CommodityTermsId(UUID(f"00000000-0000-0000-0000-{value:012d}"))


def _evidence(value: int) -> CommodityEvidenceRef:
    return CommodityEvidenceRef(UUID(f"00000000-0000-0000-0000-{value:012d}"))


def _freight(start_date: date, end_date: date) -> FreightTerms:
    return FreightTerms(
        terms_id=_terms_id(40),
        instrument_identity_id=_identity(41),
        route_identity_id=_identity(42),
        kind=FreightTransactionKind.WET_VOYAGE_CHARTER,
        calculation_start_date=start_date,
        calculation_end_date=end_date,
        evidence_ref=_evidence(43),
        worldscale_points=FreightWorldscalePoints(Decimal("100")),
    )


def _weather(start_date: date, end_date: date) -> WeatherIndexTerms:
    return WeatherIndexTerms(
        terms_id=_terms_id(50),
        instrument_identity_id=_identity(51),
        station_identity_id=_identity(52),
        index_code=WeatherIndexCode("hdd"),
        calculation_start_date=start_date,
        calculation_end_date=end_date,
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


def test_all_electricity_load_types_are_distinct_logical_material() -> None:
    profiles = tuple(
        ElectricityDeliveryProfile(
            load_type=load_type,
            settlement_periods=(ElectricitySettlementPeriodCode("all-hours"),),
        )
        for load_type in (
            ElectricityLoadType.BASE,
            ElectricityLoadType.PEAK,
            ElectricityLoadType.OFF_PEAK,
            ElectricityLoadType.BLOCK_HOURS,
            ElectricityLoadType.CUSTOM,
        )
    )

    assert tuple(profile.load_type.value for profile in profiles) == (
        "base",
        "peak",
        "off-peak",
        "block-hours",
        "custom",
    )
    assert len({profile.logical_values() for profile in profiles}) == 5


def test_freight_calculation_start_date_rejects_datetime() -> None:
    invalid = cast(date, datetime(2027, 2, 15, 12, 0))
    with pytest.raises(SpecializedCommodityValidationError, match="must be date"):
        _freight(invalid, date(2027, 2, 28))


def test_freight_calculation_end_date_rejects_datetime() -> None:
    invalid = cast(date, datetime(2027, 2, 15, 12, 0))
    with pytest.raises(SpecializedCommodityValidationError, match="must be date"):
        _freight(date(2027, 2, 1), invalid)


def test_weather_calculation_start_date_rejects_datetime() -> None:
    invalid = cast(date, datetime(2027, 1, 15, 12, 0))
    with pytest.raises(SpecializedCommodityValidationError, match="must be date"):
        _weather(invalid, date(2027, 1, 31))


def test_weather_calculation_end_date_rejects_datetime() -> None:
    invalid = cast(date, datetime(2027, 1, 15, 12, 0))
    with pytest.raises(SpecializedCommodityValidationError, match="must be date"):
        _weather(date(2027, 1, 1), invalid)
