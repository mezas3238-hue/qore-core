from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_fill_miss_anatomy_2y_v1 as atlas,
)


def test_fill_miss_anatomy_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_FILL_MISS_ANATOMY_2Y_V1"
    )
    assert atlas.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_FILL_MISS_ANATOMY_2Y_V1"
    )
    assert atlas.EXPECTED_FILL_MISS == 1091
    assert atlas.NO_TOUCH == "NO_FVG_TOUCH"
    assert atlas.LATE_FILL_CLEAN == "LATE_FILL_WITHIN_60M_CLEAN"
    assert atlas.LATE_FILL_AFTER_STOP == "LATE_FILL_WITHIN_60M_AFTER_STOP"
