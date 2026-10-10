from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_funnel_atlas_2y_v1 as atlas,
)


def test_source_first_wait5_funnel_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_FUNNEL_ATLAS_2Y_V1"
    )
    assert atlas.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_FUNNEL_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_SOURCE_FIRST_MSS == 2692
    assert atlas.EXPECTED_WAIT5_RAW == 1003
    assert atlas.FVG_MISSING == "FVG_MISSING"
    assert atlas.NORMAL_FILL_MISSING == "NORMAL_FILL_MISSING"
    assert atlas.WAIT_STOP_INVALIDATED == "WAIT_STOP_INVALIDATED"
    assert atlas.WAIT_NO_REFILL == "WAIT_NO_REFILL"
    assert atlas.STOP_INVALID_GEOMETRY == "STOP_INVALID_GEOMETRY"
    assert atlas.EXECUTABLE == "EXECUTABLE"
