from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractValidationError,
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
from qore.infrastructure.fixed_income_economics import (
    CompoundingConventionCode,
    DayCountConventionCode,
    FinancialTenor,
    FinancialTenorUnit,
    FixedIncomeBenchmarkReference,
    FixedIncomeReferenceRoleCode,
    FixedIncomeYieldCode,
    YieldConvention,
)
from qore.infrastructure.product_composition_semantics import (
    ProductCompositionClass,
    ProductCompositionEvidenceRef,
    ProductCompositionLeg,
    ProductCompositionLegId,
    ProductCompositionMagnitude,
    ProductCompositionMagnitudeKind,
    ProductCompositionMode,
    ProductCompositionRoleCode,
    ProductCompositionTerms,
)
from qore.infrastructure.rainbow_option_composition_semantics import (
    RainbowOptionCompositionQualification,
    RainbowOptionCompositionValidationError,
    RainbowOptionSelectionKind,
    RainbowPerformanceRuleCode,
)
from qore.infrastructure.rate_term_structure import RateCurveConvention
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


class _EvilTermsId(DerivativeTermsId):
    def __post_init__(self) -> None:
        pass


@dataclass(frozen=True, slots=True)
class _DecoratedEvilTermsId(DerivativeTermsId):
    def __post_init__(self) -> None:
        pass


class _EvilRateCurveConvention(RateCurveConvention):
    def __post_init__(self) -> None:
        pass


def _qualification() -> RainbowOptionCompositionQualification:
    root = _identity(500)
    option = OptionContractTerms(
        terms_id=DerivativeTermsId(_uuid(501)),
        instrument_identity_id=_identity(502),
        underlying_identity_id=root,
        settlement_identity_id=_identity(503),
        right=OptionRight.CALL,
        strike=DerivativeStrike(
            value=Decimal("100"),
            basis=DerivativeStrikeBasis.PRICE,
            quote_identity_id=_identity(504),
            price_quote_basis=DerivativePriceQuoteBasisCode("currency-per-unit"),
        ),
        expiry_date=date(2027, 6, 18),
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=DerivativeEvidenceRef(_uuid(505)),
        notional=DerivativeNotional(Decimal("1000"), _identity(503)),
    )
    legs = (
        ProductCompositionLeg(
            leg_id=ProductCompositionLegId(_uuid(506)),
            component_identity_id=_identity(507),
            role=ProductCompositionRoleCode("constituent"),
            magnitude=ProductCompositionMagnitude(
                ProductCompositionMagnitudeKind.WEIGHT,
                Decimal("0.4"),
            ),
            evidence_ref=ProductCompositionEvidenceRef(_uuid(508)),
        ),
        ProductCompositionLeg(
            leg_id=ProductCompositionLegId(_uuid(509)),
            component_identity_id=_identity(510),
            role=ProductCompositionRoleCode("constituent"),
            magnitude=ProductCompositionMagnitude(
                ProductCompositionMagnitudeKind.WEIGHT,
                Decimal("0.6"),
            ),
            evidence_ref=ProductCompositionEvidenceRef(_uuid(511)),
        ),
    )
    composition = ProductCompositionTerms(
        root_identity_id=root,
        composition_class=ProductCompositionClass.BASKET,
        mode=ProductCompositionMode.UNORDERED_CANONICAL,
        legs=legs,
        evidence_ref=ProductCompositionEvidenceRef(_uuid(512)),
    )
    return RainbowOptionCompositionQualification(
        option=option,
        composition=composition,
        selection=RainbowOptionSelectionKind.BEST_OF,
        performance_rule=RainbowPerformanceRuleCode("contractual-performance"),
        evidence_ref=DerivativeEvidenceRef(_uuid(513)),
    )


def _periodic_tenor() -> FinancialTenor:
    return FinancialTenor(6, FinancialTenorUnit.MONTH)


def _rate_convention() -> RateCurveConvention:
    return RateCurveConvention(
        day_count=DayCountConventionCode("actual-360"),
        compounding=CompoundingConventionCode("periodic"),
        compounding_tenor=_periodic_tenor(),
    )


def _yield_convention() -> YieldConvention:
    return YieldConvention(
        yield_code=FixedIncomeYieldCode("yield-to-maturity"),
        day_count=DayCountConventionCode("actual-365-fixed"),
        compounding=CompoundingConventionCode("periodic"),
        compounding_tenor=_periodic_tenor(),
        reference=FixedIncomeBenchmarkReference(
            reference_identity_id=_identity(514),
            role=FixedIncomeReferenceRoleCode("benchmark"),
            tenor=FinancialTenor(5, FinancialTenorUnit.YEAR),
        ),
    )


def _qualification_with_strike(
    strike: DerivativeStrike,
) -> RainbowOptionCompositionQualification:
    qualification = _qualification()
    return replace(qualification, option=replace(qualification.option, strike=strike))


def test_projection_rejects_corrupted_nested_option_terms_id() -> None:
    qualification = _qualification()
    object.__setattr__(qualification.option.terms_id, "value", "not-a-uuid")

    with pytest.raises(
        DerivativeContractValidationError,
        match="derivative terms id must be UUID",
    ):
        qualification.logical_values()


def test_projection_rejects_corrupted_nested_option_strike() -> None:
    qualification = _qualification()
    object.__setattr__(qualification.option.strike, "value", "not-a-decimal")

    with pytest.raises(
        DerivativeContractValidationError,
        match="derivative strike must be a finite Decimal",
    ):
        qualification.logical_values()


def test_projection_rejects_nested_owner_subclass_laundering() -> None:
    qualification = _qualification()
    evil = _EvilTermsId(cast(Any, "not-a-uuid"))
    object.__setattr__(qualification.option, "terms_id", evil)

    with pytest.raises(
        RainbowOptionCompositionValidationError,
        match=r"option\.terms_id must use exact declared dataclass type",
    ):
        qualification.logical_values()


def test_projection_rejects_decorated_nested_owner_subclass_laundering() -> None:
    qualification = _qualification()
    evil = _DecoratedEvilTermsId(cast(Any, "not-a-uuid"))
    object.__setattr__(qualification.option, "terms_id", evil)

    with pytest.raises(
        RainbowOptionCompositionValidationError,
        match=r"option\.terms_id must use exact declared dataclass type",
    ):
        qualification.logical_values()


def test_projection_accepts_valid_rate_strike_through_pep695_alias() -> None:
    qualification = _qualification_with_strike(
        DerivativeStrike(
            value=Decimal("0.05"),
            basis=DerivativeStrikeBasis.RATE,
            convention=_rate_convention(),
        )
    )

    assert qualification.logical_values()[1] == qualification.option.logical_values()


def test_projection_accepts_valid_yield_strike_with_nested_reference() -> None:
    qualification = _qualification_with_strike(
        DerivativeStrike(
            value=Decimal("0.0475"),
            basis=DerivativeStrikeBasis.YIELD,
            convention=_yield_convention(),
        )
    )

    assert qualification.logical_values()[1] == qualification.option.logical_values()


def test_projection_rejects_rate_convention_subclass_laundering() -> None:
    qualification = _qualification_with_strike(
        DerivativeStrike(
            value=Decimal("0.05"),
            basis=DerivativeStrikeBasis.RATE,
            convention=_rate_convention(),
        )
    )
    convention = _rate_convention()
    evil = _EvilRateCurveConvention(
        day_count=convention.day_count,
        compounding=convention.compounding,
        compounding_tenor=convention.compounding_tenor,
    )
    object.__setattr__(qualification.option.strike, "convention", evil)

    with pytest.raises(
        RainbowOptionCompositionValidationError,
        match=r"option\.strike\.convention must use exact declared dataclass type",
    ):
        qualification.logical_values()
