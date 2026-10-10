from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_fvg_confirmation_lag_atlas_2y_v1 as atlas,
)


def test_fvg_confirmation_lag_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_FVG_CONFIRMATION_LAG_ATLAS_2Y_V1"
    )
    assert atlas.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
        "FVG_CONFIRMATION_LAG_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_FVG_MISSING == 322
    assert atlas.MAX_CONFIRMATION_LAG_MINUTES == 2
