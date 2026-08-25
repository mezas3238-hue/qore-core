from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import cast
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


def _exact[T](value: object, expected_type: type[T], *, field_name: str) -> T:
    if type(value) is not expected_type:
        _fail(f"{field_name} must be exact {expected_type.__name__}")
    return cast(T, value)


def _require_uuid(value: object, *, field_name: str) -> UUID:
    return _exact(value, UUID, field_name=field_name)


def _require_date(value: object, *, field_name: str) -> date:
    return _exact(value, date, field_name=field_name)


def _require_code(value: object, *, field_name: str) -> str:
    text = _exact(value, str, field_name=field_name)
    if (
        len(text) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", text) is None
    ):
        _fail(f"{field_name} must use canonical lowercase code syntax")
    return text


def _require_decimal(
    value: object,
    *,
    field_name: str,
    positive: bool = False,
) -> Decimal:
    decimal_value = _exact(value, Decimal, field_name=field_name)
    if not decimal_value.is_finite():
        _fail(f"{field_name} must be finite")
    if positive and decimal_value <= 0:
        _fail(f"{field_name} must be positive")
    return decimal_value


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"

    decimal_tuple = normalized.as_tuple()
    exponent = _exact(
        decimal_tuple.exponent,
        int,
        field_name="finite Decimal exponent",
    )
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
    identity_id = _exact(value, EconomicIdentityId, field_name=field_name)
    _require_uuid(identity_id.value, field_name=f"{field_name} value")
    return identity_id


def _identity_values(value: EconomicIdentityId) -> tuple[str, ...]:
    identity_id = _require_identity_id(value, field_name="economic identity id")
    return (str(identity_id.value),)


def _require_economic_identity(
    value: object,
    *,
    field_name: str,
    required_family: str | None = None,
) -> EconomicIdentity:
    identity = _exact(value, EconomicIdentity, field_name=field_name)
    _require_identity_id(identity.identity_id, field_name=f"{field_name} identity_id")
    kind = _exact(identity.kind, EconomicIdentityKind, field_name=f"{field_name} kind")
    family = _exact(
        identity.family,
        IdentityFamilyCode,
        field_name=f"{field_name} family",
    )
    family_code = _require_code(
        family.value,
        field_name=f"{field_name} family value",
    )
    if required_family is not None and family_code != required_family:
        _fail(f"{field_name} family must be {required_family}")
    construction = _exact(
        identity.construction,
        IdentityConstructionKind,
        field_name=f"{field_name} construction",
    )
    evidence_ref = _exact(
        identity.evidence_ref,
        IdentityEvidenceRef,
        field_name=f"{field_name} evidence_ref",
    )
    _require_uuid(
        evidence_ref.value,
        field_name=f"{field_name} evidence_ref value",
    )
    if (
        construction is IdentityConstructionKind.CONTINUOUS_REFERENCE
        and kind is not EconomicIdentityKind.REFERENCE_OBJECT
    ):
        _fail("continuous-reference identity must be a reference object")
    return identity


def _economic_identity_values(value: EconomicIdentity) -> tuple[object, ...]:
    identity = _require_economic_identity(value, field_name="economic identity")
    return (
        _identity_values(identity.identity_id),
        identity.kind.value,
        (identity.family.value,),
        identity.construction.value,
        (str(identity.evidence_ref.value),),
    )


def _require_derivative_terms_id(value: object) -> DerivativeTermsId:
    terms_id = _exact(value, DerivativeTermsId, field_name="option terms_id")
    _require_uuid(terms_id.value, field_name="option terms_id value")
    return terms_id


def _require_derivative_evidence(value: object) -> DerivativeEvidenceRef:
    evidence_ref = _exact(
        value,
        DerivativeEvidenceRef,
        field_name="option evidence_ref",
    )
    _require_uuid(evidence_ref.value, field_name="option evidence_ref value")
    return evidence_ref


def _require_price_quote_basis(value: object) -> DerivativePriceQuoteBasisCode:
    basis = _exact(
        value,
        DerivativePriceQuoteBasisCode,
        field_name="option strike price quote basis",
    )
    _require_code(basis.value, field_name="option strike price quote basis value")
    return basis


def _require_strike(value: object) -> DerivativeStrike:
    strike = _exact(value, DerivativeStrike, field_name="option strike")
    _require_decimal(strike.value, field_name="option strike value")
    basis = _exact(
        strike.basis,
        DerivativeStrikeBasis,
        field_name="option strike basis",
    )
    if strike.quote_identity_id is not None:
        _require_identity_id(
            strike.quote_identity_id,
            field_name="option strike quote identity",
        )
    if strike.price_quote_basis is not None:
        _require_price_quote_basis(strike.price_quote_basis)

    convention = strike.convention
    if convention is not None:
        if type(convention) is RateCurveConvention:
            convention.__post_init__()
        elif type(convention) is YieldConvention:
            convention.__post_init__()
        else:
            _fail("option strike convention must use an exact retained convention type")

    if basis is DerivativeStrikeBasis.PRICE:
        if (
            strike.quote_identity_id is None
            or strike.price_quote_basis is None
            or convention is not None
        ):
            _fail("price strike requires quote identity, price quote basis, and no convention")
    elif basis is DerivativeStrikeBasis.RATE:
        if (
            strike.quote_identity_id is not None
            or strike.price_quote_basis is not None
            or type(convention) is not RateCurveConvention
        ):
            _fail("rate strike requires exact RateCurveConvention only")
    elif basis is DerivativeStrikeBasis.YIELD:
        if (
            strike.quote_identity_id is not None
            or strike.price_quote_basis is not None
            or type(convention) is not YieldConvention
        ):
            _fail("yield strike requires exact YieldConvention only")
    elif (
        strike.quote_identity_id is not None
        or strike.price_quote_basis is not None
        or convention is not None
    ):
        _fail("spread/level strike must not carry price/quote/convention material")
    return strike


def _strike_values(value: DerivativeStrike) -> tuple[object, ...]:
    strike = _require_strike(value)
    convention = strike.convention
    if type(convention) is RateCurveConvention:
        convention_values: tuple[object, ...] | None = convention.logical_values()
    elif type(convention) is YieldConvention:
        convention_values = (
            "yield-convention",
            convention.logical_values(),
        )
    else:
        convention_values = None
    return (
        _canonical_decimal(strike.value),
        strike.basis.value,
        _identity_values(strike.quote_identity_id)
        if strike.quote_identity_id is not None
        else None,
        (strike.price_quote_basis.value,)
        if strike.price_quote_basis is not None
        else None,
        convention_values,
    )


def _require_exercise(value: object) -> OptionExerciseTerms:
    exercise = _exact(value, OptionExerciseTerms, field_name="option exercise")
    style = _exact(
        exercise.style,
        OptionExerciseStyle,
        field_name="option exercise style",
    )
    if exercise.american_start_date is not None:
        _require_date(
            exercise.american_start_date,
            field_name="option American exercise start date",
        )
    bermudan_dates = _exact(
        exercise.bermudan_dates,
        tuple,
        field_name="option Bermudan dates",
    )
    for exercise_date in bermudan_dates:
        _require_date(exercise_date, field_name="option Bermudan exercise date")

    if style is OptionExerciseStyle.AMERICAN:
        if exercise.american_start_date is None or bermudan_dates:
            _fail("American exercise requires only explicit start date")
    elif style is OptionExerciseStyle.BERMUDAN:
        if exercise.american_start_date is not None or not bermudan_dates:
            _fail("Bermudan exercise requires only explicit Bermudan dates")
        if len(set(bermudan_dates)) != len(bermudan_dates):
            _fail("Bermudan exercise dates must be unique")
        if bermudan_dates != tuple(sorted(bermudan_dates)):
            _fail("Bermudan exercise dates must remain canonically ordered")
    elif exercise.american_start_date is not None or bermudan_dates:
        _fail("European exercise must not carry other exercise-date material")
    return exercise


def _exercise_values(value: OptionExerciseTerms) -> tuple[object, ...]:
    exercise = _require_exercise(value)
    return (
        exercise.style.value,
        exercise.american_start_date.isoformat()
        if exercise.american_start_date is not None
        else None,
        tuple(item.isoformat() for item in exercise.bermudan_dates),
    )


def _require_multiplier(value: object) -> DerivativeContractMultiplier:
    multiplier = _exact(
        value,
        DerivativeContractMultiplier,
        field_name="option multiplier",
    )
    _require_decimal(multiplier.value, field_name="option multiplier value", positive=True)
    _require_identity_id(
        multiplier.unit_identity_id,
        field_name="option multiplier unit identity",
    )
    return multiplier


def _multiplier_values(value: DerivativeContractMultiplier) -> tuple[object, ...]:
    multiplier = _require_multiplier(value)
    return (
        _canonical_decimal(multiplier.value),
        _identity_values(multiplier.unit_identity_id),
    )


def _require_notional(value: object) -> DerivativeNotional:
    notional = _exact(value, DerivativeNotional, field_name="option notional")
    _require_decimal(notional.value, field_name="option notional value", positive=True)
    _require_identity_id(
        notional.unit_identity_id,
        field_name="option notional unit identity",
    )
    return notional


def _notional_values(value: DerivativeNotional) -> tuple[object, ...]:
    notional = _require_notional(value)
    return (
        _canonical_decimal(notional.value),
        _identity_values(notional.unit_identity_id),
    )


def _require_option_terms(value: object) -> OptionContractTerms:
    option = _exact(value, OptionContractTerms, field_name="warrant option_terms")
    _require_derivative_terms_id(option.terms_id)
    _require_identity_id(
        option.instrument_identity_id,
        field_name="option instrument identity",
    )
    _require_identity_id(
        option.underlying_identity_id,
        field_name="option underlying identity",
    )
    _require_identity_id(
        option.settlement_identity_id,
        field_name="option settlement identity",
    )
    if option.instrument_identity_id == option.underlying_identity_id:
        _fail("option instrument and underlying identities must differ")
    if option.instrument_identity_id == option.settlement_identity_id:
        _fail("option instrument and settlement identities must differ")
    _exact(option.right, OptionRight, field_name="option right")
    _require_strike(option.strike)
    expiry_date = _require_date(option.expiry_date, field_name="option expiry_date")
    exercise = _require_exercise(option.exercise)
    if (
        exercise.american_start_date is not None
        and exercise.american_start_date > expiry_date
    ):
        _fail("American exercise start date must not be after option expiry")
    if any(item > expiry_date for item in exercise.bermudan_dates):
        _fail("Bermudan exercise date must not be after option expiry")
    _exact(
        option.settlement_style,
        DerivativeSettlementStyle,
        field_name="option settlement style",
    )
    _require_derivative_evidence(option.evidence_ref)
    if option.multiplier is not None:
        _require_multiplier(option.multiplier)
    if option.notional is not None:
        _require_notional(option.notional)
    if option.multiplier is None and option.notional is None:
        _fail("option requires multiplier and/or notional")
    return option


def _option_values(value: OptionContractTerms) -> tuple[object, ...]:
    option = _require_option_terms(value)
    return (
        "option",
        (str(option.terms_id.value),),
        _identity_values(option.instrument_identity_id),
        _identity_values(option.underlying_identity_id),
        _identity_values(option.settlement_identity_id),
        option.right.value,
        _strike_values(option.strike),
        option.expiry_date.isoformat(),
        _exercise_values(option.exercise),
        option.settlement_style.value,
        (str(option.evidence_ref.value),),
        _multiplier_values(option.multiplier) if option.multiplier is not None else None,
        _notional_values(option.notional) if option.notional is not None else None,
    )


def _require_structured_feature_id(value: object) -> StructuredFeatureId:
    feature_id = _exact(
        value,
        StructuredFeatureId,
        field_name="conversion feature_id",
    )
    _require_uuid(feature_id.value, field_name="conversion feature_id value")
    return feature_id


def _require_structured_evidence(value: object) -> StructuredEvidenceRef:
    evidence_ref = _exact(
        value,
        StructuredEvidenceRef,
        field_name="conversion evidence_ref",
    )
    _require_uuid(evidence_ref.value, field_name="conversion evidence_ref value")
    return evidence_ref


def _require_positive_ratio(value: object) -> StructuredPositiveRatio:
    ratio = _exact(
        value,
        StructuredPositiveRatio,
        field_name="conversion ratio",
    )
    _require_decimal(ratio.value, field_name="conversion ratio value", positive=True)
    return ratio


def _require_contract_level(value: object) -> StructuredContractLevel:
    level = _exact(
        value,
        StructuredContractLevel,
        field_name="conversion level",
    )
    _require_decimal(level.value, field_name="conversion level value")
    _exact(
        level.kind,
        StructuredContractLevelKind,
        field_name="conversion level kind",
    )
    _require_identity_id(
        level.reference_identity_id,
        field_name="conversion level reference identity",
    )
    unit = _exact(
        level.unit,
        StructuredLevelUnitCode,
        field_name="conversion level unit",
    )
    _require_code(unit.value, field_name="conversion level unit value")
    return level


def _contract_level_values(value: StructuredContractLevel) -> tuple[object, ...]:
    level = _require_contract_level(value)
    return (
        _canonical_decimal(level.value),
        level.kind.value,
        _identity_values(level.reference_identity_id),
        (level.unit.value,),
    )


def _require_conversion_feature(value: object) -> StructuredConversionFeature:
    feature = _exact(
        value,
        StructuredConversionFeature,
        field_name="conversion_feature",
    )
    _require_structured_feature_id(feature.feature_id)
    _require_identity_id(
        feature.target_identity_id,
        field_name="conversion target identity",
    )
    _require_positive_ratio(feature.units_per_source_unit)
    _require_structured_evidence(feature.evidence_ref)
    if feature.conversion_level is not None:
        _require_contract_level(feature.conversion_level)
    return feature


def _conversion_feature_values(value: StructuredConversionFeature) -> tuple[object, ...]:
    feature = _require_conversion_feature(value)
    return (
        "conversion",
        (str(feature.feature_id.value),),
        _identity_values(feature.target_identity_id),
        (_canonical_decimal(feature.units_per_source_unit.value),),
        _contract_level_values(feature.conversion_level)
        if feature.conversion_level is not None
        else None,
        (str(feature.evidence_ref.value),),
    )


@dataclass(frozen=True, slots=True)
class WarrantConvertibleQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="qualification id")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class WarrantConvertibleEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="qualification evidence ref")

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
        qualification_id = _exact(
            self.qualification_id,
            WarrantConvertibleQualificationId,
            field_name="qualification_id",
        )
        qualification_id.__post_init__()
        kind = _exact(
            self.kind,
            WarrantConvertibleQualificationKind,
            field_name="kind",
        )
        evidence_ref = _exact(
            self.evidence_ref,
            WarrantConvertibleEvidenceRef,
            field_name="evidence_ref",
        )
        evidence_ref.__post_init__()

        if kind is WarrantConvertibleQualificationKind.WARRANT:
            warrant_terms = _exact(
                self.terms,
                EquityWarrantQualificationTerms,
                field_name="warrant qualification terms",
            )
            warrant_terms.__post_init__()
        else:
            convertible_terms = _exact(
                self.terms,
                ConvertibleQualificationTerms,
                field_name="convertible qualification terms",
            )
            convertible_terms.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.qualification_id.logical_values(),
            self.kind.value,
            self.terms.logical_values(),
            self.evidence_ref.logical_values(),
        )
