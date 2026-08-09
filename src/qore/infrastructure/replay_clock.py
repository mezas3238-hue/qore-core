from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from qore.infrastructure.replay_availability import ReplayMarketDataObservation
from qore.kernel.errors import InfrastructureError


class ReplayClockError(InfrastructureError):
    """Base error for deterministic replay clock and visibility contracts."""

    __slots__ = ()


class ReplayClockValidationError(ReplayClockError):
    """Violation of a deterministic replay clock or visibility invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ReplayClockValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ReplayClockValidationError(f"{field_name} must be timezone-aware")


class ReplayClock:
    """Explicit monotonic simulated clock with no wall-clock dependency."""

    __slots__ = ("_current_time",)

    def __init__(self, initial_time: datetime) -> None:
        _validate_timestamp(initial_time, field_name="replay initial_time")
        self._current_time = initial_time

    def now(self) -> datetime:
        return self._current_time

    def advance_to(self, target: datetime) -> None:
        _validate_timestamp(target, field_name="replay target")
        if target < self._current_time:
            raise ReplayClockValidationError("replay clock cannot move backwards")
        self._current_time = target

    def advance_by(self, delta: timedelta) -> None:
        if not isinstance(delta, timedelta):
            raise ReplayClockValidationError("replay delta must be timedelta")
        if delta < timedelta(0):
            raise ReplayClockValidationError("replay clock cannot move backwards")
        self._current_time = self._current_time + delta


class ReplayVisibility(StrEnum):
    HIDDEN = "hidden"
    VISIBLE = "visible"


@dataclass(frozen=True, slots=True)
class ReplayVisibilityAssessment:
    """Immutable visibility result for one observation at one simulated instant."""

    observation: ReplayMarketDataObservation
    simulated_now: datetime
    visibility: ReplayVisibility

    def __post_init__(self) -> None:
        if not isinstance(self.observation, ReplayMarketDataObservation):
            raise ReplayClockValidationError(
                "visibility observation must be ReplayMarketDataObservation"
            )
        _validate_timestamp(self.simulated_now, field_name="replay simulated_now")
        if not isinstance(self.visibility, ReplayVisibility):
            raise ReplayClockValidationError(
                "visibility must be ReplayVisibility"
            )
        expected = (
            ReplayVisibility.VISIBLE
            if self.observation.available_at <= self.simulated_now
            else ReplayVisibility.HIDDEN
        )
        if self.visibility is not expected:
            raise ReplayClockValidationError(
                "visibility must match available_at and simulated_now"
            )

    @property
    def is_visible(self) -> bool:
        return self.visibility is ReplayVisibility.VISIBLE

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation.logical_values(),
            self.simulated_now.isoformat(),
            self.visibility.value,
        )


def evaluate_replay_visibility(
    observation: ReplayMarketDataObservation,
    *,
    simulated_now: datetime,
) -> ReplayVisibilityAssessment:
    """Evaluate the inclusive point-in-time visibility boundary."""

    if not isinstance(observation, ReplayMarketDataObservation):
        raise ReplayClockValidationError(
            "visibility observation must be ReplayMarketDataObservation"
        )
    _validate_timestamp(simulated_now, field_name="replay simulated_now")
    visibility = (
        ReplayVisibility.VISIBLE
        if observation.available_at <= simulated_now
        else ReplayVisibility.HIDDEN
    )
    return ReplayVisibilityAssessment(
        observation=observation,
        simulated_now=simulated_now,
        visibility=visibility,
    )


type ReplayObservationOrderKey = tuple[
    datetime,
    datetime,
    str,
    str,
    str,
    str,
    str,
    str,
]


def replay_observation_order_key(
    observation: ReplayMarketDataObservation,
) -> ReplayObservationOrderKey:
    """Return the explicit provider-neutral stable ordering key."""

    if not isinstance(observation, ReplayMarketDataObservation):
        raise ReplayClockValidationError(
            "ordered observation must be ReplayMarketDataObservation"
        )
    source = observation.source
    return (
        observation.available_at,
        observation.canonical_boundary,
        str(source.adapter_id.value),
        str(source.source_id.value),
        source.port_name.value,
        observation.instrument.symbol,
        str(observation.snapshot_id.value),
        str(observation.observation_id.value),
    )


def order_replay_observations(
    observations: tuple[ReplayMarketDataObservation, ...],
) -> tuple[ReplayMarketDataObservation, ...]:
    """Explicitly order replay observations without relying on incidental order."""

    if not isinstance(observations, tuple) or any(
        not isinstance(item, ReplayMarketDataObservation) for item in observations
    ):
        raise ReplayClockValidationError(
            "replay observations must be an immutable observation tuple"
        )
    ids = tuple(item.observation_id for item in observations)
    if len(set(ids)) != len(ids):
        raise ReplayClockValidationError("replay observation identities must be unique")
    return tuple(sorted(observations, key=replay_observation_order_key))


def visible_replay_observations(
    observations: tuple[ReplayMarketDataObservation, ...],
    *,
    simulated_now: datetime,
) -> tuple[ReplayMarketDataObservation, ...]:
    """Return only observations visible at ``simulated_now`` in stable order."""

    _validate_timestamp(simulated_now, field_name="replay simulated_now")
    ordered = order_replay_observations(observations)
    return tuple(item for item in ordered if item.available_at <= simulated_now)
