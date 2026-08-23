from __future__ import annotations

from datetime import date
from decimal import Decimal, localcontext
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeEvidenceRef,
    DerivativeNotional,
    DerivativeTermsId,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.infrastructure.volatility_variance_semantics import (
    CorrelationConstituent,
    CorrelationStrike,
    CorrelationSwapTerms,
    VarianceStrike,
    VarianceSwapTerms,
    VolatilityCalculationConventionCode,
    VolatilityObservationScheduleCode,
    VolatilityObservationTerms,
    VolatilitySettlementTerms,
    VolatilityStrike,
    VolatilitySwapTerms,
    VolatilityVarianceValidationError,
)


def test_extreme_decimal_exponents_remain_compact_and_exact() -> None:
    cases = (
        (Decimal("1E+1000000"), "1e+1000000"),
        (Decimal("1E-1000000"), "1e-1000000"),
    )

    with localcontext() as context:
        context.prec = 2
        for value, expected in cases:
            projected = VarianceStrike(value).logical_values()[0]
            assert projected == expected
            assert len(projected) == 10
            assert Decimal(projected) == value


def test_compact_fallback_preserves_existing_human_scale_material() -> None:
    assert VarianceStrike(Decimal("0.0400")).logical_values() == ("0.04",)
    assert VarianceStrike(Decimal("10000.00")).logical_values() == ("10000",)
    assert VarianceStrike(Decimal("-0.000")).logical_values() == ("0",)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(value=UUID(int=value))


def _observation_terms() -> VolatilityObservationTerms:
    return VolatilityObservationTerms(
        observation_start_date=date(2026, 1, 2),
        observation_end_date=date(2026, 6, 30),
        schedule_code=VolatilityObservationScheduleCode("daily-close"),
        calculation_convention=VolatilityCalculationConventionCode(
            "log-return-standard"
        ),
        expected_observation_count=125,
    )


def _settlement_terms() -> VolatilitySettlementTerms:
    return VolatilitySettlementTerms(
        settlement_identity_id=_identity(301),
        settlement_date=date(2026, 7, 2),
    )


def _terms_id(value: int) -> DerivativeTermsId:
    return DerivativeTermsId(value=UUID(int=value))


def _evidence(value: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(value=UUID(int=value))


def _notional(value: str) -> DerivativeNotional:
    return DerivativeNotional(
        value=Decimal(value),
        unit_identity_id=_identity(301),
    )


def test_parent_rejects_malformed_exact_variance_strike() -> None:
    malformed = object.__new__(VarianceStrike)
    object.__setattr__(malformed, "value", Decimal("-1"))

    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=_terms_id(101),
            instrument_identity_id=_identity(10),
            reference_identity_id=_identity(11),
            observation_terms=_observation_terms(),
            variance_strike=malformed,
            variance_amount=_notional("5000"),
            settlement_terms=_settlement_terms(),
            evidence_ref=_evidence(201),
        )


def test_parent_rejects_malformed_exact_volatility_strike() -> None:
    malformed = object.__new__(VolatilityStrike)
    object.__setattr__(malformed, "value", Decimal("-0.1"))

    with pytest.raises(VolatilityVarianceValidationError):
        VolatilitySwapTerms(
            terms_id=_terms_id(102),
            instrument_identity_id=_identity(20),
            reference_identity_id=_identity(21),
            observation_terms=_observation_terms(),
            volatility_strike=malformed,
            vega_notional=_notional("100"),
            settlement_terms=_settlement_terms(),
            evidence_ref=_evidence(202),
        )


def test_parent_rejects_malformed_exact_correlation_strike() -> None:
    malformed = object.__new__(CorrelationStrike)
    object.__setattr__(malformed, "value", Decimal("2"))

    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationSwapTerms(
            terms_id=_terms_id(103),
            instrument_identity_id=_identity(30),
            constituents=(
                CorrelationConstituent(_identity(31), Decimal("0.6")),
                CorrelationConstituent(_identity(32), Decimal("0.4")),
            ),
            observation_terms=_observation_terms(),
            correlation_strike=malformed,
            correlation_amount=_notional("10000"),
            settlement_terms=_settlement_terms(),
            evidence_ref=_evidence(203),
        )


def test_parent_rejects_malformed_exact_observation_terms() -> None:
    malformed = object.__new__(VolatilityObservationTerms)
    object.__setattr__(malformed, "observation_start_date", date(2026, 7, 1))
    object.__setattr__(malformed, "observation_end_date", date(2026, 6, 30))
    object.__setattr__(
        malformed,
        "schedule_code",
        VolatilityObservationScheduleCode("daily-close"),
    )
    object.__setattr__(
        malformed,
        "calculation_convention",
        VolatilityCalculationConventionCode("log-return-standard"),
    )
    object.__setattr__(malformed, "expected_observation_count", 125)

    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=_terms_id(104),
            instrument_identity_id=_identity(40),
            reference_identity_id=_identity(41),
            observation_terms=malformed,
            variance_strike=VarianceStrike(Decimal("0.04")),
            variance_amount=_notional("5000"),
            settlement_terms=_settlement_terms(),
            evidence_ref=_evidence(204),
        )


def test_parent_rejects_malformed_exact_schedule_child() -> None:
    malformed_schedule = object.__new__(VolatilityObservationScheduleCode)
    object.__setattr__(malformed_schedule, "value", "INVALID CODE")
    malformed = object.__new__(VolatilityObservationTerms)
    object.__setattr__(malformed, "observation_start_date", date(2026, 1, 2))
    object.__setattr__(malformed, "observation_end_date", date(2026, 6, 30))
    object.__setattr__(malformed, "schedule_code", malformed_schedule)
    object.__setattr__(
        malformed,
        "calculation_convention",
        VolatilityCalculationConventionCode("log-return-standard"),
    )
    object.__setattr__(malformed, "expected_observation_count", 125)

    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=_terms_id(105),
            instrument_identity_id=_identity(50),
            reference_identity_id=_identity(51),
            observation_terms=malformed,
            variance_strike=VarianceStrike(Decimal("0.04")),
            variance_amount=_notional("5000"),
            settlement_terms=_settlement_terms(),
            evidence_ref=_evidence(205),
        )


def test_parent_rejects_malformed_exact_settlement_terms() -> None:
    malformed = object.__new__(VolatilitySettlementTerms)
    object.__setattr__(malformed, "settlement_identity_id", _identity(301))
    object.__setattr__(malformed, "settlement_date", "2026-07-02")

    with pytest.raises(VolatilityVarianceValidationError):
        VarianceSwapTerms(
            terms_id=_terms_id(106),
            instrument_identity_id=_identity(60),
            reference_identity_id=_identity(61),
            observation_terms=_observation_terms(),
            variance_strike=VarianceStrike(Decimal("0.04")),
            variance_amount=_notional("5000"),
            settlement_terms=malformed,
            evidence_ref=_evidence(206),
        )


def test_parent_rejects_malformed_exact_correlation_constituent() -> None:
    malformed = object.__new__(CorrelationConstituent)
    object.__setattr__(malformed, "reference_identity_id", _identity(71))
    object.__setattr__(malformed, "weight", Decimal("0"))

    with pytest.raises(VolatilityVarianceValidationError):
        CorrelationSwapTerms(
            terms_id=_terms_id(107),
            instrument_identity_id=_identity(70),
            constituents=(
                malformed,
                CorrelationConstituent(_identity(72), Decimal("1")),
            ),
            observation_terms=_observation_terms(),
            correlation_strike=CorrelationStrike(Decimal("0.35")),
            correlation_amount=_notional("10000"),
            settlement_terms=_settlement_terms(),
            evidence_ref=_evidence(207),
        )
