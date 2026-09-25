from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r28_cold_start_floor_closure as mod,
)


def test_r28_only_tests_cold_start_near_existing_floor() -> None:
    profiles = mod._profiles()
    assert len(profiles) == 4
    assert {p.rolling_tier_trades for p in profiles} == {6}
    assert {p.min_observations for p in profiles} == {5}
    assert {p.weak_multiplier for p in profiles} == {Decimal("0.05")}
    assert {p.healthy_mean_threshold_r for p in profiles} == {Decimal("0.00")}
    assert {p.cold_multiplier for p in profiles} == {
        Decimal("0.005"),
        Decimal("0.010"),
        Decimal("0.015"),
        Decimal("0.020"),
    }


def test_r28_owner_gate_is_unchanged() -> None:
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")
