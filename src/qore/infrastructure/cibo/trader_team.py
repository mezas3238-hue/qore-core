"""CF-03/CF-16/CF-20 Dynamic Trader Team Formation (D4).

Purpose-built, temporary teams of exact-version Traders are formed around a
mission context (market / regime / instrument / problem / uncertainty / evidence
needs). Each member binds an exact trader version plus capability provenance; each
independent opinion carries a hypothesis, confidence, uncertainty, and objections;
the synthesis preserves disagreements verbatim and compares contradictory evidence
explicitly instead of silently averaging.

Reconfiguration and dissolution are first-class dispositions. No consensus or
synthesis can raise authority: a team is a REQUEST, an opinion is an OPINION, and
the synthesis is an OPINION -- never a signal, an order, a Risk decision, or a
promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    synthesize_evidence,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboSpecialtyCode,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboFunctionalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboFunctionalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


class CiboTeamNeed(StrEnum):
    """Closed catalog of purpose-built team need dimensions."""

    MARKET = "market"
    REGIME = "regime"
    INSTRUMENT = "instrument"
    PROBLEM = "problem"
    UNCERTAINTY = "uncertainty"
    EVIDENCE = "evidence"


class CiboTeamDisposition(StrEnum):
    """Team lifecycle disposition. Dissolution empties membership."""

    FORMED = "formed"
    RECONFIGURED = "reconfigured"
    DISSOLVED = "dissolved"


class CiboConfidenceLevel(StrEnum):
    """Bounded opinion confidence. No numeric averaging is performed."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _normalize_needs(values: tuple[CiboTeamNeed, ...]) -> tuple[CiboTeamNeed, ...]:
    if not isinstance(values, tuple) or not values or any(
        type(need) is not CiboTeamNeed for need in values
    ):
        raise CiboFunctionalValidationError(
            "needs must be a non-empty tuple of exact CiboTeamNeed"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError("needs must not contain duplicates")
    return tuple(sorted(values, key=lambda need: need.value))


def _identity_sort_key(identity: ResearchDecisionEvaluatorIdentity) -> tuple[str, str, str]:
    return (
        identity.family.value,
        identity.schema_version.value,
        identity.software_revision.value,
    )


def _member_key(member: CiboTraderTeamMember) -> tuple[str, str, str]:
    return _identity_sort_key(member.trader_identity)


@dataclass(frozen=True, slots=True)
class CiboTraderTeamMember:
    """Exact-version team membership bound to capability provenance."""

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    specialty: CiboSpecialtyCode
    capability_provenance: tuple[CiboEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboFunctionalValidationError(
                "team member requires ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboFunctionalValidationError(
                "team member requires CiboTraderConfigFingerprint"
            )
        if not isinstance(self.specialty, CiboSpecialtyCode):
            raise CiboFunctionalValidationError(
                "team member requires CiboSpecialtyCode"
            )
        object.__setattr__(
            self,
            "capability_provenance",
            _validate_evidence_refs(
                self.capability_provenance,
                field_name="capability provenance",
            ),
        )
        if not self.capability_provenance:
            raise CiboFunctionalValidationError(
                "team member requires non-empty capability provenance"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.specialty.logical_values(),
            tuple(item.logical_values() for item in self.capability_provenance),
        )


def _normalize_members(
    values: tuple[CiboTraderTeamMember, ...],
) -> tuple[CiboTraderTeamMember, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboTraderTeamMember) for item in values
    ):
        raise CiboFunctionalValidationError(
            "members must be a tuple of CiboTraderTeamMember"
        )
    revalidated = tuple(
        CiboTraderTeamMember(
            trader_identity=item.trader_identity,
            config_fingerprint=item.config_fingerprint,
            specialty=item.specialty,
            capability_provenance=item.capability_provenance,
        )
        for item in values
    )
    keys = tuple(
        (item.trader_identity, item.config_fingerprint) for item in revalidated
    )
    if len(set(keys)) != len(keys):
        raise CiboFunctionalValidationError(
            "team members must be unique exact versions"
        )
    return tuple(sorted(revalidated, key=_member_key))


@dataclass(frozen=True, slots=True)
class CiboTraderTeam:
    """A temporary purpose-built team of exact-version Traders (REQUEST authority)."""

    mission_code: str
    needs: tuple[CiboTeamNeed, ...]
    members: tuple[CiboTraderTeamMember, ...]
    disposition: CiboTeamDisposition
    formed_at: datetime
    provenance: tuple[str, ...]
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mission_code",
            _validate_code(self.mission_code, field_name="mission code"),
        )
        object.__setattr__(self, "needs", _normalize_needs(self.needs))
        if type(self.disposition) is not CiboTeamDisposition:
            raise CiboFunctionalValidationError(
                "team requires exact CiboTeamDisposition"
            )
        object.__setattr__(self, "members", _normalize_members(self.members))
        if self.disposition is CiboTeamDisposition.DISSOLVED:
            if self.members:
                raise CiboFunctionalValidationError(
                    "dissolved team must have no members"
                )
        elif not self.members:
            raise CiboFunctionalValidationError(
                "formed/reconfigured team requires at least one member"
            )
        _validate_timestamp(self.formed_at, field_name="team formed_at")
        object.__setattr__(
            self,
            "provenance",
            _validate_codes(self.provenance, field_name="team provenance"),
        )
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "team requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.REQUEST:
            raise CiboFunctionalValidationError(
                "team authority must be REQUEST"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mission_code,
            tuple(need.value for need in self.needs),
            tuple(item.logical_values() for item in self.members),
            self.disposition.value,
            self.formed_at.isoformat(),
            self.provenance,
            self.authority.value,
        )


def form_trader_team(
    profiles: tuple[CiboTraderCapabilityProfile, ...],
    *,
    mission_code: str,
    needs: tuple[CiboTeamNeed, ...],
    disposition: CiboTeamDisposition,
    formed_at: datetime,
    provenance: tuple[str, ...],
) -> Result[CiboTraderTeam, CiboFunctionalError]:
    """Form/reconfigure/dissolve a purpose-built team from exact-version profiles."""
    if not isinstance(profiles, tuple) or any(
        not isinstance(profile, CiboTraderCapabilityProfile) for profile in profiles
    ):
        return Failure(
            CiboFunctionalValidationError(
                "team formation requires CiboTraderCapabilityProfile members"
            )
        )
    try:
        members: list[CiboTraderTeamMember] = []
        for profile in profiles:
            CiboTraderCapabilityProfile.__post_init__(profile)
            members.append(
                CiboTraderTeamMember(
                    trader_identity=profile.trader_identity,
                    config_fingerprint=profile.config_fingerprint,
                    specialty=profile.specialty,
                    capability_provenance=tuple(
                        sorted(
                            {item.ref for item in profile.certified_lab_evidence},
                            key=lambda ref: ref.value,
                        )
                    ),
                )
            )
        return Success(
            CiboTraderTeam(
                mission_code=mission_code,
                needs=needs,
                members=tuple(members),
                disposition=disposition,
                formed_at=formed_at,
                provenance=provenance,
                authority=CiboFunctionalAuthority.REQUEST,
            )
        )
    except CiboFunctionalError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class CiboTraderTeamOpinion:
    """An independent team opinion: hypothesis, confidence, uncertainty, objections."""

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    hypothesis_code: str
    confidence: CiboConfidenceLevel
    uncertainty_codes: tuple[str, ...]
    objection_codes: tuple[str, ...]
    evidence: CiboFunctionalEvidence
    voiced_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboFunctionalValidationError(
                "team opinion requires ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboFunctionalValidationError(
                "team opinion requires CiboTraderConfigFingerprint"
            )
        object.__setattr__(
            self,
            "hypothesis_code",
            _validate_code(self.hypothesis_code, field_name="hypothesis code"),
        )
        if type(self.confidence) is not CiboConfidenceLevel:
            raise CiboFunctionalValidationError(
                "team opinion requires exact CiboConfidenceLevel"
            )
        object.__setattr__(
            self,
            "uncertainty_codes",
            _validate_codes(self.uncertainty_codes, field_name="uncertainty codes"),
        )
        object.__setattr__(
            self,
            "objection_codes",
            _validate_codes(self.objection_codes, field_name="objection codes"),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "team opinion requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        _validate_timestamp(self.voiced_at, field_name="team opinion voiced_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "team opinion requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError(
                "team opinion authority must be OPINION"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.hypothesis_code,
            self.confidence.value,
            self.uncertainty_codes,
            self.objection_codes,
            self.evidence.logical_values(),
            self.voiced_at.isoformat(),
            self.authority.value,
        )


def _normalize_opinions(
    values: tuple[CiboTraderTeamOpinion, ...],
) -> tuple[CiboTraderTeamOpinion, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboTraderTeamOpinion) for item in values
    ):
        raise CiboFunctionalValidationError(
            "opinions must be a tuple of CiboTraderTeamOpinion"
        )
    revalidated = tuple(
        CiboTraderTeamOpinion(
            trader_identity=item.trader_identity,
            config_fingerprint=item.config_fingerprint,
            hypothesis_code=item.hypothesis_code,
            confidence=item.confidence,
            uncertainty_codes=item.uncertainty_codes,
            objection_codes=item.objection_codes,
            evidence=item.evidence,
            voiced_at=item.voiced_at,
            authority=item.authority,
        )
        for item in values
    )
    keys = tuple(
        (item.trader_identity, item.config_fingerprint) for item in revalidated
    )
    if len(set(keys)) != len(keys):
        raise CiboFunctionalValidationError(
            "team opinions must be unique per exact version"
        )
    return tuple(
        sorted(revalidated, key=lambda item: _identity_sort_key(item.trader_identity))
    )


@dataclass(frozen=True, slots=True)
class CiboTraderDisagreement:
    """A preserved disagreement: distinct hypotheses on the team mission."""

    hypothesis_codes: tuple[str, ...]
    member_identities: tuple[ResearchDecisionEvaluatorIdentity, ...]
    evidence: CiboFunctionalEvidence
    detected_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "hypothesis_codes",
            _validate_codes(self.hypothesis_codes, field_name="hypothesis codes"),
        )
        if len(self.hypothesis_codes) < 2:
            raise CiboFunctionalValidationError(
                "a disagreement requires at least two distinct hypotheses"
            )
        if not isinstance(self.member_identities, tuple) or not self.member_identities:
            raise CiboFunctionalValidationError(
                "disagreement requires non-empty member identities"
            )
        if any(
            not isinstance(item, ResearchDecisionEvaluatorIdentity)
            for item in self.member_identities
        ):
            raise CiboFunctionalValidationError(
                "disagreement member identities must be ResearchDecisionEvaluatorIdentity"
            )
        if len(set(self.member_identities)) != len(self.member_identities):
            raise CiboFunctionalValidationError(
                "disagreement member identities must be distinct"
            )
        object.__setattr__(
            self,
            "member_identities",
            tuple(
                sorted(self.member_identities, key=_identity_sort_key)
            ),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "disagreement requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        _validate_timestamp(self.detected_at, field_name="disagreement detected_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.hypothesis_codes,
            tuple(item.logical_values() for item in self.member_identities),
            self.evidence.logical_values(),
            self.detected_at.isoformat(),
        )


class CiboTeamSynthesisDisposition(StrEnum):
    """Synthesis disposition. No authority increase from convergence."""

    CONVERGED = "converged"
    DIVERGED = "diverged"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"


@dataclass(frozen=True, slots=True)
class CiboTraderTeamSynthesis:
    """Preserved-opinion synthesis; disagreements are never silently averaged."""

    team: CiboTraderTeam
    opinions: tuple[CiboTraderTeamOpinion, ...]
    disagreements: tuple[CiboTraderDisagreement, ...]
    evidence: CiboFunctionalEvidence
    disposition: CiboTeamSynthesisDisposition
    synthesized_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.team, CiboTraderTeam):
            raise CiboFunctionalValidationError(
                "synthesis requires CiboTraderTeam"
            )
        CiboTraderTeam.__post_init__(self.team)
        if self.team.disposition is CiboTeamDisposition.DISSOLVED:
            raise CiboFunctionalValidationError(
                "cannot synthesize a dissolved team"
            )
        object.__setattr__(self, "opinions", _normalize_opinions(self.opinions))
        if not self.opinions:
            raise CiboFunctionalValidationError(
                "synthesis requires at least one opinion"
            )
        member_keys = {
            (member.trader_identity, member.config_fingerprint)
            for member in self.team.members
        }
        for opinion in self.opinions:
            if (opinion.trader_identity, opinion.config_fingerprint) not in member_keys:
                raise CiboFunctionalValidationError(
                    "synthesis opinion must come from a team member"
                )
        if not isinstance(self.disagreements, tuple) or any(
            not isinstance(item, CiboTraderDisagreement) for item in self.disagreements
        ):
            raise CiboFunctionalValidationError(
                "synthesis disagreements must be a tuple of CiboTraderDisagreement"
            )
        object.__setattr__(
            self,
            "disagreements",
            tuple(
                sorted(
                    {
                        CiboTraderDisagreement(
                            hypothesis_codes=item.hypothesis_codes,
                            member_identities=item.member_identities,
                            evidence=item.evidence,
                            detected_at=item.detected_at,
                        )
                        for item in self.disagreements
                    },
                    key=lambda item: item.hypothesis_codes,
                )
            ),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "synthesis requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        if type(self.disposition) is not CiboTeamSynthesisDisposition:
            raise CiboFunctionalValidationError(
                "synthesis requires exact CiboTeamSynthesisDisposition"
            )
        _validate_timestamp(self.synthesized_at, field_name="synthesis synthesized_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "synthesis requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError(
                "synthesis authority must be OPINION; consensus cannot raise authority"
            )
        # Constructor/deriver parity: the carried evidence must be the synthesis of
        # the opinions' evidence, and the disposition must match the derivation.
        try:
            synthesized = synthesize_evidence(
                tuple(opinion.evidence for opinion in self.opinions),
                as_of=self.synthesized_at,
            )
        except CiboFunctionalError as error:
            raise CiboFunctionalValidationError(
                "synthesis evidence must be the synthesis of its opinions"
            ) from error
        if self.evidence.logical_values() != synthesized.logical_values():
            raise CiboFunctionalValidationError(
                "synthesis evidence must match the synthesis of its opinions"
            )
        expected = _derive_synthesis_disposition(
            synthesized,
            self.disagreements,
        )
        if expected is not self.disposition:
            raise CiboFunctionalValidationError(
                "synthesis disposition must match the derived disposition"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.team.logical_values(),
            tuple(item.logical_values() for item in self.opinions),
            tuple(item.logical_values() for item in self.disagreements),
            self.evidence.logical_values(),
            self.disposition.value,
            self.synthesized_at.isoformat(),
            self.authority.value,
        )


def _derive_synthesis_disposition(
    evidence: CiboFunctionalEvidence,
    disagreements: tuple[CiboTraderDisagreement, ...],
) -> CiboTeamSynthesisDisposition:
    if disagreements or evidence.status is CiboEvidenceStatus.CONTRADICTORY:
        return CiboTeamSynthesisDisposition.DIVERGED
    if evidence.status is not CiboEvidenceStatus.SUFFICIENT:
        return CiboTeamSynthesisDisposition.INSUFFICIENT_EVIDENCE
    return CiboTeamSynthesisDisposition.CONVERGED


def synthesize_trader_team(
    team: CiboTraderTeam,
    opinions: tuple[CiboTraderTeamOpinion, ...],
    *,
    synthesized_at: datetime,
) -> Result[CiboTraderTeamSynthesis, CiboFunctionalError]:
    """Synthesize team opinions while preserving disagreement (never averaging)."""
    if not isinstance(team, CiboTraderTeam):
        return Failure(
            CiboFunctionalValidationError("synthesis requires CiboTraderTeam")
        )
    try:
        CiboTraderTeam.__post_init__(team)
        if team.disposition is CiboTeamDisposition.DISSOLVED:
            raise CiboFunctionalValidationError("cannot synthesize a dissolved team")
        normalized = _normalize_opinions(opinions)
        if not normalized:
            raise CiboFunctionalValidationError(
                "synthesis requires at least one opinion"
            )
        member_keys = {
            (member.trader_identity, member.config_fingerprint)
            for member in team.members
        }
        for opinion in normalized:
            if (opinion.trader_identity, opinion.config_fingerprint) not in member_keys:
                raise CiboFunctionalValidationError(
                    "synthesis opinion must come from a team member"
                )
        _validate_timestamp(synthesized_at, field_name="synthesized_at")
        hypotheses = {opinion.hypothesis_code for opinion in normalized}
        disagreements: list[CiboTraderDisagreement] = []
        if len(hypotheses) >= 2:
            disagreements.append(
                CiboTraderDisagreement(
                    hypothesis_codes=tuple(sorted(hypotheses)),
                    member_identities=tuple(
                        opinion.trader_identity for opinion in normalized
                    ),
                    evidence=synthesize_evidence(
                        tuple(opinion.evidence for opinion in normalized),
                        as_of=synthesized_at,
                    ),
                    detected_at=synthesized_at,
                )
            )
        evidence = synthesize_evidence(
            tuple(opinion.evidence for opinion in normalized),
            as_of=synthesized_at,
        )
        disposition = _derive_synthesis_disposition(
            evidence,
            tuple(disagreements),
        )
        return Success(
            CiboTraderTeamSynthesis(
                team=team,
                opinions=normalized,
                disagreements=tuple(disagreements),
                evidence=evidence,
                disposition=disposition,
                synthesized_at=synthesized_at,
                authority=CiboFunctionalAuthority.OPINION,
            )
        )
    except CiboFunctionalError as error:
        return Failure(error)


__all__ = [
    "CiboTeamNeed",
    "CiboTeamDisposition",
    "CiboConfidenceLevel",
    "CiboTraderTeamMember",
    "CiboTraderTeam",
    "form_trader_team",
    "CiboTraderTeamOpinion",
    "CiboTraderDisagreement",
    "CiboTeamSynthesisDisposition",
    "CiboTraderTeamSynthesis",
    "synthesize_trader_team",
]
