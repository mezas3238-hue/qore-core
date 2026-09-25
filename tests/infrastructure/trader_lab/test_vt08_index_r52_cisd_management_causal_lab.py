from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r52_cisd_management_causal_lab as r52,
)


def test_r52_is_small_preregistered_causal_family() -> None:
    assert tuple(r52.CISD_POLICIES) == (
        "SOFT_050_UNTIL_MFE050",
        "NOPROGRESS_8B_MFE025",
        "BE050",
    )
    assert len(r52.CISD_POLICIES) == 3
    assert r52.BASELINE_POLICY.target_r == Decimal("2.5")


def test_r52_hypotheses_do_not_change_target() -> None:
    assert all(
        policy.target_r == Decimal("2.5")
        for policy in r52.CISD_POLICIES.values()
    )


def test_r52_policy_mechanisms_are_single_axis() -> None:
    soft = r52.CISD_POLICIES["SOFT_050_UNTIL_MFE050"]
    deadline = r52.CISD_POLICIES["NOPROGRESS_8B_MFE025"]
    be = r52.CISD_POLICIES["BE050"]
    assert soft.soft_close_loss_r == Decimal("0.5")
    assert soft.deadline_bars is None
    assert soft.trail_steps == ()
    assert deadline.soft_close_loss_r is None
    assert deadline.deadline_bars == 8
    assert deadline.trail_steps == ()
    assert be.soft_close_loss_r is None
    assert be.deadline_bars is None
    assert be.trail_steps == ((Decimal("0.5"), Decimal("0")),)
