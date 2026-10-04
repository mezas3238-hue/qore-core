from qore.infrastructure.core_stack_v2.shared_lab_data_reality import DataQualityMetrics, DataQualityThresholds


def test_completeness_threshold_is_parameterized_not_asset_hardcoded() -> None:
    strict = DataQualityThresholds(min_coverage=0.99, min_usable_ratio=0.99)
    permissive = DataQualityThresholds(min_coverage=0.90, min_usable_ratio=0.90)
    metrics = DataQualityMetrics(
        expected_observations=100,
        received_observations=95,
        missing_count=5,
        duplicate_count=0,
        out_of_order_count=0,
        stale_count=0,
        invalid_count=0,
        provider_disagreement_count=0,
        gap_distribution_ns=(),
        latency_distribution_ns=(),
        usable_observations=95,
    )
    assert not metrics.passes(strict)
    assert metrics.passes(permissive)
