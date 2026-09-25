from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    metrics,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionAbstainReason,
    evaluate_expansion_at_entry_indexed,
    expansion_evaluator_fingerprint,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    CONTROL_MARKET,
    EXPANSION_MARKETS,
    NEW_MARKET_EVIDENCE_STATUS,
    NEW_RESEARCH_MARKETS,
    RESEARCH_GATES,
    USDCAD_CONTROL_EVIDENCE,
    Vt08Expansion5MFreeze,
    program_fingerprint,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_expansion_universe_is_exactly_five_markets() -> None:
    freeze = Vt08Expansion5MFreeze()
    assert EXPANSION_MARKETS == (
        "EURJPY",
        "USDCHF",
        "NZDUSD",
        "CADJPY",
        "USDCAD",
    )
    assert NEW_RESEARCH_MARKETS == ("EURJPY", "USDCHF", "NZDUSD", "CADJPY")
    assert CONTROL_MARKET == "USDCAD"
    assert ANCHORS_NY == (1, 5, 9)
    assert freeze.new_market_execution_authority is False
    assert freeze.live_authorized is False


def test_usdcad_is_bound_as_consumed_control_not_new_authority() -> None:
    assert USDCAD_CONTROL_EVIDENCE["source_run_id"] == 34759027136
    assert USDCAD_CONTROL_EVIDENCE["artifact_id"] == 10318398127
    assert USDCAD_CONTROL_EVIDENCE["status"] == "CONSUMED_CONTROL_EVIDENCE"
    assert set(NEW_MARKET_EVIDENCE_STATUS) == set(NEW_RESEARCH_MARKETS)


def test_research_gates_are_frozen_before_new_market_outcomes() -> None:
    assert RESEARCH_GATES["minimum_profit_factor"] == "1.80"
    assert RESEARCH_GATES["maximum_observed_drawdown_r"] == "6.00"
    assert RESEARCH_GATES["maximum_mc_p95_drawdown_r"] == "15.00"
    assert RESEARCH_GATES["minimum_mc_positive_terminal"] == "0.90"
    assert len(program_fingerprint()) == 64
    assert len(expansion_evaluator_fingerprint()) == 64


def test_non_expansion_market_fails_closed() -> None:
    result = evaluate_expansion_at_entry_indexed(
        symbol="GBPUSD",
        bars_by_open={},
        decision_at=datetime(2026, 9, 23, 9, 0, tzinfo=UTC),
    )
    assert result.candidate is None
    assert (
        result.abstain_reason
        is Vt08ExpansionAbstainReason.UNSUPPORTED_RESEARCH_MARKET
    )


def test_r_metrics_report_pf_drawdown_and_streak() -> None:
    now = datetime(2026, 9, 23, tzinfo=UTC)

    def trade(value: str) -> ExpansionTrade:
        r = Decimal(value)
        return ExpansionTrade(
            symbol="USDCAD",
            signal_at=now,
            exited_at=now,
            anchor_hour_ny=5,
            side=DemoTradingSetupSide.LONG,
            entry=Decimal("1.3000"),
            stop=Decimal("1.2900"),
            target=Decimal("1.3200"),
            exit_price=Decimal("1.3000"),
            exit_reason="synthetic-test",
            r_multiple=r,
        )

    result = metrics((trade("2"), trade("-1"), trade("-1"), trade("2")))
    assert result["sample_size"] == 4
    assert result["profit_factor"] == "2"
    assert result["total_r"] == "2"
    assert result["max_drawdown_r"] == "2"
    assert result["max_losing_streak"] == 2


def test_freeze_rejects_authority_mutation() -> None:
    with pytest.raises(ValueError, match="cannot grant operational authority"):
        Vt08Expansion5MFreeze(live_authorized=True)
