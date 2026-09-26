from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_residual_m3_bottleneck_atlas_2y_v1 as atlas,
)


def test_source_first_residual_m3_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_RESIDUAL_M3_BOTTLENECK_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_CLOSEBACKS == 8099
    assert atlas.EXPECTED_SOURCE_FIRST_MSS == 2692
    assert atlas.EXPECTED_RESIDUAL == 5407
