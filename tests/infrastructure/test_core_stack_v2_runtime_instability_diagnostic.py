from qore.infrastructure.core_stack_v2.runtime_instability_diagnostic import (
    RuntimeInstabilityState,
    RuntimeStabilityEvidence,
    diagnose_runtime_instability,
)


def _evidence(**overrides: object) -> RuntimeStabilityEvidence:
    values: dict[str, object] = {
        "core_runtime_executed": True,
        "deterministic_rebuild": True,
        "core_system_state": "HEALTHY",
        "error_count": 0,
        "snapshot_fingerprint_sha256": "a" * 64,
        "checkpoint_fingerprint_sha256": "b" * 64,
        "evidence_refs": ("artifact:b18",),
    }
    values.update(overrides)
    return RuntimeStabilityEvidence(**values)  # type: ignore[arg-type]


def test_real_style_healthy_deterministic_runtime_is_stable() -> None:
    result = diagnose_runtime_instability(_evidence())
    assert result.state is RuntimeInstabilityState.STABLE


def test_deterministic_rebuild_drift_is_instability() -> None:
    result = diagnose_runtime_instability(
        _evidence(deterministic_rebuild=False)
    )
    assert result.state is RuntimeInstabilityState.INSTABILITY
    assert "DETERMINISTIC_REBUILD_DRIFT" in result.reason_codes


def test_runtime_errors_are_instability() -> None:
    result = diagnose_runtime_instability(_evidence(error_count=1))
    assert result.state is RuntimeInstabilityState.INSTABILITY


def test_missing_runtime_execution_is_unknown_not_stable() -> None:
    result = diagnose_runtime_instability(
        _evidence(core_runtime_executed=False)
    )
    assert result.state is RuntimeInstabilityState.UNKNOWN


def test_runtime_diagnostic_never_acquires_authority() -> None:
    result = diagnose_runtime_instability(_evidence())
    assert result.restart_authority is False
    assert result.mutation_authority is False
    assert result.execution_authority is False
    assert result.risk_authority is False
