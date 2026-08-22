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


def _level(
    reference: identity.EconomicIdentityId,
    value: str,
) -> structured.StructuredContractLevel:
    return structured.StructuredContractLevel(
        value=Decimal(value),
        kind=structured.StructuredContractLevelKind.LEVEL,
        reference_identity_id=reference,
        unit=structured.StructuredLevelUnitCode("index-points"),
    )


def _structured_terms() -> structured.StructuredHybridSyntheticTerms:
    root = _economic_id(1)
    reference_a = _economic_id(2)
    reference_b = _economic_id(3)
    redemption = _economic_id(4)
    participation = _economic_id(5)
    conversion = _economic_id(6)
    components = (
        _component(root, reference_a, relationship_id=101, role="reference-a"),
        _component(root, reference_b, relationship_id=102, role="reference-b"),
        _component(root, redemption, relationship_id=103, role="redemption"),
        _component(root, participation, relationship_id=104, role="participation"),
        _component(root, conversion, relationship_id=105, role="conversion"),
    )
    observation = structured.StructuredObservationTerms(
        mode=structured.StructuredObservationMode.DISCRETE,
        explicit_dates=(date(2029, 6, 1),),
    )
    features: tuple[structured.StructuredFeature, ...] = (
        structured.StructuredBarrierFeature(
            feature_id=_feature_id(201),
            reference_identity_id=reference_a,
            barrier_kind=structured.StructuredBarrierKindCode("initial-level-test"),
            direction=structured.StructuredBarrierDirection.AT_OR_ABOVE,
            level=_level(reference_a, "100"),
            observation=observation,
            evidence_ref=_evidence(201),
        ),
        structured.StructuredBarrierFeature(
            feature_id=_feature_id(202),
            reference_identity_id=reference_a,
            barrier_kind=structured.StructuredBarrierKindCode("downside-threshold"),
            direction=structured.StructuredBarrierDirection.AT_OR_ABOVE,
            level=_level(reference_a, "70"),
            observation=observation,
            evidence_ref=_evidence(202),
        ),
        structured.StructuredBarrierFeature(
            feature_id=_feature_id(203),
            reference_identity_id=reference_b,
            barrier_kind=structured.StructuredBarrierKindCode("downside-threshold"),
            direction=structured.StructuredBarrierDirection.AT_OR_ABOVE,
            level=_level(reference_b, "65"),
            observation=observation,
            evidence_ref=_evidence(203),
        ),
        structured.StructuredRedemptionFeature(
            feature_id=_feature_id(204),
            redemption_identity_id=redemption,
            redemption_ratio=structured.StructuredPositiveRatio(Decimal("1")),
            redemption_date=date(2029, 6, 5),
            evidence_ref=_evidence(204),
        ),
        structured.StructuredParticipationFeature(
            feature_id=_feature_id(205),
            reference_identity_id=participation,
            direction=structured.StructuredParticipationDirection.POSITIVE,
            participation_ratio=structured.StructuredPositiveRatio(Decimal("1.5")),
            evidence_ref=_evidence(205),
        ),
        structured.StructuredConversionFeature(
            feature_id=_feature_id(206),
            target_identity_id=conversion,
            units_per_source_unit=structured.StructuredPositiveRatio(Decimal("2")),
            evidence_ref=_evidence(206),
        ),
    )
    return structured.StructuredHybridSyntheticTerms(
        terms_id=structured.StructuredTermsId(UUID(int=10)),
        instrument_identity_id=root,
        components=tuple(reversed(components)),
        features=tuple(reversed(features)),
        evidence_ref=_evidence(999),
    )


def _outcome(
    kind: note.StructuredNoteOutcomeKind,
    **overrides: Any,
) -> note.StructuredNotePayoffOutcome:
    values: dict[str, Any]
    if kind is note.StructuredNoteOutcomeKind.REDEMPTION:
        values = {"kind": kind, "redemption_feature_id": _feature_id(204)}
    elif kind is note.StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION:
        values = {
            "kind": kind,
            "redemption_feature_id": _feature_id(204),
            "participation_feature_id": _feature_id(205),
        }
    elif kind is note.StructuredNoteOutcomeKind.PARTICIPATION:
        values = {"kind": kind, "participation_feature_id": _feature_id(205)}
    else:
        values = {"kind": kind, "conversion_feature_id": _feature_id(206)}
    values.update(overrides)
    return note.StructuredNotePayoffOutcome(**values)


def _branch(
    ordinal: int,
    *,
    condition_ids: tuple[int, ...],
    mode: note.StructuredNoteConditionMode | None,
    kind: note.StructuredNoteOutcomeKind,
    branch_id: int | None = None,
    **overrides: Any,
) -> note.StructuredNotePayoffBranch:
    values: dict[str, Any] = {
        "branch_id": note.StructuredNotePayoffBranchId(UUID(int=branch_id or 300 + ordinal)),
        "ordinal": ordinal,
        "condition_mode": mode,
        "condition_feature_ids": tuple(_feature_id(value) for value in condition_ids),
        "outcome": _outcome(kind),
        "evidence_ref": _evidence(400 + ordinal),
    }
    values.update(overrides)
    return note.StructuredNotePayoffBranch(**values)


def _trigger_branches() -> tuple[note.StructuredNotePayoffBranch, ...]:
    return (
        _branch(
            3,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        ),
        _branch(
            2,
            condition_ids=(203, 202),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
        _branch(
            1,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION,
        ),
    )


def _terms(**overrides: Any) -> note.StructuredNotePayoffTerms:
    values: dict[str, Any] = {
        "terms_id": note.StructuredNotePayoffTermsId(UUID(int=500)),
        "structured_terms": _structured_terms(),
        "branches": _trigger_branches(),
        "evidence_ref": _evidence(888),
    }
    values.update(overrides)
    return note.StructuredNotePayoffTerms(**values)


def test_trigger_note_canonicalizes_first_match_branches_and_condition_sets() -> None:
    terms = _terms()
    assert tuple(branch.ordinal for branch in terms.branches) == (1, 2, 3)
    assert terms.branches[-1].is_fallback
    assert terms.branches[1].condition_feature_ids == (
        _feature_id(202),
        _feature_id(203),
    )


def test_reverse_convertible_selects_conversion_or_redemption_statically() -> None:
    terms = _terms(
        branches=(
            _branch(
                1,
                condition_ids=(202,),
                mode=note.StructuredNoteConditionMode.ALL,
                kind=note.StructuredNoteOutcomeKind.CONVERSION,
            ),
            _branch(
                2,
                condition_ids=(),
                mode=None,
                kind=note.StructuredNoteOutcomeKind.REDEMPTION,
            ),
        )
    )
    assert terms.branches[0].outcome.conversion_feature_id == _feature_id(206)
    assert terms.branches[1].outcome.redemption_feature_id == _feature_id(204)


def test_any_mode_preserves_multi_reference_condition_set() -> None:
    branch = _branch(
        1,
        condition_ids=(203, 202),
        mode=note.StructuredNoteConditionMode.ANY,
        kind=note.StructuredNoteOutcomeKind.CONVERSION,
    )
    assert branch.condition_feature_ids == (_feature_id(202), _feature_id(203))
    assert branch.condition_mode is note.StructuredNoteConditionMode.ANY
    assert branch.logical_values()[2] == "any"


class _UuidSubclass(UUID):
    pass


@pytest.mark.parametrize(
    "factory",
    [
        lambda: note.StructuredNotePayoffTermsId(cast(Any, "bad")),
        lambda: note.StructuredNotePayoffBranchId(cast(Any, "bad")),
        lambda: note.StructuredNotePayoffTermsId(cast(Any, _UuidSubclass(int=1))),
        lambda: note.StructuredNotePayoffBranchId(cast(Any, _UuidSubclass(int=2))),
    ],
)
def test_local_ids_require_exact_uuid(factory: Any) -> None:
    with pytest.raises(note.StructuredNotePayoffValidationError, match="must be UUID"):
        factory()


def test_local_ids_are_not_economic_identity_and_are_frozen() -> None:
    terms_id = note.StructuredNotePayoffTermsId(UUID(int=1))
    assert not isinstance(terms_id, identity.EconomicIdentityId)
    assert not isinstance(
        note.StructuredNotePayoffBranchId(UUID(int=2)),
        identity.EconomicIdentityId,
    )
    with pytest.raises(FrozenInstanceError):
        cast(Any, terms_id).value = UUID(int=2)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"kind": cast(Any, "redemption")}, "outcome kind"),
        ({"redemption_feature_id": cast(Any, "bad")}, "redemption_feature_id"),
        ({"participation_feature_id": cast(Any, "bad")}, "participation_feature_id"),
        ({"conversion_feature_id": cast(Any, "bad")}, "conversion_feature_id"),
    ],
)
def test_outcome_runtime_type_guards(
    overrides: dict[str, Any],
    message: str,
) -> None:
    base: dict[str, Any] = {
        "kind": note.StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION,
        "redemption_feature_id": _feature_id(204),
        "participation_feature_id": _feature_id(205),
    }
    base.update(overrides)
    with pytest.raises(note.StructuredNotePayoffValidationError, match=message):
        note.StructuredNotePayoffOutcome(**base)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _outcome(
            note.StructuredNoteOutcomeKind.REDEMPTION,
            participation_feature_id=_feature_id(205),
        ),
        lambda: note.StructuredNotePayoffOutcome(
            kind=note.StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION,
            redemption_feature_id=_feature_id(204),
        ),
        lambda: _outcome(
            note.StructuredNoteOutcomeKind.PARTICIPATION,
            conversion_feature_id=_feature_id(206),
        ),
        lambda: _outcome(
            note.StructuredNoteOutcomeKind.CONVERSION,
            redemption_feature_id=_feature_id(204),
        ),
    ],
)
def test_outcome_kind_requires_exact_feature_shape(factory: Any) -> None:
    with pytest.raises(note.StructuredNotePayoffValidationError, match="feature references"):
        factory()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"branch_id": cast(Any, "bad")}, "branch_id"),
        ({"ordinal": cast(Any, True)}, "positive int"),
        ({"ordinal": 0}, "positive int"),
        ({"condition_mode": cast(Any, "all")}, "condition_mode"),
        ({"condition_feature_ids": cast(Any, [_feature_id(201)])}, "immutable tuple"),
        ({"condition_feature_ids": (cast(Any, "bad"),)}, "StructuredFeatureId"),
        ({"condition_feature_ids": (_feature_id(201), _feature_id(201))}, "must be unique"),
        ({"outcome": cast(Any, "bad")}, "StructuredNotePayoffOutcome"),
        ({"evidence_ref": cast(Any, "bad")}, "evidence_ref"),
    ],
)
def test_branch_runtime_and_collection_guards(
    overrides: dict[str, Any],
    message: str,
) -> None:
    values: dict[str, Any] = {
        "branch_id": note.StructuredNotePayoffBranchId(UUID(int=301)),
        "ordinal": 1,
        "condition_mode": note.StructuredNoteConditionMode.ALL,
        "condition_feature_ids": (_feature_id(201),),
        "outcome": _outcome(note.StructuredNoteOutcomeKind.REDEMPTION),
        "evidence_ref": _evidence(401),
    }
    values.update(overrides)
    with pytest.raises(note.StructuredNotePayoffValidationError, match=message):
        note.StructuredNotePayoffBranch(**values)


def test_fallback_and_conditional_branch_shapes_fail_closed() -> None:
    with pytest.raises(note.StructuredNotePayoffValidationError, match="fallback branch"):
        _branch(
            1,
            condition_ids=(201,),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        )
    with pytest.raises(note.StructuredNotePayoffValidationError, match="requires condition"):
        _branch(
            1,
            condition_ids=(),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"terms_id": cast(Any, "bad")}, "terms_id"),
        ({"structured_terms": cast(Any, "bad")}, "StructuredHybridSyntheticTerms"),
        ({"branches": cast(Any, list(_trigger_branches()))}, "immutable tuple"),
        ({"branches": ()}, "at least two"),
        ({"branches": (_trigger_branches()[0],)}, "at least two"),
        ({"branches": cast(Any, (_trigger_branches()[0], "bad"))}, "must contain"),
        ({"evidence_ref": cast(Any, "bad")}, "evidence_ref"),
    ],
)
def test_top_level_runtime_and_collection_guards(
    overrides: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(note.StructuredNotePayoffValidationError, match=message):
        _terms(**overrides)


def test_top_level_branch_identity_and_ordinal_guards() -> None:
    duplicate_id = (
        _branch(
            1,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
            branch_id=700,
        ),
        _branch(
            2,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
            branch_id=700,
        ),
    )
    with pytest.raises(note.StructuredNotePayoffValidationError, match="branch ids"):
        _terms(branches=duplicate_id)

    duplicate_ordinal = (
        _branch(
            1,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
        _branch(
            1,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
            branch_id=999,
        ),
    )
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="ordinals must be unique",
    ):
        _terms(branches=duplicate_ordinal)

    non_contiguous = (
        _branch(
            1,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
        _branch(
            3,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
    )
    with pytest.raises(note.StructuredNotePayoffValidationError, match="contiguous"):
        _terms(branches=non_contiguous)


def test_top_level_fallback_and_condition_signature_guards() -> None:
    no_fallback = (
        _branch(
            1,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
        _branch(
            2,
            condition_ids=(202,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        ),
    )
    with pytest.raises(note.StructuredNotePayoffValidationError, match="exactly one fallback"):
        _terms(branches=no_fallback)

    two_fallbacks = (
        _branch(
            1,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
        _branch(
            2,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        ),
    )
    with pytest.raises(note.StructuredNotePayoffValidationError, match="exactly one fallback"):
        _terms(branches=two_fallbacks)

    fallback_first = (
        _branch(
            2,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        ),
        _branch(
            1,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
    )
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="fallback branch must be last",
    ):
        _terms(branches=fallback_first)

    duplicate_signature = (
        _branch(
            1,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
        _branch(
            2,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        ),
        _branch(
            3,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
    )
    with pytest.raises(note.StructuredNotePayoffValidationError, match="signatures must be unique"):
        _terms(branches=duplicate_signature)


def _two_branch_terms(
    first: note.StructuredNotePayoffBranch,
) -> note.StructuredNotePayoffTerms:
    return _terms(
        branches=(
            first,
            _branch(
                2,
                condition_ids=(),
                mode=None,
                kind=note.StructuredNoteOutcomeKind.REDEMPTION,
            ),
        )
    )


@pytest.mark.parametrize("condition_id", [999, 204])
def test_condition_must_resolve_to_existing_barrier(condition_id: int) -> None:
    first = _branch(
        1,
        condition_ids=(condition_id,),
        mode=note.StructuredNoteConditionMode.ALL,
        kind=note.StructuredNoteOutcomeKind.REDEMPTION,
    )
    with pytest.raises(note.StructuredNotePayoffValidationError, match="StructuredBarrierFeature"):
        _two_branch_terms(first)


@pytest.mark.parametrize(
    ("outcome", "message"),
    [
        (
            note.StructuredNotePayoffOutcome(
                kind=note.StructuredNoteOutcomeKind.REDEMPTION,
                redemption_feature_id=_feature_id(205),
            ),
            "StructuredRedemptionFeature",
        ),
        (
            note.StructuredNotePayoffOutcome(
                kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
                participation_feature_id=_feature_id(204),
            ),
            "StructuredParticipationFeature",
        ),
        (
            note.StructuredNotePayoffOutcome(
                kind=note.StructuredNoteOutcomeKind.CONVERSION,
                conversion_feature_id=_feature_id(204),
            ),
            "StructuredConversionFeature",
        ),
    ],
)
def test_outcome_feature_ids_must_resolve_to_exact_umi09_types(
    outcome: note.StructuredNotePayoffOutcome,
    message: str,
) -> None:
    first = _branch(
        1,
        condition_ids=(201,),
        mode=note.StructuredNoteConditionMode.ALL,
        kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        outcome=outcome,
    )
    with pytest.raises(note.StructuredNotePayoffValidationError, match=message):
        _two_branch_terms(first)


def test_logical_values_are_deterministic_under_caller_order() -> None:
    first = _terms()
    second = _terms(branches=tuple(reversed(first.branches)))
    assert first.logical_values() == second.logical_values()


def _participation_selection(
    *feature_ids: int,
) -> note.StructuredNoteParticipationSelection:
    return note.StructuredNoteParticipationSelection(
        kind=note.StructuredNoteParticipationSelectionKind.WORST_PERFORMING_BY_RETURN,
        candidate_feature_ids=tuple(_feature_id(value) for value in feature_ids),
    )


def _structured_terms_with_participation_candidates(
    *,
    same_reference: bool = False,
) -> structured.StructuredHybridSyntheticTerms:
    base = _structured_terms()
    reference_a = _economic_id(2)
    reference_b = reference_a if same_reference else _economic_id(3)
    candidate_features: tuple[structured.StructuredFeature, ...] = (
        structured.StructuredParticipationFeature(
            feature_id=_feature_id(207),
            reference_identity_id=reference_a,
            direction=structured.StructuredParticipationDirection.POSITIVE,
            participation_ratio=structured.StructuredPositiveRatio(Decimal("1")),
            evidence_ref=_evidence(207),
        ),
        structured.StructuredParticipationFeature(
            feature_id=_feature_id(208),
            reference_identity_id=reference_b,
            direction=structured.StructuredParticipationDirection.POSITIVE,
            participation_ratio=structured.StructuredPositiveRatio(Decimal("1")),
            evidence_ref=_evidence(208),
        ),
    )
    return structured.StructuredHybridSyntheticTerms(
        terms_id=base.terms_id,
        instrument_identity_id=base.instrument_identity_id,
        components=base.components,
        features=base.features + candidate_features,
        evidence_ref=base.evidence_ref,
    )


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: note.StructuredNoteParticipationSelection(
                kind=cast(Any, "worst-performing-by-return"),
                candidate_feature_ids=(_feature_id(207), _feature_id(208)),
            ),
            "selection kind",
        ),
        (
            lambda: note.StructuredNoteParticipationSelection(
                kind=(
                    note.StructuredNoteParticipationSelectionKind.WORST_PERFORMING_BY_RETURN
                ),
                candidate_feature_ids=cast(
                    Any,
                    [_feature_id(207), _feature_id(208)],
                ),
            ),
            "immutable tuple",
        ),
        (
            lambda: _participation_selection(207),
            "at least two candidates",
        ),
        (
            lambda: note.StructuredNoteParticipationSelection(
                kind=(
                    note.StructuredNoteParticipationSelectionKind.WORST_PERFORMING_BY_RETURN
                ),
                candidate_feature_ids=(_feature_id(207), cast(Any, "bad")),
            ),
            "StructuredFeatureId",
        ),
        (
            lambda: _participation_selection(207, 207),
            "candidate ids must be unique",
        ),
    ],
)
def test_participation_selection_runtime_and_collection_guards(
    factory: Any,
    message: str,
) -> None:
    with pytest.raises(note.StructuredNotePayoffValidationError, match=message):
        factory()


def test_worst_performing_selection_is_static_and_canonical() -> None:
    selection = _participation_selection(208, 207)
    assert selection.candidate_feature_ids == (_feature_id(207), _feature_id(208))
    assert selection.logical_values() == (
        "worst-performing-by-return",
        (
            (str(UUID(int=207)),),
            (str(UUID(int=208)),),
        ),
    )


def test_outcome_rejects_raw_or_ambiguous_participation_selection() -> None:
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="participation_selection",
    ):
        note.StructuredNotePayoffOutcome(
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
            participation_selection=cast(Any, "bad"),
        )
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="direct feature or selection",
    ):
        note.StructuredNotePayoffOutcome(
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
            participation_feature_id=_feature_id(205),
            participation_selection=_participation_selection(207, 208),
        )


def test_worst_performing_selection_resolves_exact_umi09_participation_candidates() -> None:
    structured_terms = _structured_terms_with_participation_candidates()
    selected_outcome = note.StructuredNotePayoffOutcome(
        kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        participation_selection=_participation_selection(208, 207),
    )
    first = _branch(
        1,
        condition_ids=(202, 203),
        mode=note.StructuredNoteConditionMode.ANY,
        kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        outcome=selected_outcome,
    )
    terms = _terms(
        structured_terms=structured_terms,
        branches=(
            first,
            _branch(
                2,
                condition_ids=(),
                mode=None,
                kind=note.StructuredNoteOutcomeKind.REDEMPTION,
            ),
        ),
    )
    assert terms.branches[0].outcome.participation_selection == _participation_selection(
        207,
        208,
    )


@pytest.mark.parametrize("candidate_ids", [(207, 999), (201, 207)])
def test_participation_selection_candidates_must_resolve_to_participation_features(
    candidate_ids: tuple[int, int],
) -> None:
    selected_outcome = note.StructuredNotePayoffOutcome(
        kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        participation_selection=_participation_selection(*candidate_ids),
    )
    first = _branch(
        1,
        condition_ids=(202,),
        mode=note.StructuredNoteConditionMode.ALL,
        kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        outcome=selected_outcome,
    )
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="selection candidate must resolve to StructuredParticipationFeature",
    ):
        _terms(
            structured_terms=_structured_terms_with_participation_candidates(),
            branches=(
                first,
                _branch(
                    2,
                    condition_ids=(),
                    mode=None,
                    kind=note.StructuredNoteOutcomeKind.REDEMPTION,
                ),
            ),
        )


def test_worst_performing_selection_requires_distinct_underlying_identities() -> None:
    selected_outcome = note.StructuredNotePayoffOutcome(
        kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        participation_selection=_participation_selection(207, 208),
    )
    first = _branch(
        1,
        condition_ids=(202,),
        mode=note.StructuredNoteConditionMode.ALL,
        kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        outcome=selected_outcome,
    )
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="distinct underlying identities",
    ):
        _terms(
            structured_terms=_structured_terms_with_participation_candidates(
                same_reference=True
            ),
            branches=(
                first,
                _branch(
                    2,
                    condition_ids=(),
                    mode=None,
                    kind=note.StructuredNoteOutcomeKind.REDEMPTION,
                ),
            ),
        )


def test_singleton_any_canonicalizes_to_all() -> None:
    branch = _branch(
        1,
        condition_ids=(201,),
        mode=note.StructuredNoteConditionMode.ANY,
        kind=note.StructuredNoteOutcomeKind.REDEMPTION,
    )
    assert branch.condition_mode is note.StructuredNoteConditionMode.ALL
    assert branch.logical_values()[2] == "all"


def test_singleton_all_and_any_collapse_to_duplicate_signature() -> None:
    branches = (
        _branch(
            1,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ALL,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
        _branch(
            2,
            condition_ids=(201,),
            mode=note.StructuredNoteConditionMode.ANY,
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        ),
        _branch(
            3,
            condition_ids=(),
            mode=None,
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
    )
    with pytest.raises(
        note.StructuredNotePayoffValidationError,
        match="signatures must be unique",
    ):
        _terms(branches=branches)
