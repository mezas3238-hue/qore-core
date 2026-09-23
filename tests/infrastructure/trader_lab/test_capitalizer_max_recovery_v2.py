from qore.infrastructure.trader_lab import capitalizer_max_recovery_v2 as recovery


def test_max_recovery_v2_contract() -> None:
    assert recovery.IDENTITY == "QORE_CAPITALIZER_MAX_RECOVERY_V2"
    assert recovery.ARBITRATION_RAW == 854
    assert recovery.ARBITRATION_MAX3 == 841
