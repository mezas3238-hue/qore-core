from qore.infrastructure.cibo_arch2_t11_v3_retry_claim import (
    FAILED_RUN_ID,
    RETRY_TOKEN,
    T11_V3_TECHNICAL_RETRY_CLAIM,
)


def test_t11_v3_retry_is_single_pre_broker_technical_retry() -> None:
    claim = T11_V3_TECHNICAL_RETRY_CLAIM

    assert claim.failed_run_id == FAILED_RUN_ID == 36948338513
    assert claim.failed_before_credentials is True
    assert claim.failed_before_containment_preflight is True
    assert claim.failed_before_broker_mutation is True
    assert claim.terminal_artifact_count == 0
    assert claim.provider_outcomes_observed is False
    assert claim.provider_outcomes_consumed is False
    assert claim.retry_token == RETRY_TOKEN == "QUALITY_ONLY_R1"
    assert claim.scientific_model_changed is False
    assert claim.thresholds_changed is False
    assert claim.experiment_plan_changed is False
    assert claim.outcome_aware_change is False
    assert claim.one_retry_allowed is True
    assert claim.productive_authority is False
