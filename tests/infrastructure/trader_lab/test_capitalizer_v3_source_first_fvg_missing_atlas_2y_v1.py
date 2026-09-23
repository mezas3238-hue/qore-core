from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_fvg_missing_atlas_2y_v1 as atlas,
)


def test_fvg_missing_atlas_contract_is_frozen() -> None:
    assert atlas.IDENTITY == "QORE_CAPITALIZER_V3_SOURCE_FIRST_FVG_MISSING_ATLAS_2Y_V1"
    assert atlas.MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_FVG_MISSING_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_FVG_MISSING == 322
    assert atlas.NO_DISPLACEMENT_M1 == "NO_DISPLACEMENT_M1"
    assert atlas.NO_CAUSAL_OB == "NO_CAUSAL_OB"
    assert atlas.NO_PRECONFIRM_SAME_SIDE_FVG == "NO_PRECONFIRM_SAME_SIDE_FVG"


def test_fvg_direction_helpers_are_side_aware() -> None:
    class Bar:
        def __init__(self, low: str, high: str) -> None:
            from decimal import Decimal

            self.low = Decimal(low)
            self.high = Decimal(high)

    first = Bar("100", "101")
    third = Bar("102", "103")
    assert atlas._same_side_fvg(first, third, atlas.CapitalizerSide.LONG) is True
    assert atlas._opposed_fvg(first, third, atlas.CapitalizerSide.LONG) is False
    assert atlas._same_side_fvg(first, third, atlas.CapitalizerSide.SHORT) is False
    assert atlas._opposed_fvg(first, third, atlas.CapitalizerSide.SHORT) is True
