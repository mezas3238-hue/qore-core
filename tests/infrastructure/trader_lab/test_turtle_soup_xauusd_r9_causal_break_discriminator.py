from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_causal_break_discriminator as r9


def test_r9_reuses_pre_registered_r8_break_families() -> None:
    assert r9.r8.BREAK_FAMILIES["BREAK_A_DEEP_RAID_MID_LATE_CISD"] == r9.r8.BREAK_A
    assert r9.r8.BREAK_FAMILIES["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"] == r9.r8.BREAK_B


def test_percentile_interpolates_decimal_values() -> None:
    values = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4")]
    assert r9._percentile(values, 1, 4) == Decimal("1.75")
    assert r9._percentile(values, 1, 2) == Decimal("2.5")
    assert r9._percentile(values, 3, 4) == Decimal("3.25")


def test_safe_ratio_fails_closed_on_non_positive_denominator() -> None:
    assert r9._safe_ratio(Decimal("1"), Decimal("0")) is None
    assert r9._safe_ratio(Decimal("1"), Decimal("-1")) is None
    assert r9._safe_ratio(Decimal("2"), Decimal("4")) == Decimal("0.5")


def test_feature_contract_includes_core_journey_geometry() -> None:
    required = {
        "raid_depth_source_fraction",
        "reclaim_fraction_of_sweep",
        "cisd_progress_exact",
        "cisd_displacement_source_fraction",
        "protected_risk_source_fraction_exact",
        "active_dol_count",
        "selected_dol_rank",
        "h4_range_3v20_exact",
        "d1_range_5v20_exact",
    }
    assert required <= set(r9.CONTINUOUS_FEATURES)


def test_year_partitions_are_diagnostic_and_exhaust_recent() -> None:
    assert r9.EARLY_YEARS == frozenset(range(2016, 2021))
    assert r9.TRANSITION_YEARS == frozenset({2021, 2022, 2023})
    assert r9.RECENT_YEARS == frozenset({2024, 2025, 2026})
    assert not (r9.HISTORICAL_YEARS & r9.RECENT_YEARS)
