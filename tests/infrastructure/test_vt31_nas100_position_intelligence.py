from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    RESEARCH_UNCALIBRATED_POLICY,
    ContextualTrailingPolicy,
    ManagementContext,
    PositionAction,
    StructuralProtectionCandidate,
    decide_structural_protection,
    structurally_rearmed,
)


def test_uncalibrated_vt31_trailing_holds_instead_of_copying_turtle_params() -> None:
    decision = decide_structural_protection(
        side="long",
        current_stop=Decimal("100"),
        target=Decimal("120"),
        context=ManagementContext.CAUTIOUS,
        swing=StructuralProtectionCandidate(
            level=Decimal("105"),
            confirmations=1,
            source="confirmed-m1-swing",
        ),
        conquered_dol=Decimal("110"),
        policy=RESEARCH_UNCALIBRATED_POLICY,
    )
    assert decision.action is PositionAction.HOLD
    assert decision.next_stop is None
    assert decision.policy_calibrated is False


def test_calibrated_policy_never_widens_stop() -> None:
    policy = ContextualTrailingPolicy(
        supportive_swing_confirmations=3,
        mixed_swing_confirmations=2,
        cautious_swing_confirmations=1,
        dol_lock_enabled=True,
    )
    decision = decide_structural_protection(
        side="long",
        current_stop=Decimal("100"),
        target=Decimal("120"),
        context=ManagementContext.CAUTIOUS,
        swing=StructuralProtectionCandidate(
            level=Decimal("99"),
            confirmations=3,
            source="confirmed-m1-swing",
        ),
        conquered_dol=None,
        policy=policy,
    )
    assert decision.action is PositionAction.HOLD
    assert decision.next_stop is None


def test_conquered_dol_can_lock_only_when_policy_enables_it() -> None:
    policy = ContextualTrailingPolicy(
        supportive_swing_confirmations=3,
        mixed_swing_confirmations=2,
        cautious_swing_confirmations=1,
        dol_lock_enabled=True,
    )
    decision = decide_structural_protection(
        side="short",
        current_stop=Decimal("120"),
        target=Decimal("90"),
        context=ManagementContext.SUPPORTIVE,
        swing=None,
        conquered_dol=Decimal("105"),
        policy=policy,
    )
    assert decision.action is PositionAction.DOL_LOCK
    assert decision.next_stop == Decimal("105")


def test_structural_rearm_requires_new_vt31_market_event() -> None:
    exit_at = 1000
    assert structurally_rearmed(
        protected_exit_at_epoch=exit_at,
        new_raid_at_epoch=1001,
        new_confirmation_at_epoch=1002,
        new_decision_at_epoch=1003,
    )
    assert not structurally_rearmed(
        protected_exit_at_epoch=exit_at,
        new_raid_at_epoch=999,
        new_confirmation_at_epoch=1002,
        new_decision_at_epoch=1003,
    )
    assert not structurally_rearmed(
        protected_exit_at_epoch=exit_at,
        new_raid_at_epoch=1001,
        new_confirmation_at_epoch=999,
        new_decision_at_epoch=1003,
    )
