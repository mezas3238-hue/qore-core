from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_crt_h1_m3_m1_ote_1y_v6b import (
    ATR_MULTIPLIER,
    BODY_RATIO_MIN,
    IDENTITY,
    MATRIX_IDENTITY,
    STOP_IDENTITY,
    _variant_structure_logic,
)


def test_v6b_identity_and_v5_stop_contract() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_CRT_H1_M3_M1_OTE_1Y_V6B"
    assert MATRIX_IDENTITY == "QORE_CAPITALIZER_NINE_MARKET_CRT_H1_M3_M1_OTE_1Y_V6B"
    assert STOP_IDENTITY == "M1_OB_EXTREME_PLUS_5_PIP_BUFFER"


def test_v6b_thresholds_are_frozen() -> None:
    assert BODY_RATIO_MIN == Decimal("0.60")
    assert ATR_MULTIPLIER == Decimal("1.2")


def test_v6b_structure_logic() -> None:
    assert _variant_structure_logic(structure_break=True, cisd_break=True) is True
    assert _variant_structure_logic(structure_break=True, cisd_break=False) is True
    assert _variant_structure_logic(structure_break=False, cisd_break=True) is True
    assert _variant_structure_logic(structure_break=False, cisd_break=False) is False
