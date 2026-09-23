from qore.infrastructure.trader_lab import (
    capitalizer_v3_wait5_late60_delta_forensics_2y_v1 as forensic,
)


def test_wait5_late60_delta_contract_is_frozen() -> None:
    assert forensic.IDENTITY == (
        "QORE_CAPITALIZER_V3_WAIT5_LATE60_DELTA_FORENSICS_2Y_V1"
    )
    assert forensic.EXPECTED_WAIT5_RAW == 1003
    assert forensic.EXPECTED_LATE60_RAW == 1368
    assert forensic.EXPECTED_WAIT5_MAX3 == 983
    assert forensic.EXPECTED_LATE60_MAX3 == 1327
    assert forensic.EXPECTED_LATE60_SELECTED == 354
    assert forensic.EXPECTED_WAIT5_DISPLACED == 10
