from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_scalping_standard_h1_m15_m1_1y_v1 import (
    ENTRY_IDENTITY,
    IDENTITY,
    MATRIX_IDENTITY,
    PARENT_STRUCTURE_TIMEFRAME,
    Pivot,
    TFBar,
    _find_m15_parent_structure,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)


def _source(o: str, h: str, low: str, c: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


def test_variant_a_is_predeclared_h1_m15_m1_without_m5_gate() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_SCALPING_STANDARD_H1_M15_M1_1Y_V1"
    assert MATRIX_IDENTITY.endswith("SCALPING_STANDARD_H1_M15_M1_1Y_MATRIX_V1")
    assert PARENT_STRUCTURE_TIMEFRAME == "M15"
    assert ENTRY_IDENTITY == (
        "H1_C2C3__PRIOR_SESSION_SWEEP__M15_BREAK__M1_MSS_FVG_CE"
    )
    assert "M5" not in ENTRY_IDENTITY


def test_m15_parent_can_authorize_structure_without_m5_dependency() -> None:
    t0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    bars = (
        TFBar(
            t0,
            t0 + timedelta(minutes=15),
            _source("100", "101", "99", "100"),
        ),
        TFBar(
            t0 + timedelta(minutes=15),
            t0 + timedelta(minutes=30),
            _source("100", "102", "99.5", "101.5"),
        ),
        TFBar(
            t0 + timedelta(minutes=30),
            t0 + timedelta(minutes=45),
            _source("101.5", "103", "101", "102.5"),
        ),
    )
    pivots = (
        Pivot(
            occurred_at=t0 - timedelta(minutes=10),
            confirmed_at=t0 - timedelta(minutes=5),
            price=Decimal("102"),
            kind="HIGH",
        ),
        Pivot(
            occurred_at=t0 - timedelta(minutes=8),
            confirmed_at=t0 - timedelta(minutes=4),
            price=Decimal("99"),
            kind="LOW",
        ),
    )

    event = _find_m15_parent_structure(
        bars,
        pivots,
        after=t0,
        before=t0 + timedelta(hours=1),
        side=CapitalizerSide.LONG,
    )

    assert event is not None
    assert event.timeframe == "M15"
    assert event.break_price == Decimal("102")
    assert event.protected_swing_price == Decimal("99")
