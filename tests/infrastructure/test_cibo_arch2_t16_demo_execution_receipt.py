from qore.infrastructure.cibo_arch2_t16_demo_execution_receipt import (
    ARTIFACT_DIGEST,
    ARTIFACT_ID,
    PAYLOAD_SHA256,
    RUN_HEAD_SHA,
    RUN_ID,
    T16_DEMO_EXECUTION_RECEIPT,
)


def test_t16_demo_execution_receipt_is_immutable_and_scope_clean() -> None:
    receipt = T16_DEMO_EXECUTION_RECEIPT
    assert RUN_ID == 36934306276
    assert len(RUN_HEAD_SHA) == 40
    assert ARTIFACT_ID == 11197137857
    assert ARTIFACT_DIGEST.startswith("sha256:")
    assert PAYLOAD_SHA256.startswith("sha256:")
    assert receipt.round_trip_count == 4
    assert receipt.required_hedges == ("US30", "US500")
    assert receipt.created_positions_closed is True
    assert receipt.realized_slippage_coverage_complete is True
    assert receipt.realized_execution_coverage_complete is True
    assert receipt.full_hedge_cost_model_ready is True
    assert dict(receipt.max_round_trip_cost_bps)["US30"] > 0
    assert dict(receipt.max_round_trip_cost_bps)["US500"] > 0
    assert receipt.holdout_outcomes_used is False
    assert receipt.vps_touched is False
    assert receipt.live_authorized is False
    assert receipt.productive_authority is False
