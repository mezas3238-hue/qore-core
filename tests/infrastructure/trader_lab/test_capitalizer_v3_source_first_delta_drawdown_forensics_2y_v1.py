from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_delta_drawdown_forensics_2y_v1 as atlas,
)


def test_source_first_delta_drawdown_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_DELTA_DRAWDOWN_FORENSICS_2Y_V1"
    )
    assert atlas.EXPECTED_V3_RAW == 475
    assert atlas.EXPECTED_SOURCE_FIRST_RAW == 1142
    assert atlas.EXPECTED_V3_MAX3 == 474
    assert atlas.EXPECTED_SOURCE_FIRST_MAX3 == 1118
    assert atlas.ADDED == "SOURCE_FIRST_ADDED"
    assert atlas.LOST == "SOURCE_FIRST_LOST"
    assert atlas.PRESERVED == "PRESERVED_SAME_MSS"
    assert atlas.REPLACED == "REPLACED_MSS"
