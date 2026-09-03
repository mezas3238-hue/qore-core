"""Immutable Trader Lab stage evidence records and typed provenance seams.

Stage evidence carries an exact, content-bound reference to pre-existing
evidence (replay chronology, frozen-OOS, resampling, economic, Risk, CIBO, or
independent validation) without fabricating its conclusions. Every record binds
one exact stage and one exact candidate binding, is immutable, and is
fingerprinted so that stale, mismatched, or post-hoc mutated evidence cannot be
reused.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from qore.infrastructure.market_event_replay import (
    RetainedMarketEventObservation,
    order_market_event_observations,
)
from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapDistribution,
)
from qore.infrastructure.research_economic_evidence import ResearchReturnObservation
from qore.infrastructure.research_evaluation_freeze import ResearchEvaluationFreezeEvidence
from qore.infrastructure.research_frozen_oos_evidence import ResearchFrozenOosEvidence
from qore.infrastructure.research_resampling_envelope import ResearchResamplingEnvelope
from qore.infrastructure.research_sampling_frame import ResearchSamplingFrame
from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabError,
    TraderLabValidationError,
    _canonical_decimal,
    _validate_sha256,
    _validate_token,
    compute_trader_lab_candidate_fingerprint,
)
from qore.kernel.result import Failure, Result, Success


class TraderLabStage(StrEnum):
    """Closed set of mandatory qualification stages, in canonical order."""

    RESEARCH = "research"
    REPLAY = "replay"
    FAST_FORWARD = "fast_forward"
    OOS = "oos"
    STRESS = "stress"
    MONTE_CARLO = "monte_carlo"
    RISK_REVIEW = "risk_review"
    CIBO_REVIEW = "cibo_review"
    INDEPENDENT_VALIDATION = "independent_validation"


class TraderLabEvidenceKind(StrEnum):
    """Closed provenance classes a stage-evidence reference may carry."""

    REPLAY_CHRONOLOGY = "replay.chronology"
    FAST_FORWARD_QUALIFICATION = "trader_lab.fast_forward"
    RESEARCH_STRATEGY_BINDING = "research.strategy_binding"
    FROZEN_OOS = "research.frozen_oos"
    OOS_PERFORMANCE = "research.oos_performance"
    SAMPLING_FRAME = "research.sampling_frame"
    BLOCK_BOOTSTRAP_DISTRIBUTION = "research.block_bootstrap_distribution"
    RESAMPLING_ENVELOPE = "research.resampling_envelope"
    MONTE_CARLO_QUALIFICATION = "trader_lab.monte_carlo"
    STRESS_EVIDENCE = "trader_lab.stress"
    RISK_REVIEW = "risk.review"
    CIBO_REVIEW = "cibo.review"
    ECONOMIC_EVALUATION = "economic.evaluation"
    INDEPENDENT_VALIDATION = "independent.validation"


#: Fail-closed stage -> allowed evidence-kind contract. Each mandatory stage may
#: only carry the semantically correct provenance class(es); any other kind is
#: rejected both on construction and at trust-boundary revalidation.
STAGE_ALLOWED_EVIDENCE_KINDS: dict[TraderLabStage, frozenset[TraderLabEvidenceKind]] = {
    TraderLabStage.RESEARCH: frozenset(
        {TraderLabEvidenceKind.RESEARCH_STRATEGY_BINDING}
    ),
    TraderLabStage.REPLAY: frozenset({TraderLabEvidenceKind.REPLAY_CHRONOLOGY}),
    TraderLabStage.FAST_FORWARD: frozenset(
        {TraderLabEvidenceKind.FAST_FORWARD_QUALIFICATION}
    ),
    TraderLabStage.OOS: frozenset({TraderLabEvidenceKind.FROZEN_OOS}),
    TraderLabStage.STRESS: frozenset({TraderLabEvidenceKind.STRESS_EVIDENCE}),
    TraderLabStage.MONTE_CARLO: frozenset(
        {TraderLabEvidenceKind.MONTE_CARLO_QUALIFICATION}
    ),
    TraderLabStage.RISK_REVIEW: frozenset({TraderLabEvidenceKind.RISK_REVIEW}),
    TraderLabStage.CIBO_REVIEW: frozenset({TraderLabEvidenceKind.CIBO_REVIEW}),
    TraderLabStage.INDEPENDENT_VALIDATION: frozenset(
        {TraderLabEvidenceKind.INDEPENDENT_VALIDATION}
    ),
}

#: Evidence kinds whose content identity is derived from an in-repo canonical
#: object (or an in-repo verified-evidence seam) by a content-deriving helper.
#: None of these may be built through the opaque reference seam, so an arbitrary
#: caller-supplied digest cannot launder a governed gate. Risk/CIBO/independent-
#: validation kinds are deliberately absent: they have no in-repo producer and
#: are external-authenticated (see ``_EXTERNAL_AUTHENTICATED_KINDS``).
_SELF_AUTHENTICATING_KINDS: frozenset[TraderLabEvidenceKind] = frozenset(
    {
        TraderLabEvidenceKind.REPLAY_CHRONOLOGY,
        TraderLabEvidenceKind.FAST_FORWARD_QUALIFICATION,
        TraderLabEvidenceKind.RESEARCH_STRATEGY_BINDING,
        TraderLabEvidenceKind.FROZEN_OOS,
        TraderLabEvidenceKind.OOS_PERFORMANCE,
        TraderLabEvidenceKind.SAMPLING_FRAME,
        TraderLabEvidenceKind.BLOCK_BOOTSTRAP_DISTRIBUTION,
        TraderLabEvidenceKind.RESAMPLING_ENVELOPE,
        TraderLabEvidenceKind.MONTE_CARLO_QUALIFICATION,
        TraderLabEvidenceKind.STRESS_EVIDENCE,
        TraderLabEvidenceKind.ECONOMIC_EVALUATION,
    }
)

#: Evidence kinds governed by an external authority with no in-repo producer.
#: A qualifying reference for these kinds must carry a sealed authenticity proof
#: issued by an owning authority OUTSIDE the Lab; no public or private Trader Lab
#: constructor can mint one.
_EXTERNAL_AUTHENTICATED_KINDS: frozenset[TraderLabEvidenceKind] = frozenset(
    {
        TraderLabEvidenceKind.RISK_REVIEW,
        TraderLabEvidenceKind.CIBO_REVIEW,
        TraderLabEvidenceKind.INDEPENDENT_VALIDATION,
    }
)


def evidence_kind_is_self_authenticating(kind: TraderLabEvidenceKind) -> bool:
    """Return whether the Lab can content-verify this kind from an in-repo object."""

    if not isinstance(kind, TraderLabEvidenceKind):
        raise TraderLabValidationError("kind must be TraderLabEvidenceKind")
    return kind in _SELF_AUTHENTICATING_KINDS


def evidence_kind_is_external_authenticated(kind: TraderLabEvidenceKind) -> bool:
    """Return whether this kind is governed by an external authority (fail-closed)."""

    if not isinstance(kind, TraderLabEvidenceKind):
        raise TraderLabValidationError("kind must be TraderLabEvidenceKind")
    return kind in _EXTERNAL_AUTHENTICATED_KINDS


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TraderLabValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderLabValidationError(f"{field_name} must be timezone-aware")


def _canonical_bytes(payload: object) -> bytes:
    def _default(value: object) -> str:
        if isinstance(value, Decimal):
            return _canonical_decimal(value)
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat(timespec="microseconds")
        raise TypeError(f"unsupported canonical material: {type(value).__qualname__}")

    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_default,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class TraderLabEvidenceDigest:
    """SHA-256 content digest of one referenced evidence object."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="evidence digest")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TraderLabEvidenceReference:
    """Typed, content-bound reference to pre-existing evidence.

    ``content_digest`` is the SHA-256 of the referenced evidence's canonical
    content. For self-authenticating kinds it is derived from the referenced
    object by the helper builders below; for external seams (Risk/CIBO/economic/
    independent validation) it is an opaque caller-supplied digest that the Lab
    never treats as independent proof of content it cannot verify.

    ``strategy_binding_fingerprint`` records the exact research strategy lineage
    when the referenced object exposes it, so cross-candidate evidence reuse is
    rejected at every trust boundary.
    """

    kind: TraderLabEvidenceKind
    reference_id: UUID
    content_digest: TraderLabEvidenceDigest
    schema_version: str
    self_authenticating: bool = field(default=False, init=False)
    strategy_binding_fingerprint: str | None = None
    external_authenticity_proof: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        _validate_evidence_reference_invariants(self)

    def canonical_sort_key(self) -> tuple[str, str, str, str, bool, str, str]:
        """Deterministic total order for canonical unordered-set comparisons."""
        return (
            self.kind.value,
            str(self.reference_id),
            self.content_digest.value,
            self.schema_version,
            self.self_authenticating,
            (
                self.strategy_binding_fingerprint
                if self.strategy_binding_fingerprint is not None
                else ""
            ),
            (
                self.external_authenticity_proof
                if self.external_authenticity_proof is not None
                else ""
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            str(self.reference_id),
            self.content_digest.logical_values(),
            self.schema_version,
            self.self_authenticating,
            self.strategy_binding_fingerprint,
            self.external_authenticity_proof,
        )


def _validate_evidence_reference_invariants(
    reference: TraderLabEvidenceReference,
    *,
    field_name: str = "evidence reference",
) -> None:
    """Validate every invariant of one evidence reference (exact runtime types).

    Runs both at construction and at trust-boundary revalidation. Exact enum
    runtime type is enforced BEFORE any StrEnum value-equality membership, so a
    reflectively-injected raw string cannot launder past ``kind in allowed_kinds``.
    """

    if not isinstance(reference.kind, TraderLabEvidenceKind):
        raise TraderLabValidationError(
            f"{field_name} kind must be TraderLabEvidenceKind"
        )
    if not isinstance(reference.reference_id, UUID):
        raise TraderLabValidationError(f"{field_name} reference_id must be a UUID")
    if not isinstance(reference.content_digest, TraderLabEvidenceDigest):
        raise TraderLabValidationError(
            f"{field_name} content_digest must be TraderLabEvidenceDigest"
        )
    _validate_sha256(
        reference.content_digest.value,
        field_name=f"{field_name} content digest",
    )
    _validate_token(reference.schema_version, field_name=f"{field_name} schema version")
    if type(reference.self_authenticating) is not bool:
        raise TraderLabValidationError(
            f"{field_name} self_authenticating must be a bool"
        )
    if reference.strategy_binding_fingerprint is not None:
        _validate_sha256(
            reference.strategy_binding_fingerprint,
            field_name=f"{field_name} strategy binding fingerprint",
        )
    if reference.external_authenticity_proof is not None:
        _validate_sha256(
            reference.external_authenticity_proof,
            field_name=f"{field_name} external authenticity proof",
        )
    if evidence_kind_is_self_authenticating(
        reference.kind
    ) and not reference.self_authenticating:
        raise TraderLabValidationError(
            f"{field_name} self-authenticating evidence kind must be built via its "
            "content-deriving helper, never an opaque seam"
        )
    if evidence_kind_is_external_authenticated(reference.kind):
        if reference.self_authenticating:
            raise TraderLabValidationError(
                f"{field_name} external-authenticated evidence kind cannot be "
                "self-authenticating"
            )
        if reference.external_authenticity_proof is None:
            raise TraderLabValidationError(
                f"{field_name} external-authenticated evidence kind requires a "
                "sealed authenticity proof issued by an owning authority"
            )
        if reference.content_digest.value != reference.external_authenticity_proof:
            raise TraderLabValidationError(
                f"{field_name} external authenticity proof must equal the "
                "reference content digest"
            )
    elif reference.external_authenticity_proof is not None:
        raise TraderLabValidationError(
            f"{field_name} non-external evidence kind cannot carry an external "
            "authenticity proof"
        )


def validate_trader_lab_evidence_reference(
    reference: TraderLabEvidenceReference,
    *,
    field_name: str = "evidence reference",
) -> None:
    """Re-validate a nested evidence reference at a trust boundary."""

    if not isinstance(reference, TraderLabEvidenceReference):
        raise TraderLabValidationError(
            f"{field_name} must be TraderLabEvidenceReference"
        )
    _validate_evidence_reference_invariants(reference, field_name=field_name)


def _make_self_authenticating_reference(
    *,
    kind: TraderLabEvidenceKind,
    reference_id: UUID,
    content_digest: TraderLabEvidenceDigest,
    schema_version: str,
    strategy_binding_fingerprint: str | None,
) -> TraderLabEvidenceReference:
    """Construct a self-authenticating reference through the only internal path.

    ``self_authenticating`` is ``init=False``, so it cannot be supplied to the
    dataclass constructor: an arbitrary caller-supplied digest can never mint a
    self-authenticating reference. Only the content-deriving helpers below (and
    their siblings in ``governed_gate``/``fast_forward``/``robustness``) call this
    factory, each deriving the digest from the referenced canonical object.
    """

    reference = object.__new__(TraderLabEvidenceReference)
    object.__setattr__(reference, "kind", kind)
    object.__setattr__(reference, "reference_id", reference_id)
    object.__setattr__(reference, "content_digest", content_digest)
    object.__setattr__(reference, "schema_version", schema_version)
    object.__setattr__(reference, "self_authenticating", True)
    object.__setattr__(
        reference, "strategy_binding_fingerprint", strategy_binding_fingerprint
    )
    object.__setattr__(reference, "external_authenticity_proof", None)
    _validate_evidence_reference_invariants(reference)
    return reference


def _make_external_authenticated_reference(
    *,
    kind: TraderLabEvidenceKind,
    reference_id: UUID,
    content_digest: TraderLabEvidenceDigest,
    schema_version: str,
    strategy_binding_fingerprint: str | None,
    authenticity_proof_fingerprint: str,
) -> TraderLabEvidenceReference:
    """Construct an external-authenticated reference through the only internal path.

    ``external_authenticity_proof`` is ``init=False``, so it cannot be supplied to
    the dataclass constructor. Only ``verify_governed_gate_evidence`` (which
    consumes an already-issued external authenticity proof) may call this
    factory; the production Trader Lab surface exposes no caller that can mint a
    qualifying Risk/CIBO/independent-validation reference.
    """

    reference = object.__new__(TraderLabEvidenceReference)
    object.__setattr__(reference, "kind", kind)
    object.__setattr__(reference, "reference_id", reference_id)
    object.__setattr__(reference, "content_digest", content_digest)
    object.__setattr__(reference, "schema_version", schema_version)
    object.__setattr__(reference, "self_authenticating", False)
    object.__setattr__(
        reference, "strategy_binding_fingerprint", strategy_binding_fingerprint
    )
    object.__setattr__(
        reference, "external_authenticity_proof", authenticity_proof_fingerprint
    )
    _validate_evidence_reference_invariants(reference)
    return reference


def make_trader_lab_evidence_reference(
    *,
    kind: TraderLabEvidenceKind,
    reference_id: UUID,
    content_digest: TraderLabEvidenceDigest,
    schema_version: str,
) -> TraderLabEvidenceReference:
    """Fail-closed opaque reference seam.

    Every evidence kind is now self-authenticating: its content identity must be
    derived from the canonical object (or the verified-evidence seam) by the
    corresponding content-deriving helper. An arbitrary caller-supplied digest
    can therefore never mint a governed-gate or economic reference, and cannot
    advance the lifecycle or ``DEMO_ELIGIBLE``.
    """

    raise TraderLabValidationError(
        "opaque evidence references are disabled: every evidence kind requires "
        "its content-deriving helper"
    )


def _verify_strategy_lineage(
    candidate: TraderLabCandidateBinding,
    strategy_binding: ResearchRunStrategyBinding,
) -> str:
    """Verify exact strategy lineage and return the binding fingerprint string."""

    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    if not isinstance(strategy_binding, ResearchRunStrategyBinding):
        raise TraderLabValidationError(
            "strategy lineage requires ResearchRunStrategyBinding"
        )
    if (
        strategy_binding.binding_fingerprint
        != candidate.strategy_binding.binding_fingerprint
    ):
        raise TraderLabValidationError(
            "referenced evidence strategy lineage does not match the candidate"
        )
    return candidate.strategy_binding.binding_fingerprint.value


def reference_research_frozen_oos(
    candidate: TraderLabCandidateBinding,
    evidence: ResearchFrozenOosEvidence,
) -> TraderLabEvidenceReference:
    """Reference exact frozen-OOS evidence bound to the candidate strategy lineage."""

    if not isinstance(evidence, ResearchFrozenOosEvidence):
        raise TraderLabValidationError(
            "frozen OOS reference requires ResearchFrozenOosEvidence"
        )
    lineage = _verify_strategy_lineage(
        candidate, evidence.evaluation_freeze.strategy_binding
    )
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.FROZEN_OOS,
        reference_id=evidence.evidence_id.value,
        content_digest=TraderLabEvidenceDigest(evidence.fingerprint.value),
        schema_version="research.frozen-oos.v1",
        strategy_binding_fingerprint=lineage,
    )


def reference_research_evaluation_freeze(
    candidate: TraderLabCandidateBinding,
    evidence: ResearchEvaluationFreezeEvidence,
) -> TraderLabEvidenceReference:
    """Reference the pre-outcome methodology/strategy freeze binding for RESEARCH.

    ``ResearchEvaluationFreezeEvidence`` proves exact strategy content preceded the
    temporal evaluation plan and carries no OOS performance material, so it is the
    only evidence class that may satisfy the RESEARCH stage. It must never be
    replaced by ``ResearchFrozenOosEvidence`` (which embeds post-outcome OOS
    performance and would launder hindsight into the earlier stage).
    """

    if not isinstance(evidence, ResearchEvaluationFreezeEvidence):
        raise TraderLabValidationError(
            "research strategy binding requires ResearchEvaluationFreezeEvidence"
        )
    lineage = _verify_strategy_lineage(candidate, evidence.strategy_binding)
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.RESEARCH_STRATEGY_BINDING,
        reference_id=evidence.evidence_id.value,
        content_digest=TraderLabEvidenceDigest(evidence.fingerprint.value),
        schema_version="research.evaluation-freeze.v1",
        strategy_binding_fingerprint=lineage,
    )


def reference_research_economic(
    candidate: TraderLabCandidateBinding,
    observation: ResearchReturnObservation,
) -> TraderLabEvidenceReference:
    """Reference exact economic-evaluation evidence bound to the candidate run.

    ``ResearchReturnObservation`` is an authoritative research economic-evidence
    object (gross/net P&L over an explicit capital basis). Its digest is derived
    from the object's canonical content, so an arbitrary caller-supplied digest
    cannot satisfy the economic-evaluation promotion gate.
    """

    if not isinstance(observation, ResearchReturnObservation):
        raise TraderLabValidationError(
            "economic evaluation reference requires ResearchReturnObservation"
        )
    if observation.run != candidate.strategy_binding.run:
        raise TraderLabValidationError(
            "economic evaluation evidence must bind the exact candidate research run"
        )
    lineage = candidate.strategy_binding.binding_fingerprint.value
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.economic_return.v1",
                    "observation_id": str(observation.observation_id.value),
                    "run_input_fingerprint": observation.run.input_fingerprint.value,
                    "strategy_binding_fingerprint": lineage,
                    "capital_basis_currency": observation.capital_basis.currency.value,
                    "capital_basis_amount": _canonical_decimal(
                        observation.capital_basis.amount
                    ),
                    "return_rate": _canonical_decimal(observation.return_rate),
                    "observed_at": observation.observed_at.astimezone(UTC).isoformat(
                        timespec="microseconds"
                    ),
                    "basis": observation.basis.value,
                }
            )
        ).hexdigest()
    )
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.ECONOMIC_EVALUATION,
        reference_id=observation.observation_id.value,
        content_digest=digest,
        schema_version="research.economic-return.v1",
        strategy_binding_fingerprint=lineage,
    )


def reference_research_sampling_frame(
    candidate: TraderLabCandidateBinding,
    frame: ResearchSamplingFrame,
) -> TraderLabEvidenceReference:
    """Reference an exact sampling frame bound to the candidate strategy lineage."""

    if not isinstance(frame, ResearchSamplingFrame):
        raise TraderLabValidationError(
            "sampling frame reference requires ResearchSamplingFrame"
        )
    lineage = _verify_strategy_lineage(
        candidate, frame.frozen_oos.evaluation_freeze.strategy_binding
    )
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.sampling_frame.v1",
                    "frame_id": str(frame.frame_id.value),
                    "frozen_oos_fingerprint": frame.frozen_oos.fingerprint.value,
                    "strategy_binding_fingerprint": lineage,
                    "sampling_unit": frame.sampling_unit.value,
                    "fold_sample_sizes": list(frame.fold_sample_sizes),
                    "overlap_status": frame.overlap_status.value,
                    "sample_size": frame.sample_size,
                }
            )
        ).hexdigest()
    )
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.SAMPLING_FRAME,
        reference_id=frame.frame_id.value,
        content_digest=digest,
        schema_version="research.sampling-frame.v1",
        strategy_binding_fingerprint=lineage,
    )


def reference_research_block_bootstrap_distribution(
    candidate: TraderLabCandidateBinding,
    distribution: ResearchBlockBootstrapDistribution,
) -> TraderLabEvidenceReference:
    """Reference an exact block-bootstrap distribution bound to the candidate."""

    if not isinstance(distribution, ResearchBlockBootstrapDistribution):
        raise TraderLabValidationError(
            "block bootstrap reference requires ResearchBlockBootstrapDistribution"
        )
    lineage = _verify_strategy_lineage(
        candidate,
        distribution.diagnostic.frame.frozen_oos.evaluation_freeze.strategy_binding,
    )
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.block_bootstrap.v1",
                    "distribution_id": str(distribution.distribution_id.value),
                    "frozen_oos_fingerprint": (
                        distribution.diagnostic.frame.frozen_oos.fingerprint.value
                    ),
                    "strategy_binding_fingerprint": lineage,
                    "diagnostic_id": str(
                        distribution.diagnostic.diagnostic_id.value
                    ),
                    "diagnostic_status": distribution.diagnostic.status.value,
                    "policy": list(distribution.policy.logical_values()),
                    "sample_size": distribution.sample_size,
                    "source_mean": _canonical_decimal(distribution.source_mean),
                    "resampled_means": [
                        _canonical_decimal(value)
                        for value in distribution.resampled_means
                    ],
                }
            )
        ).hexdigest()
    )
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.BLOCK_BOOTSTRAP_DISTRIBUTION,
        reference_id=distribution.distribution_id.value,
        content_digest=digest,
        schema_version="research.block-bootstrap.v1",
        strategy_binding_fingerprint=lineage,
    )


def reference_research_resampling_envelope(
    candidate: TraderLabCandidateBinding,
    envelope: ResearchResamplingEnvelope,
) -> TraderLabEvidenceReference:
    """Reference an exact resampling envelope bound to the candidate lineage."""

    if not isinstance(envelope, ResearchResamplingEnvelope):
        raise TraderLabValidationError(
            "resampling envelope reference requires ResearchResamplingEnvelope"
        )
    lineage = _verify_strategy_lineage(
        candidate,
        envelope.distribution.diagnostic.frame.frozen_oos.evaluation_freeze.strategy_binding,
    )
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.resampling_envelope.v1",
                    "envelope_id": str(envelope.envelope_id.value),
                    "frozen_oos_fingerprint": (
                        envelope.distribution.diagnostic.frame.frozen_oos.fingerprint.value
                    ),
                    "strategy_binding_fingerprint": lineage,
                    "distribution_id": str(
                        envelope.distribution.distribution_id.value
                    ),
                    "policy": list(envelope.policy.logical_values()),
                    "empirical_sample_size": envelope.empirical_sample_size,
                    "lower_mean": _canonical_decimal(envelope.lower_mean),
                    "median_mean": _canonical_decimal(envelope.median_mean),
                    "upper_mean": _canonical_decimal(envelope.upper_mean),
                }
            )
        ).hexdigest()
    )
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.RESAMPLING_ENVELOPE,
        reference_id=envelope.envelope_id.value,
        content_digest=digest,
        schema_version="research.resampling-envelope.v1",
        strategy_binding_fingerprint=lineage,
    )


def compute_replay_chronology_digest(
    observations: tuple[RetainedMarketEventObservation, ...],
) -> TraderLabEvidenceDigest:
    """Compute the shared canonical replay-chronology content digest.

    This is the single canonical digest used by both the REPLAY stage reference
    and the FAST_FORWARD qualification so their histories cannot diverge.
    """

    ordered = order_market_event_observations(observations)
    if not ordered:
        raise TraderLabValidationError(
            "replay chronology requires non-empty observations"
        )
    return TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.replay_chronology.v1",
                    "event_count": len(ordered),
                    "events": [list(item.logical_values()) for item in ordered],
                }
            )
        ).hexdigest()
    )


def reference_replay_chronology(
    observations: tuple[RetainedMarketEventObservation, ...],
) -> TraderLabEvidenceReference:
    """Reference the exact ordered replay chronology of retained market events."""

    digest = compute_replay_chronology_digest(observations)
    reference_id = uuid5(
        NAMESPACE_URL, f"qore.trader_lab.replay.chronology:{digest.value}"
    )
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.REPLAY_CHRONOLOGY,
        reference_id=reference_id,
        content_digest=digest,
        schema_version="market-event-replay.v1",
        strategy_binding_fingerprint=None,
    )


@dataclass(frozen=True, slots=True)
class TraderLabStageEvidenceId:
    """Immutable identity of one stage-evidence record."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TraderLabValidationError("stage evidence id must be a UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TraderLabStageEvidenceFingerprint:
    """Canonical SHA-256 digest of the complete stage-evidence record."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="stage evidence fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _canonical_supplementary(
    supplementary: tuple[TraderLabEvidenceReference, ...],
) -> tuple[TraderLabEvidenceReference, ...]:
    """Return the canonical unordered-set projection of supplementary references.

    Supplementary references carry no positional meaning: identity is an
    order-insensitive set. Every item is deep-validated and duplicate
    ``reference_id`` values are rejected so the set is well-defined.
    """

    if not isinstance(supplementary, tuple) or any(
        not isinstance(item, TraderLabEvidenceReference) for item in supplementary
    ):
        raise TraderLabValidationError(
            "supplementary must be an immutable TraderLabEvidenceReference tuple"
        )
    for item in supplementary:
        validate_trader_lab_evidence_reference(
            item, field_name="supplementary reference"
        )
    reference_ids = [item.reference_id for item in supplementary]
    if len(set(reference_ids)) != len(reference_ids):
        raise TraderLabValidationError(
            "supplementary evidence references must be unique"
        )
    return tuple(sorted(supplementary, key=lambda item: item.canonical_sort_key()))


def compute_trader_lab_stage_evidence_fingerprint(
    *,
    stage: TraderLabStage,
    candidate: TraderLabCandidateBinding,
    source_reference: TraderLabEvidenceReference,
    supplementary: tuple[TraderLabEvidenceReference, ...],
    produced_at: datetime,
) -> TraderLabStageEvidenceFingerprint:
    """Hash the complete stage-evidence identity, including explicit time."""

    if not isinstance(stage, TraderLabStage):
        raise TraderLabValidationError("stage must be TraderLabStage")
    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    validate_trader_lab_evidence_reference(
        source_reference, field_name="source reference"
    )
    ordered_supplementary = _canonical_supplementary(supplementary)
    _validate_timestamp(produced_at, field_name="stage evidence produced_at")
    canonical = {
        "schema": "qore.trader_lab.stage_evidence.v1",
        "stage": stage.value,
        "candidate_fingerprint": candidate.fingerprint.value,
        "source_reference": list(source_reference.logical_values()),
        "supplementary": [
            list(item.logical_values()) for item in ordered_supplementary
        ],
        "produced_at": produced_at.astimezone(UTC).isoformat(timespec="microseconds"),
    }
    encoded = _canonical_bytes(canonical)
    return TraderLabStageEvidenceFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class TraderLabStageEvidenceRecord:
    """Immutable stage evidence with explicit provenance, fingerprint, and time.

    All identity and time material is supplied explicitly; there is no hidden
    clock or random identity. The record binds exactly one stage and one
    candidate and cannot carry free-form prose as promotion authority.
    """

    evidence_id: TraderLabStageEvidenceId
    stage: TraderLabStage
    candidate: TraderLabCandidateBinding
    source_reference: TraderLabEvidenceReference
    produced_at: datetime
    fingerprint: TraderLabStageEvidenceFingerprint
    supplementary: tuple[TraderLabEvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        _validate_stage_evidence_record_invariants(self)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.stage.value,
            self.candidate.fingerprint.logical_values(),
            self.source_reference.logical_values(),
            tuple(item.logical_values() for item in self.supplementary),
            self.produced_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.fingerprint.logical_values(),
        )


#: Evidence kinds that MUST carry a strategy lineage binding. The only kind that
#: legitimately omits lineage is REPLAY_CHRONOLOGY (a shared, strategy-agnostic
#: replay history); every other kind is content-bound to one candidate strategy.
_KINDS_REQUIRING_LINEAGE: frozenset[TraderLabEvidenceKind] = frozenset(
    kind
    for kind in TraderLabEvidenceKind
    if kind is not TraderLabEvidenceKind.REPLAY_CHRONOLOGY
)


def _validate_reference_lineage(
    candidate: TraderLabCandidateBinding,
    reference: TraderLabEvidenceReference,
    *,
    field_name: str,
) -> None:
    """Reject a reference whose strategy lineage mismatches the candidate."""

    if reference.strategy_binding_fingerprint is None:
        if reference.kind in _KINDS_REQUIRING_LINEAGE:
            raise TraderLabValidationError(
                f"{field_name} requires a strategy lineage binding"
            )
        return
    if reference.strategy_binding_fingerprint != (
        candidate.strategy_binding.binding_fingerprint.value
    ):
        raise TraderLabValidationError(
            f"{field_name} strategy lineage does not match the candidate"
        )


def _validate_stage_evidence_record_invariants(
    record: TraderLabStageEvidenceRecord,
) -> None:
    """Validate every invariant of one stage-evidence record.

    This runs both at construction and at trust-boundary revalidation, so a
    reflectively corrupted frozen record cannot be silently reused.
    """

    if not isinstance(record.evidence_id, TraderLabStageEvidenceId):
        raise TraderLabValidationError("evidence_id must be TraderLabStageEvidenceId")
    if not isinstance(record.stage, TraderLabStage):
        raise TraderLabValidationError("stage must be TraderLabStage")
    if not isinstance(record.candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    _validate_timestamp(record.produced_at, field_name="stage evidence produced_at")
    if not isinstance(record.fingerprint, TraderLabStageEvidenceFingerprint):
        raise TraderLabValidationError(
            "fingerprint must be TraderLabStageEvidenceFingerprint"
        )

    # Recompute the candidate fingerprint from retained material so a
    # reflectively corrupted candidate binding cannot launder into the record.
    expected_candidate = compute_trader_lab_candidate_fingerprint(
        candidate_id=record.candidate.candidate_id,
        version=record.candidate.version,
        strategy_binding=record.candidate.strategy_binding,
    )
    if record.candidate.fingerprint != expected_candidate:
        raise TraderLabValidationError(
            "candidate fingerprint must match the recomputed exact binding"
        )

    # Deep-validate the source and every supplementary reference (exact runtime
    # types) BEFORE any StrEnum value-equality membership or fingerprint use.
    validate_trader_lab_evidence_reference(
        record.source_reference, field_name="source reference"
    )
    ordered_supplementary = _canonical_supplementary(record.supplementary)
    if record.supplementary != ordered_supplementary:
        raise TraderLabValidationError(
            "supplementary references must use canonical unordered-set order"
        )

    allowed_kinds = STAGE_ALLOWED_EVIDENCE_KINDS[record.stage]
    if record.source_reference.kind not in allowed_kinds:
        raise TraderLabValidationError(
            "evidence kind is not allowed for the mandatory stage"
        )
    for item in record.supplementary:
        if item.kind not in allowed_kinds:
            raise TraderLabValidationError(
                "supplementary evidence kind is not allowed for the mandatory stage"
            )
    _validate_reference_lineage(
        record.candidate, record.source_reference, field_name="source reference"
    )
    for item in record.supplementary:
        _validate_reference_lineage(
            record.candidate, item, field_name="supplementary reference"
        )

    expected = compute_trader_lab_stage_evidence_fingerprint(
        stage=record.stage,
        candidate=record.candidate,
        source_reference=record.source_reference,
        supplementary=record.supplementary,
        produced_at=record.produced_at,
    )
    if record.fingerprint != expected:
        raise TraderLabValidationError(
            "stage evidence fingerprint must match the exact record"
        )


def validate_trader_lab_stage_evidence_record(
    record: TraderLabStageEvidenceRecord,
) -> None:
    """Re-validate a stage-evidence record at a trust boundary."""

    if not isinstance(record, TraderLabStageEvidenceRecord):
        raise TraderLabValidationError(
            "record must be TraderLabStageEvidenceRecord"
        )
    _validate_stage_evidence_record_invariants(record)


def build_trader_lab_stage_evidence(
    *,
    evidence_id: TraderLabStageEvidenceId,
    stage: TraderLabStage,
    candidate: TraderLabCandidateBinding,
    source_reference: TraderLabEvidenceReference,
    produced_at: datetime,
    supplementary: tuple[TraderLabEvidenceReference, ...] = (),
) -> Result[TraderLabStageEvidenceRecord, TraderLabError]:
    """Build immutable stage evidence without executing or evaluating anything."""

    try:
        ordered_supplementary = _canonical_supplementary(supplementary)
        fingerprint = compute_trader_lab_stage_evidence_fingerprint(
            stage=stage,
            candidate=candidate,
            source_reference=source_reference,
            supplementary=ordered_supplementary,
            produced_at=produced_at,
        )
        return Success(
            TraderLabStageEvidenceRecord(
                evidence_id=evidence_id,
                stage=stage,
                candidate=candidate,
                source_reference=source_reference,
                produced_at=produced_at,
                fingerprint=fingerprint,
                supplementary=ordered_supplementary,
            )
        )
    except TraderLabError as error:
        return Failure(error)
