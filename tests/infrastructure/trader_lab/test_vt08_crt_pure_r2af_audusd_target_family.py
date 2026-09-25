from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    ARMS,
    EFF1_HIGH,
    EFF1_LOW,
    TARGET_MULTIPLE,
    TargetArm,
)


def test_r2af_target_family_is_frozen() -> None:
    assert ARMS == (
        TargetArm.MIDPOINT_CONTROL,
        TargetArm.FIXED_1R,
        TargetArm.FIXED_1_5R,
        TargetArm.FIXED_2R,
    )
    assert TARGET_MULTIPLE == {
        TargetArm.FIXED_1R: Decimal("1.0"),
        TargetArm.FIXED_1_5R: Decimal("1.5"),
        TargetArm.FIXED_2R: Decimal("2.0"),
    }


def test_r2af_keeps_exact_aud_regime() -> None:
    assert EFF1_LOW == Decimal("0.10")
    assert EFF1_HIGH == Decimal("0.20")
