from qore.infrastructure.trader_lab import (
    capitalizer_v3_only_causal_series_atlas_2y_v1 as atlas,
)


def test_v3_only_causal_series_contract_is_frozen() -> None:
    assert atlas.IDENTITY == "QORE_CAPITALIZER_V3_ONLY_CAUSAL_SERIES_ATLAS_2Y_V1"
    assert atlas.EXPECTED_V3_ONLY == 87
    assert atlas.SOURCE_NOT_AVAILABLE == "SOURCE_BOUNDARY_NOT_YET_AVAILABLE"
    assert atlas.NEW_POST_SWEEP_RESET == "NEW_POST_SWEEP_SERIES_RESET"


def test_v3_only_boundary_relation_is_side_aware() -> None:
    from decimal import Decimal

    assert atlas._boundary_relation(
        Decimal("99"), Decimal("100"), atlas.CapitalizerSide.LONG
    ) == "CURRENT_EASIER"
    assert atlas._boundary_relation(
        Decimal("101"), Decimal("100"), atlas.CapitalizerSide.SHORT
    ) == "CURRENT_EASIER"
