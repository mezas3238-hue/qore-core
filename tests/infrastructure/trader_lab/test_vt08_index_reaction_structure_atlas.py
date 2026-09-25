from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_market_journey_atlas import Bar
from qore.infrastructure.trader_lab.vt08_index_reaction_structure_atlas import (
    _breaker_zones,
    _order_block_zones,
    _segment_behavior,
    _zone_retests,
)


def _bar(
    minute: int,
    *,
    opened: str,
    high: str,
    low: str,
    closed: str,
) -> Bar:
    start = datetime(2024, 1, 2, 10, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return Bar(
        opened_at=start,
        closed_at=start + timedelta(minutes=15),
        open=Decimal(opened),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(closed),
    )


def test_cisd_confirmed_order_block_requires_retest_before_signal() -> None:
    bars = (
        _bar(0, opened="10", high="10.2", low="8.8", closed="9"),
        _bar(15, opened="9", high="10.8", low="8.9", closed="10.5"),
        _bar(30, opened="10.4", high="10.6", low="9.1", closed="9.6"),
    )
    zones = _order_block_zones(bars[:2])
    assert len(zones) == 1
    zone = zones[0]
    assert zone.kind == "order-block"
    assert zone.side == "bullish"
    assert zone.low == Decimal("8.8")
    assert zone.high == Decimal("10.2")

    signal_after_retest = bars[-1].closed_at + timedelta(minutes=15)
    retests = _zone_retests(zones, bars, signal_after_retest)
    assert retests
    assert retests[-1]["kind"] == "order-block"

    same_bar_signal = bars[-1].closed_at
    assert not _zone_retests(zones, bars, same_bar_signal)


def test_ttrades_bullish_breaker_sequence_is_detected() -> None:
    bars = (
        _bar(0, opened="10", high="10.5", low="9.5", closed="10.1"),
        _bar(15, opened="9.2", high="10.2", low="8", closed="9.8"),
        _bar(30, opened="9.8", high="12", low="9", closed="11.5"),
        _bar(45, opened="9", high="10", low="7", closed="9.4"),
        _bar(60, opened="10", high="13", low="8.5", closed="12.5"),
        _bar(75, opened="12", high="12.2", low="9", closed="10"),
    )
    zones = _breaker_zones(bars)
    bullish = [zone for zone in zones if zone.side == "bullish"]
    assert bullish
    assert bullish[0].definition == "ttrades-low-high-lower-low-higher-high"


def test_behavior_descriptors_are_diagnostic_not_economic() -> None:
    balanced = (
        _bar(0, opened="10", high="10.2", low="9.8", closed="9.9"),
        _bar(15, opened="9.9", high="10.2", low="9.8", closed="10.1"),
        _bar(30, opened="10.1", high="10.2", low="9.8", closed="9.9"),
        _bar(45, opened="9.9", high="10.2", low="9.8", closed="10"),
    )
    payload = _segment_behavior(balanced)
    assert payload["descriptor"] == "accumulation-like"
    assert int(str(payload["body_flip_count"])) >= 2

    expansion = (
        _bar(0, opened="10", high="10.2", low="9.9", closed="10.1"),
        _bar(15, opened="10.1", high="10.8", low="10", closed="10.7"),
        _bar(30, opened="10.7", high="11.5", low="10.6", closed="11.4"),
    )
    assert _segment_behavior(expansion)["descriptor"] == "expansion-like"
