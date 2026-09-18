from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract


def test_three_markets_are_independent_and_concurrent() -> None:
    assert contract.MARKETS == ("NAS100", "SP500", "US30")
    assert contract.MAX_ACTIVE_POSITIONS_PER_SYMBOL == 1
    assert contract.MAX_CROSS_MARKET_CONCURRENT_POSITIONS == 3
    assert contract.GLOBAL_SINGLE_POSITION_RULE is False
    assert contract.CROSS_MARKET_CONCURRENCY_REQUIRED is True
    assert contract.VALID_SIGNAL_SUPPRESSION_DUE_TO_OTHER_MARKET_OPEN is False


def test_risk_may_resize_but_not_zero_valid_cross_market_signals() -> None:
    assert contract.RISK_MAY_RESIZE_VALID_SIGNALS is True
    assert contract.ZERO_RISK_AS_SIGNAL_SUPPRESSION is False
    assert contract.SAME_TIMESTAMP_SIGNALS_MUST_SHARE_PRE_BATCH_STATE is True


def test_portfolio_drawdown_ceiling_is_six_r() -> None:
    assert contract.PORTFOLIO_MAX_DRAWDOWN_R == Decimal("6")
    assert contract.PREFERRED_PORTFOLIO_DRAWDOWN_BAND_R == (
        Decimal("5"),
        Decimal("6"),
    )


def test_density_ranges_are_architectural() -> None:
    assert contract.validates_trade_count(years=5, sample=1500)
    assert contract.validates_trade_count(years=5, sample=1600)
    assert not contract.validates_trade_count(years=5, sample=1499)
    assert contract.validates_trade_count(years=2, sample=600)
    assert contract.validates_trade_count(years=2, sample=700)


def test_contract_grants_no_live_authority() -> None:
    assert contract.LIVE_AUTHORIZED is False
    assert contract.REAL_CAPITAL_AUTHORIZED is False
    assert contract.PRODUCTION_AUTHORIZED is False
