from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.core.application import CoreApplication
from qore.infrastructure.architecture_conformance import (
    ArchitectureConformanceEvidence,
    ArchitectureConformanceVerdict,
)
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.production_readiness_evidence import (
    ProductionReadinessEvidence,
    ProductionReadinessVerdict,
)
from qore.infrastructure.release_baseline import ReleaseBaselineManifest
from qore.kernel.result import Failure, Result, Success


class QoreCoreClosureError(ExternalPortError):
    """Base error for the final QORE Core closure validation."""

    __slots__ = ()


class QoreCoreClosureValidationError(QoreCoreClosureError):
    """Violation of QORE Core closure invariants."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise QoreCoreClosureValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise QoreCoreClosureValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class QoreCoreClosureEvidence:
    core: CoreApplication
    architecture: ArchitectureConformanceEvidence
    readiness: ProductionReadinessEvidence
    baseline: ReleaseBaselineManifest
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.core, CoreApplication):
            raise QoreCoreClosureValidationError(
                "closure evidence core must be CoreApplication"
            )
        if not isinstance(self.architecture, ArchitectureConformanceEvidence):
            raise QoreCoreClosureValidationError(
                "closure evidence requires ArchitectureConformanceEvidence"
            )
        if not isinstance(self.readiness, ProductionReadinessEvidence):
            raise QoreCoreClosureValidationError(
                "closure evidence requires ProductionReadinessEvidence"
            )
        if not isinstance(self.baseline, ReleaseBaselineManifest):
            raise QoreCoreClosureValidationError(
                "closure evidence requires ReleaseBaselineManifest"
            )
        _validate_timestamp(self.evaluated_at, field_name="evaluated_at")
        if not self.architecture.passed:
            raise QoreCoreClosureValidationError(
                "closure requires architecture conformance PASS"
            )
        if not self.readiness.passed:
            raise QoreCoreClosureValidationError(
                "closure requires production readiness PASS"
            )
        if not self.baseline.passed:
            raise QoreCoreClosureValidationError(
                "closure requires release baseline PASS"
            )
        if self.baseline.architecture_verdict is not ArchitectureConformanceVerdict.PASS:
            raise QoreCoreClosureValidationError(
                "baseline architecture verdict must be PASS"
            )
        if self.baseline.readiness_verdict is not ProductionReadinessVerdict.PASS:
            raise QoreCoreClosureValidationError(
                "baseline readiness verdict must be PASS"
            )
        if self.evaluated_at < self.baseline.created_at:
            raise QoreCoreClosureValidationError(
                "closure evaluation must not predate baseline creation"
            )

    @property
    def passed(self) -> bool:
        return True

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.architecture.logical_values(),
            self.readiness.logical_values(),
            self.baseline.logical_values(),
            self.evaluated_at.isoformat(),
        )


def validate_qore_core_closure(
    core: CoreApplication,
    architecture: ArchitectureConformanceEvidence,
    readiness: ProductionReadinessEvidence,
    baseline: ReleaseBaselineManifest,
    *,
    expected_repository: str,
    expected_commit_sha: str,
    evaluated_at: datetime,
) -> Result[QoreCoreClosureEvidence, QoreCoreClosureError]:
    if not isinstance(core, CoreApplication):
        return Failure(
            QoreCoreClosureValidationError("core must be CoreApplication")
        )
    if not isinstance(architecture, ArchitectureConformanceEvidence):
        return Failure(
            QoreCoreClosureValidationError(
                "architecture must be ArchitectureConformanceEvidence"
            )
        )
    if not isinstance(readiness, ProductionReadinessEvidence):
        return Failure(
            QoreCoreClosureValidationError(
                "readiness must be ProductionReadinessEvidence"
            )
        )
    if not isinstance(baseline, ReleaseBaselineManifest):
        return Failure(
            QoreCoreClosureValidationError(
                "baseline must be ReleaseBaselineManifest"
            )
        )
    if baseline.repository != expected_repository:
        return Failure(
            QoreCoreClosureValidationError(
                "release baseline repository identity mismatch"
            )
        )
    if baseline.commit_sha != expected_commit_sha:
        return Failure(
            QoreCoreClosureValidationError(
                "release baseline commit identity mismatch"
            )
        )

    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    try:
        evidence = QoreCoreClosureEvidence(
            core=core,
            architecture=architecture,
            readiness=readiness,
            baseline=baseline,
            evaluated_at=evaluated_at,
        )
    except QoreCoreClosureError as error:
        return Failure(error)

    if core.event_bus is not event_bus:
        return Failure(
            QoreCoreClosureValidationError(
                "closure validation must preserve Core EventBus"
            )
        )
    if core.runtime_plan != runtime_plan:
        return Failure(
            QoreCoreClosureValidationError(
                "closure validation must preserve Core RuntimePlan"
            )
        )
    if core.runtime_snapshot() != runtime_snapshot:
        return Failure(
            QoreCoreClosureValidationError(
                "closure validation must preserve Core RuntimeSnapshot"
            )
        )
    if core.runtime_health() != runtime_health:
        return Failure(
            QoreCoreClosureValidationError(
                "closure validation must preserve Core RuntimeHealth"
            )
        )
    return Success(evidence)
