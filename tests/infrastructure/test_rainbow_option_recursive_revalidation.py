from __future__ import annotations

from dataclasses import dataclass
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
