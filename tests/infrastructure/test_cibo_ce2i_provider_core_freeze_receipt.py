from qore.infrastructure.cibo_ce2i_provider_core_freeze_receipt import (
    PROVIDER_COMPONENT_FREEZE_SHA256,
    PROVIDER_CORE_FREEZE_ARTIFACT_ID,
    PROVIDER_CORE_FREEZE_RECEIPT,
    PROVIDER_STRESS_BOUND_SHA256,
    provider_core_freeze_receipt_payload,
)


def test_provider_core_freeze_receipt_is_pre_holdout_only() -> None:
    receipt = PROVIDER_CORE_FREEZE_RECEIPT
    payload = provider_core_freeze_receipt_payload()

    assert receipt.core_pre_holdout_ready is True
    assert receipt.provider_deployment_ready is False
    assert receipt.empirical_slippage_claimed is False
    assert receipt.historical_provider_economics_claimed is False
    assert receipt.holdout_outcomes_used is False
    assert receipt.productive_authority is False
    assert payload["artifact_id"] == PROVIDER_CORE_FREEZE_ARTIFACT_ID
    assert (
        payload["provider_component_freeze_sha256"]
        == PROVIDER_COMPONENT_FREEZE_SHA256
    )
    assert (
        payload["provider_stress_bound_sha256"]
        == PROVIDER_STRESS_BOUND_SHA256
    )
