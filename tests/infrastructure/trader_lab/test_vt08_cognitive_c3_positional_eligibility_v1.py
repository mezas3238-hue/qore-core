from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_c3_positional_eligibility_v1 import (
    _geometry_valid,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_c3_positional_stop_geometry_is_directional() -> None:
    assert _geometry_valid(
        side=DemoTradingSetupSide.LONG,
        entry=Decimal("100"),
        stop=Decimal("99"),
    )
    assert not _geometry_valid(
        side=DemoTradingSetupSide.LONG,
        entry=Decimal("100"),
        stop=Decimal("101"),
    )
    assert _geometry_valid(
        side=DemoTradingSetupSide.SHORT,
        entry=Decimal("100"),
        stop=Decimal("101"),
    )
