from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r40_nas100_short_structural_prior as mod,
)


def test_r40_preserves_owner_contract() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")


def test_r40_structural_prior_is_single_and_nonzero() -> None:
    assert mod.NAS100_SHORT_MULTIPLIER == Decimal("0.25")
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
    assert mod.NAS100_SHORT_MULTIPLIER > 0


def test_r40_keeps_r34_poi_baseline_frozen() -> None:
    assert (
        mod.BASE_POI_OVERLAY.profile_id
        == "PO-W10-N5-C0.50-WEAK0.50-T0.05"
    )
