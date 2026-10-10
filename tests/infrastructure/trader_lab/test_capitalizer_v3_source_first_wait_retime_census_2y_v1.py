from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait_retime_census_2y_v1 as census,
)


def test_source_first_wait_retime_contract_is_frozen() -> None:
    assert census.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT_RETIME_CENSUS_2Y_V1"
    )
    assert census.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT_RETIME_CENSUS_2Y_V1"
    )
    assert census.WAIT_MINUTES == 5
    assert census.EXPECTED_SOURCE_FIRST_RAW == 1142
