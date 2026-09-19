from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as mod,
)


def test_r31_targets_owner_density_contract_v2() -> None:
    assert contract.CONTRACT_ID == "VT08_INDEX_CONCURRENT_MARKET_CONTRACT_V2"
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.TARGET_R == Decimal("2.5")


def test_r31_does_not_silently_change_permanent_symbol_concurrency() -> None:
    assert contract.MAX_ACTIVE_POSITIONS_PER_SYMBOL == 1
    assert contract.CROSS_MARKET_CONCURRENCY_REQUIRED is True
    assert mod.IDENTITY == "VT08_INDEX_R31_SOURCE_COMPLETE_STRUCTURAL_CONCURRENCY_001"


def test_r31_requires_raw_edge_in_addition_to_governed_metrics() -> None:
    assert mod.RAW_PRIMARY_PF_FLOOR == Decimal("1.00")
    assert mod.GOVERNED_PRIMARY_PF_MIN == Decimal("1.50")
    assert mod.GOVERNED_SECONDARY_PF_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")
