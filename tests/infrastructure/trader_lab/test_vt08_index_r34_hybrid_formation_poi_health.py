from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import (
    vt08_index_r29_candidate_freeze as r29,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r34_hybrid_formation_poi_health as mod,
)


def test_r34_preserves_owner_contract_v2() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")


def test_r34_overlay_profiles_are_strictly_positive() -> None:
    profiles = mod._profiles()
    assert profiles
    assert len(profiles) == 96
    assert all(profile.cold_multiplier > 0 for profile in profiles)
    assert all(profile.weak_multiplier > 0 for profile in profiles)


def test_r34_health_states_use_completed_history_contract() -> None:
    assert mod._health(
        (),
        minimum=5,
        cold=Decimal("0.50"),
        weak=Decimal("0.10"),
        threshold=Decimal("0"),
    ) == (Decimal("0.50"), "COLD")
    assert mod._health(
        (Decimal("-1"),) * 5,
        minimum=5,
        cold=Decimal("0.50"),
        weak=Decimal("0.10"),
        threshold=Decimal("0"),
    ) == (Decimal("0.10"), "WEAK")
    assert mod._health(
        (Decimal("1"),) * 5,
        minimum=5,
        cold=Decimal("0.50"),
        weak=Decimal("0.10"),
        threshold=Decimal("0"),
    ) == (Decimal("1"), "HEALTHY")


def test_r34_keeps_r29_frozen_structural_hierarchy() -> None:
    assert r29.QUALITY == {
        "base_weight": "0.005",
        "tier_a_weight": "1.50",
        "tier_b_weight": "0.75",
        "tier_c_weight": "0.10",
    }
    assert r29.FORMATION_HEALTH_PROFILE_ID == "FH-W6-N5-C0.005-WEAK0.05-T0.00"
