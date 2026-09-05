"""CIBO Cognitive Attention, Reasoning Routing, and Calibration seam (CA-05/06/09).

Deterministic, evidence-bound context-selection primitives for anomalies,
unresolved contradictions, stale/missing evidence, pending goals, economic/risk
deterioration references, and high-value research questions. Priorities carry
bounded integer scores/ranks and explicit priority reasons — never hidden model
authority.

The reasoning-routing seam represents *why* a deeper reasoning mode is
requested, *what* evidence is missing, and *when* abstention is required. It is
a complementary seam that binds later to Batch 006 FAST/HIGH/MAX/
COUNCIL_ADVERSARIAL modes at the Cognitive Integration Gate; it does **not**
define a second reasoning-mode enum.

The calibration seam carries a bounded confidence band, a note, and an explicit
abstention flag without redefining Batch 006 uncertainty enums.

Architecture laws honoured: no fabricated evidence (5, 7), deterministic
ordering (19), exact int scores / ``bool != int`` (15), secret-bearing strings
fail closed (20), no global mutable state (21), no ambient time/RNG (14).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    contains_secret_material,
    require_exact_int,
    require_exact_str,
)

_DEPTH_HINTS = frozenset({"fast", "high", "max", "council_adversarial"})

# Substrate-native calibration kind tokens (underscore convention, mirroring
# _DEPTH_HINTS); the integration gate maps these to the Batch 006
# CiboUncertaintyKind enum. An empty token means "derive from abstention_required
# and confidence_band". This is a separate substrate vocabulary and does not
# redefine the Batch 006 enum.
_CALIBRATION_KINDS = frozenset(
    {
        "",
        "insufficient_evidence",
        "unresolved_contradiction",
        "competing_hypotheses",
        "more_evidence_requested",
        "abstain_defer",
        "bounded_confidence",
    }
)


class AttentionError(CiboCognitiveError):
    """Base error for the CIBO cognitive attention substrate."""

    __slots__ = ()


class AttentionValidationError(AttentionError, CiboCognitiveValidationError):
    """Violation of a cognitive attention invariant."""

    __slots__ = ()


class AttentionSignalKind(StrEnum):
    """Context-selection reason categories (evidence-bound, no authority)."""

    ANOMALY = "anomaly"
    CONTRADICTION = "contradiction"
    STALE_EVIDENCE = "stale-evidence"
    MISSING_EVIDENCE = "missing-evidence"
    PENDING_GOAL = "pending-goal"
    RISK_DETERIORATION = "risk-deterioration"
    RESEARCH_QUESTION = "research-question"


@dataclass(frozen=True, slots=True)
class AttentionEvidenceRef:
    """Explicit reference to the evidence backing an attention signal."""

    reference_id: str
    fingerprint: CiboCognitiveFingerprint | None = None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_str(self.reference_id, field="attention evidence reference id")
        if not self.reference_id.strip():
            raise AttentionValidationError("attention evidence reference id must not be blank")
        if contains_secret_material(self.reference_id):
            raise AttentionValidationError(
                "attention evidence reference id must not carry secret-bearing material"
            )
        if self.fingerprint is not None:
            if type(self.fingerprint) is not CiboCognitiveFingerprint:
                raise AttentionValidationError(
                    "attention evidence fingerprint must be a CiboCognitiveFingerprint"
                )
            self.fingerprint.revalidate()

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.reference_id,
            self.fingerprint.value if self.fingerprint is not None else None,
        )

    def sort_key(self) -> tuple[str, str]:
        return (
            self.reference_id,
            self.fingerprint.value if self.fingerprint is not None else "",
        )


@dataclass(frozen=True, slots=True)
class AttentionSignal:
    """One evidence-bound candidate for cognitive context selection."""

    signal_id: UUID
    kind: AttentionSignalKind
    summary: str
    evidence_refs: tuple[AttentionEvidenceRef, ...]
    severity: int
    priority_reason: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.signal_id) is not UUID:
            raise AttentionValidationError("attention signal id must be a UUID")
        if type(self.kind) is not AttentionSignalKind:
            raise AttentionValidationError("attention signal kind must be an AttentionSignalKind")
        require_exact_str(self.summary, field="attention signal summary")
        if not self.summary.strip():
            raise AttentionValidationError("attention signal summary must not be blank")
        if contains_secret_material(self.summary):
            raise AttentionValidationError(
                "attention signal summary must not carry secret-bearing material"
            )
        if type(self.evidence_refs) is not tuple:
            raise AttentionValidationError("attention evidence refs must be a tuple")
        if not self.evidence_refs:
            raise AttentionValidationError(
                "attention signal must carry at least one evidence reference"
            )
        for ref in self.evidence_refs:
            if type(ref) is not AttentionEvidenceRef:
                raise AttentionValidationError(
                    "attention evidence refs must contain only AttentionEvidenceRef values"
                )
            ref.revalidate()
        require_exact_int(self.severity, field="attention signal severity")
        if not 0 <= self.severity <= 100:
            raise AttentionValidationError("attention signal severity must be in [0, 100]")
        require_exact_str(self.priority_reason, field="attention priority reason")
        if not self.priority_reason.strip():
            raise AttentionValidationError("attention priority reason must not be blank")
        if contains_secret_material(self.priority_reason):
            raise AttentionValidationError(
                "attention priority reason must not carry secret-bearing material"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.signal_id),
            self.kind.value,
            self.summary,
            tuple(ref.logical_values() for ref in self.evidence_refs),
            self.severity,
            self.priority_reason,
        )

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.summary,
            tuple(ref.sort_key() for ref in self.evidence_refs),
            self.severity,
            self.priority_reason,
            str(self.signal_id),
        )


@dataclass(frozen=True, slots=True)
class RankedSignal:
    """A signal paired with its bounded, deterministic score."""

    signal: AttentionSignal
    score: int

    def __post_init__(self) -> None:
        if type(self.signal) is not AttentionSignal:
            raise AttentionValidationError("ranked signal must wrap an AttentionSignal")
        require_exact_int(self.score, field="ranked signal score")
        if not 0 <= self.score <= 100:
            raise AttentionValidationError("ranked signal score must be in [0, 100]")


@dataclass(frozen=True, slots=True)
class ContextSelectionResult:
    """Deterministically ranked context-selection result."""

    ranked: tuple[RankedSignal, ...]

    def __post_init__(self) -> None:
        if type(self.ranked) is not tuple:
            raise AttentionValidationError("ranked signals must be a tuple")
        for item in self.ranked:
            if type(item) is not RankedSignal:
                raise AttentionValidationError(
                    "ranked signals must contain only RankedSignal values"
                )


def _score(signal: AttentionSignal) -> int:
    return signal.severity


def select_context(
    signals: Sequence[AttentionSignal], *, max_results: int = 10
) -> ContextSelectionResult:
    """Rank signals deterministically without inventing any evidence.

    Every signal is revalidated (recursive revalidation of nested evidence
    references) before ranking. Ranking is by descending bounded score, with a
    canonical tiebreak that is invariant under input permutation.
    """
    if not isinstance(signals, Sequence):
        raise AttentionValidationError("signals must be a sequence")
    require_exact_int(max_results, field="max results")
    if max_results <= 0:
        raise AttentionValidationError("max results must be a positive integer")
    scored: list[RankedSignal] = []
    for signal in signals:
        if type(signal) is not AttentionSignal:
            raise AttentionValidationError("signals must contain only AttentionSignal values")
        signal.revalidate()
        scored.append(RankedSignal(signal=signal, score=_score(signal)))
    scored.sort(key=lambda item: (-item.score, item.signal.sort_key()))
    return ContextSelectionResult(ranked=tuple(scored[:max_results]))


class ReasoningRouteDecision(StrEnum):
    """Routing decision: proceed, or abstain for insufficient evidence."""

    PROCEED = "proceed"
    ABSTAIN_INSUFFICIENT_EVIDENCE = "abstain-insufficient-evidence"


@dataclass(frozen=True, slots=True)
class ReasoningDepthHint:
    """Complementary depth hint bound to Batch 006 reasoning modes at the gate."""

    value: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_str(self.value, field="reasoning depth hint")
        if self.value not in _DEPTH_HINTS:
            raise AttentionValidationError(
                "reasoning depth hint must be one of fast, high, max, council_adversarial"
            )

    def logical_values(self) -> tuple[str]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ReasoningRequest:
    """Why deeper reasoning is requested and what evidence is missing."""

    request_id: UUID
    depth_hint: ReasoningDepthHint
    missing_evidence: tuple[str, ...]
    justification: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.request_id) is not UUID:
            raise AttentionValidationError("reasoning request id must be a UUID")
        if type(self.depth_hint) is not ReasoningDepthHint:
            raise AttentionValidationError(
                "reasoning depth hint must be a ReasoningDepthHint"
            )
        self.depth_hint.revalidate()
        if type(self.missing_evidence) is not tuple:
            raise AttentionValidationError("missing evidence must be a tuple")
        for item in self.missing_evidence:
            require_exact_str(item, field="missing evidence item")
            if not item.strip():
                raise AttentionValidationError("missing evidence item must not be blank")
            if contains_secret_material(item):
                raise AttentionValidationError(
                    "missing evidence item must not carry secret-bearing material"
                )
        require_exact_str(self.justification, field="reasoning justification")
        if not self.justification.strip():
            raise AttentionValidationError("reasoning justification must not be blank")
        if contains_secret_material(self.justification):
            raise AttentionValidationError(
                "reasoning justification must not carry secret-bearing material"
            )


@dataclass(frozen=True, slots=True)
class ReasoningRoutingOutcome:
    """Deterministic routing outcome with explicit requested evidence."""

    decision: ReasoningRouteDecision
    reasons: tuple[str, ...]
    requested_evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.decision) is not ReasoningRouteDecision:
            raise AttentionValidationError(
                "reasoning routing decision must be a ReasoningRouteDecision"
            )
        if type(self.reasons) is not tuple or not self.reasons:
            raise AttentionValidationError("routing reasons must be a non-empty tuple")
        for reason in self.reasons:
            require_exact_str(reason, field="routing reason")
            if not reason.strip():
                raise AttentionValidationError("routing reason must not be blank")
            if contains_secret_material(reason):
                raise AttentionValidationError(
                    "routing reason must not carry secret-bearing material"
                )
        if type(self.requested_evidence) is not tuple:
            raise AttentionValidationError("requested evidence must be a tuple")
        for item in self.requested_evidence:
            require_exact_str(item, field="requested evidence item")
            if not item.strip():
                raise AttentionValidationError("requested evidence item must not be blank")
            if contains_secret_material(item):
                raise AttentionValidationError(
                    "requested evidence item must not carry secret-bearing material"
                )
        if self.decision is ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE:
            if not self.requested_evidence:
                raise AttentionValidationError(
                    "abstention requires at least one requested evidence item"
                )
        elif self.requested_evidence:
            raise AttentionValidationError(
                "proceed decision must not request additional evidence"
            )


def route_reasoning(request: ReasoningRequest) -> ReasoningRoutingOutcome:
    """Route a deeper-reasoning request; abstain when evidence is missing."""
    if type(request) is not ReasoningRequest:
        raise AttentionValidationError("request must be a ReasoningRequest")
    request.revalidate()
    if request.missing_evidence:
        return ReasoningRoutingOutcome(
            decision=ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE,
            reasons=("insufficient evidence to reason deeper",),
            requested_evidence=request.missing_evidence,
        )
    return ReasoningRoutingOutcome(
        decision=ReasoningRouteDecision.PROCEED,
        reasons=(request.justification,),
        requested_evidence=(),
    )


@dataclass(frozen=True, slots=True)
class CalibrationNote:
    """Bounded calibration/abstention seam (does not redefine uncertainty enums).

    ``kind`` is an optional substrate-native token carrying the explicit
    uncertainty signal; an empty token means "derive from abstention_required +
    confidence_band".
    """

    confidence_band: int
    note: str
    abstention_required: bool
    kind: str = ""

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        require_exact_int(self.confidence_band, field="calibration confidence band")
        if not 0 <= self.confidence_band <= 100:
            raise AttentionValidationError("calibration confidence band must be in [0, 100]")
        require_exact_str(self.note, field="calibration note")
        if not self.note.strip():
            raise AttentionValidationError("calibration note must not be blank")
        if contains_secret_material(self.note):
            raise AttentionValidationError(
                "calibration note must not carry secret-bearing material"
            )
        if type(self.abstention_required) is not bool:
            raise AttentionValidationError(
                "calibration abstention flag must be an exact bool"
            )
        require_exact_str(self.kind, field="calibration kind")
        if self.kind not in _CALIBRATION_KINDS:
            raise AttentionValidationError(
                "calibration kind must be one of the bounded substrate tokens"
            )


def calibration_requires_abstention(note: CalibrationNote) -> bool:
    """Return whether the calibration seam requires abstention."""
    if type(note) is not CalibrationNote:
        raise AttentionValidationError("note must be a CalibrationNote")
    note.revalidate()
    return note.abstention_required


__all__ = [
    "AttentionError",
    "AttentionEvidenceRef",
    "AttentionSignal",
    "AttentionSignalKind",
    "AttentionValidationError",
    "CalibrationNote",
    "ContextSelectionResult",
    "RankedSignal",
    "ReasoningDepthHint",
    "ReasoningRequest",
    "ReasoningRouteDecision",
    "ReasoningRoutingOutcome",
    "calibration_requires_abstention",
    "route_reasoning",
    "select_context",
]
