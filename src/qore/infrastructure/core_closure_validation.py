from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.core.application import CoreApplication
from qore.infrastructure.architecture_conformance import ArchitectureConformanceEvidence
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.production_readiness_evidence import ProductionReadinessEvidence
from qore.infrastructure.release_baseline import (
    ReleaseBaselineManifest,
    build_release_baseline,
)
from qore.kernel.result import Failure, Result, Success


class CoreClosureValidationError(ExternalPortError):
    """Violation of a PHASE-13 Core closure invariant."""

    __slots__ = ()


class CoreClosureVerdict(StrEnum):
    PASS = "pass"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CoreClosureValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CoreClosureValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CoreClosureValidationResult:
    """Immutable proof that all PHASE-13 closure prerequisites passed."""

    core: CoreApplication
    architecture: ArchitectureConformanceEvidence
    readiness: ProductionReadinessEvidence
    baseline: ReleaseBaselineManifest
    validated_at: datetime
    verdict: CoreClosureVerdict = CoreClosureVerdict.PASS

    def __post_init__(self) -> None:
        if not isinstance(self.core, CoreApplication):
            raise CoreClosureValidationError("closure core must be CoreApplication")
        if not isinstance(self.architecture, ArchitectureConformanceEvidence):
            raise CoreClosureValidationError(
                "closure architecture must be ArchitectureConformanceEvidence"
            )
        if not isinstance(self.readiness, ProductionReadinessEvidence):
            raise CoreClosureValidationError(
                "closure readiness must be ProductionReadinessEvidence"
            )
        if not isinstance(self.baseline, ReleaseBaselineManifest):
            raise CoreClosureValidationError(
                "closure baseline must be ReleaseBaselineManifest"
            )
        _validate_timestamp(self.validated_at, field_name="validated_at")
        if not self.architecture.passed:
            raise CoreClosureValidationError(
                "closure requires architecture conformance PASS"
            )
        if not self.readiness.passed:
            raise CoreClosureValidationError(
                "closure requires production readiness PASS"
            )
        if not self.baseline.passed:
            raise CoreClosureValidationError("closure requires release baseline PASS")
        if self.baseline.architecture_verdict is not self.architecture.verdict:
            raise CoreClosureValidationError(
                "closure baseline architecture verdict must match evidence"
            )
        if self.baseline.readiness_verdict is not self.readiness.verdict:
            raise CoreClosureValidationError(
                "closure baseline readiness verdict must match evidence"
            )
        if self.validated_at < self.baseline.created_at:
            raise CoreClosureValidationError(
                "closure validation must not predate release baseline"
            )
        if self.verdict is not CoreClosureVerdict.PASS:
            raise CoreClosureValidationError("closure verdict must be PASS")

    @property
    def passed(self) -> bool:
        return True

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.architecture.logical_values(),
            self.readiness.logical_values(),
            self.baseline.logical_values(),
            self.validated_at.isoformat(),
            self.verdict.value,
        )


def validate_core_closure(
    core: CoreApplication,
    repository: str,
    commit_sha: str,
    architecture: ArchitectureConformanceEvidence,
    readiness: ProductionReadinessEvidence,
    *,
    baseline_created_at: datetime,
    validated_at: datetime,
) -> Result[CoreClosureValidationResult, ExternalPortError]:
    """Build and validate a PASS-only closure proof without mutating Core."""
    if not isinstance(core, CoreApplication):
        return Failure(CoreClosureValidationError("closure core must be CoreApplication"))

    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    baseline_result = build_release_baseline(
        repository,
        commit_sha,
        architecture,
        readiness,
        created_at=baseline_created_at,
    )
    if isinstance(baseline_result, Failure):
        return Failure(baseline_result.error)

    try:
        result = CoreClosureValidationResult(
            core=core,
            architecture=architecture,
            readiness=readiness,
            baseline=baseline_result.value,
            validated_at=validated_at,
        )
    except ExternalPortError as error:
        return Failure(error)

    if core.event_bus is not event_bus:
        return Failure(CoreClosureValidationError("closure must preserve Core EventBus"))
    if core.runtime_plan != runtime_plan:
        return Failure(
            CoreClosureValidationError("closure must not mutate Core RuntimePlan")
        )
    if core.runtime_snapshot() != runtime_snapshot:
        return Failure(
            CoreClosureValidationError("closure must not mutate Core RuntimeSnapshot")
        )
    if core.runtime_health() != runtime_health:
        return Failure(
            CoreClosureValidationError("closure must not mutate Core RuntimeHealth")
        )
    return Success(result)
