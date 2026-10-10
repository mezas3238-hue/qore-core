from qore.infrastructure.trader_lab import capitalizer_max_recovery_v1 as recovery


def test_max_recovery_v1_contract() -> None:
    assert recovery.IDENTITY == "QORE_CAPITALIZER_MAX_RECOVERY_V1"
    assert recovery.BASELINE_RAW == 854
    assert recovery.BASELINE_MAX3 == 841
