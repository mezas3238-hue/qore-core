from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal, localcontext
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.insurance_linked_risk_transfer_semantics as ils
from qore.infrastructure.insurance_linked_risk_transfer_semantics import (
    InsuranceLinkedEconomicEffect,
    InsuranceLinkedEconomicEffectId,
    InsuranceLinkedEffectActionCode,
    InsuranceLinkedEffectMagnitude,
    InsuranceLinkedEffectRuleCode,
    InsuranceLinkedEffectTargetCode,
    InsuranceLinkedEffectUnitCode,
    InsuranceLinkedEvidenceRef,
    InsuranceLinkedRiskMeasureReferenceId,
    InsuranceLinkedRiskSubjectRef,
    InsuranceLinkedRiskTransferQualificationId,
    InsuranceLinkedRiskTransferTerms,
    InsuranceLinkedRiskTransferValidationError,
    InsuranceLinkedRiskTypeCode,
    InsuranceLinkedTransferFormCode,
    InsuranceLinkedTriggerBasisCode,
    InsuranceLinkedTriggerCombinationRuleCode,
    InsuranceLinkedTriggerComparator,
    InsuranceLinkedTriggerComponent,
    InsuranceLinkedTriggerComponentId,
    InsuranceLinkedTriggerId,
    InsuranceLinkedTriggerMetricCode,
    InsuranceLinkedTriggerRuleCode,
    InsuranceLinkedTriggerSourceCode,
    InsuranceLinkedTriggerStructure,
    InsuranceLinkedTriggerStructureKind,
    InsuranceLinkedTriggerThreshold,
    InsuranceLinkedTriggerUnitCode,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
)


def _uuid(i: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{i:012d}")


def _identity(
    i: int = 1,
    *,
    family: str = "fixed-income-credit",
    kind: EconomicIdentityKind = EconomicIdentityKind.TRADABLE_INSTRUMENT,
) -> EconomicIdentity:
    return EconomicIdentity(
        EconomicIdentityId(_uuid(i)),
        kind,
        IdentityFamilyCode(family),
        IdentityConstructionKind.NATIVE,
        IdentityEvidenceRef(_uuid(1000 + i)),
    )


def _threshold(value: str = "100", unit: str = "index-points") -> (
    InsuranceLinkedTriggerThreshold
):
    return InsuranceLinkedTriggerThreshold(
        Decimal(value),
        InsuranceLinkedTriggerUnitCode(unit),
    )


def _component(
    i: int = 1,
    *,
    basis: str = "indemnity",
    metric: str = "aggregate-loss",
    threshold: InsuranceLinkedTriggerThreshold | None = None,
    formula: bool = False,
    sequence: int | None = None,
) -> InsuranceLinkedTriggerComponent:
    selected = None if formula else (threshold or _threshold())
    return InsuranceLinkedTriggerComponent(
        component_id=InsuranceLinkedTriggerComponentId(_uuid(2000 + i)),
        basis=InsuranceLinkedTriggerBasisCode(basis),
        metric=InsuranceLinkedTriggerMetricCode(metric),
        measure_reference_id=InsuranceLinkedRiskMeasureReferenceId(_uuid(3000 + i)),
        source=InsuranceLinkedTriggerSourceCode("contractual-source"),
        rule=InsuranceLinkedTriggerRuleCode("contractual-trigger-rule"),
        evidence_ref=InsuranceLinkedEvidenceRef(_uuid(4000 + i)),
        threshold=selected,
        comparator=(
            None
            if selected is None
            else InsuranceLinkedTriggerComparator.GREATER_THAN_OR_EQUAL
        ),
        sequence_ordinal=sequence,
    )


def _single(component: InsuranceLinkedTriggerComponent | None = None) -> (
    InsuranceLinkedTriggerStructure
):
    return InsuranceLinkedTriggerStructure(
        InsuranceLinkedTriggerId(_uuid(5001)),
        InsuranceLinkedTriggerStructureKind.SINGLE,
        (component or _component(),),
        InsuranceLinkedEvidenceRef(_uuid(5002)),
    )


def _hybrid(
    components: tuple[InsuranceLinkedTriggerComponent, ...] | None = None,
) -> InsuranceLinkedTriggerStructure:
    selected = components or (
        _component(1, basis="parametric", metric="wind-speed"),
        _component(2, basis="industry-loss", metric="industry-loss"),
    )
    return InsuranceLinkedTriggerStructure(
        InsuranceLinkedTriggerId(_uuid(5101)),
        InsuranceLinkedTriggerStructureKind.HYBRID,
        selected,
        InsuranceLinkedEvidenceRef(_uuid(5102)),
        InsuranceLinkedTriggerCombinationRuleCode("all-components"),
    )


def _effect(
    i: int = 1,
    *,
    target: str = "principal",
    action: str = "reduce",
    magnitude: InsuranceLinkedEffectMagnitude | None = None,
) -> InsuranceLinkedEconomicEffect:
    return InsuranceLinkedEconomicEffect(
        InsuranceLinkedEconomicEffectId(_uuid(6000 + i)),
        InsuranceLinkedEffectTargetCode(target),
        InsuranceLinkedEffectActionCode(action),
        InsuranceLinkedEffectRuleCode("contractual-effect-rule"),
        InsuranceLinkedEvidenceRef(_uuid(7000 + i)),
        magnitude,
    )


def _terms(
    *,
    family: str = "fixed-income-credit",
    identity: EconomicIdentity | None = None,
    risks: tuple[InsuranceLinkedRiskTypeCode, ...] | None = None,
    form: str = "catastrophe-bond",
    subjects: tuple[InsuranceLinkedRiskSubjectRef, ...] | None = None,
    trigger: InsuranceLinkedTriggerStructure | None = None,
    effects: tuple[InsuranceLinkedEconomicEffect, ...] | None = None,
) -> InsuranceLinkedRiskTransferTerms:
    return InsuranceLinkedRiskTransferTerms(
        InsuranceLinkedRiskTransferQualificationId(_uuid(8001)),
        identity or _identity(family=family),
        risks or (InsuranceLinkedRiskTypeCode("catastrophe"),),
        InsuranceLinkedTransferFormCode(form),
        subjects or (InsuranceLinkedRiskSubjectRef(_uuid(8101)),),
        trigger or _single(),
        effects or (_effect(),),
        InsuranceLinkedEvidenceRef(_uuid(8002)),
        date(2026, 1, 1),
        date(2030, 1, 1),
    )


def test_catastrophe_bond_indemnity_representation() -> None:
    value = _terms()
    assert value.logical_values()[0] == "insurance-linked-risk-transfer-terms"
    assert value.trigger.components[0].basis.value == "indemnity"


@pytest.mark.parametrize(
    ("family", "risk", "form"),
    [
        ("fixed-income-credit", "catastrophe", "catastrophe-bond"),
        ("structured-hybrid-products", "medical-claim-cost", "event-linked-security"),
        ("forwards-swaps-otc", "mortality", "mortality-swap"),
        ("forwards-swaps-otc", "longevity", "longevity-swap"),
    ],
)
def test_cross_family_roots(family: str, risk: str, form: str) -> None:
    value = _terms(
        family=family,
        risks=(InsuranceLinkedRiskTypeCode(risk),),
        form=form,
    )
    assert value.instrument_identity.family.value == family


@pytest.mark.parametrize(
    "basis",
    ["indemnity", "parametric", "industry-loss", "modeled-loss"],
)
def test_evidenced_trigger_bases(basis: str) -> None:
    assert _terms(trigger=_single(_component(basis=basis))).trigger.components[
        0
    ].basis.value == basis


def test_formulaic_mortality_trigger_needs_no_fake_threshold() -> None:
    component = _component(
        basis="modeled-loss",
        metric="mortality-index",
        formula=True,
    )
    value = _terms(
        family="forwards-swaps-otc",
        risks=(InsuranceLinkedRiskTypeCode("mortality"),),
        form="mortality-swap",
        trigger=_single(component),
    )
    assert value.trigger.components[0].threshold is None


def test_hybrid_unordered_input_is_canonical() -> None:
    first = _component(1, basis="parametric", metric="wind-speed")
    second = _component(2, basis="industry-loss", metric="industry-loss")
    assert _hybrid((first, second)).logical_values() == _hybrid(
        (second, first)
    ).logical_values()


def test_hybrid_explicit_sequence_is_contractual() -> None:
    first = _component(1, sequence=1)
    second = _component(2, basis="modeled-loss", sequence=2)
    value = _hybrid((second, first))
    assert tuple(item.sequence_ordinal for item in value.components) == (1, 2)


@pytest.mark.parametrize(
    "components",
    [
        (_component(1),),
        (_component(1, sequence=1), _component(2)),
        (_component(1, sequence=1), _component(2, sequence=1)),
    ],
)
def test_invalid_hybrid_shapes_fail_closed(
    components: tuple[InsuranceLinkedTriggerComponent, ...],
) -> None:
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _hybrid(components)


def test_single_rejects_extra_component_rule_or_sequence() -> None:
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        InsuranceLinkedTriggerStructure(
            InsuranceLinkedTriggerId(_uuid(1)),
            InsuranceLinkedTriggerStructureKind.SINGLE,
            (_component(1), _component(2)),
            InsuranceLinkedEvidenceRef(_uuid(2)),
        )
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _single(_component(sequence=1))


def test_threshold_and_comparator_are_paired() -> None:
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        InsuranceLinkedTriggerComponent(
            InsuranceLinkedTriggerComponentId(_uuid(1)),
            InsuranceLinkedTriggerBasisCode("modeled-loss"),
            InsuranceLinkedTriggerMetricCode("mortality-index"),
            InsuranceLinkedRiskMeasureReferenceId(_uuid(2)),
            InsuranceLinkedTriggerSourceCode("contractual-source"),
            InsuranceLinkedTriggerRuleCode("formula-rule"),
            InsuranceLinkedEvidenceRef(_uuid(3)),
            comparator=InsuranceLinkedTriggerComparator.GREATER_THAN,
        )


def test_duplicate_trigger_semantics_rejected_with_different_ids() -> None:
    first = _component(1)
    duplicate = InsuranceLinkedTriggerComponent(
        InsuranceLinkedTriggerComponentId(_uuid(2999)),
        first.basis,
        first.metric,
        first.measure_reference_id,
        first.source,
        first.rule,
        InsuranceLinkedEvidenceRef(_uuid(4999)),
        threshold=first.threshold,
        comparator=first.comparator,
    )
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _hybrid((first, duplicate))


def test_multi_risk_subject_and_effect_sets_are_canonical() -> None:
    risks = (
        InsuranceLinkedRiskTypeCode("mortality"),
        InsuranceLinkedRiskTypeCode("longevity"),
    )
    subjects = (
        InsuranceLinkedRiskSubjectRef(_uuid(101)),
        InsuranceLinkedRiskSubjectRef(_uuid(100)),
    )
    effects = (
        _effect(2, target="interest", action="suspend"),
        _effect(1),
    )
    a = _terms(risks=risks, subjects=subjects, effects=effects)
    b = _terms(
        risks=tuple(reversed(risks)),
        subjects=tuple(reversed(subjects)),
        effects=tuple(reversed(effects)),
    )
    assert a.logical_values() == b.logical_values()


def test_duplicate_risk_subject_and_effect_semantics_rejected() -> None:
    risk = InsuranceLinkedRiskTypeCode("catastrophe")
    subject = InsuranceLinkedRiskSubjectRef(_uuid(100))
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _terms(risks=(risk, risk))
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _terms(subjects=(subject, subject))
    first = _effect(1)
    duplicate = InsuranceLinkedEconomicEffect(
        InsuranceLinkedEconomicEffectId(_uuid(6999)),
        first.target,
        first.action,
        first.rule,
        InsuranceLinkedEvidenceRef(_uuid(7999)),
    )
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _terms(effects=(first, duplicate))


def test_decimal_canonicalization_is_context_independent() -> None:
    threshold = _threshold("123456789.123450000")
    with localcontext() as context:
        context.prec = 3
        low = threshold.logical_values()
    with localcontext() as context:
        context.prec = 50
        high = threshold.logical_values()
    assert low == high


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity")])
def test_non_finite_decimal_rejected(value: Decimal) -> None:
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        InsuranceLinkedTriggerThreshold(
            value,
            InsuranceLinkedTriggerUnitCode("index-points"),
        )


def test_magnitude_and_threshold_can_bind_canonical_unit_identity() -> None:
    unit = EconomicIdentityId(_uuid(9001))
    threshold = InsuranceLinkedTriggerThreshold(
        Decimal("10"),
        InsuranceLinkedTriggerUnitCode("currency-amount"),
        unit,
    )
    magnitude = InsuranceLinkedEffectMagnitude(
        Decimal("5"),
        InsuranceLinkedEffectUnitCode("currency-amount"),
        unit,
    )
    assert threshold.logical_values()[2] == magnitude.logical_values()[2]


@pytest.mark.parametrize(
    "family",
    ["equities", "event-contracts", "crypto-digital-assets"],
)
def test_unrelated_root_family_rejected(family: str) -> None:
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _terms(family=family)


def test_reference_object_and_continuous_root_rejected() -> None:
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _terms(identity=_identity(kind=EconomicIdentityKind.REFERENCE_OBJECT))
    fabricated = object.__new__(EconomicIdentity)
    object.__setattr__(fabricated, "identity_id", EconomicIdentityId(_uuid(1)))
    object.__setattr__(fabricated, "kind", EconomicIdentityKind.TRADABLE_INSTRUMENT)
    object.__setattr__(fabricated, "family", IdentityFamilyCode("fixed-income-credit"))
    object.__setattr__(
        fabricated,
        "construction",
        IdentityConstructionKind.CONTINUOUS_REFERENCE,
    )
    object.__setattr__(fabricated, "evidence_ref", IdentityEvidenceRef(_uuid(2)))
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _terms(identity=fabricated)


def test_bool_str_subclass_and_datetime_laundering_rejected() -> None:
    class SneakyStr(str):
        pass

    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        InsuranceLinkedRiskTypeCode(cast(str, SneakyStr("catastrophe")))
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _component(sequence=cast(int, True))
    value = _terms()
    object.__setattr__(value, "effective_from", cast(date, datetime(2026, 1, 1)))
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        value.logical_values()


def test_fabricated_and_corrupted_nested_state_rejected() -> None:
    broken = object.__new__(InsuranceLinkedTriggerStructure)
    object.__setattr__(broken, "trigger_id", InsuranceLinkedTriggerId(_uuid(1)))
    object.__setattr__(broken, "kind", InsuranceLinkedTriggerStructureKind.HYBRID)
    object.__setattr__(broken, "components", ())
    object.__setattr__(broken, "evidence_ref", InsuranceLinkedEvidenceRef(_uuid(2)))
    object.__setattr__(
        broken,
        "combination_rule",
        InsuranceLinkedTriggerCombinationRuleCode("all-components"),
    )
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        _terms(trigger=broken)
    value = _terms()
    object.__setattr__(value.trigger.components[0], "source", cast(object, "bad"))
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        value.logical_values()


def test_values_are_frozen_and_dates_are_chronological() -> None:
    value = _terms()
    with pytest.raises(FrozenInstanceError):
        value.transfer_form = (  # type: ignore[misc]
            InsuranceLinkedTransferFormCode("other")
        )
    with pytest.raises(InsuranceLinkedRiskTransferValidationError):
        InsuranceLinkedRiskTransferTerms(
            value.qualification_id,
            value.instrument_identity,
            value.risk_types,
            value.transfer_form,
            value.risk_subjects,
            value.trigger,
            value.effects,
            value.evidence_ref,
            date(2030, 1, 2),
            date(2030, 1, 1),
        )


def test_module_has_no_operational_model_or_production_authority() -> None:
    source = inspect.getsource(ils).lower()
    forbidden = (
        "requests.",
        "httpx",
        "aiohttp",
        "socket",
        "subprocess",
        "place_order",
        "submit_order",
        "execute_order",
        "api_key",
        "secret_key",
        "datetime.now",
        "uuid4(",
    )
    assert all(token not in source for token in forbidden)
    for name in ("evaluate_trigger", "price", "expected_loss", "settle"):
        assert not hasattr(ils, name)
