from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

import qore.infrastructure.structured_hybrid_synthetic_semantics as structured
import qore.infrastructure.structured_note_payoff_semantics as note
import qore.infrastructure.universal_instrument_identity as identity


def _economic_id(value: int) -> identity.EconomicIdentityId:
    return identity.EconomicIdentityId(UUID(int=value))


def _feature_id(value: int) -> structured.StructuredFeatureId:
    return structured.StructuredFeatureId(UUID(int=value))


def _evidence(value: int) -> structured.StructuredEvidenceRef:
    return structured.StructuredEvidenceRef(UUID(int=value))


def _component(
    root: identity.EconomicIdentityId,
    target: identity.EconomicIdentityId,
    *,
    relationship_id: int,
    role: str,
) -> structured.StructuredComponentBinding:
    return structured.StructuredComponentBinding(
        root_identity_id=root,
        relationship=identity.IdentityRelationship(
            relationship_id=identity.IdentityRelationshipId(UUID(int=relationship_id)),
            source_identity_id=root,
            target_identity_id=target,
            relationship=identity.IdentityRelationshipCode("structured-component"),
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            effective_until=None,
            evidence_ref=identity.IdentityEvidenceRef(UUID(int=10_000 + relationship_id)),
            ordinal=relationship_id,
        ),
        role=structured.StructuredComponentRoleCode(role),
        evidence_ref=_evidence(20_000 + relationship_id),
    )


def _structured_terms() -> structured.StructuredHybridSyntheticTerms:
    root = _economic_id(1)
    reference = _economic_id(2)
    redemption = _economic_id(3)
    observation = structured.StructuredObservationTerms(
        mode=structured.StructuredObservationMode.DISCRETE,
        explicit_dates=(date(2030, 6, 3),),
    )
    return structured.StructuredHybridSyntheticTerms(
        terms_id=structured.StructuredTermsId(UUID(int=10)),
        instrument_identity_id=root,
        components=(
            _component(root, reference, relationship_id=101, role="reference"),
            _component(root, redemption, relationship_id=102, role="redemption"),
        ),
        features=(
            structured.StructuredBarrierFeature(
                feature_id=_feature_id(201),
                reference_identity_id=reference,
                barrier_kind=structured.StructuredBarrierKindCode("downside-threshold"),
                direction=structured.StructuredBarrierDirection.AT_OR_ABOVE,
                level=structured.StructuredContractLevel(
                    value=Decimal("70"),
                    kind=structured.StructuredContractLevelKind.LEVEL,
                    reference_identity_id=reference,
                    unit=structured.StructuredLevelUnitCode("index-points"),
                ),
                observation=observation,
                evidence_ref=_evidence(201),
            ),
            structured.StructuredRedemptionFeature(
                feature_id=_feature_id(202),
                redemption_identity_id=redemption,
                redemption_ratio=structured.StructuredPositiveRatio(Decimal("1")),
                redemption_date=date(2030, 6, 7),
                evidence_ref=_evidence(202),
            ),
        ),
        evidence_ref=_evidence(999),
    )


def _selection() -> note.StructuredNoteParticipationSelection:
    return note.StructuredNoteParticipationSelection(
        kind=note.StructuredNoteParticipationSelectionKind.WORST_PERFORMING_BY_RETURN,
        candidate_feature_ids=(_feature_id(301), _feature_id(302)),
    )


def _outcome() -> note.StructuredNotePayoffOutcome:
    return note.StructuredNotePayoffOutcome(
        kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        redemption_feature_id=_feature_id(202),
    )


def _conditional_branch() -> note.StructuredNotePayoffBranch:
    return note.StructuredNotePayoffBranch(
        branch_id=note.StructuredNotePayoffBranchId(UUID(int=401)),
        ordinal=1,
        condition_mode=note.StructuredNoteConditionMode.ALL,
        condition_feature_ids=(_feature_id(201),),
        outcome=_outcome(),
        evidence_ref=_evidence(401),
    )


def _fallback_branch() -> note.StructuredNotePayoffBranch:
    return note.StructuredNotePayoffBranch(
        branch_id=note.StructuredNotePayoffBranchId(UUID(int=402)),
        ordinal=2,
        condition_mode=None,
        condition_feature_ids=(),
        outcome=_outcome(),
        evidence_ref=_evidence(402),
    )


def _payoff_terms() -> note.StructuredNotePayoffTerms:
    return note.StructuredNotePayoffTerms(
        terms_id=note.StructuredNotePayoffTermsId(UUID(int=500)),
        structured_terms=_structured_terms(),
        branches=(_conditional_branch(), _fallback_branch()),
        evidence_ref=_evidence(888),
    )


def test_composite_payoff_contracts_are_behaviorally_frozen() -> None:
    selection = _selection()
    outcome = _outcome()
    branch = _conditional_branch()
    terms = _payoff_terms()

    mutations: tuple[tuple[object, str, object], ...] = (
        (
            selection,
            "candidate_feature_ids",
            (_feature_id(901), _feature_id(902)),
        ),
        (outcome, "kind", note.StructuredNoteOutcomeKind.CONVERSION),
        (branch, "ordinal", 99),
        (terms, "branches", ()),
    )

    for instance, field_name, replacement in mutations:
        with pytest.raises(FrozenInstanceError):
            setattr(cast(Any, instance), field_name, replacement)


def test_composite_payoff_contracts_are_slotted_without_instance_dict() -> None:
    instances: tuple[object, ...] = (
        _selection(),
        _outcome(),
        _conditional_branch(),
        _payoff_terms(),
    )

    for instance in instances:
        assert not hasattr(instance, "__dict__")


class _TermsIdSubclass(note.StructuredNotePayoffTermsId):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-terms-id",)


class _BranchIdSubclass(note.StructuredNotePayoffBranchId):
    __slots__ = ()

    def logical_values(self) -> tuple[str, ...]:
        return ("spoofed-branch-id",)


class _SelectionSubclass(note.StructuredNoteParticipationSelection):
    __slots__ = ()

    def logical_values(self) -> tuple[object, ...]:
        return ("spoofed-selection",)


class _OutcomeSubclass(note.StructuredNotePayoffOutcome):
    __slots__ = ()

    def logical_values(self) -> tuple[object, ...]:
        return ("spoofed-outcome",)


class _InvertedFallbackBranch(note.StructuredNotePayoffBranch):
    __slots__ = ()

    @property
    def is_fallback(self) -> bool:
        return self.condition_mode is not None

    def logical_values(self) -> tuple[object, ...]:
        return ("spoofed-branch",)


def test_local_id_subclasses_are_rejected_before_logical_identity_use() -> None:
    with pytest.raises(note.StructuredNotePayoffValidationError, match="terms_id"):
        note.StructuredNotePayoffTerms(
            terms_id=_TermsIdSubclass(UUID(int=500)),
            structured_terms=_structured_terms(),
            branches=(_conditional_branch(), _fallback_branch()),
            evidence_ref=_evidence(888),
        )

    with pytest.raises(note.StructuredNotePayoffValidationError, match="branch_id"):
        note.StructuredNotePayoffBranch(
            branch_id=_BranchIdSubclass(UUID(int=401)),
            ordinal=1,
            condition_mode=note.StructuredNoteConditionMode.ALL,
            condition_feature_ids=(_feature_id(201),),
            outcome=_outcome(),
            evidence_ref=_evidence(401),
        )


def test_selection_and_outcome_subclasses_are_rejected_before_virtual_projection() -> None:
    selection = _SelectionSubclass(
        kind=note.StructuredNoteParticipationSelectionKind.WORST_PERFORMING_BY_RETURN,
        candidate_feature_ids=(_feature_id(301), _feature_id(302)),
    )
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="participation_selection",
    ):
        note.StructuredNotePayoffOutcome(
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
            participation_selection=selection,
        )

    outcome = _OutcomeSubclass(
        kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        redemption_feature_id=_feature_id(202),
    )
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="StructuredNotePayoffOutcome",
    ):
        note.StructuredNotePayoffBranch(
            branch_id=note.StructuredNotePayoffBranchId(UUID(int=401)),
            ordinal=1,
            condition_mode=note.StructuredNoteConditionMode.ALL,
            condition_feature_ids=(_feature_id(201),),
            outcome=outcome,
            evidence_ref=_evidence(401),
        )


def test_branch_subclass_cannot_spoof_final_fallback_or_logical_identity() -> None:
    real_fallback = _InvertedFallbackBranch(
        branch_id=note.StructuredNotePayoffBranchId(UUID(int=401)),
        ordinal=1,
        condition_mode=None,
        condition_feature_ids=(),
        outcome=_outcome(),
        evidence_ref=_evidence(401),
    )
    real_conditional = _InvertedFallbackBranch(
        branch_id=note.StructuredNotePayoffBranchId(UUID(int=402)),
        ordinal=2,
        condition_mode=note.StructuredNoteConditionMode.ALL,
        condition_feature_ids=(_feature_id(201),),
        outcome=_outcome(),
        evidence_ref=_evidence(402),
    )

    assert real_fallback.condition_mode is None
    assert not real_fallback.is_fallback
    assert real_conditional.condition_mode is note.StructuredNoteConditionMode.ALL
    assert real_conditional.is_fallback
    assert real_fallback.logical_values() == ("spoofed-branch",)

    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="branches must contain StructuredNotePayoffBranch",
    ):
        note.StructuredNotePayoffTerms(
            terms_id=note.StructuredNotePayoffTermsId(UUID(int=500)),
            structured_terms=_structured_terms(),
            branches=(real_fallback, real_conditional),
            evidence_ref=_evidence(888),
        )
