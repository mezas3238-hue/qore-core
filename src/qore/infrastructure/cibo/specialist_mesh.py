"""CF-02 Market Intelligence Mesh.

Specialist opinions are reduced into a single OPINION summary. A specialist opines
only; the mesh never launders a specialist opinion into a formal signal, order, or
recommendation -- the synthesized authority stays OPINION.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
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


class CiboSpecialistFaculty(StrEnum):
    """Closed faculty catalog for the Market Intelligence Mesh."""

    EQUITY = "equity"
    FIXED_INCOME_RATES = "fixed-income-rates"
    FX = "fx"
    FUTURES = "futures"
    OPTIONS = "options"
    VOLATILITY = "volatility"
    COMMODITIES = "commodities"
    SYNTHETIC_CROSS_ASSET = "synthetic-cross-asset"
    MACRO_REGIME = "macro-regime"
    LIQUIDITY_MICROSTRUCTURE = "liquidity-microstructure"


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


@dataclass(frozen=True, slots=True)
class CiboSpecialistOpinion:
    """A single specialist opinion; a specialist opines only (authority OPINION)."""

    faculty: CiboSpecialistFaculty
    opinion_code: str
    evidence: CiboFunctionalEvidence
    authored_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if type(self.faculty) is not CiboSpecialistFaculty:
            raise CiboFunctionalValidationError(
                "specialist opinion requires exact CiboSpecialistFaculty"
            )
        object.__setattr__(
            self,
            "opinion_code",
            _validate_code(self.opinion_code, field_name="opinion code"),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "specialist opinion requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        _validate_timestamp(self.authored_at, field_name="specialist opinion authored_at")
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError(
                "specialist opinion authority must be OPINION"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.faculty.value,
            self.opinion_code,
            self.evidence.logical_values(),
            self.authored_at.isoformat(),
            self.authority.value,
        )


def _opinion_key(opinion: CiboSpecialistOpinion) -> tuple[str, str, str]:
    return (
        opinion.faculty.value,
        opinion.opinion_code,
        opinion.authored_at.astimezone(UTC).isoformat(),
    )


def _normalize_opinions(
    opinions: tuple[CiboSpecialistOpinion, ...],
) -> tuple[CiboSpecialistOpinion, ...]:
    """Revalidate, deduplicate, and deterministically order specialist opinions."""
    if not isinstance(opinions, tuple) or any(
        not isinstance(item, CiboSpecialistOpinion) for item in opinions
    ):
        raise CiboFunctionalValidationError(
            "opinions must be a tuple of CiboSpecialistOpinion"
        )
    revalidated = tuple(
        CiboSpecialistOpinion(
            faculty=item.faculty,
            opinion_code=item.opinion_code,
            evidence=item.evidence,
            authored_at=item.authored_at,
            authority=item.authority,
        )
        for item in opinions
    )
    deduped: dict[tuple[str, str, str], CiboSpecialistOpinion] = {}
    for opinion in revalidated:
        deduped.setdefault(_opinion_key(opinion), opinion)
    return tuple(sorted(deduped.values(), key=_opinion_key))


@dataclass(frozen=True, slots=True)
class CiboSpecialistMeshSummary:
    """Immutable OPINION summary of a set of specialist opinions."""

    faculty_count: int
    opinions: tuple[CiboSpecialistOpinion, ...]
    evidence: CiboFunctionalEvidence
    authority: CiboFunctionalAuthority
    concluded_at: datetime

    def __post_init__(self) -> None:
        if type(self.faculty_count) is not int or self.faculty_count < 0:
            raise CiboFunctionalValidationError(
                "faculty_count must be a non-negative int"
            )
        object.__setattr__(self, "opinions", _normalize_opinions(self.opinions))
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "mesh summary requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.evidence)
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError(
                "mesh summary authority must be OPINION"
            )
        _validate_timestamp(self.concluded_at, field_name="mesh summary concluded_at")
        if self.faculty_count != len({opinion.faculty for opinion in self.opinions}):
            raise CiboFunctionalValidationError(
                "faculty_count must match the distinct faculties of the opinions"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.faculty_count,
            tuple(opinion.logical_values() for opinion in self.opinions),
            self.evidence.logical_values(),
            self.authority.value,
            self.concluded_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboSpecialistMesh:
    """Stateless deterministic collector of specialist opinions into one OPINION."""

    def collect(
        self,
        opinions: tuple[CiboSpecialistOpinion, ...],
        *,
        concluded_at: datetime,
    ) -> Result[CiboSpecialistMeshSummary, CiboFunctionalError]:
        """Deduplicate opinions, synthesize evidence, and stay at OPINION authority."""
        try:
            _validate_timestamp(concluded_at, field_name="concluded_at")
            normalized = _normalize_opinions(opinions)
            if not normalized:
                raise CiboFunctionalValidationError(
                    "collect requires at least one specialist opinion"
                )
            evidence = synthesize_evidence(
                tuple(opinion.evidence for opinion in normalized),
                as_of=concluded_at,
            )
            summary = CiboSpecialistMeshSummary(
                faculty_count=len({opinion.faculty for opinion in normalized}),
                opinions=normalized,
                evidence=evidence,
                authority=CiboFunctionalAuthority.OPINION,
                concluded_at=concluded_at,
            )
            return Success(summary)
        except CiboFunctionalError as error:
            return Failure(error)
