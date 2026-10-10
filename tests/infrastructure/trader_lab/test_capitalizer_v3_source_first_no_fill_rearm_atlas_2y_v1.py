from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_no_fill_rearm_atlas_2y_v1 as atlas,
)


def test_no_fill_rearm_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_NO_FILL_REARM_ATLAS_2Y_V1"
    )
    assert atlas.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_NO_FILL_REARM_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_NORMAL_FILL_MISSING == 1091
    assert atlas.NORMAL_FILL_MISSING == "NORMAL_FILL_MISSING"
