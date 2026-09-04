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
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_attention import CalibrationNote, ReasoningDepthHint
from qore.infrastructure.cibo_cognitive_causality import (
    CausalClaim,
    CausalClaimKind,
    CausalClaimStatus,
    CausalClaimStrength,
    CausalEvidence,
    CausalEvidencePolarity,
    CausalVariable,
    build_causal_claim,
)
from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    TraderSubject,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_evaluation import (
    CapabilityEvidence,
    CapabilityOutcome,
    CognitiveEvaluation,
    EvaluationDimension,
    EvaluationDimensionScore,
    InterventionIdentity,
    InterventionKind,
    TraderDevelopmentAttribution,
    build_trader_development_attribution,
    capability_evidence_fingerprint,
    evaluate_cognition,
)
from qore.infrastructure.cibo_cognitive_hypotheses import (
    Hypothesis,
    HypothesisEvidence,
    HypothesisEvidencePolarity,
    HypothesisStatus,
    build_hypothesis,
    transition_hypothesis,
)
from qore.infrastructure.cibo_cognitive_integration import (
    CiboCognitiveIntegrationValidationError,
    CiboIntegratedCognitiveEpisode,
    CiboIntegratedContentBinding,
    CiboIntegratedEvidenceBinding,
    CiboIntegratedReplay,
    bind_attribution_reference,
    bind_causal_claim_reference,
    bind_deliberation_role,
    bind_evaluation_reference,
    bind_evidence_fingerprint,
    bind_hypothesis_reference,
    bind_learning_record_reference,
    bind_metacognitive_audit_reference,
    bind_metacognitive_reasoning_mode,
    bind_plan_reference,
    bind_reasoning_mode,
    bind_replay_reference,
    bind_scenario_reference,
    bind_suitability_reference,
    bind_synthesis_reference,
    bind_uncertainty_kind,
    bind_world_snapshot_reference,
    build_integrated_episode,
    replay_integrated_episode,
)
from qore.infrastructure.cibo_cognitive_metacognition import (
    MetacognitiveAudit,
    MetacognitiveFinding,
    ReasoningTransition,
    build_metacognitive_audit,
    build_reasoning_transition,
)
from qore.infrastructure.cibo_cognitive_planning import (
    CognitiveGoal,
    CognitiveGoalId,
    CognitiveGoalStatus,
    CognitiveLearningRecord,
    CognitivePlan,
    CognitiveTask,
    CognitiveTaskId,
    CognitiveTaskStatus,
    EvidenceBundle,
    EvidenceRequirement,
    build_cognitive_plan,
)
from qore.infrastructure.cibo_cognitive_replay import (
    ReplayEpisode,
    ReplayToolCall,
    build_replay_episode,
)
from qore.infrastructure.cibo_cognitive_scenarios import (
    Scenario,
    ScenarioAlternative,
    ScenarioAssumption,
    ScenarioFactKind,
    ScenarioFamily,
    build_scenario,
)
from qore.infrastructure.cibo_cognitive_tools import FacultyId
from qore.infrastructure.cibo_cognitive_world_model import (
    MarketContextKind,
    MarketContextReference,
    MarketTraderContext,
    MarketTraderSuitability,
    MarketTraderSuitabilityDisposition,
    WorldModelDomain,
    WorldModelReference,
    WorldModelReferenceStatus,
    WorldModelSnapshot,
    WorldModelSourceId,
    WorldModelSourceVersion,
    build_market_trader_suitability,
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
_T_PRE = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
_T_INT = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)
_T_POST = datetime(2026, 8, 8, 0, 0, tzinfo=UTC)
_CAUSAL = UUID("60000000-0000-0000-0000-000000000010")
_CORR = UUID("60000000-0000-0000-0000-000000000011")
_HYP = UUID("60000000-0000-0000-0000-000000000012")
_HYP_COMPETING = UUID("60000000-0000-0000-0000-000000000013")
_LEARN = UUID("60000000-0000-0000-0000-000000000014")
_AUDIT_ID = UUID("60000000-0000-0000-0000-000000000015")
_SCEN_BASE = UUID("60000000-0000-0000-0000-000000000016")
_SCEN_ADVERSE = UUID("60000000-0000-0000-0000-000000000017")
_SCEN_EXTREME = UUID("60000000-0000-0000-0000-000000000018")
_SCEN_REGIME = UUID("60000000-0000-0000-0000-000000000019")
_ALT = UUID("60000000-0000-0000-0000-000000000020")

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
        uncertainty=CiboUncertainty(
            kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE, confidence=_bounded_confidence()
        ),
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


def _trader_subject() -> TraderSubject:
    trader_id = "trader.demo"
    version = "v1"
    return TraderSubject(
        trader_id=trader_id,
        trader_version=version,
        fingerprint=fingerprint_material((trader_id, version)),
    )


def _ctx_ref(kind: MarketContextKind, reference: str) -> MarketContextReference:
    return MarketContextReference(
        kind=kind,
        reference=reference,
        as_of=_AWARE,
        status=WorldModelReferenceStatus.CURRENT,
        evidence_fingerprint=fingerprint_material((kind.value, reference)),
        evidence_label=f"{kind.value} evidence",
    )


def _suitability() -> MarketTraderSuitability:
    context = MarketTraderContext(
        market=_ctx_ref(MarketContextKind.MARKET, "market.fx"),
        instrument=_ctx_ref(MarketContextKind.INSTRUMENT, "instrument.eurusd"),
        regime=_ctx_ref(MarketContextKind.REGIME, "regime.trending"),
    )
    return build_market_trader_suitability(
        suitability_id=_WORLD,
        trader=_trader_subject(),
        context=context,
        disposition=MarketTraderSuitabilityDisposition.DEGRADED,
        evidence_lineage=(_fp("lineage"),),
    )


def _intervention(trader: TraderSubject) -> InterventionIdentity:
    return InterventionIdentity(
        intervention_id="cibo.dev",
        intervention_version="v1",
        target_trader_fingerprint=trader.fingerprint,
        kind=InterventionKind.DEVELOPMENT,
        fingerprint=fingerprint_material(
            ("cibo.dev", "v1", trader.fingerprint.value, InterventionKind.DEVELOPMENT.value)
        ),
    )


def _attribution() -> TraderDevelopmentAttribution:
    trader = _trader_subject()
    pre = CapabilityEvidence(
        reference="ev.pre",
        capability="discipline",
        observed_at=_T_PRE,
        evidence_fingerprint=capability_evidence_fingerprint(
            reference="ev.pre", capability="discipline", observed_at=_T_PRE
        ),
    )
    post = CapabilityEvidence(
        reference="ev.post",
        capability="discipline",
        observed_at=_T_POST,
        evidence_fingerprint=capability_evidence_fingerprint(
            reference="ev.post",
            capability="discipline",
            observed_at=_T_POST,
            outcome=CapabilityOutcome.IMPROVED,
        ),
        outcome=CapabilityOutcome.IMPROVED,
    )
    return build_trader_development_attribution(
        attribution_id=_SYNTH,
        trader=trader,
        intervention=_intervention(trader),
        development_hypothesis="training improves discipline",
        target_capability="discipline",
        applied_at=_T_INT,
        pre_intervention_evidence=(pre,),
        post_intervention_evidence=(post,),
    )


def _episode(
    *,
    evidence_bindings: tuple[CiboIntegratedEvidenceBinding, ...] | None = None,
    reasoning_mode: CiboReasoningMode = CiboReasoningMode.HIGH,
    recorded_at: datetime = _AWARE,
    world_snapshot: WorldModelSnapshot | None = None,
    memory_refs: tuple[UUID, ...] = (),
    deliberation_outcome: CiboCouncilOutcome | None = None,
    synthesis: CiboCouncilSynthesis | None = None,
    replay: ReplayEpisode | None = None,
    evaluation: CognitiveEvaluation | None = None,
    plan_reference: CognitivePlan | None = None,
    tool_calls: tuple[ReplayToolCall, ...] = (),
    uncertainty: CiboUncertainty | None = None,
    trader_suitability: MarketTraderSuitability | None = None,
    intervention_attribution: TraderDevelopmentAttribution | None = None,
    reasoning_transition: ReasoningTransition | None = None,
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
        reasoning_transition=reasoning_transition,
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

    def test_world_snapshot_preserved(self) -> None:
        snapshot = _world_snapshot()
        episode = _episode(world_snapshot=snapshot)
        assert episode.world_snapshot is snapshot

    def test_non_snapshot_world_snapshot_rejected(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            _episode(world_snapshot=cast(WorldModelSnapshot, "not-a-snapshot"))

    def test_replay_requires_matching_integration_id(self) -> None:
        foreign = build_replay_episode(
            episode_id=_OTHER,
            recorded_at=_AWARE,
            world_snapshot_id=_WORLD,
            goal_plan_state="planning",
            evidence_refs=("evidence:demo",),
        )
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="replay"):
            _episode(replay=foreign)

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
        world = _world_snapshot()
        synthesis = _synthesis()
        replay = _replay()
        evaluation = _evaluation()
        plan_ref = _plan()
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
                synthesis=_synthesis(),
            )

    def test_synthesis_requires_decision_outcome(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="decision"):
            _episode(synthesis=_synthesis())

    def test_decision_outcome_with_synthesis_is_preserved(self) -> None:
        binding = _synthesis()
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
        assert episode.logical_values()[15] == episode.uncertainty.logical_values()

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
        first = _world_snapshot()
        second_reference = WorldModelReference(
            domain=WorldModelDomain.MARKET,
            source_id=WorldModelSourceId("source-a"),
            source_version=WorldModelSourceVersion("2"),
            as_of=_AWARE,
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=fingerprint_material("source-a:2"),
            evidence_label="provider-neutral market evidence v2",
        )
        second = build_world_model_snapshot(
            snapshot_id=_WORLD, as_of=_AWARE, references=[second_reference]
        )
        a = _episode(world_snapshot=first)
        b = _episode(world_snapshot=second)
        assert a.fingerprint != b.fingerprint


class TestAuthorityFreeFirewall:
    def test_integrated_episode_is_authority_free(self) -> None:
        _assert_no_authority_fields(_episode())

    def test_content_binding_is_authority_free(self) -> None:
        _assert_no_authority_fields(
            CiboIntegratedContentBinding(id=_WORLD, fingerprint=_fp("content"))
        )

    def test_no_authority_bearing_output_created_by_integrated_cognition(self) -> None:
        episode = _episode(
            deliberation_outcome=CiboCouncilOutcome.DECISION,
            synthesis=_synthesis(),
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
    def test_suitability_binding_rejects_non_suitability_source(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_suitability_reference(cast(MarketTraderSuitability, _world_snapshot()))

    def test_attribution_binding_rejects_non_attribution_source(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_attribution_reference(cast(TraderDevelopmentAttribution, _evaluation()))

    def test_suitability_binding_derives_from_source_content(self) -> None:
        suitability = _suitability()
        binding = bind_suitability_reference(suitability)
        assert binding.id == suitability.suitability_id
        assert binding.fingerprint == suitability.fingerprint

    def test_attribution_binding_derives_from_source_content(self) -> None:
        attribution = _attribution()
        binding = bind_attribution_reference(attribution)
        assert binding.id == attribution.attribution_id
        assert binding.fingerprint == attribution.fingerprint

    def test_episode_with_source_objects_builds_and_replays(self) -> None:
        episode = build_integrated_episode(
            integration_id=_ID,
            reasoning_mode=CiboReasoningMode.HIGH,
            evidence_bindings=(_binding("a"),),
            recorded_at=_AWARE,
            trader_suitability=_suitability(),
            intervention_attribution=_attribution(),
        )
        replay = replay_integrated_episode(episode)
        assert replay.fingerprint == episode.fingerprint
        assert replay.view == episode.logical_values()

    def test_source_bindings_are_authority_free(self) -> None:
        suitability = bind_suitability_reference(_suitability())
        attribution = bind_attribution_reference(_attribution())
        for binding in (suitability, attribution):
            assert isinstance(binding, CiboIntegratedContentBinding)
            assert not any(hasattr(binding, name) for name in _AUTHORITY_FIELDS)

    def test_callerminted_content_binding_not_admittable_as_source(self) -> None:
        fabricated = CiboIntegratedContentBinding(id=_WORLD, fingerprint=_fp("unverified"))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            _episode(
                trader_suitability=cast(MarketTraderSuitability, fabricated),
            )

    def test_swapped_suitability_fingerprint_fails_closed(self) -> None:
        suitability = _suitability()
        object.__setattr__(suitability, "fingerprint", _fp("forged"))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_suitability_reference(suitability)

    def test_swapped_attribution_fingerprint_fails_closed(self) -> None:
        attribution = _attribution()
        object.__setattr__(attribution, "fingerprint", _fp("forged"))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_attribution_reference(attribution)


class TestProofRootClosure:
    """I-1b: trusted admission re-derives ``(id, fingerprint)`` from source content.

    No caller-supplied binding object may self-assert trusted status through direct
    construction, helper call, reflective mutation, subclassing, copy/replace/
    pickle-style reconstruction, swapped id/fingerprint, stale/wrong content, or
    replayed fabrication.
    """

    def test_w1_direct_arbitrary_binding_is_not_admittable(self) -> None:
        fabricated = CiboIntegratedContentBinding(id=_WORLD, fingerprint=_fp("unverified"))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            _episode(world_snapshot=cast(WorldModelSnapshot, fabricated))

    def test_w2_no_proven_marker_exists_to_set(self) -> None:
        binding = bind_synthesis_reference(_synthesis())
        assert not hasattr(binding, "_proven")
        with pytest.raises(AttributeError):
            object.__setattr__(binding, "_proven", True)

    def test_w3_proven_helper_is_removed(self) -> None:
        import qore.infrastructure.cibo_cognitive_integration as integration

        assert not hasattr(integration, "_proven_content_binding")
        assert not hasattr(integration, "require_proven")

    def test_w4_swapped_id_cannot_keep_original_fingerprint(self) -> None:
        snapshot = _world_snapshot()
        object.__setattr__(snapshot, "snapshot_id", _OTHER)
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            _episode(world_snapshot=snapshot)

    def test_w5_fabricated_fingerprints_rejected(self) -> None:
        for hex_value in ("0" * 64, "f" * 64):
            snapshot = _world_snapshot()
            object.__setattr__(snapshot, "fingerprint", CiboCognitiveFingerprint(hex_value))
            with pytest.raises(CiboCognitiveIntegrationValidationError):
                _episode(world_snapshot=snapshot)

    def test_w6_stale_swapped_content_rejected_at_admission(self) -> None:
        snapshot = _world_snapshot()
        swapped = WorldModelReference(
            domain=WorldModelDomain.MARKET,
            source_id=WorldModelSourceId("source-b"),
            source_version=WorldModelSourceVersion("2"),
            as_of=_AWARE,
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=fingerprint_material("source-b:2"),
            evidence_label="swapped",
        )
        object.__setattr__(snapshot, "references", (swapped,))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            _episode(world_snapshot=snapshot)

    def test_w7_exact_runtime_type_subclass_rejected(self) -> None:
        class EvilSnapshot(WorldModelSnapshot):
            pass

        good = _world_snapshot()
        evil = EvilSnapshot(
            snapshot_id=good.snapshot_id,
            as_of=good.as_of,
            staleness_threshold=good.staleness_threshold,
            references=good.references,
            contradictions=good.contradictions,
            fingerprint=good.fingerprint,
        )
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            _episode(world_snapshot=evil)

    def test_w8_reflective_corruption_after_valid_bind_rejected(self) -> None:
        episode = _episode(world_snapshot=_world_snapshot())
        swapped = WorldModelReference(
            domain=WorldModelDomain.MARKET,
            source_id=WorldModelSourceId("source-b"),
            source_version=WorldModelSourceVersion("2"),
            as_of=_AWARE,
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=fingerprint_material("source-b:2"),
            evidence_label="swapped",
        )
        object.__setattr__(episode.world_snapshot, "references", (swapped,))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            replay_integrated_episode(episode)

    def test_w9_fabricated_replay_round_trip_rejected(self) -> None:
        fabricated = CiboIntegratedContentBinding(id=_ID, fingerprint=_fp("fabricated"))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            _episode(replay=cast(ReplayEpisode, fabricated))

    def test_w10_valid_source_bindings_remain_deterministic(self) -> None:
        def build() -> CiboIntegratedCognitiveEpisode:
            return _episode(
                world_snapshot=_world_snapshot(),
                deliberation_outcome=CiboCouncilOutcome.DECISION,
                synthesis=_synthesis(),
                replay=_replay(),
                evaluation=_evaluation(),
                plan_reference=_plan(),
            )

        left = build()
        right = build()
        assert left.fingerprint == right.fingerprint
        assert left.logical_values() == right.logical_values()
        replay = replay_integrated_episode(left)
        assert replay.view == left.logical_values()
        assert replay.fingerprint == left.fingerprint

    def test_schema_arity_and_version_pinned(self) -> None:
        values = _episode().logical_values()
        assert len(values) == 22
        assert values[0] == "cibo-integrated-episode:v3"


class TestTimezoneMetamorphism:
    def test_episode_logical_values_identical_across_offsets(self) -> None:
        utc = datetime(2026, 8, 9, 5, 0, tzinfo=UTC)
        est = datetime(2026, 8, 9, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        left = _episode(recorded_at=utc)
        right = _episode(recorded_at=est)
        assert left.logical_values() == right.logical_values()
        assert left.fingerprint == right.fingerprint

    def test_episode_distinct_instants_stay_distinct(self) -> None:
        left = _episode(recorded_at=datetime(2026, 8, 9, 5, 0, tzinfo=UTC))
        right = _episode(recorded_at=datetime(2026, 8, 9, 5, 1, tzinfo=UTC))
        assert left.logical_values() != right.logical_values()
        assert left.fingerprint != right.fingerprint


def test_zero_confidence_band_with_abstention_maps_to_insufficient_evidence() -> None:
    note = CalibrationNote(confidence_band=0, note="none", abstention_required=True)
    assert bind_uncertainty_kind(note) is CiboUncertaintyKind.INSUFFICIENT_EVIDENCE


# --- Strengthened superarchitecture (CA 3.1..3.4) bindings + end-to-end slice ---


def _causal_variable(code: str) -> CausalVariable:
    return CausalVariable(code=code, fingerprint=fingerprint_material((code,)))


def _causal_evidence(ref: str, polarity: CausalEvidencePolarity) -> CausalEvidence:
    return CausalEvidence(
        ref=CiboCognitiveEvidenceRef(ref),
        polarity=polarity,
        observed_at=_AWARE,
        fingerprint=fingerprint_material((ref, polarity.value, _AWARE)),
    )


def _correlation_claim() -> CausalClaim:
    return build_causal_claim(
        claim_id=_CORR,
        kind=CausalClaimKind.CORRELATION,
        cause=_causal_variable("activity"),
        effect=_causal_variable("outcome"),
        strength=CausalClaimStrength.WEAK,
        status=CausalClaimStatus.ACTIVE,
    )


def _causation_claim() -> CausalClaim:
    return build_causal_claim(
        claim_id=_CAUSAL,
        kind=CausalClaimKind.CAUSATION,
        cause=_causal_variable("intervention"),
        effect=_causal_variable("capability"),
        confounders=(_causal_variable("selection-bias"),),
        confounders_addressed=True,
        evidence_for=(_causal_evidence("evidence:causal-for", CausalEvidencePolarity.SUPPORTS),),
        strength=CausalClaimStrength.MODERATE,
        status=CausalClaimStatus.ACTIVE,
    )


def _scenario(sid: UUID, family: ScenarioFamily, version: str, *, abstained: bool) -> Scenario:
    assumptions = (
        ScenarioAssumption(
            code="no-fabricated-probability", fact_kind=ScenarioFactKind.HYPOTHETICAL
        ),
    )
    alternatives: tuple[ScenarioAlternative, ...] = ()
    if not abstained:
        alternatives = (
            ScenarioAlternative(
                alternative_id=_ALT, action_code="research", outcome_code="undetermined"
            ),
        )
    return build_scenario(
        scenario_id=sid,
        family=family,
        version=version,
        assumptions=assumptions,
        alternatives=alternatives,
        abstained=abstained,
        uncertainty=CiboUncertainty(kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE),
        limitations=("no-calibrated-probability",),
    )


def _hyp_evidence(ref: str, polarity: HypothesisEvidencePolarity) -> HypothesisEvidence:
    return HypothesisEvidence(
        ref=CiboCognitiveEvidenceRef(ref),
        polarity=polarity,
        observed_at=_AWARE,
        fingerprint=fingerprint_material((ref, polarity.value, _AWARE)),
    )


def _hypothesis_lineage() -> tuple[Hypothesis, ...]:
    born = build_hypothesis(
        hypothesis_id=_HYP, content_code="h.regime", status=HypothesisStatus.BORN
    )
    active = transition_hypothesis(born, HypothesisStatus.ACTIVE)
    refuted = transition_hypothesis(
        active,
        HypothesisStatus.REFUTED,
        contradictions=(
            _hyp_evidence("evidence:against", HypothesisEvidencePolarity.CONTRADICTION),
        ),
    )
    revised = transition_hypothesis(
        refuted,
        HypothesisStatus.REVISED,
        content_code="h.regime-revised",
        reason_code="new.evidence",
    )
    re_active = transition_hypothesis(revised, HypothesisStatus.ACTIVE)
    competing = build_hypothesis(
        hypothesis_id=_HYP_COMPETING, content_code="h.competing", status=HypothesisStatus.ACTIVE
    )
    return (born, active, refuted, revised, re_active, competing)


def _audit() -> MetacognitiveAudit:
    return build_metacognitive_audit(
        audit_id=_AUDIT_ID,
        reasoning_mode=CiboReasoningMode.HIGH,
        evidence_sufficiency=MetacognitiveFinding.INSUFFICIENT_EVIDENCE,
        reason_codes=("missing-evidence",),
    )


def _transition() -> ReasoningTransition:
    return build_reasoning_transition(
        from_mode=CiboReasoningMode.HIGH,
        to_mode=CiboReasoningMode.MAX,
        reason_code="insufficient-evidence",
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:gap"),),
    )


def _decision_synthesis() -> CiboCouncilSynthesis:
    return CiboCouncilSynthesis(
        synthesis_id=_SYNTH,
        summary="Decision synthesis",
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:synthesis"),),
        uncertainty=CiboUncertainty(
            kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE, confidence=_bounded_confidence()
        ),
        synthesized_at=_AWARE,
    )


def _learning_record() -> CognitiveLearningRecord:
    return CognitiveLearningRecord(
        record_id=_LEARN,
        decision_time=_T_INT,
        expected_result="capability improves",
        actual_result_reference=EvidenceBundle(reference="evidence:realized", observed_at=_T_POST),
        contemporaneous_evidence=(EvidenceBundle(reference="evidence:pre", observed_at=_T_PRE),),
        later_evidence=(EvidenceBundle(reference="evidence:post", observed_at=_T_POST),),
        error_attribution="no-error",
        counterfactuals=("no-intervention",),
        reflection_note="expected result matched realized evidence",
        supersedes=None,
    )


class TestStrengthenedCapabilityBindings:
    def test_metacognitive_reasoning_mode_binds_target_mode(self) -> None:
        assert bind_metacognitive_reasoning_mode(_transition()) is CiboReasoningMode.MAX

    def test_causal_claim_reference_binds_self_fingerprint(self) -> None:
        claim = _causation_claim()
        binding = bind_causal_claim_reference(claim)
        assert binding.id == _CAUSAL
        assert binding.fingerprint == claim.fingerprint

    def test_scenario_reference_binds_self_fingerprint(self) -> None:
        scenario = _scenario(_SCEN_BASE, ScenarioFamily.BASE, "1", abstained=True)
        binding = bind_scenario_reference(scenario)
        assert binding.id == _SCEN_BASE
        assert binding.fingerprint == scenario.fingerprint

    def test_hypothesis_reference_binds_self_fingerprint(self) -> None:
        hypothesis = build_hypothesis(
            hypothesis_id=_HYP, content_code="h.regime", status=HypothesisStatus.ACTIVE
        )
        binding = bind_hypothesis_reference(hypothesis)
        assert binding.id == _HYP
        assert binding.fingerprint == hypothesis.fingerprint

    def test_metacognitive_audit_reference_binds_self_fingerprint(self) -> None:
        audit = _audit()
        binding = bind_metacognitive_audit_reference(audit)
        assert binding.id == _AUDIT_ID
        assert binding.fingerprint == audit.fingerprint

    def test_learning_record_reference_binds_content_fingerprint(self) -> None:
        record = _learning_record()
        binding = bind_learning_record_reference(record)
        assert binding.id == _LEARN

    def test_forged_causal_claim_fingerprint_rejected(self) -> None:
        claim = _causation_claim()
        object.__setattr__(claim, "fingerprint", _fp("forged"))
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            bind_causal_claim_reference(claim)

    def test_episode_requires_reasoning_mode_to_match_transition(self) -> None:
        with pytest.raises(CiboCognitiveIntegrationValidationError, match="metacognition-selected"):
            _episode(reasoning_mode=CiboReasoningMode.FAST, reasoning_transition=_transition())


class TestStrengthenedEndToEndComposition:
    def _build(self) -> CiboIntegratedCognitiveEpisode:
        transition = _transition()
        selected = bind_metacognitive_reasoning_mode(transition)
        assert selected is CiboReasoningMode.MAX
        return build_integrated_episode(
            integration_id=_ID,
            reasoning_mode=selected,
            evidence_bindings=(_binding("world"),),
            recorded_at=_AWARE,
            world_snapshot=_world_snapshot(),
            deliberation_outcome=CiboCouncilOutcome.DECISION,
            synthesis=_decision_synthesis(),
            replay=_replay(),
            evaluation=_evaluation(),
            plan_reference=_plan(),
            uncertainty=CiboUncertainty(
                kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE, confidence=_bounded_confidence()
            ),
            causal_claims=(_correlation_claim(), _causation_claim()),
            scenarios=(
                _scenario(_SCEN_BASE, ScenarioFamily.BASE, "1", abstained=False),
                _scenario(_SCEN_ADVERSE, ScenarioFamily.ADVERSE, "1", abstained=True),
                _scenario(_SCEN_EXTREME, ScenarioFamily.EXTREME, "1", abstained=True),
                _scenario(_SCEN_REGIME, ScenarioFamily.REGIME_CHANGE, "1", abstained=True),
            ),
            metacognitive_audit=_audit(),
            reasoning_transition=transition,
            hypotheses=_hypothesis_lineage(),
            learning_records=(_learning_record(),),
        )

    def test_full_cycle_composes_deterministically(self) -> None:
        left = self._build()
        right = self._build()
        assert left.fingerprint == right.fingerprint
        assert left.logical_values() == right.logical_values()

    def test_replay_reproduces_same_semantic_result(self) -> None:
        episode = self._build()
        replay = replay_integrated_episode(episode)
        assert replay.view == episode.logical_values()
        assert replay.fingerprint == episode.fingerprint

    def test_capabilities_participate_in_replay_view(self) -> None:
        episode = self._build()
        values = episode.logical_values()
        assert len(values) == 22
        assert isinstance(values[16], tuple) and len(values[16]) == 2  # causal claims
        assert isinstance(values[17], tuple) and len(values[17]) == 4  # scenarios
        assert values[18] is not None  # metacognitive audit reference
        assert values[19] is not None  # reasoning transition
        assert isinstance(values[20], tuple) and len(values[20]) == 6  # hypothesis lineage
        assert isinstance(values[21], tuple) and len(values[21]) == 1  # learning records

    def test_composition_is_authority_free(self) -> None:
        _assert_no_authority_fields(self._build())

    def test_reflective_corruption_of_capability_fails_replay(self) -> None:
        episode = self._build()
        # correlation claim at canonical index 1 must never carry strong strength
        object.__setattr__(episode.causal_claims[1], "strength", CausalClaimStrength.STRONG)
        with pytest.raises(CiboCognitiveIntegrationValidationError):
            replay_integrated_episode(episode)
