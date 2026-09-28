from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
    provider_economics_evidence_ref,
)


def test_provider_economics_evidence_is_point_in_time_not_historical() -> None:
    evidence = CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS

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


def test_provider_economics_reference_binds_artifact_digest() -> None:
    reference = provider_economics_evidence_ref()

    assert "artifact:10974092916" in reference
    assert (
        "430e7cfce506727cc48f487c6e52bc8f800d3b80dc314cd6b47a648974c23a71"
        in reference
    )
    assert "HISTORICAL_EXACT_FALSE" in reference
