from qore.infrastructure.trader_lab.capitalizer_human_decision_graph_v48 import V48Session
from qore.infrastructure.trader_lab.capitalizer_three_session_coverage_gate_v48 import (
    SESSION_MARKETS,
    V48_THREE_SESSION_COVERAGE_GATE,
    V48SessionMarketCoverage,
    V48ThreeSessionCoverageDecision,
    assess_three_session_coverage,
)


def _full_rows() -> tuple[V48SessionMarketCoverage, ...]:
    counts = {
        (V48Session.ASIA, "USDJPY"): 4,
        (V48Session.ASIA, "AUDJPY"): 0,
        (V48Session.ASIA, "AUDUSD"): 2,
        (V48Session.ASIA, "GBPJPY"): 0,
        (V48Session.LONDON, "EURUSD"): 3,
        (V48Session.LONDON, "GBPUSD"): 1,
        (V48Session.NEW_YORK, "XAUUSD"): 2,
        (V48Session.NEW_YORK, "USDCAD"): 0,
        (V48Session.NEW_YORK, "NAS100"): 5,
    }
    return tuple(
        V48SessionMarketCoverage(session, market, counts[(session, market)])
        for session, markets in SESSION_MARKETS.items()
        for market in markets
    )


def test_three_session_gate_requires_all_nine_markets_to_be_censused() -> None:
    result = assess_three_session_coverage(_full_rows())
    assert result.decision is V48ThreeSessionCoverageDecision.COMPLETE_PRE_ECONOMIC
    assert result.missing_market_rows == ()
    assert result.empty_sessions == ()


def test_zero_market_is_allowed_if_session_itself_has_real_opportunity() -> None:
    result = assess_three_session_coverage(_full_rows())
    totals = dict(result.session_opportunity_totals)
    assert totals[V48Session.ASIA] == 6
    assert totals[V48Session.LONDON] == 4
    assert totals[V48Session.NEW_YORK] == 7
    assert result.forces_trade_quota is False


def test_missing_market_row_fails_closed() -> None:
    result = assess_three_session_coverage(_full_rows()[:-1])
    assert result.decision is V48ThreeSessionCoverageDecision.INCOMPLETE
    assert result.missing_market_rows == ("NEW_YORK:NAS100",)


def test_session_with_zero_source_complete_opportunities_fails_operability() -> None:
    rows = tuple(
        V48SessionMarketCoverage(
            row.session,
            row.market,
            0 if row.session is V48Session.LONDON else row.source_complete_opportunities,
        )
        for row in _full_rows()
    )
    result = assess_three_session_coverage(rows)
    assert result.decision is V48ThreeSessionCoverageDecision.INCOMPLETE
    assert result.empty_sessions == (V48Session.LONDON,)


def test_gate_preserves_max3_as_ceiling_and_grants_no_fresh_authority() -> None:
    gate = V48_THREE_SESSION_COVERAGE_GATE
    assert gate.max_executions_per_session == 3
    assert gate.quota_required is False
    assert gate.economics_authorized is False
    assert gate.fresh_holdout_authorized is False
