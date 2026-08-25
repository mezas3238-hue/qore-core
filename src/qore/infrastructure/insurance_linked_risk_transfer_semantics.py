"""Static insurance-linked risk-transfer semantics for UMI13-UNR-020.

This D04 owner qualifies transferred insurance risk, contractual trigger terms,
and declarative economic effects. It never observes/resolves triggers, adjusts
claims, runs actuarial models, values instruments, maps providers, executes,
settles, mutates economic state, or authorizes Production.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import ClassVar, Never
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
)
from qore.kernel.errors import InfrastructureError

_ALLOWED_ROOT_FAMILIES = frozenset(
    {
        "fixed-income-credit",
        "structured-hybrid-products",
        "forwards-swaps-otc",
    }
)
_CODE_PATTERN = r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*"


class InsuranceLinkedRiskTransferSemanticsError(InfrastructureError):
    __slots__ = ()


class InsuranceLinkedRiskTransferValidationError(
    InsuranceLinkedRiskTransferSemanticsError
):
    __slots__ = ()


def _fail(message: str) -> Never:
    raise InsuranceLinkedRiskTransferValidationError(message)


def _uuid(value: object, name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{name} must be exact UUID")


def _identity_id(value: object, name: str) -> None:
    if type(value) is not EconomicIdentityId:
        _fail(f"{name} must be exact EconomicIdentityId")
    _uuid(value.value, f"{name}.value")


def _date(value: object, name: str) -> None:
    if type(value) is not date:
        _fail(f"{name} must be exact date")


def _positive_int(value: object, name: str) -> None:
    if type(value) is not int or value <= 0:
        _fail(f"{name} must be positive exact int")


def _decimal(value: object, name: str, *, non_negative: bool = False) -> None:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{name} must be exact finite Decimal")
    if non_negative and value < 0:
        _fail(f"{name} must be non-negative")


def _canonical_decimal(value: Decimal) -> str:
    parts = value.as_tuple()
    digits = list(parts.digits)
    if not any(digits):
        return "0"
    exponent = int(parts.exponent)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    text = "".join(str(digit) for digit in digits)
    sign = "-" if parts.sign else ""
    adjusted = exponent + len(digits) - 1
    mantissa = text[0] + ("." + text[1:] if len(text) > 1 else "")
    compact = f"{sign}{mantissa}e{'+' if adjusted >= 0 else ''}{adjusted}"
    if exponent >= 0:
        fixed_len = len(sign) + len(text) + exponent
        fixed = text + ("0" * exponent)
    else:
        point = len(text) + exponent
        fixed_len = (
            len(sign) + len(text) + 1
            if point > 0
            else len(sign) + 2 + (-point) + len(text)
        )
        fixed = (
            text[:point] + "." + text[point:]
            if point > 0
            else "0." + ("0" * (-point)) + text
        )
    return compact if fixed_len > len(compact) + 1 else sign + fixed


@dataclass(frozen=True, slots=True)
class _UuidValue:
    value: UUID
    _label: ClassVar[str] = "UUID value"

    def __post_init__(self) -> None:
        _uuid(self.value, self._label)

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class InsuranceLinkedRiskTransferQualificationId(_UuidValue):
    _label: ClassVar[str] = "qualification id"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedEvidenceRef(_UuidValue):
    _label: ClassVar[str] = "evidence ref"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedRiskSubjectRef(_UuidValue):
    """Opaque contractual risk subject/book reference; not legal identity."""

    _label: ClassVar[str] = "risk subject ref"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedRiskMeasureReferenceId(_UuidValue):
    """Opaque contractual measure/index reference; never a data-fetch key."""

    _label: ClassVar[str] = "risk measure reference id"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerId(_UuidValue):
    _label: ClassVar[str] = "trigger id"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerComponentId(_UuidValue):
    _label: ClassVar[str] = "trigger component id"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedEconomicEffectId(_UuidValue):
    _label: ClassVar[str] = "economic effect id"


@dataclass(frozen=True, slots=True)
class _CodeValue:
    value: str
    _label: ClassVar[str] = "code"

    def __post_init__(self) -> None:
        valid = (
            type(self.value) is str
            and bool(self.value)
            and len(self.value) <= 96
            and fullmatch(_CODE_PATTERN, self.value) is not None
        )
        if not valid:
            _fail(f"{self._label} must use canonical lowercase code syntax")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class InsuranceLinkedRiskTypeCode(_CodeValue):
    _label: ClassVar[str] = "risk type code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTransferFormCode(_CodeValue):
    _label: ClassVar[str] = "transfer form code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerBasisCode(_CodeValue):
    _label: ClassVar[str] = "trigger basis code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerMetricCode(_CodeValue):
    _label: ClassVar[str] = "trigger metric code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerSourceCode(_CodeValue):
    _label: ClassVar[str] = "trigger source code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerRuleCode(_CodeValue):
    _label: ClassVar[str] = "trigger rule code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerCombinationRuleCode(_CodeValue):
    _label: ClassVar[str] = "trigger combination rule code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerUnitCode(_CodeValue):
    _label: ClassVar[str] = "trigger unit code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedEffectTargetCode(_CodeValue):
    _label: ClassVar[str] = "effect target code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedEffectActionCode(_CodeValue):
    _label: ClassVar[str] = "effect action code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedEffectRuleCode(_CodeValue):
    _label: ClassVar[str] = "effect rule code"


@dataclass(frozen=True, slots=True)
class InsuranceLinkedEffectUnitCode(_CodeValue):
    _label: ClassVar[str] = "effect unit code"


class InsuranceLinkedTriggerStructureKind(StrEnum):
    SINGLE = "single"
    HYBRID = "hybrid"


class InsuranceLinkedTriggerComparator(StrEnum):
    LESS_THAN = "less-than"
    LESS_THAN_OR_EQUAL = "less-than-or-equal"
    GREATER_THAN = "greater-than"
    GREATER_THAN_OR_EQUAL = "greater-than-or-equal"
    EQUAL = "equal"


def _exact(value: object, expected: type[object], name: str) -> None:
    if type(value) is not expected:
        _fail(f"{name} has invalid exact type")
    validator = getattr(value, "__post_init__", None)
    if not callable(validator):
        _fail(f"{name} has no validator")
    validator()


def _root_identity(value: object) -> None:
    if type(value) is not EconomicIdentity:
        _fail("instrument_identity must be exact EconomicIdentity")
    _identity_id(value.identity_id, "instrument_identity.identity_id")
    if type(value.kind) is not EconomicIdentityKind:
        _fail("instrument_identity.kind must be exact EconomicIdentityKind")
    if value.kind is not EconomicIdentityKind.TRADABLE_INSTRUMENT:
        _fail("insurance-linked root identity must be tradable instrument")
    if type(value.family) is not IdentityFamilyCode:
        _fail("instrument_identity.family has invalid exact type")
    if type(value.family.value) is not str:
        _fail("instrument_identity.family.value must be exact str")
    value.family.__post_init__()
    if value.family.value not in _ALLOWED_ROOT_FAMILIES:
        _fail("insurance-linked root family is outside UNR-020 scope")
    if type(value.construction) is not IdentityConstructionKind:
        _fail("instrument_identity.construction has invalid exact type")
    if value.construction is IdentityConstructionKind.CONTINUOUS_REFERENCE:
        _fail("tradable insurance-linked root cannot be continuous-reference")
    if type(value.evidence_ref) is not IdentityEvidenceRef:
        _fail("instrument_identity.evidence_ref has invalid exact type")
    _uuid(value.evidence_ref.value, "instrument_identity.evidence_ref.value")
    value.evidence_ref.__post_init__()


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerThreshold:
    value: Decimal
    unit: InsuranceLinkedTriggerUnitCode
    unit_identity_id: EconomicIdentityId | None = None

    def __post_init__(self) -> None:
        _decimal(self.value, "trigger threshold value")
        _exact(self.unit, InsuranceLinkedTriggerUnitCode, "trigger threshold unit")
        if self.unit_identity_id is not None:
            _identity_id(self.unit_identity_id, "trigger threshold unit_identity_id")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            _canonical_decimal(self.value),
            self.unit.logical_values(),
            self.unit_identity_id.logical_values()
            if self.unit_identity_id is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerComponent:
    component_id: InsuranceLinkedTriggerComponentId
    basis: InsuranceLinkedTriggerBasisCode
    metric: InsuranceLinkedTriggerMetricCode
    measure_reference_id: InsuranceLinkedRiskMeasureReferenceId
    source: InsuranceLinkedTriggerSourceCode
    rule: InsuranceLinkedTriggerRuleCode
    evidence_ref: InsuranceLinkedEvidenceRef
    reference_identity_id: EconomicIdentityId | None = None
    threshold: InsuranceLinkedTriggerThreshold | None = None
    comparator: InsuranceLinkedTriggerComparator | None = None
    sequence_ordinal: int | None = None

    def __post_init__(self) -> None:
        _exact(self.component_id, InsuranceLinkedTriggerComponentId, "component_id")
        _exact(self.basis, InsuranceLinkedTriggerBasisCode, "trigger basis")
        _exact(self.metric, InsuranceLinkedTriggerMetricCode, "trigger metric")
        _exact(
            self.measure_reference_id,
            InsuranceLinkedRiskMeasureReferenceId,
            "measure reference",
        )
        _exact(self.source, InsuranceLinkedTriggerSourceCode, "trigger source")
        _exact(self.rule, InsuranceLinkedTriggerRuleCode, "trigger rule")
        _exact(self.evidence_ref, InsuranceLinkedEvidenceRef, "component evidence")
        if self.reference_identity_id is not None:
            _identity_id(self.reference_identity_id, "reference_identity_id")
        if self.sequence_ordinal is not None:
            _positive_int(self.sequence_ordinal, "sequence_ordinal")
        if self.threshold is None:
            if self.comparator is not None:
                _fail("comparator requires explicit threshold")
        else:
            _exact(self.threshold, InsuranceLinkedTriggerThreshold, "threshold")
            if type(self.comparator) is not InsuranceLinkedTriggerComparator:
                _fail("threshold requires exact comparator")

    def semantic_key(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.basis.value,
            self.metric.value,
            str(self.measure_reference_id.value),
            str(self.reference_identity_id.value)
            if self.reference_identity_id is not None
            else None,
            self.source.value,
            self.rule.value,
            self.threshold.logical_values() if self.threshold is not None else None,
            self.comparator.value if self.comparator is not None else None,
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "insurance-linked-trigger-component",
            self.component_id.logical_values(),
            self.basis.logical_values(),
            self.metric.logical_values(),
            self.measure_reference_id.logical_values(),
            self.reference_identity_id.logical_values()
            if self.reference_identity_id is not None
            else None,
            self.source.logical_values(),
            self.rule.logical_values(),
            self.threshold.logical_values() if self.threshold is not None else None,
            self.comparator.value if self.comparator is not None else None,
            self.sequence_ordinal,
            self.evidence_ref.logical_values(),
        )


def _component_sort(value: InsuranceLinkedTriggerComponent) -> tuple[str, ...]:
    return (repr(value.semantic_key()), str(value.component_id.value))


def _sequence_sort(value: InsuranceLinkedTriggerComponent) -> tuple[int, str]:
    if value.sequence_ordinal is None:
        _fail("sequenced component lacks sequence_ordinal")
    return (value.sequence_ordinal, str(value.component_id.value))


@dataclass(frozen=True, slots=True)
class InsuranceLinkedTriggerStructure:
    trigger_id: InsuranceLinkedTriggerId
    kind: InsuranceLinkedTriggerStructureKind
    components: tuple[InsuranceLinkedTriggerComponent, ...]
    evidence_ref: InsuranceLinkedEvidenceRef
    combination_rule: InsuranceLinkedTriggerCombinationRuleCode | None = None

    def __post_init__(self) -> None:
        _exact(self.trigger_id, InsuranceLinkedTriggerId, "trigger_id")
        if type(self.kind) is not InsuranceLinkedTriggerStructureKind:
            _fail("trigger kind has invalid exact type")
        if type(self.components) is not tuple or not self.components:
            _fail("trigger components must be non-empty exact tuple")
        ids: set[UUID] = set()
        semantics: set[tuple[object, ...]] = set()
        ordinals: list[int | None] = []
        for component in self.components:
            _exact(component, InsuranceLinkedTriggerComponent, "trigger component")
            if component.component_id.value in ids:
                _fail("duplicate trigger component id")
            ids.add(component.component_id.value)
            key = component.semantic_key()
            if key in semantics:
                _fail("duplicate trigger component semantics")
            semantics.add(key)
            ordinals.append(component.sequence_ordinal)
        canonical: tuple[InsuranceLinkedTriggerComponent, ...]
        if self.kind is InsuranceLinkedTriggerStructureKind.SINGLE:
            if len(self.components) != 1:
                _fail("single trigger requires exactly one component")
            if self.combination_rule is not None or ordinals[0] is not None:
                _fail("single trigger cannot have combination rule or sequence")
            canonical = self.components
        else:
            if len(self.components) < 2:
                _fail("hybrid trigger requires at least two components")
            _exact(
                self.combination_rule,
                InsuranceLinkedTriggerCombinationRuleCode,
                "combination_rule",
            )
            has_sequence = [ordinal is not None for ordinal in ordinals]
            if any(has_sequence) and not all(has_sequence):
                _fail("hybrid sequence must be supplied for all or no components")
            if all(has_sequence):
                concrete = [ordinal for ordinal in ordinals if ordinal is not None]
                if len(concrete) != len(set(concrete)):
                    _fail("duplicate hybrid sequence ordinal")
                canonical = tuple(sorted(self.components, key=_sequence_sort))
            else:
                canonical = tuple(sorted(self.components, key=_component_sort))
        if self.components != canonical:
            object.__setattr__(self, "components", canonical)
        _exact(self.evidence_ref, InsuranceLinkedEvidenceRef, "trigger evidence")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "insurance-linked-trigger-structure",
            self.trigger_id.logical_values(),
            self.kind.value,
            tuple(component.logical_values() for component in self.components),
            self.combination_rule.logical_values()
            if self.combination_rule is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class InsuranceLinkedEffectMagnitude:
    value: Decimal
    unit: InsuranceLinkedEffectUnitCode
    unit_identity_id: EconomicIdentityId | None = None

    def __post_init__(self) -> None:
        _decimal(self.value, "effect magnitude", non_negative=True)
        _exact(self.unit, InsuranceLinkedEffectUnitCode, "effect unit")
        if self.unit_identity_id is not None:
            _identity_id(self.unit_identity_id, "effect unit_identity_id")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            _canonical_decimal(self.value),
            self.unit.logical_values(),
            self.unit_identity_id.logical_values()
            if self.unit_identity_id is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class InsuranceLinkedEconomicEffect:
    effect_id: InsuranceLinkedEconomicEffectId
    target: InsuranceLinkedEffectTargetCode
    action: InsuranceLinkedEffectActionCode
    rule: InsuranceLinkedEffectRuleCode
    evidence_ref: InsuranceLinkedEvidenceRef
    fixed_magnitude: InsuranceLinkedEffectMagnitude | None = None

    def __post_init__(self) -> None:
        _exact(self.effect_id, InsuranceLinkedEconomicEffectId, "effect_id")
        _exact(self.target, InsuranceLinkedEffectTargetCode, "effect target")
        _exact(self.action, InsuranceLinkedEffectActionCode, "effect action")
        _exact(self.rule, InsuranceLinkedEffectRuleCode, "effect rule")
        _exact(self.evidence_ref, InsuranceLinkedEvidenceRef, "effect evidence")
        if self.fixed_magnitude is not None:
            _exact(self.fixed_magnitude, InsuranceLinkedEffectMagnitude, "magnitude")

    def semantic_key(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.target.value,
            self.action.value,
            self.rule.value,
            self.fixed_magnitude.logical_values()
            if self.fixed_magnitude is not None
            else None,
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "insurance-linked-economic-effect",
            self.effect_id.logical_values(),
            self.target.logical_values(),
            self.action.logical_values(),
            self.rule.logical_values(),
            self.fixed_magnitude.logical_values()
            if self.fixed_magnitude is not None
            else None,
            self.evidence_ref.logical_values(),
        )


def _effect_sort(value: InsuranceLinkedEconomicEffect) -> tuple[str, str]:
    return (repr(value.semantic_key()), str(value.effect_id.value))


@dataclass(frozen=True, slots=True)
class InsuranceLinkedRiskTransferTerms:
    """One static insurance-linked risk-transfer qualification."""

    qualification_id: InsuranceLinkedRiskTransferQualificationId
    instrument_identity: EconomicIdentity
    risk_types: tuple[InsuranceLinkedRiskTypeCode, ...]
    transfer_form: InsuranceLinkedTransferFormCode
    risk_subjects: tuple[InsuranceLinkedRiskSubjectRef, ...]
    trigger: InsuranceLinkedTriggerStructure
    effects: tuple[InsuranceLinkedEconomicEffect, ...]
    evidence_ref: InsuranceLinkedEvidenceRef
    effective_from: date | None = None
    effective_until: date | None = None

    def __post_init__(self) -> None:
        _exact(
            self.qualification_id,
            InsuranceLinkedRiskTransferQualificationId,
            "qualification_id",
        )
        _root_identity(self.instrument_identity)
        if type(self.risk_types) is not tuple or not self.risk_types:
            _fail("risk_types must be non-empty exact tuple")
        risk_codes: set[str] = set()
        for risk_type in self.risk_types:
            _exact(risk_type, InsuranceLinkedRiskTypeCode, "risk type")
            if risk_type.value in risk_codes:
                _fail("duplicate insurance-linked risk type")
            risk_codes.add(risk_type.value)
        canonical_risks = tuple(sorted(self.risk_types, key=lambda item: item.value))
        if self.risk_types != canonical_risks:
            object.__setattr__(self, "risk_types", canonical_risks)
        _exact(self.transfer_form, InsuranceLinkedTransferFormCode, "transfer_form")
        if type(self.risk_subjects) is not tuple or not self.risk_subjects:
            _fail("risk_subjects must be non-empty exact tuple")
        subject_ids: set[UUID] = set()
        for subject in self.risk_subjects:
            _exact(subject, InsuranceLinkedRiskSubjectRef, "risk subject")
            if subject.value in subject_ids:
                _fail("duplicate insurance-linked risk subject")
            subject_ids.add(subject.value)
        canonical_subjects = tuple(
            sorted(self.risk_subjects, key=lambda item: str(item.value))
        )
        if self.risk_subjects != canonical_subjects:
            object.__setattr__(self, "risk_subjects", canonical_subjects)
        _exact(self.trigger, InsuranceLinkedTriggerStructure, "trigger")
        if type(self.effects) is not tuple or not self.effects:
            _fail("effects must be non-empty exact tuple")
        effect_ids: set[UUID] = set()
        effect_semantics: set[tuple[object, ...]] = set()
        for effect in self.effects:
            _exact(effect, InsuranceLinkedEconomicEffect, "economic effect")
            if effect.effect_id.value in effect_ids:
                _fail("duplicate economic effect id")
            effect_ids.add(effect.effect_id.value)
            key = effect.semantic_key()
            if key in effect_semantics:
                _fail("duplicate economic effect semantics")
            effect_semantics.add(key)
        canonical_effects = tuple(sorted(self.effects, key=_effect_sort))
        if self.effects != canonical_effects:
            object.__setattr__(self, "effects", canonical_effects)
        _exact(self.evidence_ref, InsuranceLinkedEvidenceRef, "evidence_ref")
        if self.effective_from is not None:
            _date(self.effective_from, "effective_from")
        if self.effective_until is not None:
            _date(self.effective_until, "effective_until")
        if (
            self.effective_from is not None
            and self.effective_until is not None
            and self.effective_until < self.effective_from
        ):
            _fail("effective_until must not precede effective_from")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "insurance-linked-risk-transfer-terms",
            self.qualification_id.logical_values(),
            self.instrument_identity.logical_values(),
            tuple(item.logical_values() for item in self.risk_types),
            self.transfer_form.logical_values(),
            tuple(item.logical_values() for item in self.risk_subjects),
            self.trigger.logical_values(),
            tuple(item.logical_values() for item in self.effects),
            self.effective_from.isoformat()
            if self.effective_from is not None
            else None,
            self.effective_until.isoformat()
            if self.effective_until is not None
            else None,
            self.evidence_ref.logical_values(),
        )
