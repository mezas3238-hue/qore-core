from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_regime_forensics as f


def test_era_partition() -> None:
    assert f._era(2016) == "2016_2019_POSITIVE_BASELINE"
    assert f._era(2019) == "2016_2019_POSITIVE_BASELINE"
    assert f._era(2020) == "2020_2021_FLAT_TRANSITION"
    assert f._era(2022) == "2022_2023_RECOVERY"
    assert f._era(2026) == "2024_2026_NEGATIVE_RECENT"


def test_stat_hit_rates() -> None:
    rows = [
        {"primary_net_r": "2", "exit_reason": "TARGET"},
        {"primary_net_r": "-1", "exit_reason": "STOP"},
        {"primary_net_r": "0.5", "exit_reason": "GAP_TARGET_CAPPED"},
        {"primary_net_r": "-1", "exit_reason": "STOP_FIRST"},
    ]
    result = f._stat(rows)
    assert result["n"] == 4
    assert result["total_r"] == "0.5"
    assert result["profit_factor"] == "1.25"
    assert result["win_rate"] == "0.5"
    assert result["stop_rate"] == "0.5"
    assert result["target_rate"] == "0.5"
