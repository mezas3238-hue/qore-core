from qore.infrastructure.trader_lab.capitalizer_high_frequency_density_gate_v49 import (
    V49_DENSITY_MANDATE,
    V49DensityDecision,
    assess_v49_density,
)


def test_v48_159_per_year_is_explicitly_below_v49_high_frequency_floor() -> None:
    result = assess_v49_density(
        annual_total=159,
        asia_total=65,
        london_total=30,
        new_york_total=64,
    )
    assert result.decision is V49DensityDecision.INSUFFICIENT_DENSITY


def test_v49_requires_material_density_in_all_three_sessions() -> None:
    result = assess_v49_density(
        annual_total=650,
        asia_total=220,
        london_total=190,
        new_york_total=240,
    )
    assert result.decision is V49DensityDecision.HIGH_FREQUENCY_CAPACITY_PASS
    assert result.outcome_used is False
    assert result.economics_used is False
    assert result.quota_imposed is False


def test_one_empty_or_weak_session_fails_even_when_annual_total_is_large() -> None:
    result = assess_v49_density(
        annual_total=700,
        asia_total=320,
        london_total=60,
        new_york_total=320,
    )
    assert result.decision is V49DensityDecision.INSUFFICIENT_DENSITY


def test_density_floor_is_qore_engineering_not_source_rule() -> None:
    state = V49_DENSITY_MANDATE
    assert state.source_rule is False
    assert state.owner_qore_engineering_requirement is True
    assert state.minimum_annual_source_complete == 500
    assert state.minimum_per_session_source_complete == 100
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
