from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r43_sp500_long_stability_prior as r43
from qore.infrastructure.trader_lab import vt08_index_r44_candidate_freeze as freeze
from qore.infrastructure.trader_lab import vt08_index_r45_frozen_recent_2y_reproduction as mod


def test_r45_uses_exact_frozen_candidate() -> None:
    assert freeze.CANDIDATE_ID == "VT08_INDEX_R43_SOURCE_COMPLETE_2448_001"
    assert freeze.GOVERNANCE["two_year_retuning_permitted"] is False
    assert freeze.dependency_contract_matches() is True


def test_r45_owner_2y_contract() -> None:
    assert contract.TWO_YEAR_MIN_TRADES == 1000
    assert mod.TWO_YEAR_MIN_TRADES == 1000
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")


def test_r45_frozen_structural_priors_match_r43() -> None:
    assert freeze.STRUCTURAL_PRIORS["nas100_market_multiplier"] == "0.50"
    assert freeze.STRUCTURAL_PRIORS["nas100_short_extra_multiplier"] == "0.50"
    assert freeze.STRUCTURAL_PRIORS["nas100_short_total_multiplier"] == "0.2500"
    assert freeze.STRUCTURAL_PRIORS["sp500_long_multiplier"] == str(
        r43.SP500_LONG_MULTIPLIER
    )


def test_r45_window_is_two_full_years() -> None:
    assert mod.START_DATE.isoformat() == "2024-09-15"
    assert mod.END_DATE_EXCLUSIVE.isoformat() == "2026-09-15"
