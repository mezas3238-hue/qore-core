from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_v3_fibonacci_ab_1y_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    STOP_IDENTITY,
    TARGET_IDENTITY,
    OTEZone,
    _find_ote_fill,
)


def _bar(
    at: datetime,
    *,
    o: str,
    h: str,
    low: str,
    c: str,
) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
        volume=None,
        digits=5,
    )


def test_identity_and_v3_downstream_contract() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_FIBONACCI_AB_1Y_V1"
    assert MATRIX_IDENTITY == "QORE_CAPITALIZER_NINE_MARKET_V3_FIBONACCI_AB_1Y_V1"
    assert STOP_IDENTITY == "M3_BROKEN_SWING_PLUS_5_PIP_BUFFER"
    assert TARGET_IDENTITY == "FIXED_2R_OR_NEXT_H1_OPEN"


def test_ote_absorption_can_enter_before_079() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    zone = OTEZone(
        impulse_start=Decimal("100"),
        impulse_end=Decimal("110"),
        level_062=Decimal("103.8"),
        level_0705=Decimal("102.95"),
        level_079=Decimal("102.1"),
        zone_low=Decimal("102.1"),
        zone_high=Decimal("103.8"),
    )
    bars = (
        _bar(now, o="103.6", h="103.7", low="103.2", c="103.4"),
        _bar(now + timedelta(minutes=1), o="103.3", h="103.8", low="103.3", c="103.6"),
    )

    class Event:
        side = CapitalizerSide.LONG
        confirmed_at = now

    status, reaction = _find_ote_fill(
        bars,
        event=Event(),  # type: ignore[arg-type]
        zone=zone,
        deadline=now + timedelta(hours=1),
    )
    assert status == "ABSORPTION"
    assert reaction is not None
    assert reaction.bucket == "0.62_TO_0.705"


def test_close_through_079_invalidates() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    zone = OTEZone(
        impulse_start=Decimal("100"),
        impulse_end=Decimal("110"),
        level_062=Decimal("103.8"),
        level_0705=Decimal("102.95"),
        level_079=Decimal("102.1"),
        zone_low=Decimal("102.1"),
        zone_high=Decimal("103.8"),
    )
    bars = (_bar(now, o="102.4", h="102.5", low="101.8", c="101.9"),)

    class Event:
        side = CapitalizerSide.LONG
        confirmed_at = now

    status, reaction = _find_ote_fill(
        bars,
        event=Event(),  # type: ignore[arg-type]
        zone=zone,
        deadline=now + timedelta(hours=1),
    )
    assert status == "INVALIDATED_079"
    assert reaction is None
