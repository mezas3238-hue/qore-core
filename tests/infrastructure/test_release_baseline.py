from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.architecture_conformance import (
    ArchitectureConformanceCheck,
    ArchitectureConformanceEvidence,
    ArchitectureConformanceRecord,
    ArchitectureConformanceStatus,
    aggregate_architecture_conformance,
)
from qore.infrastructure.production_readiness_evidence import (
    ProductionReadinessCheck,
    ProductionReadinessEvidence,
    ProductionReadinessRecord,
    ProductionReadinessStatus,
    aggregate_production_readiness,
)
from qore.infrastructure.release_baseline import (
    ReleaseBaselineValidationError,
    build_release_baseline,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 10, 40, tzinfo=UTC)
_COMMIT_SHA = "753b99589ef6369f009cb52ea39615ea4035fb11"


def _architecture(*, fail: bool = False) -> ArchitectureConformanceEvidence:
    records = tuple(
        ArchitectureConformanceRecord(
            check=check,
            status=(
                ArchitectureConformanceStatus.FAIL
                if fail and check is ArchitectureConformanceCheck.CORE_ISOLATION
                else ArchitectureConformanceStatus.PASS
            ),
            observed_at=_NOW,
            code=(
                f"{check.value}.fail"
                if fail and check is ArchitectureConformanceCheck.CORE_ISOLATION
                else f"{check.value}.pass"
            ),
        )
        for check in ArchitectureConformanceCheck
    )
    result = aggregate_architecture_conformance(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    return result.value


def _readiness(*, fail: bool = False) -> ProductionReadinessEvidence:
    records = tuple(
        ProductionReadinessRecord(
            check=check,
            status=(
                ProductionReadinessStatus.FAIL
                if fail and check is ProductionReadinessCheck.SAFETY_VALIDATION
                else ProductionReadinessStatus.PASS
            ),
            observed_at=_NOW,
            code=(
                f"{check.value}.fail"
                if fail and check is ProductionReadinessCheck.SAFETY_VALIDATION
                else f"{check.value}.pass"
            ),
        )
        for check in ProductionReadinessCheck
    )
    result = aggregate_production_readiness(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    return result.value


def test_passing_evidence_builds_exact_release_baseline() -> None:
    result = build_release_baseline(
        "mezas3238-hue/qore-core",
        _COMMIT_SHA,
        _architecture(),
        _readiness(),
        created_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Success)
    assert result.value.passed is True
    assert result.value.commit_sha == _COMMIT_SHA
    assert result.value.phase_start == 1
    assert result.value.phase_end == 12
    assert result.value.quality_gate == "qore-ci"


def test_invalid_commit_sha_is_rejected() -> None:
    result = build_release_baseline(
        "mezas3238-hue/qore-core",
        "not-a-real-sha",
        _architecture(),
        _readiness(),
        created_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReleaseBaselineValidationError)


def test_failing_architecture_prevents_baseline() -> None:
    result = build_release_baseline(
        "mezas3238-hue/qore-core",
        _COMMIT_SHA,
        _architecture(fail=True),
        _readiness(),
        created_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReleaseBaselineValidationError)


def test_failing_readiness_prevents_baseline() -> None:
    result = build_release_baseline(
        "mezas3238-hue/qore-core",
        _COMMIT_SHA,
        _architecture(),
        _readiness(fail=True),
        created_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReleaseBaselineValidationError)


def test_baseline_cannot_predate_evidence() -> None:
    result = build_release_baseline(
        "mezas3238-hue/qore-core",
        _COMMIT_SHA,
        _architecture(),
        _readiness(),
        created_at=_NOW,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ReleaseBaselineValidationError)
