from qore.infrastructure.trader_lab import (
    capitalizer_v3_wait5_late60_carry_context_forensics_2y_v1 as forensic,
)


def test_late60_carry_context_contract_is_frozen() -> None:
    assert forensic.IDENTITY == (
        "QORE_CAPITALIZER_V3_WAIT5_LATE60_CARRY_CONTEXT_FORENSICS_2Y_V1"
    )
    assert forensic.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_WAIT5_LATE60_CARRY_CONTEXT_FORENSICS_2Y_V1"
    )
    assert forensic.EXPECTED_LATE_RAW == 365
    assert forensic.EXPECTED_LATE_SELECTED == 354
    assert forensic.EXTENSION_MINUTES == 60
