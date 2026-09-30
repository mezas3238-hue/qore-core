from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_final_2y_v1 as recovery,
)


def test_max_recovery_final_contract_is_frozen() -> None:
    assert recovery.IDENTITY == "QORE_CAPITALIZER_MAX_RECOVERY_FINAL_2Y_V1"
    assert recovery.EXPECTED_WAIT_REJECTED == 165
    assert recovery.EXPECTED_WAIT_REARMS == 3
    assert recovery.WAIT_MINUTES == 5
