"""Independent full-source oracle: causal as-of must match binary search exactly."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random

from qore.infrastructure.research_accelerator.asof import asof_pair
from qore.infrastructure.research_accelerator.real_source import _binary_reference


def test_oracle_agrees_on_gaps_crossed_and_no_pair() -> None:
    origin = datetime(2024, 3, 10, 8, tzinfo=UTC)
    def ms(n: int) -> datetime:
        return origin + timedelta(milliseconds=n)
    bids = (
        (ms(0), Decimal("100")),
        (ms(100), Decimal("101")),
        (ms(900), Decimal("102")),
        (ms(1400), Decimal("100")),
    )
    asks = (
        (ms(50), Decimal("100.5")),
        (ms(150), Decimal("101.5")),
        (ms(1000), Decimal("101")),
        (ms(1420), Decimal("100.2")),
    )
    expected, quarantine = _binary_reference(
        bids, asks, max_staleness_ms=250,
    )
    actual, observed_quarantine = asof_pair(
        bids, asks, max_staleness_ms=250,
    )
    assert expected == actual
    assert quarantine == observed_quarantine
    assert quarantine["no_pair"] > 0
    assert quarantine["stale"] > 0
    assert quarantine["crossed"] > 0


def test_oracle_agrees_on_randomized_disjoint_side_clocks() -> None:
    origin = datetime(2025, 1, 8, 15, tzinfo=UTC)
    for seed in range(30):
        rng = Random(seed)
        bid_ticks = []
        ask_ticks = []
        bt = 0
        at = 20
        for _ in range(100):
            bt += rng.randint(20, 180)
            at += rng.randint(30, 170)
            bid_ticks.append((
                origin + timedelta(milliseconds=bt),
                Decimal("100") + Decimal(rng.randint(0, 90)) / 100,
            ))
            ask_ticks.append((
                origin + timedelta(milliseconds=at),
                Decimal("101") + Decimal(rng.randint(0, 90)) / 100,
            ))
        bids = tuple(bid_ticks)
        asks = tuple(ask_ticks)
        expected, expected_counts = _binary_reference(
            bids, asks, max_staleness_ms=250,
        )
        actual, counts = asof_pair(bids, asks, max_staleness_ms=250)
        assert expected == actual, seed
        assert expected_counts == counts, seed
