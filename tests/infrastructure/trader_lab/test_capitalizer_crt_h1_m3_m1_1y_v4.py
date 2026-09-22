from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_crt_h1_m3_m1_1y_v4 import (
    CRTEvent,
    IDENTITY,
    MATRIX_IDENTITY,
    _target_geometry,
)


def test_v4_identity_is_separate() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_CRT_H1_M3_M1_1Y_V4"
    assert MATRIX_IDENTITY == "QORE_CAPITALIZER_NINE_MARKET_CRT_H1_M3_M1_1Y_V4"


def test_long_targets_use_reference_eq_and_high() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    event = CRTEvent(
        side=CapitalizerSide.LONG,
        reference_opened_at=now - timedelta(hours=1),
        reference_closed_at=now,
        reference_high=Decimal("110"),
        reference_low=Decimal("100"),
        reference_eq=Decimal("105"),
        n1_opened_at=now,
        n1_deadline=now + timedelta(hours=1),
        sweep_at=now + timedelta(minutes=5),
        sweep_extreme=Decimal("99"),
        m5_closeback_at=now + timedelta(minutes=10),
    )
    assert _target_geometry(
        crt=event,
        entry_price=Decimal("102"),
    ) == (Decimal("105"), Decimal("110"))


def test_short_targets_use_reference_eq_and_low() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    event = CRTEvent(
        side=CapitalizerSide.SHORT,
        reference_opened_at=now - timedelta(hours=1),
        reference_closed_at=now,
        reference_high=Decimal("110"),
        reference_low=Decimal("100"),
        reference_eq=Decimal("105"),
        n1_opened_at=now,
        n1_deadline=now + timedelta(hours=1),
        sweep_at=now + timedelta(minutes=5),
        sweep_extreme=Decimal("111"),
        m5_closeback_at=now + timedelta(minutes=10),
    )
    assert _target_geometry(
        crt=event,
        entry_price=Decimal("108"),
    ) == (Decimal("105"), Decimal("100"))


def test_target_geometry_fails_closed_when_tp1_is_behind_entry() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    event = CRTEvent(
        side=CapitalizerSide.LONG,
        reference_opened_at=now - timedelta(hours=1),
        reference_closed_at=now,
        reference_high=Decimal("110"),
        reference_low=Decimal("100"),
        reference_eq=Decimal("105"),
        n1_opened_at=now,
        n1_deadline=now + timedelta(hours=1),
        sweep_at=now + timedelta(minutes=5),
        sweep_extreme=Decimal("99"),
        m5_closeback_at=now + timedelta(minutes=10),
    )
    assert _target_geometry(
        crt=event,
        entry_price=Decimal("106"),
    ) is None
