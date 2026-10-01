from decimal import Decimal

from qore.infrastructure.cibo_ce2i_provider_execution_stress_bound import (
    FROZEN_PROVIDER_EXECUTION_STRESS_PROFILE,
    provider_execution_stress_profile_sha256,
)


def test_provider_execution_stress_profile_is_non_improving_and_frozen() -> None:
    profile = FROZEN_PROVIDER_EXECUTION_STRESS_PROFILE

    assert len(profile.scenarios) == 4
    assert tuple(item.scenario_id for item in profile.scenarios) == (
        "NATIVE_BASE",
        "MODERATE_DEGRADATION",
        "SEVERE_DEGRADATION",
        "EXTREME_DEGRADATION",
    )
    assert all(item.spread_multiplier >= Decimal("1") for item in profile.scenarios)
    assert all(item.commission_multiplier >= Decimal("1") for item in profile.scenarios)
    assert all(item.margin_multiplier >= Decimal("1") for item in profile.scenarios)
    assert profile.empirical_slippage_claimed is False
    assert profile.historical_2017_exact_claimed is False
    assert profile.holdout_outcomes_used is False
    assert profile.productive_authority is False
    assert provider_execution_stress_profile_sha256().startswith("sha256:")
