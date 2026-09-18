from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r17_cibo_journey_capacity_memory import (
    _period,
    _profile,
)


def test_period_mapping() -> None:
    assert _period(2019) == "early_2016_2020"
    assert _period(2022) == "transition_2021_2023"
    assert _period(2026) == "recent_2024_2026"


def test_profile_measures_liquidity_depth_not_pnl() -> None:
    rows = [
        {
            "active_dol_levels": 4,
            "max_dol_rank_touched": 3,
            "nearest_dol_r": "1.0",
            "invalidated_before_rank_1": False,
            "reached_rank_1": True,
            "reached_rank_2": True,
            "reached_rank_3": True,
            "reached_rank_4": False,
            "reached_rank_5": False,
            "first_dol_touch_minutes": "15",
        },
        {
            "active_dol_levels": 2,
            "max_dol_rank_touched": 0,
            "nearest_dol_r": "1.5",
            "invalidated_before_rank_1": True,
            "reached_rank_1": False,
            "reached_rank_2": False,
            "reached_rank_3": False,
            "reached_rank_4": False,
            "reached_rank_5": False,
            "first_dol_touch_minutes": None,
        },
    ]
    p = _profile(rows)
    assert p["observations"] == 2
    assert p["reached_rank_1"] == 1
    assert p["reached_rank_2"] == 1
    assert p["reached_rank_3"] == 1
    assert p["invalidated_before_rank_1_rate"] == "0.5"
