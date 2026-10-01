from qore.infrastructure.cibo_phase22_provider_execution_calibration_receipt import (
    EMPIRICAL_ARTIFACT_DIGEST,
    EMPIRICAL_ARTIFACT_ID,
    EMPIRICAL_RUN_HEAD_SHA,
    EMPIRICAL_RUN_ID,
    PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT,
    POPULATION_ARTIFACT_DIGEST,
    POPULATION_ARTIFACT_ID,
    POPULATION_RUN_HEAD_SHA,
    POPULATION_RUN_ID,
    phase22_provider_execution_calibration_payload,
)


def test_phase22_provider_execution_calibration_is_exact_artifact_bound() -> None:
    receipt = PHASE22_PROVIDER_EXECUTION_CALIBRATION_RECEIPT

    assert POPULATION_RUN_ID == 36922694706
    assert POPULATION_RUN_HEAD_SHA == (
        "380a7ee726c97eef700ff31a1fa7839efd0436c9"
    )
    assert POPULATION_ARTIFACT_ID == 11192332824
    assert POPULATION_ARTIFACT_DIGEST == (
        "sha256:049da53fe89fe5e56176b5a32771be67"
        "4fafd3b94d425d4594a6a06eb149ac70"
    )
    assert EMPIRICAL_RUN_ID == 36929985176
    assert EMPIRICAL_RUN_HEAD_SHA == (
        "59a7e9bc6051883f7090193860546dcb3e1f3e74"
    )
    assert EMPIRICAL_ARTIFACT_ID == 11194919112
    assert EMPIRICAL_ARTIFACT_DIGEST == (
        "sha256:9e20c1d1486391cc1c9e70ab4fa8b9c"
        "ae7eb36bd23b8774ae70353c93a8852ab"
    )
    assert receipt.execution_population_ready is True
    assert receipt.empirical_slippage_calibrated is True
    assert receipt.execution_model_ready is True
    assert receipt.created_positions_closed is True
    assert receipt.minimum_volume_only is True
    assert receipt.empirical_observation_count == 53
    assert receipt.blockers == ()
    assert receipt.broker_mutation_performed is False
    assert receipt.holdout_outcomes_used is False
    assert receipt.historical_provider_economics_claimed is False
    assert receipt.historical_holdout_execution_claimed is False
    assert receipt.fundednext_touched is False
    assert receipt.vps_touched is False

    payload = phase22_provider_execution_calibration_payload()
    assert payload["status"] == "READY"
    assert payload["receipt_sha256"] == receipt.fingerprint()
