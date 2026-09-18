from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as mod


def test_r8_density_and_target_contract() -> None:
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600
    assert mod.TARGETS == (
        Decimal("1.5"),
        Decimal("2.0"),
        Decimal("2.5"),
        Decimal("3.0"),
    )


def test_r8_target_policy_resets_management() -> None:
    policy = mod._target_policy(Decimal("2.0"))
    assert policy.target_r == Decimal("2.0")
    assert policy.soft_close_loss_r is None
    assert policy.deadline_bars is None
    assert policy.trail_name == "OFF"
