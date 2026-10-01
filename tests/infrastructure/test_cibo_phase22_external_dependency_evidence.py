from qore.infrastructure.cibo_phase22_external_dependency_evidence import (
    build_phase22_external_dependency_evidence,
)


def test_phase22_provider_dependency_is_explicit_and_holdout_stays_sealed() -> None:
    evidence = build_phase22_external_dependency_evidence()
    payload = evidence.payload()

    assert evidence.disposition == "EXTERNAL_DEPENDENCY_BLOCKED"
    assert evidence.phase20_realized_execution_economics_required is True
    assert evidence.phase20_synthetic_evidence_allowed is False
    assert evidence.phase22_synthetic_evidence_allowed is False
    assert evidence.historical_provider_economics_claimed is False
    assert evidence.provider_deployment_ready is False
    assert evidence.historical_shadow_provider_usd_imputation_allowed is False
    assert evidence.fresh_holdout_consumed is False
    assert evidence.productive_authority is False
    assert "PROVIDER_ECONOMICS" in payload["affected_arch_b_workstreams"]
    assert "T20_EMPIRICAL_RELEASE" in payload["affected_arch_b_workstreams"]
