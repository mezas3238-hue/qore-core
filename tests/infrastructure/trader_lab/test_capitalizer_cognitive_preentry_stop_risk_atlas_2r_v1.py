from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_preentry_stop_risk_atlas_2r_v1 as atlas,
)


def test_trade_projection_keeps_post_audit_outcome_separate() -> None:
    row = {
        "symbol": "EURUSD",
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "side": "LONG",
        "entry_at": "2026-01-05T09:00:00+00:00",
        "post_audit_exit_at": "2026-01-05T09:10:00+00:00",
        "post_audit_realized_gross_r": "-1",
        "post_audit_exit_reason": "STOP",
    }
    trade = atlas._trade(row)
    assert trade["realized_gross_r"] == "-1"
    assert trade["exit_reason"] == "STOP"
    assert "microstructure_observations" not in trade


def test_metrics_preserve_entry_order_drawdown() -> None:
    rows = (
        {
            "symbol": "EURUSD",
            "entry_at": "2026-01-05T09:00:00+00:00",
            "realized_gross_r": "2",
            "exit_reason": "TARGET",
        },
        {
            "symbol": "GBPUSD",
            "entry_at": "2026-01-05T09:10:00+00:00",
            "realized_gross_r": "-1",
            "exit_reason": "STOP",
        },
        {
            "symbol": "EURUSD",
            "entry_at": "2026-01-05T09:20:00+00:00",
            "realized_gross_r": "-1",
            "exit_reason": "STOP",
        },
    )
    metrics = atlas._metrics(rows)
    assert metrics["trades"] == 3
    assert metrics["wins"] == 1
    assert metrics["losses"] == 2
    assert metrics["stops"] == 2
    assert metrics["profit_factor"] == "1"
    assert metrics["max_drawdown_r"] == "2"
