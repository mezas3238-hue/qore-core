from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.commodity_contract_delivery_semantics import (
    CommodityEvidenceRef,
    CommodityPhysicalDeliveryTerms,
    CommodityReferenceTerms,
    CommodityTermsId,
)
from qore.infrastructure.derivative_contract_semantics import DerivativeSettlementStyle
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class SpecializedCommoditySemanticsError(InfrastructureError):
    """Base error for bounded specialized commodity static semantics."""

    __slots__ = ()


class SpecializedCommodityValidationError(SpecializedCommoditySemanticsError):
    """Violation of a specialized commodity static semantic invariant."""

    __slots__ = ()


def _identity(value: EconomicIdentityId, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise SpecializedCommodityValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _date(value: date, field_name: str) -> None:
    if type(value) is not date:
        raise SpecializedCommodityValidationError(f"{field_name} must be date")


def _code(value: str, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise SpecializedCommodityValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _finite(value: Decimal, field_name: str, *, non_negative: bool = False) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise SpecializedCommodityValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if non_negative and value < 0:
        raise SpecializedCommodityValidationError(
            f"{field_name} must be non-negative"
        )


def _positive(value: Decimal, field_name: str) -> None:
    _finite(value, field_name)
    if value <= 0:
        raise SpecializedCommodityValidationError(f"{field_name} must be positive")


def _decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def _year(value: int, field_name: str) -> None:
    if type(value) is not int or not 1 <= value <= 9999:
        raise SpecializedCommodityValidationError(
            f"{field_name} must be an int in 1..9999"
        )


class ElectricityLoadType(StrEnum):
    BASE = "base"
    PEAK = "peak"
    OFF_PEAK = "off-peak"
    BLOCK_HOURS = "block-hours"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class ElectricitySettlementPeriodCode:
    """Governed delivery-period/profile code; no calendar resolution authority."""

    value: str

    def __post_init__(self) -> None:
        _code(self.value, "electricity settlement-period code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ElectricityQuantityStep:
    """Contractual shaped quantity effective from a date; no dispatch authority."""

    effective_date: date
    quantity: Decimal
    unit_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _date(self.effective_date, "electricity quantity effective_date")
        _positive(self.quantity, "electricity quantity")
        _identity(self.unit_identity_id, "electricity quantity unit identity")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.effective_date.isoformat(),
            _decimal(self.quantity),
            self.unit_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ElectricityDeliveryProfile:
    load_type: ElectricityLoadType
    settlement_periods: tuple[ElectricitySettlementPeriodCode, ...]
    quantity_steps: tuple[ElectricityQuantityStep, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.load_type, ElectricityLoadType):
            raise SpecializedCommodityValidationError(
                "electricity load_type must be ElectricityLoadType"
            )
        if type(self.settlement_periods) is not tuple or not self.settlement_periods:
            raise SpecializedCommodityValidationError(
                "electricity settlement_periods must be a non-empty immutable tuple"
            )
        for period in self.settlement_periods:
            if not isinstance(period, ElectricitySettlementPeriodCode):
                raise SpecializedCommodityValidationError(
                    "electricity settlement_periods must contain "
                    "ElectricitySettlementPeriodCode"
                )
        period_values = tuple(period.value for period in self.settlement_periods)
        if len(set(period_values)) != len(period_values):
            raise SpecializedCommodityValidationError(
                "electricity settlement-period codes must be unique"
            )
        object.__setattr__(
            self,
            "settlement_periods",
            tuple(sorted(self.settlement_periods, key=lambda period: period.value)),
        )
        if type(self.quantity_steps) is not tuple:
            raise SpecializedCommodityValidationError(
                "electricity quantity_steps must be an immutable tuple"
            )
        for step in self.quantity_steps:
            if not isinstance(step, ElectricityQuantityStep):
                raise SpecializedCommodityValidationError(
                    "electricity quantity_steps must contain ElectricityQuantityStep"
                )
        dates = tuple(step.effective_date for step in self.quantity_steps)
        if len(set(dates)) != len(dates):
            raise SpecializedCommodityValidationError(
                "electricity quantity-step dates must be unique"
            )
        if self.quantity_steps:
            units = {step.unit_identity_id for step in self.quantity_steps}
            if len(units) != 1:
                raise SpecializedCommodityValidationError(
                    "electricity quantity steps must use one unit identity"
                )
            object.__setattr__(
                self,
                "quantity_steps",
                tuple(sorted(self.quantity_steps, key=lambda step: step.effective_date)),
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.load_type.value,
            tuple(period.logical_values() for period in self.settlement_periods),
            tuple(step.logical_values() for step in self.quantity_steps),
        )


@dataclass(frozen=True, slots=True)
class ElectricityContractTerms:
    terms_id: CommodityTermsId
    commodity_reference: CommodityReferenceTerms
    physical_delivery: CommodityPhysicalDeliveryTerms
    delivery_profile: ElectricityDeliveryProfile
    evidence_ref: CommodityEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CommodityTermsId):
            raise SpecializedCommodityValidationError(
                "electricity terms_id must be CommodityTermsId"
            )
        if not isinstance(self.commodity_reference, CommodityReferenceTerms):
            raise SpecializedCommodityValidationError(
                "electricity commodity_reference must be CommodityReferenceTerms"
            )
        if not isinstance(self.physical_delivery, CommodityPhysicalDeliveryTerms):
            raise SpecializedCommodityValidationError(
                "electricity physical_delivery must be CommodityPhysicalDeliveryTerms"
            )
        if not isinstance(self.delivery_profile, ElectricityDeliveryProfile):
            raise SpecializedCommodityValidationError(
                "electricity delivery_profile must be ElectricityDeliveryProfile"
            )
        if self.delivery_profile.quantity_steps:
            unit = self.delivery_profile.quantity_steps[0].unit_identity_id
            if unit != self.commodity_reference.measurement_unit_identity_id:
                raise SpecializedCommodityValidationError(
                    "electricity shaped quantity unit must match commodity measurement unit"
                )
            for step in self.delivery_profile.quantity_steps:
                if not any(
                    alternative.window.start_date
                    <= step.effective_date
                    <= alternative.window.end_date
                    for alternative in self.physical_delivery.alternatives
                ):
                    raise SpecializedCommodityValidationError(
                        "electricity quantity-step dates must fall within delivery alternatives"
                    )
        if not isinstance(self.evidence_ref, CommodityEvidenceRef):
            raise SpecializedCommodityValidationError(
                "electricity evidence_ref must be CommodityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "electricity-contract",
            self.terms_id.logical_values(),
            self.commodity_reference.logical_values(),
            self.physical_delivery.logical_values(),
            self.delivery_profile.logical_values(),
            self.evidence_ref.logical_values(),
        )


class FreightTransactionKind(StrEnum):
    WET_VOYAGE_CHARTER = "wet-voyage-charter"
    DRY_VOYAGE_CHARTER = "dry-voyage-charter"
    TIME_CHARTER = "time-charter"


@dataclass(frozen=True, slots=True)
class FreightWorldscalePoints:
    value: Decimal

    def __post_init__(self) -> None:
        _finite(self.value, "freight Worldscale points", non_negative=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class FreightContractRate:
    value: Decimal
    quote_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _finite(self.value, "freight contract rate", non_negative=True)
        _identity(self.quote_identity_id, "freight contract-rate quote identity")

    def logical_values(self) -> tuple[object, ...]:
        return (_decimal(self.value), self.quote_identity_id.logical_values())


@dataclass(frozen=True, slots=True)
class FreightTerms:
    terms_id: CommodityTermsId
    instrument_identity_id: EconomicIdentityId
    route_identity_id: EconomicIdentityId
    kind: FreightTransactionKind
    calculation_start_date: date
    calculation_end_date: date
    evidence_ref: CommodityEvidenceRef
    worldscale_points: FreightWorldscalePoints | None = None
    contract_rate: FreightContractRate | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CommodityTermsId):
            raise SpecializedCommodityValidationError(
                "freight terms_id must be CommodityTermsId"
            )
        _identity(self.instrument_identity_id, "freight instrument identity")
        _identity(self.route_identity_id, "freight route identity")
        if self.instrument_identity_id == self.route_identity_id:
            raise SpecializedCommodityValidationError(
                "freight instrument and route identities must differ"
            )
        if not isinstance(self.kind, FreightTransactionKind):
            raise SpecializedCommodityValidationError(
                "freight kind must be FreightTransactionKind"
            )
        _date(self.calculation_start_date, "freight calculation_start_date")
        _date(self.calculation_end_date, "freight calculation_end_date")
        if self.calculation_end_date < self.calculation_start_date:
            raise SpecializedCommodityValidationError(
                "freight calculation_end_date must not precede calculation_start_date"
            )
        if self.worldscale_points is not None and not isinstance(
            self.worldscale_points, FreightWorldscalePoints
        ):
            raise SpecializedCommodityValidationError(
                "freight worldscale_points has invalid type"
            )
        if self.contract_rate is not None and not isinstance(
            self.contract_rate, FreightContractRate
        ):
            raise SpecializedCommodityValidationError(
                "freight contract_rate has invalid type"
            )
        if self.kind is FreightTransactionKind.WET_VOYAGE_CHARTER:
            if self.worldscale_points is None or self.contract_rate is not None:
                raise SpecializedCommodityValidationError(
                    "wet voyage charter requires Worldscale points only"
                )
        elif self.contract_rate is None or self.worldscale_points is not None:
            raise SpecializedCommodityValidationError(
                "dry voyage/time charter requires contract rate only"
            )
        if not isinstance(self.evidence_ref, CommodityEvidenceRef):
            raise SpecializedCommodityValidationError(
                "freight evidence_ref must be CommodityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "freight-contract",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.route_identity_id.logical_values(),
            self.kind.value,
            self.calculation_start_date.isoformat(),
            self.calculation_end_date.isoformat(),
            self.worldscale_points.logical_values()
            if self.worldscale_points is not None
            else None,
            self.contract_rate.logical_values() if self.contract_rate is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class WeatherIndexCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "weather index code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class WeatherLevelUnitCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "weather level unit code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class WeatherSettlementLevelCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "weather settlement-level code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class WeatherReferenceLevel:
    value: Decimal
    unit: WeatherLevelUnitCode

    def __post_init__(self) -> None:
        _finite(self.value, "weather reference level")
        if not isinstance(self.unit, WeatherLevelUnitCode):
            raise SpecializedCommodityValidationError(
                "weather reference-level unit must be WeatherLevelUnitCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (_decimal(self.value), self.unit.logical_values())


@dataclass(frozen=True, slots=True)
class WeatherNotionalPerIndexUnit:
    value: Decimal
    currency_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _positive(self.value, "weather notional per index unit")
        _identity(self.currency_identity_id, "weather notional currency identity")

    def logical_values(self) -> tuple[object, ...]:
        return (_decimal(self.value), self.currency_identity_id.logical_values())


@dataclass(frozen=True, slots=True)
class WeatherIndexTerms:
    terms_id: CommodityTermsId
    instrument_identity_id: EconomicIdentityId
    station_identity_id: EconomicIdentityId
    index_code: WeatherIndexCode
    calculation_start_date: date
    calculation_end_date: date
    reference_level: WeatherReferenceLevel
    settlement_level: WeatherSettlementLevelCode
    notional_per_index_unit: WeatherNotionalPerIndexUnit
    evidence_ref: CommodityEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CommodityTermsId):
            raise SpecializedCommodityValidationError(
                "weather terms_id must be CommodityTermsId"
            )
        _identity(self.instrument_identity_id, "weather instrument identity")
        _identity(self.station_identity_id, "weather station identity")
        if self.instrument_identity_id == self.station_identity_id:
            raise SpecializedCommodityValidationError(
                "weather instrument and station identities must differ"
            )
        if not isinstance(self.index_code, WeatherIndexCode):
            raise SpecializedCommodityValidationError(
                "weather index_code must be WeatherIndexCode"
            )
        _date(self.calculation_start_date, "weather calculation_start_date")
        _date(self.calculation_end_date, "weather calculation_end_date")
        if self.calculation_end_date < self.calculation_start_date:
            raise SpecializedCommodityValidationError(
                "weather calculation_end_date must not precede calculation_start_date"
            )
        if not isinstance(self.reference_level, WeatherReferenceLevel):
            raise SpecializedCommodityValidationError(
                "weather reference_level must be WeatherReferenceLevel"
            )
        if not isinstance(self.settlement_level, WeatherSettlementLevelCode):
            raise SpecializedCommodityValidationError(
                "weather settlement_level must be WeatherSettlementLevelCode"
            )
        if not isinstance(self.notional_per_index_unit, WeatherNotionalPerIndexUnit):
            raise SpecializedCommodityValidationError(
                "weather notional_per_index_unit has invalid type"
            )
        if not isinstance(self.evidence_ref, CommodityEvidenceRef):
            raise SpecializedCommodityValidationError(
                "weather evidence_ref must be CommodityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "weather-index-contract",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.station_identity_id.logical_values(),
            self.index_code.logical_values(),
            self.calculation_start_date.isoformat(),
            self.calculation_end_date.isoformat(),
            self.reference_level.logical_values(),
            self.settlement_level.logical_values(),
            self.notional_per_index_unit.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class EnvironmentalProductTypeCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "environmental product-type code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EnvironmentalApplicableLawCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "environmental applicable-law code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EnvironmentalTrackingSystemCode:
    value: str

    def __post_init__(self) -> None:
        _code(self.value, "environmental tracking-system code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EnvironmentalCompliancePeriod:
    start_year: int
    end_year: int

    def __post_init__(self) -> None:
        _year(self.start_year, "environmental compliance start_year")
        _year(self.end_year, "environmental compliance end_year")
        if self.end_year < self.start_year:
            raise SpecializedCommodityValidationError(
                "environmental compliance end_year must not precede start_year"
            )

    def logical_values(self) -> tuple[int, int]:
        return (self.start_year, self.end_year)


class EnvironmentalVintageEligibilityKind(StrEnum):
    EXACT_SET = "exact-set"
    CONTRACT_YEAR_AND_PRIOR = "contract-year-and-prior"


@dataclass(frozen=True, slots=True)
class EnvironmentalVintageEligibility:
    kind: EnvironmentalVintageEligibilityKind
    exact_vintages: tuple[int, ...] = ()
    contract_year: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EnvironmentalVintageEligibilityKind):
            raise SpecializedCommodityValidationError(
                "environmental vintage kind has invalid type"
            )
        if type(self.exact_vintages) is not tuple:
            raise SpecializedCommodityValidationError(
                "environmental exact_vintages must be an immutable tuple"
            )
        for vintage in self.exact_vintages:
            _year(vintage, "environmental exact vintage")
        if len(set(self.exact_vintages)) != len(self.exact_vintages):
            raise SpecializedCommodityValidationError(
                "environmental exact vintages must be unique"
            )
        if self.kind is EnvironmentalVintageEligibilityKind.EXACT_SET:
            if not self.exact_vintages or self.contract_year is not None:
                raise SpecializedCommodityValidationError(
                    "exact-set eligibility requires vintages and forbids contract_year"
                )
            object.__setattr__(self, "exact_vintages", tuple(sorted(self.exact_vintages)))
        else:
            if self.exact_vintages or self.contract_year is None:
                raise SpecializedCommodityValidationError(
                    "contract-year-and-prior requires contract_year only"
                )
            _year(self.contract_year, "environmental contract year")

    def logical_values(self) -> tuple[object, ...]:
        return (self.kind.value, self.exact_vintages, self.contract_year)


@dataclass(frozen=True, slots=True)
class EnvironmentalProductTerms:
    terms_id: CommodityTermsId
    commodity_reference: CommodityReferenceTerms
    settlement_style: DerivativeSettlementStyle
    product_type: EnvironmentalProductTypeCode
    vintage_eligibility: EnvironmentalVintageEligibility
    evidence_ref: CommodityEvidenceRef
    physical_delivery: CommodityPhysicalDeliveryTerms | None = None
    compliance_period: EnvironmentalCompliancePeriod | None = None
    applicable_law: EnvironmentalApplicableLawCode | None = None
    tracking_system: EnvironmentalTrackingSystemCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CommodityTermsId):
            raise SpecializedCommodityValidationError(
                "environmental terms_id must be CommodityTermsId"
            )
        if not isinstance(self.commodity_reference, CommodityReferenceTerms):
            raise SpecializedCommodityValidationError(
                "environmental commodity_reference must be CommodityReferenceTerms"
            )
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise SpecializedCommodityValidationError(
                "environmental settlement_style must be DerivativeSettlementStyle"
            )
        if not isinstance(self.product_type, EnvironmentalProductTypeCode):
            raise SpecializedCommodityValidationError(
                "environmental product_type has invalid type"
            )
        if not isinstance(self.vintage_eligibility, EnvironmentalVintageEligibility):
            raise SpecializedCommodityValidationError(
                "environmental vintage_eligibility has invalid type"
            )
        if self.physical_delivery is not None and not isinstance(
            self.physical_delivery, CommodityPhysicalDeliveryTerms
        ):
            raise SpecializedCommodityValidationError(
                "environmental physical_delivery has invalid type"
            )
        if self.settlement_style is DerivativeSettlementStyle.PHYSICAL:
            if self.physical_delivery is None:
                raise SpecializedCommodityValidationError(
                    "physical environmental product requires physical delivery terms"
                )
        elif self.physical_delivery is not None:
            raise SpecializedCommodityValidationError(
                "cash environmental product must not carry physical delivery terms"
            )
        if self.compliance_period is not None and not isinstance(
            self.compliance_period, EnvironmentalCompliancePeriod
        ):
            raise SpecializedCommodityValidationError(
                "environmental compliance_period has invalid type"
            )
        if self.applicable_law is not None and not isinstance(
            self.applicable_law, EnvironmentalApplicableLawCode
        ):
            raise SpecializedCommodityValidationError(
                "environmental applicable_law has invalid type"
            )
        if self.tracking_system is not None and not isinstance(
            self.tracking_system, EnvironmentalTrackingSystemCode
        ):
            raise SpecializedCommodityValidationError(
                "environmental tracking_system has invalid type"
            )
        if not isinstance(self.evidence_ref, CommodityEvidenceRef):
            raise SpecializedCommodityValidationError(
                "environmental evidence_ref must be CommodityEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "environmental-product",
            self.terms_id.logical_values(),
            self.commodity_reference.logical_values(),
            self.settlement_style.value,
            self.product_type.logical_values(),
            self.vintage_eligibility.logical_values(),
            self.physical_delivery.logical_values()
            if self.physical_delivery is not None
            else None,
            self.compliance_period.logical_values()
            if self.compliance_period is not None
            else None,
            self.applicable_law.logical_values()
            if self.applicable_law is not None
            else None,
            self.tracking_system.logical_values()
            if self.tracking_system is not None
            else None,
            self.evidence_ref.logical_values(),
        )
