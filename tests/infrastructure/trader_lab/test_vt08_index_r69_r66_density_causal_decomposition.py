from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r69_r66_density_causal_decomposition as r69,
)


def test_r69_rate_is_per_complete_provider_backed_m15_bucket() -> None:
    rate = r69._rate(trades=70, complete_m15_buckets=10000)
    assert rate == Decimal("0.007")
    assert rate * r69.RATE_SCALE == Decimal("70")


def test_r69_projection_separates_coverage_from_structural_rate() -> None:
    baseline_counts = {"NAS100": 100}
    baseline_availability = {
        "NAS100": {
            "complete_three_m5_buckets": 10000,
            "m15_buckets": 10000,
        }
    }
    failed_counts = {"NAS100": 70}
    failed_availability = {
        "NAS100": {
            "complete_three_m5_buckets": 8000,
            "m15_buckets": 9000,
        }
    }
    row = r69._projection(
        baseline_counts=baseline_counts,
        baseline_availability=baseline_availability,
        r66_counts=failed_counts,
        r66_availability=failed_availability,
    )
    assert Decimal(row["expected_at_observed_complete_exposure"]) == Decimal("80")
    assert Decimal(row["expected_at_full_observed_bucket_exposure"]) == Decimal("90")
    assert Decimal(row["projected_missing_coverage_component_trades"]) == Decimal("10")
    assert Decimal(row["projected_structural_rate_component_trades"]) == Decimal("10")


def test_r69_gate_remains_preregistered_r66_gate() -> None:
    assert r69.R66_DENSITY_GATE == 1000
