from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_alternate_families_target1_1y_v1 as alternate,
)


def test_alternate_family_target1_contract_is_frozen() -> None:
    assert alternate.IDENTITY == (
        "QORE_CAPITALIZER_ALTERNATE_FAMILIES_TARGET1_1Y_V1"
    )
    assert alternate.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_ALTERNATE_FAMILIES_TARGET1_1Y_V1"
    )
    assert alternate.TARGET_R == Decimal("1.00")
    assert alternate.FAST_SOURCE_RUN_ID == 35861327955
    assert alternate.STANDARD_SOURCE_RUN_ID == 35861313294
    assert alternate.SOURCE_M1_RUN_ID == 35548099334
    assert alternate.EXPECTED_FAST_RAW == 327
    assert alternate.EXPECTED_STANDARD_RAW == 191
