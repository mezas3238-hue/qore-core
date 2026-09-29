from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_event_opposite_boundary_v47_s1r_e as audit,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def _bar(
    opened_at: datetime,
    *,
    high: Decimal,
    low: Decimal,
) -> CapitalizerM1Bar:
    mid = (high + low) / Decimal("2")
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=mid,
        high=high,
        low=low,
        close=mid,
        volume=None,
        digits=5,
    )


def test_previous_day_pair_returns_exact_range_and_known_time() -> None:
    start = datetime(2025, 1, 5, 14, 0, tzinfo=UTC)
    bars = tuple(
        _bar(
            start + timedelta(minutes=index),
            high=Decimal("1.1100") + Decimal(index) / Decimal("100000"),
            low=Decimal("1.0900") - Decimal(index) / Decimal("100000"),
        )
        for index in range(61)
    )
    prepared = audit.s1._prepare_source_series(bars)

    pair = audit._previous_day_pair(
        prepared,
        operating_day=date(2025, 1, 6),
    )

    assert pair is not None
    high, low, known_at = pair
    assert high == max(row.high for row in bars)
    assert low == min(row.low for row in bars)
    assert known_at == bars[-1].closed_at


def test_matching_h1_swing_recovers_same_pivot_opposite_extreme() -> None:
    start = datetime(2025, 1, 6, 10, 0, tzinfo=UTC)
    hourly = (
        (Decimal("101"), Decimal("95")),
        (Decimal("102"), Decimal("95")),
        (Decimal("105"), Decimal("94")),
        (Decimal("102"), Decimal("95")),
        (Decimal("101"), Decimal("95")),
    )
    bars: list[CapitalizerM1Bar] = []
    for hour, (high, low) in enumerate(hourly):
        opened = start + timedelta(hours=hour)
        bars.extend(
            _bar(
                opened + timedelta(minutes=minute),
                high=high,
                low=low,
            )
            for minute in range(60)
        )
    prepared = audit.s1._prepare_source_series(tuple(bars))

    match = audit._latest_matching_h1_swing_pivot(
        prepared,
        kind="HIGH",
        price=Decimal("105"),
        before=start + timedelta(hours=5),
    )

    assert match is not None
    pivot, known_at = match
    assert pivot.source.high == Decimal("105")
    assert pivot.source.low == Decimal("94")
    assert known_at == start + timedelta(hours=5)


def test_directional_ahead_law_is_frozen() -> None:
    from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
        CapitalizerSide,
    )

    assert audit._ahead(
        Decimal("101"),
        Decimal("100"),
        CapitalizerSide.LONG,
    )
    assert not audit._ahead(
        Decimal("99"),
        Decimal("100"),
        CapitalizerSide.LONG,
    )
    assert audit._ahead(
        Decimal("99"),
        Decimal("100"),
        CapitalizerSide.SHORT,
    )
    assert not audit._ahead(
        Decimal("101"),
        Decimal("100"),
        CapitalizerSide.SHORT,
    )


def test_report_requires_complete_classification_coverage() -> None:
    with pytest.raises(ValueError, match="classification coverage drift"):
        audit.EventBoundaryPeriodMarketReport(
            identity=audit.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            source_events=2,
            aligned_h1_strict_m15_events=2,
            classification_counts={
                audit.OppositeBoundaryClass.EVENT_OPPOSITE_BOUNDARY_VALID.value: 1,
            },
            current_target_relation_counts={
                audit.CurrentTargetSetRelation.PRESENT_UNIQUE_CURRENT_SET.value: 2,
            },
            valid_event_opposite_boundaries=1,
            valid_hidden_inside_multi_target_ambiguity=0,
        )
