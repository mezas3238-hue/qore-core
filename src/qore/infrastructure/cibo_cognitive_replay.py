"""CIBO Cognitive Replay / Audit and authority-free handoff seam (CA-16/14/15).

Cognitive observability/replay/audit semantics sufficient to reconstruct, from
exact recorded inputs, the evidence available at episode time, the world-model
snapshot identity, selected attention reasons, goal/plan state, tool requests
and results, alternatives/counterfactuals, uncertainty/contradictions, and a
recommendation/handoff reference plus what changed afterward.

Replay is deterministic over exact recorded inputs and never reads the current
clock or the network: ``recorded_at`` and every fingerprint are caller-supplied.

A typed, authority-free handoff envelope represents
``COGNITIVE OUTPUT -> FORMAL REQUEST/RECOMMENDATION FOR EXTERNAL POLICY/RISK
PIPELINE`` by reference. It contains no execution credential/order/account/
promotion/Risk-decision authority and cannot itself authorize action.

Architecture laws honoured: replay never reads current time/network (14),
deterministic fingerprints (19), secret-bearing strings fail closed (20),
authority never emerges from cognitive output (3, 4, 13), and the
dialogue/opinion seam never becomes a formal signal implicitly (5, 6).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    contains_secret_material,
    fingerprint_material,
    require_aware_datetime,
    require_exact_str,
)
from qore.kernel.temporal import canonical_instant


class ReplayError(CiboCognitiveError):
    """Base error for the CIBO cognitive replay/audit substrate."""

    __slots__ = ()


class ReplayValidationError(ReplayError, CiboCognitiveValidationError):
    """Violation of a cognitive replay or handoff invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ReplayToolCall:
    """A tool request/result pair referenced by its exact fingerprints."""

    request_id: UUID
    input_fingerprint: CiboCognitiveFingerprint
    result_fingerprint: CiboCognitiveFingerprint | None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.request_id) is not UUID:
            raise ReplayValidationError("replay tool call request id must be a UUID")
        if type(self.input_fingerprint) is not CiboCognitiveFingerprint:
            raise ReplayValidationError(
                "replay tool call input fingerprint must be a CiboCognitiveFingerprint"
            )
        self.input_fingerprint.revalidate()
        if self.result_fingerprint is not None:
            if type(self.result_fingerprint) is not CiboCognitiveFingerprint:
                raise ReplayValidationError(
                    "replay tool call result fingerprint must be a CiboCognitiveFingerprint"
                )
            self.result_fingerprint.revalidate()

    def logical_values(self) -> tuple[str, str, str | None]:
        return (
            str(self.request_id),
            self.input_fingerprint.value,
            self.result_fingerprint.value if self.result_fingerprint is not None else None,
        )

    def sort_key(self) -> tuple[str, str, str]:
        return (
            str(self.request_id),
            self.input_fingerprint.value,
            self.result_fingerprint.value if self.result_fingerprint is not None else "",
        )


def _require_text(value: object, *, field: str) -> str:
    text = require_exact_str(value, field=field)
    if not text.strip():
        raise ReplayValidationError(f"{field} must not be blank")
    if contains_secret_material(text):
        raise ReplayValidationError(f"{field} must not carry secret-bearing material")
    return text


def _require_texts(value: object, *, field: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ReplayValidationError(f"{field} must be a tuple")
    return tuple(_require_text(item, field=f"{field} item") for item in value)


def _sort_tool_calls(calls: tuple[ReplayToolCall, ...]) -> tuple[ReplayToolCall, ...]:
    return tuple(sorted(calls, key=lambda call: call.sort_key()))


def _episode_material(
    episode_id: UUID,
    recorded_at: datetime,
    world_snapshot_id: UUID,
    attention_reasons: tuple[str, ...],
    goal_plan_state: str,
    tool_calls: tuple[ReplayToolCall, ...],
    counterfactuals: tuple[str, ...],
    uncertainties: tuple[str, ...],
    contradictions: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    changes_after: tuple[str, ...],
    handoff_reference: str | None,
) -> tuple[object, ...]:
    return (
        str(episode_id),
        canonical_instant(recorded_at),
        str(world_snapshot_id),
        attention_reasons,
        goal_plan_state,
        tuple(call.logical_values() for call in tool_calls),
        counterfactuals,
        uncertainties,
        contradictions,
        evidence_refs,
        changes_after,
        handoff_reference,
    )


@dataclass(frozen=True, slots=True)
class ReplayEpisode:
    """Immutable record of the exact inputs for one cognitive episode."""

    episode_id: UUID
    recorded_at: datetime
    world_snapshot_id: UUID
    attention_reasons: tuple[str, ...]
    goal_plan_state: str
    tool_calls: tuple[ReplayToolCall, ...]
    counterfactuals: tuple[str, ...]
    uncertainties: tuple[str, ...]
    contradictions: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    changes_after: tuple[str, ...]
    handoff_reference: str | None
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.episode_id) is not UUID:
            raise ReplayValidationError("replay episode id must be a UUID")
        require_aware_datetime(self.recorded_at, field="replay recorded_at")
        if type(self.world_snapshot_id) is not UUID:
            raise ReplayValidationError("replay world snapshot id must be a UUID")
        _require_texts(self.attention_reasons, field="replay attention reasons")
        _require_text(self.goal_plan_state, field="replay goal plan state")
        if type(self.tool_calls) is not tuple:
            raise ReplayValidationError("replay tool calls must be a tuple")
        for call in self.tool_calls:
            if type(call) is not ReplayToolCall:
                raise ReplayValidationError(
                    "replay tool calls must contain only ReplayToolCall values"
                )
            call.revalidate()
        if _sort_tool_calls(self.tool_calls) != self.tool_calls:
            raise ReplayValidationError("replay tool calls must be canonically ordered")
        _require_texts(self.counterfactuals, field="replay counterfactuals")
        _require_texts(self.uncertainties, field="replay uncertainties")
        _require_texts(self.contradictions, field="replay contradictions")
        evidence_refs = _require_texts(self.evidence_refs, field="replay evidence refs")
        if not evidence_refs:
            raise ReplayValidationError(
                "replay episode must cite source evidence for material cognition"
            )
        _require_texts(self.changes_after, field="replay changes after")
        if self.handoff_reference is not None:
            _require_text(self.handoff_reference, field="replay handoff reference")
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise ReplayValidationError("replay fingerprint must be a CiboCognitiveFingerprint")
        self.fingerprint.revalidate()
        expected = fingerprint_material(self.logical_values())
        if self.fingerprint != expected:
            raise ReplayValidationError(
                "replay fingerprint does not match its recorded inputs"
            )

    def logical_values(self) -> tuple[object, ...]:
        return _episode_material(
            self.episode_id,
            self.recorded_at,
            self.world_snapshot_id,
            self.attention_reasons,
            self.goal_plan_state,
            self.tool_calls,
            self.counterfactuals,
            self.uncertainties,
            self.contradictions,
            self.evidence_refs,
            self.changes_after,
            self.handoff_reference,
        )


@dataclass(frozen=True, slots=True)
class ReplayReconstruction:
    """Deterministic reconstruction of an episode from exact recorded inputs."""

    episode_id: UUID
    recorded_at: datetime
    view: tuple[object, ...]
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        if type(self.episode_id) is not UUID:
            raise ReplayValidationError("reconstruction episode id must be a UUID")
        require_aware_datetime(self.recorded_at, field="reconstruction recorded_at")
        if type(self.view) is not tuple:
            raise ReplayValidationError("reconstruction view must be a tuple")
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise ReplayValidationError(
                "reconstruction fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if self.fingerprint != fingerprint_material(self.view):
            raise ReplayValidationError(
                "reconstruction fingerprint does not match its view"
            )


def build_replay_episode(
    *,
    episode_id: UUID,
    recorded_at: datetime,
    world_snapshot_id: UUID,
    attention_reasons: Sequence[str] = (),
    goal_plan_state: str = "",
    tool_calls: Sequence[ReplayToolCall] = (),
    counterfactuals: Sequence[str] = (),
    uncertainties: Sequence[str] = (),
    contradictions: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    changes_after: Sequence[str] = (),
    handoff_reference: str | None = None,
) -> ReplayEpisode:
    """Build a validated, canonically ordered, fingerprinted replay episode."""
    require_aware_datetime(recorded_at, field="replay recorded_at")
    if not isinstance(tool_calls, Sequence):
        raise ReplayValidationError("tool calls must be a sequence")
    validated_calls: list[ReplayToolCall] = []
    for call in tool_calls:
        if type(call) is not ReplayToolCall:
            raise ReplayValidationError("tool calls must contain only ReplayToolCall values")
        call.revalidate()
        validated_calls.append(call)
    calls = _sort_tool_calls(tuple(validated_calls))
    material = _episode_material(
        episode_id,
        recorded_at,
        world_snapshot_id,
        tuple(attention_reasons),
        goal_plan_state,
        calls,
        tuple(counterfactuals),
        tuple(uncertainties),
        tuple(contradictions),
        tuple(evidence_refs),
        tuple(changes_after),
        handoff_reference,
    )
    return ReplayEpisode(
        episode_id=episode_id,
        recorded_at=recorded_at,
        world_snapshot_id=world_snapshot_id,
        attention_reasons=tuple(attention_reasons),
        goal_plan_state=goal_plan_state,
        tool_calls=calls,
        counterfactuals=tuple(counterfactuals),
        uncertainties=tuple(uncertainties),
        contradictions=tuple(contradictions),
        evidence_refs=tuple(evidence_refs),
        changes_after=tuple(changes_after),
        handoff_reference=handoff_reference,
        fingerprint=fingerprint_material(material),
    )


def replay_episode(episode: ReplayEpisode) -> ReplayReconstruction:
    """Deterministically replay an episode without reading clock or network."""
    if type(episode) is not ReplayEpisode:
        raise ReplayValidationError("episode must be a ReplayEpisode")
    episode.revalidate()
    return ReplayReconstruction(
        episode_id=episode.episode_id,
        recorded_at=episode.recorded_at,
        view=episode.logical_values(),
        fingerprint=episode.fingerprint,
    )


class CognitiveHandoffKind(StrEnum):
    """Authority-free handoff kind: recommendation or formal request."""

    RECOMMENDATION = "recommendation"
    FORMAL_REQUEST = "formal-request"


@dataclass(frozen=True, slots=True)
class CognitiveHandoff:
    """Typed, authority-free handoff envelope for an external policy/Risk pipeline."""

    handoff_id: UUID
    kind: CognitiveHandoffKind
    source_reference: str
    summary: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.handoff_id) is not UUID:
            raise ReplayValidationError("handoff id must be a UUID")
        if type(self.kind) is not CognitiveHandoffKind:
            raise ReplayValidationError("handoff kind must be a CognitiveHandoffKind")
        _require_text(self.source_reference, field="handoff source reference")
        _require_text(self.summary, field="handoff summary")
        evidence_refs = _require_texts(self.evidence_refs, field="handoff evidence refs")
        if not evidence_refs:
            raise ReplayValidationError("handoff must cite at least one evidence reference")


class CognitiveUtteranceKind(StrEnum):
    """Dialogue/opinion seam kinds. Never a formal signal."""

    OPINION = "opinion"
    DIALOGUE = "dialogue"


@dataclass(frozen=True, slots=True)
class CognitiveUtterance:
    """Typed cognitive-dialogue/opinion seam. Never a formal signal implicitly."""

    utterance_id: UUID
    kind: CognitiveUtteranceKind
    content: str
    source: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.utterance_id) is not UUID:
            raise ReplayValidationError("utterance id must be a UUID")
        if type(self.kind) is not CognitiveUtteranceKind:
            raise ReplayValidationError("utterance kind must be a CognitiveUtteranceKind")
        _require_text(self.content, field="utterance content")
        _require_text(self.source, field="utterance source")


__all__ = [
    "CognitiveHandoff",
    "CognitiveHandoffKind",
    "CognitiveUtterance",
    "CognitiveUtteranceKind",
    "ReplayEpisode",
    "ReplayError",
    "ReplayReconstruction",
    "ReplayToolCall",
    "ReplayValidationError",
    "build_replay_episode",
    "replay_episode",
]
