from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import (
    vt08_index_r36_causal_market_side_health as mod,
)


def test_r36_preserves_owner_density_and_risk_contract() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")


def test_r36_freezes_r35_best_hybrid_overlay_as_baseline() -> None:
    assert mod.BASE_OVERLAY.profile_id == "PO-W10-N5-C0.50-WEAK0.50-T0.05"


def test_r36_bounded_market_side_profiles_never_raise_risk() -> None:
    profiles = mod._profiles()
    assert len(profiles) == 72
    assert all(Decimal("0") < p.cold_multiplier <= Decimal("1") for p in profiles)
    assert all(Decimal("0") < p.weak_multiplier <= Decimal("1") for p in profiles)
    assert all(p.min_observations <= p.rolling_group_trades for p in profiles)
