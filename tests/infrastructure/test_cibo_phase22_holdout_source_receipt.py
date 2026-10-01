from qore.infrastructure.cibo_phase22_holdout_source_receipt import (
    PHASE22_HOLDOUT_SOURCE_RECEIPT,
    SOURCE_ARCHIVES,
    VT08_REQUIRED_MARKETS,
    phase22_holdout_source_receipt_payload,
)


def test_phase22_source_receipt_freezes_nine_market_archives() -> None:
    receipt = PHASE22_HOLDOUT_SOURCE_RECEIPT

    assert receipt.source_ready is True
    assert receipt.burn_clean is True
    assert len(receipt.source_archives) == 9
    assert receipt.source_archives == SOURCE_ARCHIVES
    assert set(VT08_REQUIRED_MARKETS).issubset(
        {item[0] for item in receipt.source_archives}
    )
    assert receipt.trader_outcomes_executed is False
    assert receipt.selection_outcomes_inspected is False
    assert receipt.productive_authority is False


def test_phase22_source_receipt_payload_preserves_fresh_governance() -> None:
    payload = phase22_holdout_source_receipt_payload()

    assert payload["schema"] == "qore.cibo.phase22.holdout-source-receipt.v1"
    assert payload["candidate_id"] == "CIBO_USD60_6M_HOLDOUT_2017H1_V1"
    assert payload["source_ready"] is True
    assert payload["burn_clean"] is True
    assert len(payload["source_archives"]) == 9
    assert payload["trader_outcomes_executed"] is False
    assert payload["selection_outcomes_inspected"] is False
    assert payload["productive_authority"] is False
