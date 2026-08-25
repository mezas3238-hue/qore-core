from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeNotional,
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
from qore.infrastructure.fixed_income_economics import YieldConvention
from qore.infrastructure.rate_term_structure import RateCurveConvention
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
from qore.kernel.errors import InfrastructureError


class WarrantConvertibleQualificationError(InfrastructureError):
    """Base error for warrant/convertible structural qualification semantics."""

    __slots__ = ()


class WarrantConvertibleQualificationValidationError(
    WarrantConvertibleQualificationError
):
    """Violation of one warrant/convertible qualification invariant."""

    __slots__ = ()


def _fail(message: str) -> None:
    raise WarrantConvertibleQualificationValidationError(message)


def _require_uuid(value: object, *, field_name: str) -> UUID:
    if type(value) is not UUID:
        _fail(f"{field_name} must be exact UUID")
    return value


def _require_date(value: object, *, field_name: str) -> date:
    if type(value) is not date:
        _fail(f"{field_name} must be exact date")
    return value


def _require_code(value: object, *, field_name: str) -> str:
    if (
        type(value) is not str
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        _fail(f"{field_name} must use exact canonical lowercase code syntax")
    return value


def _require_decimal(
    value: object,
    *,
    field_name: str,
    positive: bool = False,
) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{field_name} must be an exact finite Decimal")
    if positive and value <= 0:
        _fail(f"{field_name} must be positive")
    return value


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"

    decimal_tuple = normalized.as_tuple()
    if not isinstance(decimal_tuple.exponent, int):
        _fail("finite Decimal must expose an integer exponent")
    exponent = decimal_tuple.exponent
    digits = "".join(str(digit) for digit in decimal_tuple.digits)
    sign = "-" if decimal_tuple.sign else ""

    if exponent == 0:
        return sign + digits

    scientific_exponent = exponent + len(digits) - 1
    mantissa = digits[0] if len(digits) == 1 else digits[0] + "." + digits[1:]
    compact = f"{sign}{mantissa}e{scientific_exponent:+d}"

    if exponent >= 0:
        fixed_length = len(sign) + len(digits) + exponent
    else:
        point = len(digits) + exponent
        fixed_length = (
            len(sign) + len(digits) + 1
            if point > 0
            else len(sign) + 2 + (-point) + len(digits)
        )

    if fixed_length > len(compact) + 1:
        return compact

    if exponent >= 0:
        fixed = digits + ("0" * exponent)
    else:
        point = len(digits) + exponent
        fixed = (
            digits[:point] + "." + digits[point:]
            if point > 0
            else "0." + ("0" * (-point)) + digits
        )
    return sign + fixed


def _require_identity_id(value: object, *, field_name: str) -> EconomicIdentityId:
    if type(value) is not EconomicIdentityId:
        _fail(f"{field_name} must be exact EconomicIdentityId")
    _require_uuid(value.value, field_name=f"{field_name} value")
    return value


def _identity_values(value: EconomicIdentityId) -> tuple[str, ...]:
    _require_identity_id(value, field_name="economic identity id")
    return (str(value.value),)


def _require_economic_identity(
    value: object,
    *,
    field_name: str,
    required_family: str | None = None,
) -> EconomicIdentity:
    if type(value) is not EconomicIdentity:
        _fail(f"{field_name} must be exact EconomicIdentity")
    _require_identity_id(value.identity_id, field_name=f"{field_name} identity_id")
    if type(value.kind) is not EconomicIdentityKind:
        _fail(f"{field_name} kind must be exact EconomicIdentityKind")
    if type(value.family) is not IdentityFamilyCode:
        _fail(f"{field_name} family must be exact IdentityFamilyCode")
    family_code = _require_code(
        value.family.value,
        field_name=f"{field_name} family value",
    )
    if required_family is not None and family_code != required_family:
        _fail(f"{field_name} family must be {required_family}")
    if type(value.construction) is not IdentityConstructionKind:
        _fail(f"{field_name} construction must be exact IdentityConstructionKind")
    if type(value.evidence_ref) is not IdentityEvidenceRef:
        _fail(f"{field_name} evidence_ref must be exact IdentityEvidenceRef")
    _require_uuid(
        value.evidence_ref.value,
        field_name=f"{field_name} evidence_ref value",
    )
    if (
        value.construction is IdentityConstructionKind.CONTINUOUS_REFERENCE
        and value.kind is not EconomicIdentityKind.REFERENCE_OBJECT
    ):
        _fail("continuous-reference identity must be a reference object")
    return value


def _economic_identity_values(value: EconomicIdentity) -> tuple[object, ...]:
    _require_economic_identity(value, field_name="economic identity")
    return (
        _identity_values(value.identity_id),
        value.kind.value,
        (value.family.value,),
        value.construction.value,
        (str(value.evidence_ref.value),),
    )


def _require_derivative_terms_id(value: object) -> DerivativeTermsId:
    if type(value) is not DerivativeTermsId:
        _fail("option terms_id must be exact DerivativeTermsId")
    _require_uuid(value.value, field_name="option terms_id value")
    return value


def _require_derivative_evidence(value: object) -> DerivativeEvidenceRef:
    if type(value) is not DerivativeEvidenceRef:
        _fail("option evidence_ref must be exact DerivativeEvidenceRef")
    _require_uuid(value.value, field_name="option evidence_ref value")
    return value


def _require_price_quote_basis(value: object) -> DerivativePriceQuoteBasisCode:
    if type(value) is not DerivativePriceQuoteBasisCode:
        _fail("option strike price quote basis must be exact DerivativePriceQuoteBasisCode")
    _require_code(value.value, field_name="option strike price quote basis value")
    return value


def _require_strike(value: object) -> DerivativeStrike:
    if type(value) is not DerivativeStrike:
        _fail("option strike must be exact DerivativeStrike")
    _require_decimal(value.value, field_name="option strike value")
    if type(value.basis) is not DerivativeStrikeBasis:
        _fail("option strike basis must be exact DerivativeStrikeBasis")
    if value.quote_identity_id is not None:
        _require_identity_id(
            value.quote_identity_id,
            field_name="option strike quote identity",
        )
    if value.price_quote_basis is not None:
        _require_price_quote_basis(value.price_quote_basis)
    if value.convention is not None:
        if type(value.convention) not in (RateCurveConvention, YieldConvention):
            _fail("option strike convention must use an exact retained convention type")
        value.convention.__post_init__()

    if value.basis is DerivativeStrikeBasis.PRICE:
        if (
            value.quote_identity_id is None
            or value.price_quote_basis is None
            or value.convention is not None
        ):
            _fail("price strike requires quote identity, price quote basis, and no convention")
    elif value.basis is DerivativeStrikeBasis.RATE:
        if (
            value.quote_identity_id is not None
            or value.price_quote_basis is not None
            or type(value.convention) is not RateCurveConvention
        ):
            _fail("rate strike requires exact RateCurveConvention only")
    elif value.basis is DerivativeStrikeBasis.YIELD:
        if (
            value.quote_identity_id is not None
            or value.price_quote_basis is not None
            or type(value.convention) is not YieldConvention
        ):
            _fail("yield strike requires exact YieldConvention only")
    elif (
        value.quote_identity_id is not None
        or value.price_quote_basis is not None
        or value.convention is not None
    ):
        _fail("spread/level strike must not carry price/quote/convention material")
    return value


def _strike_values(value: DerivativeStrike) -> tuple[object, ...]:
    _require_strike(value)
    if type(value.convention) is RateCurveConvention:
        convention_values: tuple[object, ...] | None = value.convention.logical_values()
    elif type(value.convention) is YieldConvention:
        convention_values = ("yield-convention", value.convention.logical_values())
    else:
        convention_values = None
    return (
        _canonical_decimal(value.value),
        value.basis.value,
        _identity_values(value.quote_identity_id)
        if value.quote_identity_id is not None
        else None,
        (value.price_quote_basis.value,)
        if value.price_quote_basis is not None
        else None,
        convention_values,
    )


def _require_exercise(value: object) -> OptionExerciseTerms:
    if type(value) is not OptionExerciseTerms:
        _fail("option exercise must be exact OptionExerciseTerms")
    if type(value.style) is not OptionExerciseStyle:
        _fail("option exercise style must be exact OptionExerciseStyle")
    if value.american_start_date is not None:
        _require_date(
            value.american_start_date,
            field_name="option American exercise start date",
        )
    if type(value.bermudan_dates) is not tuple:
        _fail("option Bermudan dates must be exact tuple")
    for exercise_date in value.bermudan_dates:
        _require_date(exercise_date, field_name="option Bermudan exercise date")

    if value.style is OptionExerciseStyle.AMERICAN:
        if value.american_start_date is None or value.bermudan_dates:
            _fail("American exercise requires only explicit start date")
    elif value.style is OptionExerciseStyle.BERMUDAN:
        if value.american_start_date is not None or not value.bermudan_dates:
            _fail("Bermudan exercise requires only explicit Bermudan dates")
        if len(set(value.bermudan_dates)) != len(value.bermudan_dates):
            _fail("Bermudan exercise dates must be unique")
        if value.bermudan_dates != tuple(sorted(value.bermudan_dates)):
            _fail("Bermudan exercise dates must remain canonically ordered")
    elif value.american_start_date is not None or value.bermudan_dates:
        _fail("European exercise must not carry other exercise-date material")
    return value


def _exercise_values(value: OptionExerciseTerms) -> tuple[object, ...]:
    _require_exercise(value)
    return (
        value.style.value,
        value.american_start_date.isoformat()
        if value.american_start_date is not None
        else None,
        tuple(item.isoformat() for item in value.bermudan_dates),
    )


def _require_multiplier(value: object) -> DerivativeContractMultiplier:
    if type(value) is not DerivativeContractMultiplier:
        _fail("option multiplier must be exact DerivativeContractMultiplier")
    _require_decimal(value.value, field_name="option multiplier value", positive=True)
    _require_identity_id(
        value.unit_identity_id,
        field_name="option multiplier unit identity",
    )
    return value


def _multiplier_values(value: DerivativeContractMultiplier) -> tuple[object, ...]:
    _require_multiplier(value)
    return (_canonical_decimal(value.value), _identity_values(value.unit_identity_id))


def _require_notional(value: object) -> DerivativeNotional:
    if type(value) is not DerivativeNotional:
        _fail("option notional must be exact DerivativeNotional")
    _require_decimal(value.value, field_name="option notional value", positive=True)
    _require_identity_id(
        value.unit_identity_id,
        field_name="option notional unit identity",
    )
    return value


def _notional_values(value: DerivativeNotional) -> tuple[object, ...]:
    _require_notional(value)
    return (_canonical_decimal(value.value), _identity_values(value.unit_identity_id))


def _require_option_terms(value: object) -> OptionContractTerms:
    if type(value) is not OptionContractTerms:
        _fail("warrant option_terms must be exact OptionContractTerms")
    _require_derivative_terms_id(value.terms_id)
    _require_identity_id(value.instrument_identity_id, field_name="option instrument identity")
    _require_identity_id(value.underlying_identity_id, field_name="option underlying identity")
    _require_identity_id(value.settlement_identity_id, field_name="option settlement identity")
    if value.instrument_identity_id == value.underlying_identity_id:
        _fail("option instrument and underlying identities must differ")
    if value.instrument_identity_id == value.settlement_identity_id:
        _fail("option instrument and settlement identities must differ")
    if type(value.right) is not OptionRight:
        _fail("option right must be exact OptionRight")
    _require_strike(value.strike)
    _require_date(value.expiry_date, field_name="option expiry_date")
    _require_exercise(value.exercise)
    if (
        value.exercise.american_start_date is not None
        and value.exercise.american_start_date > value.expiry_date
    ):
        _fail("American exercise start date must not be after option expiry")
    if any(item > value.expiry_date for item in value.exercise.bermudan_dates):
        _fail("Bermudan exercise date must not be after option expiry")
    if type(value.settlement_style) is not DerivativeSettlementStyle:
        _fail("option settlement style must be exact DerivativeSettlementStyle")
    _require_derivative_evidence(value.evidence_ref)
    if value.multiplier is not None:
        _require_multiplier(value.multiplier)
    if value.notional is not None:
        _require_notional(value.notional)
    if value.multiplier is None and value.notional is None:
        _fail("option requires multiplier and/or notional")
    return value


def _option_values(value: OptionContractTerms) -> tuple[object, ...]:
    _require_option_terms(value)
    return (
        "option",
        (str(value.terms_id.value),),
        _identity_values(value.instrument_identity_id),
        _identity_values(value.underlying_identity_id),
        _identity_values(value.settlement_identity_id),
        value.right.value,
        _strike_values(value.strike),
        value.expiry_date.isoformat(),
        _exercise_values(value.exercise),
        value.settlement_style.value,
        (str(value.evidence_ref.value),),
        _multiplier_values(value.multiplier) if value.multiplier is not None else None,
        _notional_values(value.notional) if value.notional is not None else None,
    )


def _require_structured_feature_id(value: object) -> StructuredFeatureId:
    if type(value) is not StructuredFeatureId:
        _fail("conversion feature_id must be exact StructuredFeatureId")
    _require_uuid(value.value, field_name="conversion feature_id value")
    return value


def _require_structured_evidence(value: object) -> StructuredEvidenceRef:
    if type(value) is not StructuredEvidenceRef:
        _fail("conversion evidence_ref must be exact StructuredEvidenceRef")
    _require_uuid(value.value, field_name="conversion evidence_ref value")
    return value


def _require_positive_ratio(value: object) -> StructuredPositiveRatio:
    if type(value) is not StructuredPositiveRatio:
        _fail("conversion ratio must be exact StructuredPositiveRatio")
    _require_decimal(value.value, field_name="conversion ratio value", positive=True)
    return value


def _require_contract_level(value: object) -> StructuredContractLevel:
    if type(value) is not StructuredContractLevel:
        _fail("conversion level must be exact StructuredContractLevel")
    _require_decimal(value.value, field_name="conversion level value")
    if type(value.kind) is not StructuredContractLevelKind:
        _fail("conversion level kind must be exact StructuredContractLevelKind")
    _require_identity_id(
        value.reference_identity_id,
        field_name="conversion level reference identity",
    )
    if type(value.unit) is not StructuredLevelUnitCode:
        _fail("conversion level unit must be exact StructuredLevelUnitCode")
    _require_code(value.unit.value, field_name="conversion level unit value")
    return value


def _contract_level_values(value: StructuredContractLevel) -> tuple[object, ...]:
    _require_contract_level(value)
    return (
        _canonical_decimal(value.value),
        value.kind.value,
        _identity_values(value.reference_identity_id),
        (value.unit.value,),
    )


def _require_conversion_feature(value: object) -> StructuredConversionFeature:
    if type(value) is not StructuredConversionFeature:
        _fail("conversion_feature must be exact StructuredConversionFeature")
    _require_structured_feature_id(value.feature_id)
    _require_identity_id(value.target_identity_id, field_name="conversion target identity")
    _require_positive_ratio(value.units_per_source_unit)
    _require_structured_evidence(value.evidence_ref)
    if value.conversion_level is not None:
        _require_contract_level(value.conversion_level)
    return value


def _conversion_feature_values(value: StructuredConversionFeature) -> tuple[object, ...]:
    _require_conversion_feature(value)
    return (
        "conversion",
        (str(value.feature_id.value),),
        _identity_values(value.target_identity_id),
        (_canonical_decimal(value.units_per_source_unit.value),),
        _contract_level_values(value.conversion_level)
        if value.conversion_level is not None
        else None,
        (str(value.evidence_ref.value),),
    )


@dataclass(frozen=True, slots=True)
class WarrantConvertibleQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(value=self.value, field_name="qualification id")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class WarrantConvertibleEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(value=self.value, field_name="qualification evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


class WarrantConvertibleQualificationKind(StrEnum):
    WARRANT = "warrant"
    CONVERTIBLE = "convertible"


@dataclass(frozen=True, slots=True)
class EquityWarrantQualificationTerms:
    warrant_identity: EconomicIdentity
    target_equity_identity: EconomicIdentity
    option_terms: OptionContractTerms

    def __post_init__(self) -> None:
        warrant = _require_economic_identity(
            self.warrant_identity,
            field_name="warrant identity",
        )
        target = _require_economic_identity(
            self.target_equity_identity,
            field_name="warrant target equity identity",
            required_family="equities",
        )
        option = _require_option_terms(self.option_terms)
        if warrant.identity_id == target.identity_id:
            _fail("warrant and target equity identities must differ")
        if option.instrument_identity_id != warrant.identity_id:
            _fail("option instrument identity must match warrant identity")
        if option.underlying_identity_id != target.identity_id:
            _fail("option underlying identity must match target equity identity")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "warrant",
            _economic_identity_values(self.warrant_identity),
            _economic_identity_values(self.target_equity_identity),
            _option_values(self.option_terms),
        )


@dataclass(frozen=True, slots=True)
class ConvertibleQualificationTerms:
    convertible_identity: EconomicIdentity
    target_equity_identity: EconomicIdentity
    conversion_feature: StructuredConversionFeature
    credit_leg_identity: EconomicIdentity | None = None

    def __post_init__(self) -> None:
        convertible = _require_economic_identity(
            self.convertible_identity,
            field_name="convertible identity",
        )
        target = _require_economic_identity(
            self.target_equity_identity,
            field_name="convertible target equity identity",
            required_family="equities",
        )
        feature = _require_conversion_feature(self.conversion_feature)
        if convertible.identity_id == target.identity_id:
            _fail("convertible and target equity identities must differ")
        if feature.target_identity_id != target.identity_id:
            _fail("conversion target identity must match target equity identity")
        if self.credit_leg_identity is not None:
            credit_leg = _require_economic_identity(
                self.credit_leg_identity,
                field_name="convertible credit leg identity",
                required_family="fixed-income-credit",
            )
            if credit_leg.identity_id == target.identity_id:
                _fail("convertible credit leg and target equity identities must differ")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "convertible",
            _economic_identity_values(self.convertible_identity),
            _economic_identity_values(self.target_equity_identity),
            _conversion_feature_values(self.conversion_feature),
            _economic_identity_values(self.credit_leg_identity)
            if self.credit_leg_identity is not None
            else None,
        )


type WarrantConvertibleQualificationTerms = (
    EquityWarrantQualificationTerms | ConvertibleQualificationTerms
)


@dataclass(frozen=True, slots=True)
class WarrantConvertibleQualification:
    qualification_id: WarrantConvertibleQualificationId
    kind: WarrantConvertibleQualificationKind
    terms: WarrantConvertibleQualificationTerms
    evidence_ref: WarrantConvertibleEvidenceRef

    def __post_init__(self) -> None:
        if type(self.qualification_id) is not WarrantConvertibleQualificationId:
            _fail("qualification_id must be exact WarrantConvertibleQualificationId")
        self.qualification_id.__post_init__()
        if type(self.kind) is not WarrantConvertibleQualificationKind:
            _fail("kind must be exact WarrantConvertibleQualificationKind")
        if type(self.evidence_ref) is not WarrantConvertibleEvidenceRef:
            _fail("evidence_ref must be exact WarrantConvertibleEvidenceRef")
        self.evidence_ref.__post_init__()

        expected_type = (
            EquityWarrantQualificationTerms
            if self.kind is WarrantConvertibleQualificationKind.WARRANT
            else ConvertibleQualificationTerms
        )
        if type(self.terms) is not expected_type:
            _fail("qualification kind and terms variant must match exactly")
        self.terms.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.qualification_id.logical_values(),
            self.kind.value,
            self.terms.logical_values(),
            self.evidence_ref.logical_values(),
        )
