from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.infrastructure.architecture_conformance import (
    ArchitectureConformanceCheck,
    ArchitectureConformanceEvidence,
    ArchitectureConformanceRecord,
    ArchitectureConformanceStatus,
    aggregate_architecture_conformance,
)
from qore.infrastructure.core_closure import (
    QoreCoreClosureValidationError,
    validate_qore_core_closure,
)
from qore.infrastructure.production_readiness_evidence import (
    ProductionReadinessCheck,
    ProductionReadinessEvidence,
    ProductionReadinessRecord,
    ProductionReadinessStatus,
    aggregate_production_readiness,
)
from qore.infrastructure.release_baseline import (
    ReleaseBaselineManifest,
    build_release_baseline,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 10, 50, tzinfo=UTC)
_REPOSITORY = "mezas3238-hue/qore-core"
_COMMIT_SHA = "22e467f8b96ae7d7e4a5aaee1c87baf9a307f61a"


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-core-closure"))
    assert isinstance(result, Success)
    return result.value


def _architecture() -> ArchitectureConformanceEvidence:
    records = tuple(
        ArchitectureConformanceRecord(
            check=check,
            status=ArchitectureConformanceStatus.PASS,
            observed_at=_NOW,
            code=f"{check.value}.pass",
        )
        for check in ArchitectureConformanceCheck
    )
    result = aggregate_architecture_conformance(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    return result.value


def _readiness() -> ProductionReadinessEvidence:
    records = tuple(
        ProductionReadinessRecord(
            check=check,
            status=ProductionReadinessStatus.PASS,
            observed_at=_NOW,
            code=f"{check.value}.pass",
        )
        for check in ProductionReadinessCheck
    )
    result = aggregate_production_readiness(
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    return result.value


def _baseline() -> ReleaseBaselineManifest:
    result = build_release_baseline(
        _REPOSITORY,
        _COMMIT_SHA,
        _architecture(),
        _readiness(),
        created_at=_NOW + timedelta(seconds=2),
    )
    assert isinstance(result, Success)
    return result.value


def test_complete_closure_evidence_passes_and_preserves_core() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    result = validate_qore_core_closure(
        core,
        _architecture(),
        _readiness(),
        _baseline(),
        expected_repository=_REPOSITORY,
        expected_commit_sha=_COMMIT_SHA,
        evaluated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Success)
    assert result.value.passed is True
    assert result.value.core is core
    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health


def test_commit_identity_mismatch_fails_closed() -> None:
    result = validate_qore_core_closure(
        _core(),
        _architecture(),
        _readiness(),
        _baseline(),
        expected_repository=_REPOSITORY,
        expected_commit_sha="a" * 40,
        evaluated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, QoreCoreClosureValidationError)


def test_repository_identity_mismatch_fails_closed() -> None:
    result = validate_qore_core_closure(
        _core(),
        _architecture(),
        _readiness(),
        _baseline(),
        expected_repository="other/qore-core",
        expected_commit_sha=_COMMIT_SHA,
        evaluated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, QoreCoreClosureValidationError)


def test_closure_cannot_predate_baseline() -> None:
    result = validate_qore_core_closure(
        _core(),
        _architecture(),
        _readiness(),
        _baseline(),
        expected_repository=_REPOSITORY,
        expected_commit_sha=_COMMIT_SHA,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, QoreCoreClosureValidationError)


def test_closure_surface_exposes_no_live_execution_capability() -> None:
    result = validate_qore_core_closure(
        _core(),
        _architecture(),
        _readiness(),
        _baseline(),
        expected_repository=_REPOSITORY,
        expected_commit_sha=_COMMIT_SHA,
        evaluated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Success)
    evidence = result.value
    assert not hasattr(evidence, "connect_broker")
    assert not hasattr(evidence, "submit_order")
    assert not hasattr(evidence, "account_credentials")
