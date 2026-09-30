from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_body_readiness_atlas_2y_v1 as atlas,
)


def test_body_readiness_contract_is_frozen() -> None:
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_BODY_READINESS_ATLAS_2Y_V1"
    )
    assert atlas.EXPECTED_BODY_BLOCKERS == 825
    assert atlas.FROZEN_BODY_RATIO == Decimal("0.60")


def test_body_bands_are_deterministic() -> None:
    assert atlas._body_band(None) == "NO_RATIO"
    assert atlas._body_band(Decimal("0.39")) == "LT_0_40"
    assert atlas._body_band(Decimal("0.52")) == "0_50_TO_LT_0_55"
    assert atlas._body_band(Decimal("0.58")) == "0_55_TO_LT_0_60"
