from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from re import fullmatch

from qore.infrastructure.architecture_conformance import (
    ArchitectureConformanceEvidence,
    ArchitectureConformanceVerdict,
)
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.production_readiness_evidence import (
    ProductionReadinessEvidence,
    ProductionReadinessVerdict,
)
from qore.kernel.result import Failure, Result, Success


class ReleaseBaselineError(ExternalPortError):
    """Base error for the PHASE-13 release baseline manifest."""

    __slots__ = ()


class ReleaseBaselineValidationError(ReleaseBaselineError):
    """Violation of release baseline invariants."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ReleaseBaselineValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ReleaseBaselineValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_repository(value: str) -> None:
    if not isinstance(value, str) or fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value
    ) is None:
        raise ReleaseBaselineValidationError(
            "repository must use owner/name syntax"
        )


def _validate_commit_sha(value: str) -> None:
    if not isinstance(value, str) or fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ReleaseBaselineValidationError(
            "commit_sha must be an exact lowercase 40-character Git SHA"
        )


def _validate_quality_gate(value: str) -> None:
    if not isinstance(value, str) or fullmatch(r"[a-z0-9._+-]+", value) is None:
        raise ReleaseBaselineValidationError(
            "quality_gate must use canonical lowercase syntax"
        )


@dataclass(frozen=True, slots=True)
class ReleaseBaselineManifest:
    repository: str
    commit_sha: str
    phase_start: int
    phase_end: int
    quality_gate: str
    architecture_verdict: ArchitectureConformanceVerdict
    readiness_verdict: ProductionReadinessVerdict
    created_at: datetime

    def __post_init__(self) -> None:
        _validate_repository(self.repository)
        _validate_commit_sha(self.commit_sha)
        for field_name, value in (
            ("phase_start", self.phase_start),
            ("phase_end", self.phase_end),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ReleaseBaselineValidationError(
                    f"{field_name} must be an int"
                )
        if self.phase_start != 1 or self.phase_end != 12:
            raise ReleaseBaselineValidationError(
                "PHASE-13 release baseline must cover completed PHASE-01 through PHASE-12"
            )
        _validate_quality_gate(self.quality_gate)
        if self.architecture_verdict is not ArchitectureConformanceVerdict.PASS:
            raise ReleaseBaselineValidationError(
                "release baseline requires architecture conformance PASS"
            )
        if self.readiness_verdict is not ProductionReadinessVerdict.PASS:
            raise ReleaseBaselineValidationError(
                "release baseline requires production readiness PASS"
            )
        _validate_timestamp(self.created_at, field_name="created_at")

    @property
    def passed(self) -> bool:
        return True

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.repository,
            self.commit_sha,
            self.phase_start,
            self.phase_end,
            self.quality_gate,
            self.architecture_verdict.value,
            self.readiness_verdict.value,
            self.created_at.isoformat(),
        )


def build_release_baseline(
    repository: str,
    commit_sha: str,
    architecture: ArchitectureConformanceEvidence,
    readiness: ProductionReadinessEvidence,
    *,
    created_at: datetime,
    quality_gate: str = "qore-ci",
) -> Result[ReleaseBaselineManifest, ReleaseBaselineError]:
    if not isinstance(architecture, ArchitectureConformanceEvidence):
        return Failure(
            ReleaseBaselineValidationError(
                "architecture must be ArchitectureConformanceEvidence"
            )
        )
    if not isinstance(readiness, ProductionReadinessEvidence):
        return Failure(
            ReleaseBaselineValidationError(
                "readiness must be ProductionReadinessEvidence"
            )
        )
    if not architecture.passed:
        return Failure(
            ReleaseBaselineValidationError(
                "architecture conformance must pass before baseline creation"
            )
        )
    if not readiness.passed:
        return Failure(
            ReleaseBaselineValidationError(
                "production readiness must pass before baseline creation"
            )
        )
    if created_at < architecture.evaluated_at or created_at < readiness.evaluated_at:
        return Failure(
            ReleaseBaselineValidationError(
                "baseline creation must not predate evidence evaluation"
            )
        )
    try:
        return Success(
            ReleaseBaselineManifest(
                repository=repository,
                commit_sha=commit_sha,
                phase_start=1,
                phase_end=12,
                quality_gate=quality_gate,
                architecture_verdict=architecture.verdict,
                readiness_verdict=readiness.verdict,
                created_at=created_at,
            )
        )
    except ReleaseBaselineError as error:
        return Failure(error)
