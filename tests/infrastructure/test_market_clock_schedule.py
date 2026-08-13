from __future__ import annotations

import inspect
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.market_clock_schedule as schedule_module
from qore.infrastructure.market_clock_schedule import (
    MarketClockScheduleValidationError,
    ScheduleBTrigger,
    WallClockBoundary,
    WallClockTransition,
    derive_schedule_b_instants,
    derive_wall_clock_transitions,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_event_replay import (
    MarketCaptureLineageId,
    MarketCaptureSessionId,
    MarketCaptureSessionOrdinal,
    MarketEventAvailabilityBasis,
    MarketEventAvailabilityEvidenceReference,
    MarketEventObservationId,
    MarketIngressSequence,
    RetainedMarketEventObservation,
)
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketPrice,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(1)),
        source_id=SourceId(_uuid(2)),
        port_name=PortName("market-data.schedule-b-test"),
    )


def _event(
    *,
    suffix: int,
    sequence: int,
    available_at: datetime,
    receipt_offset_ms: int = 0,
) -> RetainedMarketEventObservation:
    observed_at = available_at - timedelta(seconds=2)
    quote = QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(_uuid(100 + suffix)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        observed_at=observed_at,
        bid=MarketPrice(Decimal("1.1000")),
        ask=MarketPrice(Decimal("1.1001")),
        evidence_ref=MarketObservationEvidenceReference(_uuid(200 + suffix)),
    )
    received_at = observed_at + timedelta(seconds=1, milliseconds=receipt_offset_ms)
    core_ingress_at = received_at + timedelta(milliseconds=1)
    return RetainedMarketEventObservation(
        event_id=MarketEventObservationId(_uuid(300 + suffix)),
        payload=quote,
        capture_lineage_id=MarketCaptureLineageId(_uuid(400)),
        capture_session_id=MarketCaptureSessionId(_uuid(500)),
        capture_session_ordinal=MarketCaptureSessionOrdinal(0),
        ingress_sequence=MarketIngressSequence(sequence),
        boundary_received_at=received_at,
        core_ingress_at=core_ingress_at,
        availability_evidence_at=core_ingress_at,
        available_at=available_at,
        availability_basis=MarketEventAvailabilityBasis.CORE_INGRESS,
        availability_evidence_ref=MarketEventAvailabilityEvidenceReference(
            _uuid(600 + suffix)
        ),
    )


def test_wall_clock_summer_and_winter_follow_new_york_iana_offsets() -> None:
    boundaries = (WallClockBoundary(9),)

    summer = derive_wall_clock_transitions(
        simulated_start=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 7, 2, 0, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=boundaries,
    )
    winter = derive_wall_clock_transitions(
        simulated_start=datetime(2026, 1, 15, 0, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 1, 16, 0, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=boundaries,
    )

    assert tuple(item.simulated_now for item in summer) == (
        datetime(2026, 7, 1, 13, 0, tzinfo=UTC),
    )
    assert tuple(item.simulated_now for item in winter) == (
        datetime(2026, 1, 15, 14, 0, tzinfo=UTC),
    )


def test_spring_forward_does_not_fabricate_nonexistent_local_boundary() -> None:
    transitions = derive_wall_clock_transitions(
        simulated_start=datetime(2026, 3, 8, 5, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 3, 8, 9, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=(WallClockBoundary(2, 30), WallClockBoundary(3)),
    )

    assert tuple(item.boundary for item in transitions) == (WallClockBoundary(3),)
    assert transitions[0].simulated_now == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)


def test_fall_back_ambiguous_local_boundary_fails_closed() -> None:
    with pytest.raises(MarketClockScheduleValidationError):
        derive_wall_clock_transitions(
            simulated_start=datetime(2026, 11, 1, 4, 0, tzinfo=UTC),
            simulated_end=datetime(2026, 11, 1, 8, 0, tzinfo=UTC),
            timezone_name="America/New_York",
            boundaries=(WallClockBoundary(1, 30),),
        )


def test_half_open_window_includes_start_and_excludes_end() -> None:
    transitions = derive_wall_clock_transitions(
        simulated_start=datetime(2026, 8, 12, 13, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 8, 12, 14, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=(WallClockBoundary(9), WallClockBoundary(10)),
    )

    assert tuple(item.simulated_now for item in transitions) == (
        datetime(2026, 8, 12, 13, 0, tzinfo=UTC),
    )


def test_wall_clock_transition_rejects_fractional_second_instant() -> None:
    with pytest.raises(MarketClockScheduleValidationError):
        WallClockTransition(
            simulated_now=datetime(
                2026,
                8,
                12,
                13,
                0,
                0,
                500_000,
                tzinfo=UTC,
            ),
            timezone_name="America/New_York",
            local_date=date(2026, 8, 12),
            boundary=WallClockBoundary(9),
        )


def test_clock_only_instants_exist_without_market_events() -> None:
    result = derive_schedule_b_instants(
        (),
        simulated_start=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 8, 12, 22, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=(WallClockBoundary(9), WallClockBoundary(16), WallClockBoundary(17)),
    )

    assert tuple(item.simulated_now for item in result) == (
        datetime(2026, 8, 12, 13, 0, tzinfo=UTC),
        datetime(2026, 8, 12, 20, 0, tzinfo=UTC),
        datetime(2026, 8, 12, 21, 0, tzinfo=UTC),
    )
    assert all(item.triggers == (ScheduleBTrigger.WALL_CLOCK,) for item in result)


def test_market_only_instant_is_retained_in_arrival_order() -> None:
    first = _event(
        suffix=1,
        sequence=1,
        available_at=datetime(2026, 8, 12, 18, 0, tzinfo=UTC),
    )
    second = _event(
        suffix=2,
        sequence=2,
        available_at=datetime(2026, 8, 12, 18, 0, tzinfo=UTC),
        receipt_offset_ms=2,
    )

    result = derive_schedule_b_instants(
        (second, first),
        simulated_start=datetime(2026, 8, 12, 17, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 8, 12, 19, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=(),
    )

    assert len(result) == 1
    assert result[0].newly_available_market_events == (first, second)
    assert result[0].wall_clock_transitions == ()
    assert result[0].triggers == (ScheduleBTrigger.MARKET_DATA,)


def test_market_and_wall_clock_collision_produces_one_instant_with_both_causes() -> None:
    sixteen_ny = datetime(2026, 8, 12, 20, 0, tzinfo=UTC)
    event = _event(suffix=3, sequence=1, available_at=sixteen_ny)

    result = derive_schedule_b_instants(
        (event,),
        simulated_start=datetime(2026, 8, 12, 19, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 8, 12, 21, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=(WallClockBoundary(16),),
    )

    assert len(result) == 1
    instant = result[0]
    assert instant.simulated_now == sixteen_ny
    assert instant.newly_available_market_events == (event,)
    assert tuple(item.boundary for item in instant.wall_clock_transitions) == (
        WallClockBoundary(16),
    )
    assert instant.triggers == (
        ScheduleBTrigger.MARKET_DATA,
        ScheduleBTrigger.WALL_CLOCK,
    )


def test_input_permutation_and_duplicate_boundaries_do_not_change_schedule() -> None:
    first = _event(
        suffix=4,
        sequence=1,
        available_at=datetime(2026, 8, 12, 18, 0, tzinfo=UTC),
    )
    second = _event(
        suffix=5,
        sequence=2,
        available_at=datetime(2026, 8, 12, 19, 0, tzinfo=UTC),
        receipt_offset_ms=2,
    )
    boundaries = (
        WallClockBoundary(16),
        WallClockBoundary(9),
        WallClockBoundary(16),
    )

    left = derive_schedule_b_instants(
        (second, first),
        simulated_start=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 8, 12, 21, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=boundaries,
    )
    right = derive_schedule_b_instants(
        (first, second),
        simulated_start=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
        simulated_end=datetime(2026, 8, 12, 21, 0, tzinfo=UTC),
        timezone_name="America/New_York",
        boundaries=tuple(reversed(boundaries)),
    )

    assert tuple(item.logical_values() for item in left) == tuple(
        item.logical_values() for item in right
    )
    sixteen = next(
        item
        for item in left
        if item.simulated_now == datetime(2026, 8, 12, 20, 0, tzinfo=UTC)
    )
    assert len(sixteen.wall_clock_transitions) == 1


def test_invalid_timezone_boundary_and_window_fail_closed() -> None:
    with pytest.raises(MarketClockScheduleValidationError):
        derive_wall_clock_transitions(
            simulated_start=datetime(2026, 8, 12, 0, 0, tzinfo=UTC),
            simulated_end=datetime(2026, 8, 13, 0, 0, tzinfo=UTC),
            timezone_name="Not/AZone",
            boundaries=(WallClockBoundary(9),),
        )
    with pytest.raises(MarketClockScheduleValidationError):
        derive_wall_clock_transitions(
            simulated_start=datetime(2026, 8, 12, 0, 0, tzinfo=UTC),
            simulated_end=datetime(2026, 8, 13, 0, 0, tzinfo=UTC),
            timezone_name="../America/New_York",
            boundaries=(WallClockBoundary(9),),
        )
    with pytest.raises(MarketClockScheduleValidationError):
        WallClockBoundary(24)
    with pytest.raises(MarketClockScheduleValidationError):
        derive_wall_clock_transitions(
            simulated_start=datetime(2026, 8, 13, 0, 0, tzinfo=UTC),
            simulated_end=datetime(2026, 8, 13, 0, 0, tzinfo=UTC),
            timezone_name="America/New_York",
            boundaries=(WallClockBoundary(9),),
        )


def test_schedule_module_has_no_trading_policy_or_hidden_runtime_side_effects() -> None:
    source = inspect.getsource(schedule_module).lower()
    for forbidden in (
        "datetime.now(",
        "datetime.utcnow(",
        "uuid4(",
        "sleep(",
        "threading",
        "asyncio",
        "scheduler",
        "retry",
        "requests.",
        "httpx",
        "aiohttp",
        "socket",
        "ctrader",
        "oanda",
        "market_close",
        "force_close",
        "liquidat",
    ):
        assert forbidden not in source
