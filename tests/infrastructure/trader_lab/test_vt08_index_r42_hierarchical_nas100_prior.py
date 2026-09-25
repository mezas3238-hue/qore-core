from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r42_hierarchical_nas100_prior as mod,
)


def test_r42_preserves_owner_contract() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")


def test_r42_hierarchical_prior_is_bounded_and_nonzero() -> None:
    assert mod.NAS100_MARKET_MULTIPLIER == Decimal("0.50")
    assert mod.NAS100_SHORT_EXTRA_MULTIPLIER == Decimal("0.50")
    assert mod.NAS100_SHORT_TOTAL_MULTIPLIER == Decimal("0.25")
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")


def test_r42_preserves_r40_short_total_multiplier() -> None:
    assert mod.NAS100_SHORT_TOTAL_MULTIPLIER == Decimal("0.25")
