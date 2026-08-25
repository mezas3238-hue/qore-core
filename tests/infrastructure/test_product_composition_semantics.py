from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.product_composition_semantics import (
    ProductCompositionClass,
    ProductCompositionDirection,
    ProductCompositionEvidenceRef,
    ProductCompositionLeg,
    ProductCompositionLegId,
    ProductCompositionLegOrdinal,
    ProductCompositionMagnitude,
    ProductCompositionMagnitudeKind,
    ProductCompositionMode,
    ProductCompositionRoleCode,
    ProductCompositionTerms,
    ProductCompositionValidationError,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


class UUIDSubclass(UUID):
    pass


class StrSubclass(str):
    pass


def _tuple_value(value: object) -> tuple[object, ...]:
    assert type(value) is tuple
    return cast(tuple[object, ...], value)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _evidence(value: int) -> ProductCompositionEvidenceRef:
    return ProductCompositionEvidenceRef(_uuid(10_000 + value))


def _magnitude(
    kind: ProductCompositionMagnitudeKind = ProductCompositionMagnitudeKind.WEIGHT,
    value: Decimal = Decimal("1"),
    *,
    unit_identity_id: EconomicIdentityId | None = None,
) -> ProductCompositionMagnitude:
    return ProductCompositionMagnitude(kind, value, unit_identity_id)


def _leg(
    value: int,
    component: int,
    role: str,
    *,
    direction: ProductCompositionDirection | None = None,
    magnitude: ProductCompositionMagnitude | None = None,
    ordinal: int | None = None,
) -> ProductCompositionLeg:
    return ProductCompositionLeg(
        leg_id=ProductCompositionLegId(_uuid(value)),
        component_identity_id=_identity(component),
        role=ProductCompositionRoleCode(role),
        magnitude=magnitude if magnitude is not None else _magnitude(),
        evidence_ref=_evidence(value),
        direction=direction,
        ordinal=ProductCompositionLegOrdinal(ordinal) if ordinal is not None else None,
    )


def _terms(
    legs: tuple[ProductCompositionLeg, ...],
    *,
    composition_class: ProductCompositionClass = ProductCompositionClass.BASKET,
    mode: ProductCompositionMode = ProductCompositionMode.UNORDERED_CANONICAL,
) -> ProductCompositionTerms:
    return ProductCompositionTerms(
        root_identity_id=_identity(9000),
        composition_class=composition_class,
        mode=mode,
        legs=legs,
        evidence_ref=_evidence(9000),
    )


def test_product_composition_class_set_is_exact() -> None:
    assert {value.value for value in ProductCompositionClass} == {
        "basket",
        "spread",
        "multi-leg",
    }


def test_product_composition_mode_set_is_exact() -> None:
    assert {value.value for value in ProductCompositionMode} == {
        "ordered-contractual",
        "unordered-canonical",
    }


def test_magnitude_kind_set_is_exact() -> None:
    assert {value.value for value in ProductCompositionMagnitudeKind} == {
        "ratio",
        "weight",
        "quantity",
    }


@pytest.mark.parametrize("composition_class", tuple(ProductCompositionClass))
@pytest.mark.parametrize("mode", tuple(ProductCompositionMode))
def test_product_class_does_not_imply_order_mode(
    composition_class: ProductCompositionClass,
    mode: ProductCompositionMode,
) -> None:
    legs = (
        _leg(1, 1, "primary", ordinal=1),
        _leg(2, 2, "secondary", ordinal=2),
    )
    if mode is ProductCompositionMode.UNORDERED_CANONICAL:
        legs = (
            _leg(1, 1, "primary"),
            _leg(2, 2, "secondary"),
        )
    terms = _terms(legs, composition_class=composition_class, mode=mode)
    assert terms.composition_class is composition_class
    assert terms.mode is mode


def test_ordered_contractual_canonicalizes_by_ordinal() -> None:
    second = _leg(2, 20, "secondary", ordinal=2)
    first = _leg(1, 10, "primary", ordinal=1)
    terms = _terms(
        (second, first),
        mode=ProductCompositionMode.ORDERED_CONTRACTUAL,
    )
    assert tuple(
        leg.ordinal.value for leg in terms.legs if leg.ordinal is not None
    ) == (1, 2)


def test_unordered_canonical_ignores_caller_order() -> None:
    alpha = _leg(999, 10, "alpha")
    beta = _leg(1, 10, "beta")
    first = _terms((beta, alpha))
    second = _terms((alpha, beta))

    assert first.logical_values() == second.logical_values()
    assert tuple(leg.role.value for leg in first.legs) == ("alpha", "beta")


def test_unordered_sort_does_not_use_local_leg_id_or_evidence() -> None:
    alpha = _leg(9999, 10, "alpha")
    beta = _leg(1, 10, "beta")
    terms = _terms((beta, alpha))
    assert terms.legs[0].role.value == "alpha"
    assert terms.legs[0].leg_id.value == _uuid(9999)


def test_ordered_requires_ordinal_on_every_leg() -> None:
    with pytest.raises(
        ProductCompositionValidationError,
        match="requires an ordinal on every leg",
    ):
        _terms(
            (_leg(1, 1, "a", ordinal=1), _leg(2, 2, "b")),
            mode=ProductCompositionMode.ORDERED_CONTRACTUAL,
        )


def test_unordered_rejects_any_ordinal() -> None:
    with pytest.raises(
        ProductCompositionValidationError,
        match="must not carry leg ordinals",
    ):
        _terms((_leg(1, 1, "a", ordinal=1), _leg(2, 2, "b")))


def test_ordered_rejects_duplicate_ordinals() -> None:
    with pytest.raises(
        ProductCompositionValidationError,
        match="ordinals must be unique",
    ):
        _terms(
            (_leg(1, 1, "a", ordinal=1), _leg(2, 2, "b", ordinal=1)),
            mode=ProductCompositionMode.ORDERED_CONTRACTUAL,
        )


def test_ordered_rejects_noncontiguous_ordinals() -> None:
    with pytest.raises(
        ProductCompositionValidationError,
        match="contiguous from 1",
    ):
        _terms(
            (_leg(1, 1, "a", ordinal=1), _leg(2, 2, "b", ordinal=3)),
            mode=ProductCompositionMode.ORDERED_CONTRACTUAL,
        )


def test_ordinal_rejects_bool_laundering() -> None:
    with pytest.raises(ProductCompositionValidationError, match="exact int"):
        ProductCompositionLegOrdinal(True)


def test_terms_require_exact_tuple_with_at_least_two_legs() -> None:
    with pytest.raises(ProductCompositionValidationError, match="exact tuple"):
        ProductCompositionTerms(
            root_identity_id=_identity(9000),
            composition_class=ProductCompositionClass.BASKET,
            mode=ProductCompositionMode.UNORDERED_CANONICAL,
            legs=cast(
                tuple[ProductCompositionLeg, ...],
                [_leg(1, 1, "a"), _leg(2, 2, "b")],
            ),
            evidence_ref=_evidence(9000),
        )

    with pytest.raises(ProductCompositionValidationError, match="at least two legs"):
        _terms((_leg(1, 1, "a"),))


def test_root_identity_cannot_be_component() -> None:
    root_leg = ProductCompositionLeg(
        leg_id=ProductCompositionLegId(_uuid(1)),
        component_identity_id=_identity(9000),
        role=ProductCompositionRoleCode("root"),
        magnitude=_magnitude(),
        evidence_ref=_evidence(1),
    )
    with pytest.raises(
        ProductCompositionValidationError,
        match="must not reference itself",
    ):
        _terms((root_leg, _leg(2, 2, "other")))


def test_leg_ids_must_be_unique() -> None:
    first = _leg(1, 1, "a")
    second = ProductCompositionLeg(
        leg_id=first.leg_id,
        component_identity_id=_identity(2),
        role=ProductCompositionRoleCode("b"),
        magnitude=_magnitude(),
        evidence_ref=_evidence(2),
    )
    with pytest.raises(
        ProductCompositionValidationError,
        match="leg ids must be unique",
    ):
        _terms((first, second))


def test_exact_semantic_duplicate_is_rejected_despite_distinct_local_material() -> None:
    first = _leg(
        1,
        10,
        "constituent",
        direction=ProductCompositionDirection.LONG,
        magnitude=_magnitude(ProductCompositionMagnitudeKind.WEIGHT, Decimal("0.5")),
    )
    second = _leg(
        2,
        10,
        "constituent",
        direction=ProductCompositionDirection.LONG,
        magnitude=_magnitude(ProductCompositionMagnitudeKind.WEIGHT, Decimal("0.500")),
    )
    with pytest.raises(
        ProductCompositionValidationError,
        match="semantic legs must be unique",
    ):
        _terms((first, second))


def test_same_component_is_allowed_when_semantic_role_differs() -> None:
    terms = _terms(
        (
            _leg(1, 10, "receive"),
            _leg(2, 10, "deliver"),
        ),
        composition_class=ProductCompositionClass.SPREAD,
    )
    assert len(terms.legs) == 2


def test_same_component_is_allowed_when_direction_differs() -> None:
    terms = _terms(
        (
            _leg(1, 10, "exposure", direction=ProductCompositionDirection.LONG),
            _leg(2, 10, "exposure", direction=ProductCompositionDirection.SHORT),
        ),
        composition_class=ProductCompositionClass.MULTI_LEG,
    )
    assert len(terms.legs) == 2


@pytest.mark.parametrize(
    "kind",
    (
        ProductCompositionMagnitudeKind.RATIO,
        ProductCompositionMagnitudeKind.WEIGHT,
    ),
)
def test_ratio_and_weight_must_not_carry_unit(
    kind: ProductCompositionMagnitudeKind,
) -> None:
    with pytest.raises(
        ProductCompositionValidationError,
        match="must not carry a unit",
    ):
        _magnitude(kind, unit_identity_id=_identity(500))


def test_quantity_can_be_dimensionless_or_unitful() -> None:
    dimensionless = _magnitude(ProductCompositionMagnitudeKind.QUANTITY, Decimal("2"))
    unitful = _magnitude(
        ProductCompositionMagnitudeKind.QUANTITY,
        Decimal("3"),
        unit_identity_id=_identity(500),
    )
    assert dimensionless.logical_values()[-1] is None
    assert unitful.logical_values()[-1] == (str(_uuid(500)),)


@pytest.mark.parametrize("value", (Decimal("0"), Decimal("-1")))
def test_magnitude_must_be_positive(value: Decimal) -> None:
    with pytest.raises(ProductCompositionValidationError, match="must be positive"):
        _magnitude(value=value)


@pytest.mark.parametrize("value", (Decimal("NaN"), Decimal("Infinity")))
def test_magnitude_must_be_finite(value: Decimal) -> None:
    with pytest.raises(ProductCompositionValidationError, match="must be finite"):
        _magnitude(value=value)


def test_magnitude_rejects_float_and_bool() -> None:
    with pytest.raises(ProductCompositionValidationError, match="exact Decimal"):
        ProductCompositionMagnitude(
            ProductCompositionMagnitudeKind.WEIGHT,
            cast(Decimal, 1.0),
        )
    with pytest.raises(ProductCompositionValidationError, match="exact Decimal"):
        ProductCompositionMagnitude(
            ProductCompositionMagnitudeKind.WEIGHT,
            cast(Decimal, True),
        )


def test_uuid_subclass_laundering_is_rejected() -> None:
    bad = EconomicIdentityId(_uuid(1))
    object.__setattr__(bad, "value", UUIDSubclass(str(_uuid(1))))
    with pytest.raises(ProductCompositionValidationError, match="exact UUID"):
        ProductCompositionLeg(
            leg_id=ProductCompositionLegId(_uuid(1)),
            component_identity_id=bad,
            role=ProductCompositionRoleCode("component"),
            magnitude=_magnitude(),
            evidence_ref=_evidence(1),
        )


def test_str_subclass_laundering_is_rejected() -> None:
    role = ProductCompositionRoleCode("component")
    object.__setattr__(role, "value", StrSubclass("component"))
    with pytest.raises(ProductCompositionValidationError, match="exact str"):
        ProductCompositionLeg(
            leg_id=ProductCompositionLegId(_uuid(2)),
            component_identity_id=_identity(2),
            role=role,
            magnitude=_magnitude(),
            evidence_ref=_evidence(2),
        )


def test_post_construction_component_uuid_corruption_is_rejected() -> None:
    leg = _leg(1, 1, "a")
    terms = _terms((leg, _leg(2, 2, "b")))
    object.__setattr__(leg.component_identity_id, "value", "bad")
    with pytest.raises(ProductCompositionValidationError, match="exact UUID"):
        terms.logical_values()


def test_post_construction_role_corruption_is_rejected() -> None:
    leg = _leg(1, 1, "a")
    terms = _terms((leg, _leg(2, 2, "b")))
    object.__setattr__(leg.role, "value", 123)
    with pytest.raises(ProductCompositionValidationError, match="exact str"):
        terms.logical_values()


def test_post_construction_magnitude_corruption_is_rejected() -> None:
    leg = _leg(1, 1, "a")
    terms = _terms((leg, _leg(2, 2, "b")))
    object.__setattr__(leg.magnitude, "value", 1.0)
    with pytest.raises(ProductCompositionValidationError, match="exact Decimal"):
        terms.logical_values()


def test_post_construction_magnitude_kind_corruption_is_rejected() -> None:
    leg = _leg(1, 1, "a")
    terms = _terms((leg, _leg(2, 2, "b")))
    object.__setattr__(leg.magnitude, "kind", "weight")
    with pytest.raises(
        ProductCompositionValidationError,
        match="exact ProductCompositionMagnitudeKind",
    ):
        terms.logical_values()


def test_post_construction_ordinal_corruption_is_rejected() -> None:
    leg = _leg(1, 1, "a", ordinal=1)
    terms = _terms(
        (leg, _leg(2, 2, "b", ordinal=2)),
        mode=ProductCompositionMode.ORDERED_CONTRACTUAL,
    )
    assert leg.ordinal is not None
    object.__setattr__(leg.ordinal, "value", True)
    with pytest.raises(ProductCompositionValidationError, match="exact int"):
        terms.logical_values()


def test_post_construction_unit_uuid_corruption_is_rejected() -> None:
    magnitude = _magnitude(
        ProductCompositionMagnitudeKind.QUANTITY,
        Decimal("2"),
        unit_identity_id=_identity(500),
    )
    leg = _leg(1, 1, "a", magnitude=magnitude)
    terms = _terms((leg, _leg(2, 2, "b")))
    assert magnitude.unit_identity_id is not None
    object.__setattr__(magnitude.unit_identity_id, "value", "bad")
    with pytest.raises(ProductCompositionValidationError, match="exact UUID"):
        terms.logical_values()


def test_post_construction_direction_laundering_is_rejected() -> None:
    leg = _leg(1, 1, "a", direction=ProductCompositionDirection.LONG)
    terms = _terms((leg, _leg(2, 2, "b")))
    object.__setattr__(leg, "direction", "long")
    with pytest.raises(
        ProductCompositionValidationError,
        match="exact ProductCompositionDirection",
    ):
        terms.logical_values()


def test_extreme_positive_decimal_uses_compact_representation() -> None:
    terms = _terms(
        (
            _leg(
                1,
                1,
                "a",
                magnitude=_magnitude(
                    ProductCompositionMagnitudeKind.QUANTITY,
                    Decimal("1E+100000000"),
                ),
            ),
            _leg(2, 2, "b"),
        )
    )
    legs_values = _tuple_value(terms.logical_values()[4])
    first_leg_values = _tuple_value(legs_values[0])
    magnitude_values = _tuple_value(first_leg_values[4])
    assert magnitude_values[1] == "1e+100000000"


def test_extreme_negative_decimal_uses_compact_representation() -> None:
    terms = _terms(
        (
            _leg(
                1,
                1,
                "a",
                magnitude=_magnitude(
                    ProductCompositionMagnitudeKind.RATIO,
                    Decimal("1E-100000000"),
                ),
            ),
            _leg(2, 2, "b"),
        )
    )
    legs_values = _tuple_value(terms.logical_values()[4])
    first_leg_values = _tuple_value(legs_values[0])
    magnitude_values = _tuple_value(first_leg_values[4])
    assert magnitude_values[1] == "1e-100000000"


def test_logical_values_schema_is_versioned() -> None:
    terms = _terms((_leg(1, 1, "a"), _leg(2, 2, "b")))
    assert terms.logical_values()[0] == "product-composition.v1"


def test_contract_has_no_implicit_clock_or_operational_authority() -> None:
    source = Path("src/qore/infrastructure/product_composition_semantics.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "datetime.now",
        "date.today",
        "uuid4(",
        "requests.",
        "httpx.",
        "rebalance",
        "route_order",
        "submit_order",
        "place_order",
        "send_order",
        "execute_trade",
        "settle_trade",
    )
    for token in forbidden:
        assert token not in source
