from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_trader_v49 import (
    V49TradeDirection,
    materialize_trade_intent,
    select_portfolio_trade_intents,
)


def _opportunity(
    *,
    symbol: str,
    session: str,
    day: str,
    minute: int,
) -> V49Opportunity:
    at = f"2025-01-02T10:{minute:02d}:00+00:00"
    return V49Opportunity(
        symbol=symbol,
        session=session,
        operating_date=day,
        h1_state_direction="BULLISH",
        h1_state_from="2025-01-02T09:00:00+00:00",
        h1_state_until="2025-01-02T12:00:00+00:00",
        h1_state_basis="H1_C2",
        m15_setup_confirmed_at="2025-01-02T09:45:00+00:00",
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=at,
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )


def test_materialized_trade_uses_m1_entry_m15_stop_h1_target() -> None:
    trade = materialize_trade_intent(
        _opportunity(symbol="EURUSD", session="LONDON", day="2025-01-02", minute=5)
    )
    assert trade.direction is V49TradeDirection.LONG
    assert str(trade.entry_price) == "100"
    assert str(trade.stop_price) == "99"
    assert str(trade.target_price) == "101"
    assert trade.outcome_used is False


def test_portfolio_selection_caps_at_three_per_session_day_across_markets() -> None:
    rows = tuple(
        _opportunity(
            symbol=("EURUSD" if index % 2 == 0 else "GBPUSD"),
            session="LONDON",
            day="2025-01-02",
            minute=index,
        )
        for index in range(6)
    )
    selected = select_portfolio_trade_intents(rows)
    assert len(selected) == 3
    assert [item.symbol for item in selected] == ["EURUSD", "GBPUSD", "EURUSD"]
