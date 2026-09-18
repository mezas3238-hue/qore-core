from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import (
    vt08_index_r25_density_reconstitution_forensics as mod,
)


def test_owner_density_contract_v2_is_active() -> None:
    assert contract.CONTRACT_ID == "VT08_INDEX_CONCURRENT_MARKET_CONTRACT_V2"
    assert contract.FIVE_YEAR_TRADE_RANGE == (2300, 2500)
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert contract.PORTFOLIO_MAX_DRAWDOWN_R == Decimal("6")


def test_r25_is_forensics_not_candidate_selection() -> None:
    assert mod.IDENTITY == "VT08_INDEX_R25_DENSITY_RECONSTITUTION_FORENSICS_001"
    assert mod.DIAGNOSTIC_TARGETS == (
        Decimal("1.5"),
        Decimal("2.0"),
        Decimal("2.5"),
        Decimal("3.0"),
    )


def test_concurrency_contract_is_unchanged() -> None:
    assert contract.MARKETS == ("NAS100", "SP500", "US30")
    assert contract.GLOBAL_SINGLE_POSITION_RULE is False
    assert contract.CROSS_MARKET_CONCURRENCY_REQUIRED is True
    assert contract.VALID_SIGNAL_SUPPRESSION_DUE_TO_OTHER_MARKET_OPEN is False
    assert contract.ZERO_RISK_AS_SIGNAL_SUPPRESSION is False
