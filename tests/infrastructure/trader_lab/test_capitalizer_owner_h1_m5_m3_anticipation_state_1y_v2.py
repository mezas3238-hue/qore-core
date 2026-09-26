from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_owner_h1_m5_m3_anticipation_state_1y_v2 import (
    ENTRY_IDENTITY,
    IDENTITY,
    MATRIX_IDENTITY,
    _h1_hour_bounds,
    _zone_overlap,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)


def test_owner_five_change_contract_identity() -> None:
    assert IDENTITY == (
        "QORE_CAPITALIZER_OWNER_H1_M5_M3_ANTICIPATION_STATE_1Y_V2"
    )
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_"
        "OWNER_H1_M5_M3_ANTICIPATION_STATE_1Y_V2"
    )
    assert "SWEEP_SESSION_STATE" in ENTRY_IDENTITY
    assert "H1_ANTICIPATION_TSPOT" in ENTRY_IDENTITY
    assert "M3_MSS" not in ENTRY_IDENTITY


def test_h1_hour_bounds_are_same_hour_deadline() -> None:
    moment = datetime(2026, 9, 22, 14, 37, tzinfo=UTC)
    opened, deadline = _h1_hour_bounds(moment)
    assert deadline - opened == timedelta(hours=1)
    assert opened.minute == 0
    assert deadline.minute == 0


def test_zone_overlap_remains_optional_confluence() -> None:
    assert _zone_overlap(
        Decimal("100"),
        Decimal("102"),
        Decimal("101"),
        Decimal("103"),
    ) == (Decimal("101"), Decimal("102"))
    assert _zone_overlap(
        Decimal("100"),
        Decimal("101"),
        Decimal("102"),
        Decimal("103"),
    ) is None


def test_aggregated_bar_shape_is_available_for_h1_context() -> None:
    now = datetime(2026, 9, 22, 14, 0, tzinfo=UTC)
    bar = AggregatedBar(
        opened_at=now,
        closed_at=now + timedelta(hours=1),
        source=CapitalizerSourceBar(
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("99"),
            close=Decimal("101"),
        ),
        minute_count=60,
    )
    assert bar.source.low == Decimal("99")
