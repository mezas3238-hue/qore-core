from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_2y_v1 as wait5,
)


def test_source_first_wait5_contract_is_frozen() -> None:
    assert wait5.IDENTITY == "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_2Y_V1"
    assert wait5.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_2Y_V1"
    )
    assert wait5.WAIT_MINUTES == 5
    assert wait5.SOURCE_FIRST_BASELINE_TRADES == 1118
    assert wait5.SOURCE_FIRST_BASELINE_PF == Decimal(
        "1.245847667002435638004144440"
    )
    assert wait5.SOURCE_FIRST_BASELINE_DD_R == Decimal(
        "18.13811917508204475002954529"
    )
