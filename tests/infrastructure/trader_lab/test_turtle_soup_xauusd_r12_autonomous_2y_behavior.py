from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r12_autonomous_2y_behavior import _stats


def test_stats_measure_stop_target_and_rr() -> None:
    rows = [
        {
            "primary_net_r": "1.95", "gross_r": "2.0",
            "entry": "100", "stop": "99", "target": "102",
        },
        {
            "primary_net_r": "-1.05", "gross_r": "-1.0",
            "entry": "100", "stop": "98", "target": "103",
        },
    ]
    result = _stats(rows)
    assert result["trades"] == 2
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["total_primary_r"] == "0.90"
    assert result["median_stop_price_distance"] == "2"
    assert result["median_target_price_distance"] == "3"
    assert result["median_planned_rr"] == "2"


def test_empty_stats_fail_neutral() -> None:
    assert _stats([]) == {"trades": 0}
