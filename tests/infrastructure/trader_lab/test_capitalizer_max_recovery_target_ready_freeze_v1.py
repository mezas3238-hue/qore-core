from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_ready_freeze_v1 as freeze,
)


def test_target_ready_freeze_contract() -> None:
    assert freeze.IDENTITY == "QORE_CAPITALIZER_MAX_RECOVERY_TARGET_READY_FREEZE_V1"
    assert freeze.WAIT_MINUTES == 5
