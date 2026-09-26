from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.multi_horizon_incidence import (
    HorizonIncidencePoint,
    build_multi_horizon_incidence_profile,
)


def test_frontload_separates_imminence_from_far_horizon_probability() -> None:
    profile = build_multi_horizon_incidence_profile(
        (
            HorizonIncidencePoint(1, adverse_bps=3_000, favorable_bps=500),
            HorizonIncidencePoint(3, adverse_bps=4_000, favorable_bps=900),
            HorizonIncidencePoint(10, adverse_bps=5_000, favorable_bps=1_500),
        )
    )

    assert profile.adverse_frontload_bps == 6_000
    assert profile.favorable_frontload_bps == 3_333
    assert profile.frontload_margin_bps > 0
    assert profile.near_directional_margin_bps > 0
    assert profile.outcome_used is False
    assert profile.pnl_used is False
    assert profile.future_market_used is False
    assert profile.risk_authority is False
    assert profile.execution_authority is False


def test_non_monotonic_model_curve_is_repaired_causally() -> None:
    profile = build_multi_horizon_incidence_profile(
        (
            HorizonIncidencePoint(1, adverse_bps=2_000, favorable_bps=1_000),
            HorizonIncidencePoint(3, adverse_bps=1_500, favorable_bps=1_200),
            HorizonIncidencePoint(5, adverse_bps=2_500, favorable_bps=900),
        )
    )

    assert profile.adverse_curve_bps == (2_000, 2_000, 2_500)
    assert profile.favorable_curve_bps == (1_000, 1_200, 1_200)
    assert profile.adverse_monotonic_repairs == 1
    assert profile.favorable_monotonic_repairs == 1


def test_horizons_must_be_strictly_increasing() -> None:
    with pytest.raises(ValueError):
        build_multi_horizon_incidence_profile(
            (
                HorizonIncidencePoint(3, adverse_bps=2_000, favorable_bps=1_000),
                HorizonIncidencePoint(3, adverse_bps=3_000, favorable_bps=1_500),
            )
        )
