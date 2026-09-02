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
from dataclasses import dataclass
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
from qore.infrastructure.research_frozen_oos_evidence import ResearchFrozenOosEvidence
from qore.infrastructure.research_resampling_envelope import ResearchResamplingEnvelope
from qore.infrastructure.research_sampling_frame import ResearchSamplingFrame
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabError,
    TraderLabValidationError,
    _validate_sha256,
    _validate_token,
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
    FROZEN_OOS = "research.frozen_oos"
    OOS_PERFORMANCE = "research.oos_performance"
    SAMPLING_FRAME = "research.sampling_frame"
    BLOCK_BOOTSTRAP_DISTRIBUTION = "research.block_bootstrap_distribution"
    RESAMPLING_ENVELOPE = "research.resampling_envelope"
    RISK_REVIEW = "risk.review"
    CIBO_REVIEW = "cibo.review"
    ECONOMIC_EVALUATION = "economic.evaluation"
    INDEPENDENT_VALIDATION = "independent.validation"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TraderLabValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderLabValidationError(f"{field_name} must be timezone-aware")


def _canonical_bytes(payload: object) -> bytes:
    def _default(value: object) -> str:
        if isinstance(value, Decimal):
            return format(value, "f")
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
    content. It is supplied by the referencing party (or computed by the helper
    builders below); the Lab never fabricates the referenced evidence's
    conclusions.
    """

    kind: TraderLabEvidenceKind
    reference_id: UUID
    content_digest: TraderLabEvidenceDigest
    schema_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TraderLabEvidenceKind):
            raise TraderLabValidationError(
                "evidence reference kind must be TraderLabEvidenceKind"
            )
        if not isinstance(self.reference_id, UUID):
            raise TraderLabValidationError("evidence reference_id must be a UUID")
        if not isinstance(self.content_digest, TraderLabEvidenceDigest):
            raise TraderLabValidationError(
                "content_digest must be TraderLabEvidenceDigest"
            )
        _validate_token(self.schema_version, field_name="evidence schema version")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            str(self.reference_id),
            self.content_digest.logical_values(),
            self.schema_version,
        )


def make_trader_lab_evidence_reference(
    *,
    kind: TraderLabEvidenceKind,
    reference_id: UUID,
    content_digest: TraderLabEvidenceDigest,
    schema_version: str,
) -> TraderLabEvidenceReference:
    """Build an opaque typed reference (used for Risk/CIBO/economic seams)."""

    return TraderLabEvidenceReference(
        kind=kind,
        reference_id=reference_id,
        content_digest=content_digest,
        schema_version=schema_version,
    )


def reference_research_frozen_oos(
    evidence: ResearchFrozenOosEvidence,
) -> TraderLabEvidenceReference:
    """Reference exact frozen-OOS evidence by its own composed fingerprint."""

    if not isinstance(evidence, ResearchFrozenOosEvidence):
        raise TraderLabValidationError(
            "frozen OOS reference requires ResearchFrozenOosEvidence"
        )
    return TraderLabEvidenceReference(
        kind=TraderLabEvidenceKind.FROZEN_OOS,
        reference_id=evidence.evidence_id.value,
        content_digest=TraderLabEvidenceDigest(evidence.fingerprint.value),
        schema_version="research.frozen-oos.v1",
    )


def reference_research_sampling_frame(
    frame: ResearchSamplingFrame,
) -> TraderLabEvidenceReference:
    """Reference an exact sampling frame bound to its frozen-OOS fingerprint."""

    if not isinstance(frame, ResearchSamplingFrame):
        raise TraderLabValidationError(
            "sampling frame reference requires ResearchSamplingFrame"
        )
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.sampling_frame.v1",
                    "frame_id": str(frame.frame_id.value),
                    "frozen_oos_fingerprint": frame.frozen_oos.fingerprint.value,
                    "overlap_status": frame.overlap_status.value,
                    "sample_size": frame.sample_size,
                }
            )
        ).hexdigest()
    )
    return TraderLabEvidenceReference(
        kind=TraderLabEvidenceKind.SAMPLING_FRAME,
        reference_id=frame.frame_id.value,
        content_digest=digest,
        schema_version="research.sampling-frame.v1",
    )


def reference_research_block_bootstrap_distribution(
    distribution: ResearchBlockBootstrapDistribution,
) -> TraderLabEvidenceReference:
    """Reference an exact deterministic block-bootstrap distribution."""

    if not isinstance(distribution, ResearchBlockBootstrapDistribution):
        raise TraderLabValidationError(
            "block bootstrap reference requires ResearchBlockBootstrapDistribution"
        )
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.block_bootstrap.v1",
                    "distribution_id": str(distribution.distribution_id.value),
                    "diagnostic_id": str(distribution.diagnostic.diagnostic_id.value),
                    "policy": list(distribution.policy.logical_values()),
                    "sample_size": distribution.sample_size,
                    "source_mean": format(distribution.source_mean, "f"),
                    "resampled_means": [
                        format(value, "f") for value in distribution.resampled_means
                    ],
                }
            )
        ).hexdigest()
    )
    return TraderLabEvidenceReference(
        kind=TraderLabEvidenceKind.BLOCK_BOOTSTRAP_DISTRIBUTION,
        reference_id=distribution.distribution_id.value,
        content_digest=digest,
        schema_version="research.block-bootstrap.v1",
    )


def reference_research_resampling_envelope(
    envelope: ResearchResamplingEnvelope,
) -> TraderLabEvidenceReference:
    """Reference an exact deterministic resampling envelope."""

    if not isinstance(envelope, ResearchResamplingEnvelope):
        raise TraderLabValidationError(
            "resampling envelope reference requires ResearchResamplingEnvelope"
        )
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.resampling_envelope.v1",
                    "envelope_id": str(envelope.envelope_id.value),
                    "distribution_id": str(
                        envelope.distribution.distribution_id.value
                    ),
                    "policy": list(envelope.policy.logical_values()),
                    "empirical_sample_size": envelope.empirical_sample_size,
                    "lower_mean": format(envelope.lower_mean, "f"),
                    "median_mean": format(envelope.median_mean, "f"),
                    "upper_mean": format(envelope.upper_mean, "f"),
                }
            )
        ).hexdigest()
    )
    return TraderLabEvidenceReference(
        kind=TraderLabEvidenceKind.RESAMPLING_ENVELOPE,
        reference_id=envelope.envelope_id.value,
        content_digest=digest,
        schema_version="research.resampling-envelope.v1",
    )


def reference_replay_chronology(
    observations: tuple[RetainedMarketEventObservation, ...],
) -> TraderLabEvidenceReference:
    """Reference the exact ordered replay chronology of retained market events."""

    ordered = order_market_event_observations(observations)
    if not ordered:
        raise TraderLabValidationError(
            "replay chronology reference requires non-empty observations"
        )
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.replay_chronology.v1",
                    "event_count": len(ordered),
                    "events": [list(item.logical_values()) for item in ordered],
                }
            )
        ).hexdigest()
    )
    reference_id = uuid5(NAMESPACE_URL, f"qore.trader_lab.replay.chronology:{digest.value}")
    return TraderLabEvidenceReference(
        kind=TraderLabEvidenceKind.REPLAY_CHRONOLOGY,
        reference_id=reference_id,
        content_digest=digest,
        schema_version="market-event-replay.v1",
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
    if not isinstance(source_reference, TraderLabEvidenceReference):
        raise TraderLabValidationError(
            "source_reference must be TraderLabEvidenceReference"
        )
    if not isinstance(supplementary, tuple) or any(
        not isinstance(item, TraderLabEvidenceReference) for item in supplementary
    ):
        raise TraderLabValidationError(
            "supplementary must be an immutable TraderLabEvidenceReference tuple"
        )
    _validate_timestamp(produced_at, field_name="stage evidence produced_at")
    canonical = {
        "schema": "qore.trader_lab.stage_evidence.v1",
        "stage": stage.value,
        "candidate_fingerprint": candidate.fingerprint.value,
        "source_reference": list(source_reference.logical_values()),
        "supplementary": [list(item.logical_values()) for item in supplementary],
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
        if not isinstance(self.evidence_id, TraderLabStageEvidenceId):
            raise TraderLabValidationError(
                "evidence_id must be TraderLabStageEvidenceId"
            )
        if not isinstance(self.stage, TraderLabStage):
            raise TraderLabValidationError("stage must be TraderLabStage")
        if not isinstance(self.candidate, TraderLabCandidateBinding):
            raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
        if not isinstance(self.source_reference, TraderLabEvidenceReference):
            raise TraderLabValidationError(
                "source_reference must be TraderLabEvidenceReference"
            )
        _validate_timestamp(self.produced_at, field_name="stage evidence produced_at")
        if not isinstance(self.supplementary, tuple) or any(
            not isinstance(item, TraderLabEvidenceReference) for item in self.supplementary
        ):
            raise TraderLabValidationError(
                "supplementary must be an immutable TraderLabEvidenceReference tuple"
            )
        if not isinstance(self.fingerprint, TraderLabStageEvidenceFingerprint):
            raise TraderLabValidationError(
                "fingerprint must be TraderLabStageEvidenceFingerprint"
            )
        expected = compute_trader_lab_stage_evidence_fingerprint(
            stage=self.stage,
            candidate=self.candidate,
            source_reference=self.source_reference,
            supplementary=self.supplementary,
            produced_at=self.produced_at,
        )
        if self.fingerprint != expected:
            raise TraderLabValidationError(
                "stage evidence fingerprint must match the exact record"
            )

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
        fingerprint = compute_trader_lab_stage_evidence_fingerprint(
            stage=stage,
            candidate=candidate,
            source_reference=source_reference,
            supplementary=supplementary,
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
                supplementary=supplementary,
            )
        )
    except TraderLabError as error:
        return Failure(error)
