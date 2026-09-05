"""CF-20 Functional Coordination.

One coherent faculty-bus seam so Markets / Traders / Portfolio / Economics / Quant /
Research / Core Health / Dialogue do not become isolated pseudo-CIBOs. Every
faculty contributes an immutable, attributed record; the coordinator revalidates
each nested material, preserves disagreements (never collapses them), synthesizes
evidence deterministically, and emits only RECOMMEND / REQUEST / ABSTAIN.

The coordinator grants no execution authority, mutates no code/config, and never
launders an opinion/dialogue into a formal signal, order, or Risk decision. Its
authority ceiling is exactly the shared ``CiboFunctionalAuthority`` ladder, which
has no EXECUTION/ORDER/DECISION member.
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


class CiboFacultyDomain(StrEnum):
    """Closed catalog of the CIBO functional faculties (CF-01..CF-19)."""

    FINANCIAL_WORLD_MONITORING = "financial-world-monitoring"
    MARKET_INTELLIGENCE_MESH = "market-intelligence-mesh"
    TRADER_DIRECTOR = "trader-director"
    TRADER_ACADEMY = "trader-academy"
    OPPORTUNITY_SEARCH = "opportunity-search"
    PORTFOLIO_INTELLIGENCE = "portfolio-intelligence"
    ECONOMIC_INTELLIGENCE = "economic-intelligence"
    OUTCOME_JOURNAL = "outcome-journal"
    FAILURE_INTELLIGENCE = "failure-intelligence"
    QUANTITATIVE_INTELLIGENCE = "quantitative-intelligence"
    RESEARCH_DIRECTOR = "research-director"
    RISK_AWARE_RECOMMENDATION = "risk-aware-recommendation"
    CORE_HEALTH = "core-health"
    EXECUTIVE_PLANNER = "executive-planner"
    CEO_DIALOGUE = "ceo-dialogue"
    TRADER_VOICE = "trader-voice"
    DECISION_JOURNAL = "decision-journal"
    SELF_EVALUATION = "self-evaluation"
    LEARNING = "learning"


class CiboCoordinationDisposition(StrEnum):
    """Coordinator dispositions. No execution/order/Risk decision is represented."""

    RECOMMEND = "recommend"
    REQUEST = "request"
    ABSTAIN = "abstain"


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


@dataclass(frozen=True, slots=True)
class CiboFunctionalContribution:
    """A single attributed faculty contribution into the coordination bus."""

    faculty: CiboFacultyDomain
    contribution_code: str
    subject_key: str
    authority: CiboFunctionalAuthority
    evidence: CiboFunctionalEvidence
    authored_at: datetime
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.faculty) is not CiboFacultyDomain:
            raise CiboFunctionalValidationError(
                "contribution requires exact CiboFacultyDomain"
            )
        object.__setattr__(
            self,
            "contribution_code",
            _validate_code(self.contribution_code, field_name="contribution code"),
        )
        object.__setattr__(
            self,
            "subject_key",
            _validate_code(self.subject_key, field_name="subject key"),
        )
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "contribution requires exact CiboFunctionalAuthority"
            )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "contribution requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        _validate_timestamp(self.authored_at, field_name="contribution authored_at")
        object.__setattr__(
            self,
            "provenance",
            _validate_codes(self.provenance, field_name="contribution provenance"),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.faculty.value,
            self.contribution_code,
            self.subject_key,
            self.authority.value,
            self.evidence.logical_values(),
            self.authored_at.isoformat(),
            self.provenance,
        )


def _contribution_key(
    contribution: CiboFunctionalContribution,
) -> tuple[str, str]:
    return (contribution.faculty.value, contribution.contribution_code)


def _revalidate_contribution(
    contribution: CiboFunctionalContribution,
) -> CiboFunctionalContribution:
    return CiboFunctionalContribution(
        faculty=contribution.faculty,
        contribution_code=contribution.contribution_code,
        subject_key=contribution.subject_key,
        authority=contribution.authority,
        evidence=CiboFunctionalEvidence(
            status=contribution.evidence.status,
            evidence_refs=contribution.evidence.evidence_refs,
            as_of=contribution.evidence.as_of,
            dependency_kind=contribution.evidence.dependency_kind,
            reasons=contribution.evidence.reasons,
        ),
        authored_at=contribution.authored_at,
        provenance=contribution.provenance,
    )


def _normalize_contributions(
    contributions: tuple[CiboFunctionalContribution, ...],
) -> tuple[CiboFunctionalContribution, ...]:
    """Revalidate, deduplicate, and deterministically order contributions.

    Exact duplicates collapse to one record. Two distinct contributions sharing
    the same (faculty, code) key are a malformed input: the caller must keep each
    faculty/code conclusion unique rather than silently overwriting one.
    """
    if not isinstance(contributions, tuple) or any(
        not isinstance(item, CiboFunctionalContribution) for item in contributions
    ):
        raise CiboFunctionalValidationError(
            "contributions must be a tuple of CiboFunctionalContribution"
        )
    revalidated = tuple(
        _revalidate_contribution(item) for item in contributions
    )
    by_key: dict[tuple[str, str], CiboFunctionalContribution] = {}
    for contribution in revalidated:
        key = _contribution_key(contribution)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = contribution
        elif existing.logical_values() != contribution.logical_values():
            raise CiboFunctionalValidationError(
                f"duplicate faculty/code {key!r} with differing material"
            )
    return tuple(sorted(by_key.values(), key=_contribution_key))


@dataclass(frozen=True, slots=True)
class CiboFunctionalDisagreement:
    """A preserved disagreement: distinct conclusions on the same subject.

    The coordinator never picks a side; it records the disagreeing faculties,
    their distinct conclusion codes, and the synthesized evidence verbatim.
    """

    subject_key: str
    faculties: tuple[CiboFacultyDomain, ...]
    conclusion_codes: tuple[str, ...]
    evidence: CiboFunctionalEvidence
    detected_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject_key",
            _validate_code(self.subject_key, field_name="disagreement subject key"),
        )
        if not isinstance(self.faculties, tuple) or not self.faculties or any(
            type(faculty) is not CiboFacultyDomain for faculty in self.faculties
        ):
            raise CiboFunctionalValidationError(
                "disagreement requires a non-empty tuple of exact CiboFacultyDomain"
            )
        if len(set(self.faculties)) != len(self.faculties):
            raise CiboFunctionalValidationError(
                "disagreement faculties must be distinct; duplicate faculties are rejected"
            )
        object.__setattr__(
            self,
            "faculties",
            tuple(sorted(self.faculties, key=lambda faculty: faculty.value)),
        )
        object.__setattr__(
            self,
            "conclusion_codes",
            _validate_codes(self.conclusion_codes, field_name="conclusion codes"),
        )
        if len(self.conclusion_codes) < 2:
            raise CiboFunctionalValidationError(
                "a disagreement requires at least two distinct conclusions"
            )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "disagreement requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        _validate_timestamp(self.detected_at, field_name="disagreement detected_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.subject_key,
            tuple(faculty.value for faculty in self.faculties),
            self.conclusion_codes,
            self.evidence.logical_values(),
            self.detected_at.isoformat(),
        )


def _detect_disagreements(
    contributions: tuple[CiboFunctionalContribution, ...],
    *,
    detected_at: datetime,
) -> tuple[CiboFunctionalDisagreement, ...]:
    grouped: dict[str, list[CiboFunctionalContribution]] = {}
    for contribution in contributions:
        grouped.setdefault(contribution.subject_key, []).append(contribution)
    disagreements: list[CiboFunctionalDisagreement] = []
    for subject_key in sorted(grouped):
        members = grouped[subject_key]
        conclusion_codes = {member.contribution_code for member in members}
        if len(conclusion_codes) < 2:
            continue
        evidence = synthesize_evidence(
            tuple(member.evidence for member in members),
            as_of=detected_at,
        )
        disagreements.append(
            CiboFunctionalDisagreement(
                subject_key=subject_key,
                faculties=tuple(
                    sorted({member.faculty for member in members}, key=lambda f: f.value)
                ),
                conclusion_codes=tuple(sorted(conclusion_codes)),
                evidence=evidence,
                detected_at=detected_at,
            )
        )
    return tuple(disagreements)


_DISPOSITION_AUTHORITY: dict[CiboCoordinationDisposition, CiboFunctionalAuthority] = {
    CiboCoordinationDisposition.RECOMMEND: CiboFunctionalAuthority.RECOMMENDATION,
    CiboCoordinationDisposition.REQUEST: CiboFunctionalAuthority.REQUEST,
    CiboCoordinationDisposition.ABSTAIN: CiboFunctionalAuthority.ABSTENTION,
}


@dataclass(frozen=True, slots=True)
class CiboFunctionalCoordination:
    """Immutable coordination result: typed recommendation/request/abstention only."""

    disposition: CiboCoordinationDisposition
    authority: CiboFunctionalAuthority
    contributions: tuple[CiboFunctionalContribution, ...]
    disagreements: tuple[CiboFunctionalDisagreement, ...]
    evidence: CiboFunctionalEvidence
    coordinated_at: datetime
    request_code: str | None = None

    def __post_init__(self) -> None:
        if type(self.disposition) is not CiboCoordinationDisposition:
            raise CiboFunctionalValidationError(
                "coordination requires exact CiboCoordinationDisposition"
            )
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "coordination requires exact CiboFunctionalAuthority"
            )
        if _DISPOSITION_AUTHORITY[self.disposition] is not self.authority:
            raise CiboFunctionalValidationError(
                "coordination authority must match its disposition"
            )
        object.__setattr__(
            self,
            "contributions",
            _normalize_contributions(self.contributions),
        )
        if not self.contributions:
            raise CiboFunctionalValidationError(
                "coordination requires at least one contribution"
            )
        object.__setattr__(
            self,
            "disagreements",
            _normalize_disagreements(self.disagreements),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "coordination requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        _validate_timestamp(self.coordinated_at, field_name="coordination coordinated_at")
        # Constructor/coordinator parity: the carried evidence must be exactly the
        # deterministic synthesis of the contributions' evidence, never a decoupled
        # or hand-authored value that would admit a state ``coordinate`` cannot emit.
        try:
            synthesized = synthesize_evidence(
                tuple(contribution.evidence for contribution in self.contributions),
                as_of=self.coordinated_at,
            )
        except CiboFunctionalError as error:
            raise CiboFunctionalValidationError(
                "coordination evidence must be the synthesis of its contributions"
            ) from error
        if self.evidence.logical_values() != synthesized.logical_values():
            raise CiboFunctionalValidationError(
                "coordination evidence must match the synthesis of its contributions"
            )
        if self.request_code is not None:
            object.__setattr__(
                self,
                "request_code",
                _validate_code(self.request_code, field_name="request code"),
            )
        if self.disposition is CiboCoordinationDisposition.REQUEST:
            if self.request_code is None:
                raise CiboFunctionalValidationError(
                    "request disposition requires a request code"
                )
        elif self.request_code is not None:
            raise CiboFunctionalValidationError(
                "request code is only valid for request disposition"
            )
        # Constructor/coordinator parity: direct construction must not admit a
        # stronger semantic state than ``coordinate`` would emit.
        if self.disposition is CiboCoordinationDisposition.RECOMMEND:
            if self.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    "recommend disposition requires sufficient evidence"
                )
            if self.disagreements:
                raise CiboFunctionalValidationError(
                    "recommend disposition must not carry unresolved disagreements"
                )
        elif self.disposition is CiboCoordinationDisposition.ABSTAIN:
            if (
                self.evidence.status is CiboEvidenceStatus.SUFFICIENT
                and not self.disagreements
            ):
                raise CiboFunctionalValidationError(
                    "abstain disposition must reflect non-sufficient evidence or a disagreement"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.disposition.value,
            self.authority.value,
            tuple(item.logical_values() for item in self.contributions),
            tuple(item.logical_values() for item in self.disagreements),
            self.evidence.logical_values(),
            self.coordinated_at.isoformat(),
            self.request_code,
        )


def _normalize_disagreements(
    disagreements: tuple[CiboFunctionalDisagreement, ...],
) -> tuple[CiboFunctionalDisagreement, ...]:
    if not isinstance(disagreements, tuple) or any(
        not isinstance(item, CiboFunctionalDisagreement) for item in disagreements
    ):
        raise CiboFunctionalValidationError(
            "disagreements must be a tuple of CiboFunctionalDisagreement"
        )
    revalidated = tuple(
        CiboFunctionalDisagreement(
            subject_key=item.subject_key,
            faculties=item.faculties,
            conclusion_codes=item.conclusion_codes,
            evidence=item.evidence,
            detected_at=item.detected_at,
        )
        for item in disagreements
    )
    keyed: dict[str, CiboFunctionalDisagreement] = {}
    for item in revalidated:
        existing = keyed.get(item.subject_key)
        if existing is None:
            keyed[item.subject_key] = item
        elif existing.logical_values() != item.logical_values():
            raise CiboFunctionalValidationError(
                f"differing disagreements for subject {item.subject_key!r} are rejected"
            )
    return tuple(sorted(keyed.values(), key=lambda item: item.subject_key))


def _choose_disposition(
    *,
    evidence: CiboFunctionalEvidence,
    disagreements: tuple[CiboFunctionalDisagreement, ...],
    request_code: str | None,
) -> tuple[CiboCoordinationDisposition, CiboFunctionalAuthority]:
    if request_code is not None:
        return (
            CiboCoordinationDisposition.REQUEST,
            CiboFunctionalAuthority.REQUEST,
        )
    if disagreements or evidence.status is CiboEvidenceStatus.CONTRADICTORY:
        return (
            CiboCoordinationDisposition.ABSTAIN,
            CiboFunctionalAuthority.ABSTENTION,
        )
    if evidence.status is CiboEvidenceStatus.SUFFICIENT:
        return (
            CiboCoordinationDisposition.RECOMMEND,
            CiboFunctionalAuthority.RECOMMENDATION,
        )
    return (
        CiboCoordinationDisposition.ABSTAIN,
        CiboFunctionalAuthority.ABSTENTION,
    )


@dataclass(frozen=True, slots=True)
class CiboFunctionalCoordinator:
    """Deterministic, stateless functional faculty bus.

    ``coordinate`` reduces attributed contributions to one typed coordination.
    A disagreement or non-sufficient synthesized evidence fails closed to ABSTAIN;
    an explicit request code yields REQUEST; only fully sufficient, non-conflicting
    evidence yields RECOMMEND. None of these carries execution authority.
    """

    def coordinate(
        self,
        contributions: tuple[CiboFunctionalContribution, ...],
        *,
        coordinated_at: datetime,
        request_code: str | None = None,
    ) -> Result[CiboFunctionalCoordination, CiboFunctionalError]:
        try:
            _validate_timestamp(coordinated_at, field_name="coordinated_at")
            normalized = _normalize_contributions(contributions)
            if not normalized:
                raise CiboFunctionalValidationError(
                    "coordinate requires at least one contribution"
                )
            normalized_request = (
                None
                if request_code is None
                else _validate_code(request_code, field_name="request code")
            )
            disagreements = _detect_disagreements(
                normalized,
                detected_at=coordinated_at,
            )
            evidence = synthesize_evidence(
                tuple(contribution.evidence for contribution in normalized),
                as_of=coordinated_at,
            )
            disposition, authority = _choose_disposition(
                evidence=evidence,
                disagreements=disagreements,
                request_code=normalized_request,
            )
            return Success(
                CiboFunctionalCoordination(
                    disposition=disposition,
                    authority=authority,
                    contributions=normalized,
                    disagreements=disagreements,
                    evidence=evidence,
                    coordinated_at=coordinated_at,
                    request_code=normalized_request,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)

    def logical_values(self) -> tuple[object, ...]:
        return ()
