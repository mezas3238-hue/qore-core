from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_market_stop_intelligence_5y_replay_v1 import (
    _metrics,
    structural_stop_for_row,
)


def _row(side: str) -> dict[str, object]:
    if side == "LONG":
        return {
            "side": "LONG",
            "entry_price": "100",
            "target_price": "110",
            "m1_order_block_low": "96",
            "m1_order_block_high": "99",
        }
    return {
        "side": "SHORT",
        "entry_price": "100",
        "target_price": "90",
        "m1_order_block_low": "101",
        "m1_order_block_high": "104",
    }


def test_structural_stop_uses_validated_ob_directional_extreme() -> None:
    assert structural_stop_for_row(_row("LONG")) == Decimal("96")
    assert structural_stop_for_row(_row("SHORT")) == Decimal("104")


def test_structural_stop_rejects_invalid_geometry() -> None:
    row = _row("LONG")
    row["m1_order_block_low"] = "101"
    assert structural_stop_for_row(row) is None


def test_metrics_preserve_stop_target_session_counts() -> None:
    rows = [
        {
            "entry_at": "2026-01-01T13:00:00+00:00",
            "realized_gross_r": "2",
            "exit_reason": "TARGET",
        },
        {
            "entry_at": "2026-01-02T13:00:00+00:00",
            "realized_gross_r": "-1",
            "exit_reason": "STOP",
        },
        {
            "entry_at": "2026-01-03T13:00:00+00:00",
            "realized_gross_r": "0.5",
            "exit_reason": "SESSION_EXIT",
        },
    ]
    result = _metrics(rows, "realized_gross_r")
    assert result.trades == 3
    assert result.profit_factor == "2.5"
    assert result.total_r == "1.5"
    assert result.max_drawdown_r == "1"
    assert result.max_losing_streak == 1
    assert result.stop_exits == 1
    assert result.target_exits == 1
    assert result.session_exits == 1
