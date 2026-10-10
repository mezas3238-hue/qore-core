from qore.infrastructure.trader_lab.vt08_cognitive_m3_intracycle_c2_density_census_v1 import (
    PROFILE,
    SCHEMA,
)


def test_m3_intracycle_c2_density_census_freeze() -> None:
    assert PROFILE == "M3_FRACTAL"
    assert SCHEMA.endswith("m3_intracycle_c2_density_census.v1")
