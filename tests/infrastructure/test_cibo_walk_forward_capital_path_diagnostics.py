from decimal import Decimal

from scripts.cibo_walk_forward_capital_path_diagnostics import (
    build_capital_path_diagnostics,
)


def _decision(signal: str, trader: str) -> dict[str, object]:
    return {
        "signal_fingerprint": signal,
        "trader_id": trader,
        "risk_decision": "ALLOW",
        "capital_disposition": "RISK_REVIEW_READY",
        "sizing_mode": "CAPABILITY_MAXIMUM",
        "adaptive_leverage_multiplier": "4",
        "requested_volume": "1",
        "authorized_volume": "1",
        "requested_stop_risk_usd": "10",
        "authorized_stop_risk_usd": "10",
    }


def test_capital_path_diagnostics_locates_threshold_crossing_and_minimum() -> None:
    replay = {
        "decision_receipts": [
            _decision("s1", "T1"),
            _decision("s2", "T2"),
            _decision("s3", "T1"),
        ],
        "settlement_receipts": [
            {
                "signal_fingerprint": "s2",
                "trader_id": "T2",
                "settled_at": "2026-01-02T00:00:00+00:00",
                "realized_net_pnl_usd": "-20",
            },
            {
                "signal_fingerprint": "s1",
                "trader_id": "T1",
                "settled_at": "2026-01-01T00:00:00+00:00",
                "realized_net_pnl_usd": "6",
            },
            {
                "signal_fingerprint": "s3",
                "trader_id": "T1",
                "settled_at": "2026-01-03T00:00:00+00:00",
                "realized_net_pnl_usd": "-16",
            },
        ],
    }

    result = build_capital_path_diagnostics(
        replay,
        initial_capital_usd=Decimal("60"),
    )

    assert result["ending_capital_usd"] == "30"
    assert result["peak_capital_usd"] == "66"
    assert result["minimum_capital_usd"] == "30"
    assert result["maximum_drawdown_usd"] == "36"
    assert result["first_threshold_crossings"]["0.75"]["signal_fingerprint"] == "s2"
    assert result["first_threshold_crossings"]["0.50"]["signal_fingerprint"] == "s3"
    assert result["minimum_capital_event"]["signal_fingerprint"] == "s3"
    assert result["net_pnl_by_trader_usd"] == {"T1": "-10", "T2": "-20"}
    assert result["gross_loss_by_trader_usd"] == {"T1": "16", "T2": "20"}
    assert result["gross_profit_by_trader_usd"] == {"T1": "6"}
    assert result["postdecision_only"] is True
    assert result["predecision_authority"] is False
