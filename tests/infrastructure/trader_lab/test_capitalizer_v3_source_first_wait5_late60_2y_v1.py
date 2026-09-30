from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_late60_2y_v1 as late60,
)


def test_wait5_late60_contract_is_frozen() -> None:
    assert late60.IDENTITY == "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_LATE60_2Y_V1"
    assert late60.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_LATE60_2Y_V1"
    )
    assert late60.EXTENSION_MINUTES == 60
    assert late60.EXPECTED_WAIT5_RAW == 1003
    assert late60.EXPECTED_WAIT5_MAX3 == 983
    assert late60.EXPECTED_FILL_MISS == 1091
    assert late60.EXPECTED_CLEAN_LATE == 376
    assert late60.WAIT5_PF == Decimal("1.384597543145107741177480996")
    assert late60.WAIT5_DD_R == Decimal("11.9420088471277198029814040")
