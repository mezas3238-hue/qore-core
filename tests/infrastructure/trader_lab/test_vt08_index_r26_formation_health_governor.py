from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r26_formation_health_governor as mod


def test_r26_has_only_two_adaptive_formation_tiers() -> None:
    assert mod.ADAPTIVE_TIERS == (
        "A_FVG_H4_LATENCY_121_180",
        "B_FVG_CISD_LATENCY_4_7",
    )


def test_r26_health_is_cold_then_healthy_or_weak() -> None:
    profile = mod.FormationHealthProfile(
        rolling_tier_trades=10,
        min_observations=3,
        cold_multiplier=Decimal("0.25"),
        weak_multiplier=Decimal("0.10"),
        healthy_mean_threshold_r=Decimal("0.05"),
    )
    assert mod._health_multiplier((), profile=profile) == (
        Decimal("0.25"),
        "COLD",
    )
    assert mod._health_multiplier(
        (Decimal("-1"), Decimal("-1"), Decimal("2")),
        profile=profile,
    ) == (Decimal("0.10"), "WEAK")
    assert mod._health_multiplier(
        (Decimal("0.10"), Decimal("0.10"), Decimal("0.10")),
        profile=profile,
    ) == (Decimal("1"), "HEALTHY")


def test_r26_search_is_bounded_and_nonzero() -> None:
    profiles = mod._profiles()
    assert len(profiles) == 48
    assert all(profile.cold_multiplier > 0 for profile in profiles)
    assert all(profile.weak_multiplier > 0 for profile in profiles)
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")


def test_r26_owner_economic_gate_is_explicit() -> None:
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")
