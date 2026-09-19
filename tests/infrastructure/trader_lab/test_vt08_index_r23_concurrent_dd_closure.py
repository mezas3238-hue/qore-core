from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r23_concurrent_dd_closure as mod


def test_r23_permanent_concurrency_contract() -> None:
    assert contract.GLOBAL_SINGLE_POSITION_RULE is False
    assert contract.CROSS_MARKET_CONCURRENCY_REQUIRED is True
    assert contract.MAX_CROSS_MARKET_CONCURRENT_POSITIONS == 3
    assert contract.VALID_SIGNAL_SUPPRESSION_DUE_TO_OTHER_MARKET_OPEN is False
    assert contract.ZERO_RISK_AS_SIGNAL_SUPPRESSION is False


def test_r23_hard_dd_contract_is_six_on_both_stress_surfaces() -> None:
    assert mod.PORTFOLIO_DD_MAX == Decimal("6")
    assert mod.PF_PRIMARY_MIN == Decimal("1.50")
    assert mod.PF_SECONDARY_MIN == Decimal("1.30")


def test_r23_search_uses_tighter_nonzero_caps() -> None:
    profiles = mod._risk_profiles()
    assert profiles
    caps = {profile.portfolio_risk_budget_r for profile in profiles}
    assert min(caps) == Decimal("0.40")
    assert max(caps) == Decimal("0.90")
    assert all(profile.hard_multiplier > 0 for profile in profiles)
    assert all(profile.warn_multiplier > 0 for profile in profiles)
    assert all(profile.loss_multiplier > 0 for profile in profiles)
