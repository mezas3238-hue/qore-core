from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r42_hierarchical_nas100_prior as r42,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r43_sp500_long_stability_prior as mod,
)


def test_r43_preserves_owner_contract() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")


def test_r43_sp500_long_prior_is_moderate_and_nonzero() -> None:
    assert mod.SP500_LONG_MULTIPLIER == Decimal("0.75")
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")


def test_r43_preserves_r42_nas100_hierarchy() -> None:
    assert r42.NAS100_MARKET_MULTIPLIER == Decimal("0.50")
    assert r42.NAS100_SHORT_TOTAL_MULTIPLIER == Decimal("0.25")
