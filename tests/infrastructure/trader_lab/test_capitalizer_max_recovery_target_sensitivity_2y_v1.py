from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v1 as sensitivity,
)


def test_target_sensitivity_contract_is_frozen() -> None:
    assert sensitivity.IDENTITY == (
        "QORE_CAPITALIZER_MAX_RECOVERY_TARGET_SENSITIVITY_2Y_V1"
    )
    assert sensitivity.BASELINE_TARGET_R == Decimal("2.00")
    assert sensitivity.EXPECTED_FINAL_RAW == 963
    assert sensitivity.EXPECTED_FINAL_MAX3 == 948
    assert sensitivity.TARGET_RS == (
        Decimal("1.00"),
        Decimal("1.25"),
        Decimal("1.50"),
        Decimal("1.75"),
        Decimal("2.00"),
        Decimal("2.25"),
        Decimal("2.50"),
        Decimal("2.75"),
        Decimal("3.00"),
    )
