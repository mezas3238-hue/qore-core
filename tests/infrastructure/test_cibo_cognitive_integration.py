"""Provider-neutral CIBO Cognitive Integration Gate adversarial + property tests.

Covers IA-COG-FINAL-003/006: the reconciliation of Batch 006 (executive substrate)
with Batch 008 (complementary cognitive substrate) through reference/fingerprint/
identity seams only, plus the Correction-003 residuals — dangling replay rejection,
swapped UUID + wrong fingerprint rejection, disagreement-never-bounded-confidence,
all six uncertainty kinds, nested revalidation, single-construction builder, and
deterministic content binding.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_attention import CalibrationNote, ReasoningDepthHint
from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_evaluation import (
    CognitiveEvaluation,
    EvaluationDimension,
    EvaluationDimensionScore,
    evaluate_cognition,
)
from qore.infrastructure.cibo_cognitive_integration import (
    CiboCognitiveIntegrationValidationError,
    CiboIntegratedAttributionBinding,
    CiboIntegratedCognitiveEpisode,
    CiboIntegratedContentBinding,
    CiboIntegratedEvidenceBinding,
    CiboIntegratedReplay,
    CiboIntegratedSuitabilityBinding,
    bind_deliberation_role,
    bind_evaluation_reference,
    bind_evidence_fingerprint,
    bind_plan_reference,
    bind_reasoning_mode,
    bind_replay_reference,
    bind_synthesis_reference,
    bind_uncertainty_kind,
    bind_world_snapshot_reference,
    build_integrated_episode,
    replay_integrated_episode,
)
from qore.infrastructure.cibo_cognitive_planning import (
    CognitiveGoal,
    CognitiveGoalId,
    CognitiveGoalStatus,
    CognitivePlan,
    CognitiveTask,
    CognitiveTaskId,
    CognitiveTaskStatus,
    EvidenceRequirement,
    build_cognitive_plan,
)
from qore.infrastructure.cibo_cognitive_replay import (
    ReplayEpisode,
    ReplayToolCall,
    build_replay_episode,
)
from qore.infrastructure.cibo_cognitive_tools import FacultyId
from qore.infrastructure.cibo_cognitive_world_model import (
    WorldModelDomain,
    WorldModelReference,
    WorldModelReferenceStatus,
    WorldModelSnapshot,
    WorldModelSourceId,
    WorldModelSourceVersion,
    build_world_model_snapshot,
)
from qore.infrastructure.cibo_executive_deliberation import (
    CiboCouncilOutcome,
    CiboCouncilSynthesis,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboDeliberationRole,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)

_AWARE = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_ID = UUID("60000000-0000-0000-0000-000000000001")
_WORLD = UUID("60000000-0000-0000-0000-000000000002")
_SYNTH = UUID("60000000-0000-0000-0000-000000000003")
_OTHER = UUID("60000000-0000-0000-0000-000000000099")

_AUTHORITY_FIELDS = frozenset(
    {
        "order",
        "intent",
        "execution",
        "risk",
        "provider",
        "promotion",
        "demo",
        "live",
        "production",
        "capital",
        "account",
        "credential",
        "secret",
        "token",
        "authorization",
        "quantity",
    }
)


def _fp(seed: str) -> CiboCognitiveFingerprint:
    return fingerprint_material(seed)


def _binding(seed: str) -> CiboIntegratedEvidenceBinding:
    return bind_evidence_fingerprint(_fp(seed))


def _content_binding(seed: str) -> CiboIntegratedContentBinding:
    return CiboIntegratedContentBinding(id=_WORLD, fingerprint=_fp(seed))


def _bounded_confidence() -> CiboConfidence:
    return CiboConfidence(
        level=CiboConfidenceLevel.MEDIUM,
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:bounded"),),
    )


def _world_reference() -> WorldModelReference:
    return WorldModelReference(
        domain=WorldModelDomain.MARKET,
        source_id=WorldModelSourceId("source-a"),
        source_version=WorldModelSourceVersion("1"),
        as_of=_AWARE,
        status=WorldModelReferenceStatus.CURRENT,
        evidence_fingerprint=fingerprint_material("source-a:1"),
        evidence_label="provider-neutral market evidence",
    )


def _world_snapshot() -> WorldModelSnapshot:
    return build_world_model_snapshot(
        snapshot_id=_WORLD, as_of=_AWARE, references=[_world_reference()]
    )


def _synthesis() -> CiboCouncilSynthesis:
    return CiboCouncilSynthesis(
        synthesis_id=_SYNTH,
        summary="Executive synthesis",
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:synthesis"),),
        uncertainty=CiboUncertainty(kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE),
        synthesized_at=_AWARE,
    )


def _evaluation() -> CognitiveEvaluation:
    return evaluate_cognition(
        evaluation_id=_SYNTH,
        evaluated_reference="subject-demo",
        dimensions=(
            EvaluationDimensionScore(
                dimension=EvaluationDimension.EVIDENCE_SUFFICIENCY, score=80, note="sufficient"
            ),
        ),
        evidence_refs=("evidence:demo",),
    )


def _plan() -> CognitivePlan:
    goal = CognitiveGoal(
        goal_id=CognitiveGoalId(_WORLD), description="goal", status=CognitiveGoalStatus.PENDING
    )
    task = CognitiveTask(
        task_id=CognitiveTaskId(_SYNTH),
        goal_id=goal.goal_id,
        description="task",
        dependencies=(),
        required_evidence=(EvidenceRequirement(reference="ev-1"),),
        status=CognitiveTaskStatus.PENDING,
    )
    return build_cognitive_plan(plan_id=_ID, goals=[goal], tasks=[task])


def _replay() -> ReplayEpisode:
    return build_replay_episode(
        episode_id=_ID,
        recorded_at=_AWARE,
        world_snapshot_id=_WORLD,
        goal_plan_state="planning",
        evidence_refs=("evidence:demo",),
    )


def _tool_call() -> ReplayToolCall:
    return ReplayToolCall(
        request_id=_WORLD,
        input_fingerprint=_fp("tool-input"),
        result_fingerprint=_fp("tool-output"),
    )


def _episode(
    *,
    evidence_bindings: tuple[CiboIntegratedEvidenceBinding, ...] | None = None,
    reasoning_mode: CiboReasoningMode = CiboReasoningMode.HIGH,
    recorded_at: datetime = _AWARE,
    world_snapshot: CiboIntegratedContentBinding | None = None,
    memory_refs: tuple[UUID, ...] = (),
    deliberation_outcome: CiboCouncilOutcome | None = None,
    synthesis: CiboIntegratedContentBinding | None = None,
    replay: CiboIntegratedContentBinding | None = None,
    evaluation: CiboIntegratedContentBinding | None = None,
    plan_reference: CiboIntegratedContentBinding | None = None,
    tool_calls: tuple[ReplayToolCall, ...] = (),
    uncertainty: CiboUncertainty | None = None,
    trader_suitability: CiboIntegratedSuitabilityBinding | None = None,
    intervention_attribution: CiboIntegratedAttributionBinding | None = None,
) -> CiboIntegratedCognitiveEpisode:
    return build_integrated_episode(
        integration_id=_ID,
        reasoning_mode=reasoning_mode,
        evidence_bindings=evidence_bindings if evidence_bindings is not None else (_binding("a"),),
        recorded_at=recorded_at,
        world_snapshot=world_snapshot,
        memory_refs=memory_refs,
        deliberation_outcome=deliberation_outcome,
        synthesis=synthesis,
        replay=replay,
        evaluation=evaluation,
        plan_reference=plan_reference,
        tool_calls=tool_calls,
        uncertainty=uncertainty,
        trader_suitability=trader_suitability,
        intervention_attribution=intervention_attribution,
    )


def _assert_no_authority_fields(obj: object, path: str = "root") -> None:
    assert dataclasses.is_dataclass(obj), f"{path} is not a frozen dataclass"
    field_map = getattr(obj, "__dataclass_fields__", {})
    overlap = set(field_map) & _AUTHORITY_FIELDS
    assert not overlap, f"{path} carries authority-bearing fields: {sorted(overlap)}"
    for name in field_map:
        value = getattr(obj, name)
        if dataclasses.is_dataclass(value):
            _assert_no_authority_fields(value, path=f"{path}.{name}")
        elif isinstance(value, tuple):
            for index, item in enumerate(value):
                if dataclasses.is_dataclass(item):
                    _assert_no_authority_fields(item, path=f"{path}.{name}[{index}]")


class TestReasoningModeBinding:
    def test_maps_each_depth_hint_to_exact_mode(self) -> None:
        expected = {
            "fast": CiboReasoningMode.FAST,
            "high": CiboReasoningMode.HIGH,
            "max": CiboReasoningMode.MAX,
            "council_adversarial": CiboReasoningMode.COUNCIL_ADVERSARIAL,
        }
        for token, mode in expected.items():
            assert bind_reasoning_mode(ReasoningDepthHint(token)) is mode

    def test_council_hint_is_normalized_hyphen_not_underscore(self) -> None:
        mode = bind_reasoning_mode(ReasoningDepthHint("council_adversarial"))
        assert mode is CiboReasoningMode.COUNCIL_ADVERSARIAL
        assert mode.value == "council-adversarial"

    def test_is_deterministic(self) -> None:
        assert bind_reasoning_mode(ReasoningDepthHint("max")) is bind_reasoning_mode(
            ReasoningDepthHint("max")
        )

    def test_rejects_non_hint_type(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_reasoning_mode(cast(ReasoningDepthHint, "fast"))


class TestEvidenceFingerprintBinding:
    def test_binds_verbatim_hex_under_sha256_namespace(self) -> None:
        digest = "a" * 64
        binding = bind_evidence_fingerprint(CiboCognitiveFingerprint(digest))
        assert binding.fingerprint.value == digest
        assert binding.evidence_ref.value == f"sha256:{digest}"

    def test_mismatched_pair_fails_closed(self) -> None:
        with pytest.raises(
            CiboCognitiveIntegrationValidationError,
            match="mismatch|does not match",
        ):
            CiboIntegratedEvidenceBinding(
                fingerprint=CiboCognitiveFingerprint("a" * 64),
                evidence_ref=CiboCognitiveEvidenceRef(f"sha256:{'b' * 64}"),
            )

    def test_rejects_fingerprint_subclass(self) -> None:
        class EvilFingerprint(CiboCognitiveFingerprint):
            def revalidate(self) -> None:
                pass

        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_evidence_fingerprint(EvilFingerprint("a" * 64))


class TestDeliberationRoleBinding:
    def test_binds_canonical_faculty_id_to_role(self) -> None:
        role = bind_deliberation_role(FacultyId("macro-analysis"))
        assert isinstance(role, CiboDeliberationRole)
        assert role.value == "macro-analysis"

    def test_fails_closed_on_non_canonical_identity(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_deliberation_role(FacultyId("MacroAnalysis"))


class TestUncertaintyKindBinding:
    def test_abstention_maps_to_abstain_defer(self) -> None:
        note = CalibrationNote(confidence_band=40, note="volatile", abstention_required=True)
        assert bind_uncertainty_kind(note) is CiboUncertaintyKind.ABSTAIN_DEFER

    def test_non_abstention_maps_to_bounded_confidence(self) -> None:
        note = CalibrationNote(confidence_band=70, note="stable", abstention_required=False)
        assert bind_uncertainty_kind(note) is CiboUncertaintyKind.BOUNDED_CONFIDENCE

    def test_zero_confidence_is_not_positive_bounded_confidence(self) -> None:
        note = CalibrationNote(confidence_band=0, note="none", abstention_required=False)
        assert bind_uncertainty_kind(note) is CiboUncertaintyKind.INSUFFICIENT_EVIDENCE

    def test_covers_all_six_kinds(self) -> None:
        expected = {
            "insufficient_evidence": CiboUncertaintyKind.INSUFFICIENT_EVIDENCE,
            "unresolved_contradiction": CiboUncertaintyKind.UNRESOLVED_CONTRADICTION,
            "competing_hypotheses": CiboUncertaintyKind.COMPETING_HYPOTHESES,
            "more_evidence_requested": CiboUncertaintyKind.MORE_EVIDENCE_REQUESTED,
            "abstain_defer": CiboUncertaintyKind.ABSTAIN_DEFER,
            "bounded_confidence": CiboUncertaintyKind.BOUNDED_CONFIDENCE,
        }
        for token, kind in expected.items():
            note = CalibrationNote(
                confidence_band=50, note="n", abstention_required=False, kind=token
            )
            assert bind_uncertainty_kind(note) is kind

    def test_rejects_unknown_kind_token(self) -> None:
        with pytest.raises(CiboCognitiveValidationError):
            CalibrationNote(confidence_band=50, note="n", abstention_required=False, kind="bogus")

    def test_rejects_non_note_type(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_uncertainty_kind(cast(CalibrationNote, object()))


class TestContentBinding:
    def test_rejects_non_uuid_id(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            CiboIntegratedContentBinding(id=cast(UUID, "x"), fingerprint=_fp("a"))

    def test_rejects_wrong_fingerprint_type(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            CiboIntegratedContentBinding(
                id=_WORLD, fingerprint=cast(CiboCognitiveFingerprint, "not-a-fingerprint")
            )

    def test_world_snapshot_reference_rejects_swapped_content(self) -> None:
        good = _world_snapshot()
        evil = WorldModelSnapshot(
            snapshot_id=good.snapshot_id,
            as_of=good.as_of,
            staleness_threshold=good.staleness_threshold,
            references=(_world_reference(),),
            contradictions=good.contradictions,
            fingerprint=good.fingerprint,
        )
        # swap the retained reference under the same id/fingerprint
        swapped = WorldModelReference(
            domain=WorldModelDomain.MARKET,
            source_id=WorldModelSourceId("source-b"),
            source_version=WorldModelSourceVersion("2"),
            as_of=_AWARE,
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=fingerprint_material("source-b:2"),
            evidence_label="swapped",
        )
        object.__setattr__(evil, "references", (swapped,))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_world_snapshot_reference(evil)

    def test_world_snapshot_reference_binds_canonical_fingerprint(self) -> None:
        binding = bind_world_snapshot_reference(_world_snapshot())
        assert binding.id == _WORLD
        assert binding.fingerprint == _world_snapshot().fingerprint

    def test_synthesis_reference_binds_content_fingerprint(self) -> None:
        binding = bind_synthesis_reference(_synthesis())
        assert binding.id == _SYNTH
        assert binding.fingerprint == fingerprint_material(_synthesis().logical_values())

    def test_evaluation_reference_binds_content_fingerprint(self) -> None:
        first = bind_evaluation_reference(_evaluation())
        assert first.fingerprint != _fp("other")
        other = evaluate_cognition(
            evaluation_id=_SYNTH,
            evaluated_reference="other-reference",
            dimensions=(
                EvaluationDimensionScore(
                    dimension=EvaluationDimension.EVIDENCE_SUFFICIENCY, score=80, note="sufficient"
                ),
            ),
            evidence_refs=("evidence:demo",),
        )
        assert bind_evaluation_reference(other).fingerprint != first.fingerprint

    def test_plan_reference_binds_content_fingerprint(self) -> None:
        binding = bind_plan_reference(_plan())
        assert binding.id == _ID
        assert binding.fingerprint is not None

    def test_replay_reference_requires_matching_episode_id(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="replay"):
            bind_replay_reference(_replay(), integration_id=_OTHER)

    def test_replay_reference_rejects_forged_self_fingerprint(self) -> None:
        replay = _replay()
        object.__setattr__(replay, "fingerprint", CiboCognitiveFingerprint("f" * 64))
        with pytest.raises(CiboCognitiveValidationError):
            bind_replay_reference(replay, integration_id=_ID)


class TestIntegratedEpisodeComposition:
    def test_is_deterministic_same_input_same_fingerprint(self) -> None:
        first = _episode()
        second = _episode()
        assert first.fingerprint == second.fingerprint
        assert first.logical_values() == second.logical_values()

    def test_evidence_bindings_are_canonically_ordered(self) -> None:
        episode = _episode(evidence_bindings=(_binding("z"), _binding("a"), _binding("m")))
        values = [binding.fingerprint.value for binding in episode.evidence_bindings]
        assert values == sorted(values)

    def test_permutation_invariance(self) -> None:
        a = _episode(evidence_bindings=(_binding("a"), _binding("b")))
        b = _episode(evidence_bindings=(_binding("b"), _binding("a")))
        assert a.fingerprint == b.fingerprint

    def test_permutation_invariance_extends_to_tool_calls(self) -> None:
        c1 = ReplayToolCall(request_id=_WORLD, input_fingerprint=_fp("i1"), result_fingerprint=None)
        c2 = ReplayToolCall(request_id=_SYNTH, input_fingerprint=_fp("i2"), result_fingerprint=None)
        a = _episode(tool_calls=(c1, c2))
        b = _episode(tool_calls=(c2, c1))
        assert a.fingerprint == b.fingerprint
        assert a.logical_values() == b.logical_values()

    def test_duplicate_evidence_bindings_rejected(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="duplicate"):
            _episode(evidence_bindings=(_binding("a"), _binding("a")))

    def test_duplicate_tool_calls_rejected(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="duplicate"):
            _episode(tool_calls=(_tool_call(), _tool_call()))

    def test_duplicate_memory_refs_rejected(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="duplicate"):
            _episode(memory_refs=(_WORLD, _WORLD))

    def test_fingerprint_mismatch_rejected(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="fingerprint"):
            CiboIntegratedCognitiveEpisode(
                integration_id=_ID,
                reasoning_mode=CiboReasoningMode.HIGH,
                evidence_bindings=(_binding("a"),),
                recorded_at=_AWARE,
                fingerprint=CiboCognitiveFingerprint("c" * 64),
            )

    def test_missing_evidence_fails_closed(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="evidence"):
            _episode(evidence_bindings=())

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="timezone"):
            _episode(recorded_at=datetime(2026, 8, 9, 0, 0))

    def test_world_snapshot_binding_preserved(self) -> None:
        binding = bind_world_snapshot_reference(_world_snapshot())
        episode = _episode(world_snapshot=binding)
        assert episode.world_snapshot is binding

    def test_non_binding_world_snapshot_rejected(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            _episode(world_snapshot=cast(CiboIntegratedContentBinding, "not-a-binding"))

    def test_replay_binding_requires_matching_integration_id(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="replay"):
            _episode(replay=CiboIntegratedContentBinding(id=_OTHER, fingerprint=_fp("r")))

    def test_builder_rejects_non_binding_item(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            build_integrated_episode(
                integration_id=_ID,
                reasoning_mode=CiboReasoningMode.HIGH,
                evidence_bindings=cast(
                    list[CiboIntegratedEvidenceBinding],
                    [_binding("a"), "not-a-binding"],
                ),
                recorded_at=_AWARE,
            )

    def test_builder_round_trips_every_field(self) -> None:
        world = bind_world_snapshot_reference(_world_snapshot())
        synthesis = bind_synthesis_reference(_synthesis())
        replay = bind_replay_reference(_replay(), integration_id=_ID)
        evaluation = bind_evaluation_reference(_evaluation())
        plan_ref = bind_plan_reference(_plan())
        episode = _episode(
            world_snapshot=world,
            deliberation_outcome=CiboCouncilOutcome.DECISION,
            synthesis=synthesis,
            replay=replay,
            evaluation=evaluation,
            plan_reference=plan_ref,
            tool_calls=(_tool_call(),),
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
                confidence=_bounded_confidence(),
            ),
        )
        assert episode.world_snapshot is world
        assert episode.synthesis is synthesis
        assert episode.replay is replay
        assert episode.evaluation is evaluation
        assert episode.plan_reference is plan_ref
        assert episode.tool_calls == (_tool_call(),)
        assert episode.uncertainty is not None
        assert episode.fingerprint == fingerprint_material(episode.logical_values())


class TestDisagreementAndUncertaintyPreservation:
    def test_disagreement_outcome_forbids_synthesis(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="disagreement"):
            _episode(
                deliberation_outcome=CiboCouncilOutcome.DISAGREEMENT,
                synthesis=_content_binding("s"),
            )

    def test_synthesis_requires_decision_outcome(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="decision"):
            _episode(synthesis=_content_binding("s"))

    def test_decision_outcome_with_synthesis_is_preserved(self) -> None:
        binding = _content_binding("s")
        episode = _episode(
            deliberation_outcome=CiboCouncilOutcome.DECISION,
            synthesis=binding,
        )
        assert episode.synthesis is binding
        assert episode.deliberation_outcome is CiboCouncilOutcome.DECISION

    def test_disagreement_forbids_bounded_confidence(self) -> None:
        for outcome in (
            CiboCouncilOutcome.DISAGREEMENT,
            CiboCouncilOutcome.NO_DECISION,
            CiboCouncilOutcome.BLOCKED,
        ):
            with pytest.raises(
                CiboCognitiveIntegrationValidationError, match="bounded confidence"
            ):
                _episode(
                    deliberation_outcome=outcome,
                    uncertainty=CiboUncertainty(
                        kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
                        confidence=_bounded_confidence(),
                    ),
                )

    def test_disagreement_preserved_with_non_bounded_uncertainty(self) -> None:
        episode = _episode(
            deliberation_outcome=CiboCouncilOutcome.DISAGREEMENT,
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.UNRESOLVED_CONTRADICTION, detail_codes=("contradiction",)
            ),
        )
        assert episode.uncertainty is not None
        assert episode.uncertainty.kind is CiboUncertaintyKind.UNRESOLVED_CONTRADICTION

    def test_uncertainty_preserved_in_logical_values(self) -> None:
        episode = _episode(
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.UNRESOLVED_CONTRADICTION, detail_codes=("c",)
            )
        )
        assert episode.uncertainty is not None
        assert episode.logical_values()[-1] == episode.uncertainty.logical_values()

    def test_episode_rejects_reflectively_corrupted_uncertainty(self) -> None:
        episode = _episode(
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.UNRESOLVED_CONTRADICTION, detail_codes=("c",)
            )
        )
        object.__setattr__(episode.uncertainty, "detail_codes", ())
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            replay_integrated_episode(episode)


class TestReplayEquivalence:
    def test_replay_reconstructs_identical_view_and_fingerprint(self) -> None:
        episode = _episode(memory_refs=(_WORLD,))
        replay = replay_integrated_episode(episode)
        assert isinstance(replay, CiboIntegratedReplay)
        assert replay.view == episode.logical_values()
        assert replay.fingerprint == episode.fingerprint

    def test_replay_rejects_tampered_episode(self) -> None:
        episode = _episode()
        object.__setattr__(episode.evidence_bindings[0].evidence_ref, "value", "sha256:deadbeef")
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            replay_integrated_episode(episode)

    def test_no_dangling_replay_fingerprint_field(self) -> None:
        assert not hasattr(_episode(), "replay_fingerprint")

    def test_changed_referenced_content_invalidates_fingerprint(self) -> None:
        a = _episode(world_snapshot=CiboIntegratedContentBinding(id=_WORLD, fingerprint=_fp("w1")))
        b = _episode(world_snapshot=CiboIntegratedContentBinding(id=_WORLD, fingerprint=_fp("w2")))
        assert a.fingerprint != b.fingerprint


class TestAuthorityFreeFirewall:
    def test_integrated_episode_is_authority_free(self) -> None:
        _assert_no_authority_fields(_episode())

    def test_content_binding_is_authority_free(self) -> None:
        _assert_no_authority_fields(_content_binding("a"))

    def test_no_authority_bearing_output_created_by_integrated_cognition(self) -> None:
        episode = _episode(
            deliberation_outcome=CiboCouncilOutcome.DECISION,
            synthesis=_content_binding("s"),
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
                confidence=_bounded_confidence(),
            ),
        )
        view = episode.logical_values()
        assert not any(hasattr(episode, name) for name in _AUTHORITY_FIELDS)
        for item in view:
            assert item is None or isinstance(item, (str, tuple))

    def test_logical_view_fingerprints_deterministically(self) -> None:
        episode = _episode()
        assert episode.fingerprint == fingerprint_material(episode.logical_values())


class TestMarketTraderAndAttributionBindings:
    def test_suitability_binding_rejects_non_uuid(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            CiboIntegratedSuitabilityBinding(
                suitability_id=cast(UUID, "not-a-uuid"), fingerprint=_fp("suit")
            )

    def test_attribution_binding_rejects_non_fingerprint(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            CiboIntegratedAttributionBinding(
                attribution_id=_SYNTH,
                fingerprint=cast(CiboCognitiveFingerprint, "not-a-fingerprint"),
            )

    def test_episode_with_new_bindings_builds_and_replays(self) -> None:
        suit = CiboIntegratedSuitabilityBinding(suitability_id=_WORLD, fingerprint=_fp("suit"))
        attr = CiboIntegratedAttributionBinding(attribution_id=_SYNTH, fingerprint=_fp("attr"))
        episode = build_integrated_episode(
            integration_id=_ID,
            reasoning_mode=CiboReasoningMode.HIGH,
            evidence_bindings=(_binding("a"),),
            recorded_at=_AWARE,
            trader_suitability=suit,
            intervention_attribution=attr,
        )
        replay = replay_integrated_episode(episode)
        assert replay.fingerprint == episode.fingerprint
        assert replay.view == episode.logical_values()

    def test_new_bindings_are_authority_free(self) -> None:
        suit = CiboIntegratedSuitabilityBinding(suitability_id=_WORLD, fingerprint=_fp("suit"))
        attr = CiboIntegratedAttributionBinding(attribution_id=_SYNTH, fingerprint=_fp("attr"))
        for binding in (suit, attr):
            assert not any(hasattr(binding, name) for name in _AUTHORITY_FIELDS)
