from qore.infrastructure.trader_lab.capitalizer_v3_step4_trade_delta_provenance_2y_v1 import (
    EXPECTED_STEP4_MAX3,
    EXPECTED_STEP4_RAW,
    EXPECTED_V3_MAX3,
    EXPECTED_V3_RAW,
    IDENTITY,
)


def test_trade_delta_provenance_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_STEP4_TRADE_DELTA_PROVENANCE_2Y_V1"
    assert EXPECTED_V3_RAW == 475
    assert EXPECTED_STEP4_RAW == 495
    assert EXPECTED_V3_MAX3 == 474
    assert EXPECTED_STEP4_MAX3 == 494
