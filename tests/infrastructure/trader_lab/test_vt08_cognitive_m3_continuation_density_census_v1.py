from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_m3_continuation_density_census_v1 import (
    SCHEMA,
    ContinuationOpportunity,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_m3_continuation_density_census_freeze() -> None:
    assert SCHEMA.endswith("m3_continuation_density_census.v1")
    item = ContinuationOpportunity(
        signal_at=datetime.now(UTC),
        side=DemoTradingSetupSide.LONG,
        entry=Decimal("2"),
        stop=Decimal("1"),
        destination=Decimal("4"),
        room_r=Decimal("2"),
    )
    assert item.room_r == Decimal("2")
