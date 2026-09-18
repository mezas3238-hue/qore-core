from qore.infrastructure.trader_lab import turtle_soup_xauusd_r8_structural_break_counterfactual as r8


def test_break_a_frozen_exact() -> None:
    assert r8.BREAK_A == {
        "raid_depth_range_bucket": "q4:<=0.50",
        "cisd_progress_bucket": "q3:<=0.75",
        "reclaim_latency_bucket": "<=5m",
        "protected_risk_range_bucket": "q3:<=1.0",
    }


def test_break_b_frozen_exact() -> None:
    assert r8.BREAK_B == {
        "raid_depth_range_bucket": "q3:<=0.25",
        "cisd_progress_bucket": "q2:<=0.50",
        "reclaim_latency_bucket": "<=5m",
        "protected_risk_range_bucket": "q3:<=1.0",
        "h4_range_3v20": "normal_0.75_1.25",
    }


def test_matches_requires_entire_signature() -> None:
    row = dict(r8.BREAK_B)
    assert r8._matches(row, r8.BREAK_B)
    row["h4_range_3v20"] = "compressed<=0.75"
    assert not r8._matches(row, r8.BREAK_B)


def test_periods_include_required_slices() -> None:
    periods = r8._periods()
    assert periods["early_2016_2020"] == set(range(2016, 2021))
    assert periods["transition_2021_2023"] == {2021, 2022, 2023}
    assert periods["recent_2024_2026"] == {2024, 2025, 2026}
    assert periods["2024"] == {2024}
