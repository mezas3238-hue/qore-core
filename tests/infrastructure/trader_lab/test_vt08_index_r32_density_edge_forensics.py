from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r32_density_edge_forensics as mod


def test_r32_is_forensics_only_on_contract_v2_density() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R32_DENSITY_EDGE_FORENSICS_001"
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert mod.TARGET_R == Decimal("2.5")


def test_r32_stress_surfaces_are_frozen() -> None:
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")
