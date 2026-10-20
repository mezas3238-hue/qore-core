from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.crt_pure_candidate_replay import (
    CrtPureReplayCandle,
    detect_candidate_formation,
    scan_candidate_formations,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
    CrtPureRangeOutcome,
)


def _candle(
    *,
    market: CrtPureMarket = CrtPureMarket.AUDUSD,
    minute: int,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> CrtPureReplayCandle:
    opened = datetime(2026, 1, 2, 12, minute, tzinfo=UTC)
    return CrtPureReplayCandle(
        market=market,
        opened_at=opened,
        closed_at=opened + timedelta(minutes=5),
        open_price=Decimal(open_price),
        high_price=Decimal(high),
        low_price=Decimal(low),
        close_price=Decimal(close),
    )


def test_replay_formation_becomes_visible_only_at_event_close() -> None:
    reference = _candle(
        minute=0,
        open_price="1.1000",
        high="1.1020",
        low="1.0980",
        close="1.1010",
    )
    observed = _candle(
        minute=5,
        open_price="1.1010",
        high="1.1030",
        low="1.0990",
        close="1.1015",
    )
    formation = detect_candidate_formation(reference, observed)
    assert formation.outcome is CrtPureRangeOutcome.TURTLE_SOUP
    assert formation.direction is CrtPureCandidateDirection.BEARISH
    assert formation.causal_at == observed.closed_at
    assert formation.execution_authorized is False
    assert formation.research_only is True
    assert formation.midpoint == Decimal("1.1")
    assert formation.opposite_edge == Decimal("1.0980")


def test_replay_rejects_future_or_overlapping_reference() -> None:
    reference = _candle(
        minute=5,
        open_price="1.1000",
        high="1.1020",
        low="1.0980",
        close="1.1010",
    )
    observed = _candle(
        minute=0,
        open_price="1.1010",
        high="1.1030",
        low="1.0990",
        close="1.1015",
    )
    with pytest.raises(ValueError, match="overlapping/future"):
        detect_candidate_formation(reference, observed)


def test_scan_requires_one_market_and_chronological_order() -> None:
    first = _candle(
        minute=0,
        open_price="1.1000",
        high="1.1020",
        low="1.0980",
        close="1.1010",
    )
    second = _candle(
        minute=5,
        open_price="1.1010",
        high="1.1030",
        low="1.0990",
        close="1.1015",
    )
    third = _candle(
        market=CrtPureMarket.USDJPY,
        minute=10,
        open_price="150.0",
        high="151.0",
        low="149.0",
        close="150.5",
    )
    assert len(scan_candidate_formations((first, second))) == 1

    with pytest.raises(ValueError, match="chronological"):
        scan_candidate_formations((second, first))

    with pytest.raises(ValueError, match="exactly one market"):
        scan_candidate_formations((first, third))


def test_replay_candle_enforces_valid_ohlc() -> None:
    with pytest.raises(ValueError, match="open must be inside"):
        _candle(
            minute=0,
            open_price="2.0",
            high="1.5",
            low="1.0",
            close="1.2",
        )
