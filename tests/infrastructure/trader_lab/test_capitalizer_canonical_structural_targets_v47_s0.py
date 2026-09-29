from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_structural_targets_v47_s0 as targets,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
)


def _bar(
    opened_at: datetime,
    *,
    open_: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def _hour(
    start: datetime,
    *,
    high: str,
    low: str = "99",
) -> tuple[CapitalizerM1Bar, ...]:
    return tuple(
        _bar(
            start + timedelta(minutes=minute),
            high=high,
            low=low,
        )
        for minute in range(60)
    )


def test_exact_source_frame_requires_every_underlying_m1_minute() -> None:
    start = datetime(2025, 1, 6, 10, 0, tzinfo=UTC)
    complete = _hour(start, high="105")
    frames = targets.build_exact_source_frames(complete)
    assert len(frames["H1"]) == 1
    assert frames["H1"][0].source.high == Decimal("105")

    missing = tuple(row for index, row in enumerate(complete) if index != 17)
    incomplete = targets.build_exact_source_frames(missing)
    assert incomplete["H1"] == ()


def test_source_opposite_boundary_can_resolve_single_structural_target() -> None:
    start = datetime(2025, 1, 6, 10, 0, tzinfo=UTC)
    bars = tuple(
        _bar(start + timedelta(minutes=minute), high="102", low="98")
        for minute in range(30)
    )
    decision = start + timedelta(minutes=30)
    binding = targets.bind_structural_target(
        bars,
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        decision_at=decision,
        source_opposite_boundary=targets.S0SourceOppositeBoundary(
            target_price=Decimal("110"),
            known_at=start,
            source_timeframe="H1",
        ),
    )

    assert binding.resolution.resolved is True
    assert binding.resolution.observation is not None
    assert binding.resolution.observation.target_price == Decimal("110")
    assert (
        binding.resolution.target_kind
        is CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE
    )
    assert binding.outcome_used is False
    assert binding.interpolation_used is False


def test_touched_source_opposite_boundary_is_not_available() -> None:
    start = datetime(2025, 1, 6, 10, 0, tzinfo=UTC)
    bars = (
        *tuple(
            _bar(start + timedelta(minutes=minute), high="102", low="98")
            for minute in range(10)
        ),
        _bar(
            start + timedelta(minutes=10),
            high="111",
            low="99",
        ),
        *tuple(
            _bar(start + timedelta(minutes=minute), high="102", low="98")
            for minute in range(11, 30)
        ),
    )
    binding = targets.bind_structural_target(
        tuple(bars),
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        decision_at=start + timedelta(minutes=30),
        source_opposite_boundary=targets.S0SourceOppositeBoundary(
            target_price=Decimal("110"),
            known_at=start,
            source_timeframe="H1",
        ),
    )

    assert binding.candidates == ()
    assert binding.resolution.resolved is False
    assert binding.resolution.reasons == ("NO_ELIGIBLE_STRUCTURAL_TARGET",)


def test_multiple_distinct_targets_remain_unresolved_without_priority() -> None:
    start = datetime(2025, 1, 6, 10, 0, tzinfo=UTC)
    prior_hour = _hour(start, high="105")
    current_partial = tuple(
        _bar(
            start + timedelta(hours=1, minutes=minute),
            high="102",
            low="98",
        )
        for minute in range(30)
    )
    decision = start + timedelta(hours=1, minutes=30)

    binding = targets.bind_structural_target(
        tuple((*prior_hour, *current_partial)),
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        decision_at=decision,
        source_opposite_boundary=targets.S0SourceOppositeBoundary(
            target_price=Decimal("110"),
            known_at=start,
            source_timeframe="H1",
        ),
    )

    assert {
        (item.kind, item.target_price)
        for item in binding.candidates
    } == {
        (
            CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
            Decimal("105"),
        ),
        (
            CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
            Decimal("110"),
        ),
    }
    assert binding.resolution.resolved is False
    assert binding.resolution.reasons == (
        "MULTIPLE_STRUCTURAL_TARGETS_REVIEW_REQUIRED",
    )
