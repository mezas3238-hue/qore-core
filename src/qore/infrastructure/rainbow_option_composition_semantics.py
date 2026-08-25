from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from typing import cast

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
        self.option.__post_init__()

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
