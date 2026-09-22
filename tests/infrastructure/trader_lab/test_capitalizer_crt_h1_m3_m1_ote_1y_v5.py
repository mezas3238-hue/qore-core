from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_crt_h1_m3_m1_ote_1y_v5 import (
    IDENTITY,
    MATRIX_IDENTITY,
    OTEZone,
    _find_ote_reaction,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)


def _bar(
    at: datetime,
    *,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def _zone() -> OTEZone:
    return OTEZone(
        impulse_start=Decimal("100"),
        impulse_end=Decimal("110"),
        level_050=Decimal("105"),
        level_062=Decimal("103.8"),
        level_0705=Decimal("102.95"),
        level_079=Decimal("102.1"),
        zone_low=Decimal("102.1"),
        zone_high=Decimal("103.8"),
    )


def test_v5_identity_is_separate() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_CRT_H1_M3_M1_OTE_1Y_V5"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_CRT_H1_M3_M1_OTE_1Y_V5"
    )


def test_zone_touch_without_079_does_not_enter() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="104.0",
            high="104.1",
            low="103.0",
            close="103.7",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.LONG,
        zone=_zone(),
        after=now,
    )
    assert status == "OTE_ONLY_NO_079_TOUCH"
    assert reaction is None


def test_long_requires_two_candle_absorption_at_079() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="102.5",
            high="102.6",
            low="102.1",
            close="102.3",
        ),
        _bar(
            now + timedelta(minutes=1),
            open_price="102.2",
            high="102.8",
            low="102.2",
            close="102.6",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.LONG,
        zone=_zone(),
        after=now,
    )
    assert status == "ABSORPTION_AT_079"
    assert reaction is not None
    assert reaction.reaction_type == "TWO_CANDLE_ABSORPTION_AT_079"
    assert reaction.index == 1


def test_short_requires_two_candle_absorption_at_079() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    zone = OTEZone(
        impulse_start=Decimal("110"),
        impulse_end=Decimal("100"),
        level_050=Decimal("105"),
        level_062=Decimal("106.2"),
        level_0705=Decimal("107.05"),
        level_079=Decimal("107.9"),
        zone_low=Decimal("106.2"),
        zone_high=Decimal("107.9"),
    )
    bars = (
        _bar(
            now,
            open_price="107.4",
            high="107.9",
            low="107.3",
            close="107.7",
        ),
        _bar(
            now + timedelta(minutes=1),
            open_price="107.8",
            high="107.8",
            low="107.1",
            close="107.5",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.SHORT,
        zone=zone,
        after=now,
    )
    assert status == "ABSORPTION_AT_079"
    assert reaction is not None
    assert reaction.index == 1


def test_close_through_079_invalidates_before_entry() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="102.4",
            high="102.5",
            low="101.8",
            close="101.9",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.LONG,
        zone=_zone(),
        after=now,
    )
    assert status == "INVALIDATED_CLOSE_THROUGH_079"
    assert reaction is None


def test_single_rejection_candle_is_not_enough() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="102.5",
            high="102.6",
            low="102.1",
            close="102.3",
        ),
        _bar(
            now + timedelta(minutes=1),
            open_price="102.4",
            high="102.5",
            low="102.2",
            close="102.35",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.LONG,
        zone=_zone(),
        after=now,
    )
    assert status == "TOUCHED_079_NO_ABSORPTION"
    assert reaction is None
