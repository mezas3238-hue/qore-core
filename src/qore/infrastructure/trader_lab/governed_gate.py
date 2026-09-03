"""EXTERNAL_ISSUED_EVIDENCE seam for Risk/CIBO/independent-validation gates.

The Trader Lab never manufactures a Risk, CIBO, or independent-validation
decision. These gates are governed by external authorities that do not yet expose
an in-repo content-digest evidence producer. The Lab therefore carries a
provider-neutral CONSUME/VERIFY-ONLY seam:

- ``TraderLabGovernedGateEvidence`` is a typed record of externally produced
  material (authority identity and exact authority kind, decision, timestamp,
  provenance digest). It is a carrier only: a locally constructed APPROVED record
  is NOT authentic governed evidence and cannot qualify any stage by itself.
- ``TraderLabGovernedAuthenticityProof`` is a sealed authenticity proof issued by
  an owning authority OUTSIDE the Lab. Its ``_issued`` marker is ``init=False``
  and the Lab ships NO function that can set it, so no Trader Lab public or
  private surface can synthesize a proof.
- ``verify_governed_gate_evidence`` is the ONLY path that can turn an APPROVED
  record into a qualifying stage reference, and it consumes an ALREADY-ISSUED
  proof rather than manufacturing an authority decision. With no proof (the
  production baseline) the gate is ``EXTERNAL_EVIDENCE_DEPENDENT`` and fails
  closed.

The authority root is therefore the external authority's issuance capability,
which is deliberately absent from this module: there is no authenticator
Protocol to duck-type past, and no private mint helper to call. A proof can only
be constructed by code outside the Lab that deliberately sets the sealed
``_issued`` marker (an external authority, or a trusted test double in the test
suite). Risk/CIBO/independent-validation ownership stays outside the Lab; no
concrete provider, credential, network client, or operational authority is
imported here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabError,
    TraderLabValidationError,
    _validate_sha256,
    _validate_token,
    compute_trader_lab_candidate_fingerprint,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    _canonical_bytes,
    _make_external_authenticated_reference,
)
from qore.kernel.result import Failure, Result, Success


class TraderLabGovernedGate(StrEnum):
    """The three distinct external review gates the Lab may carry."""

    RISK_REVIEW = "risk_review"
    CIBO_REVIEW = "cibo_review"
    INDEPENDENT_VALIDATION = "independent_validation"


class TraderLabGovernedAuthorityKind(StrEnum):
    """Exact owning-authority kind; one distinct kind per governed gate.

    A governed evidence record and its authenticity proof must bind the exact
    authority kind that owns the gate. A Risk authority cannot issue a CIBO or
    independent-validation decision, and the Trader Lab itself is never one of
    these kinds.
    """

    RISK = "risk"
    CIBO = "cibo"
    INDEPENDENT_VALIDATION = "independent_validation"


class TraderLabGovernedDecision(StrEnum):
    """Closed governed-decision outcomes carried from the external authority."""

    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"
    DEFERRED = "deferred"


_GATE_KINDS: dict[TraderLabGovernedGate, TraderLabEvidenceKind] = {
    TraderLabGovernedGate.RISK_REVIEW: TraderLabEvidenceKind.RISK_REVIEW,
    TraderLabGovernedGate.CIBO_REVIEW: TraderLabEvidenceKind.CIBO_REVIEW,
    TraderLabGovernedGate.INDEPENDENT_VALIDATION: (
        TraderLabEvidenceKind.INDEPENDENT_VALIDATION
    ),
}

_GATE_AUTHORITY_KINDS: dict[
    TraderLabGovernedGate, TraderLabGovernedAuthorityKind
] = {
    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,
    TraderLabGovernedGate.CIBO_REVIEW: TraderLabGovernedAuthorityKind.CIBO,
    TraderLabGovernedGate.INDEPENDENT_VALIDATION: (
        TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION
    ),
}


def _require_gate_authority_kind(
    gate: TraderLabGovernedGate,
    authority_kind: TraderLabGovernedAuthorityKind,
) -> None:
    """Fail closed unless the authority kind exactly owns the given gate.

    Exact runtime type is enforced before any value comparison so a reflectively
    injected raw string or a StrEnum subclass member cannot launder past the
    membership check.
    """

    if type(gate) is not TraderLabGovernedGate:
        raise TraderLabValidationError("gate must be TraderLabGovernedGate")
    if type(authority_kind) is not TraderLabGovernedAuthorityKind:
        raise TraderLabValidationError(
            "authority_kind must be TraderLabGovernedAuthorityKind"
        )
    expected = _GATE_AUTHORITY_KINDS[gate]
    if authority_kind is not expected:
        raise TraderLabValidationError(
            f"authority kind {authority_kind.value} does not govern gate "
            f"{gate.value}"
        )


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TraderLabValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderLabValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class TraderLabGovernedGateEvidenceId:
    """Immutable identity of one governed review evidence record."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TraderLabValidationError("governed gate evidence id must be a UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TraderLabGovernedGateFingerprint:
    """Canonical SHA-256 digest of the governed review evidence record."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="governed gate fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_trader_lab_governed_gate_fingerprint(
    *,
    evidence_id: TraderLabGovernedGateEvidenceId,
    gate: TraderLabGovernedGate,
    authority_kind: TraderLabGovernedAuthorityKind,
    candidate: TraderLabCandidateBinding,
    authority_id: UUID,
    authority_name: str,
    decision: TraderLabGovernedDecision,
    decided_at: datetime,
    authority_evidence_digest: TraderLabEvidenceDigest,
) -> TraderLabGovernedGateFingerprint:
    """Hash the exact governed review identity, authority kind, and provenance."""

    if not isinstance(evidence_id, TraderLabGovernedGateEvidenceId):
        raise TraderLabValidationError(
            "evidence_id must be TraderLabGovernedGateEvidenceId"
        )
    _require_gate_authority_kind(gate, authority_kind)
    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    if not isinstance(authority_id, UUID):
        raise TraderLabValidationError("authority_id must be a UUID")
    _validate_token(authority_name, field_name="governed authority name")
    if type(decision) is not TraderLabGovernedDecision:
        raise TraderLabValidationError("decision must be TraderLabGovernedDecision")
    _validate_timestamp(decided_at, field_name="governed decided_at")
    if not isinstance(authority_evidence_digest, TraderLabEvidenceDigest):
        raise TraderLabValidationError(
            "authority_evidence_digest must be TraderLabEvidenceDigest"
        )
    _validate_sha256(
        authority_evidence_digest.value,
        field_name="authority evidence digest",
    )
    canonical = {
        "schema": "qore.trader_lab.governed_gate.v1",
        "evidence_id": str(evidence_id.value),
        "gate": gate.value,
        "authority_kind": authority_kind.value,
        "candidate_fingerprint": candidate.fingerprint.value,
        "authority_id": str(authority_id),
        "authority_name": authority_name,
        "decision": decision.value,
        "decided_at": decided_at.astimezone(UTC).isoformat(timespec="microseconds"),
        "authority_evidence_digest": authority_evidence_digest.value,
    }
    return TraderLabGovernedGateFingerprint(sha256(_canonical_bytes(canonical)).hexdigest())


@dataclass(frozen=True, slots=True)
class TraderLabGovernedGateEvidence:
    """Typed record of externally produced governed review material (carrier only).

    Produced by the external authority, not by the Trader Lab. Constructing this
    record locally yields a structurally typed APPROVED object, which is NOT
    authentic governed evidence and cannot qualify a stage by itself. Only
    ``verify_governed_gate_evidence`` (through an already-issued external
    authenticity proof) can turn it into a qualifying reference.
    """

    evidence_id: TraderLabGovernedGateEvidenceId
    gate: TraderLabGovernedGate
    authority_kind: TraderLabGovernedAuthorityKind
    candidate: TraderLabCandidateBinding
    authority_id: UUID
    authority_name: str
    decision: TraderLabGovernedDecision
    decided_at: datetime
    authority_evidence_digest: TraderLabEvidenceDigest
    fingerprint: TraderLabGovernedGateFingerprint

    def __post_init__(self) -> None:
        validate_trader_lab_governed_gate_evidence(self)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.gate.value,
            self.authority_kind.value,
            self.candidate.fingerprint.logical_values(),
            str(self.authority_id),
            self.authority_name,
            self.decision.value,
            self.decided_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.authority_evidence_digest.logical_values(),
            self.fingerprint.logical_values(),
        )


def validate_trader_lab_governed_gate_evidence(
    evidence: TraderLabGovernedGateEvidence,
) -> None:
    """Re-validate a governed review evidence record at a trust boundary."""

    if type(evidence) is not TraderLabGovernedGateEvidence:
        raise TraderLabValidationError(
            "evidence must be TraderLabGovernedGateEvidence"
        )
    if not isinstance(evidence.evidence_id, TraderLabGovernedGateEvidenceId):
        raise TraderLabValidationError(
            "evidence_id must be TraderLabGovernedGateEvidenceId"
        )
    _require_gate_authority_kind(evidence.gate, evidence.authority_kind)
    if not isinstance(evidence.candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    expected_candidate = compute_trader_lab_candidate_fingerprint(
        candidate_id=evidence.candidate.candidate_id,
        version=evidence.candidate.version,
        strategy_binding=evidence.candidate.strategy_binding,
    )
    if evidence.candidate.fingerprint != expected_candidate:
        raise TraderLabValidationError(
            "candidate fingerprint must match the recomputed exact binding"
        )
    if not isinstance(evidence.authority_id, UUID):
        raise TraderLabValidationError("authority_id must be a UUID")
    _validate_token(evidence.authority_name, field_name="governed authority name")
    if type(evidence.decision) is not TraderLabGovernedDecision:
        raise TraderLabValidationError("decision must be TraderLabGovernedDecision")
    _validate_timestamp(evidence.decided_at, field_name="governed decided_at")
    if not isinstance(evidence.authority_evidence_digest, TraderLabEvidenceDigest):
        raise TraderLabValidationError(
            "authority_evidence_digest must be TraderLabEvidenceDigest"
        )
    _validate_sha256(
        evidence.authority_evidence_digest.value,
        field_name="authority evidence digest",
    )
    if not isinstance(evidence.fingerprint, TraderLabGovernedGateFingerprint):
        raise TraderLabValidationError(
            "fingerprint must be TraderLabGovernedGateFingerprint"
        )
    expected = compute_trader_lab_governed_gate_fingerprint(
        evidence_id=evidence.evidence_id,
        gate=evidence.gate,
        authority_kind=evidence.authority_kind,
        candidate=evidence.candidate,
        authority_id=evidence.authority_id,
        authority_name=evidence.authority_name,
        decision=evidence.decision,
        decided_at=evidence.decided_at,
        authority_evidence_digest=evidence.authority_evidence_digest,
    )
    if evidence.fingerprint != expected:
        raise TraderLabValidationError(
            "governed gate fingerprint must match the exact evidence"
        )


class TraderLabExternalEvidenceDependencyError(TraderLabError):
    """External governed evidence required but no external authority proof is present."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class TraderLabGovernedAuthenticityProof:
    """Sealed authenticity proof issued by an owning authority OUTSIDE the Lab.

    ``_issued`` is ``init=False`` and no function in this module can set it, so no
    public or private Trader Lab value constructor can synthesize a proof. The
    proof binds the exact evidence fingerprint, candidate, gate, authority kind,
    issuer, and time, and carries its own deterministic fingerprint.
    """

    evidence_fingerprint: TraderLabGovernedGateFingerprint
    candidate: TraderLabCandidateBinding
    gate: TraderLabGovernedGate
    authority_kind: TraderLabGovernedAuthorityKind
    issuer_id: UUID
    issued_at: datetime
    proof_fingerprint: TraderLabGovernedGateFingerprint
    _issued: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self._issued is not True:
            raise TraderLabValidationError(
                "authenticity proof must be issued by an owning authority outside "
                "the Trader Lab"
            )
        _validate_governed_authenticity_proof(self)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_fingerprint.logical_values(),
            self.candidate.fingerprint.logical_values(),
            self.gate.value,
            self.authority_kind.value,
            str(self.issuer_id),
            self.issued_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.proof_fingerprint.logical_values(),
        )


def compute_trader_lab_governed_authenticity_proof_fingerprint(
    *,
    evidence_fingerprint: TraderLabGovernedGateFingerprint,
    candidate: TraderLabCandidateBinding,
    gate: TraderLabGovernedGate,
    authority_kind: TraderLabGovernedAuthorityKind,
    issuer_id: UUID,
    issued_at: datetime,
) -> TraderLabGovernedGateFingerprint:
    """Hash the exact authenticity-proof identity issued for one evidence record."""

    if not isinstance(evidence_fingerprint, TraderLabGovernedGateFingerprint):
        raise TraderLabValidationError(
            "evidence_fingerprint must be TraderLabGovernedGateFingerprint"
        )
    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    _require_gate_authority_kind(gate, authority_kind)
    if not isinstance(issuer_id, UUID):
        raise TraderLabValidationError("issuer_id must be a UUID")
    _validate_timestamp(issued_at, field_name="authenticity issued_at")
    canonical = {
        "schema": "qore.trader_lab.governed_authenticity.v1",
        "evidence_fingerprint": evidence_fingerprint.value,
        "candidate_fingerprint": candidate.fingerprint.value,
        "gate": gate.value,
        "authority_kind": authority_kind.value,
        "issuer_id": str(issuer_id),
        "issued_at": issued_at.astimezone(UTC).isoformat(timespec="microseconds"),
    }
    return TraderLabGovernedGateFingerprint(sha256(_canonical_bytes(canonical)).hexdigest())


def _validate_governed_authenticity_proof(
    proof: TraderLabGovernedAuthenticityProof,
) -> None:
    """Re-validate a sealed authenticity proof at a trust boundary."""

    if type(proof) is not TraderLabGovernedAuthenticityProof:
        raise TraderLabValidationError(
            "proof must be TraderLabGovernedAuthenticityProof"
        )
    if proof._issued is not True:
        raise TraderLabValidationError(
            "authenticity proof must be issued by an owning authority outside "
            "the Trader Lab"
        )
    if not isinstance(proof.evidence_fingerprint, TraderLabGovernedGateFingerprint):
        raise TraderLabValidationError(
            "proof evidence_fingerprint must be TraderLabGovernedGateFingerprint"
        )
    if not isinstance(proof.candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("proof candidate must be TraderLabCandidateBinding")
    expected_candidate = compute_trader_lab_candidate_fingerprint(
        candidate_id=proof.candidate.candidate_id,
        version=proof.candidate.version,
        strategy_binding=proof.candidate.strategy_binding,
    )
    if proof.candidate.fingerprint != expected_candidate:
        raise TraderLabValidationError(
            "proof candidate fingerprint must match the recomputed exact binding"
        )
    _require_gate_authority_kind(proof.gate, proof.authority_kind)
    if not isinstance(proof.issuer_id, UUID):
        raise TraderLabValidationError("proof issuer_id must be a UUID")
    _validate_timestamp(proof.issued_at, field_name="authenticity issued_at")
    if not isinstance(proof.proof_fingerprint, TraderLabGovernedGateFingerprint):
        raise TraderLabValidationError(
            "proof_fingerprint must be TraderLabGovernedGateFingerprint"
        )
    expected = compute_trader_lab_governed_authenticity_proof_fingerprint(
        evidence_fingerprint=proof.evidence_fingerprint,
        candidate=proof.candidate,
        gate=proof.gate,
        authority_kind=proof.authority_kind,
        issuer_id=proof.issuer_id,
        issued_at=proof.issued_at,
    )
    if proof.proof_fingerprint != expected:
        raise TraderLabValidationError(
            "authenticity proof fingerprint must match the exact proof"
        )


def validate_trader_lab_governed_authenticity_proof(
    proof: TraderLabGovernedAuthenticityProof,
) -> None:
    """Public re-validation entry for a sealed authenticity proof."""

    _validate_governed_authenticity_proof(proof)


def verify_governed_gate_evidence(
    candidate: TraderLabCandidateBinding,
    evidence: TraderLabGovernedGateEvidence,
    proof: TraderLabGovernedAuthenticityProof | None,
) -> Result[TraderLabEvidenceReference, TraderLabError]:
    """Verify externally issued governed evidence through the consume-only seam.

    This is the ONLY path that turns an APPROVED governed record into a
    qualifying stage reference. It consumes an ALREADY-ISSUED external proof; the
    Lab itself issues no authenticity proof and mints no qualifying external
    decision. With no proof (the production baseline) it fails closed as
    ``EXTERNAL_EVIDENCE_DEPENDENT``.
    """

    try:
        if not isinstance(candidate, TraderLabCandidateBinding):
            raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
        validate_trader_lab_governed_gate_evidence(evidence)
        if evidence.candidate != candidate:
            raise TraderLabValidationError(
                "governed evidence must bind the exact candidate"
            )
        if evidence.decision is not TraderLabGovernedDecision.APPROVED:
            raise TraderLabValidationError(
                "only an approved governed review may qualify its stage"
            )
        if proof is None:
            raise TraderLabExternalEvidenceDependencyError(
                "Risk/CIBO/independent-validation evidence requires an "
                "externally issued authenticity proof; none is available "
                "(EXTERNAL_EVIDENCE_DEPENDENT)"
            )
        _validate_governed_authenticity_proof(proof)
        if proof.candidate != candidate:
            raise TraderLabValidationError(
                "authenticity proof must bind the exact candidate"
            )
        if proof.gate is not evidence.gate:
            raise TraderLabValidationError(
                "authenticity proof gate must match the evidence gate"
            )
        if proof.authority_kind is not evidence.authority_kind:
            raise TraderLabValidationError(
                "authenticity proof authority kind must match the evidence"
            )
        if proof.evidence_fingerprint != evidence.fingerprint:
            raise TraderLabValidationError(
                "authenticity proof must bind the exact evidence fingerprint"
            )
        if proof.issuer_id != evidence.authority_id:
            raise TraderLabValidationError(
                "authenticity proof issuer must be the exact deciding authority"
            )
        if proof.issued_at < evidence.decided_at:
            raise TraderLabValidationError(
                "authenticity proof cannot predate the governed decision"
            )
        return Success(
            _make_external_authenticated_reference(
                kind=_GATE_KINDS[evidence.gate],
                reference_id=evidence.evidence_id.value,
                content_digest=TraderLabEvidenceDigest(proof.proof_fingerprint.value),
                schema_version="trader_lab.governed-gate.v1",
                strategy_binding_fingerprint=(
                    candidate.strategy_binding.binding_fingerprint.value
                ),
                authenticity_proof_fingerprint=proof.proof_fingerprint.value,
            )
        )
    except TraderLabError as error:
        return Failure(error)
