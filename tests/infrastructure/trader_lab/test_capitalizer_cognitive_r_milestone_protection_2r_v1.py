from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as lab,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide


def test_staged_protection_is_monotonic_in_milestone() -> None:
    mode = lab.ProtectionMode.STAGED_050_100_150
    assert lab._desired_lock(mode, Decimal("0.49")) is None
    assert lab._desired_lock(mode, Decimal("0.50")) == Decimal("0")
    assert lab._desired_lock(mode, Decimal("1.00")) == Decimal("0.25")
    assert lab._desired_lock(mode, Decimal("1.50")) == Decimal("0.75")


def test_long_stop_improvement_cannot_widen() -> None:
    assert lab._is_improvement(
        side=CapitalizerSide.LONG,
        candidate=Decimal("100"),
        active=Decimal("99"),
    )
    assert not lab._is_improvement(
        side=CapitalizerSide.LONG,
        candidate=Decimal("98"),
        active=Decimal("99"),
    )


def test_short_stop_improvement_cannot_widen() -> None:
    assert lab._is_improvement(
        side=CapitalizerSide.SHORT,
        candidate=Decimal("100"),
        active=Decimal("101"),
    )
    assert not lab._is_improvement(
        side=CapitalizerSide.SHORT,
        candidate=Decimal("102"),
        active=Decimal("101"),
    )
