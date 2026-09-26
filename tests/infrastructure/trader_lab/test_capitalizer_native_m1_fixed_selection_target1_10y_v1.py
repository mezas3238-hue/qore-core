from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_native_m1_fixed_selection_target1_10y_v1 as target1,
)


def test_dense_native_m1_target1_contract_is_frozen() -> None:
    assert target1.IDENTITY == (
        "QORE_CAPITALIZER_NATIVE_M1_FIXED_SELECTION_TARGET1_10Y_V1"
    )
    assert target1.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_NATIVE_M1_FIXED_SELECTION_TARGET1_10Y_V1"
    )
    assert target1.TARGET_R == Decimal("1.00")
    assert target1.SOURCE_RUN_ID == 35548099334
    assert target1.SOURCE_SHA == (
        "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
    )
    assert target1.EXPECTED_RAW_TRADES == 21696
    assert target1.EXPECTED_SOURCE_MAX3_TRADES == 16600
