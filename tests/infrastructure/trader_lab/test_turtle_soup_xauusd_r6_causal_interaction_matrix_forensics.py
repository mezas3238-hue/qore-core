from decimal import Decimal

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r6_causal_interaction_matrix_forensics as r6


def _stat(trades: int, mean: str) -> dict[str, object]:
    return {
        "trades": trades,
        "total_primary_r": str(Decimal(mean) * trades),
        "mean_primary_r": mean,
        "profit_factor": None,
        "target_rate": None,
        "stop_rate": None,
    }


def test_pre_registered_core_contains_requested_causal_journey_features() -> None:
    assert r6.JOURNEY_CORE == (
        "raid_depth_range_bucket",
        "cisd_progress_bucket",
        "reclaim_latency_bucket",
        "protected_risk_range_bucket",
    )
    assert all("year" not in feature and "date" not in feature for _, features in r6.INTERACTION_TEMPLATES for feature in features)


def test_classify_robust_valid_requires_all_supported_periods_positive() -> None:
    years = {str(year): _stat(10, "0.10") for year in (2024, 2025, 2026)}
    result = r6._classify(_stat(25, "0.20"), _stat(20, "0.10"), _stat(30, "0.12"), years)
    assert result == "ROBUST_VALID"


def test_classify_structural_break_requires_recent_years_negative() -> None:
    years = {str(year): _stat(10, "-0.10") for year in (2024, 2025, 2026)}
    result = r6._classify(_stat(25, "0.20"), _stat(20, "0.01"), _stat(30, "-0.12"), years)
    assert result == "STRUCTURAL_BREAK_TO_INVALID"


def test_support_contract_rejects_small_recent_year_cell() -> None:
    years = {
        "2024": _stat(10, "0.10"),
        "2025": _stat(7, "0.10"),
        "2026": _stat(10, "0.10"),
    }
    result = r6._classify(_stat(25, "0.20"), _stat(20, "0.10"), _stat(30, "0.12"), years)
    assert result == "INSUFFICIENT_SUPPORT"
