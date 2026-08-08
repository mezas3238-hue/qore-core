from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.market_test_observability import (
    MarketTestObservabilityValidationError,
    MarketTestObservation,
    MarketTestObservationCategory,
    MarketTestObservationState,
    build_market_test_observability_evidence,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 11, 35, tzinfo=UTC)


def _observation(
    category: MarketTestObservationCategory,
    state: MarketTestObservationState = MarketTestObservationState.HEALTHY,
) -> MarketTestObservation:
    return MarketTestObservation(
        category=category,
        state=state,
        observed_at=_NOW,
        message=f"{category.value} state recorded",
        reference=f"mission02:{category.value}:001",
    )


def _complete(
    *,
    degraded: MarketTestObservationCategory | None = None,
    blocked: MarketTestObservationCategory | None = None,
) -> tuple[MarketTestObservation, ...]:
    observations: list[MarketTestObservation] = []
    for category in MarketTestObservationCategory:
        state = MarketTestObservationState.HEALTHY
        if category is degraded:
            state = MarketTestObservationState.DEGRADED
        if category is blocked:
            state = MarketTestObservationState.BLOCKED
        observations.append(_observation(category, state))
    return tuple(observations)


def test_complete_evidence_is_sorted_and_healthy() -> None:
    result = build_market_test_observability_evidence(
        tuple(reversed(_complete())),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.state is MarketTestObservationState.HEALTHY
    assert tuple(item.category.value for item in result.value.observations) == tuple(
        sorted(category.value for category in MarketTestObservationCategory)
    )


def test_blocked_observation_dominates_aggregate_state() -> None:
    result = build_market_test_observability_evidence(
        _complete(
            degraded=MarketTestObservationCategory.MARKET_DATA,
            blocked=MarketTestObservationCategory.SAFETY,
        ),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.state is MarketTestObservationState.BLOCKED


def test_missing_category_fails_closed() -> None:
    result = build_market_test_observability_evidence(
        _complete()[:-1],
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestObservabilityValidationError)


def test_duplicate_category_fails_closed() -> None:
    observations = _complete()
    result = build_market_test_observability_evidence(
        observations + (observations[0],),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestObservabilityValidationError)


def test_secret_like_message_is_rejected() -> None:
    with pytest.raises(MarketTestObservabilityValidationError):
        MarketTestObservation(
            category=MarketTestObservationCategory.EXECUTION,
            state=MarketTestObservationState.HEALTHY,
            observed_at=_NOW,
            message="authorization: bearer hidden-value",
            reference="mission02:execution:001",
        )


def test_observation_cannot_postdate_evidence() -> None:
    observations = list(_complete())
    observations[0] = MarketTestObservation(
        category=observations[0].category,
        state=observations[0].state,
        observed_at=_NOW + timedelta(seconds=2),
        message=observations[0].message,
        reference=observations[0].reference,
    )

    result = build_market_test_observability_evidence(
        tuple(observations),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, MarketTestObservabilityValidationError)
