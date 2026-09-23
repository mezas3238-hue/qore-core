from qore.infrastructure.trader_lab.capitalizer_v3_source_first_delta_drawdown_forensics_2y_v1 import (
    ADDED,
    EXPECTED_SOURCE_FIRST_MAX3,
    EXPECTED_SOURCE_FIRST_RAW,
    EXPECTED_V3_MAX3,
    EXPECTED_V3_RAW,
    IDENTITY,
    LOST,
    PRESERVED,
    REPLACED,
)


def test_source_first_delta_drawdown_contract_is_frozen() -> None:
    assert IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_DELTA_DRAWDOWN_FORENSICS_2Y_V1"
    )
    assert EXPECTED_V3_RAW == 475
    assert EXPECTED_SOURCE_FIRST_RAW == 1142
    assert EXPECTED_V3_MAX3 == 474
    assert EXPECTED_SOURCE_FIRST_MAX3 == 1118
    assert ADDED == "SOURCE_FIRST_ADDED"
    assert LOST == "SOURCE_FIRST_LOST"
    assert PRESERVED == "PRESERVED_SAME_MSS"
    assert REPLACED == "REPLACED_MSS"
