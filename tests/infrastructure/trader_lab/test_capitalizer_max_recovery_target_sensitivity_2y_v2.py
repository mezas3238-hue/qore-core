from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v2 as v2,
)


def test_target_hit_realized_r_equals_requested_target_r() -> None:
    assert v2._correct_realized_target_r(
        lifecycle_realized=Decimal("2"),
        reason="TARGET",
        target_r=Decimal("1.00"),
    ) == Decimal("1.00")
    assert v2._correct_realized_target_r(
        lifecycle_realized=Decimal("2"),
        reason="TARGET",
        target_r=Decimal("1.25"),
    ) == Decimal("1.25")
    assert v2._correct_realized_target_r(
        lifecycle_realized=Decimal("2"),
        reason="TARGET",
        target_r=Decimal("2.00"),
    ) == Decimal("2.00")
    assert v2._correct_realized_target_r(
        lifecycle_realized=Decimal("-1"),
        reason="STOP",
        target_r=Decimal("1.00"),
    ) == Decimal("-1")
    assert v2._correct_realized_target_r(
        lifecycle_realized=Decimal("0.375"),
        reason="TIME_EXIT",
        target_r=Decimal("1.00"),
    ) == Decimal("0.375")


def test_v2_declares_v1_accounting_defect() -> None:
    assert v2.V1_DEFECT == "TARGET_HIT_REALIZED_R_HARDCODED_TO_2"
    assert v2.BASELINE_TARGET_R == Decimal("2.00")
    assert Decimal("1.00") in v2.TARGET_RS
    assert Decimal("3.00") in v2.TARGET_RS
