from datetime import UTC, datetime, timedelta
from decimal import Decimal

import qore.infrastructure.trader_lab.capitalizer_v3_density_multi_mss_1y_v1 as d2
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_v3_density_multi_mss_1y_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    STOP_IDENTITY,
    TARGET_IDENTITY,
    M3MssEvent,
    _find_all_m3_mss,
)


def test_density_multi_mss_keeps_v3_economic_contract() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_DENSITY_MULTI_MSS_1Y_V1"
    assert (
        MATRIX_IDENTITY
        == "QORE_CAPITALIZER_NINE_MARKET_V3_DENSITY_MULTI_MSS_1Y_V1"
    )
    assert STOP_IDENTITY == "M3_BROKEN_SWING_PLUS_5_PIP_BUFFER"
    assert TARGET_IDENTITY == "FIXED_2R_OR_NEXT_H1_OPEN"


def test_multi_mss_empty_window_is_empty() -> None:
    now = datetime(2026, 9, 22, tzinfo=UTC)
    assert _find_all_m3_mss(
        (),
        (),
        (),
        after=now,
        before=now,
        side=CapitalizerSide.LONG,
    ) == ()


def test_multi_mss_cursor_advances_to_event_confirmation(monkeypatch) -> None:
    start = datetime(2026, 9, 22, 10, tzinfo=UTC)
    first_at = start + timedelta(minutes=9)
    second_at = start + timedelta(minutes=21)
    calls: list[datetime] = []

    def event(at: datetime) -> M3MssEvent:
        return M3MssEvent(
            side=CapitalizerSide.LONG,
            confirmed_at=at,
            displacement_opened_at=at - timedelta(minutes=3),
            displacement_closed_at=at,
            broken_swing_price=Decimal("100"),
            cisd_boundary=Decimal("99"),
            body_ratio=Decimal("0.70"),
            atr14=Decimal("1"),
            displacement_range=Decimal("2"),
        )

    events = iter((event(first_at), event(second_at), None))

    def fake_find(*args, after: datetime, **kwargs):
        calls.append(after)
        return next(events)

    monkeypatch.setattr(d2, "_find_m3_mss", fake_find)

    found = _find_all_m3_mss(
        (),
        (),
        (),
        after=start,
        before=start + timedelta(hours=1),
        side=CapitalizerSide.LONG,
    )

    assert [item.confirmed_at for item in found] == [first_at, second_at]
    assert calls == [start, first_at, second_at]
