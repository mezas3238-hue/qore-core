"""CIBO Cognitive explicit causal reasoning substrate (CA strengthening 3.1).

Typed, immutable, replay-safe causal claims that keep association/correlation
strictly separate from causal attribution. A causal claim carries typed
cause/effect/context/confounder variables, typed evidence-for/against/
contradiction/limitation, a bounded strength that can never exceed evidence
sufficiency, competing causal hypotheses may be represented simultaneously, and
falsification/supersession is deterministic and auditable.

Laws honoured: correlation is not causation (an intervention/outcome correlation
never auto-upgrades to causal attribution); strength is evidence-bounded; exact
runtime types (bool != int, no subclass laundering); deterministic canonical
ordering + self-fingerprints; secret-bearing strings fail closed; no ambient
time/RNG/network; no global mutable state; no authority transfer.
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
    require_exact_str,
    utc_instant,
)
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CausalityError(CiboCognitiveError):
    """Base error for the CIBO cognitive causal reasoning substrate."""

    __slots__ = ()


class CausalityValidationError(CausalityError, CiboCognitiveValidationError):
    """A causal claim violates a deterministic causal-integrity invariant."""

    __slots__ = ()


class CausalClaimKind(StrEnum):
    """Typed separation of association from causal attribution."""

    CORRELATION = "correlation"
    CAUSATION = "causation"
    NON_CAUSAL = "non-causal"


class CausalEvidencePolarity(StrEnum):
    """Evidence polarity toward a causal claim."""

    SUPPORTS = "supports"
    AGAINST = "against"
    CONTRADICTION = "contradiction"
    LIMITATION = "limitation"


class CausalClaimStrength(StrEnum):
    """Bounded causal claim strength; never a raw float or bool."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class CausalClaimStatus(StrEnum):
    """Lifecycle status of a causal claim."""

    ACTIVE = "active"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"
    SUPERSEDED = "superseded"


def _validate_code(value: object, *, field: str) -> str:
    text = require_exact_str(value, field=field)
    if compile(_CODE_RE).fullmatch(text) is None:
        raise CausalityValidationError(
            f"{field} must use canonical lowercase code syntax"
        )
    if contains_secret_material(text):
        raise CausalityValidationError(f"{field} must not carry secret-bearing material")
    return text


def _canonical_variables(
    values: tuple[CausalVariable, ...], *, field: str
) -> tuple[CausalVariable, ...]:
    if type(values) is not tuple or any(type(v) is not CausalVariable for v in values):
        raise CausalityValidationError(
            f"{field} must be an immutable tuple of CausalVariable"
        )
    for variable in values:
        variable.revalidate()
    if len({v.code for v in values}) != len(values):
        raise CausalityValidationError(f"{field} must not contain duplicate variables")
    return tuple(sorted(values, key=lambda v: v.code))


def _canonical_evidence(
    values: tuple[CausalEvidence, ...], *, field: str
) -> tuple[CausalEvidence, ...]:
    if type(values) is not tuple or any(type(v) is not CausalEvidence for v in values):
        raise CausalityValidationError(
            f"{field} must be an immutable tuple of CausalEvidence"
        )
    for item in values:
        item.revalidate()
    if len(set(values)) != len(values):
        raise CausalityValidationError(f"{field} must not contain duplicate evidence")
    return tuple(sorted(values, key=lambda item: item.sort_key()))


@dataclass(frozen=True, slots=True)
class CausalVariable:
    """One typed variable in a causal model (cause/effect/context/confounder)."""

    code: str
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        object.__setattr__(self, "code", _validate_code(self.code, field="causal variable"))
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CausalityValidationError(
                "causal variable fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if self.fingerprint != fingerprint_material((self.code,)):
            raise CausalityValidationError(
                "causal variable fingerprint does not match its code"
            )

    def logical_values(self) -> tuple[str, str]:
        return (self.code, self.fingerprint.value)


@dataclass(frozen=True, slots=True)
class CausalEvidence:
    """One evidence-bound observation for/against/contradicting a claim."""

    ref: CiboCognitiveEvidenceRef
    polarity: CausalEvidencePolarity
    observed_at: datetime
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.ref) is not CiboCognitiveEvidenceRef:
            raise CausalityValidationError(
                "causal evidence ref must be a CiboCognitiveEvidenceRef"
            )
        self.ref.revalidate()
        if type(self.polarity) is not CausalEvidencePolarity:
            raise CausalityValidationError(
                "causal evidence polarity must be a CausalEvidencePolarity"
            )
        require_aware_datetime(self.observed_at, field="causal evidence observed_at")
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CausalityValidationError(
                "causal evidence fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        expected = fingerprint_material(
            (self.ref.value, self.polarity.value, self.observed_at)
        )
        if self.fingerprint != expected:
            raise CausalityValidationError(
                "causal evidence fingerprint does not match its content"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.ref.value,
            self.polarity.value,
            utc_instant(self.observed_at, field="causal evidence observed_at"),
        )

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.polarity.value,
            self.ref.value,
            utc_instant(self.observed_at, field="causal evidence observed_at"),
        )


@dataclass(frozen=True, slots=True)
class CausalClaim:
    """One typed causal hypothesis/claim with evidence-bounded strength."""

    claim_id: UUID
    kind: CausalClaimKind
    cause: CausalVariable
    effect: CausalVariable
    context: tuple[CausalVariable, ...]
    confounders: tuple[CausalVariable, ...]
    confounders_addressed: bool
    evidence_for: tuple[CausalEvidence, ...]
    evidence_against: tuple[CausalEvidence, ...]
    contradictions: tuple[CausalEvidence, ...]
    limitations: tuple[CausalEvidence, ...]
    strength: CausalClaimStrength
    status: CausalClaimStatus
    supersedes: UUID | None
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.claim_id) is not UUID:
            raise CausalityValidationError("causal claim id must be a UUID")
        if type(self.kind) is not CausalClaimKind:
            raise CausalityValidationError("causal claim kind must be a CausalClaimKind")
        if type(self.cause) is not CausalVariable:
            raise CausalityValidationError("causal claim cause must be a CausalVariable")
        self.cause.revalidate()
        if type(self.effect) is not CausalVariable:
            raise CausalityValidationError("causal claim effect must be a CausalVariable")
        self.effect.revalidate()
        if self.cause.code == self.effect.code:
            raise CausalityValidationError("cause and effect must be distinct variables")
        object.__setattr__(
            self, "context", _canonical_variables(self.context, field="causal context")
        )
        object.__setattr__(
            self,
            "confounders",
            _canonical_variables(self.confounders, field="causal confounders"),
        )
        if type(self.confounders_addressed) is not bool:
            raise CausalityValidationError(
                "confounders_addressed must be an exact bool"
            )
        object.__setattr__(
            self,
            "evidence_for",
            _canonical_evidence(self.evidence_for, field="causal evidence for"),
        )
        object.__setattr__(
            self,
            "evidence_against",
            _canonical_evidence(self.evidence_against, field="causal evidence against"),
        )
        object.__setattr__(
            self,
            "contradictions",
            _canonical_evidence(self.contradictions, field="causal contradictions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _canonical_evidence(self.limitations, field="causal limitations"),
        )
        if type(self.strength) is not CausalClaimStrength:
            raise CausalityValidationError(
                "causal claim strength must be a CausalClaimStrength"
            )
        if type(self.status) is not CausalClaimStatus:
            raise CausalityValidationError(
                "causal claim status must be a CausalClaimStatus"
            )
        if self.supersedes is not None and type(self.supersedes) is not UUID:
            raise CausalityValidationError("causal supersedes must be a UUID or None")
        if self.supersedes == self.claim_id:
            raise CausalityValidationError("a causal claim must not supersede itself")
        self._validate_coherence()
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise CausalityValidationError(
                "causal claim fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if self.fingerprint != fingerprint_material(self.logical_values()):
            raise CausalityValidationError(
                "causal claim fingerprint does not match its canonical content"
            )

    def _validate_coherence(self) -> None:
        if self.kind is CausalClaimKind.CORRELATION:
            if self.strength is CausalClaimStrength.STRONG:
                raise CausalityValidationError(
                    "a correlation claim must not assert strong strength"
                )
        if self.kind is CausalClaimKind.CAUSATION:
            if not self.confounders_addressed:
                raise CausalityValidationError(
                    "a causation claim requires confounders to be addressed"
                )
        if self.strength is CausalClaimStrength.STRONG and not self.evidence_for:
            raise CausalityValidationError(
                "strong strength requires backing evidence"
            )
        if self.evidence_against or self.contradictions:
            if self.strength is CausalClaimStrength.STRONG:
                raise CausalityValidationError(
                    "strong strength is not admissible with against/contradiction evidence"
                )
        if self.status is CausalClaimStatus.CONFIRMED:
            if not self.evidence_for:
                raise CausalityValidationError(
                    "a confirmed claim requires backing evidence for"
                )
            if self.evidence_against or self.contradictions:
                raise CausalityValidationError(
                    "a confirmed claim must not carry against/contradiction evidence"
                )
        if self.status is CausalClaimStatus.REFUTED:
            if not self.contradictions and not self.evidence_against:
                raise CausalityValidationError(
                    "a refuted claim requires falsifying evidence"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.claim_id),
            self.kind.value,
            self.cause.logical_values(),
            self.effect.logical_values(),
            tuple(v.logical_values() for v in self.context),
            tuple(v.logical_values() for v in self.confounders),
            self.confounders_addressed,
            tuple(e.logical_values() for e in self.evidence_for),
            tuple(e.logical_values() for e in self.evidence_against),
            tuple(e.logical_values() for e in self.contradictions),
            tuple(e.logical_values() for e in self.limitations),
            self.strength.value,
            self.status.value,
            None if self.supersedes is None else str(self.supersedes),
        )


def build_causal_claim(
    *,
    claim_id: UUID,
    kind: CausalClaimKind,
    cause: CausalVariable,
    effect: CausalVariable,
    context: Sequence[CausalVariable] = (),
    confounders: Sequence[CausalVariable] = (),
    confounders_addressed: bool = False,
    evidence_for: Sequence[CausalEvidence] = (),
    evidence_against: Sequence[CausalEvidence] = (),
    contradictions: Sequence[CausalEvidence] = (),
    limitations: Sequence[CausalEvidence] = (),
    strength: CausalClaimStrength,
    status: CausalClaimStatus,
    supersedes: UUID | None = None,
) -> CausalClaim:
    """Build a validated, canonically ordered, fingerprinted causal claim."""
    if type(claim_id) is not UUID:
        raise CausalityValidationError("causal claim id must be a UUID")
    if not isinstance(context, Sequence):
        raise CausalityValidationError("context must be a sequence")
    if not isinstance(confounders, Sequence):
        raise CausalityValidationError("confounders must be a sequence")
    if not isinstance(evidence_for, Sequence):
        raise CausalityValidationError("evidence_for must be a sequence")
    if not isinstance(evidence_against, Sequence):
        raise CausalityValidationError("evidence_against must be a sequence")
    if not isinstance(contradictions, Sequence):
        raise CausalityValidationError("contradictions must be a sequence")
    if not isinstance(limitations, Sequence):
        raise CausalityValidationError("limitations must be a sequence")
    return CausalClaim(
        claim_id=claim_id,
        kind=kind,
        cause=cause,
        effect=effect,
        context=tuple(context),
        confounders=tuple(confounders),
        confounders_addressed=confounders_addressed,
        evidence_for=tuple(evidence_for),
        evidence_against=tuple(evidence_against),
        contradictions=tuple(contradictions),
        limitations=tuple(limitations),
        strength=strength,
        status=status,
        supersedes=supersedes,
        fingerprint=fingerprint_material(
            _claim_material(
                claim_id,
                kind,
                cause,
                effect,
                tuple(context),
                tuple(confounders),
                confounders_addressed,
                tuple(evidence_for),
                tuple(evidence_against),
                tuple(contradictions),
                tuple(limitations),
                strength,
                status,
                supersedes,
            )
        ),
    )


def _claim_material(
    claim_id: UUID,
    kind: CausalClaimKind,
    cause: CausalVariable,
    effect: CausalVariable,
    context: tuple[CausalVariable, ...],
    confounders: tuple[CausalVariable, ...],
    confounders_addressed: bool,
    evidence_for: tuple[CausalEvidence, ...],
    evidence_against: tuple[CausalEvidence, ...],
    contradictions: tuple[CausalEvidence, ...],
    limitations: tuple[CausalEvidence, ...],
    strength: CausalClaimStrength,
    status: CausalClaimStatus,
    supersedes: UUID | None,
) -> tuple[object, ...]:
    return (
        str(claim_id),
        kind.value,
        cause.logical_values(),
        effect.logical_values(),
        tuple(v.logical_values() for v in context),
        tuple(v.logical_values() for v in confounders),
        confounders_addressed,
        tuple(e.logical_values() for e in evidence_for),
        tuple(e.logical_values() for e in evidence_against),
        tuple(e.logical_values() for e in contradictions),
        tuple(e.logical_values() for e in limitations),
        strength.value,
        status.value,
        None if supersedes is None else str(supersedes),
    )


def assert_causal_lineage_acyclic(claims: Sequence[CausalClaim]) -> None:
    """Raise if the ``supersedes`` graph among the claims contains a cycle."""
    if not isinstance(claims, Sequence):
        raise CausalityValidationError("claims must be a sequence")
    by_id: dict[UUID, CausalClaim] = {}
    for claim in claims:
        if type(claim) is not CausalClaim:
            raise CausalityValidationError("claims must contain only CausalClaim values")
        claim.revalidate()
        if claim.claim_id in by_id:
            raise CausalityValidationError("claims must have unique ids")
        by_id[claim.claim_id] = claim

    visiting: set[UUID] = set()
    visited: set[UUID] = set()

    def visit(node: UUID) -> None:
        if node in visiting:
            raise CausalityValidationError("causal supersession lineage must be acyclic")
        if node in visited:
            return
        visiting.add(node)
        supersedes = by_id[node].supersedes
        if supersedes is not None and supersedes in by_id:
            visit(supersedes)
        visiting.remove(node)
        visited.add(node)

    for claim_id in by_id:
        visit(claim_id)


__all__ = [
    "CausalClaim",
    "CausalClaimKind",
    "CausalClaimStatus",
    "CausalClaimStrength",
    "CausalEvidence",
    "CausalEvidencePolarity",
    "CausalVariable",
    "CausalityError",
    "CausalityValidationError",
    "assert_causal_lineage_acyclic",
    "build_causal_claim",
]
