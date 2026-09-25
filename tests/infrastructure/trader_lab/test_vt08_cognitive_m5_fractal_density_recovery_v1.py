from qore.infrastructure.trader_lab.vt08_cognitive_m5_fractal_density_recovery_v1 import (
    PROFILE,
)


def test_m5_profile_is_independent_not_cross_confirmation() -> None:
    assert PROFILE == "M5_FRACTAL"
