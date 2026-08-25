from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import cast
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class ProductCompositionError(InfrastructureError):
    """Base error for product-specific composition semantics."""

    __slots__ = ()


class ProductCompositionValidationError(ProductCompositionError):
    """Violation of one product-composition invariant."""

    __slots__ = ()


def _fail(message: str) -> None:
    raise ProductCompositionValidationError(message)


def _exact[T](value: object, expected_type: type[T], *, field_name: str) -> T:
    if type(value) is not expected_type:
        _fail(f"{field_name} must be exact {expected_type.__name__}")
    return cast(T, value)


def _require_uuid(value: object, *, field_name: str) -> UUID:
    return _exact(value, UUID, field_name=field_name)


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
    decimal_tuple = value.as_tuple()
    digits_list = list(decimal_tuple.digits)
    if not any(digits_list):
        return "0"

    exponent = _exact(
        decimal_tuple.exponent,
        int,
        field_name="finite Decimal exponent",
    )
    while len(digits_list) > 1 and digits_list[-1] == 0:
        digits_list.pop()
        exponent += 1

    digits = "".join(str(digit) for digit in digits_list)
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


def _identity_values(
    value: EconomicIdentityId,
    *,
    field_name: str,
) -> tuple[str, ...]:
    identity_id = _require_identity_id(value, field_name=field_name)
    return (str(identity_id.value),)


@dataclass(frozen=True, slots=True)
class ProductCompositionLegId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="product composition leg id")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ProductCompositionEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="product composition evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ProductCompositionRoleCode:
    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="product composition role code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ProductCompositionLegOrdinal:
    value: int

    def __post_init__(self) -> None:
        ordinal = _exact(
            self.value,
            int,
            field_name="product composition leg ordinal",
        )
        if ordinal <= 0:
            _fail("product composition leg ordinal must be positive")

    def logical_values(self) -> tuple[int, ...]:
        self.__post_init__()
        return (self.value,)


class ProductCompositionClass(StrEnum):
    BASKET = "basket"
    SPREAD = "spread"
    MULTI_LEG = "multi-leg"


class ProductCompositionMode(StrEnum):
    ORDERED_CONTRACTUAL = "ordered-contractual"
    UNORDERED_CANONICAL = "unordered-canonical"


class ProductCompositionDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class ProductCompositionMagnitudeKind(StrEnum):
    RATIO = "ratio"
    WEIGHT = "weight"
    QUANTITY = "quantity"


@dataclass(frozen=True, slots=True)
class ProductCompositionMagnitude:
    kind: ProductCompositionMagnitudeKind
    value: Decimal
    unit_identity_id: EconomicIdentityId | None = None

    def __post_init__(self) -> None:
        kind = _exact(
            self.kind,
            ProductCompositionMagnitudeKind,
            field_name="product composition magnitude kind",
        )
        _require_decimal(
            self.value,
            field_name="product composition magnitude value",
            positive=True,
        )
        if self.unit_identity_id is not None:
            _require_identity_id(
                self.unit_identity_id,
                field_name="product composition magnitude unit identity",
            )
        if (
            kind
            in {
                ProductCompositionMagnitudeKind.RATIO,
                ProductCompositionMagnitudeKind.WEIGHT,
            }
            and self.unit_identity_id is not None
        ):
            _fail("ratio/weight product composition magnitude must not carry a unit")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.kind.value,
            _canonical_decimal(self.value),
            _identity_values(
                self.unit_identity_id,
                field_name="product composition magnitude unit identity",
            )
            if self.unit_identity_id is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class ProductCompositionLeg:
    leg_id: ProductCompositionLegId
    component_identity_id: EconomicIdentityId
    role: ProductCompositionRoleCode
    magnitude: ProductCompositionMagnitude
    evidence_ref: ProductCompositionEvidenceRef
    direction: ProductCompositionDirection | None = None
    ordinal: ProductCompositionLegOrdinal | None = None

    def __post_init__(self) -> None:
        leg_id = _exact(
            self.leg_id,
            ProductCompositionLegId,
            field_name="product composition leg_id",
        )
        leg_id.__post_init__()
        _require_identity_id(
            self.component_identity_id,
            field_name="product composition component identity",
        )
        role = _exact(
            self.role,
            ProductCompositionRoleCode,
            field_name="product composition role",
        )
        role.__post_init__()
        magnitude = _exact(
            self.magnitude,
            ProductCompositionMagnitude,
            field_name="product composition magnitude",
        )
        magnitude.__post_init__()
        evidence_ref = _exact(
            self.evidence_ref,
            ProductCompositionEvidenceRef,
            field_name="product composition leg evidence_ref",
        )
        evidence_ref.__post_init__()
        if self.direction is not None:
            _exact(
                self.direction,
                ProductCompositionDirection,
                field_name="product composition direction",
            )
        if self.ordinal is not None:
            ordinal = _exact(
                self.ordinal,
                ProductCompositionLegOrdinal,
                field_name="product composition ordinal",
            )
            ordinal.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.leg_id.logical_values(),
            _identity_values(
                self.component_identity_id,
                field_name="product composition component identity",
            ),
            self.role.logical_values(),
            self.direction.value if self.direction is not None else None,
            self.magnitude.logical_values(),
            self.ordinal.logical_values() if self.ordinal is not None else None,
            self.evidence_ref.logical_values(),
        )


def _semantic_sort_key(leg: ProductCompositionLeg) -> tuple[str, ...]:
    leg.__post_init__()
    unit_value = (
        str(leg.magnitude.unit_identity_id.value)
        if leg.magnitude.unit_identity_id is not None
        else ""
    )
    return (
        str(leg.component_identity_id.value),
        leg.role.value,
        leg.direction.value if leg.direction is not None else "",
        leg.magnitude.kind.value,
        _canonical_decimal(leg.magnitude.value),
        unit_value,
    )


@dataclass(frozen=True, slots=True)
class ProductCompositionTerms:
    root_identity_id: EconomicIdentityId
    composition_class: ProductCompositionClass
    mode: ProductCompositionMode
    legs: tuple[ProductCompositionLeg, ...]
    evidence_ref: ProductCompositionEvidenceRef

    def __post_init__(self) -> None:
        root_identity_id = _require_identity_id(
            self.root_identity_id,
            field_name="product composition root identity",
        )
        _exact(
            self.composition_class,
            ProductCompositionClass,
            field_name="product composition class",
        )
        mode = _exact(
            self.mode,
            ProductCompositionMode,
            field_name="product composition mode",
        )
        legs = _exact(
            self.legs,
            tuple,
            field_name="product composition legs",
        )
        if len(legs) < 2:
            _fail("product composition legs must contain at least two legs")

        validated_legs: list[ProductCompositionLeg] = []
        for value in legs:
            leg = _exact(
                value,
                ProductCompositionLeg,
                field_name="product composition leg",
            )
            leg.__post_init__()
            if leg.component_identity_id == root_identity_id:
                _fail(
                    "product composition root must not reference itself as a component"
                )
            validated_legs.append(leg)

        leg_ids = tuple(leg.leg_id.value for leg in validated_legs)
        if len(set(leg_ids)) != len(leg_ids):
            _fail("product composition leg ids must be unique")

        semantic_keys = tuple(_semantic_sort_key(leg) for leg in validated_legs)
        if len(set(semantic_keys)) != len(semantic_keys):
            _fail("product composition semantic legs must be unique")

        if mode is ProductCompositionMode.ORDERED_CONTRACTUAL:
            if any(leg.ordinal is None for leg in validated_legs):
                _fail("ordered product composition requires an ordinal on every leg")
            ordinals = tuple(
                cast(ProductCompositionLegOrdinal, leg.ordinal).value
                for leg in validated_legs
            )
            if len(set(ordinals)) != len(ordinals):
                _fail("ordered product composition ordinals must be unique")
            ordered = tuple(
                sorted(
                    validated_legs,
                    key=lambda leg: cast(
                        ProductCompositionLegOrdinal,
                        leg.ordinal,
                    ).value,
                )
            )
            actual = tuple(
                cast(ProductCompositionLegOrdinal, leg.ordinal).value for leg in ordered
            )
            expected = tuple(range(1, len(ordered) + 1))
            if actual != expected:
                _fail("ordered product composition ordinals must be contiguous from 1")
        else:
            if any(leg.ordinal is not None for leg in validated_legs):
                _fail("unordered product composition must not carry leg ordinals")
            ordered = tuple(sorted(validated_legs, key=_semantic_sort_key))

        object.__setattr__(self, "legs", ordered)
        evidence_ref = _exact(
            self.evidence_ref,
            ProductCompositionEvidenceRef,
            field_name="product composition evidence_ref",
        )
        evidence_ref.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "product-composition.v1",
            _identity_values(
                self.root_identity_id,
                field_name="product composition root identity",
            ),
            self.composition_class.value,
            self.mode.value,
            tuple(leg.logical_values() for leg in self.legs),
            self.evidence_ref.logical_values(),
        )
