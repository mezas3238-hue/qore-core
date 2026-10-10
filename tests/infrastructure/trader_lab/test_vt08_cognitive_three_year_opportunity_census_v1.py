from qore.infrastructure.trader_lab.vt08_cognitive_three_year_opportunity_census_v1 import (
    _presence_mask,
)


def test_presence_masks_do_not_double_count_profiles() -> None:
    assert _presence_mask({"M15_STANDARD"}) == "M15"
    assert _presence_mask({"M5_FRACTAL"}) == "M5"
    assert _presence_mask({"M3_FRACTAL"}) == "M3"
    assert _presence_mask({"M15_STANDARD", "M5_FRACTAL"}) == "M15_M5"
    assert _presence_mask(
        {"M15_STANDARD", "M5_FRACTAL", "M3_FRACTAL"}
    ) == "M15_M5_M3"
