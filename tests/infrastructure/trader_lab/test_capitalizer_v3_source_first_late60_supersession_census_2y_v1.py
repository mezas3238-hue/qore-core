from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_late60_supersession_census_2y_v1 as census,
)


def test_late60_supersession_census_contract_is_frozen() -> None:
    assert census.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_LATE60_SUPERSESSION_CENSUS_2Y_V1"
    )
    assert census.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
        "LATE60_SUPERSESSION_CENSUS_2Y_V1"
    )
    assert census.EXPECTED_CLEAN_LATE == 376
    assert census.NO_NEW_SWEEP == "NO_NEW_SWEEP"
    assert census.NEW_SWEEP_ONLY == "NEW_SWEEP_ONLY"
    assert census.NEW_CLOSEBACK_NO_MSS == "NEW_CLOSEBACK_NO_MSS"
    assert census.NEW_MSS == "NEW_MSS"
