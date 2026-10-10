from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_no_m3_timing_atlas_2y_v1 as atlas,
)


def test_no_m3_timing_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_NO_M3_TIMING_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_NO_M3 == 390


def test_remaining_bands_are_deterministic() -> None:
    assert atlas._remaining_band(Decimal("0")) == "LE_0M"
    assert atlas._remaining_band(Decimal("0.5")) == "GT_0_TO_1M"
    assert atlas._remaining_band(Decimal("2.5")) == "GT_2_TO_3M"
    assert atlas._remaining_band(Decimal("4")) == "GT_3M"
