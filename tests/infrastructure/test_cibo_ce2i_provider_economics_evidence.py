from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
    provider_economics_evidence_ref,
)


def test_provider_economics_evidence_is_point_in_time_not_historical() -> None:
    evidence = CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS

    assert evidence.workflow_run_id == 36810489106
    assert evidence.artifact_id == 11139835744
    assert evidence.provider_terms_ready is True
    assert evidence.slippage_empirically_calibrated is False
    assert evidence.historical_exact_claimed is False
    assert evidence.execution_model_ready is False
    assert evidence.broker_mutation_performed is False
    assert evidence.holdout_outcomes_used is False
    assert evidence.target_aware is False
    assert set(evidence.symbols) == {
        "AUDJPY",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "XAUUSD",
    }


def test_provider_economics_reference_binds_latest_verified_artifact() -> None:
    reference = provider_economics_evidence_ref()

    assert "artifact:11139835744" in reference
    assert (
        "dc9bb7a969c12fabfca4ce7ea1ca1c015298b8f3817035d39ed24597d993fa02"
        in reference
    )
    assert "HISTORICAL_EXACT_FALSE" in reference
