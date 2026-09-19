from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import (
    vt08_index_r33_causal_poi_health_governor as mod,
)


def test_r33_preserves_density_and_stress_contract() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")


def test_r33_health_profiles_are_causal_and_positive() -> None:
    profiles = mod._profiles()
    assert profiles
    assert all(profile.base_weight > 0 for profile in profiles)
    assert all(profile.cold_multiplier > 0 for profile in profiles)
    assert all(profile.weak_multiplier > 0 for profile in profiles)
    assert mod.POI_FAMILIES == ("cisd", "fvg", "relevant-swing")


def test_health_multiplier_uses_completed_history_only_contract() -> None:
    profile = mod.PoiHealthProfile(
        base_weight=Decimal("0.10"),
        rolling_family_trades=10,
        min_observations=5,
        cold_multiplier=Decimal("0.25"),
        weak_multiplier=Decimal("0.10"),
        healthy_mean_threshold_r=Decimal("0"),
    )
    assert mod._health_multiplier((), profile=profile) == (
        Decimal("0.25"),
        "COLD",
    )
    assert mod._health_multiplier(
        (Decimal("-1"),) * 5,
        profile=profile,
    ) == (Decimal("0.10"), "WEAK")
    assert mod._health_multiplier(
        (Decimal("1"),) * 5,
        profile=profile,
    ) == (Decimal("1"), "HEALTHY")
