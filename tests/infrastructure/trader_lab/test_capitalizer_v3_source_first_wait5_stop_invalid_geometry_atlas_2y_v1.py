from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_stop_invalid_geometry_atlas_2y_v1 as atlas,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide


def test_stop_invalid_geometry_atlas_contract_is_frozen() -> None:
    assert atlas.EXPECTED_INVALID == 111
    assert atlas.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_"
        "STOP_INVALID_GEOMETRY_ATLAS_2Y_V1"
    )


def test_buffered_stop_preserves_v3_directional_buffer() -> None:
    assert atlas._buffered_stop(
        side=CapitalizerSide.LONG,
        pivot_price=Decimal("100"),
        buffer_price=Decimal("5"),
    ) == Decimal("95")
    assert atlas._buffered_stop(
        side=CapitalizerSide.SHORT,
        pivot_price=Decimal("100"),
        buffer_price=Decimal("5"),
    ) == Decimal("105")


def test_valid_stop_is_directional() -> None:
    assert atlas._valid_stop(
        side=CapitalizerSide.LONG,
        entry_price=Decimal("100"),
        stop_price=Decimal("95"),
    )
    assert not atlas._valid_stop(
        side=CapitalizerSide.LONG,
        entry_price=Decimal("90"),
        stop_price=Decimal("95"),
    )
    assert atlas._valid_stop(
        side=CapitalizerSide.SHORT,
        entry_price=Decimal("100"),
        stop_price=Decimal("105"),
    )
