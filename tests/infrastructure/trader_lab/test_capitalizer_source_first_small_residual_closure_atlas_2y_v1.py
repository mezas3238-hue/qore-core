from qore.infrastructure.trader_lab import (
    capitalizer_source_first_small_residual_closure_atlas_2y_v1 as atlas,
)


def test_small_residual_closure_contract() -> None:
    assert atlas.EXPECTED_NO_DIRECTIONAL == 55
    assert atlas.EXPECTED_NO_SOURCE_BOUNDARY == 13
    assert atlas.TARGET_BLOCKERS == {
        "NO_DIRECTIONAL_AFTER_BOUNDARY",
        "NO_SOURCE_BOUNDARY",
    }
