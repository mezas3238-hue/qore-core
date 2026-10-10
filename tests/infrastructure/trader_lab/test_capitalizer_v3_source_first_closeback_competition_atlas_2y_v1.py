from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_closeback_competition_atlas_2y_v1 as atlas,
)


def test_closeback_competition_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_CLOSEBACK_COMPETITION_ATLAS_2Y_V1"
    )
    assert atlas.WAIT_MINUTES == 5
