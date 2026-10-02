from qore.infrastructure.cibo_phase22_provider_numeric_execution_receipt import (
    PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT,
    phase22_provider_numeric_execution_freeze_receipt_payload,
)


def test_provider_numeric_freeze_receipt_binds_green_preoutcome_artifact() -> None:
    receipt = PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT
    payload = phase22_provider_numeric_execution_freeze_receipt_payload()

    assert receipt.run_id == 36956504705
    assert receipt.run_head_sha == (
        "887f062f253631aad24aea1d01412e79ce46569b"
    )
    assert receipt.artifact_id == 11206475793
    assert receipt.artifact_digest.startswith("sha256:")
    assert receipt.same_account_proven is True
    assert receipt.holdout_market_data_read is False
    assert receipt.holdout_outcomes_used is False
    assert receipt.broker_mutation_performed is False
    assert receipt.productive_authority is False
    assert payload["receipt_sha256"] == receipt.fingerprint()
