from qore.infrastructure.trader_lab.capitalizer_v3_density_n1_n2_1y_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    STOP_IDENTITY,
    TARGET_IDENTITY,
)


def test_density_n1_n2_keeps_v3_economic_contract() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_DENSITY_N1_N2_1Y_V1"
    assert MATRIX_IDENTITY == "QORE_CAPITALIZER_NINE_MARKET_V3_DENSITY_N1_N2_1Y_V1"
    assert STOP_IDENTITY == "M3_BROKEN_SWING_PLUS_5_PIP_BUFFER"
    assert TARGET_IDENTITY == "FIXED_2R_OR_NEXT_H1_OPEN"
