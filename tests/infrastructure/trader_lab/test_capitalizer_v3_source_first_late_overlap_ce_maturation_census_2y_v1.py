from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_late_overlap_ce_maturation_census_2y_v1 as census,
)


def test_late_overlap_ce_maturation_contract_is_frozen() -> None:
    assert census.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_"
        "LATE_OVERLAP_CE_MATURATION_CENSUS_2Y_V1"
    )
    assert census.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
        "LATE_OVERLAP_CE_MATURATION_CENSUS_2Y_V1"
    )
    assert census.EXPECTED_CLEAN_LATE == 376
    assert census.EXTENSION_MINUTES == 60
    assert census.CE_SAME_BAR == "CE_AVAILABLE_SAME_BAR"
    assert census.CE_LATER == "CE_AVAILABLE_LATER"
    assert census.STOP_BEFORE_CE == "STOP_INVALIDATED_BEFORE_CE"
    assert census.NO_CE == "NO_CE_BEFORE_EXTENDED_DEADLINE"
