from qore.infrastructure.trader_lab import (
    vt08_index_concurrent_market_contract as contract,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r35_five_year_temporal_contract as r35,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r38_five_block_edge_forensics as mod,
)


def test_r38_preserves_density_contract() -> None:
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.validates_trade_count(years=5, sample=2448)


def test_r38_uses_exact_five_year_boundaries() -> None:
    boundaries = r35._annual_boundaries()
    assert len(boundaries) == 6
    assert boundaries[0].isoformat() == "2018-09-15"
    assert boundaries[-1].isoformat() == "2023-09-15"


def test_r38_identity_is_forensics_only() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R38_FIVE_BLOCK_EDGE_FORENSICS_001"
