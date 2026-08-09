from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    QuoteSnapshot,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.replay_clock import (
    ReplayClock,
    ReplayClockValidationError,
    ReplayVisibility,
    ReplayVisibilityAssessment,
    evaluate_replay_visibility,
    order_replay_observations,
    replay_observation_order_key,
    visible_replay_observations,
)

_BASE = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_ADAPTER = AdapterId(UUID("63000000-0000-0000-0000-000000000001"))


def _uuid(suffix: int) -> UUID:
    return UUID(f"63000000-0000-0000-0000-{suffix:012d}")


def _source(*, suffix: int, port: str = "market-data.replay-clock") -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER,
        source_id=SourceId(_uuid(suffix)),
        port_name=PortName(port),
    )


def _observation(
    *,
    suffix: int,
    observed_at: datetime = _BASE,
    available_at: datetime | None = None,
    source: ExternalSourceDescriptor | None = None,
    instrument: str = "EURUSD",
) -> ReplayMarketDataObservation:
    resolved_source = source if source is not None else _source(suffix=10)
    snapshot = QuoteSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(100 + suffix)),
        instrument=Instrument(instrument),
        source=resolved_source,
        observed_at=observed_at,
        bid=1.16,
        ask=1.1602,
    )
    replay_at = available_at if available_at is not None else observed_at
    return ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(200 + suffix)),
        payload=snapshot,
        availability_evidence_at=observed_at,
        available_at=replay_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(300 + suffix)
        ),
    )


def test_replay_clock_preserves_explicit_non_utc_aware_time() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    initial = datetime(2026, 8, 9, 17, 30, tzinfo=offset)
    clock = ReplayClock(initial)

    assert clock.now() is initial
    assert clock.now().isoformat().endswith("+05:30")


def test_replay_clock_rejects_naive_initial_or_target_time() -> None:
    with pytest.raises(ReplayClockValidationError, match="timezone-aware"):
        ReplayClock(datetime(2026, 8, 9, 12, 0))

    clock = ReplayClock(_BASE)
    with pytest.raises(ReplayClockValidationError, match="timezone-aware"):
        clock.advance_to(datetime(2026, 8, 9, 12, 1))


def test_replay_clock_advance_to_is_monotonic_and_equality_is_allowed() -> None:
    clock = ReplayClock(_BASE)
    clock.advance_to(_BASE)
    assert clock.now() == _BASE

    later = _BASE + timedelta(minutes=5)
    clock.advance_to(later)
    assert clock.now() == later

    with pytest.raises(ReplayClockValidationError, match="cannot move backwards"):
        clock.advance_to(later - timedelta(microseconds=1))
    assert clock.now() == later


def test_replay_clock_advance_by_rejects_negative_or_wrong_runtime_type() -> None:
    clock = ReplayClock(_BASE)
    clock.advance_by(timedelta(0))
    clock.advance_by(timedelta(seconds=30))
    assert clock.now() == _BASE + timedelta(seconds=30)

    with pytest.raises(ReplayClockValidationError, match="cannot move backwards"):
        clock.advance_by(timedelta(microseconds=-1))
    with pytest.raises(ReplayClockValidationError, match="must be timedelta"):
        clock.advance_by(cast(timedelta, 1))


def test_visibility_is_hidden_before_available_at_and_inclusive_at_boundary() -> None:
    available_at = _BASE + timedelta(seconds=10)
    observation = _observation(suffix=1, available_at=available_at)

    hidden = evaluate_replay_visibility(
        observation,
        simulated_now=available_at - timedelta(microseconds=1),
    )
    exact = evaluate_replay_visibility(observation, simulated_now=available_at)
    after = evaluate_replay_visibility(
        observation,
        simulated_now=available_at + timedelta(microseconds=1),
    )

    assert hidden.visibility is ReplayVisibility.HIDDEN
    assert hidden.is_visible is False
    assert exact.visibility is ReplayVisibility.VISIBLE
    assert exact.is_visible is True
    assert after.visibility is ReplayVisibility.VISIBLE


def test_visibility_assessment_cannot_contradict_availability_evidence() -> None:
    observation = _observation(
        suffix=2,
        available_at=_BASE + timedelta(seconds=10),
    )
    with pytest.raises(ReplayClockValidationError, match="must match"):
        ReplayVisibilityAssessment(
            observation=observation,
            simulated_now=_BASE,
            visibility=ReplayVisibility.VISIBLE,
        )


def test_visibility_gate_hides_future_observations_and_returns_stable_order() -> None:
    first = _observation(
        suffix=3,
        observed_at=_BASE + timedelta(seconds=1),
        available_at=_BASE + timedelta(seconds=5),
    )
    second = _observation(
        suffix=4,
        observed_at=_BASE + timedelta(seconds=2),
        available_at=_BASE + timedelta(seconds=5),
    )
    future = _observation(
        suffix=5,
        observed_at=_BASE + timedelta(seconds=3),
        available_at=_BASE + timedelta(seconds=8),
    )

    visible = visible_replay_observations(
        (future, second, first),
        simulated_now=_BASE + timedelta(seconds=5),
    )

    assert visible == (first, second)
    assert future not in visible


def test_ordering_uses_full_source_identity_before_instrument_and_ids() -> None:
    earlier_source = _source(suffix=20, port="market-data.same-adapter")
    later_source = _source(suffix=21, port="market-data.same-adapter")
    available_at = _BASE + timedelta(seconds=5)
    earlier = _observation(
        suffix=6,
        source=earlier_source,
        available_at=available_at,
    )
    later = _observation(
        suffix=7,
        source=later_source,
        available_at=available_at,
    )

    ordered = order_replay_observations((later, earlier))

    assert ordered == (earlier, later)
    assert replay_observation_order_key(earlier) < replay_observation_order_key(later)


def test_ordering_is_repeatable_and_rejects_duplicate_observation_identity() -> None:
    first = _observation(suffix=8, available_at=_BASE + timedelta(seconds=1))
    second = _observation(suffix=9, available_at=_BASE + timedelta(seconds=2))

    left = order_replay_observations((second, first))
    right = order_replay_observations((second, first))
    assert tuple(item.logical_values() for item in left) == tuple(
        item.logical_values() for item in right
    )

    with pytest.raises(ReplayClockValidationError, match="identities must be unique"):
        order_replay_observations((first, first))


def test_clock_and_visibility_surfaces_expose_no_trading_or_decision_authority() -> None:
    prohibited = {
        "buy",
        "core_decision",
        "create_decision",
        "dispatch",
        "sell",
        "submit_order",
    }
    assert prohibited.isdisjoint(set(dir(ReplayClock)))
    assert prohibited.isdisjoint(set(dir(ReplayVisibilityAssessment)))
