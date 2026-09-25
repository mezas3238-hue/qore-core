from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r93_fractal_cascade_density_validation as r93,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _m5(opened: datetime, value: int) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=5),
        open=Decimal(value),
        high=Decimal(value + 2),
        low=Decimal(value - 2),
        close=Decimal(value + 1),
    )


def test_r93_m15_requires_three_complete_m5_bars() -> None:
    t0 = datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
    bars = (
        _m5(t0, 100),
        _m5(t0 + timedelta(minutes=5), 101),
        _m5(t0 + timedelta(minutes=10), 102),
    )
    m15 = r93._complete_m15_from_m5(bars)
    assert len(m15) == 1
    assert m15[0].opened_at == t0
    assert m15[0].close == 103

    incomplete = r93._complete_m15_from_m5(bars[:2])
    assert incomplete == ()


def test_r93_source_run_and_identity_are_frozen() -> None:
    assert r93.SOURCE_R92_RUN_ID == 35530286516
    assert r93.IDENTITY == (
        "VT08_INDEX_R93_EXACT_FRACTAL_CASCADE_DENSITY_VALIDATION_001"
    )
