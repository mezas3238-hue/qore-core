from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_atr_readiness_atlas_2y_v1 as atlas,
)


def test_source_first_atr_readiness_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_ATR_READINESS_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_ATR_BLOCKERS == 2232
    assert atlas.FROZEN_ATR_MULTIPLIER == Decimal("1.2")
    assert atlas.FROZEN_BODY_RATIO_MIN == Decimal("0.60")


def test_ratio_bands_do_not_relax_threshold() -> None:
    assert atlas._ratio_band(Decimal("1.19")) == "1_10_TO_LT_1_20"
    assert atlas._ratio_band(Decimal("1.20")) == "EQ_1_20"
    assert atlas._ratio_band(Decimal("1.21")) == "GT_1_20_UNEXPECTED"
