from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_late60_forensics_2y_v1 as forensic,
)


def test_wait5_late60_forensics_contract_is_frozen() -> None:
    assert forensic.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_LATE60_FORENSICS_2Y_V1"
    )
    assert forensic.EXPECTED_LATE60_SELECTED == 354
    assert forensic.EXPECTED_LATE60_PORTFOLIO == 1327
    assert forensic.EXPECTED_WAIT5_PORTFOLIO == 983
