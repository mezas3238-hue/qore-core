"""Provider-neutral CIBO Cognitive Integration Gate.

This module is the single explicit integration seam that reconciles the Batch 006
executive substrate (cognitive contracts, brain, memory, deliberation, journal)
with the Batch 008 complementary cognitive substrate (world model, attention,
planning, tools, replay, evaluation). It composes the two families by
reference/fingerprint/identity only, without importing any Functions/Trader
Manager/Trader Lab implementation:

- reasoning-depth hint -> ``CiboReasoningMode`` (CA-06);
- ``CiboCognitiveFingerprint`` -> ``CiboCognitiveEvidenceRef`` (CA-02);
- faculty identity -> ``CiboDeliberationRole`` (CA-07);
- calibration note -> ``CiboUncertaintyKind`` (CA-09);
- world/synthesis/evaluation/replay/plan references by exact
  ``(id, fingerprint)`` content bindings (CA-04/CA-10/CA-16/CA-17);
- tool orchestration by exact request/input/result fingerprints (CA-12);
- an authority-free integrated episode referencing both substrates
  (CA-14/15/16/17).

The gate is deterministic, immutable, exact-type/version/evidence/fingerprint
bound, and replayable. It creates no business function, no Trader Manager, no
Risk decision, no provider order, no execution authority, no DEMO/Production
eligibility, and no real-capital authority. Disagreement, uncertainty, provenance
and source evidence are preserved; missing or contradictory evidence fails closed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from qore.infrastructure.cibo_cognitive_attention import CalibrationNote, ReasoningDepthHint
from qore.infrastructure.cibo_cognitive_causality import (
    CausalClaim,
    CausalityValidationError,
)
from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveFingerprint,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveValidationError as CiboCommonValidationError,
)
from qore.infrastructure.cibo_cognitive_evaluation import (
    CognitiveEvaluation,
    TraderDevelopmentAttribution,
)
from qore.infrastructure.cibo_cognitive_hypotheses import (
    Hypothesis,
    HypothesisValidationError,
)
from qore.infrastructure.cibo_cognitive_metacognition import (
    MetacognitionValidationError,
    MetacognitiveAudit,
    ReasoningTransition,
)
from qore.infrastructure.cibo_cognitive_planning import (
    CognitiveLearningRecord,
    CognitivePlan,
)
from qore.infrastructure.cibo_cognitive_replay import ReplayEpisode, ReplayToolCall
from qore.infrastructure.cibo_cognitive_scenarios import (
    Scenario,
    ScenarioValidationError,
)
from qore.infrastructure.cibo_cognitive_tools import FacultyId
from qore.infrastructure.cibo_cognitive_world_model import (
    MarketTraderSuitability,
    WorldModelSnapshot,
    build_world_model_snapshot,
)
from qore.infrastructure.cibo_executive_deliberation import (
    CiboCouncilOutcome,
    CiboCouncilSynthesis,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.temporal import canonical_instant
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboCognitiveValidationError,
    CiboDeliberationRole,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)

_FINGERPRINT_REF_PREFIX = "sha256:"

# Fingerprint schema boundary: bump when logical_values() shape changes so an
# old fingerprint can never silently validate against a new shape.
_EPISODE_SCHEMA_VERSION = "cibo-integrated-episode:v3"


def _reasoning_mode_for_hint(value: str) -> CiboReasoningMode:
    """Total reasoning-depth -> reasoning-mode binding (CA-06).

    The hint token uses an underscore ("council_adversarial") while the Batch 006
    enum uses a hyphen ("council-adversarial"), so the binding is an explicit,
    exhaustive ``match`` over the caller-validated hint token — never a blind
    string passthrough and never a mutable module-level registry (hard law 21).
    """
    match value:
        case "fast":
            return CiboReasoningMode.FAST
        case "high":
            return CiboReasoningMode.HIGH
        case "max":
            return CiboReasoningMode.MAX
        case "council_adversarial":
            return CiboReasoningMode.COUNCIL_ADVERSARIAL
        case _:
            raise CiboCognitiveIntegrationValidationError(
                "unsupported reasoning depth hint token"
            )


# Council outcomes that must never collapse into a synthesis (mirrors Batch 006
# council law without re-declaring its ownership).
_DISAGREEMENT_OUTCOMES = frozenset(
    {
        CiboCouncilOutcome.INSUFFICIENT_EVIDENCE,
        CiboCouncilOutcome.DISAGREEMENT,
        CiboCouncilOutcome.NO_DECISION,
        CiboCouncilOutcome.BLOCKED,
    }
)


class CiboCognitiveIntegrationError(InfrastructureError):
    """Base error for the provider-neutral CIBO Cognitive Integration Gate."""

    __slots__ = ()


class CiboCognitiveIntegrationValidationError(CiboCognitiveIntegrationError):
    """An integration binding violates a deterministic, authority-free invariant."""

    __slots__ = ()


def _require_aware_datetime(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must be timezone-aware")


def _uncertainty_kind_for_token(value: str) -> CiboUncertaintyKind | None:
    """Map a substrate-native calibration kind token to a Batch 006 kind."""
    match value:
        case "insufficient_evidence":
            return CiboUncertaintyKind.INSUFFICIENT_EVIDENCE
        case "unresolved_contradiction":
            return CiboUncertaintyKind.UNRESOLVED_CONTRADICTION
        case "competing_hypotheses":
            return CiboUncertaintyKind.COMPETING_HYPOTHESES
        case "more_evidence_requested":
            return CiboUncertaintyKind.MORE_EVIDENCE_REQUESTED
        case "abstain_defer":
            return CiboUncertaintyKind.ABSTAIN_DEFER
        case "bounded_confidence":
            return CiboUncertaintyKind.BOUNDED_CONFIDENCE
        case _:
            return None


def bind_reasoning_mode(depth_hint: ReasoningDepthHint) -> CiboReasoningMode:
    """Deterministically bind a Batch 008 reasoning-depth hint to a Batch 006 mode."""
    if type(depth_hint) is not ReasoningDepthHint:
        raise CiboCognitiveIntegrationValidationError(
            "reasoning depth hint must be a ReasoningDepthHint"
        )
    depth_hint.revalidate()
    return _reasoning_mode_for_hint(depth_hint.value)


def bind_uncertainty_kind(note: CalibrationNote) -> CiboUncertaintyKind:
    """Deterministically bind a Batch 008 calibration note to a Batch 006 kind.

    An explicit substrate-native ``kind`` token is carried verbatim (total map);
    otherwise a zero ``confidence_band`` -> ``INSUFFICIENT_EVIDENCE`` (zero
    confidence is never manufactured into positive bounded confidence, and takes
    precedence over abstention), else ``abstention_required`` -> ``ABSTAIN_DEFER``,
    else ``BOUNDED_CONFIDENCE``. No confidence value is fabricated: the bound kind
    preserves uncertainty without inventing evidence.
    """
    if type(note) is not CalibrationNote:
        raise CiboCognitiveIntegrationValidationError("note must be a CalibrationNote")
    note.revalidate()
    kind = _uncertainty_kind_for_token(note.kind)
    if kind is not None:
        return kind
    if note.confidence_band <= 0:
        return CiboUncertaintyKind.INSUFFICIENT_EVIDENCE
    if note.abstention_required:
        return CiboUncertaintyKind.ABSTAIN_DEFER
    return CiboUncertaintyKind.BOUNDED_CONFIDENCE


@dataclass(frozen=True, slots=True)
class CiboIntegratedEvidenceBinding:
    """An exact fingerprint -> evidence-reference binding.

    The reference value is deterministically derived as ``sha256:<64-hex>`` so the
    fingerprint is preserved verbatim and remains recoverable, while satisfying the
    Cognitive-owned opaque-reference grammar (which requires a leading lowercase
    letter). A mismatched pair fails closed at construction and revalidation.
    """

    fingerprint: CiboCognitiveFingerprint
    evidence_ref: CiboCognitiveEvidenceRef

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CiboCognitiveIntegrationValidationError(
                "evidence binding fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if type(self.evidence_ref) is not CiboCognitiveEvidenceRef:
            raise CiboCognitiveIntegrationValidationError(
                "evidence binding ref must be a CiboCognitiveEvidenceRef"
            )
        self.evidence_ref.revalidate()
        expected = f"{_FINGERPRINT_REF_PREFIX}{self.fingerprint.value}"
        if self.evidence_ref.value != expected:
            raise CiboCognitiveIntegrationValidationError(
                "evidence binding ref does not match its fingerprint"
            )

    def logical_values(self) -> tuple[str, str]:
        return (self.fingerprint.value, self.evidence_ref.value)


def bind_evidence_fingerprint(
    fingerprint: CiboCognitiveFingerprint,
) -> CiboIntegratedEvidenceBinding:
    """Bind an exact sha256 fingerprint to a Cognitive-owned evidence reference."""
    if type(fingerprint) is not CiboCognitiveFingerprint:
        raise CiboCognitiveIntegrationValidationError(
            "evidence fingerprint must be a CiboCognitiveFingerprint"
        )
    fingerprint.revalidate()
    return CiboIntegratedEvidenceBinding(
        fingerprint=fingerprint,
        evidence_ref=CiboCognitiveEvidenceRef(
            f"{_FINGERPRINT_REF_PREFIX}{fingerprint.value}"
        ),
    )


def bind_suitability_reference(
    suitability: MarketTraderSuitability,
) -> CiboIntegratedContentBinding:
    """Bind a suitability assertion by its re-verified self-fingerprint.

    The source object is revalidated (``MarketTraderSuitability.revalidate``
    proves ``fingerprint == canonical content``), so swapped content under a kept
    ``suitability_id`` or a forged fingerprint fails closed. Only the
    ``(id, fingerprint)`` reference is projected: no disposition, trader identity,
    or market/instrument/regime content is inlined, so no authority is created.
    """
    if type(suitability) is not MarketTraderSuitability:
        raise CiboCognitiveIntegrationValidationError(
            "suitability reference requires a MarketTraderSuitability source"
        )
    try:
        suitability.revalidate()
    except CiboCommonValidationError as error:
        raise CiboCognitiveIntegrationValidationError(
            "suitability source failed revalidation"
        ) from error
    return CiboIntegratedContentBinding(
        id=suitability.suitability_id,
        fingerprint=suitability.fingerprint,
    )


def bind_attribution_reference(
    attribution: TraderDevelopmentAttribution,
) -> CiboIntegratedContentBinding:
    """Bind a development attribution by its re-verified self-fingerprint.

    The source object is revalidated (``TraderDevelopmentAttribution.revalidate``
    proves ``fingerprint == canonical content``), so swapped content under a kept
    ``attribution_id`` or a forged fingerprint fails closed. Only the
    ``(id, fingerprint)`` reference is projected: no intervention, disposition,
    hypothesis, or evidence is inlined, so no authority is created.
    """
    if type(attribution) is not TraderDevelopmentAttribution:
        raise CiboCognitiveIntegrationValidationError(
            "attribution reference requires a TraderDevelopmentAttribution source"
        )
    try:
        attribution.revalidate()
    except CiboCommonValidationError as error:
        raise CiboCognitiveIntegrationValidationError(
            "attribution source failed revalidation"
        ) from error
    return CiboIntegratedContentBinding(
        id=attribution.attribution_id,
        fingerprint=attribution.fingerprint,
    )


def bind_deliberation_role(faculty_id: FacultyId) -> CiboDeliberationRole:
    """Bind a Batch 008 faculty identity to a Batch 006 deliberation role.

    The binding is by ``faculty_id`` only and fails closed when the identity is
    not a canonical deliberation-role code; no lowercase coercion is performed.
    """
    if type(faculty_id) is not FacultyId:
        raise CiboCognitiveIntegrationValidationError("faculty id must be a FacultyId")
    faculty_id.revalidate()
    try:
        return CiboDeliberationRole(faculty_id.value)
    except CiboCognitiveValidationError as error:
        raise CiboCognitiveIntegrationValidationError(
            "faculty id is not a canonical deliberation role code"
        ) from error


@dataclass(frozen=True, slots=True)
class CiboIntegratedContentBinding:
    """An exact immutable ``(id, fingerprint)`` reference into another record.

    The fingerprint is the referenced record's own content/version self-fingerprint.
    The reference carries no caller-assertable proof state: it is admissible into an
    integrated episode/replay only when the episode re-derives it from verified
    source content at the admission boundary (``bind_*_reference``), never from a
    directly constructed, mutated, copied, or otherwise caller-supplied binding
    object.
    """

    id: UUID
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.id) is not UUID:
            raise CiboCognitiveIntegrationValidationError("content binding id must be a UUID")
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CiboCognitiveIntegrationValidationError(
                "content binding fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()

    def logical_values(self) -> tuple[str, str]:
        return (str(self.id), self.fingerprint.value)


def bind_world_snapshot_reference(snapshot: WorldModelSnapshot) -> CiboIntegratedContentBinding:
    """Bind a world snapshot by its canonical, re-verified self-fingerprint.

    The snapshot is re-canonicalized and re-fingerprinted from its retained content,
    so swapped content under a kept ``snapshot_id`` fails closed.
    """
    if type(snapshot) is not WorldModelSnapshot:
        raise CiboCognitiveIntegrationValidationError(
            "world snapshot must be a WorldModelSnapshot"
        )
    rebuilt = build_world_model_snapshot(
        snapshot_id=snapshot.snapshot_id,
        as_of=snapshot.as_of,
        references=snapshot.references,
        contradictions=snapshot.contradictions,
        staleness_threshold=snapshot.staleness_threshold,
    )
    if rebuilt.fingerprint != snapshot.fingerprint:
        raise CiboCognitiveIntegrationValidationError(
            "world snapshot fingerprint does not match its canonical content"
        )
    return CiboIntegratedContentBinding(id=snapshot.snapshot_id, fingerprint=snapshot.fingerprint)


def bind_synthesis_reference(synthesis: CiboCouncilSynthesis) -> CiboIntegratedContentBinding:
    """Bind a council synthesis by its content fingerprint."""
    if type(synthesis) is not CiboCouncilSynthesis:
        raise CiboCognitiveIntegrationValidationError(
            "synthesis must be a CiboCouncilSynthesis"
        )
    synthesis.revalidate()
    return CiboIntegratedContentBinding(
        id=synthesis.synthesis_id,
        fingerprint=fingerprint_material(synthesis.logical_values()),
    )


def _evaluation_fingerprint(evaluation: CognitiveEvaluation) -> CiboCognitiveFingerprint:
    return fingerprint_material(
        (
            str(evaluation.evaluation_id),
            evaluation.evaluated_reference,
            tuple(dimension.logical_values() for dimension in evaluation.dimensions),
            evaluation.status.value,
            tuple(sorted(evaluation.evidence_refs)),
            tuple(sorted(evaluation.contradiction_refs)),
        )
    )


def bind_evaluation_reference(evaluation: CognitiveEvaluation) -> CiboIntegratedContentBinding:
    """Bind a cognitive evaluation by its content fingerprint."""
    if type(evaluation) is not CognitiveEvaluation:
        raise CiboCognitiveIntegrationValidationError(
            "evaluation must be a CognitiveEvaluation"
        )
    evaluation.revalidate()
    return CiboIntegratedContentBinding(
        id=evaluation.evaluation_id,
        fingerprint=_evaluation_fingerprint(evaluation),
    )


def _plan_fingerprint(plan: CognitivePlan) -> CiboCognitiveFingerprint:
    goals = tuple(
        goal.logical_values() for goal in sorted(plan.goals, key=lambda g: g.sort_key())
    )
    tasks = tuple(
        task.logical_values() for task in sorted(plan.tasks, key=lambda t: t.sort_key())
    )
    return fingerprint_material(
        (
            str(plan.plan_id),
            goals,
            tasks,
            plan.revision,
            plan.parent_revision,
        )
    )


def bind_plan_reference(plan: CognitivePlan) -> CiboIntegratedContentBinding:
    """Bind a cognitive plan by its canonical content fingerprint (CA-10)."""
    if type(plan) is not CognitivePlan:
        raise CiboCognitiveIntegrationValidationError("plan must be a CognitivePlan")
    plan.revalidate()
    return CiboIntegratedContentBinding(id=plan.plan_id, fingerprint=_plan_fingerprint(plan))


def bind_replay_reference(
    replay: ReplayEpisode, *, integration_id: UUID
) -> CiboIntegratedContentBinding:
    """Bind the integrated episode to its own replay record (CA-16).

    ``replay.fingerprint`` is the replay's self-fingerprint (revalidation already
    proves ``fingerprint == content``); the cross-id invariant
    ``replay.episode_id == integration_id`` prevents a foreign replay reference.
    """
    if type(replay) is not ReplayEpisode:
        raise CiboCognitiveIntegrationValidationError("replay must be a ReplayEpisode")
    if type(integration_id) is not UUID:
        raise CiboCognitiveIntegrationValidationError("integration id must be a UUID")
    replay.revalidate()
    if replay.episode_id != integration_id:
        raise CiboCognitiveIntegrationValidationError(
            "replay episode id does not match the integrated episode id"
        )
    return CiboIntegratedContentBinding(id=replay.episode_id, fingerprint=replay.fingerprint)


def bind_causal_claim_reference(claim: CausalClaim) -> CiboIntegratedContentBinding:
    """Bind a causal claim by its re-verified self-fingerprint (CA strengthening 3.1).

    The source ``CausalClaim`` is revalidated (its own ``revalidate`` proves
    ``fingerprint == canonical content``), so swapped content under a kept
    ``claim_id`` or a forged fingerprint fails closed. Only the ``(id,
    fingerprint)`` reference is projected; no cause/effect/confounder content or
    authority is inlined.
    """
    if type(claim) is not CausalClaim:
        raise CiboCognitiveIntegrationValidationError(
            "causal claim reference requires a CausalClaim source"
        )
    try:
        claim.revalidate()
    except CausalityValidationError as error:
        raise CiboCognitiveIntegrationValidationError(
            "causal claim source failed revalidation"
        ) from error
    return CiboIntegratedContentBinding(id=claim.claim_id, fingerprint=claim.fingerprint)


def bind_scenario_reference(scenario: Scenario) -> CiboIntegratedContentBinding:
    """Bind a scenario by its re-verified self-fingerprint (CA strengthening 3.2).

    The source ``Scenario`` is revalidated, so swapped content under a kept
    ``scenario_id`` or a forged fingerprint fails closed. Only the ``(id,
    fingerprint)`` reference is projected; scenario output is advisory cognition
    only and creates no execution authority.
    """
    if type(scenario) is not Scenario:
        raise CiboCognitiveIntegrationValidationError(
            "scenario reference requires a Scenario source"
        )
    try:
        scenario.revalidate()
    except ScenarioValidationError as error:
        raise CiboCognitiveIntegrationValidationError(
            "scenario source failed revalidation"
        ) from error
    return CiboIntegratedContentBinding(id=scenario.scenario_id, fingerprint=scenario.fingerprint)


def bind_metacognitive_audit_reference(
    audit: MetacognitiveAudit,
) -> CiboIntegratedContentBinding:
    """Bind a metacognitive audit by its re-verified self-fingerprint (CA 3.3).

    The audit is revalidated, so swapped reason codes, suppressed missing
    specialists, or a forged fingerprint fails closed. Only the ``(id,
    fingerprint)`` reference is projected; the audit never self-certifies
    authority.
    """
    if type(audit) is not MetacognitiveAudit:
        raise CiboCognitiveIntegrationValidationError(
            "metacognitive audit reference requires a MetacognitiveAudit source"
        )
    try:
        audit.revalidate()
    except MetacognitionValidationError as error:
        raise CiboCognitiveIntegrationValidationError(
            "metacognitive audit source failed revalidation"
        ) from error
    return CiboIntegratedContentBinding(id=audit.audit_id, fingerprint=audit.fingerprint)


def bind_hypothesis_reference(hypothesis: Hypothesis) -> CiboIntegratedContentBinding:
    """Bind a hypothesis by its re-verified self-fingerprint (CA strengthening 3.4).

    The source ``Hypothesis`` is revalidated, so a forged ``CONFIRMED`` status, a
    swapped ``(id, content)`` pair, or a forged fingerprint fails closed. Only the
    ``(id, fingerprint)`` reference is projected; hypotheses confer no authority.
    """
    if type(hypothesis) is not Hypothesis:
        raise CiboCognitiveIntegrationValidationError(
            "hypothesis reference requires a Hypothesis source"
        )
    try:
        hypothesis.revalidate()
    except HypothesisValidationError as error:
        raise CiboCognitiveIntegrationValidationError(
            "hypothesis source failed revalidation"
        ) from error
    return CiboIntegratedContentBinding(
        id=hypothesis.hypothesis_id, fingerprint=hypothesis.fingerprint
    )


def _learning_record_fingerprint(record: CognitiveLearningRecord) -> CiboCognitiveFingerprint:
    """Derive a deterministic content fingerprint for a learning record.

    ``CognitiveLearningRecord`` retains no self-fingerprint, so the integration
    projects its retained content (decision time, expected result, evidence
    bundles, attribution, counterfactuals, reflection, supersession) to canonical
    material. Evidence bundles are canonically ordered so the fingerprint is stable
    under permutation.
    """
    return fingerprint_material(
        (
            str(record.record_id),
            canonical_instant(record.decision_time),
            record.expected_result,
            None
            if record.actual_result_reference is None
            else record.actual_result_reference.logical_values(),
            tuple(
                bundle.logical_values()
                for bundle in sorted(
                    record.contemporaneous_evidence,
                    key=lambda item: (item.reference, item.observed_at),
                )
            ),
            tuple(
                bundle.logical_values()
                for bundle in sorted(
                    record.later_evidence,
                    key=lambda item: (item.reference, item.observed_at),
                )
            ),
            record.error_attribution,
            record.counterfactuals,
            record.reflection_note,
            None if record.supersedes is None else str(record.supersedes),
        )
    )


def bind_learning_record_reference(
    record: CognitiveLearningRecord,
) -> CiboIntegratedContentBinding:
    """Bind a learning record by its derived content fingerprint (CA 3.4 / step 12).

    The source ``CognitiveLearningRecord`` is revalidated (its own ``revalidate``
    enforces expected-vs-realized evidence ordering and secret hygiene) and its
    content is fingerprinted, so hindsight-corrupted or swapped content fails
    closed. Only the ``(id, fingerprint)`` reference is projected; learning is
    advisory reflection only.
    """
    if type(record) is not CognitiveLearningRecord:
        raise CiboCognitiveIntegrationValidationError(
            "learning record reference requires a CognitiveLearningRecord source"
        )
    record.revalidate()
    return CiboIntegratedContentBinding(
        id=record.record_id, fingerprint=_learning_record_fingerprint(record)
    )


def bind_metacognitive_reasoning_mode(
    transition: ReasoningTransition,
) -> CiboReasoningMode:
    """Return the metacognition-selected reasoning mode (CA strengthening 3.3).

    The ``ReasoningTransition`` is revalidated (evidence-gated escalation, no
    self-loop), and its ``to_mode`` is the bounded reasoning mode the Router must
    adopt. This is advisory cognition only: it selects a reasoning policy and
    creates no order/execution/Risk/Production authority.
    """
    if type(transition) is not ReasoningTransition:
        raise CiboCognitiveIntegrationValidationError(
            "metacognitive reasoning mode requires a ReasoningTransition"
        )
    try:
        transition.revalidate()
    except MetacognitionValidationError as error:
        raise CiboCognitiveIntegrationValidationError(
            "reasoning transition failed revalidation"
        ) from error
    return transition.to_mode


def _canonical_bindings(
    values: tuple[CiboIntegratedEvidenceBinding, ...],
    *,
    field_name: str,
) -> tuple[CiboIntegratedEvidenceBinding, ...]:
    if type(values) is not tuple or any(
        type(item) is not CiboIntegratedEvidenceBinding for item in values
    ):
        raise CiboCognitiveIntegrationValidationError(
            f"{field_name} must be an immutable tuple of CiboIntegratedEvidenceBinding"
        )
    if len(set(values)) != len(values):
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.fingerprint.value))


def _canonical_uuids(values: tuple[UUID, ...], *, field_name: str) -> tuple[UUID, ...]:
    if type(values) is not tuple or any(type(v) is not UUID for v in values):
        raise CiboCognitiveIntegrationValidationError(
            f"{field_name} must be an immutable tuple of UUIDs"
        )
    if len(set(values)) != len(values):
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values))


def _canonical_tool_calls(
    values: tuple[ReplayToolCall, ...],
    *,
    field_name: str,
) -> tuple[ReplayToolCall, ...]:
    if type(values) is not tuple or any(type(item) is not ReplayToolCall for item in values):
        raise CiboCognitiveIntegrationValidationError(
            f"{field_name} must be an immutable tuple of ReplayToolCall"
        )
    if len(set(values)) != len(values):
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.sort_key()))


def _canonical_causal_claims(
    values: tuple[CausalClaim, ...], *, field_name: str
) -> tuple[CausalClaim, ...]:
    if type(values) is not tuple or any(type(item) is not CausalClaim for item in values):
        raise CiboCognitiveIntegrationValidationError(
            f"{field_name} must be an immutable tuple of CausalClaim"
        )
    for claim in values:
        try:
            claim.revalidate()
        except CiboCommonValidationError as error:
            raise CiboCognitiveIntegrationValidationError(
                f"{field_name} contains a causal claim that failed revalidation"
            ) from error
    if len({claim.claim_id for claim in values}) != len(values):
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda claim: str(claim.claim_id)))


def _canonical_scenarios(
    values: tuple[Scenario, ...], *, field_name: str
) -> tuple[Scenario, ...]:
    if type(values) is not tuple or any(type(item) is not Scenario for item in values):
        raise CiboCognitiveIntegrationValidationError(
            f"{field_name} must be an immutable tuple of Scenario"
        )
    for scenario in values:
        try:
            scenario.revalidate()
        except CiboCommonValidationError as error:
            raise CiboCognitiveIntegrationValidationError(
                f"{field_name} contains a scenario that failed revalidation"
            ) from error
    if len({scenario.scenario_id for scenario in values}) != len(values):
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda scenario: str(scenario.scenario_id)))


def _canonical_hypotheses(
    values: tuple[Hypothesis, ...], *, field_name: str
) -> tuple[Hypothesis, ...]:
    if type(values) is not tuple or any(type(item) is not Hypothesis for item in values):
        raise CiboCognitiveIntegrationValidationError(
            f"{field_name} must be an immutable tuple of Hypothesis"
        )
    for hypothesis in values:
        try:
            hypothesis.revalidate()
        except CiboCommonValidationError as error:
            raise CiboCognitiveIntegrationValidationError(
                f"{field_name} contains a hypothesis that failed revalidation"
            ) from error
    keys = {(hypothesis.hypothesis_id, hypothesis.revision) for hypothesis in values}
    if len(keys) != len(values):
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must not contain duplicates")
    return tuple(
        sorted(values, key=lambda hypothesis: (str(hypothesis.hypothesis_id), hypothesis.revision))
    )


def _canonical_learning_records(
    values: tuple[CognitiveLearningRecord, ...], *, field_name: str
) -> tuple[CognitiveLearningRecord, ...]:
    if type(values) is not tuple or any(
        type(item) is not CognitiveLearningRecord for item in values
    ):
        raise CiboCognitiveIntegrationValidationError(
            f"{field_name} must be an immutable tuple of CognitiveLearningRecord"
        )
    for record in values:
        try:
            record.revalidate()
        except CiboCommonValidationError as error:
            raise CiboCognitiveIntegrationValidationError(
                f"{field_name} contains a learning record that failed revalidation"
            ) from error
    if len({record.record_id for record in values}) != len(values):
        raise CiboCognitiveIntegrationValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda record: str(record.record_id)))


@dataclass(frozen=True, slots=True)
class CiboIntegratedCognitiveEpisode:
    """An authority-free, fingerprint-bound composition of both substrates.

    Content fields retain their verified source objects (world snapshot, synthesis,
    replay, evaluation, plan) so trust can be re-derived from source content at the
    admission and replay boundaries; the episode fingerprint and ``logical_values()``
    project those sources down to ``(id, fingerprint)`` references only, so no
    authority, credential, order, or business semantic is inlined. Disagreement is
    preserved (a disagreement outcome forbids a synthesis reference and bounded
    confidence), uncertainty is preserved and recursively revalidated, and the whole
    episode is deterministically self-fingerprinted.
    """

    integration_id: UUID
    reasoning_mode: CiboReasoningMode
    evidence_bindings: tuple[CiboIntegratedEvidenceBinding, ...]
    recorded_at: datetime
    world_snapshot: WorldModelSnapshot | None = None
    memory_refs: tuple[UUID, ...] = ()
    deliberation_outcome: CiboCouncilOutcome | None = None
    synthesis: CiboCouncilSynthesis | None = None
    replay: ReplayEpisode | None = None
    evaluation: CognitiveEvaluation | None = None
    plan_reference: CognitivePlan | None = None
    tool_calls: tuple[ReplayToolCall, ...] = ()
    uncertainty: CiboUncertainty | None = None
    trader_suitability: MarketTraderSuitability | None = None
    intervention_attribution: TraderDevelopmentAttribution | None = None
    causal_claims: tuple[CausalClaim, ...] = ()
    scenarios: tuple[Scenario, ...] = ()
    metacognitive_audit: MetacognitiveAudit | None = None
    reasoning_transition: ReasoningTransition | None = None
    hypotheses: tuple[Hypothesis, ...] = ()
    learning_records: tuple[CognitiveLearningRecord, ...] = ()
    fingerprint: CiboCognitiveFingerprint | None = None

    def __post_init__(self) -> None:
        self._validate(deriving=True)

    def _validate(self, *, deriving: bool) -> None:
        if type(self.integration_id) is not UUID:
            raise CiboCognitiveIntegrationValidationError("integration id must be a UUID")
        if type(self.reasoning_mode) is not CiboReasoningMode:
            raise CiboCognitiveIntegrationValidationError(
                "integrated episode requires CiboReasoningMode"
            )
        bindings = _canonical_bindings(
            self.evidence_bindings, field_name="integrated evidence bindings"
        )
        if not bindings:
            raise CiboCognitiveIntegrationValidationError(
                "integrated episode requires explicit backing evidence"
            )
        for binding in bindings:
            binding.revalidate()
        object.__setattr__(self, "evidence_bindings", bindings)
        _require_aware_datetime(self.recorded_at, field_name="integrated recorded_at")
        object.__setattr__(
            self,
            "memory_refs",
            _canonical_uuids(self.memory_refs, field_name="integrated memory refs"),
        )
        if self.deliberation_outcome is not None and type(
            self.deliberation_outcome
        ) is not CiboCouncilOutcome:
            raise CiboCognitiveIntegrationValidationError(
                "deliberation outcome must be a CiboCouncilOutcome or None"
            )
        (
            world_ref,
            synthesis_ref,
            replay_ref,
            evaluation_ref,
            plan_ref,
            suitability_ref,
            attribution_ref,
        ) = self._content_references()
        object.__setattr__(
            self,
            "tool_calls",
            _canonical_tool_calls(self.tool_calls, field_name="integrated tool calls"),
        )
        object.__setattr__(
            self,
            "causal_claims",
            _canonical_causal_claims(self.causal_claims, field_name="integrated causal claims"),
        )
        object.__setattr__(
            self,
            "scenarios",
            _canonical_scenarios(self.scenarios, field_name="integrated scenarios"),
        )
        object.__setattr__(
            self,
            "hypotheses",
            _canonical_hypotheses(self.hypotheses, field_name="integrated hypotheses"),
        )
        object.__setattr__(
            self,
            "learning_records",
            _canonical_learning_records(
                self.learning_records, field_name="integrated learning records"
            ),
        )
        if self.metacognitive_audit is not None:
            if type(self.metacognitive_audit) is not MetacognitiveAudit:
                raise CiboCognitiveIntegrationValidationError(
                    "metacognitive audit must be a MetacognitiveAudit or None"
                )
            try:
                self.metacognitive_audit.revalidate()
            except MetacognitionValidationError as error:
                raise CiboCognitiveIntegrationValidationError(
                    "metacognitive audit failed revalidation"
                ) from error
        if self.reasoning_transition is not None:
            if type(self.reasoning_transition) is not ReasoningTransition:
                raise CiboCognitiveIntegrationValidationError(
                    "reasoning transition must be a ReasoningTransition or None"
                )
            try:
                self.reasoning_transition.revalidate()
            except MetacognitionValidationError as error:
                raise CiboCognitiveIntegrationValidationError(
                    "reasoning transition failed revalidation"
                ) from error
            if self.reasoning_transition.to_mode is not self.reasoning_mode:
                raise CiboCognitiveIntegrationValidationError(
                    "episode reasoning mode must equal the metacognition-selected mode"
                )
        if self.uncertainty is not None:
            if type(self.uncertainty) is not CiboUncertainty:
                raise CiboCognitiveIntegrationValidationError(
                    "uncertainty must be a CiboUncertainty or None"
                )
            try:
                self.uncertainty.revalidate()
            except CiboCognitiveValidationError as error:
                raise CiboCognitiveIntegrationValidationError(
                    "uncertainty failed nested revalidation"
                ) from error
        # trader_suitability and intervention_attribution are source objects; they
        # are re-derived to (id, fingerprint) references inside _content_references.
        if self.deliberation_outcome in _DISAGREEMENT_OUTCOMES:
            if self.synthesis is not None:
                raise CiboCognitiveIntegrationValidationError(
                    "a disagreement outcome must not carry a synthesis reference"
                )
            if (
                self.uncertainty is not None
                and self.uncertainty.kind is CiboUncertaintyKind.BOUNDED_CONFIDENCE
            ):
                raise CiboCognitiveIntegrationValidationError(
                    "a disagreement outcome must not carry bounded confidence uncertainty"
                )
        if self.synthesis is not None:
            if self.deliberation_outcome is not CiboCouncilOutcome.DECISION:
                raise CiboCognitiveIntegrationValidationError(
                    "a synthesis reference requires a decision outcome"
                )
        expected = fingerprint_material(
            self._logical_values(
                world_ref,
                synthesis_ref,
                replay_ref,
                evaluation_ref,
                plan_ref,
                suitability_ref,
                attribution_ref,
            )
        )
        if self.fingerprint is None:
            if deriving:
                # Construction derives the immutable self-fingerprint exactly once.
                object.__setattr__(self, "fingerprint", expected)
            else:
                raise CiboCognitiveIntegrationValidationError(
                    "integrated fingerprint is missing; revalidation must not re-certify "
                    "a frozen episode"
                )
        else:
            if type(self.fingerprint) is not CiboCognitiveFingerprint:
                raise CiboCognitiveIntegrationValidationError(
                    "integrated fingerprint must be a CiboCognitiveFingerprint"
                )
            if self.fingerprint != expected:
                raise CiboCognitiveIntegrationValidationError(
                    "integrated fingerprint does not match its bound content"
                )

    def revalidate(self) -> None:
        self._validate(deriving=False)

    def _content_references(
        self,
    ) -> tuple[
        CiboIntegratedContentBinding | None,
        CiboIntegratedContentBinding | None,
        CiboIntegratedContentBinding | None,
        CiboIntegratedContentBinding | None,
        CiboIntegratedContentBinding | None,
        CiboIntegratedContentBinding | None,
        CiboIntegratedContentBinding | None,
    ]:
        """Re-derive trusted ``(id, fingerprint)`` references from source content.

        Each ``bind_*_reference`` revalidates its source and re-derives the
        fingerprint from that source's content, so forged, swapped, stale, or
        reflectively corrupted source fails closed here. No caller-supplied binding
        object is ever trusted.
        """
        return (
            None
            if self.world_snapshot is None
            else bind_world_snapshot_reference(self.world_snapshot),
            None if self.synthesis is None else bind_synthesis_reference(self.synthesis),
            None
            if self.replay is None
            else bind_replay_reference(self.replay, integration_id=self.integration_id),
            None if self.evaluation is None else bind_evaluation_reference(self.evaluation),
            None if self.plan_reference is None else bind_plan_reference(self.plan_reference),
            None
            if self.trader_suitability is None
            else bind_suitability_reference(self.trader_suitability),
            None
            if self.intervention_attribution is None
            else bind_attribution_reference(self.intervention_attribution),
        )

    def _capability_references(
        self,
    ) -> tuple[
        tuple[CiboIntegratedContentBinding, ...],
        tuple[CiboIntegratedContentBinding, ...],
        CiboIntegratedContentBinding | None,
        tuple[CiboIntegratedContentBinding, ...],
        tuple[CiboIntegratedContentBinding, ...],
    ]:
        """Re-derive trusted references for the four strengthened capabilities.

        Causal claims, scenarios, hypotheses and learning records are retained as
        source objects; each is revalidated and re-derived to an ``(id,
        fingerprint)`` reference so forged, swapped, stale or reflectively
        corrupted source fails closed at the replay boundary. The metacognitive
        audit is re-derived the same way. No caller-supplied binding object is
        trusted.
        """
        return (
            tuple(bind_causal_claim_reference(claim) for claim in self.causal_claims),
            tuple(bind_scenario_reference(scenario) for scenario in self.scenarios),
            None
            if self.metacognitive_audit is None
            else bind_metacognitive_audit_reference(self.metacognitive_audit),
            tuple(bind_hypothesis_reference(hypothesis) for hypothesis in self.hypotheses),
            tuple(bind_learning_record_reference(record) for record in self.learning_records),
        )

    def logical_values(self) -> tuple[object, ...]:
        """Project the episode to reference-only logical material.

        Content fields are reduced to their ``(id, fingerprint)`` references by
        re-deriving from retained source content, so the fingerprint never inlines
        source content and any forged content fails closed.
        """
        return self._logical_values(*self._content_references())

    def _logical_values(
        self,
        world_ref: CiboIntegratedContentBinding | None,
        synthesis_ref: CiboIntegratedContentBinding | None,
        replay_ref: CiboIntegratedContentBinding | None,
        evaluation_ref: CiboIntegratedContentBinding | None,
        plan_ref: CiboIntegratedContentBinding | None,
        suitability_ref: CiboIntegratedContentBinding | None,
        attribution_ref: CiboIntegratedContentBinding | None,
    ) -> tuple[object, ...]:
        (
            causal_refs,
            scenario_refs,
            metacog_ref,
            hypothesis_refs,
            learning_refs,
        ) = self._capability_references()
        return (
            _EPISODE_SCHEMA_VERSION,
            str(self.integration_id),
            self.reasoning_mode.value,
            tuple(item.logical_values() for item in self.evidence_bindings),
            canonical_instant(self.recorded_at),
            None if world_ref is None else world_ref.logical_values(),
            tuple(str(v) for v in self.memory_refs),
            None if self.deliberation_outcome is None else self.deliberation_outcome.value,
            None if synthesis_ref is None else synthesis_ref.logical_values(),
            None if replay_ref is None else replay_ref.logical_values(),
            None if evaluation_ref is None else evaluation_ref.logical_values(),
            None if plan_ref is None else plan_ref.logical_values(),
            tuple(item.logical_values() for item in self.tool_calls),
            None if suitability_ref is None else suitability_ref.logical_values(),
            None if attribution_ref is None else attribution_ref.logical_values(),
            None if self.uncertainty is None else self.uncertainty.logical_values(),
            tuple(item.logical_values() for item in causal_refs),
            tuple(item.logical_values() for item in scenario_refs),
            None if metacog_ref is None else metacog_ref.logical_values(),
            None
            if self.reasoning_transition is None
            else self.reasoning_transition.logical_values(),
            tuple(item.logical_values() for item in hypothesis_refs),
            tuple(item.logical_values() for item in learning_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboIntegratedReplay:
    """Deterministic reconstruction of an integrated episode."""

    integration_id: UUID
    recorded_at: datetime
    view: tuple[object, ...]
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        if type(self.integration_id) is not UUID:
            raise CiboCognitiveIntegrationValidationError("replay integration id must be a UUID")
        _require_aware_datetime(self.recorded_at, field_name="replay recorded_at")
        if type(self.view) is not tuple:
            raise CiboCognitiveIntegrationValidationError("replay view must be a tuple")
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CiboCognitiveIntegrationValidationError(
                "replay fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if self.fingerprint != fingerprint_material(self.view):
            raise CiboCognitiveIntegrationValidationError(
                "replay fingerprint does not match its view"
            )


def build_integrated_episode(
    *,
    integration_id: UUID,
    reasoning_mode: CiboReasoningMode,
    evidence_bindings: Sequence[CiboIntegratedEvidenceBinding],
    recorded_at: datetime,
    world_snapshot: WorldModelSnapshot | None = None,
    memory_refs: Sequence[UUID] = (),
    deliberation_outcome: CiboCouncilOutcome | None = None,
    synthesis: CiboCouncilSynthesis | None = None,
    replay: ReplayEpisode | None = None,
    evaluation: CognitiveEvaluation | None = None,
    plan_reference: CognitivePlan | None = None,
    tool_calls: Sequence[ReplayToolCall] = (),
    uncertainty: CiboUncertainty | None = None,
    trader_suitability: MarketTraderSuitability | None = None,
    intervention_attribution: TraderDevelopmentAttribution | None = None,
    causal_claims: Sequence[CausalClaim] = (),
    scenarios: Sequence[Scenario] = (),
    metacognitive_audit: MetacognitiveAudit | None = None,
    reasoning_transition: ReasoningTransition | None = None,
    hypotheses: Sequence[Hypothesis] = (),
    learning_records: Sequence[CognitiveLearningRecord] = (),
) -> CiboIntegratedCognitiveEpisode:
    """Build a validated, canonically ordered, self-fingerprinted episode.

    Sequence inputs are validated at the factory boundary, and content references
    are supplied as their verified source objects (world snapshot, synthesis,
    replay, evaluation, plan, causal claims, scenarios, metacognitive audit,
    hypotheses, learning records); the episode re-derives each ``(id,
    fingerprint)`` binding from that source content at the admission boundary, so
    no caller supplied binding object can self-assert trusted status. The episode
    is constructed exactly once (its ``__post_init__`` canonicalizes and
    fingerprints every field), so no field can be silently dropped between two
    constructions.
    """
    if type(integration_id) is not UUID:
        raise CiboCognitiveIntegrationValidationError("integration id must be a UUID")
    if not isinstance(evidence_bindings, Sequence):
        raise CiboCognitiveIntegrationValidationError("evidence bindings must be a sequence")
    if not isinstance(memory_refs, Sequence):
        raise CiboCognitiveIntegrationValidationError("memory refs must be a sequence")
    if not isinstance(tool_calls, Sequence):
        raise CiboCognitiveIntegrationValidationError("tool calls must be a sequence")
    if not isinstance(causal_claims, Sequence):
        raise CiboCognitiveIntegrationValidationError("causal claims must be a sequence")
    if not isinstance(scenarios, Sequence):
        raise CiboCognitiveIntegrationValidationError("scenarios must be a sequence")
    if not isinstance(hypotheses, Sequence):
        raise CiboCognitiveIntegrationValidationError("hypotheses must be a sequence")
    if not isinstance(learning_records, Sequence):
        raise CiboCognitiveIntegrationValidationError("learning records must be a sequence")
    bindings = tuple(evidence_bindings)
    for binding in bindings:
        if type(binding) is not CiboIntegratedEvidenceBinding:
            raise CiboCognitiveIntegrationValidationError(
                "evidence bindings must contain only CiboIntegratedEvidenceBinding values"
            )
        binding.revalidate()
    calls = tuple(tool_calls)
    for call in calls:
        if type(call) is not ReplayToolCall:
            raise CiboCognitiveIntegrationValidationError(
                "tool calls must contain only ReplayToolCall values"
            )
        call.revalidate()
    return CiboIntegratedCognitiveEpisode(
        integration_id=integration_id,
        reasoning_mode=reasoning_mode,
        evidence_bindings=bindings,
        recorded_at=recorded_at,
        world_snapshot=world_snapshot,
        memory_refs=tuple(memory_refs),
        deliberation_outcome=deliberation_outcome,
        synthesis=synthesis,
        replay=replay,
        evaluation=evaluation,
        plan_reference=plan_reference,
        tool_calls=calls,
        uncertainty=uncertainty,
        trader_suitability=trader_suitability,
        intervention_attribution=intervention_attribution,
        causal_claims=tuple(causal_claims),
        scenarios=tuple(scenarios),
        metacognitive_audit=metacognitive_audit,
        reasoning_transition=reasoning_transition,
        hypotheses=tuple(hypotheses),
        learning_records=tuple(learning_records),
    )


def replay_integrated_episode(episode: CiboIntegratedCognitiveEpisode) -> CiboIntegratedReplay:
    """Deterministically replay an integrated episode without reading clock/network."""
    if type(episode) is not CiboIntegratedCognitiveEpisode:
        raise CiboCognitiveIntegrationValidationError(
            "episode must be a CiboIntegratedCognitiveEpisode"
        )
    episode.revalidate()
    if episode.fingerprint is None:
        raise CiboCognitiveIntegrationValidationError(
            "integrated episode has no fingerprint to replay"
        )
    return CiboIntegratedReplay(
        integration_id=episode.integration_id,
        recorded_at=episode.recorded_at,
        view=episode.logical_values(),
        fingerprint=episode.fingerprint,
    )


__all__ = [
    "CiboCognitiveIntegrationError",
    "CiboCognitiveIntegrationValidationError",
    "CiboIntegratedCognitiveEpisode",
    "CiboIntegratedContentBinding",
    "CiboIntegratedEvidenceBinding",
    "CiboIntegratedReplay",
    "bind_attribution_reference",
    "bind_causal_claim_reference",
    "bind_deliberation_role",
    "bind_evaluation_reference",
    "bind_evidence_fingerprint",
    "bind_hypothesis_reference",
    "bind_learning_record_reference",
    "bind_metacognitive_audit_reference",
    "bind_metacognitive_reasoning_mode",
    "bind_plan_reference",
    "bind_reasoning_mode",
    "bind_replay_reference",
    "bind_scenario_reference",
    "bind_suitability_reference",
    "bind_synthesis_reference",
    "bind_uncertainty_kind",
    "bind_world_snapshot_reference",
    "build_integrated_episode",
    "replay_integrated_episode",
]
