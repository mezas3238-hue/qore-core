from datetime import date
from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as mod,
)


def test_r35_uses_exact_five_full_year_blocks() -> None:
    assert mod._annual_boundaries() == (
        date(2018, 9, 15),
        date(2019, 9, 15),
        date(2020, 9, 15),
        date(2021, 9, 15),
        date(2022, 9, 15),
        date(2023, 9, 15),
    )


def test_r35_preserves_owner_economic_contract() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")


def test_r35_requires_every_full_block_positive() -> None:
    blocks = {
        f"Y{i}": {"sample": 1, "total_r": "0.1"}
        for i in range(1, 6)
    }
    assert mod._all_blocks_positive(blocks) is True
    blocks["Y3"]["total_r"] = "0"
    assert mod._all_blocks_positive(blocks) is False
