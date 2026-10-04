from qore.infrastructure.core_stack_v2.mc24_empirical_half_life import (
    HalfLifeStatus,
    KnowledgeHalfLifeBin,
    measure_empirical_half_life,
)


def _bin(i: int, benefit: int, regression: int = 0, samples: int = 700):
    return KnowledgeHalfLifeBin(
        bin_index=i,
        start_age_days=i * 90,
        end_age_days=(i + 1) * 90,
        sample_count=samples,
        pooled_incremental_information_bps=benefit,
        maximum_target_regression_bps=regression,
    )


def test_half_life_requires_two_consecutive_below_half_reference() -> None:
    result = measure_empirical_half_life(
        (
            _bin(0, 400),
            _bin(1, 250),
            _bin(2, 190),
            _bin(3, 180),
            _bin(4, 170),
        )
    )
    assert result.status is HalfLifeStatus.MEASURED
    assert result.half_life_threshold_bps == 200
    assert result.half_life_days == 180
    assert result.empirical_half_life_validated is True


def test_persistent_benefit_yields_lower_bound() -> None:
    result = measure_empirical_half_life(
        (_bin(0, 400), _bin(1, 350), _bin(2, 310), _bin(3, 250))
    )
    assert result.status is HalfLifeStatus.LOWER_BOUND
    assert result.lower_bound_days == 360
    assert result.empirical_half_life_validated is True


def test_catastrophic_forgetting_is_separate_from_measurement() -> None:
    result = measure_empirical_half_life(
        (
            _bin(0, 400),
            _bin(1, 300),
            _bin(2, 190, regression=700),
            _bin(3, 180),
        )
    )
    assert result.status is HalfLifeStatus.MEASURED
    assert result.catastrophic_forgetting_detected is True
    assert result.retained_knowledge_non_degradation_pass is False


def test_insufficient_bins_do_not_fabricate_half_life() -> None:
    result = measure_empirical_half_life(
        (_bin(0, 400), _bin(1, 200), _bin(2, 100, samples=100))
    )
    assert result.status is HalfLifeStatus.INSUFFICIENT
    assert result.empirical_half_life_validated is False
