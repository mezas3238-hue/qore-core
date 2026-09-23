from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait_rearm_atlas_2y_v1 as atlas,
)


def test_wait_rearm_atlas_contract_is_frozen() -> None:
    assert atlas.IDENTITY == "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT_REARM_ATLAS_2Y_V1"
    assert atlas.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT_REARM_ATLAS_2Y_V1"
    )
    assert atlas.WAIT_MINUTES == 5
    assert atlas.EXPECTED_STALE_WAIT5_RAW == 199
