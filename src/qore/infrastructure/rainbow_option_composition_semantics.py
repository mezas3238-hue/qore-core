from __future__ import annotations

import types
import typing
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from re import fullmatch
from typing import cast, get_args, get_origin, get_type_hints

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeEvidenceRef,
    OptionContractTerms,
)
from qore.infrastructure.product_composition_semantics import (
    ProductCompositionClass,
    ProductCompositionTerms,
)
from qore.kernel.errors import InfrastructureError


class RainbowOptionCompositionError(InfrastructureError):
    """Base error for bounded rainbow option composition semantics."""

    __slots__ = ()


class RainbowOptionCompositionValidationError(RainbowOptionCompositionError):
    """Violation of one rainbow option composition invariant."""

    __slots__ = ()


def _fail(message: str) -> None:
    raise RainbowOptionCompositionValidationError(message)


def _require_code(value: object, *, field_name: str) -> str:
    if type(value) is not str:
        _fail(f"{field_name} must be exact str")
    text = cast(str, value)
    if (
        len(text) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", text) is None
    ):
        _fail(f"{field_name} must use canonical lowercase code syntax")
    return text


def _declared_dataclass_types(annotation: object) -> tuple[type[object], ...]:
    if isinstance(annotation, type) and is_dataclass(annotation):
        return (annotation,)
    origin = get_origin(annotation)
    if origin in (types.UnionType, typing.Union):
        declared: list[type[object]] = []
        for member in get_args(annotation):
            declared.extend(_declared_dataclass_types(member))
        return tuple(declared)
    return ()


def _tuple_item_annotations(annotation: object, *, length: int) -> tuple[object, ...]:
    if get_origin(annotation) is not tuple:
        return ()
    members = get_args(annotation)
    if len(members) == 2 and members[1] is Ellipsis:
        return (members[0],) * length
    if len(members) == length:
        return members
    return ()


def _require_exact_declared_dataclass_type(
    value: object,
    *,
    annotation: object,
    field_path: str,
) -> None:
    declared = _declared_dataclass_types(annotation)
    if not declared or type(value) not in declared:
        _fail(f"{field_path} must use exact declared dataclass type")


def _revalidate_dataclass_tree(
    value: object,
    *,
    visited: set[int] | None = None,
    path: str = "option",
) -> None:
    """Re-run exact nested dataclass owners without accepting subclass laundering."""

    if not is_dataclass(value) or isinstance(value, type):
        return
    seen = set() if visited is None else visited
    marker = id(value)
    if marker in seen:
        return
    seen.add(marker)

    type_hints = get_type_hints(type(value))
    for dataclass_field in fields(value):
        child = getattr(value, dataclass_field.name)
        annotation = type_hints[dataclass_field.name]
        child_path = f"{path}.{dataclass_field.name}"
        if is_dataclass(child) and not isinstance(child, type):
            _require_exact_declared_dataclass_type(
                child,
                annotation=annotation,
                field_path=child_path,
            )
            _revalidate_dataclass_tree(child, visited=seen, path=child_path)
        elif type(child) is tuple:
            item_annotations = _tuple_item_annotations(annotation, length=len(child))
            for index, item in enumerate(child):
                if is_dataclass(item) and not isinstance(item, type):
                    item_annotation = (
                        item_annotations[index]
                        if index < len(item_annotations)
                        else object
                    )
                    item_path = f"{child_path}[{index}]"
                    _require_exact_declared_dataclass_type(
                        item,
                        annotation=item_annotation,
                        field_path=item_path,
                    )
                    _revalidate_dataclass_tree(item, visited=seen, path=item_path)

    post_init = getattr(value, "__post_init__", None)
    if callable(post_init):
        post_init()


class RainbowOptionSelectionKind(StrEnum):
    """Contractual best/worst selection; never a current constituent result."""

    BEST_OF = "best-of"
    WORST_OF = "worst-of"


@dataclass(frozen=True, slots=True)
class RainbowPerformanceRuleCode:
    """Opaque governed rule for comparing constituent performance."""

    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="rainbow performance rule code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class RainbowOptionCompositionQualification:
    """Bind one UMI-05 option to one UNR-024 basket and a best/worst rule."""

    option: OptionContractTerms
    composition: ProductCompositionTerms
    selection: RainbowOptionSelectionKind
    performance_rule: RainbowPerformanceRuleCode
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if type(self.option) is not OptionContractTerms:
            _fail("rainbow option must be exact OptionContractTerms")
        _revalidate_dataclass_tree(self.option)

        if type(self.composition) is not ProductCompositionTerms:
            _fail("rainbow composition must be exact ProductCompositionTerms")
        self.composition.__post_init__()
        if self.composition.composition_class is not ProductCompositionClass.BASKET:
            _fail("rainbow best/worst composition must be BASKET")
        if self.option.underlying_identity_id != self.composition.root_identity_id:
            _fail("rainbow option underlying must equal composition root identity")

        if type(self.selection) is not RainbowOptionSelectionKind:
            _fail("rainbow selection must be exact RainbowOptionSelectionKind")

        if type(self.performance_rule) is not RainbowPerformanceRuleCode:
            _fail("rainbow performance rule must be exact RainbowPerformanceRuleCode")
        self.performance_rule.__post_init__()

        if type(self.evidence_ref) is not DerivativeEvidenceRef:
            _fail("rainbow evidence must be exact DerivativeEvidenceRef")
        self.evidence_ref.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "rainbow-option-composition.v1",
            self.option.logical_values(),
            self.composition.logical_values(),
            self.selection.value,
            self.performance_rule.logical_values(),
            self.evidence_ref.logical_values(),
        )
