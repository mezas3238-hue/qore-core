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
    values: tuple[CausalEvidence, ...],
    *,
    field: str,
    polarity: CausalEvidencePolarity | None = None,
) -> tuple[CausalEvidence, ...]:
    if type(values) is not tuple or any(type(v) is not CausalEvidence for v in values):
        raise CausalityValidationError(
            f"{field} must be an immutable tuple of CausalEvidence"
        )
    for item in values:
        item.revalidate()
        if polarity is not None and item.polarity is not polarity:
            raise CausalityValidationError(
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
            raise CausalityValidationError(f"{field} must not contain duplicate evidence")
        seen.add(key)
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
class ConfounderResolution:
    """Evidence-bound resolution of one confounder for a CAUSATION claim.

    ``CORRELATION != CAUSATION``: a causation claim must explain the mechanism
    and resolve each declared confounder with explicit evidence, never a bare
    caller-supplied boolean. This binding pairs one confounder variable with the
    exact evidence observation that addresses it.
    """

    confounder: CausalVariable
    evidence: CausalEvidence

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.confounder) is not CausalVariable:
            raise CausalityValidationError(
                "confounder resolution confounder must be a CausalVariable"
            )
        self.confounder.revalidate()
        if type(self.evidence) is not CausalEvidence:
            raise CausalityValidationError(
                "confounder resolution evidence must be a CausalEvidence"
            )
        self.evidence.revalidate()
        if self.evidence.polarity is not CausalEvidencePolarity.SUPPORTS:
            # CORRELATION != CAUSATION: evidence used to justify a causal
            # attribution must be positively supporting. AGAINST/CONTRADICTION/
            # LIMITATION evidence cannot count as confounder resolution; a
            # caller cannot relabel a contradictory observation into a
            # supporting resolution.
            raise CausalityValidationError(
                "confounder resolution evidence must carry SUPPORTS polarity"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.confounder.logical_values(), self.evidence.logical_values())

    def sort_key(self) -> tuple[object, ...]:
        return (self.confounder.code, self.confounder.fingerprint.value,
                self.evidence.sort_key())


@dataclass(frozen=True, slots=True)
class MechanismBinding:
    """Evidence-bound mechanism for a CAUSATION claim.

    ``CORRELATION != CAUSATION``: a caller-supplied mechanism label is not an
    authority root. A causation claim must explain the mechanism through a typed
    evidence observation (reference + fingerprint identity), never a bare label
    such as ``mechanism_code="x"``. This binding pairs the mechanism's canonical
    code with the exact evidence observation that demonstrates the mechanism
    actually operates.
    """

    code: str
    evidence: CausalEvidence

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        object.__setattr__(
            self, "code", _validate_code(self.code, field="causal mechanism")
        )
        if type(self.evidence) is not CausalEvidence:
            raise CausalityValidationError(
                "mechanism binding evidence must be a CausalEvidence"
            )
        self.evidence.revalidate()
        if self.evidence.polarity is not CausalEvidencePolarity.SUPPORTS:
            # CORRELATION != CAUSATION: evidence used to establish the mechanism
            # must be positively supporting. AGAINST/CONTRADICTION/LIMITATION
            # evidence cannot establish a mechanism; a caller cannot relabel a
            # contradictory observation into a mechanism authority.
            raise CausalityValidationError(
                "mechanism binding evidence must carry SUPPORTS polarity"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.code, self.evidence.logical_values())

    def sort_key(self) -> tuple[object, ...]:
        return (self.code, self.evidence.sort_key())


def _canonical_confounder_resolutions(
    values: tuple[ConfounderResolution, ...], *, field: str
) -> tuple[ConfounderResolution, ...]:
    """Canonicalize confounder resolutions: exact types, revalidation, dedup by
    confounder code (a confounder is resolved once, not twice)."""
    if type(values) is not tuple or any(
        type(item) is not ConfounderResolution for item in values
    ):
        raise CausalityValidationError(
            f"{field} must be an immutable tuple of ConfounderResolution"
        )
    for resolution in values:
        resolution.revalidate()
    seen: set[str] = set()
    for resolution in values:
        if resolution.confounder.code in seen:
            raise CausalityValidationError(
                f"{field} must not contain duplicate confounder resolutions"
            )
        seen.add(resolution.confounder.code)
    return tuple(sorted(values, key=lambda item: item.sort_key()))


@dataclass(frozen=True, slots=True)
class CausalClaim:
    """One typed causal hypothesis/claim with evidence-bounded strength."""

    claim_id: UUID
    kind: CausalClaimKind
    cause: CausalVariable
    effect: CausalVariable
    context: tuple[CausalVariable, ...]
    confounders: tuple[CausalVariable, ...]
    mechanism: MechanismBinding | None
    confounder_resolutions: tuple[ConfounderResolution, ...]
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
        if self.mechanism is not None:
            if type(self.mechanism) is not MechanismBinding:
                raise CausalityValidationError(
                    "causal mechanism must be a MechanismBinding or None"
                )
            self.mechanism.revalidate()
        object.__setattr__(
            self,
            "confounder_resolutions",
            _canonical_confounder_resolutions(
                self.confounder_resolutions,
                field="causal confounder resolutions",
            ),
        )
        object.__setattr__(
            self,
            "evidence_for",
            _canonical_evidence(
                self.evidence_for,
                field="causal evidence for",
                polarity=CausalEvidencePolarity.SUPPORTS,
            ),
        )
        object.__setattr__(
            self,
            "evidence_against",
            _canonical_evidence(
                self.evidence_against,
                field="causal evidence against",
                polarity=CausalEvidencePolarity.AGAINST,
            ),
        )
        object.__setattr__(
            self,
            "contradictions",
            _canonical_evidence(
                self.contradictions,
                field="causal contradictions",
                polarity=CausalEvidencePolarity.CONTRADICTION,
            ),
        )
        object.__setattr__(
            self,
            "limitations",
            _canonical_evidence(
                self.limitations,
                field="causal limitations",
                polarity=CausalEvidencePolarity.LIMITATION,
            ),
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
            # CORRELATION != CAUSATION: a causation claim requires a typed,
            # evidence-bound mechanism (reference + fingerprint identity) and an
            # evidence-bound resolution for EVERY declared confounder — never a
            # bare caller-supplied label or boolean.
            if self.mechanism is None:
                raise CausalityValidationError(
                    "a causation claim requires an evidence-bound mechanism"
                )
            confounder_codes = {variable.code for variable in self.confounders}
            resolution_codes = {
                resolution.confounder.code for resolution in self.confounder_resolutions
            }
            if resolution_codes != confounder_codes:
                raise CausalityValidationError(
                    "a causation claim must resolve every declared confounder with "
                    "explicit evidence"
                )
            # R6 F3 closure: confounder-resolution evidence must be provenance-
            # retained by exact canonical identity (reference + polarity + UTC
            # instant) in the claim's governed evidence material. This keeps a
            # confirmed causal claim from semantically depending on contradictory
            # or unretained material sitting outside the claim-evidence
            # accounting boundary.
            evidence_for_identity = {
                evidence.logical_values() for evidence in self.evidence_for
            }
            for resolution in self.confounder_resolutions:
                if resolution.evidence.logical_values() not in evidence_for_identity:
                    raise CausalityValidationError(
                        "confounder resolution evidence must be retained in the "
                        "claim's evidence_for"
                    )
            # R7 F3 closure: the mechanism evidence must be provenance-retained
            # in the claim's evidence_for by exact canonical identity, and must
            # be distinct from every confounder-resolution evidence observation —
            # one observation cannot be laundered into the entire causal
            # authority (mechanism + confounder control).
            if self.mechanism.evidence.logical_values() not in evidence_for_identity:
                raise CausalityValidationError(
                    "mechanism binding evidence must be retained in the claim's "
                    "evidence_for"
                )
            resolution_evidence = {
                resolution.evidence.logical_values()
                for resolution in self.confounder_resolutions
            }
            if self.mechanism.evidence.logical_values() in resolution_evidence:
                raise CausalityValidationError(
                    "mechanism binding evidence must be distinct from confounder "
                    "resolution evidence"
                )
        else:
            if self.mechanism is not None:
                raise CausalityValidationError(
                    "a mechanism binding is only admissible on a causation claim"
                )
            if self.confounder_resolutions:
                raise CausalityValidationError(
                    "confounder resolutions are only admissible on a causation claim"
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
            None if self.mechanism is None else self.mechanism.logical_values(),
            tuple(r.logical_values() for r in self.confounder_resolutions),
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
    mechanism: MechanismBinding | None = None,
    confounder_resolutions: Sequence[ConfounderResolution] = (),
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
    if not isinstance(confounder_resolutions, Sequence):
        raise CausalityValidationError("confounder_resolutions must be a sequence")
    if not isinstance(evidence_for, Sequence):
        raise CausalityValidationError("evidence_for must be a sequence")
    if not isinstance(evidence_against, Sequence):
        raise CausalityValidationError("evidence_against must be a sequence")
    if not isinstance(contradictions, Sequence):
        raise CausalityValidationError("contradictions must be a sequence")
    if not isinstance(limitations, Sequence):
        raise CausalityValidationError("limitations must be a sequence")
    # Canonicalize every semantically-unordered sequence BEFORE deriving the
    # fingerprint, so any permutation of the same semantic input produces the
    # same canonical state and fingerprint (constructor == revalidate).
    canonical_context = _canonical_variables(tuple(context), field="causal context")
    canonical_confounders = _canonical_variables(tuple(confounders), field="causal confounders")
    if mechanism is not None:
        if type(mechanism) is not MechanismBinding:
            raise CausalityValidationError(
                "causal mechanism must be a MechanismBinding or None"
            )
        mechanism.revalidate()
    canonical_mechanism = mechanism
    canonical_resolutions = _canonical_confounder_resolutions(
        tuple(confounder_resolutions), field="causal confounder resolutions"
    )
    canonical_for = _canonical_evidence(
        tuple(evidence_for),
        field="causal evidence for",
        polarity=CausalEvidencePolarity.SUPPORTS,
    )
    canonical_against = _canonical_evidence(
        tuple(evidence_against),
        field="causal evidence against",
        polarity=CausalEvidencePolarity.AGAINST,
    )
    canonical_contradictions = _canonical_evidence(
        tuple(contradictions),
        field="causal contradictions",
        polarity=CausalEvidencePolarity.CONTRADICTION,
    )
    canonical_limitations = _canonical_evidence(
        tuple(limitations),
        field="causal limitations",
        polarity=CausalEvidencePolarity.LIMITATION,
    )
    return CausalClaim(
        claim_id=claim_id,
        kind=kind,
        cause=cause,
        effect=effect,
        context=canonical_context,
        confounders=canonical_confounders,
        mechanism=canonical_mechanism,
        confounder_resolutions=canonical_resolutions,
        evidence_for=canonical_for,
        evidence_against=canonical_against,
        contradictions=canonical_contradictions,
        limitations=canonical_limitations,
        strength=strength,
        status=status,
        supersedes=supersedes,
        fingerprint=fingerprint_material(
            _claim_material(
                claim_id,
                kind,
                cause,
                effect,
                canonical_context,
                canonical_confounders,
                canonical_mechanism,
                canonical_resolutions,
                canonical_for,
                canonical_against,
                canonical_contradictions,
                canonical_limitations,
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
    mechanism: MechanismBinding | None,
    confounder_resolutions: tuple[ConfounderResolution, ...],
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
        None if mechanism is None else mechanism.logical_values(),
        tuple(r.logical_values() for r in confounder_resolutions),
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
    "ConfounderResolution",
    "CausalityError",
    "CausalityValidationError",
    "MechanismBinding",
    "assert_causal_lineage_acyclic",
    "build_causal_claim",
]
