from qore.infrastructure.trader_lab import (
    capitalizer_v3_wait5_late60_strict_continuity_forensics_2y_v1 as forensic,
)


def test_strict_continuity_forensics_contract_is_frozen() -> None:
    assert forensic.IDENTITY == (
        "QORE_CAPITALIZER_V3_WAIT5_LATE60_STRICT_CONTINUITY_FORENSICS_2Y_V1"
    )
    assert forensic.EXPECTED_ATLAS_ROWS == 365
    assert forensic.EXPECTED_LATE_RAW == 365
    assert forensic.EXPECTED_ELIGIBLE_LATE == 57
    assert forensic.EXPECTED_WAIT5_RAW == 1003
    assert forensic.EXPECTED_WAIT5_MAX3 == 983
    assert forensic.EXPECTED_CANDIDATE_MAX3 == 1038
    assert forensic.EXPECTED_SELECTED_LATE == 56
