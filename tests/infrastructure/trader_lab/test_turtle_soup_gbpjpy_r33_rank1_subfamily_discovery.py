from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r33_rank1_subfamily_discovery as r33,
)


def test_family_discovery_gate_is_predeclared() -> None:
    assert r33.MIN_OBSERVATIONS == 200
    assert r33.MIN_PF_010 == Decimal("1.35")
    assert r33.REQUIRED_POSITIVE_QUINTILES == 5
    assert r33.MAX_FAMILIES == 8
    assert r33.MIN_INCREMENTAL_OBSERVATIONS == 100


def test_family_features_exclude_calendar_and_outcomes() -> None:
    forbidden = {"year", "period", "target_rank", "target_route"}
    assert forbidden.isdisjoint(r33.PRE_ENTRY_FEATURES)
    assert all("gross" not in field and "net" not in field for field in r33.PRE_ENTRY_FEATURES)


def test_rank1_stat_is_full_lifecycle_net_010() -> None:
    rows = [
        {"strategy_entry_at": "2024-01-01T00:00:00+00:00", "STATIC_net_010_r": "1"},
        {"strategy_entry_at": "2024-01-02T00:00:00+00:00", "STATIC_net_010_r": "-0.5"},
    ]
    stat = r33._stat(rows)
    assert stat["total_r"] == "0.5"
    assert Decimal(str(stat["profit_factor"])) == Decimal("2")
