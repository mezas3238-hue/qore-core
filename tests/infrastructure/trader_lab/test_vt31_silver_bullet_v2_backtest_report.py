from __future__ import annotations

import pytest

from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest_report import (
    Vt31SilverBulletV2BacktestReportError,
    enrich_vt31_silver_bullet_v2_backtest_payload,
)


def _trade(*, side: str, outcome: str, r_multiple: str | None) -> dict[str, object]:
    return {
        "signal_at": "2026-07-08T14:03:00+00:00",
        "filled_at": "2026-07-08T14:04:00+00:00",
        "resolved_at": "2026-07-08T14:05:00+00:00",
        "side": side,
        "entry_price": "100",
        "stop_loss": "99",
        "take_profit": "102",
        "exit_price": "102" if r_multiple is not None else None,
        "outcome": outcome,
        "r_multiple": r_multiple,
    }


def _payload() -> dict[str, object]:
    trades = [
        _trade(side="long", outcome="target", r_multiple="2"),
        _trade(side="long", outcome="stop", r_multiple="-1"),
        _trade(side="short", outcome="gap_censored", r_multiple=None),
    ]
    return {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_backtest.v1",
        "symbol": "NAS100",
        "filled_count": len(trades),
        "trades": trades,
    }


def test_directional_report_reconciles_long_and_short_trade_counts() -> None:
    result = enrich_vt31_silver_bullet_v2_backtest_payload(_payload())

    assert result["long_trade_count"] == 2
    assert result["short_trade_count"] == 1
    assert result["long_trade_count"] + result["short_trade_count"] == result["filled_count"]

    directional = result["directional_breakdown"]
    assert isinstance(directional, dict)
    long = directional["long"]
    short = directional["short"]
    assert isinstance(long, dict)
    assert isinstance(short, dict)

    assert long == {
        "trade_count": 2,
        "terminal_sample_size": 2,
        "target_count": 1,
        "stop_count": 1,
        "gap_censored_count": 0,
        "data_end_censored_count": 0,
        "win_rate": "0.5",
        "expectancy_r": "0.5",
        "population_variance_r": "2.25",
    }
    assert short == {
        "trade_count": 1,
        "terminal_sample_size": 0,
        "target_count": 0,
        "stop_count": 0,
        "gap_censored_count": 1,
        "data_end_censored_count": 0,
        "win_rate": "0",
        "expectancy_r": "0",
        "population_variance_r": "0",
    }


def test_directional_report_fails_closed_when_filled_count_does_not_reconcile() -> None:
    payload = _payload()
    payload["filled_count"] = 4

    with pytest.raises(
        Vt31SilverBulletV2BacktestReportError,
        match="filled_count must equal",
    ):
        enrich_vt31_silver_bullet_v2_backtest_payload(payload)


def test_directional_report_fails_closed_on_noncanonical_side() -> None:
    payload = _payload()
    trades = payload["trades"]
    assert isinstance(trades, list)
    trade = trades[0]
    assert isinstance(trade, dict)
    trade["side"] = "buy"

    with pytest.raises(
        Vt31SilverBulletV2BacktestReportError,
        match="canonical LONG/SHORT",
    ):
        enrich_vt31_silver_bullet_v2_backtest_payload(payload)
