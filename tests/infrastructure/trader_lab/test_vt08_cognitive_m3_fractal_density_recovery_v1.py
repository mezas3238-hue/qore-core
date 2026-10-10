from qore.infrastructure.trader_lab.vt08_cognitive_m3_fractal_density_recovery_v1 import (
    PROFILE,
)


def test_m3_profile_is_independent_not_cross_confirmation() -> None:
    assert PROFILE == "M3_FRACTAL"
