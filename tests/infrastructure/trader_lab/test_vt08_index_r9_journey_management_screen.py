from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r9_journey_management_screen as mod


def test_r9_management_contract() -> None:
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600
    assert mod.RAW_PF_GOAL == Decimal("1.20")
    assert mod.RAW_DD_GOAL == Decimal("30")


def test_r9_policy_space_is_bounded() -> None:
    policies = mod._policies()
    assert len(policies) == 30
    assert {policy.target_r for policy in policies} == {
        Decimal("2.5"),
        Decimal("3.0"),
    }
    assert {policy.trail_name for policy in policies} == {
        "OFF",
        "BE050",
        "LOCK025_075",
    }
