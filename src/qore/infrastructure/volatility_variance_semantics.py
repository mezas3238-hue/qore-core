from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from re import fullmatch
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeEvidenceRef,
    DerivativeNotional,
    DerivativeTermsId,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class VolatilityVarianceSemanticsError(InfrastructureError):
    """Base error for bounded volatility/variance/correlation semantics."""

    __slots__ = ()


class VolatilityVarianceValidationError(VolatilityVarianceSemanticsError):
    """Violation of a volatility/variance/correlation contract invariant."""

    __slots__ = ()


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        type(value) is not str
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise VolatilityVarianceValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        raise VolatilityVarianceValidationError(f"{field_name} must be exact UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if type(value) is not EconomicIdentityId:
        raise VolatilityVarianceValidationError(
            f"{field_name} must be exact EconomicIdentityId"
        )
    _validate_uuid(value.value, field_name=f"{field_name} value")


def _validate_terms_id(value: DerivativeTermsId) -> None:
    if type(value) is not DerivativeTermsId:
        raise VolatilityVarianceValidationError(
            "volatility-family terms_id must be exact DerivativeTermsId"
        )
    _validate_uuid(value.value, field_name="volatility-family terms_id value")


def _validate_evidence_ref(value: DerivativeEvidenceRef) -> None:
    if type(value) is not DerivativeEvidenceRef:
        raise VolatilityVarianceValidationError(
            "volatility-family evidence_ref must be exact DerivativeEvidenceRef"
        )
    _validate_uuid(value.value, field_name="volatility-family evidence_ref value")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise VolatilityVarianceValidationError(f"{field_name} must be date")


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    non_negative: bool = False,
) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise VolatilityVarianceValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if non_negative and value < 0:
        raise VolatilityVarianceValidationError(
            f"{field_name} must be non-negative"
        )


def _validate_notional(value: DerivativeNotional, *, field_name: str) -> None:
    if type(value) is not DerivativeNotional:
        raise VolatilityVarianceValidationError(
            f"{field_name} must be exact DerivativeNotional"
        )
    _validate_decimal(value.value, field_name=f"{field_name} value")
    if value.value <= 0:
        raise VolatilityVarianceValidationError(f"{field_name} value must be positive")
    _validate_identity(
        value.unit_identity_id,
        field_name=f"{field_name} unit identity",
    )


def _validate_payout_unit(
    value: DerivativeNotional,
    settlement_terms: VolatilitySettlementTerms,
    *,
    field_name: str,
) -> None:
    if value.unit_identity_id != settlement_terms.settlement_identity_id:
        raise VolatilityVarianceValidationError(
            f"{field_name} unit identity must equal settlement identity"
        )


def _canonical_decimal(value: Decimal) -> str:
    parts = value.as_tuple()
    if all(digit == 0 for digit in parts.digits):
        return "0"

    digits = list(parts.digits)
    exponent = int(parts.exponent)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1

    normalized = Decimal((parts.sign, tuple(digits), exponent))
    compact = str(normalized).lower()
    sign_length = 1 if parts.sign else 0

    if exponent >= 0:
        fixed_length = sign_length + len(digits) + exponent
    elif -exponent < len(digits):
        fixed_length = sign_length + len(digits) + 1
    else:
        fixed_length = sign_length + 2 - exponent

    if fixed_length <= len(compact) + 1:
        return format(normalized, "f")
    return compact


def _notional_logical_values(value: DerivativeNotional) -> tuple[object, ...]:
    return (
        _canonical_decimal(value.value),
        (str(value.unit_identity_id.value),),
    )


@dataclass(frozen=True, slots=True)
class VolatilityObservationScheduleCode:
    """Static observation-schedule qualification; never a schedule engine."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="volatility observation schedule code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class VolatilityCalculationConventionCode:
    """Static realized-metric convention code; never a calculator."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="volatility calculation convention code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class VarianceStrike:
    """Non-negative contractual variance strike."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="variance strike", non_negative=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class VolatilityStrike:
    """Non-negative contractual volatility strike."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="volatility strike", non_negative=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class CorrelationStrike:
    """Contractual correlation strike in the closed interval [-1, 1]."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="correlation strike")
        if self.value < Decimal("-1") or self.value > Decimal("1"):
            raise VolatilityVarianceValidationError(
                "correlation strike must be between -1 and 1 inclusive"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class VolatilityObservationTerms:
    """Static observation window and convention, not observed path or calculation."""

    observation_start_date: date
    observation_end_date: date
    schedule_code: VolatilityObservationScheduleCode
    calculation_convention: VolatilityCalculationConventionCode
    expected_observation_count: int | None = None

    def __post_init__(self) -> None:
        _validate_date(
            self.observation_start_date,
            field_name="volatility observation start date",
        )
        _validate_date(
            self.observation_end_date,
            field_name="volatility observation end date",
        )
        if self.observation_end_date <= self.observation_start_date:
            raise VolatilityVarianceValidationError(
                "volatility observation end date must be after start date"
            )
        if type(self.schedule_code) is not VolatilityObservationScheduleCode:
            raise VolatilityVarianceValidationError(
                "volatility observation schedule_code must be typed"
            )
        if type(self.calculation_convention) is not VolatilityCalculationConventionCode:
            raise VolatilityVarianceValidationError(
                "volatility observation calculation_convention must be typed"
            )
        if self.expected_observation_count is not None and (
            type(self.expected_observation_count) is not int
            or self.expected_observation_count <= 0
        ):
            raise VolatilityVarianceValidationError(
                "expected observation count must be a positive int or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_start_date.isoformat(),
            self.observation_end_date.isoformat(),
            self.schedule_code.logical_values(),
            self.calculation_convention.logical_values(),
            self.expected_observation_count,
        )


@dataclass(frozen=True, slots=True)
class VolatilitySettlementTerms:
    """Static contractual settlement target/date; performs no settlement."""

    settlement_identity_id: EconomicIdentityId
    settlement_date: date

    def __post_init__(self) -> None:
        _validate_identity(
            self.settlement_identity_id,
            field_name="volatility settlement identity",
        )
        _validate_date(self.settlement_date, field_name="volatility settlement date")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.settlement_identity_id.logical_values(),
            self.settlement_date.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CorrelationConstituent:
    """One static correlation-basket reference and contractual relative weight."""

    reference_identity_id: EconomicIdentityId
    weight: Decimal

    def __post_init__(self) -> None:
        _validate_identity(
            self.reference_identity_id,
            field_name="correlation constituent reference identity",
        )
        _validate_decimal(self.weight, field_name="correlation constituent weight")
        if self.weight <= 0:
            raise VolatilityVarianceValidationError(
                "correlation constituent weight must be positive"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.reference_identity_id.logical_values(),
            _canonical_decimal(self.weight),
        )


def _validate_schedule_code_child(value: VolatilityObservationScheduleCode) -> None:
    if type(value) is not VolatilityObservationScheduleCode:
        raise VolatilityVarianceValidationError(
            "volatility observation schedule_code must be typed"
        )
    _validate_code(value.value, field_name="volatility observation schedule code")


def _validate_calculation_convention_child(
    value: VolatilityCalculationConventionCode,
) -> None:
    if type(value) is not VolatilityCalculationConventionCode:
        raise VolatilityVarianceValidationError(
            "volatility observation calculation_convention must be typed"
        )
    _validate_code(value.value, field_name="volatility calculation convention code")


def _validate_variance_strike_child(value: VarianceStrike) -> None:
    if type(value) is not VarianceStrike:
        raise VolatilityVarianceValidationError(
            "variance swap variance_strike must be VarianceStrike"
        )
    _validate_decimal(value.value, field_name="variance strike", non_negative=True)


def _validate_volatility_strike_child(value: VolatilityStrike) -> None:
    if type(value) is not VolatilityStrike:
        raise VolatilityVarianceValidationError(
            "volatility swap volatility_strike must be VolatilityStrike"
        )
    _validate_decimal(value.value, field_name="volatility strike", non_negative=True)


def _validate_correlation_strike_child(value: CorrelationStrike) -> None:
    if type(value) is not CorrelationStrike:
        raise VolatilityVarianceValidationError(
            "correlation swap correlation_strike must be CorrelationStrike"
        )
    _validate_decimal(value.value, field_name="correlation strike")
    if value.value < Decimal("-1") or value.value > Decimal("1"):
        raise VolatilityVarianceValidationError(
            "correlation strike must be between -1 and 1 inclusive"
        )


def _validate_observation_terms_child(value: VolatilityObservationTerms) -> None:
    if type(value) is not VolatilityObservationTerms:
        raise VolatilityVarianceValidationError(
            "volatility-family observation_terms must be typed"
        )
    _validate_date(
        value.observation_start_date,
        field_name="volatility observation start date",
    )
    _validate_date(
        value.observation_end_date,
        field_name="volatility observation end date",
    )
    if value.observation_end_date <= value.observation_start_date:
        raise VolatilityVarianceValidationError(
            "volatility observation end date must be after start date"
        )
    _validate_schedule_code_child(value.schedule_code)
    _validate_calculation_convention_child(value.calculation_convention)
    if value.expected_observation_count is not None and (
        type(value.expected_observation_count) is not int
        or value.expected_observation_count <= 0
    ):
        raise VolatilityVarianceValidationError(
            "expected observation count must be a positive int or None"
        )


def _validate_settlement_terms_child(value: VolatilitySettlementTerms) -> None:
    if type(value) is not VolatilitySettlementTerms:
        raise VolatilityVarianceValidationError(
            "volatility-family settlement_terms must be typed"
        )
    _validate_identity(
        value.settlement_identity_id,
        field_name="volatility settlement identity",
    )
    _validate_date(value.settlement_date, field_name="volatility settlement date")


def _validate_correlation_constituent_child(value: CorrelationConstituent) -> None:
    if type(value) is not CorrelationConstituent:
        raise VolatilityVarianceValidationError(
            "correlation swap constituents must be CorrelationConstituent"
        )
    _validate_identity(
        value.reference_identity_id,
        field_name="correlation constituent reference identity",
    )
    _validate_decimal(value.weight, field_name="correlation constituent weight")
    if value.weight <= 0:
        raise VolatilityVarianceValidationError(
            "correlation constituent weight must be positive"
        )


def _validate_common_contract(
    *,
    terms_id: DerivativeTermsId,
    instrument_identity_id: EconomicIdentityId,
    observation_terms: VolatilityObservationTerms,
    settlement_terms: VolatilitySettlementTerms,
    evidence_ref: DerivativeEvidenceRef,
) -> None:
    _validate_terms_id(terms_id)
    _validate_identity(
        instrument_identity_id,
        field_name="volatility-family instrument identity",
    )
    _validate_observation_terms_child(observation_terms)
    _validate_settlement_terms_child(settlement_terms)
    if settlement_terms.settlement_date < observation_terms.observation_end_date:
        raise VolatilityVarianceValidationError(
            "volatility-family settlement date must not precede observation end"
        )
    if settlement_terms.settlement_identity_id == instrument_identity_id:
        raise VolatilityVarianceValidationError(
            "volatility-family instrument and settlement identities must differ"
        )
    _validate_evidence_ref(evidence_ref)


@dataclass(frozen=True, slots=True)
class VarianceSwapTerms:
    """Static single-netted-leg variance-swap economics."""

    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    reference_identity_id: EconomicIdentityId
    observation_terms: VolatilityObservationTerms
    variance_strike: VarianceStrike
    variance_amount: DerivativeNotional
    settlement_terms: VolatilitySettlementTerms
    evidence_ref: DerivativeEvidenceRef
    vega_notional: DerivativeNotional | None = None

    def __post_init__(self) -> None:
        _validate_common_contract(
            terms_id=self.terms_id,
            instrument_identity_id=self.instrument_identity_id,
            observation_terms=self.observation_terms,
            settlement_terms=self.settlement_terms,
            evidence_ref=self.evidence_ref,
        )
        _validate_identity(
            self.reference_identity_id,
            field_name="variance swap reference identity",
        )
        if self.reference_identity_id == self.instrument_identity_id:
            raise VolatilityVarianceValidationError(
                "variance swap instrument and reference identities must differ"
            )
        _validate_variance_strike_child(self.variance_strike)
        _validate_notional(
            self.variance_amount,
            field_name="variance swap variance_amount",
        )
        _validate_payout_unit(
            self.variance_amount,
            self.settlement_terms,
            field_name="variance swap variance_amount",
        )
        if self.vega_notional is not None:
            _validate_notional(
                self.vega_notional,
                field_name="variance swap vega_notional",
            )
            _validate_payout_unit(
                self.vega_notional,
                self.settlement_terms,
                field_name="variance swap vega_notional",
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "variance-swap",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.observation_terms.logical_values(),
            self.variance_strike.logical_values(),
            _notional_logical_values(self.variance_amount),
            _notional_logical_values(self.vega_notional)
            if self.vega_notional is not None
            else None,
            self.settlement_terms.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class VolatilitySwapTerms:
    """Static single-netted-leg volatility-swap economics."""

    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    reference_identity_id: EconomicIdentityId
    observation_terms: VolatilityObservationTerms
    volatility_strike: VolatilityStrike
    vega_notional: DerivativeNotional
    settlement_terms: VolatilitySettlementTerms
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        _validate_common_contract(
            terms_id=self.terms_id,
            instrument_identity_id=self.instrument_identity_id,
            observation_terms=self.observation_terms,
            settlement_terms=self.settlement_terms,
            evidence_ref=self.evidence_ref,
        )
        _validate_identity(
            self.reference_identity_id,
            field_name="volatility swap reference identity",
        )
        if self.reference_identity_id == self.instrument_identity_id:
            raise VolatilityVarianceValidationError(
                "volatility swap instrument and reference identities must differ"
            )
        _validate_volatility_strike_child(self.volatility_strike)
        _validate_notional(
            self.vega_notional,
            field_name="volatility swap vega_notional",
        )
        _validate_payout_unit(
            self.vega_notional,
            self.settlement_terms,
            field_name="volatility swap vega_notional",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "volatility-swap",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.observation_terms.logical_values(),
            self.volatility_strike.logical_values(),
            _notional_logical_values(self.vega_notional),
            self.settlement_terms.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CorrelationSwapTerms:
    """Static single-netted-leg correlation-swap economics."""

    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    constituents: tuple[CorrelationConstituent, ...]
    observation_terms: VolatilityObservationTerms
    correlation_strike: CorrelationStrike
    correlation_amount: DerivativeNotional
    settlement_terms: VolatilitySettlementTerms
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        _validate_common_contract(
            terms_id=self.terms_id,
            instrument_identity_id=self.instrument_identity_id,
            observation_terms=self.observation_terms,
            settlement_terms=self.settlement_terms,
            evidence_ref=self.evidence_ref,
        )
        if type(self.constituents) is not tuple or len(self.constituents) < 2:
            raise VolatilityVarianceValidationError(
                "correlation swap constituents must be a tuple with at least two entries"
            )
        for constituent in self.constituents:
            _validate_correlation_constituent_child(constituent)
        ordered_constituents = tuple(
            sorted(
                self.constituents,
                key=lambda constituent: str(constituent.reference_identity_id.value),
            )
        )
        object.__setattr__(self, "constituents", ordered_constituents)
        identities = tuple(
            constituent.reference_identity_id for constituent in self.constituents
        )
        if len(set(identities)) != len(identities):
            raise VolatilityVarianceValidationError(
                "correlation swap constituent identities must be unique"
            )
        if self.instrument_identity_id in identities:
            raise VolatilityVarianceValidationError(
                "correlation swap instrument must not be a basket constituent"
            )
        _validate_correlation_strike_child(self.correlation_strike)
        _validate_notional(
            self.correlation_amount,
            field_name="correlation swap correlation_amount",
        )
        _validate_payout_unit(
            self.correlation_amount,
            self.settlement_terms,
            field_name="correlation swap correlation_amount",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "correlation-swap",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            tuple(constituent.logical_values() for constituent in self.constituents),
            self.observation_terms.logical_values(),
            self.correlation_strike.logical_values(),
            _notional_logical_values(self.correlation_amount),
            self.settlement_terms.logical_values(),
            self.evidence_ref.logical_values(),
        )
