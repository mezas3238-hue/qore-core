from qore.infrastructure.trader_lab.capitalizer_v3_cisd_boundary_semantics_census_2y_v1 import (
    CURRENT,
    EXPECTED_CLOSEBACKS,
    EXPECTED_V3_MSS,
    IDENTITY,
    MATRIX_IDENTITY,
    PERSISTENT_EXTREME,
    SOURCE_FIRST,
)


def test_boundary_semantics_census_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_CISD_BOUNDARY_SEMANTICS_CENSUS_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_BOUNDARY_SEMANTICS_CENSUS_2Y_V1"
    )
    assert EXPECTED_CLOSEBACKS == 8099
    assert EXPECTED_V3_MSS == 1254
    assert CURRENT == "CURRENT_V3_IMMEDIATE_EXTREME"
    assert SOURCE_FIRST == "SOURCE_FIRST_OPPOSING_OPEN"
    assert PERSISTENT_EXTREME == "PERSISTENT_EXTREME_OPEN"
