from __future__ import annotations

import pytest

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cg_wait_capacity_forensics as r2cg,
)


def test_capacity_is_upper_bound_not_trade_entry_permission() -> None:
    x = r2cg._capacity(815, 856, 365, fold_count=11)
    assert x["strict_nested_trades"] == 1180
    assert x["upper_bound_trades"] == 1671
    assert x["upper_bound_trades_per_year"] < 170
    assert x["remaining_trades_to_target"] == 690
    assert x["arithmetic_ceiling_reaches_target"] is False
    assert x["upper_bound_only_not_an_executable_or_profitable_portfolio"] is True


def test_capacity_rejects_invalid_or_inconsistent_counts() -> None:
    with pytest.raises(ValueError, match="Invalid WAIT capacity"):
        r2cg._capacity(20, 4, 5, fold_count=1)
    with pytest.raises(ValueError, match="Invalid WAIT capacity"):
        r2cg._capacity(20, 4, 2, fold_count=0)


def test_transition_attribution_reconciles_pairwise_difference() -> None:
    totals: dict[str, dict[str, float | int]] = {}
    r2cg._attribution_add(totals, transition="NESTED_ONLY_EXECUTE", delayed_r=1.2)
    r2cg._attribution_add(totals, transition="NESTED_ONLY_EXECUTE", delayed_r=-1.0)
    r2cg._attribution_add(totals, transition="CONTROL_ONLY_EXECUTE", delayed_r=-0.8)
    r2cg._check_transition_delta(totals, 1.0, scope="test")
    assert totals["NESTED_ONLY_EXECUTE"]["count"] == 2
    with pytest.raises(ValueError, match="transition-delta"):
        r2cg._check_transition_delta(totals, -10, scope="test")


def test_exact_frozen_fold_reconciliation_blocks_result_drift() -> None:
    source = {
        "trades": 2,
        "total_r": 0.5,
        "profit_factor": 1.5,
        "max_drawdown_r": 1.0,
        "dead_on_arrival_rate": 0.5,
        "origin_counts": {"INITIAL_EXECUTE": 1, "WAIT_DELAYED_EXECUTE": 1},
        "cost_stress": {
            "COST_0.02R": {
                "trades": 2,
                "total_r": 0.46,
                "profit_factor": 1.4,
                "max_drawdown_r": 1.02,
            },
            "COST_0.05R": {
                "trades": 2,
                "total_r": 0.4,
                "profit_factor": 1.3,
                "max_drawdown_r": 1.05,
            },
        },
    }
    r2cg._compared_metrics(source, dict(source), scope="test")
    with pytest.raises(ValueError, match="frozen reconciliation failed"):
        r2cg._compared_metrics(
            {**source, "total_r": 100.0}, source, scope="test"
        )


def test_unknown_markets_fail_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported market"):
        r2cg._configure("XAUUSD")
    assert r2cg.ARMS == ("CONTROL_ALL", "STRICT_NESTED_WAIT_4Y")
    assert r2cg.BAD_YEARS == {"AUDUSD": 2016, "USDJPY": 2023}
