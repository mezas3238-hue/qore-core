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
from qore.infrastructure.core_closure_validation import (
    CoreClosureVerdict,
    validate_core_closure,
)
from qore.infrastructure.production_readiness_evidence import (
    ProductionReadinessCheck,
    ProductionReadinessEvidence,
    ProductionReadinessRecord,
    ProductionReadinessStatus,
    aggregate_production_readiness,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 10, 50, tzinfo=UTC)
_BASELINE_SHA = "22e467f8b96ae7d7e4a5aaee1c87baf9a307f61a"


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-core-closure"))
    assert isinstance(result, Success)
    return result.value


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


def test_complete_evidence_produces_exact_pass_baseline() -> None:
    result = validate_core_closure(
        _core(),
        "mezas3238-hue/qore-core",
        _BASELINE_SHA,
        _architecture(),
        _readiness(),
        baseline_created_at=_NOW + timedelta(seconds=2),
        validated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Success)
    assert result.value.passed is True
    assert result.value.verdict is CoreClosureVerdict.PASS
    assert result.value.baseline.commit_sha == _BASELINE_SHA
    assert result.value.baseline.phase_start == 1
    assert result.value.baseline.phase_end == 12


def test_failing_architecture_prevents_closure_result() -> None:
    result = validate_core_closure(
        _core(),
        "mezas3238-hue/qore-core",
        _BASELINE_SHA,
        _architecture(fail=True),
        _readiness(),
        baseline_created_at=_NOW + timedelta(seconds=2),
        validated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)


def test_failing_readiness_prevents_closure_result() -> None:
    result = validate_core_closure(
        _core(),
        "mezas3238-hue/qore-core",
        _BASELINE_SHA,
        _architecture(),
        _readiness(fail=True),
        baseline_created_at=_NOW + timedelta(seconds=2),
        validated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)


def test_invalid_commit_identity_prevents_closure() -> None:
    result = validate_core_closure(
        _core(),
        "mezas3238-hue/qore-core",
        "invalid-sha",
        _architecture(),
        _readiness(),
        baseline_created_at=_NOW + timedelta(seconds=2),
        validated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Failure)


def test_closure_cannot_predate_baseline() -> None:
    result = validate_core_closure(
        _core(),
        "mezas3238-hue/qore-core",
        _BASELINE_SHA,
        _architecture(),
        _readiness(),
        baseline_created_at=_NOW + timedelta(seconds=3),
        validated_at=_NOW + timedelta(seconds=2),
    )

    assert isinstance(result, Failure)


def test_closure_validation_preserves_core_state() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    result = validate_core_closure(
        core,
        "mezas3238-hue/qore-core",
        _BASELINE_SHA,
        _architecture(),
        _readiness(),
        baseline_created_at=_NOW + timedelta(seconds=2),
        validated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Success)
    assert result.value.core is core
    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health


def test_closure_result_exposes_no_live_or_publication_surface() -> None:
    result = validate_core_closure(
        _core(),
        "mezas3238-hue/qore-core",
        _BASELINE_SHA,
        _architecture(),
        _readiness(),
        baseline_created_at=_NOW + timedelta(seconds=2),
        validated_at=_NOW + timedelta(seconds=3),
    )

    assert isinstance(result, Success)
    assert not hasattr(result.value, "connect_broker")
    assert not hasattr(result.value, "publish_release")
    assert not hasattr(result.value, "deploy")
