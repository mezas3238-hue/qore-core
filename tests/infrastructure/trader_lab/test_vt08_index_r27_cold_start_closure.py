from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r27_cold_start_closure as mod


def test_r27_only_varies_cold_start_confidence_and_minimum_observations() -> None:
    profiles = mod._profiles()
    assert len(profiles) == 8
    assert {p.rolling_tier_trades for p in profiles} == {6}
    assert {p.weak_multiplier for p in profiles} == {Decimal("0.05")}
    assert {p.healthy_mean_threshold_r for p in profiles} == {Decimal("0.00")}
    assert {p.min_observations for p in profiles} == {3, 5}
    assert {p.cold_multiplier for p in profiles} == {
        Decimal("0.025"),
        Decimal("0.050"),
        Decimal("0.075"),
        Decimal("0.100"),
    }


def test_r27_owner_gate_remains_unchanged() -> None:
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")
