from qore.infrastructure.trader_lab.vt08_cognitive_m3_entry_geometry_census_v1 import (
    PROFILE,
    SCHEMA,
)


def test_m3_entry_geometry_census_freeze() -> None:
    assert PROFILE == "M3_FRACTAL"
    assert SCHEMA.endswith("m3_entry_geometry_census.v1")
