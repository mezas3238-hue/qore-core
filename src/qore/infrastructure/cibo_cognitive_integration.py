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
from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveFingerprint,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_evaluation import CognitiveEvaluation
from qore.infrastructure.cibo_cognitive_planning import CognitivePlan
from qore.infrastructure.cibo_cognitive_replay import ReplayEpisode, ReplayToolCall
from qore.infrastructure.cibo_cognitive_tools import FacultyId
from qore.infrastructure.cibo_cognitive_world_model import (
    WorldModelSnapshot,
    build_world_model_snapshot,
)
from qore.infrastructure.cibo_executive_deliberation import (
    CiboCouncilOutcome,
    CiboCouncilSynthesis,
)
from qore.kernel.errors import InfrastructureError
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
_EPISODE_SCHEMA_VERSION = "cibo-integrated-episode:v2"


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
    otherwise ``abstention_required`` -> ``ABSTAIN_DEFER``, a zero ``confidence_band``
    -> ``INSUFFICIENT_EVIDENCE`` (zero confidence is never manufactured into positive
    bounded confidence), else ``BOUNDED_CONFIDENCE``. No confidence value is
    fabricated: the bound kind preserves uncertainty without inventing evidence.
    """
    if type(note) is not CalibrationNote:
        raise CiboCognitiveIntegrationValidationError("note must be a CalibrationNote")
    note.revalidate()
    kind = _uncertainty_kind_for_token(note.kind)
    if kind is not None:
        return kind
    if note.abstention_required:
        return CiboUncertaintyKind.ABSTAIN_DEFER
    if note.confidence_band <= 0:
        return CiboUncertaintyKind.INSUFFICIENT_EVIDENCE
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


@dataclass(frozen=True, slots=True)
class CiboIntegratedSuitabilityBinding:
    """An exact (suitability id, fingerprint) reference into the world model.

    The binding references a ``MarketTraderSuitability`` by identity and its
    self-fingerprint only; it never inlines the disposition, trader identity, or
    any market/instrument/regime content, and therefore creates no authority.
    """

    suitability_id: UUID
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.suitability_id) is not UUID:
            raise CiboCognitiveIntegrationValidationError(
                "suitability binding id must be a UUID"
            )
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CiboCognitiveIntegrationValidationError(
                "suitability binding fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()

    def logical_values(self) -> tuple[str, str]:
        return (str(self.suitability_id), self.fingerprint.value)


@dataclass(frozen=True, slots=True)
class CiboIntegratedAttributionBinding:
    """An exact (attribution id, fingerprint) reference into the evaluation layer.

    The binding references a ``TraderDevelopmentAttribution`` by identity and
    self-fingerprint only; it never inlines the intervention, disposition,
    hypothesis, or evidence, and therefore creates no authority.
    """

    attribution_id: UUID
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.attribution_id) is not UUID:
            raise CiboCognitiveIntegrationValidationError(
                "attribution binding id must be a UUID"
            )
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CiboCognitiveIntegrationValidationError(
                "attribution binding fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()

    def logical_values(self) -> tuple[str, str]:
        return (str(self.attribution_id), self.fingerprint.value)


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
    The verified entry points (``bind_*_reference``) revalidate the referenced record
    before constructing the binding, so an unproven fingerprint cannot enter the
    episode fingerprint.
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
    return CiboIntegratedContentBinding(
        id=snapshot.snapshot_id, fingerprint=snapshot.fingerprint
    )


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


@dataclass(frozen=True, slots=True)
class CiboIntegratedCognitiveEpisode:
    """An authority-free, fingerprint-bound composition of both substrates.

    Every cross-substrate link is a UUID/fingerprint reference; no authority,
    content, credential, order, or business semantic is inlined. Disagreement is
    preserved (a disagreement outcome forbids a synthesis reference and bounded
    confidence), uncertainty is preserved and recursively revalidated, and the whole
    episode is deterministically self-fingerprinted.
    """

    integration_id: UUID
    reasoning_mode: CiboReasoningMode
    evidence_bindings: tuple[CiboIntegratedEvidenceBinding, ...]
    recorded_at: datetime
    world_snapshot: CiboIntegratedContentBinding | None = None
    memory_refs: tuple[UUID, ...] = ()
    deliberation_outcome: CiboCouncilOutcome | None = None
    synthesis: CiboIntegratedContentBinding | None = None
    replay: CiboIntegratedContentBinding | None = None
    evaluation: CiboIntegratedContentBinding | None = None
    plan_reference: CiboIntegratedContentBinding | None = None
    tool_calls: tuple[ReplayToolCall, ...] = ()
    uncertainty: CiboUncertainty | None = None
    trader_suitability: CiboIntegratedSuitabilityBinding | None = None
    intervention_attribution: CiboIntegratedAttributionBinding | None = None
    fingerprint: CiboCognitiveFingerprint | None = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
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
        for field_name, value in (
            ("world snapshot", self.world_snapshot),
            ("synthesis", self.synthesis),
            ("replay", self.replay),
            ("evaluation", self.evaluation),
            ("plan reference", self.plan_reference),
        ):
            if value is not None:
                if type(value) is not CiboIntegratedContentBinding:
                    raise CiboCognitiveIntegrationValidationError(
                        f"{field_name} must be a CiboIntegratedContentBinding or None"
                    )
                value.revalidate()
        if self.replay is not None and self.replay.id != self.integration_id:
            raise CiboCognitiveIntegrationValidationError(
                "replay binding id must equal the integrated episode id"
            )
        object.__setattr__(
            self,
            "tool_calls",
            _canonical_tool_calls(self.tool_calls, field_name="integrated tool calls"),
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
        if self.trader_suitability is not None:
            if type(self.trader_suitability) is not CiboIntegratedSuitabilityBinding:
                raise CiboCognitiveIntegrationValidationError(
                    "trader suitability must be a CiboIntegratedSuitabilityBinding or None"
                )
            self.trader_suitability.revalidate()
        if self.intervention_attribution is not None:
            if type(self.intervention_attribution) is not CiboIntegratedAttributionBinding:
                raise CiboCognitiveIntegrationValidationError(
                    "intervention attribution must be a "
                    "CiboIntegratedAttributionBinding or None"
                )
            self.intervention_attribution.revalidate()
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
        expected = fingerprint_material(self.logical_values())
        if self.fingerprint is None:
            object.__setattr__(self, "fingerprint", expected)
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
        self._validate()

    def logical_values(self) -> tuple[object, ...]:
        return (
            _EPISODE_SCHEMA_VERSION,
            str(self.integration_id),
            self.reasoning_mode.value,
            tuple(item.logical_values() for item in self.evidence_bindings),
            self.recorded_at.isoformat(),
            None if self.world_snapshot is None else self.world_snapshot.logical_values(),
            tuple(str(v) for v in self.memory_refs),
            None if self.deliberation_outcome is None else self.deliberation_outcome.value,
            None if self.synthesis is None else self.synthesis.logical_values(),
            None if self.replay is None else self.replay.logical_values(),
            None if self.evaluation is None else self.evaluation.logical_values(),
            None if self.plan_reference is None else self.plan_reference.logical_values(),
            tuple(item.logical_values() for item in self.tool_calls),
            None if self.trader_suitability is None else self.trader_suitability.logical_values(),
            None
            if self.intervention_attribution is None
            else self.intervention_attribution.logical_values(),
            None if self.uncertainty is None else self.uncertainty.logical_values(),
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
    world_snapshot: CiboIntegratedContentBinding | None = None,
    memory_refs: Sequence[UUID] = (),
    deliberation_outcome: CiboCouncilOutcome | None = None,
    synthesis: CiboIntegratedContentBinding | None = None,
    replay: CiboIntegratedContentBinding | None = None,
    evaluation: CiboIntegratedContentBinding | None = None,
    plan_reference: CiboIntegratedContentBinding | None = None,
    tool_calls: Sequence[ReplayToolCall] = (),
    uncertainty: CiboUncertainty | None = None,
    trader_suitability: CiboIntegratedSuitabilityBinding | None = None,
    intervention_attribution: CiboIntegratedAttributionBinding | None = None,
) -> CiboIntegratedCognitiveEpisode:
    """Build a validated, canonically ordered, self-fingerprinted episode.

    Sequence inputs are validated at the factory boundary; the episode is
    constructed exactly once (its ``__post_init__`` canonicalizes and fingerprints
    every field), so no field can be silently dropped between two constructions.
    """
    if type(integration_id) is not UUID:
        raise CiboCognitiveIntegrationValidationError("integration id must be a UUID")
    if not isinstance(evidence_bindings, Sequence):
        raise CiboCognitiveIntegrationValidationError("evidence bindings must be a sequence")
    if not isinstance(memory_refs, Sequence):
        raise CiboCognitiveIntegrationValidationError("memory refs must be a sequence")
    if not isinstance(tool_calls, Sequence):
        raise CiboCognitiveIntegrationValidationError("tool calls must be a sequence")
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
    "CiboIntegratedAttributionBinding",
    "CiboIntegratedCognitiveEpisode",
    "CiboIntegratedContentBinding",
    "CiboIntegratedEvidenceBinding",
    "CiboIntegratedReplay",
    "CiboIntegratedSuitabilityBinding",
    "bind_deliberation_role",
    "bind_evidence_fingerprint",
    "bind_evaluation_reference",
    "bind_plan_reference",
    "bind_reasoning_mode",
    "bind_replay_reference",
    "bind_synthesis_reference",
    "bind_uncertainty_kind",
    "bind_world_snapshot_reference",
    "build_integrated_episode",
    "replay_integrated_episode",
]
