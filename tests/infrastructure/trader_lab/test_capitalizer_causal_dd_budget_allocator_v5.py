from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_causal_dd_budget_allocator_v5 as lab,
)


def test_budget_caps_new_trade_by_remaining_headroom() -> None:
    multiplier, headroom = lab._budget_multiplier(
        budget=Decimal("5.50"),
        realized_dd=Decimal("4.70"),
        active_reserved=Decimal("0.30"),
        surface_multiplier=Decimal("1"),
    )
    assert headroom == Decimal("0.50")
    assert multiplier == Decimal("0.50")


def test_surface_cap_still_applies_when_budget_has_room() -> None:
    multiplier, headroom = lab._budget_multiplier(
        budget=Decimal("5.50"),
        realized_dd=Decimal("1"),
        active_reserved=Decimal("0.50"),
        surface_multiplier=Decimal("0.35"),
    )
    assert headroom == Decimal("4.00")
    assert multiplier == Decimal("0.35")


def test_minimum_execution_r_preserves_entry_when_headroom_is_zero() -> None:
    multiplier, headroom = lab._budget_multiplier(
        budget=Decimal("5.00"),
        realized_dd=Decimal("5"),
        active_reserved=Decimal("1"),
        surface_multiplier=Decimal("0.20"),
    )
    assert headroom == Decimal("0")
    assert multiplier == lab.MIN_EXECUTION_R
