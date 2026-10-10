from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_cisd_readiness_atlas_2y_v1 as atlas,
)


def test_cisd_readiness_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_CISD_READINESS_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_CISD_BLOCKERS == 213


def test_cisd_gap_bands_are_deterministic() -> None:
    assert atlas._gap_band(None) == "NO_GAP"
    assert atlas._gap_band(Decimal("0.02")) == "LE_0_02_ATR"
    assert atlas._gap_band(Decimal("0.07")) == "GT_0_05_TO_0_10_ATR"
    assert atlas._gap_band(Decimal("0.30")) == "GT_0_20_ATR"
