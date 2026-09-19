from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r22_concurrent_stable_formation as mod


def test_r22_contract() -> None:
    assert mod.FIVE_YEAR_MIN_TRADES == 1500
    assert mod.FIVE_YEAR_MAX_TRADES == 1600
    assert mod.PRIMARY_PF_GOAL == Decimal("1.50")
    assert mod.PRIMARY_DD_GOAL == Decimal("6")
    assert mod.SECONDARY_PF_GOAL == Decimal("1.30")
    assert mod.SECONDARY_DD_GOAL == Decimal("8")


def test_r22_quality_profiles_are_bounded() -> None:
    profiles = mod._quality_profiles()
    assert len(profiles) == 54
    assert all(profile.base_weight > 0 for profile in profiles)
    assert all(profile.tier_a_weight >= profile.tier_b_weight for profile in profiles)


def test_r22_risk_profiles_are_bounded() -> None:
    profiles = mod._risk_profiles()
    assert len(profiles) == 648
    assert all(profile.portfolio_risk_budget_r > 0 for profile in profiles)
    assert all(profile.hard_dd_r > profile.warn_dd_r for profile in profiles)


def test_r22_batch_allocation_preserves_every_signal() -> None:
    assigned, scaled = mod._allocate_batch(
        (Decimal("1"), Decimal("1"), Decimal("1")),
        active_risk=Decimal("0.5"),
        budget=Decimal("1.5"),
    )
    assert scaled
    assert len(assigned) == 3
    assert all(value > 0 for value in assigned)


def test_r22_minimum_weight_is_nonzero() -> None:
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
