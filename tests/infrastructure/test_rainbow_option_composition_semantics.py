from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.rainbow_option_composition_semantics as rainbow_module
from qore.infrastructure.derivative_contract_semantics import (
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
    ProductCompositionValidationError,
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


def _derivative_evidence(value: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(value))


def _composition_evidence(value: int) -> ProductCompositionEvidenceRef:
    return ProductCompositionEvidenceRef(_uuid(value))


def _strike() -> DerivativeStrike:
    return DerivativeStrike(
        value=Decimal("100"),
        basis=DerivativeStrikeBasis.PRICE,
        quote_identity_id=_identity(900),
        price_quote_basis=DerivativePriceQuoteBasisCode("currency-per-unit"),
    )


def _option(
    underlying: EconomicIdentityId,
    *,
    right: OptionRight = OptionRight.CALL,
) -> OptionContractTerms:
    return OptionContractTerms(
        terms_id=DerivativeTermsId(_uuid(100)),
        instrument_identity_id=_identity(101),
        underlying_identity_id=underlying,
        settlement_identity_id=_identity(102),
        right=right,
        strike=_strike(),
        expiry_date=date(2027, 6, 18),
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_derivative_evidence(103),
        notional=DerivativeNotional(Decimal("1000"), _identity(102)),
    )


def _leg(
    *,
    leg_id: int,
    component: int,
    weight: str,
) -> ProductCompositionLeg:
    return ProductCompositionLeg(
        leg_id=ProductCompositionLegId(_uuid(leg_id)),
        component_identity_id=_identity(component),
        role=ProductCompositionRoleCode("constituent"),
        magnitude=ProductCompositionMagnitude(
            kind=ProductCompositionMagnitudeKind.WEIGHT,
            value=Decimal(weight),
        ),
        evidence_ref=_composition_evidence(1000 + leg_id),
    )


def _composition(
    root: EconomicIdentityId,
    *,
    composition_class: ProductCompositionClass = ProductCompositionClass.BASKET,
    reverse: bool = False,
) -> ProductCompositionTerms:
    legs: tuple[ProductCompositionLeg, ...] = (
        _leg(leg_id=201, component=301, weight="0.4"),
        _leg(leg_id=202, component=302, weight="0.6"),
    )
    if reverse:
        legs = tuple(reversed(legs))
    return ProductCompositionTerms(
        root_identity_id=root,
        composition_class=composition_class,
        mode=ProductCompositionMode.UNORDERED_CANONICAL,
        legs=legs,
        evidence_ref=_composition_evidence(203),
    )


def _qualification(
    *,
    selection: RainbowOptionSelectionKind = RainbowOptionSelectionKind.BEST_OF,
    composition_class: ProductCompositionClass = ProductCompositionClass.BASKET,
    rule: str = "contractual-performance",
    reverse: bool = False,
) -> RainbowOptionCompositionQualification:
    root = _identity(200)
    return RainbowOptionCompositionQualification(
        option=_option(root),
        composition=_composition(
            root,
            composition_class=composition_class,
            reverse=reverse,
        ),
        selection=selection,
        performance_rule=RainbowPerformanceRuleCode(rule),
        evidence_ref=_derivative_evidence(204),
    )


def test_selection_set_is_exactly_best_of_and_worst_of() -> None:
    assert tuple(item.value for item in RainbowOptionSelectionKind) == (
        "best-of",
        "worst-of",
    )


def test_best_of_binds_option_to_exact_basket_root() -> None:
    qualification = _qualification()
    assert qualification.option.underlying_identity_id == qualification.composition.root_identity_id
    assert qualification.composition.composition_class is ProductCompositionClass.BASKET
    assert qualification.logical_values()[0] == "rainbow-option-composition.v1"
    assert qualification.logical_values()[3] == "best-of"
    assert qualification.logical_values()[4] == ("contractual-performance",)


def test_worst_of_is_distinct_contractual_material() -> None:
    best = _qualification(selection=RainbowOptionSelectionKind.BEST_OF)
    worst = _qualification(selection=RainbowOptionSelectionKind.WORST_OF)
    assert best.logical_values() != worst.logical_values()
    assert worst.logical_values()[3] == "worst-of"


def test_underlying_must_equal_composition_root() -> None:
    with pytest.raises(
        RainbowOptionCompositionValidationError,
        match="underlying must equal composition root",
    ):
        RainbowOptionCompositionQualification(
            option=_option(_identity(999)),
            composition=_composition(_identity(200)),
            selection=RainbowOptionSelectionKind.BEST_OF,
            performance_rule=RainbowPerformanceRuleCode("contractual-performance"),
            evidence_ref=_derivative_evidence(204),
        )


@pytest.mark.parametrize(
    "composition_class",
    (ProductCompositionClass.SPREAD, ProductCompositionClass.MULTI_LEG),
)
def test_best_worst_rainbow_requires_basket(
    composition_class: ProductCompositionClass,
) -> None:
    with pytest.raises(RainbowOptionCompositionValidationError, match="must be BASKET"):
        _qualification(composition_class=composition_class)


def test_qualification_does_not_duplicate_composition_leg_material() -> None:
    assert tuple(field.name for field in fields(RainbowOptionCompositionQualification)) == (
        "option",
        "composition",
        "selection",
        "performance_rule",
        "evidence_ref",
    )
    source = Path(rainbow_module.__file__).read_text()
    assert "ProductCompositionLeg" not in source
    assert "ProductCompositionMagnitude" not in source
    assert "component_identity_id" not in source


def test_no_current_winner_or_performance_state_is_stored() -> None:
    names = {field.name for field in fields(RainbowOptionCompositionQualification)}
    assert names.isdisjoint(
        {
            "selected_component",
            "winning_component",
            "current_winner",
            "current_performance",
            "observed_performance",
            "payoff",
            "valuation",
            "price",
        }
    )


@pytest.mark.parametrize("bad_rule", ("", "Uppercase", "bad rule", "a" * 65))
def test_performance_rule_requires_canonical_code(bad_rule: str) -> None:
    with pytest.raises(RainbowOptionCompositionValidationError):
        RainbowPerformanceRuleCode(bad_rule)


def test_performance_rule_rejects_non_exact_string() -> None:
    with pytest.raises(RainbowOptionCompositionValidationError, match="must be exact str"):
        RainbowPerformanceRuleCode(cast(Any, True))


def test_aggregate_requires_exact_owner_types() -> None:
    valid = _qualification()
    with pytest.raises(RainbowOptionCompositionValidationError, match="exact OptionContractTerms"):
        RainbowOptionCompositionQualification(
            option=cast(Any, object()),
            composition=valid.composition,
            selection=RainbowOptionSelectionKind.BEST_OF,
            performance_rule=RainbowPerformanceRuleCode("contractual-performance"),
            evidence_ref=_derivative_evidence(204),
        )
    with pytest.raises(
        RainbowOptionCompositionValidationError,
        match="exact ProductCompositionTerms",
    ):
        RainbowOptionCompositionQualification(
            option=valid.option,
            composition=cast(Any, object()),
            selection=RainbowOptionSelectionKind.BEST_OF,
            performance_rule=RainbowPerformanceRuleCode("contractual-performance"),
            evidence_ref=_derivative_evidence(204),
        )


def test_selection_requires_exact_enum_not_string() -> None:
    valid = _qualification()
    with pytest.raises(RainbowOptionCompositionValidationError, match="selection must be exact"):
        RainbowOptionCompositionQualification(
            option=valid.option,
            composition=valid.composition,
            selection=cast(Any, "best-of"),
            performance_rule=RainbowPerformanceRuleCode("contractual-performance"),
            evidence_ref=_derivative_evidence(204),
        )


def test_rule_and_evidence_require_exact_wrappers() -> None:
    valid = _qualification()
    with pytest.raises(RainbowOptionCompositionValidationError, match="performance rule must be exact"):
        RainbowOptionCompositionQualification(
            option=valid.option,
            composition=valid.composition,
            selection=RainbowOptionSelectionKind.BEST_OF,
            performance_rule=cast(Any, "contractual-performance"),
            evidence_ref=_derivative_evidence(204),
        )
    with pytest.raises(RainbowOptionCompositionValidationError, match="evidence must be exact"):
        RainbowOptionCompositionQualification(
            option=valid.option,
            composition=valid.composition,
            selection=RainbowOptionSelectionKind.BEST_OF,
            performance_rule=RainbowPerformanceRuleCode("contractual-performance"),
            evidence_ref=cast(Any, object()),
        )


def test_unordered_caller_order_does_not_change_projection() -> None:
    normal = _qualification(reverse=False)
    reversed_input = _qualification(reverse=True)
    assert normal.composition.logical_values() == reversed_input.composition.logical_values()
    assert normal.logical_values() == reversed_input.logical_values()


def test_option_economics_are_preserved_not_recreated() -> None:
    qualification = _qualification(selection=RainbowOptionSelectionKind.WORST_OF)
    option_values = qualification.option.logical_values()
    assert qualification.logical_values()[1] == option_values
    assert option_values[0] == "option"
    assert qualification.option.right is OptionRight.CALL
    assert qualification.option.strike.value == Decimal("100")


def test_composition_projection_is_preserved_not_flattened() -> None:
    qualification = _qualification()
    assert qualification.logical_values()[2] == qualification.composition.logical_values()
    assert qualification.composition.logical_values()[0] == "product-composition.v1"
    assert len(qualification.composition.legs) == 2


def test_logical_values_revalidates_root_binding_after_corruption() -> None:
    qualification = _qualification()
    object.__setattr__(qualification.option, "underlying_identity_id", _identity(998))
    with pytest.raises(
        RainbowOptionCompositionValidationError,
        match="underlying must equal composition root",
    ):
        qualification.logical_values()


def test_logical_values_revalidates_nested_composition() -> None:
    qualification = _qualification()
    first_leg = qualification.composition.legs[0]
    object.__setattr__(
        first_leg,
        "component_identity_id",
        qualification.composition.root_identity_id,
    )
    with pytest.raises(ProductCompositionValidationError, match="must not reference itself"):
        qualification.logical_values()


def test_logical_values_revalidates_rule_and_selection_after_corruption() -> None:
    qualification = _qualification()
    object.__setattr__(qualification.performance_rule, "value", "BAD RULE")
    with pytest.raises(RainbowOptionCompositionValidationError):
        qualification.logical_values()

    qualification = _qualification()
    object.__setattr__(qualification, "selection", "best-of")
    with pytest.raises(RainbowOptionCompositionValidationError, match="selection must be exact"):
        qualification.logical_values()


def test_values_are_frozen() -> None:
    rule = RainbowPerformanceRuleCode("contractual-performance")
    qualification = _qualification()
    with pytest.raises(FrozenInstanceError):
        rule.__setattr__("value", "other")
    with pytest.raises(FrozenInstanceError):
        qualification.__setattr__("selection", RainbowOptionSelectionKind.WORST_OF)


def test_no_ambiguous_third_selection_is_authorized() -> None:
    values = {item.value for item in RainbowOptionSelectionKind}
    assert "rainbow" not in values
    assert "other" not in values
    assert "ranked" not in values


def test_source_has_no_operational_or_valuation_authority() -> None:
    source = Path(rainbow_module.__file__).read_text()
    for token in (
        "datetime.now",
        "date.today",
        "uuid4",
        "requests.",
        "httpx.",
        "socket",
        "subprocess",
        "threading",
        "sleep(",
        "submit_order",
        "execute_order",
        "market_data",
        "current_winner",
        "selected_component",
        "calculate_payoff",
        "valuation_engine",
        "risk_manager",
        "production_account",
        "api_key",
        "secret",
        "password",
    ):
        assert token not in source


def test_source_dependencies_stop_at_certified_aggregates() -> None:
    source = Path(rainbow_module.__file__).read_text()
    assert "OptionContractTerms" in source
    assert "ProductCompositionTerms" in source
    assert "ProductCompositionClass" in source
    assert "ProductCompositionLeg" not in source
    assert "ProductCompositionMagnitude" not in source


def test_performance_rule_is_opaque_not_a_runtime_calculator() -> None:
    qualification = _qualification(rule="total-return-comparison")
    assert qualification.performance_rule.logical_values() == ("total-return-comparison",)
    assert not hasattr(qualification.performance_rule, "evaluate")
    assert not hasattr(qualification.performance_rule, "calculate")
    assert not hasattr(qualification, "select")
    assert not hasattr(qualification, "payoff")
