from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r37_integrated_market_side_budget as mod,
)


def test_r37_preserves_owner_contract() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")


def test_r37_freezes_r34_poi_baseline() -> None:
    assert (
        mod.BASE_POI_OVERLAY.profile_id
        == "PO-W10-N5-C0.50-WEAK0.50-T0.05"
    )


def test_r37_profile_grid_is_bounded_and_nonzero() -> None:
    profiles = mod._profiles()
    assert len(profiles) == 72
    assert all(
        Decimal("0") < profile.cold_multiplier <= Decimal("1")
        for profile in profiles
    )
    assert all(
        Decimal("0") < profile.weak_multiplier <= Decimal("1")
        for profile in profiles
    )
