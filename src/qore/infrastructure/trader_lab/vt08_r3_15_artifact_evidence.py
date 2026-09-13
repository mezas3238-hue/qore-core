"""Immutable official-artifact references for VT-08 R3.15 certification.

This adapter is intentionally narrow: it can only reference the frozen VT-08
R3.15/R3.12 evidence set and derives every Trader Lab digest from exact immutable
GitHub Actions artifact identities plus the exact candidate binding. It does not
accept arbitrary evidence kinds or caller-supplied Trader Lab digests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from re import fullmatch
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabValidationError,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    TraderLabStage,
    _canonical_bytes,
    _make_self_authenticating_reference,
)

_R315_HEAD = "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
_R312_HEAD = "6a09be314a5c8b6a17822ea141a41d521aaf8655"
_R314_HEAD = "266fa60df2654ffcbce3a89569295bb19f791022"
_EXPECTED_METHOD = "0c3fe8e1353386f7384a8532c7fe71bbbe9fcfdf1da7530be4b53e01bc59de0d"
_EXPECTED_SOURCE = "403d54304f241f4a11b1ef847aa2a8b12d5ba6ffa2d9be5bb5cd9c19586943e3"

_ALLOWED_STAGES = frozenset(
    {
        TraderLabStage.RESEARCH,
        TraderLabStage.REPLAY,
        TraderLabStage.FAST_FORWARD,
        TraderLabStage.OOS,
        TraderLabStage.MONTE_CARLO,
        TraderLabStage.ECONOMIC_EVIDENCE,
    }
)
_KIND_BY_STAGE = {
    TraderLabStage.RESEARCH: TraderLabEvidenceKind.RESEARCH_STRATEGY_BINDING,
    TraderLabStage.REPLAY: TraderLabEvidenceKind.REPLAY_CHRONOLOGY,
    TraderLabStage.FAST_FORWARD: TraderLabEvidenceKind.FAST_FORWARD_QUALIFICATION,
    TraderLabStage.OOS: TraderLabEvidenceKind.FROZEN_OOS,
    TraderLabStage.MONTE_CARLO: TraderLabEvidenceKind.MONTE_CARLO_QUALIFICATION,
    TraderLabStage.ECONOMIC_EVIDENCE: TraderLabEvidenceKind.ECONOMIC_EVALUATION,
}
@dataclass(frozen=True, slots=True)
class Vt08R315ImmutableArtifact:
    """One immutable external artifact participating in final certification."""

    name: str
    artifact_id: int
    run_id: int
    head_sha: str
    digest: str

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise TraderLabValidationError("artifact name must be non-empty")
        if type(self.artifact_id) is not int or self.artifact_id <= 0:
            raise TraderLabValidationError("artifact id must be positive")
        if type(self.run_id) is not int or self.run_id <= 0:
            raise TraderLabValidationError("artifact run id must be positive")
        if fullmatch(r"[0-9a-f]{40}", self.head_sha) is None:
            raise TraderLabValidationError("artifact head must be exact git SHA")
        if fullmatch(r"[0-9a-f]{64}", self.digest) is None:
            raise TraderLabValidationError("artifact digest must be SHA-256")

    def logical_values(self) -> tuple[object, ...]:
        return (self.name, self.artifact_id, self.run_id, self.head_sha, self.digest)


R315_HOLDOUT_ARTIFACT = Vt08R315ImmutableArtifact(
    name="qore-vt08-r3-15-independent-holdout-64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222",
    artifact_id=10_318_827_002,
    run_id=34_759_027_136,
    head_sha=_R315_HEAD,
    digest="73aad16176f2f5335b47fff6510f8f3ce586e2d0a291dd6056c4d3c9e57f9ae4",
)
R312_RISK_ARTIFACT = Vt08R315ImmutableArtifact(
    name="qore-vt08-r3-12-adaptive-prop-risk-6a09be314a5c8b6a17822ea141a41d521aaf8655",
    artifact_id=10_309_794_877,
    run_id=34_733_491_533,
    head_sha=_R312_HEAD,
    digest="6b1ccbeac047b1d06d0b9eee7c24443d2ab03d7a9f33389dbc7ab34adba51d77",
)
R314_FUNDING_ARTIFACT = Vt08R315ImmutableArtifact(
    name="qore-vt08-r3-14-two-phase-funding-266fa60df2654ffcbce3a89569295bb19f791022",
    artifact_id=10_311_039_498,
    run_id=34_737_134_896,
    head_sha=_R314_HEAD,
    digest="4745b610b4fe590b94dd715ef2e31d878971d768e96cf84ad6883a2d98869ac8",
)
_ARTIFACTS_BY_STAGE = {
    TraderLabStage.RESEARCH: (R314_FUNDING_ARTIFACT,),
    TraderLabStage.REPLAY: (R315_HOLDOUT_ARTIFACT,),
    TraderLabStage.FAST_FORWARD: (R314_FUNDING_ARTIFACT,),
    TraderLabStage.OOS: (R314_FUNDING_ARTIFACT,),
    TraderLabStage.MONTE_CARLO: (R312_RISK_ARTIFACT,),
    TraderLabStage.ECONOMIC_EVIDENCE: (R315_HOLDOUT_ARTIFACT,),
}


@dataclass(frozen=True, slots=True)
class Vt08R315ArtifactEvidence:
    """Content-derived attestation for one self-authenticating Lab stage."""

    stage: TraderLabStage
    candidate: TraderLabCandidateBinding
    artifacts: tuple[Vt08R315ImmutableArtifact, ...]
    payload_digest: str
    produced_at: datetime

    def __post_init__(self) -> None:
        if self.stage not in _ALLOWED_STAGES:
            raise TraderLabValidationError("stage is not artifact-backed in R3.15")
        if not isinstance(self.candidate, TraderLabCandidateBinding):
            raise TraderLabValidationError("artifact evidence requires candidate binding")
        if type(self.artifacts) is not tuple or not self.artifacts:
            raise TraderLabValidationError("artifact evidence requires immutable sources")
        if len({item.artifact_id for item in self.artifacts}) != len(self.artifacts):
            raise TraderLabValidationError("artifact evidence cannot duplicate artifacts")
        if self.artifacts != _ARTIFACTS_BY_STAGE[self.stage]:
            raise TraderLabValidationError(
                "stage must use the exact immutable official artifact"
            )
        if fullmatch(r"[0-9a-f]{64}", self.payload_digest) is None:
            raise TraderLabValidationError("payload digest must be SHA-256")
        if (
            type(self.produced_at) is not datetime
            or self.produced_at.tzinfo is None
            or self.produced_at.utcoffset() is None
        ):
            raise TraderLabValidationError("artifact produced_at must be timezone-aware")
        _validate_candidate(self.candidate)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.stage.value,
            self.candidate.fingerprint.value,
            tuple(item.logical_values() for item in self.artifacts),
            self.payload_digest,
            self.produced_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


def _manifest(candidate: TraderLabCandidateBinding) -> dict[str, str]:
    values: dict[str, str] = {}
    for parameter in candidate.strategy_binding.manifest.parameters:
        if parameter.name.startswith("trader."):
            if type(parameter.value) is not str:
                raise TraderLabValidationError("VT-08 trader manifest values must be strings")
            values[parameter.name] = parameter.value
    return values


def _validate_candidate(candidate: TraderLabCandidateBinding) -> None:
    values = _manifest(candidate)
    required = {
        "trader.code": "vt-08",
        "trader.methodology_id": "ttrades-h4-po3-b01",
        "trader.methodology_version": "r3.8-author-clarified-b01-v1",
        "trader.methodology_fingerprint": _EXPECTED_METHOD,
        "trader.source_contract_fingerprint": _EXPECTED_SOURCE,
        "trader.executable_version": "r3.8-b01-author-clarified-v1",
        "trader.portfolio": "B_COMBINED",
        "trader.qualified_markets": "AUDJPY,GBPJPY,GBPUSD",
        "trader.qualified_timeframes": "M15,H4",
    }
    for key, expected in required.items():
        if values.get(key) != expected:
            raise TraderLabValidationError(f"VT-08 R3.15 candidate mismatch: {key}")
    if candidate.version.value != "r3.8-b01-author-clarified-v1":
        raise TraderLabValidationError("VT-08 R3.15 candidate version mismatch")
    config = values.get("trader.config_fingerprint")
    if config is None or fullmatch(r"[0-9a-f]{64}", config) is None:
        raise TraderLabValidationError("VT-08 R3.15 config fingerprint mismatch")
    if candidate.strategy_binding.run.software_revision.value != _R315_HEAD:
        raise TraderLabValidationError("VT-08 R3.15 candidate must bind evidence HEAD")


def validate_vt08_r315_candidate(candidate: TraderLabCandidateBinding) -> None:
    """Revalidate the exact B01 portfolio candidate at an authority boundary."""

    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    _validate_candidate(candidate)


def reference_vt08_r315_artifact_evidence(
    evidence: Vt08R315ArtifactEvidence,
) -> TraderLabEvidenceReference:
    """Derive a candidate-bound self-authenticating reference from frozen sources."""

    if not isinstance(evidence, Vt08R315ArtifactEvidence):
        raise TraderLabValidationError("evidence must be Vt08R315ArtifactEvidence")
    evidence.__post_init__()
    canonical = {
        "schema": "qore.vt08.r3.15.immutable-artifact-evidence.v1",
        "values": evidence.logical_values(),
        "methodology_fingerprint": _EXPECTED_METHOD,
        "source_contract_fingerprint": _EXPECTED_SOURCE,
        "r315_evidence_head": _R315_HEAD,
        "r312_evidence_head": _R312_HEAD,
        "r314_parent_head": _R314_HEAD,
    }
    digest = TraderLabEvidenceDigest(sha256(_canonical_bytes(canonical)).hexdigest())
    reference_id = uuid5(
        NAMESPACE_URL,
        f"qore:vt08:r315:{evidence.stage.value}:{digest.value}",
    )
    return _make_self_authenticating_reference(
        kind=_KIND_BY_STAGE[evidence.stage],
        reference_id=reference_id,
        content_digest=digest,
        schema_version="qore.vt08.r3.15.artifact-attestation.v1",
        strategy_binding_fingerprint=(
            evidence.candidate.strategy_binding.binding_fingerprint.value
        ),
    )
