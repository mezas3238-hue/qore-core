from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from re import fullmatch

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
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise VolatilityVarianceValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise VolatilityVarianceValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise VolatilityVarianceValidationError(f"{field_name} must be date")


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    non_negative: bool = False,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise VolatilityVarianceValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if non_negative and value < 0:
        raise VolatilityVarianceValidationError(
            f"{field_name} must be non-negative"
        )


def _canonical_decimal(value: Decimal) -> str:
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


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
        if not isinstance(self.schedule_code, VolatilityObservationScheduleCode):
            raise VolatilityVarianceValidationError(
                "volatility observation schedule_code must be typed"
            )
        if not isinstance(
            self.calculation_convention,
            VolatilityCalculationConventionCode,
        ):
            raise VolatilityVarianceValidationError(
                "volatility calculation_convention must be typed"
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


def _validate_common_contract(
    *,
    terms_id: DerivativeTermsId,
    instrument_identity_id: EconomicIdentityId,
    observation_terms: VolatilityObservationTerms,
    settlement_terms: VolatilitySettlementTerms,
    evidence_ref: DerivativeEvidenceRef,
) -> None:
    if not isinstance(terms_id, DerivativeTermsId):
        raise VolatilityVarianceValidationError(
            "volatility-family terms_id must be DerivativeTermsId"
        )
    _validate_identity(
        instrument_identity_id,
        field_name="volatility-family instrument identity",
    )
    if not isinstance(observation_terms, VolatilityObservationTerms):
        raise VolatilityVarianceValidationError(
            "volatility-family observation_terms must be typed"
        )
    if not isinstance(settlement_terms, VolatilitySettlementTerms):
        raise VolatilityVarianceValidationError(
            "volatility-family settlement_terms must be typed"
        )
    if settlement_terms.settlement_date < observation_terms.observation_end_date:
        raise VolatilityVarianceValidationError(
            "volatility-family settlement date must not precede observation end"
        )
    if not isinstance(evidence_ref, DerivativeEvidenceRef):
        raise VolatilityVarianceValidationError(
            "volatility-family evidence_ref must be DerivativeEvidenceRef"
        )


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
        if not isinstance(self.variance_strike, VarianceStrike):
            raise VolatilityVarianceValidationError(
                "variance swap variance_strike must be VarianceStrike"
            )
        if not isinstance(self.variance_amount, DerivativeNotional):
            raise VolatilityVarianceValidationError(
                "variance swap variance_amount must be DerivativeNotional"
            )
        if self.vega_notional is not None and not isinstance(
            self.vega_notional,
            DerivativeNotional,
        ):
            raise VolatilityVarianceValidationError(
                "variance swap vega_notional must be DerivativeNotional or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "variance-swap",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.observation_terms.logical_values(),
            self.variance_strike.logical_values(),
            self.variance_amount.logical_values(),
            self.vega_notional.logical_values()
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
        if not isinstance(self.volatility_strike, VolatilityStrike):
            raise VolatilityVarianceValidationError(
                "volatility swap volatility_strike must be VolatilityStrike"
            )
        if not isinstance(self.vega_notional, DerivativeNotional):
            raise VolatilityVarianceValidationError(
                "volatility swap vega_notional must be DerivativeNotional"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "volatility-swap",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.observation_terms.logical_values(),
            self.volatility_strike.logical_values(),
            self.vega_notional.logical_values(),
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
            if not isinstance(constituent, CorrelationConstituent):
                raise VolatilityVarianceValidationError(
                    "correlation swap constituents must be CorrelationConstituent"
                )
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
        if not isinstance(self.correlation_strike, CorrelationStrike):
            raise VolatilityVarianceValidationError(
                "correlation swap correlation_strike must be CorrelationStrike"
            )
        if not isinstance(self.correlation_amount, DerivativeNotional):
            raise VolatilityVarianceValidationError(
                "correlation swap correlation_amount must be DerivativeNotional"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "correlation-swap",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            tuple(
                constituent.logical_values()
                for constituent in self.constituents
            ),
            self.observation_terms.logical_values(),
            self.correlation_strike.logical_values(),
            self.correlation_amount.logical_values(),
            self.settlement_terms.logical_values(),
            self.evidence_ref.logical_values(),
        )
