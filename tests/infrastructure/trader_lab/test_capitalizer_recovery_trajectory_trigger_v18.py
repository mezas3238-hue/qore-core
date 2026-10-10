from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_recovery_trajectory_trigger_v18 as lab,
)


def test_delay_bands_are_predeclared() -> None:
    assert lab._delay_band(Decimal("5")) == "FAST_0_5"
    assert lab._delay_band(Decimal("5.01")) == "MID_5_15"
    assert lab._delay_band(Decimal("15")) == "MID_5_15"
    assert lab._delay_band(Decimal("15.01")) == "SLOW_GT15"


def test_trigger_families_share_first_milestone() -> None:
    assert lab.FAMILIES["TRIGGER_050"][0] == Decimal("0.50")
    assert lab.FAMILIES["TRIGGER_075"][0] == Decimal("0.75")
    assert lab.FAMILIES["TRIGGER_100"][0] == Decimal("1.00")
    assert len(lab.FAMILIES["TRIGGER_100"][1]) == 3


def test_dominance_rejects_tradeoff() -> None:
    control = (Decimal("1"), Decimal("1"), Decimal("-0.2"), Decimal("0.2")) * 5
    candidate = (Decimal("1"), Decimal("1"), Decimal("-1"), Decimal("1")) * 5
    assert not lab._dominates(control, candidate, minimum=20)


def test_cell_support_is_not_sparse_single_digit() -> None:
    assert min(lab.MIN_SUPPORT.values()) >= 12
    assert list(lab.MIN_SUPPORT) == [
        "DELAY_DEST",
        "DELAY_VOL",
        "DELAY",
    ]


def test_recovery_preserves_surface_sizing_contract() -> None:
    assert lab.RECOVERY_DD == Decimal("3")
    assert lab.MAX_BASE_MULTIPLIER == Decimal("0.35")
