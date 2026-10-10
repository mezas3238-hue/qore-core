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


def _long_zone() -> OTEZone:
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


def _short_zone() -> OTEZone:
    return OTEZone(
        impulse_start=Decimal("110"),
        impulse_end=Decimal("100"),
        level_050=Decimal("105"),
        level_062=Decimal("106.2"),
        level_0705=Decimal("107.05"),
        level_079=Decimal("107.9"),
        zone_low=Decimal("106.2"),
        zone_high=Decimal("107.9"),
    )


def test_v5_identity_is_separate() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_CRT_H1_M3_M1_OTE_1Y_V5"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_CRT_H1_M3_M1_OTE_1Y_V5"
    )


def test_long_absorption_in_062_to_0705_enters_without_waiting_for_079() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="103.6",
            high="103.7",
            low="103.2",
            close="103.4",
        ),
        _bar(
            now + timedelta(minutes=1),
            open_price="103.3",
            high="103.8",
            low="103.3",
            close="103.6",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.LONG,
        zone=_long_zone(),
        after=now,
    )
    assert status == "ABSORPTION_IN_OTE"
    assert reaction is not None
    assert reaction.absorption_bucket == "0.62_TO_0.705"
    assert reaction.level_079_touched is False


def test_long_absorption_in_0705_to_079_enters() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="102.9",
            high="103.0",
            low="102.5",
            close="102.7",
        ),
        _bar(
            now + timedelta(minutes=1),
            open_price="102.6",
            high="103.2",
            low="102.6",
            close="103.0",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.LONG,
        zone=_long_zone(),
        after=now,
    )
    assert status == "ABSORPTION_IN_OTE"
    assert reaction is not None
    assert reaction.absorption_bucket == "0.705_TO_0.79"


def test_short_absorption_anywhere_in_ote_enters() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="106.6",
            high="106.9",
            low="106.5",
            close="106.8",
        ),
        _bar(
            now + timedelta(minutes=1),
            open_price="106.9",
            high="106.9",
            low="106.4",
            close="106.6",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.SHORT,
        zone=_short_zone(),
        after=now,
    )
    assert status == "ABSORPTION_IN_OTE"
    assert reaction is not None
    assert reaction.absorption_bucket == "0.62_TO_0.705"


def test_wick_through_079_can_reject_if_close_does_not_invalidate() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="102.5",
            high="102.6",
            low="101.9",
            close="102.3",
        ),
        _bar(
            now + timedelta(minutes=1),
            open_price="102.2",
            high="102.7",
            low="102.2",
            close="102.5",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.LONG,
        zone=_long_zone(),
        after=now,
    )
    assert status == "ABSORPTION_IN_OTE"
    assert reaction is not None
    assert reaction.level_079_touched is True
    assert reaction.absorption_retracement == Decimal("0.79")


def test_close_through_079_invalidates_before_absorption() -> None:
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
        zone=_long_zone(),
        after=now,
    )
    assert status == "INVALIDATED_CLOSE_THROUGH_079"
    assert reaction is None


def test_zone_touch_without_two_candle_absorption_does_not_enter() -> None:
    now = datetime(2026, 9, 22, 13, 0, tzinfo=UTC)
    bars = (
        _bar(
            now,
            open_price="103.6",
            high="103.7",
            low="103.2",
            close="103.4",
        ),
        _bar(
            now + timedelta(minutes=1),
            open_price="103.5",
            high="103.6",
            low="103.3",
            close="103.45",
        ),
    )
    status, reaction = _find_ote_reaction(
        bars,
        side=CapitalizerSide.LONG,
        zone=_long_zone(),
        after=now,
    )
    assert status == "OTE_INTERACTION_NO_ABSORPTION"
    assert reaction is None
