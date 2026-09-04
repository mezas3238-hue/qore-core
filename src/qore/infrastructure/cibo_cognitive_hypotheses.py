"""CIBO Cognitive persistent hypothesis lifecycle substrate (CA strengthening 3.4).

CIBO hypotheses have a durable, replayable lifecycle instead of being disposable
text. Each hypothesis has a stable identity + revision/version lineage, a content
fingerprint, evidence-for/against/contradiction/tests, confidence bounded by
evidence, an explicit supersession chain with cycle prevention, and no
mutation-in-place of prior historical versions. Causal hypotheses may participate
via an optional ``(id, fingerprint)`` binding without making every hypothesis
causal.

Lifecycle: BORN -> ACTIVE/UNDER_TEST -> CONFIRMED|REFUTED|INCONCLUSIVE ->
REVISED/SUPERSEDED. Invalid direct terminal-state construction without required
evidence fails closed; refuted hypotheses cannot resurrect without a new revision;
supersession is acyclic and auditable.

Laws honoured: confirmation derives from retained evidence (never a caller bool);
exact runtime types (bool != int); deterministic ordering + self-fingerprints;
secret-bearing strings fail closed; no ambient time/RNG/network; no global mutable
state; no authority transfer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import compile
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    contains_secret_material,
    fingerprint_material,
    require_aware_datetime,
    require_exact_int,
    require_exact_str,
    utc_instant,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


class HypothesisError(CiboCognitiveError):
    """Base error for the CIBO cognitive hypothesis lifecycle substrate."""

    __slots__ = ()


class HypothesisValidationError(HypothesisError, CiboCognitiveValidationError):
    """A hypothesis violates a deterministic lifecycle-integrity invariant."""

    __slots__ = ()


class HypothesisStatus(StrEnum):
    """Typed hypothesis lifecycle states."""

    BORN = "born"
    ACTIVE = "active"
    UNDER_TEST = "under-test"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"
    REVISED = "revised"
    SUPERSEDED = "superseded"


class HypothesisEvidencePolarity(StrEnum):
    """Evidence polarity toward a hypothesis."""

    SUPPORTS = "supports"
    AGAINST = "against"
    CONTRADICTION = "contradiction"
    TEST_RESULT = "test-result"


# Valid transitions (a hypothesis is immutable; transitions build a new revision).
_VALID_TRANSITIONS: dict[HypothesisStatus, frozenset[HypothesisStatus]] = {
    HypothesisStatus.BORN: frozenset({HypothesisStatus.ACTIVE, HypothesisStatus.UNDER_TEST}),
    HypothesisStatus.ACTIVE: frozenset(
        {
            HypothesisStatus.UNDER_TEST,
            HypothesisStatus.CONFIRMED,
            HypothesisStatus.REFUTED,
            HypothesisStatus.INCONCLUSIVE,
            HypothesisStatus.SUPERSEDED,
        }
    ),
    HypothesisStatus.UNDER_TEST: frozenset(
        {
            HypothesisStatus.CONFIRMED,
            HypothesisStatus.REFUTED,
            HypothesisStatus.INCONCLUSIVE,
            HypothesisStatus.SUPERSEDED,
        }
    ),
    HypothesisStatus.CONFIRMED: frozenset(
        {HypothesisStatus.REVISED, HypothesisStatus.SUPERSEDED}
    ),
    HypothesisStatus.REFUTED: frozenset(
        {HypothesisStatus.REVISED, HypothesisStatus.SUPERSEDED}
    ),
    HypothesisStatus.INCONCLUSIVE: frozenset(
        {HypothesisStatus.REVISED, HypothesisStatus.SUPERSEDED}
    ),
    HypothesisStatus.REVISED: frozenset(
        {HypothesisStatus.ACTIVE, HypothesisStatus.SUPERSEDED}
    ),
    HypothesisStatus.SUPERSEDED: frozenset(),
}


def _validate_code(value: object, *, field: str) -> str:
    text = require_exact_str(value, field=field)
    if compile(_CODE_RE).fullmatch(text) is None:
        raise HypothesisValidationError(
            f"{field} must use canonical lowercase code syntax"
        )
    if contains_secret_material(text):
        raise HypothesisValidationError(f"{field} must not carry secret-bearing material")
    return text


def _canonical_codes(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(v) is not str for v in values):
        raise HypothesisValidationError(f"{field} must be an immutable tuple of strings")
    normalized = tuple(_validate_code(v, field=field) for v in values)
    if len(set(normalized)) != len(normalized):
        raise HypothesisValidationError(f"{field} must not contain duplicates")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class HypothesisEvidence:
    """One evidence-bound observation for/against/contradicting a hypothesis."""

    ref: CiboCognitiveEvidenceRef
    polarity: HypothesisEvidencePolarity
    observed_at: datetime
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.ref) is not CiboCognitiveEvidenceRef:
            raise HypothesisValidationError(
                "hypothesis evidence ref must be a CiboCognitiveEvidenceRef"
            )
        self.ref.revalidate()
        if type(self.polarity) is not HypothesisEvidencePolarity:
            raise HypothesisValidationError(
                "hypothesis evidence polarity must be a HypothesisEvidencePolarity"
            )
        require_aware_datetime(self.observed_at, field="hypothesis evidence observed_at")
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise HypothesisValidationError(
                "hypothesis evidence fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        expected = fingerprint_material(
            (self.ref.value, self.polarity.value, self.observed_at)
        )
        if self.fingerprint != expected:
            raise HypothesisValidationError(
                "hypothesis evidence fingerprint does not match its content"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.ref.value,
            self.polarity.value,
            utc_instant(self.observed_at, field="hypothesis evidence observed_at"),
        )

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.polarity.value,
            self.ref.value,
            utc_instant(self.observed_at, field="hypothesis evidence observed_at"),
        )


def _validate_causal_claim_ref(causal_claim_ref: tuple[object, ...] | None) -> None:
    """Validate the optional ``(id, fingerprint)`` causal binding.

    Shared by ``build_hypothesis`` (before the fingerprint is derived) and
    ``Hypothesis.revalidate`` so a malformed binding always fails closed as a
    ``HypothesisValidationError`` rather than crashing during materialization.
    """
    if causal_claim_ref is None:
        return
    if type(causal_claim_ref) is not tuple or len(causal_claim_ref) != 2:
        raise HypothesisValidationError(
            "causal claim ref must be a (id, fingerprint) tuple or None"
        )
    if type(causal_claim_ref[0]) is not UUID:
        raise HypothesisValidationError("causal claim ref id must be a UUID")
    if type(causal_claim_ref[1]) is not CiboCognitiveFingerprint:
        raise HypothesisValidationError(
            "causal claim ref fingerprint must be a CiboCognitiveFingerprint"
        )
    causal_claim_ref[1].revalidate()


def _causal_ref_material(
    causal_claim_ref: tuple[object, ...] | None,
) -> tuple[str, str] | None:
    """Project a validated causal binding to canonical ``(id, fingerprint)`` material.

    Re-validates the binding and narrows its runtime types for mypy, so malformed
    input fails closed as a ``HypothesisValidationError`` rather than crashing.
    """
    _validate_causal_claim_ref(causal_claim_ref)
    if causal_claim_ref is None:
        return None
    claim_id = causal_claim_ref[0]
    claim_fp = causal_claim_ref[1]
    if type(claim_id) is not UUID or type(claim_fp) is not CiboCognitiveFingerprint:
        raise HypothesisValidationError("causal claim ref must be a validated binding")
    return (str(claim_id), claim_fp.value)


def _canonical_evidence(
    values: tuple[HypothesisEvidence, ...],
    *,
    field: str,
    polarity: HypothesisEvidencePolarity | None = None,
) -> tuple[HypothesisEvidence, ...]:
    if type(values) is not tuple or any(type(v) is not HypothesisEvidence for v in values):
        raise HypothesisValidationError(
            f"{field} must be an immutable tuple of HypothesisEvidence"
        )
    for item in values:
        item.revalidate()
        if polarity is not None and item.polarity is not polarity:
            # A channel is typed by its polarity: evidence_for/against/
            # contradictions/tests must carry only their own polarity, so a
            # caller cannot relabel generic evidence into a governed channel.
            raise HypothesisValidationError(
                f"{field} must carry only {polarity.value} evidence"
            )
    # Dedup over canonical instant semantics (logical_values normalizes every
    # observed_at to its UTC instant), so genuinely-distinct DST-fold instants
    # remain distinct while equivalent-offset representations of one instant
    # dedup identically — never relying on fold-blind aware-datetime equality.
    seen: set[tuple[object, ...]] = set()
    for item in values:
        key = item.logical_values()
        if key in seen:
            raise HypothesisValidationError(f"{field} must not contain duplicate evidence")
        seen.add(key)
    return tuple(sorted(values, key=lambda item: item.sort_key()))


@dataclass(frozen=True, slots=True)
class Hypothesis:
    """One durable, revisioned, evidence-bound hypothesis."""

    hypothesis_id: UUID
    content_code: str
    revision: int
    revision_parent: UUID | None
    status: HypothesisStatus
    evidence_for: tuple[HypothesisEvidence, ...]
    evidence_against: tuple[HypothesisEvidence, ...]
    contradictions: tuple[HypothesisEvidence, ...]
    tests: tuple[HypothesisEvidence, ...]
    confidence: CiboConfidence | None
    supersedes: UUID | None
    causal_claim_ref: tuple[object, ...] | None
    fingerprint: CiboCognitiveFingerprint
    reason_code: str | None = None

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.hypothesis_id) is not UUID:
            raise HypothesisValidationError("hypothesis id must be a UUID")
        object.__setattr__(
            self, "content_code", _validate_code(self.content_code, field="hypothesis content")
        )
        require_exact_int(self.revision, field="hypothesis revision")
        if self.revision < 0:
            raise HypothesisValidationError("hypothesis revision must be non-negative")
        if self.revision_parent is not None and type(self.revision_parent) is not UUID:
            raise HypothesisValidationError("revision parent must be a UUID or None")
        if type(self.status) is not HypothesisStatus:
            raise HypothesisValidationError("hypothesis status must be a HypothesisStatus")
        object.__setattr__(
            self,
            "evidence_for",
            _canonical_evidence(
                self.evidence_for,
                field="hypothesis evidence for",
                polarity=HypothesisEvidencePolarity.SUPPORTS,
            ),
        )
        object.__setattr__(
            self,
            "evidence_against",
            _canonical_evidence(
                self.evidence_against,
                field="hypothesis evidence against",
                polarity=HypothesisEvidencePolarity.AGAINST,
            ),
        )
        object.__setattr__(
            self,
            "contradictions",
            _canonical_evidence(
                self.contradictions,
                field="hypothesis contradictions",
                polarity=HypothesisEvidencePolarity.CONTRADICTION,
            ),
        )
        object.__setattr__(
            self,
            "tests",
            _canonical_evidence(
                self.tests,
                field="hypothesis tests",
                polarity=HypothesisEvidencePolarity.TEST_RESULT,
            ),
        )
        if self.confidence is not None:
            if type(self.confidence) is not CiboConfidence:
                raise HypothesisValidationError(
                    "hypothesis confidence must be CiboConfidence or None"
                )
            self.confidence.revalidate()
        if self.supersedes is not None and type(self.supersedes) is not UUID:
            raise HypothesisValidationError("hypothesis supersedes must be a UUID or None")
        if self.supersedes == self.hypothesis_id:
            raise HypothesisValidationError("a hypothesis must not supersede itself")
        _validate_causal_claim_ref(self.causal_claim_ref)
        if self.reason_code is not None:
            object.__setattr__(
                self,
                "reason_code",
                _validate_code(self.reason_code, field="revision reason code"),
            )
        self._validate_status_evidence()
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise HypothesisValidationError(
                "hypothesis fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if self.fingerprint != fingerprint_material(self.logical_values()):
            raise HypothesisValidationError(
                "hypothesis fingerprint does not match its canonical content"
            )

    def _validate_status_evidence(self) -> None:
        if self.status is HypothesisStatus.CONFIRMED:
            # CONFIRMATION != FAVORABLE OUTCOME: a confirmed hypothesis requires
            # governed test/prediction evidence, never a mere favorable support
            # observation (evidence_for) on its own.
            if not self.tests:
                raise HypothesisValidationError(
                    "a confirmed hypothesis requires governed test/prediction evidence"
                )
            if self.evidence_against or self.contradictions:
                raise HypothesisValidationError(
                    "a confirmed hypothesis must not carry against/contradiction evidence"
                )
        if self.status is HypothesisStatus.REFUTED:
            if not self.evidence_against and not self.contradictions:
                raise HypothesisValidationError(
                    "a refuted hypothesis requires falsifying evidence"
                )
        if self.status is HypothesisStatus.SUPERSEDED:
            if self.supersedes is None:
                raise HypothesisValidationError(
                    "a superseded hypothesis must reference its superseding hypothesis"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.hypothesis_id),
            self.content_code,
            self.revision,
            None if self.revision_parent is None else str(self.revision_parent),
            self.status.value,
            tuple(e.logical_values() for e in self.evidence_for),
            tuple(e.logical_values() for e in self.evidence_against),
            tuple(e.logical_values() for e in self.contradictions),
            tuple(e.logical_values() for e in self.tests),
            None if self.confidence is None else self.confidence.logical_values(),
            None if self.supersedes is None else str(self.supersedes),
            _causal_ref_material(self.causal_claim_ref),
            self.reason_code,
        )


def _material(
    hypothesis_id: UUID,
    content_code: str,
    revision: int,
    revision_parent: UUID | None,
    status: HypothesisStatus,
    evidence_for: tuple[HypothesisEvidence, ...],
    evidence_against: tuple[HypothesisEvidence, ...],
    contradictions: tuple[HypothesisEvidence, ...],
    tests: tuple[HypothesisEvidence, ...],
    confidence: CiboConfidence | None,
    supersedes: UUID | None,
    causal_claim_ref: tuple[object, ...] | None,
    reason_code: str | None,
) -> tuple[object, ...]:
    return (
        str(hypothesis_id),
        content_code,
        revision,
        None if revision_parent is None else str(revision_parent),
        status.value,
        tuple(e.logical_values() for e in evidence_for),
        tuple(e.logical_values() for e in evidence_against),
        tuple(e.logical_values() for e in contradictions),
        tuple(e.logical_values() for e in tests),
        None if confidence is None else confidence.logical_values(),
        None if supersedes is None else str(supersedes),
        _causal_ref_material(causal_claim_ref),
        reason_code,
    )


def build_hypothesis(
    *,
    hypothesis_id: UUID,
    content_code: str,
    revision: int = 0,
    revision_parent: UUID | None = None,
    status: HypothesisStatus = HypothesisStatus.BORN,
    evidence_for: Sequence[HypothesisEvidence] = (),
    evidence_against: Sequence[HypothesisEvidence] = (),
    contradictions: Sequence[HypothesisEvidence] = (),
    tests: Sequence[HypothesisEvidence] = (),
    confidence: CiboConfidence | None = None,
    supersedes: UUID | None = None,
    causal_claim_ref: tuple[object, ...] | None = None,
    reason_code: str | None = None,
) -> Hypothesis:
    """Build a validated, canonically ordered, fingerprinted hypothesis."""
    if not isinstance(evidence_for, Sequence):
        raise HypothesisValidationError("evidence_for must be a sequence")
    if not isinstance(evidence_against, Sequence):
        raise HypothesisValidationError("evidence_against must be a sequence")
    if not isinstance(contradictions, Sequence):
        raise HypothesisValidationError("contradictions must be a sequence")
    if not isinstance(tests, Sequence):
        raise HypothesisValidationError("tests must be a sequence")
    _validate_causal_claim_ref(causal_claim_ref)
    # Canonicalize every semantically-unordered sequence BEFORE deriving the
    # fingerprint, so any permutation of the same semantic input produces the
    # same canonical state and fingerprint (constructor == revalidate).
    canonical_for = _canonical_evidence(
        tuple(evidence_for),
        field="hypothesis evidence for",
        polarity=HypothesisEvidencePolarity.SUPPORTS,
    )
    canonical_against = _canonical_evidence(
        tuple(evidence_against),
        field="hypothesis evidence against",
        polarity=HypothesisEvidencePolarity.AGAINST,
    )
    canonical_contradictions = _canonical_evidence(
        tuple(contradictions),
        field="hypothesis contradictions",
        polarity=HypothesisEvidencePolarity.CONTRADICTION,
    )
    canonical_tests = _canonical_evidence(
        tuple(tests),
        field="hypothesis tests",
        polarity=HypothesisEvidencePolarity.TEST_RESULT,
    )
    return Hypothesis(
        hypothesis_id=hypothesis_id,
        content_code=content_code,
        revision=revision,
        revision_parent=revision_parent,
        status=status,
        evidence_for=canonical_for,
        evidence_against=canonical_against,
        contradictions=canonical_contradictions,
        tests=canonical_tests,
        confidence=confidence,
        supersedes=supersedes,
        causal_claim_ref=causal_claim_ref,
        reason_code=reason_code,
        fingerprint=fingerprint_material(
            _material(
                hypothesis_id,
                content_code,
                revision,
                revision_parent,
                status,
                canonical_for,
                canonical_against,
                canonical_contradictions,
                canonical_tests,
                confidence,
                supersedes,
                causal_claim_ref,
                reason_code,
            )
        ),
    )


def _evidence_identity(evidence: HypothesisEvidence) -> tuple[str, datetime]:
    """Return the canonical identity of one evidence observation.

    Identity is ``(reference value, UTC instant)``: a genuinely new observation
    of the same reference at a different instant is new material, while the same
    observation re-represented under an equivalent timezone/order, re-supplied
    verbatim, or relabeled across channels/polarities is not new.
    """
    return (
        evidence.ref.value,
        utc_instant(evidence.observed_at, field="hypothesis evidence observed_at"),
    )


def _retained_evidence_identity(hypothesis: Hypothesis) -> frozenset[tuple[str, datetime]]:
    """Return the canonical identity of every evidence a hypothesis retains."""
    return frozenset(
        _evidence_identity(evidence)
        for evidence in (
            hypothesis.evidence_for
            + hypothesis.evidence_against
            + hypothesis.contradictions
            + hypothesis.tests
        )
    )


def _union_evidence(
    retained: tuple[HypothesisEvidence, ...],
    supplied: tuple[HypothesisEvidence, ...],
) -> tuple[HypothesisEvidence, ...]:
    """Merge retained and supplied evidence, deduping by canonical identity.

    Identity is ``(reference value, UTC instant)``; re-supplying evidence that
    is already retained is ignored (it is not new material), so a transition
    that re-supplies a retained falsifier alongside a genuinely new one merges
    cleanly instead of tripping the channel's duplicate-evidence check.
    """
    seen: set[tuple[str, datetime]] = set()
    merged: list[HypothesisEvidence] = []
    for evidence in (*retained, *supplied):
        identity = _evidence_identity(evidence)
        if identity not in seen:
            seen.add(identity)
            merged.append(evidence)
    return tuple(merged)


def transition_hypothesis(
    hypothesis: Hypothesis,
    new_status: HypothesisStatus,
    *,
    content_code: str | None = None,
    reason_code: str | None = None,
    evidence_for: Sequence[HypothesisEvidence] = (),
    evidence_against: Sequence[HypothesisEvidence] = (),
    contradictions: Sequence[HypothesisEvidence] = (),
    tests: Sequence[HypothesisEvidence] = (),
    confidence: CiboConfidence | None = None,
    supersedes: UUID | None = None,
    causal_claim_ref: tuple[object, ...] | None = None,
) -> Hypothesis:
    """Build the next revision of ``hypothesis`` with a governed status transition.

    The transition is validated against the lifecycle table; invalid transitions
    (including refuted resurrection without a REVISED step) fail closed. A new
    revision is always produced; prior historical versions are never mutated.
    """
    if type(hypothesis) is not Hypothesis:
        raise HypothesisValidationError("hypothesis must be a Hypothesis")
    hypothesis.revalidate()
    if type(new_status) is not HypothesisStatus:
        raise HypothesisValidationError("new status must be a HypothesisStatus")
    if new_status not in _VALID_TRANSITIONS[hypothesis.status]:
        raise HypothesisValidationError(
            f"invalid hypothesis transition {hypothesis.status.value} -> {new_status.value}"
        )
    if new_status is HypothesisStatus.SUPERSEDED and supersedes is None:
        raise HypothesisValidationError(
            "superseded transition requires the superseding hypothesis id"
        )
    if not isinstance(evidence_for, Sequence):
        raise HypothesisValidationError("evidence_for must be a sequence")
    if not isinstance(evidence_against, Sequence):
        raise HypothesisValidationError("evidence_against must be a sequence")
    if not isinstance(contradictions, Sequence):
        raise HypothesisValidationError("contradictions must be a sequence")
    if not isinstance(tests, Sequence):
        raise HypothesisValidationError("tests must be a sequence")
    if reason_code is not None:
        _validate_code(reason_code, field="revision reason code")
    if hypothesis.status is HypothesisStatus.REFUTED and new_status is HypothesisStatus.REVISED:
        # Leaving REFUTED is a governed revision, never a ceremonial transition:
        # it requires an auditable reason code plus a durable content change or
        # genuinely new evidence/test material. "New" is decided by canonical
        # evidence identity (the retained evidence reference), so re-supplying
        # the exact same evidence, the same evidence under an alternate
        # timezone/order representation, or the same evidence relabeled into a
        # different channel/polarity never counts as new.
        if reason_code is None:
            raise HypothesisValidationError(
                "leaving refuted requires an explicit revision reason code"
            )
        content_changed = content_code is not None and content_code != hypothesis.content_code
        if not content_changed:
            retained = _retained_evidence_identity(hypothesis)
            supplied = (
                _canonical_evidence(
                    tuple(evidence_for),
                    field="hypothesis evidence for",
                    polarity=HypothesisEvidencePolarity.SUPPORTS,
                )
                + _canonical_evidence(
                    tuple(evidence_against),
                    field="hypothesis evidence against",
                    polarity=HypothesisEvidencePolarity.AGAINST,
                )
                + _canonical_evidence(
                    tuple(contradictions),
                    field="hypothesis contradictions",
                    polarity=HypothesisEvidencePolarity.CONTRADICTION,
                )
                + _canonical_evidence(
                    tuple(tests),
                    field="hypothesis tests",
                    polarity=HypothesisEvidencePolarity.TEST_RESULT,
                )
            )
            if not any(_evidence_identity(evidence) not in retained for evidence in supplied):
                raise HypothesisValidationError(
                    "leaving refuted requires material new evidence or a content change"
                )
    next_code = content_code if content_code is not None else hypothesis.content_code
    # Retain falsifying evidence (contradictions + evidence_against) across
    # revisions so a hypothesis never forgets why it was refuted, and so an old
    # falsifier cannot be laundered back in as "new" later in the lineage. The
    # merge is identity-deduped (canonical reference + UTC instant), so
    # re-supplying an already-retained falsifier alongside a genuinely new one
    # is accepted without a spurious duplicate-evidence failure. Entering
    # CONFIRMED resolves prior falsification, so those channels are cleared
    # there (a confirmed hypothesis must not carry against/contradiction).
    if new_status is HypothesisStatus.CONFIRMED:
        next_against: tuple[HypothesisEvidence, ...] = ()
        next_contradictions: tuple[HypothesisEvidence, ...] = ()
    else:
        next_against = _union_evidence(hypothesis.evidence_against, tuple(evidence_against))
        next_contradictions = _union_evidence(hypothesis.contradictions, tuple(contradictions))
    # Supporting/test evidence is per-revision (replaced, not accumulated): the
    # governed new-evidence gate for leaving REFUTED scopes its canonical-identity
    # comparison to the evidence the REFUTED hypothesis itself retains (its
    # falsifying channels), matching "must not count as new the evidence already
    # retained by the refuted hypothesis". Prior revisions stay durable via
    # immutability, and their evidence is never silently erased from the lineage.
    return build_hypothesis(
        hypothesis_id=hypothesis.hypothesis_id,
        content_code=next_code,
        revision=hypothesis.revision + 1,
        revision_parent=hypothesis.hypothesis_id,
        status=new_status,
        evidence_for=tuple(evidence_for),
        evidence_against=next_against,
        contradictions=next_contradictions,
        tests=tuple(tests),
        confidence=confidence,
        supersedes=supersedes,
        causal_claim_ref=causal_claim_ref,
        reason_code=reason_code,
    )


def assert_hypothesis_lineage_acyclic(hypotheses: Sequence[Hypothesis]) -> None:
    """Raise if the ``supersedes`` graph among hypotheses contains a cycle."""
    if not isinstance(hypotheses, Sequence):
        raise HypothesisValidationError("hypotheses must be a sequence")
    by_id: dict[UUID, Hypothesis] = {}
    for hypothesis in hypotheses:
        if type(hypothesis) is not Hypothesis:
            raise HypothesisValidationError(
                "hypotheses must contain only Hypothesis values"
            )
        hypothesis.revalidate()
        if hypothesis.hypothesis_id in by_id:
            raise HypothesisValidationError("hypotheses must have unique ids")
        by_id[hypothesis.hypothesis_id] = hypothesis

    visiting: set[UUID] = set()
    visited: set[UUID] = set()

    def visit(node: UUID) -> None:
        if node in visiting:
            raise HypothesisValidationError(
                "hypothesis supersession lineage must be acyclic"
            )
        if node in visited:
            return
        visiting.add(node)
        supersedes = by_id[node].supersedes
        if supersedes is not None and supersedes in by_id:
            visit(supersedes)
        visiting.remove(node)
        visited.add(node)

    for hypothesis_id in by_id:
        visit(hypothesis_id)


__all__ = [
    "Hypothesis",
    "HypothesisError",
    "HypothesisEvidence",
    "HypothesisEvidencePolarity",
    "HypothesisStatus",
    "HypothesisValidationError",
    "assert_hypothesis_lineage_acyclic",
    "build_hypothesis",
    "transition_hypothesis",
]
