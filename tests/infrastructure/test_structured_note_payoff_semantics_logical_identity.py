from __future__ import annotations

from dataclasses import fields
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import qore.infrastructure.structured_hybrid_synthetic_semantics as structured
import qore.infrastructure.structured_note_payoff_semantics as note
import qore.infrastructure.universal_instrument_identity as identity


def _economic_id(seed: int) -> identity.EconomicIdentityId:
    return identity.EconomicIdentityId(UUID(int=seed))


def _feature_id(seed: int) -> structured.StructuredFeatureId:
    return structured.StructuredFeatureId(UUID(int=seed))


def _evidence(seed: int) -> structured.StructuredEvidenceRef:
    return structured.StructuredEvidenceRef(UUID(int=seed))


def _component(
    root: identity.EconomicIdentityId,
    target: identity.EconomicIdentityId,
    *,
    relationship_id: int,
    role: str,
    ordinal: int,
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
            evidence_ref=identity.IdentityEvidenceRef(
                UUID(int=relationship_id + 10_000)
            ),
            ordinal=ordinal,
        ),
        role=structured.StructuredComponentRoleCode(role),
        evidence_ref=_evidence(relationship_id + 20_000),
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
    reference = _economic_id(2)
    redemption = _economic_id(3)
    participation = _economic_id(4)
    conversion = _economic_id(5)
    components = (
        _component(root, reference, relationship_id=101, role="reference", ordinal=5),
        _component(root, redemption, relationship_id=102, role="redemption", ordinal=2),
        _component(root, participation, relationship_id=103, role="participation", ordinal=8),
        _component(root, conversion, relationship_id=104, role="conversion", ordinal=9),
    )
    observation = structured.StructuredObservationTerms(
        mode=structured.StructuredObservationMode.DISCRETE,
        explicit_dates=(date(2030, 6, 3),),
    )
    features: tuple[structured.StructuredFeature, ...] = (
        structured.StructuredBarrierFeature(
            feature_id=_feature_id(201),
            reference_identity_id=reference,
            barrier_kind=structured.StructuredBarrierKindCode("initial-level-test"),
            direction=structured.StructuredBarrierDirection.AT_OR_ABOVE,
            level=_level(reference, "100"),
            observation=observation,
            evidence_ref=_evidence(301),
        ),
        structured.StructuredBarrierFeature(
            feature_id=_feature_id(202),
            reference_identity_id=reference,
            barrier_kind=structured.StructuredBarrierKindCode("downside-threshold"),
            direction=structured.StructuredBarrierDirection.AT_OR_ABOVE,
            level=_level(reference, "70"),
            observation=observation,
            evidence_ref=_evidence(302),
        ),
        structured.StructuredRedemptionFeature(
            feature_id=_feature_id(203),
            redemption_identity_id=redemption,
            redemption_ratio=structured.StructuredPositiveRatio(Decimal("1")),
            redemption_date=date(2030, 6, 7),
            evidence_ref=_evidence(303),
        ),
        structured.StructuredParticipationFeature(
            feature_id=_feature_id(204),
            reference_identity_id=participation,
            direction=structured.StructuredParticipationDirection.POSITIVE,
            participation_ratio=structured.StructuredPositiveRatio(Decimal("1.75")),
            evidence_ref=_evidence(304),
        ),
        structured.StructuredConversionFeature(
            feature_id=_feature_id(205),
            target_identity_id=conversion,
            units_per_source_unit=structured.StructuredPositiveRatio(Decimal("2.5")),
            evidence_ref=_evidence(305),
            conversion_level=None,
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
) -> note.StructuredNotePayoffOutcome:
    if kind is note.StructuredNoteOutcomeKind.REDEMPTION:
        return note.StructuredNotePayoffOutcome(
            kind=kind,
            redemption_feature_id=_feature_id(203),
        )
    if kind is note.StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION:
        return note.StructuredNotePayoffOutcome(
            kind=kind,
            redemption_feature_id=_feature_id(203),
            participation_feature_id=_feature_id(204),
        )
    if kind is note.StructuredNoteOutcomeKind.PARTICIPATION:
        return note.StructuredNotePayoffOutcome(
            kind=kind,
            participation_feature_id=_feature_id(204),
        )
    return note.StructuredNotePayoffOutcome(
        kind=kind,
        conversion_feature_id=_feature_id(205),
    )


def _branch(
    branch_seed: int,
    ordinal: int,
    *,
    mode: note.StructuredNoteConditionMode | None,
    conditions: tuple[int, ...],
    kind: note.StructuredNoteOutcomeKind,
) -> note.StructuredNotePayoffBranch:
    return note.StructuredNotePayoffBranch(
        branch_id=note.StructuredNotePayoffBranchId(UUID(int=branch_seed)),
        ordinal=ordinal,
        condition_mode=mode,
        condition_feature_ids=tuple(_feature_id(seed) for seed in conditions),
        outcome=_outcome(kind),
        evidence_ref=_evidence(branch_seed + 1_000),
    )


def _payoff_terms() -> note.StructuredNotePayoffTerms:
    branches = (
        _branch(
            401,
            1,
            mode=note.StructuredNoteConditionMode.ALL,
            conditions=(201,),
            kind=note.StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION,
        ),
        _branch(
            402,
            2,
            mode=note.StructuredNoteConditionMode.ALL,
            conditions=(202,),
            kind=note.StructuredNoteOutcomeKind.REDEMPTION,
        ),
        _branch(
            403,
            3,
            mode=None,
            conditions=(),
            kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        ),
    )
    return note.StructuredNotePayoffTerms(
        terms_id=note.StructuredNotePayoffTermsId(UUID(int=500)),
        structured_terms=_structured_terms(),
        branches=tuple(reversed(branches)),
        evidence_ref=_evidence(888),
    )


_EXPECTED_COMPONENT_101: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=101)),),
        (str(UUID(int=1)),),
        (str(UUID(int=2)),),
        ("structured-component",),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        (str(UUID(int=10_101)),),
        5,
    ),
    ("reference",),
    (str(UUID(int=20_101)),),
)
_EXPECTED_COMPONENT_102: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=102)),),
        (str(UUID(int=1)),),
        (str(UUID(int=3)),),
        ("structured-component",),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        (str(UUID(int=10_102)),),
        2,
    ),
    ("redemption",),
    (str(UUID(int=20_102)),),
)
_EXPECTED_COMPONENT_103: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=103)),),
        (str(UUID(int=1)),),
        (str(UUID(int=4)),),
        ("structured-component",),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        (str(UUID(int=10_103)),),
        8,
    ),
    ("participation",),
    (str(UUID(int=20_103)),),
)
_EXPECTED_COMPONENT_104: tuple[object, ...] = (
    (str(UUID(int=1)),),
    (
        (str(UUID(int=104)),),
        (str(UUID(int=1)),),
        (str(UUID(int=5)),),
        ("structured-component",),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        (str(UUID(int=10_104)),),
        9,
    ),
    ("conversion",),
    (str(UUID(int=20_104)),),
)

_EXPECTED_BARRIER_201: tuple[object, ...] = (
    "barrier",
    (str(UUID(int=201)),),
    (str(UUID(int=2)),),
    ("initial-level-test",),
    "at-or-above",
    ("100", "level", (str(UUID(int=2)),), ("index-points",)),
    ("discrete", ("2030-06-03",), None),
    (str(UUID(int=301)),),
)
_EXPECTED_BARRIER_202: tuple[object, ...] = (
    "barrier",
    (str(UUID(int=202)),),
    (str(UUID(int=2)),),
    ("downside-threshold",),
    "at-or-above",
    ("70", "level", (str(UUID(int=2)),), ("index-points",)),
    ("discrete", ("2030-06-03",), None),
    (str(UUID(int=302)),),
)
_EXPECTED_REDEMPTION: tuple[object, ...] = (
    "redemption",
    (str(UUID(int=203)),),
    (str(UUID(int=3)),),
    ("1",),
    "2030-06-07",
    (str(UUID(int=303)),),
)
_EXPECTED_PARTICIPATION: tuple[object, ...] = (
    "participation",
    (str(UUID(int=204)),),
    (str(UUID(int=4)),),
    "positive",
    ("1.75",),
    (str(UUID(int=304)),),
)
_EXPECTED_CONVERSION: tuple[object, ...] = (
    "conversion",
    (str(UUID(int=205)),),
    (str(UUID(int=5)),),
    ("2.5",),
    None,
    (str(UUID(int=305)),),
)
_EXPECTED_STRUCTURED_TERMS: tuple[object, ...] = (
    "structured-hybrid-synthetic",
    (str(UUID(int=10)),),
    (str(UUID(int=1)),),
    (
        _EXPECTED_COMPONENT_101,
        _EXPECTED_COMPONENT_102,
        _EXPECTED_COMPONENT_103,
        _EXPECTED_COMPONENT_104,
    ),
    (
        _EXPECTED_BARRIER_201,
        _EXPECTED_BARRIER_202,
        _EXPECTED_REDEMPTION,
        _EXPECTED_PARTICIPATION,
        _EXPECTED_CONVERSION,
    ),
    (str(UUID(int=999)),),
)

_EXPECTED_OUTCOME_REDEMPTION: tuple[object, ...] = (
    "redemption",
    (str(UUID(int=203)),),
    None,
    None,
)
_EXPECTED_OUTCOME_REDEMPTION_WITH_PARTICIPATION: tuple[object, ...] = (
    "redemption-with-participation",
    (str(UUID(int=203)),),
    (str(UUID(int=204)),),
    None,
)
_EXPECTED_OUTCOME_PARTICIPATION: tuple[object, ...] = (
    "participation",
    None,
    (str(UUID(int=204)),),
    None,
)
_EXPECTED_OUTCOME_CONVERSION: tuple[object, ...] = (
    "conversion",
    None,
    None,
    (str(UUID(int=205)),),
)

_EXPECTED_BRANCH_401: tuple[object, ...] = (
    (str(UUID(int=401)),),
    1,
    "all",
    ((str(UUID(int=201)),),),
    _EXPECTED_OUTCOME_REDEMPTION_WITH_PARTICIPATION,
    (str(UUID(int=1_401)),),
)
_EXPECTED_BRANCH_402: tuple[object, ...] = (
    (str(UUID(int=402)),),
    2,
    "all",
    ((str(UUID(int=202)),),),
    _EXPECTED_OUTCOME_REDEMPTION,
    (str(UUID(int=1_402)),),
)
_EXPECTED_BRANCH_403: tuple[object, ...] = (
    (str(UUID(int=403)),),
    3,
    None,
    (),
    _EXPECTED_OUTCOME_PARTICIPATION,
    (str(UUID(int=1_403)),),
)


def test_exact_dataclass_field_surface_is_frozen() -> None:
    assert tuple(field.name for field in fields(note.StructuredNotePayoffTermsId)) == (
        "value",
    )
    assert tuple(field.name for field in fields(note.StructuredNotePayoffBranchId)) == (
        "value",
    )
    assert tuple(
        field.name for field in fields(note.StructuredNoteParticipationSelection)
    ) == (
        "kind",
        "candidate_feature_ids",
    )
    assert tuple(field.name for field in fields(note.StructuredNotePayoffOutcome)) == (
        "kind",
        "redemption_feature_id",
        "participation_feature_id",
        "conversion_feature_id",
        "participation_selection",
    )
    assert tuple(field.name for field in fields(note.StructuredNotePayoffBranch)) == (
        "branch_id",
        "ordinal",
        "condition_mode",
        "condition_feature_ids",
        "outcome",
        "evidence_ref",
    )
    assert tuple(field.name for field in fields(note.StructuredNotePayoffTerms)) == (
        "terms_id",
        "structured_terms",
        "branches",
        "evidence_ref",
    )


def test_local_id_projections_are_independent() -> None:
    assert note.StructuredNotePayoffTermsId(UUID(int=500)).logical_values() == (
        str(UUID(int=500)),
    )
    assert note.StructuredNotePayoffBranchId(UUID(int=401)).logical_values() == (
        str(UUID(int=401)),
    )


def test_all_outcome_projections_are_independent() -> None:
    assert _outcome(note.StructuredNoteOutcomeKind.REDEMPTION).logical_values() == (
        _EXPECTED_OUTCOME_REDEMPTION
    )
    assert _outcome(
        note.StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION
    ).logical_values() == _EXPECTED_OUTCOME_REDEMPTION_WITH_PARTICIPATION
    assert _outcome(note.StructuredNoteOutcomeKind.PARTICIPATION).logical_values() == (
        _EXPECTED_OUTCOME_PARTICIPATION
    )
    assert _outcome(note.StructuredNoteOutcomeKind.CONVERSION).logical_values() == (
        _EXPECTED_OUTCOME_CONVERSION
    )


def test_conditional_and_fallback_branch_projections_are_independent() -> None:
    assert _branch(
        401,
        1,
        mode=note.StructuredNoteConditionMode.ALL,
        conditions=(201,),
        kind=note.StructuredNoteOutcomeKind.REDEMPTION_WITH_PARTICIPATION,
    ).logical_values() == _EXPECTED_BRANCH_401
    assert _branch(
        403,
        3,
        mode=None,
        conditions=(),
        kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
    ).logical_values() == _EXPECTED_BRANCH_403


def test_top_level_projection_is_complete_and_independent() -> None:
    assert _payoff_terms().logical_values() == (
        "structured-note-payoff",
        (str(UUID(int=500)),),
        _EXPECTED_STRUCTURED_TERMS,
        (
            _EXPECTED_BRANCH_401,
            _EXPECTED_BRANCH_402,
            _EXPECTED_BRANCH_403,
        ),
        (str(UUID(int=888)),),
    )


def test_condition_set_and_branch_order_are_canonical_without_expected_side_sut() -> None:
    first = _payoff_terms()
    branch = note.StructuredNotePayoffBranch(
        branch_id=note.StructuredNotePayoffBranchId(UUID(int=601)),
        ordinal=1,
        condition_mode=note.StructuredNoteConditionMode.ALL,
        condition_feature_ids=(_feature_id(202), _feature_id(201)),
        outcome=_outcome(note.StructuredNoteOutcomeKind.REDEMPTION),
        evidence_ref=_evidence(1_601),
    )
    fallback = note.StructuredNotePayoffBranch(
        branch_id=note.StructuredNotePayoffBranchId(UUID(int=602)),
        ordinal=2,
        condition_mode=None,
        condition_feature_ids=(),
        outcome=_outcome(note.StructuredNoteOutcomeKind.CONVERSION),
        evidence_ref=_evidence(1_602),
    )
    second = note.StructuredNotePayoffTerms(
        terms_id=note.StructuredNotePayoffTermsId(UUID(int=700)),
        structured_terms=_structured_terms(),
        branches=(fallback, branch),
        evidence_ref=_evidence(777),
    )

    assert first.branches[0].ordinal == 1
    assert second.branches[0].condition_feature_ids == (
        _feature_id(201),
        _feature_id(202),
    )
    assert second.logical_values() == (
        "structured-note-payoff",
        (str(UUID(int=700)),),
        _EXPECTED_STRUCTURED_TERMS,
        (
            (
                (str(UUID(int=601)),),
                1,
                "all",
                ((str(UUID(int=201)),), (str(UUID(int=202)),)),
                _EXPECTED_OUTCOME_REDEMPTION,
                (str(UUID(int=1_601)),),
            ),
            (
                (str(UUID(int=602)),),
                2,
                None,
                (),
                _EXPECTED_OUTCOME_CONVERSION,
                (str(UUID(int=1_602)),),
            ),
        ),
        (str(UUID(int=777)),),
    )


def test_worst_performing_selection_projection_is_independently_reconstructed() -> None:
    selection = note.StructuredNoteParticipationSelection(
        kind=note.StructuredNoteParticipationSelectionKind.WORST_PERFORMING_BY_RETURN,
        candidate_feature_ids=(_feature_id(208), _feature_id(207)),
    )
    assert selection.logical_values() == (
        "worst-performing-by-return",
        (
            (str(UUID(int=207)),),
            (str(UUID(int=208)),),
        ),
    )
    outcome = note.StructuredNotePayoffOutcome(
        kind=note.StructuredNoteOutcomeKind.PARTICIPATION,
        participation_selection=selection,
    )
    assert outcome.logical_values() == (
        "participation",
        None,
        (
            "worst-performing-by-return",
            (
                (str(UUID(int=207)),),
                (str(UUID(int=208)),),
            ),
        ),
        None,
    )


def test_singleton_any_projection_canonicalizes_to_all_independently() -> None:
    branch = note.StructuredNotePayoffBranch(
        branch_id=note.StructuredNotePayoffBranchId(UUID(int=801)),
        ordinal=1,
        condition_mode=note.StructuredNoteConditionMode.ANY,
        condition_feature_ids=(_feature_id(201),),
        outcome=_outcome(note.StructuredNoteOutcomeKind.REDEMPTION),
        evidence_ref=_evidence(1_801),
    )
    assert branch.logical_values() == (
        (str(UUID(int=801)),),
        1,
        "all",
        ((str(UUID(int=201)),),),
        _EXPECTED_OUTCOME_REDEMPTION,
        (str(UUID(int=1_801)),),
    )
