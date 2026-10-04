from qore.infrastructure.core_stack_v2.broker_provider_mismatch_diagnostic import (
    BrokerProviderEvidence,
    BrokerProviderMismatchState,
    diagnose_broker_provider_mismatch,
)


def _evidence(**overrides: object) -> BrokerProviderEvidence:
    values: dict[str, object] = {
        "provider_state": "HEALTHY",
        "broker_state": "HEALTHY",
        "provider_catalog_matches_frozen": True,
        "provider_error_count": 0,
        "broker_error_count": 0,
        "evidence_refs": ("artifact:b18",),
    }
    values.update(overrides)
    return BrokerProviderEvidence(**values)  # type: ignore[arg-type]


def test_consistent_real_style_observation_is_consistent() -> None:
    result = diagnose_broker_provider_mismatch(_evidence())
    assert result.state is BrokerProviderMismatchState.CONSISTENT


def test_state_divergence_is_mismatch() -> None:
    result = diagnose_broker_provider_mismatch(
        _evidence(provider_state="DEGRADED")
    )
    assert result.state is BrokerProviderMismatchState.MISMATCH
    assert "PROVIDER_BROKER_STATE_DIVERGENCE" in result.reason_codes


def test_catalog_binding_drift_is_mismatch() -> None:
    result = diagnose_broker_provider_mismatch(
        _evidence(provider_catalog_matches_frozen=False)
    )
    assert result.state is BrokerProviderMismatchState.MISMATCH


def test_error_asymmetry_is_mismatch() -> None:
    result = diagnose_broker_provider_mismatch(
        _evidence(broker_error_count=1)
    )
    assert result.state is BrokerProviderMismatchState.MISMATCH


def test_incomplete_evidence_remains_unknown() -> None:
    result = diagnose_broker_provider_mismatch(
        _evidence(provider_error_count=None)
    )
    assert result.state is BrokerProviderMismatchState.UNKNOWN


def test_diagnostic_never_acquires_authority() -> None:
    result = diagnose_broker_provider_mismatch(_evidence())
    assert result.broker_mutation_authority is False
    assert result.restart_authority is False
    assert result.order_authority is False
    assert result.risk_authority is False
