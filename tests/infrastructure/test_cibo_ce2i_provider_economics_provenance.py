from qore.infrastructure.cibo_ce2i_provider_economics_provenance import (
    PROVIDER_ECONOMICS_ARTIFACT_ID,
    PROVIDER_ECONOMICS_SYMBOLS,
    PROVIDER_ECONOMICS_WORKFLOW_RUN_ID,
    provider_economics_provenance_payload,
    provider_economics_provenance_sha256,
)


def test_provider_economics_provenance_is_current_terms_only() -> None:
    payload = provider_economics_provenance_payload()

    assert payload["workflow_run_id"] == PROVIDER_ECONOMICS_WORKFLOW_RUN_ID
    assert payload["artifact_id"] == PROVIDER_ECONOMICS_ARTIFACT_ID
    assert tuple(payload["symbols"]) == PROVIDER_ECONOMICS_SYMBOLS
    assert payload["current_provider_terms_ready"] is True
    assert payload["spread_native_ready"] is True
    assert payload["commission_native_ready"] is True
    assert payload["expected_margin_native_ready"] is True
    assert payload["slippage_empirically_calibrated"] is False
    assert payload["latency_empirically_calibrated"] is False
    assert payload["historical_2017_exact_claimed"] is False
    assert payload["execution_model_ready"] is False
    assert payload["broker_mutation_performed"] is False
    assert payload["holdout_outcomes_used"] is False
    assert payload["target_aware"] is False


def test_provider_economics_provenance_hash_is_stable() -> None:
    first = provider_economics_provenance_sha256()
    second = provider_economics_provenance_sha256()

    assert first == second
    assert len(first) == 64
