from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_shadow_boundary_forensics_2y_v1 as atlas,
)


def test_source_first_shadow_boundary_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_SHADOW_BOUNDARY_FORENSICS_2Y_V1"
    )
    assert atlas.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_SHADOW_BOUNDARY_FORENSICS_2Y_V1"
    )
    assert atlas.EXPECTED_SOURCE_FIRST_RAW == 1142
    assert atlas.EXPECTED_SOURCE_FIRST_MAX3 == 1118
    assert atlas.MISSING == "V3_BOUNDARY_MISSING"
    assert atlas.PRESENT_NOT_CROSSED == "V3_BOUNDARY_PRESENT_NOT_CROSSED"
    assert atlas.CROSSED == "V3_BOUNDARY_CROSSED"
