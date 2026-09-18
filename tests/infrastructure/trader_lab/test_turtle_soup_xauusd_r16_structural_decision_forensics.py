from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r16_structural_decision_forensics import (
    _capacity,
    _period,
    _structural_profile,
)


def test_capacity_is_any_active_dol_touch() -> None:
    assert _capacity({"touched_dol_count": 1})
    assert not _capacity({"touched_dol_count": 0})


def test_period_partition_is_diagnostic_only_mapping() -> None:
    assert _period(2018) == "early_2016_2020"
    assert _period(2022) == "transition_2021_2023"
    assert _period(2025) == "recent_2024_2026"


def test_structural_profile_uses_capacity_not_pnl() -> None:
    rows = [
        {
            "filled": True,
            "dol_capable": True,
            "selected_dol_reached": False,
            "journey_failure_stage": "NEARER_DOL_REACHED_THEN_INVALIDATED",
            "fill_latency_minutes": "0",
            "selected_dol_rank": 2,
            "nearest_dol_distance_r": "1.2",
            "selected_rr": "2.5",
        },
        {
            "filled": True,
            "dol_capable": False,
            "selected_dol_reached": False,
            "journey_failure_stage": "INVALIDATED_BEFORE_ANY_ACTIVE_DOL",
            "fill_latency_minutes": "10",
            "selected_dol_rank": 1,
            "nearest_dol_distance_r": "1.7",
            "selected_rr": "1.7",
        },
        {"filled": False},
    ]
    profile = _structural_profile(rows)
    assert profile["attempts"] == 3
    assert profile["fills"] == 2
    assert profile["dol_capable"] == 1
    assert profile["selected_dol_reached"] == 0
    assert profile["invalidated_before_any_dol"] == 1
