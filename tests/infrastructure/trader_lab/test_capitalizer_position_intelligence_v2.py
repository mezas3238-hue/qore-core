from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_position_intelligence import (
    CapitalizerOpenPositionState,
    CapitalizerPositionAction,
    CapitalizerPositionBoundaryState,
    assess_position_boundary,
    reason_open_position,
)


def test_position_intelligence_preserves_hold_protect_exit_base() -> None:
    hold = reason_open_position(
        CapitalizerOpenPositionState(
            hypothesis_id="H-1",
            source_event_id="SRC-1",
            invalidated=False,
            destination_reached=False,
            structural_protection_available=False,
        )
    )
    protect = reason_open_position(
        CapitalizerOpenPositionState(
            hypothesis_id="H-2",
            source_event_id="SRC-2",
            invalidated=False,
            destination_reached=True,
            structural_protection_available=True,
        )
    )
    exit_ = reason_open_position(
        CapitalizerOpenPositionState(
            hypothesis_id="H-3",
            source_event_id="SRC-3",
            invalidated=True,
            destination_reached=False,
            structural_protection_available=False,
        )
    )

    assert hold.action is CapitalizerPositionAction.HOLD
    assert protect.action is CapitalizerPositionAction.PROTECT
    assert exit_.action is CapitalizerPositionAction.EXIT


def test_long_stop_can_improve_or_hold_but_cannot_widen() -> None:
    improved = CapitalizerPositionBoundaryState(
        side=CapitalizerSide.LONG,
        entry_price=Decimal("100"),
        original_stop_price=Decimal("99"),
        current_stop_price=Decimal("99.5"),
        original_target_price=Decimal("103"),
        current_target_price=Decimal("103"),
    )
    held = CapitalizerPositionBoundaryState(
        side=CapitalizerSide.LONG,
        entry_price=Decimal("100"),
        original_stop_price=Decimal("99"),
        current_stop_price=Decimal("99"),
        original_target_price=Decimal("103"),
        current_target_price=Decimal("103"),
    )

    assert assess_position_boundary(improved).stop_monotonic is True
    assert assess_position_boundary(held).stop_monotonic is True

    with pytest.raises(ValueError, match="cannot widen"):
        CapitalizerPositionBoundaryState(
            side=CapitalizerSide.LONG,
            entry_price=Decimal("100"),
            original_stop_price=Decimal("99"),
            current_stop_price=Decimal("98.5"),
            original_target_price=Decimal("103"),
            current_target_price=Decimal("103"),
        )


def test_short_stop_can_improve_or_hold_but_cannot_widen() -> None:
    improved = CapitalizerPositionBoundaryState(
        side=CapitalizerSide.SHORT,
        entry_price=Decimal("100"),
        original_stop_price=Decimal("101"),
        current_stop_price=Decimal("100.5"),
        original_target_price=Decimal("97"),
        current_target_price=Decimal("97"),
    )
    assert assess_position_boundary(improved).stop_monotonic is True

    with pytest.raises(ValueError, match="cannot widen"):
        CapitalizerPositionBoundaryState(
            side=CapitalizerSide.SHORT,
            entry_price=Decimal("100"),
            original_stop_price=Decimal("101"),
            current_stop_price=Decimal("101.5"),
            original_target_price=Decimal("97"),
            current_target_price=Decimal("97"),
        )


def test_base_position_intelligence_cannot_mutate_target_or_freeze_advanced_policies() -> None:
    with pytest.raises(ValueError, match="cannot mutate target"):
        CapitalizerPositionBoundaryState(
            side=CapitalizerSide.LONG,
            entry_price=Decimal("100"),
            original_stop_price=Decimal("99"),
            current_stop_price=Decimal("99.5"),
            original_target_price=Decimal("103"),
            current_target_price=Decimal("104"),
        )

    assessment = assess_position_boundary(
        CapitalizerPositionBoundaryState(
            side=CapitalizerSide.LONG,
            entry_price=Decimal("100"),
            original_stop_price=Decimal("99"),
            current_stop_price=Decimal("99.5"),
            original_target_price=Decimal("103"),
            current_target_price=Decimal("103"),
        )
    )
    assert assessment.break_even_policy_frozen is False
    assert assessment.trailing_stop_policy_frozen is False
    assert assessment.trailing_target_policy_frozen is False
    assert assessment.zig_zig_policy_frozen is False
    assert assessment.grants_reentry is False
    assert assessment.grants_capital_authority is False
