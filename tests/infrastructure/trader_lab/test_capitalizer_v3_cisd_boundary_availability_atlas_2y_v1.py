from qore.infrastructure.trader_lab.capitalizer_v3_cisd_boundary_availability_atlas_2y_v1 import (
    EXPECTED_CLOSEBACKS,
    IDENTITY,
    MATRIX_IDENTITY,
)


def test_boundary_atlas_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_CISD_BOUNDARY_AVAILABILITY_ATLAS_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_CISD_BOUNDARY_AVAILABILITY_ATLAS_2Y_V1"
    )
    assert EXPECTED_CLOSEBACKS == 8099
