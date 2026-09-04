"""CIBO Cognitive strong metacognition substrate (CA strengthening 3.3).

CIBO evaluates whether it is using the correct reasoning process for the
problem — not merely whether the final answer looks plausible. A
metacognitive audit introspects the current reasoning mode and evidence
sufficiency at an engineering-evidence level (never exposing private
chain-of-thought), identifies missing specialist perspectives/evidence/critic
activity, and derives a bounded reasoning transition among FAST / HIGH / MAX /
COUNCIL_ADVERSARIAL under deterministic policy inputs.

Laws honoured: self-confidence is never evidence; escalation is bounded and
evidence-gated (no recursive infinite escalation); MAX is never authority;
council invocation never manufactures consensus; meta-evaluation never
self-certifies authority; auditable reason codes only (never private
chain-of-thought); exact runtime types; deterministic ordering + fingerprints;
no ambient time/RNG/network; no global mutable state.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from re import compile
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    contains_secret_material,
    fingerprint_material,
    require_exact_str,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboDeliberationRole,
    CiboReasoningMode,
)

_CODE_RE = r"[a-z][a-z0-9._-]*"

_MODE_RANK = {
    CiboReasoningMode.FAST: 0,
    CiboReasoningMode.HIGH: 1,
    CiboReasoningMode.MAX: 2,
    CiboReasoningMode.COUNCIL_ADVERSARIAL: 3,
}


class MetacognitionError(CiboCognitiveError):
    """Base error for the CIBO cognitive metacognition substrate."""

    __slots__ = ()


class MetacognitionValidationError(MetacognitionError, CiboCognitiveValidationError):
    """A metacognitive audit violates a deterministic self-monitoring invariant."""

    __slots__ = ()


class MetacognitiveFinding(StrEnum):
    """Engineering-evidence self-assessment findings (never chain-of-thought)."""

    SUFFICIENT = "sufficient"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    MISSING_SPECIALIST = "missing-specialist"
    MISSING_EVIDENCE = "missing-evidence"
    MISSING_CRITIC = "missing-critic"
    UNNECESSARY_ESCALATION = "unnecessary-escalation"
    UNRESOLVED_CONTRADICTION = "unresolved-contradiction"
    CALIBRATION_MISMATCH = "calibration-mismatch"


def _validate_code(value: object, *, field: str) -> str:
    text = require_exact_str(value, field=field)
    if compile(_CODE_RE).fullmatch(text) is None:
        raise MetacognitionValidationError(
            f"{field} must use canonical lowercase code syntax"
        )
    if contains_secret_material(text):
        raise MetacognitionValidationError(
            f"{field} must not carry secret-bearing material"
        )
    return text


def _canonical_codes(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(v) is not str for v in values):
        raise MetacognitionValidationError(
            f"{field} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(v, field=field) for v in values)
    if len(set(normalized)) != len(normalized):
        raise MetacognitionValidationError(f"{field} must not contain duplicates")
    return tuple(sorted(normalized))


def _canonical_roles(
    values: tuple[CiboDeliberationRole, ...], *, field: str
) -> tuple[CiboDeliberationRole, ...]:
    if type(values) is not tuple or any(type(v) is not CiboDeliberationRole for v in values):
        raise MetacognitionValidationError(
            f"{field} must be an immutable tuple of CiboDeliberationRole"
        )
    for role in values:
        role.revalidate()
    if len({r.value for r in values}) != len(values):
        raise MetacognitionValidationError(f"{field} must not contain duplicates")
    return tuple(sorted(values, key=lambda r: r.value))


def _canonical_evidence_refs(
    values: tuple[CiboCognitiveEvidenceRef, ...], *, field: str
) -> tuple[CiboCognitiveEvidenceRef, ...]:
    if type(values) is not tuple or any(
        type(v) is not CiboCognitiveEvidenceRef for v in values
    ):
        raise MetacognitionValidationError(
            f"{field} must be an immutable tuple of CiboCognitiveEvidenceRef"
        )
    for ref in values:
        ref.revalidate()
    if len({r.value for r in values}) != len(values):
        raise MetacognitionValidationError(f"{field} must not contain duplicates")
    return tuple(sorted(values, key=lambda r: r.value))


@dataclass(frozen=True, slots=True)
class ReasoningTransition:
    """One bounded, evidence-gated reasoning-mode transition."""

    from_mode: CiboReasoningMode
    to_mode: CiboReasoningMode
    reason_code: str
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.from_mode) is not CiboReasoningMode:
            raise MetacognitionValidationError(
                "transition from_mode must be a CiboReasoningMode"
            )
        if type(self.to_mode) is not CiboReasoningMode:
            raise MetacognitionValidationError(
                "transition to_mode must be a CiboReasoningMode"
            )
        if self.from_mode is self.to_mode:
            raise MetacognitionValidationError(
                "a reasoning transition must change mode (no self-loop escalation)"
            )
        object.__setattr__(
            self, "reason_code", _validate_code(self.reason_code, field="reason code")
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _canonical_evidence_refs(self.evidence_refs, field="transition evidence"),
        )
        if _MODE_RANK[self.to_mode] > _MODE_RANK[self.from_mode]:
            # Escalation must be justified by explicit evidence.
            if not self.evidence_refs:
                raise MetacognitionValidationError(
                    "reasoning escalation requires explicit backing evidence"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.from_mode.value,
            self.to_mode.value,
            self.reason_code,
            tuple(ref.value for ref in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class MetacognitiveAudit:
    """One engineering-evidence self-assessment (never self-certifying)."""

    audit_id: UUID
    reasoning_mode: CiboReasoningMode
    evidence_sufficiency: MetacognitiveFinding
    missing_roles: tuple[CiboDeliberationRole, ...]
    reason_codes: tuple[str, ...]
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.audit_id) is not UUID:
            raise MetacognitionValidationError("audit id must be a UUID")
        if type(self.reasoning_mode) is not CiboReasoningMode:
            raise MetacognitionValidationError(
                "audit reasoning mode must be a CiboReasoningMode"
            )
        if type(self.evidence_sufficiency) is not MetacognitiveFinding:
            raise MetacognitionValidationError(
                "audit evidence sufficiency must be a MetacognitiveFinding"
            )
        object.__setattr__(
            self,
            "missing_roles",
            _canonical_roles(self.missing_roles, field="audit missing roles"),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _canonical_codes(self.reason_codes, field="audit reason codes"),
        )
        if self.evidence_sufficiency is MetacognitiveFinding.SUFFICIENT:
            if self.missing_roles:
                raise MetacognitionValidationError(
                    "a sufficient finding must not suppress missing specialists"
                )
            if not self.reason_codes:
                raise MetacognitionValidationError(
                    "a sufficient finding requires auditable reason codes"
                )
        if self.evidence_sufficiency is MetacognitiveFinding.INSUFFICIENT_EVIDENCE:
            if not self.reason_codes:
                raise MetacognitionValidationError(
                    "an insufficient-evidence finding requires auditable reason codes"
                )
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise MetacognitionValidationError(
                "audit fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if self.fingerprint != fingerprint_material(self.logical_values()):
            raise MetacognitionValidationError(
                "audit fingerprint does not match its canonical content"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.audit_id),
            self.reasoning_mode.value,
            self.evidence_sufficiency.value,
            tuple(role.value for role in self.missing_roles),
            self.reason_codes,
        )


def build_reasoning_transition(
    *,
    from_mode: CiboReasoningMode,
    to_mode: CiboReasoningMode,
    reason_code: str,
    evidence_refs: Sequence[CiboCognitiveEvidenceRef] = (),
) -> ReasoningTransition:
    """Build a validated, evidence-gated reasoning-mode transition."""
    if not isinstance(evidence_refs, Sequence):
        raise MetacognitionValidationError("evidence refs must be a sequence")
    return ReasoningTransition(
        from_mode=from_mode,
        to_mode=to_mode,
        reason_code=reason_code,
        evidence_refs=tuple(evidence_refs),
    )


def build_metacognitive_audit(
    *,
    audit_id: UUID,
    reasoning_mode: CiboReasoningMode,
    evidence_sufficiency: MetacognitiveFinding,
    missing_roles: Sequence[CiboDeliberationRole] = (),
    reason_codes: Sequence[str] = (),
) -> MetacognitiveAudit:
    """Build a validated, deterministic metacognitive audit."""
    if not isinstance(missing_roles, Sequence):
        raise MetacognitionValidationError("missing roles must be a sequence")
    if not isinstance(reason_codes, Sequence):
        raise MetacognitionValidationError("reason codes must be a sequence")
    # Canonicalize every semantically-unordered sequence BEFORE deriving the
    # fingerprint, so any permutation of the same semantic input produces the
    # same canonical state and fingerprint (constructor == revalidate).
    canonical_roles = _canonical_roles(tuple(missing_roles), field="audit missing roles")
    canonical_codes = _canonical_codes(tuple(reason_codes), field="audit reason codes")
    return MetacognitiveAudit(
        audit_id=audit_id,
        reasoning_mode=reasoning_mode,
        evidence_sufficiency=evidence_sufficiency,
        missing_roles=canonical_roles,
        reason_codes=canonical_codes,
        fingerprint=fingerprint_material(
            (
                str(audit_id),
                reasoning_mode.value,
                evidence_sufficiency.value,
                tuple(role.value for role in canonical_roles),
                canonical_codes,
            )
        ),
    )


__all__ = [
    "MetacognitionError",
    "MetacognitionValidationError",
    "MetacognitiveAudit",
    "MetacognitiveFinding",
    "ReasoningTransition",
    "build_metacognitive_audit",
    "build_reasoning_transition",
]
