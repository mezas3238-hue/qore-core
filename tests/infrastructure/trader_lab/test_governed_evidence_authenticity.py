"""Adversarial falsification matrix for governed evidence authenticity.

Each test proves one concrete falsification vector fails closed. The production
Trader Lab is consume/verify-only: it ships no function able to mint a qualifying
APPROVED Risk/CIBO/independent-validation decision from arbitrary caller-supplied
fields. A qualifying reference requires a sealed authenticity proof issued by an
owning authority OUTSIDE the Lab (absent on this baseline, so the gate is
``EXTERNAL_EVIDENCE_DEPENDENT``).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabValidationError,
)
from qore.infrastructure.trader_lab.governed_gate import (
    TraderLabExternalEvidenceDependencyError,
    TraderLabGovernedAuthenticityProof,
    TraderLabGovernedAuthorityKind,
    TraderLabGovernedDecision,
    TraderLabGovernedGate,
    TraderLabGovernedGateEvidence,
    TraderLabGovernedGateEvidenceId,
    TraderLabGovernedGateFingerprint,
    compute_trader_lab_governed_authenticity_proof_fingerprint,
    compute_trader_lab_governed_gate_fingerprint,
    validate_trader_lab_governed_authenticity_proof,
    validate_trader_lab_governed_gate_evidence,
    verify_governed_gate_evidence,
)
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
    validate_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.promotion import (
    TraderLabPromotionStatus,
    evaluate_demo_eligibility,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceId,
    build_trader_lab_stage_evidence,
    validate_trader_lab_evidence_reference,
)
from qore.kernel.result import Failure, Success

_PROCESS_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

_CandidateFactory = Callable[..., TraderLabCandidateBinding]
_EvidenceFactory = Callable[..., Any]
_GovernedRefFactory = Callable[..., TraderLabEvidenceReference]

_GATE_AUTHORITY_KIND: dict[
    TraderLabGovernedGate, TraderLabGovernedAuthorityKind
] = {
    TraderLabGovernedGate.STRESS_REVIEW: TraderLabGovernedAuthorityKind.ROBUSTNESS,
    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,
    TraderLabGovernedGate.CIBO_REVIEW: TraderLabGovernedAuthorityKind.CIBO,
    TraderLabGovernedGate.INDEPENDENT_VALIDATION: (
        TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION
    ),
}


def _uuid(suffix: int) -> UUID:
    return UUID(f"74000000-0000-0000-0000-{suffix:012d}")


def _mint_carrier(
    candidate: TraderLabCandidateBinding,
    *,
    gate: TraderLabGovernedGate,
    suffix: int,
    decision: TraderLabGovernedDecision = TraderLabGovernedDecision.APPROVED,
    decided_at: datetime = _PROCESS_TIME,
    authority_digest: str = "b" * 64,
    authority_kind: TraderLabGovernedAuthorityKind | None = None,
) -> TraderLabGovernedGateEvidence:
    """Locally construct a typed governed review record (carrier only).

    This mirrors what the removed public mint path accepted: arbitrary
    caller-supplied authority identity/digest plus an APPROVED decision. It is
    NOT authentic governed evidence and cannot qualify a stage by itself.
    """

    kind = authority_kind if authority_kind is not None else _GATE_AUTHORITY_KIND[gate]
    authority_id = _uuid(suffix + 100000)
    authority_name = f"{kind.value}-authority"
    fingerprint = compute_trader_lab_governed_gate_fingerprint(
        evidence_id=TraderLabGovernedGateEvidenceId(_uuid(suffix)),
        gate=gate,
        authority_kind=kind,
        candidate=candidate,
        authority_id=authority_id,
        authority_name=authority_name,
        decision=decision,
        decided_at=decided_at,
        authority_evidence_digest=TraderLabEvidenceDigest(authority_digest),
    )
    return TraderLabGovernedGateEvidence(
        evidence_id=TraderLabGovernedGateEvidenceId(_uuid(suffix)),
        gate=gate,
        authority_kind=kind,
        candidate=candidate,
        authority_id=authority_id,
        authority_name=authority_name,
        decision=decision,
        decided_at=decided_at,
        authority_evidence_digest=TraderLabEvidenceDigest(authority_digest),
        fingerprint=fingerprint,
    )


def _issue_proof(
    *,
    evidence: TraderLabGovernedGateEvidence,
    candidate: TraderLabCandidateBinding,
    issued_at: datetime | None = None,
    gate: TraderLabGovernedGate | None = None,
    authority_kind: TraderLabGovernedAuthorityKind | None = None,
    issuer_id: UUID | None = None,
    evidence_fingerprint: TraderLabGovernedGateFingerprint | None = None,
    issued: bool = True,
) -> TraderLabGovernedAuthenticityProof:
    """Issue a sealed authenticity proof as an EXTERNAL authority (test double).

    Defaults bind the proof to the evidence exactly (same authority, kind, gate,
    fingerprint, and an ``issued_at`` not before the decision). Adversarial tests
    override fields to forge mismatches; the override paths represent a caller
    deliberately acting as an authority, which the Lab must still fail closed on
    when the forged bindings do not line up.
    """

    proof_gate = gate if gate is not None else evidence.gate
    proof_kind = (
        authority_kind if authority_kind is not None else evidence.authority_kind
    )
    proof_issuer = issuer_id if issuer_id is not None else evidence.authority_id
    proof_issued_at = issued_at if issued_at is not None else evidence.decided_at
    proof_evidence_fingerprint = (
        evidence_fingerprint if evidence_fingerprint is not None else evidence.fingerprint
    )
    proof_fingerprint = compute_trader_lab_governed_authenticity_proof_fingerprint(
        evidence_fingerprint=proof_evidence_fingerprint,
        candidate=candidate,
        gate=proof_gate,
        authority_kind=proof_kind,
        issuer_id=proof_issuer,
        issued_at=proof_issued_at,
    )
    proof = object.__new__(TraderLabGovernedAuthenticityProof)
    object.__setattr__(proof, "evidence_fingerprint", proof_evidence_fingerprint)
    object.__setattr__(proof, "candidate", candidate)
    object.__setattr__(proof, "gate", proof_gate)
    object.__setattr__(proof, "authority_kind", proof_kind)
    object.__setattr__(proof, "issuer_id", proof_issuer)
    object.__setattr__(proof, "issued_at", proof_issued_at)
    object.__setattr__(proof, "proof_fingerprint", proof_fingerprint)
    object.__setattr__(proof, "_issued", issued)
    return proof


def _promote(
    lifecycle: TraderLabLifecycle,
    *,
    stage: TraderLabStage,
    candidate: TraderLabCandidateBinding,
    stage_evidence_factory: _EvidenceFactory,
    evidence_suffix: int,
    produced_at: datetime,
) -> TraderLabLifecycle:
    evidence = stage_evidence_factory(
        stage=stage,
        candidate=candidate,
        evidence_suffix=evidence_suffix,
        produced_at=produced_at,
    )
    built = apply_trader_lab_promotion(
        lifecycle,
        TraderLabPromotionRequest(stage=stage, evidence=evidence),
    )
    assert isinstance(built, Success), built
    return built.value


def _qualify_through(
    lifecycle: TraderLabLifecycle,
    candidate: TraderLabCandidateBinding,
    stage_evidence_factory: _EvidenceFactory,
    stages: tuple[TraderLabStage, ...],
    start_suffix: int = 100,
) -> TraderLabLifecycle:
    current = lifecycle
    for index, stage in enumerate(stages):
        current = _promote(
            current,
            stage=stage,
            candidate=candidate,
            stage_evidence_factory=stage_evidence_factory,
            evidence_suffix=start_suffix + index,
            produced_at=_PROCESS_TIME + timedelta(minutes=index),
        )
    return current


def test_case1_caller_supplied_fake_protocol_cannot_qualify(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=1
    )

    class _FakeProtocolApprover:
        """A caller-supplied fake 'verifier' object (duck-typed, returns APPROVED)."""

        def authenticate(self, candidate: object, evidence: object) -> object:
            return Success(TraderLabGovernedDecision.APPROVED)

    # There is no authenticator parameter left; a fake verifier object passed
    # where a proof is required is rejected by exact runtime type.
    fake_verifier: Any = _FakeProtocolApprover()
    built = verify_governed_gate_evidence(candidate, carrier, fake_verifier)
    assert isinstance(built, Failure)
    assert "proof must be TraderLabGovernedAuthenticityProof" in str(built.error)


def test_case2_duck_typed_dynamic_proxy_verifier_cannot_qualify(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=2
    )

    class _DynamicProxy:
        """A dynamic proxy whose attributes resolve on demand (never a real proof)."""

        def __getattr__(self, name: str) -> object:
            if name == "_issued":
                return True
            return None

    proxy: Any = _DynamicProxy()
    built = verify_governed_gate_evidence(candidate, carrier, proxy)
    assert isinstance(built, Failure)
    assert "proof must be TraderLabGovernedAuthenticityProof" in str(built.error)


def test_case3_subclass_laundering_rejected_at_boundaries(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=3
    )

    # A subclass of the frozen evidence record cannot construct a valid instance:
    # exact runtime type is enforced in __post_init__.
    @dataclass(frozen=True, slots=True)
    class _EvidenceSubclass(TraderLabGovernedGateEvidence):
        pass

    with pytest.raises(TraderLabValidationError):
        _EvidenceSubclass(
            evidence_id=carrier.evidence_id,
            gate=carrier.gate,
            authority_kind=carrier.authority_kind,
            candidate=carrier.candidate,
            authority_id=carrier.authority_id,
            authority_name=carrier.authority_name,
            decision=carrier.decision,
            decided_at=carrier.decided_at,
            authority_evidence_digest=carrier.authority_evidence_digest,
            fingerprint=carrier.fingerprint,
        )

    # A subclass of the proof forged via object.__new__ (with _issued set) is
    # still rejected at the trust boundary by exact runtime type.
    @dataclass(frozen=True, slots=True)
    class _ProofSubclass(TraderLabGovernedAuthenticityProof):
        pass

    valid_proof = _issue_proof(evidence=carrier, candidate=candidate)
    forged_subclass = object.__new__(_ProofSubclass)
    for field_name in (
        "evidence_fingerprint",
        "candidate",
        "gate",
        "authority_kind",
        "issuer_id",
        "issued_at",
        "proof_fingerprint",
    ):
        object.__setattr__(forged_subclass, field_name, getattr(valid_proof, field_name))
    object.__setattr__(forged_subclass, "_issued", True)
    forged_subclass_any: Any = forged_subclass
    built = verify_governed_gate_evidence(candidate, carrier, forged_subclass_any)
    assert isinstance(built, Failure)
    assert "proof must be TraderLabGovernedAuthenticityProof" in str(built.error)


def test_case4_locally_forged_receipt_cannot_qualify(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=4
    )

    # Direct constructor cannot synthesize a proof (sealed _issued).
    with pytest.raises(TraderLabValidationError):
        TraderLabGovernedAuthenticityProof(
            evidence_fingerprint=carrier.fingerprint,
            candidate=candidate,
            gate=carrier.gate,
            authority_kind=carrier.authority_kind,
            issuer_id=carrier.authority_id,
            issued_at=_PROCESS_TIME,
            proof_fingerprint=TraderLabGovernedGateFingerprint("e" * 64),
        )

    # A reflectively forged proof without _issued is rejected at validation.
    unissued = _issue_proof(evidence=carrier, candidate=candidate, issued=False)
    with pytest.raises(TraderLabValidationError):
        validate_trader_lab_governed_authenticity_proof(unissued)

    # The production module ships no private proof-mint helper.
    import qore.infrastructure.trader_lab.governed_gate as governed_gate_module

    assert not hasattr(governed_gate_module, "_issue_governed_authenticity_proof")
    assert not hasattr(governed_gate_module, "TraderLabGovernedEvidenceAuthenticator")
    assert not hasattr(governed_gate_module, "authenticate_governed_gate_evidence")


def test_case5_copied_authority_fields_without_issuance_cannot_qualify(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    # A carrier with a valid self-consistent fingerprint but NO authentic
    # external issuance fails closed.
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=5
    )
    built = verify_governed_gate_evidence(candidate, carrier, None)
    assert isinstance(built, Failure)
    assert isinstance(built.error, TraderLabExternalEvidenceDependencyError)
    assert "EXTERNAL_EVIDENCE_DEPENDENT" in str(built.error)

    # A proof issued by a DIFFERENT authority (copied id/name/digest but wrong
    # issuer) is rejected.
    forged = _issue_proof(
        evidence=carrier,
        candidate=candidate,
        issuer_id=_uuid(999),
    )
    built = verify_governed_gate_evidence(candidate, carrier, forged)
    assert isinstance(built, Failure)
    assert "issuer must be the exact deciding authority" in str(built.error)


def test_case6_issuer_authority_kind_mismatch_cannot_qualify(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    risk_carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=6
    )
    # A CIBO authority issues a proof for a RISK evidence record: gate mismatch
    # (and its authority kind) is rejected.
    forged = _issue_proof(
        evidence=risk_carrier,
        candidate=candidate,
        gate=TraderLabGovernedGate.CIBO_REVIEW,
        authority_kind=TraderLabGovernedAuthorityKind.CIBO,
    )
    built = verify_governed_gate_evidence(candidate, risk_carrier, forged)
    assert isinstance(built, Failure)
    assert "gate must match" in str(built.error)

    # An authority kind that does not own the gate is rejected at fingerprint
    # time (exact mapping).
    with pytest.raises(TraderLabValidationError):
        compute_trader_lab_governed_authenticity_proof_fingerprint(
            evidence_fingerprint=risk_carrier.fingerprint,
            candidate=candidate,
            gate=TraderLabGovernedGate.RISK_REVIEW,
            authority_kind=TraderLabGovernedAuthorityKind.CIBO,
            issuer_id=_uuid(600),
            issued_at=_PROCESS_TIME,
        )


def test_case7_trader_version_experiment_candidate_policy_mismatch(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate_a = candidate_factory(candidate_suffix=1)
    candidate_b = candidate_factory(candidate_suffix=2)
    carrier_for_a = _mint_carrier(
        candidate_a, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=7
    )
    proof_for_a = _issue_proof(evidence=carrier_for_a, candidate=candidate_a)

    # Evidence bound to candidate A cannot qualify candidate B.
    built = verify_governed_gate_evidence(candidate_b, carrier_for_a, proof_for_a)
    assert isinstance(built, Failure)
    assert "must bind the exact candidate" in str(built.error)

    # A proof bound to candidate B cannot qualify candidate A's evidence even
    # when the evidence itself is bound to candidate A.
    cross_proof = _issue_proof(evidence=carrier_for_a, candidate=candidate_b)
    built = verify_governed_gate_evidence(candidate_a, carrier_for_a, cross_proof)
    assert isinstance(built, Failure)
    assert "proof must bind the exact candidate" in str(built.error)

    # A proof whose evidence fingerprint points at a DIFFERENT evidence record
    # (replay) cannot qualify this evidence.
    foreign_carrier = _mint_carrier(
        candidate_a, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=71
    )
    replayed = _issue_proof(
        evidence=carrier_for_a,
        candidate=candidate_a,
        evidence_fingerprint=foreign_carrier.fingerprint,
    )
    built = verify_governed_gate_evidence(candidate_a, carrier_for_a, replayed)
    assert isinstance(built, Failure)
    assert "evidence fingerprint" in str(built.error)


def test_case8_stale_future_replayed_evidence_fails_closed(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    # Naive (non-timezone-aware) decided_at is rejected at construction.
    with pytest.raises(TraderLabValidationError):
        _mint_carrier(
            candidate,
            gate=TraderLabGovernedGate.RISK_REVIEW,
            suffix=8,
            decided_at=datetime(2026, 8, 9, 12, 0),
        )
    # Malformed authority digest is rejected at construction.
    with pytest.raises(TraderLabValidationError):
        _mint_carrier(
            candidate,
            gate=TraderLabGovernedGate.RISK_REVIEW,
            suffix=81,
            authority_digest="zz" * 32,
        )
    # A proof issued BEFORE the governed decision is rejected (future/stale).
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=82
    )
    stale = _issue_proof(
        evidence=carrier,
        candidate=candidate,
        issued_at=carrier.decided_at - timedelta(seconds=1),
    )
    built = verify_governed_gate_evidence(candidate, carrier, stale)
    assert isinstance(built, Failure)
    assert "cannot predate" in str(built.error)

    # Non-approved decisions cannot qualify their stage.
    for decision in (
        TraderLabGovernedDecision.REJECTED,
        TraderLabGovernedDecision.CONDITIONAL,
        TraderLabGovernedDecision.DEFERRED,
    ):
        non_approved = _mint_carrier(
            candidate,
            gate=TraderLabGovernedGate.RISK_REVIEW,
            suffix=83,
            decision=decision,
        )
        proof = _issue_proof(evidence=non_approved, candidate=candidate)
        built = verify_governed_gate_evidence(candidate, non_approved, proof)
        assert isinstance(built, Failure)


def test_case9_direct_constructor_bypass_is_blocked(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    # Evidence direct constructor rejects an authority kind that does not own the
    # gate (constructor equivalence: __post_init__ runs the same invariants).
    with pytest.raises(TraderLabValidationError):
        _mint_carrier(
            candidate,
            gate=TraderLabGovernedGate.RISK_REVIEW,
            suffix=9,
            authority_kind=TraderLabGovernedAuthorityKind.CIBO,
        )
    # A raw string laundered into the gate/decision is rejected.
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=91
    )
    object.__setattr__(carrier, "gate", "risk_review")
    with pytest.raises(TraderLabValidationError):
        validate_trader_lab_governed_gate_evidence(carrier)
    carrier2 = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=92
    )
    object.__setattr__(carrier2, "authority_kind", "risk")
    with pytest.raises(TraderLabValidationError):
        validate_trader_lab_governed_gate_evidence(carrier2)


def test_case10_mutation_and_alias_against_nested_evidence_fails_closed(
    candidate_factory: _CandidateFactory,
    governed_reference_factory: _GovernedRefFactory,
    stage_evidence_factory: _EvidenceFactory,
) -> None:
    candidate = candidate_factory()
    # Reflectively mutate the nested external proof fingerprint of a RISK_REVIEW
    # qualification; trust-boundary revalidation must fail closed.
    lifecycle = _qualify_through(
        start_trader_lab_lifecycle(candidate),
        candidate,
        stage_evidence_factory,
        MANDATORY_STAGES,
    )
    assert lifecycle.state is TraderLabState.DEMO_ELIGIBLE
    risk_qual = next(
        q for q in lifecycle.qualifications if q.stage is TraderLabStage.RISK_REVIEW
    )
    object.__setattr__(
        risk_qual.evidence.source_reference,
        "external_authenticity_proof",
        "0" * 64,
    )
    with pytest.raises(TraderLabValidationError):
        validate_trader_lab_lifecycle(lifecycle)

    # A typed carrier is not a qualifying reference: the stage-evidence builder
    # rejects it outright (wrong type at the receipt boundary).
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=10
    )
    source_reference: Any = carrier
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(_uuid(1000)),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=candidate,
        source_reference=source_reference,
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Failure)

    # A lookalike dataclass carrying equal field values is not an evidence record.
    @dataclass(frozen=True)
    class _Lookalike:
        gate: str
        decision: str
        authority_name: str
        authority_evidence_digest: str

    lookalike = _Lookalike(
        gate=carrier.gate.value,
        decision=carrier.decision.value,
        authority_name=carrier.authority_name,
        authority_evidence_digest=carrier.authority_evidence_digest.value,
    )
    carrier_any: Any = carrier
    assert lookalike != carrier_any


def test_case11_valid_fingerprint_without_external_proof_fails_closed(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    # The carrier carries a valid, self-consistent fingerprint, but no external
    # proof: with no proof it fails closed.
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=11
    )
    built = verify_governed_gate_evidence(candidate, carrier, None)
    assert isinstance(built, Failure)
    assert isinstance(built.error, TraderLabExternalEvidenceDependencyError)


def test_case12_authentic_external_proof_qualifies_without_granting_authority(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=12
    )
    proof = _issue_proof(evidence=carrier, candidate=candidate)
    built = verify_governed_gate_evidence(candidate, carrier, proof)
    assert isinstance(built, Success)
    reference = built.value
    # The qualified reference is an external-authenticated reference, not a
    # self-attested mint and not authority itself.
    validate_trader_lab_evidence_reference(reference)
    assert reference.kind is TraderLabEvidenceKind.RISK_REVIEW
    assert reference.self_authenticating is False
    assert reference.external_authenticity_proof == proof.proof_fingerprint.value
    assert reference.content_digest.value == proof.proof_fingerprint.value
    # The Lab exposes no mint helper: only verify-consume exists.
    import qore.infrastructure.trader_lab as trader_lab

    assert not hasattr(trader_lab, "build_trader_lab_governed_gate_evidence")
    assert not hasattr(trader_lab, "reference_governed_gate_evidence")
    assert not hasattr(trader_lab, "authenticate_governed_gate_evidence")


def test_case13_legitimate_in_repo_paths_still_qualify_and_external_gates_depend(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
    economic_reference_factory: Callable[
        [TraderLabCandidateBinding], TraderLabEvidenceReference
    ],
) -> None:
    candidate = candidate_factory()
    in_repo_stages = MANDATORY_STAGES[
        : MANDATORY_STAGES.index(TraderLabStage.RISK_REVIEW)
    ]
    lifecycle = _qualify_through(
        start_trader_lab_lifecycle(candidate),
        candidate,
        stage_evidence_factory,
        in_repo_stages,
    )
    assert lifecycle.state is TraderLabState.MONTE_CARLO_QUALIFIED
    decision = evaluate_demo_eligibility(
        lifecycle, economic_evidence=economic_reference_factory(candidate)
    )
    assert decision.status is TraderLabPromotionStatus.EXTERNAL_EVIDENCE_DEPENDENT


def test_case14_full_lifecycle_requires_authentic_external_gates(
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _EvidenceFactory,
    economic_reference_factory: Callable[
        [TraderLabCandidateBinding], TraderLabEvidenceReference
    ],
) -> None:
    candidate = candidate_factory()
    # With a trusted external-authority test double, the full chain reaches
    # DEMO_ELIGIBLE.
    lifecycle = _qualify_through(
        start_trader_lab_lifecycle(candidate),
        candidate,
        stage_evidence_factory,
        MANDATORY_STAGES,
    )
    assert lifecycle.state is TraderLabState.DEMO_ELIGIBLE
    decision = evaluate_demo_eligibility(
        lifecycle, economic_evidence=economic_reference_factory(candidate)
    )
    assert decision.status is TraderLabPromotionStatus.DEMO_ELIGIBLE

    # Without an external proof, the external gates cannot be satisfied: the
    # chain stalls at MONTE_CARLO and promotion fails closed as dependent.
    in_repo_stages = MANDATORY_STAGES[
        : MANDATORY_STAGES.index(TraderLabStage.RISK_REVIEW)
    ]
    stalled = _qualify_through(
        start_trader_lab_lifecycle(candidate),
        candidate,
        stage_evidence_factory,
        in_repo_stages,
    )
    assert stalled.state is TraderLabState.MONTE_CARLO_QUALIFIED
    dependent = evaluate_demo_eligibility(
        stalled, economic_evidence=economic_reference_factory(candidate)
    )
    assert dependent.status is TraderLabPromotionStatus.EXTERNAL_EVIDENCE_DEPENDENT


def test_governed_verification_seam_is_verify_only_and_provider_neutral() -> None:
    """The seam is verify-only, carries no authenticator Protocol, and no provider."""

    import qore.infrastructure.trader_lab.governed_gate as governed_gate_module

    # The old authenticator Protocol and duck-typed verify path are gone.
    assert not hasattr(governed_gate_module, "TraderLabGovernedEvidenceAuthenticator")
    assert not hasattr(governed_gate_module, "authenticate_governed_gate_evidence")
    # The verify function takes an already-issued proof, not a caller verifier.
    params = inspect.signature(verify_governed_gate_evidence).parameters
    assert set(params) == {"candidate", "evidence", "proof"}

    # No concrete provider/credential/network imports leak into the seam module.
    source = inspect.getsource(governed_gate_module)
    for forbidden in (
        "import requests",
        "from requests",
        "import http",
        "from http",
        "import urllib",
        "from urllib",
        "import socket",
        "from socket",
    ):
        assert forbidden not in source

def test_external_r2_reference_subclass_mint_is_rejected(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()

    @dataclass(frozen=True, slots=True)
    class _ForgedReference(TraderLabEvidenceReference):
        external_authenticity_proof: str | None = "a" * 64
        candidate_binding_fingerprint: str | None = candidate.fingerprint.value

    with pytest.raises(TraderLabValidationError, match="exact TraderLabEvidenceReference"):
        _ForgedReference(
            kind=TraderLabEvidenceKind.RISK_REVIEW,
            reference_id=_uuid(9901),
            content_digest=TraderLabEvidenceDigest("a" * 64),
            schema_version="forged.v1",
            strategy_binding_fingerprint=(
                candidate.strategy_binding.binding_fingerprint.value
            ),
        )


def test_external_r2_governed_reference_cannot_launder_across_candidates(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate_a = candidate_factory(candidate_suffix=91)
    candidate_b = candidate_factory(
        candidate_suffix=92,
        binding=candidate_a.strategy_binding,
    )
    carrier = _mint_carrier(
        candidate_a, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=9902
    )
    proof = _issue_proof(evidence=carrier, candidate=candidate_a)
    verified = verify_governed_gate_evidence(candidate_a, carrier, proof)
    assert isinstance(verified, Success)
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(_uuid(9903)),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=candidate_b,
        source_reference=verified.value,
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Failure)
    assert "candidate binding does not match" in str(built.error)


def test_external_r2_stress_requires_external_robustness_authority(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory(candidate_suffix=93)
    carrier = _mint_carrier(
        candidate, gate=TraderLabGovernedGate.STRESS_REVIEW, suffix=9904
    )
    without_proof = verify_governed_gate_evidence(candidate, carrier, None)
    assert isinstance(without_proof, Failure)
    assert isinstance(without_proof.error, TraderLabExternalEvidenceDependencyError)

    proof = _issue_proof(evidence=carrier, candidate=candidate)
    verified = verify_governed_gate_evidence(candidate, carrier, proof)
    assert isinstance(verified, Success)
    assert verified.value.kind is TraderLabEvidenceKind.STRESS_EVIDENCE
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(_uuid(9905)),
        stage=TraderLabStage.STRESS,
        candidate=candidate,
        source_reference=verified.value,
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
