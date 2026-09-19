from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import vt08_index_r24_open_position_pressure as mod


def test_r24_preserves_permanent_concurrent_market_contract() -> None:
    assert contract.GLOBAL_SINGLE_POSITION_RULE is False
    assert contract.CROSS_MARKET_CONCURRENCY_REQUIRED is True
    assert contract.MAX_CROSS_MARKET_CONCURRENT_POSITIONS == 3
    assert contract.VALID_SIGNAL_SUPPRESSION_DUE_TO_OTHER_MARKET_OPEN is False
    assert contract.ZERO_RISK_AS_SIGNAL_SUPPRESSION is False


def test_r24_is_bounded_to_r23_winner_and_open_pressure_only() -> None:
    assert mod.BASE_QUALITY.base_weight == Decimal("0.005")
    assert mod.BASE_QUALITY.tier_a_weight == Decimal("1.50")
    assert mod.BASE_QUALITY.tier_b_weight == Decimal("0.75")
    assert mod.BASE_QUALITY.tier_c_weight == Decimal("0.10")
    assert mod.BASE_RISK.rolling_trades == 60
    assert mod.BASE_RISK.warn_dd_r == Decimal("1.25")
    assert mod.BASE_RISK.hard_dd_r == Decimal("1.50")
    assert mod.BASE_RISK.portfolio_risk_budget_r == Decimal("0.75")


def test_r24_pressure_profiles_are_nonzero_and_preregistered() -> None:
    profiles = mod._profiles()
    assert profiles
    assert len(profiles) <= 144
    assert all(profile.live_hard_loss_r > profile.live_warn_loss_r for profile in profiles)
    assert all(profile.live_warn_multiplier > 0 for profile in profiles)
    assert all(profile.live_hard_multiplier > 0 for profile in profiles)
    assert all(profile.same_side_multiplier > 0 for profile in profiles)


def test_open_pressure_multiplier_reduces_only_when_causal_state_requires_it() -> None:
    profile = mod.OpenPressureProfile(
        live_warn_loss_r=Decimal("0.10"),
        live_warn_multiplier=Decimal("0.50"),
        live_hard_loss_r=Decimal("0.25"),
        live_hard_multiplier=Decimal("0.10"),
        same_side_multiplier=Decimal("0.50"),
    )
    assert mod._pressure_multiplier(
        open_adverse_loss_r=Decimal("0.00"),
        same_side_open_count=0,
        profile=profile,
    ) == Decimal("1")
    assert mod._pressure_multiplier(
        open_adverse_loss_r=Decimal("0.15"),
        same_side_open_count=0,
        profile=profile,
    ) == Decimal("0.50")
    assert mod._pressure_multiplier(
        open_adverse_loss_r=Decimal("0.30"),
        same_side_open_count=0,
        profile=profile,
    ) == Decimal("0.10")
    assert mod._pressure_multiplier(
        open_adverse_loss_r=Decimal("0.00"),
        same_side_open_count=1,
        profile=profile,
    ) == Decimal("0.50")
    assert mod._pressure_multiplier(
        open_adverse_loss_r=Decimal("0.30"),
        same_side_open_count=1,
        profile=profile,
    ) == Decimal("0.050")


def test_r24_final_gate_uses_six_r_on_both_conservative_stress_surfaces() -> None:
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
