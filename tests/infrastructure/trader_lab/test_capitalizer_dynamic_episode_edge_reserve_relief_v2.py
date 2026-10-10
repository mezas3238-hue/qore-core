from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_edge_reserve_relief_v2 as v2,
)


def test_relief_requires_baseline_edge_but_lower_current_dd() -> None:
    baseline = {
        "profit_factor": "1.50",
        "total_r": "100",
        "max_drawdown_r": "7",
        "max_losing_streak": 6,
        "trades": 1000,
    }
    current = {
        "profit_factor": "1.70",
        "total_r": "110",
        "max_drawdown_r": "6.8",
        "max_losing_streak": 5,
        "trades": 1000,
    }
    candidate = {
        "profit_factor": "1.51",
        "total_r": "101",
        "max_drawdown_r": "6.4",
        "max_losing_streak": 6,
        "trades": 1000,
    }

    assert v2._relief_admissible(
        candidate,
        baseline=baseline,
        current=current,
    )


def test_reserve_is_pareto_monotone_and_dd_nonworsening() -> None:
    baseline = {
        "profit_factor": "1.50",
        "total_r": "100",
        "max_drawdown_r": "7",
        "max_losing_streak": 6,
        "trades": 1000,
    }
    current = {
        "profit_factor": "1.60",
        "total_r": "105",
        "max_drawdown_r": "6.8",
        "max_losing_streak": 5,
        "trades": 1000,
    }
    candidate = {
        "profit_factor": "1.61",
        "total_r": "106",
        "max_drawdown_r": "6.8",
        "max_losing_streak": 6,
        "trades": 1000,
    }

    assert v2._reserve_admissible(
        candidate,
        baseline=baseline,
        current=current,
    )
    candidate["max_drawdown_r"] = "6.81"
    assert not v2._reserve_admissible(
        candidate,
        baseline=baseline,
        current=current,
    )


def test_v2_identity() -> None:
    assert v2.IDENTITY == (
        "QORE_CAPITALIZER_DYNAMIC_EPISODE_EDGE_RESERVE_RELIEF_V2"
    )
    assert v2._profit_factor({"profit_factor": "1.25"}) == Decimal("1.25")
