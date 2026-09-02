"""Fast-Forward qualification seam for the Trader Lab.

This is NOT a second replay engine. It consumes the existing deterministic
replay chronology and proves only the Lab-specific qualification properties:
acceleration compresses wall-clock execution while simulated chronology,
``available_at`` visibility, and ordering remain exact. Every wall-clock advance
is explicit; there is no hidden wall clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from qore.infrastructure.market_event_replay import (
    MarketEventObservationId,
    RetainedMarketEventObservation,
    derive_market_event_availability_instants,
    order_market_event_observations,
    visible_market_event_observations,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabError,
    TraderLabValidationError,
    _validate_sha256,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    _canonical_bytes,
)
from qore.kernel.result import Failure, Result, Success


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TraderLabValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderLabValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class TraderLabFastForwardStep:
    """One accelerated replay step: a simulated instant plus an explicit advance."""

    simulated_now: datetime
    wall_clock_advance: timedelta

    def __post_init__(self) -> None:
        _validate_timestamp(self.simulated_now, field_name="fast-forward simulated_now")
        if not isinstance(self.wall_clock_advance, timedelta):
            raise TraderLabValidationError(
                "wall_clock_advance must be a timedelta"
            )
        if self.wall_clock_advance < timedelta(0):
            raise TraderLabValidationError(
                "wall_clock_advance must be non-negative"
            )

    def logical_values(self) -> tuple[str, int]:
        return (
            self.simulated_now.astimezone(UTC).isoformat(timespec="microseconds"),
            self.wall_clock_advance // timedelta(microseconds=1),
        )


@dataclass(frozen=True, slots=True)
class TraderLabFastForwardSchedule:
    """Explicit acceleration schedule over the base replay chronology."""

    steps: tuple[TraderLabFastForwardStep, ...]
    acceleration_factor: int

    def __post_init__(self) -> None:
        if not isinstance(self.steps, tuple) or not self.steps or any(
            not isinstance(step, TraderLabFastForwardStep) for step in self.steps
        ):
            raise TraderLabValidationError(
                "schedule steps must be a non-empty immutable step tuple"
            )
        if type(self.acceleration_factor) is not int or self.acceleration_factor < 2:
            raise TraderLabValidationError(
                "acceleration_factor must be an integer of at least two"
            )
        for previous, current in zip(self.steps, self.steps[1:], strict=False):
            if current.simulated_now <= previous.simulated_now:
                raise TraderLabValidationError(
                    "fast-forward steps must be strictly ascending in simulated time"
                )
        if sum(
            (step.wall_clock_advance for step in self.steps),
            timedelta(0),
        ) <= timedelta(0):
            raise TraderLabValidationError(
                "fast-forward schedule must advance wall clock"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(step.logical_values() for step in self.steps),
            self.acceleration_factor,
        )


@dataclass(frozen=True, slots=True)
class TraderLabFastForwardQualificationId:
    """Immutable identity of one fast-forward qualification."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TraderLabValidationError(
                "fast-forward qualification id must be a UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TraderLabFastForwardFingerprint:
    """Canonical SHA-256 digest of the fast-forward qualification."""

    value: str

    def __post_init__(self) -> None:
        _validate_sha256(self.value, field_name="fast-forward fingerprint")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_trader_lab_fast_forward_fingerprint(
    *,
    candidate: TraderLabCandidateBinding,
    schedule: TraderLabFastForwardSchedule,
    observations_digest: TraderLabEvidenceDigest,
    certified_at: datetime,
) -> TraderLabFastForwardFingerprint:
    """Hash exact candidate, schedule, replay chronology, and certification time."""

    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    if not isinstance(schedule, TraderLabFastForwardSchedule):
        raise TraderLabValidationError(
            "schedule must be TraderLabFastForwardSchedule"
        )
    if not isinstance(observations_digest, TraderLabEvidenceDigest):
        raise TraderLabValidationError(
            "observations_digest must be TraderLabEvidenceDigest"
        )
    _validate_timestamp(certified_at, field_name="fast-forward certified_at")
    canonical = {
        "schema": "qore.trader_lab.fast_forward.v1",
        "candidate_fingerprint": candidate.fingerprint.value,
        "schedule": list(schedule.logical_values()),
        "observations_digest": observations_digest.value,
        "certified_at": certified_at.astimezone(UTC).isoformat(
            timespec="microseconds"
        ),
    }
    return TraderLabFastForwardFingerprint(sha256(_canonical_bytes(canonical)).hexdigest())


def _verify_no_lookahead(
    observations: tuple[RetainedMarketEventObservation, ...],
    base_instants: tuple[datetime, ...],
) -> None:
    """Prove no event becomes visible before its exact availability instant."""

    instant_set = set(base_instants)
    previous_visible: set[MarketEventObservationId] = set()
    for instant in base_instants:
        visible = visible_market_event_observations(
            observations,
            simulated_now=instant,
        )
        visible_ids = {item.event_id for item in visible}
        newly_visible = visible_ids - previous_visible
        for item in visible:
            if item.event_id in newly_visible and item.available_at not in instant_set:
                raise TraderLabValidationError(
                    "event availability instant missing from replay chronology"
                )
            if (
                item.event_id in newly_visible
                and item.available_at != instant
            ):
                raise TraderLabValidationError(
                    "future event became visible before its availability instant"
                )
        if not previous_visible <= visible_ids:
            raise TraderLabValidationError(
                "fast-forward visibility regressed an already-visible event"
            )
        previous_visible = visible_ids


@dataclass(frozen=True, slots=True)
class TraderLabFastForwardQualification:
    """Immutable evidence that one schedule is a valid chronology acceleration."""

    qualification_id: TraderLabFastForwardQualificationId
    candidate: TraderLabCandidateBinding
    schedule: TraderLabFastForwardSchedule
    observations_digest: TraderLabEvidenceDigest
    availability_instants: tuple[datetime, ...]
    certified_at: datetime
    fingerprint: TraderLabFastForwardFingerprint

    def __post_init__(self) -> None:
        if not isinstance(
            self.qualification_id,
            TraderLabFastForwardQualificationId,
        ):
            raise TraderLabValidationError(
                "qualification_id must be TraderLabFastForwardQualificationId"
            )
        if not isinstance(self.candidate, TraderLabCandidateBinding):
            raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
        if not isinstance(self.schedule, TraderLabFastForwardSchedule):
            raise TraderLabValidationError(
                "schedule must be TraderLabFastForwardSchedule"
            )
        if not isinstance(self.observations_digest, TraderLabEvidenceDigest):
            raise TraderLabValidationError(
                "observations_digest must be TraderLabEvidenceDigest"
            )
        if not isinstance(self.availability_instants, tuple) or not all(
            isinstance(value, datetime) for value in self.availability_instants
        ):
            raise TraderLabValidationError(
                "availability_instants must be an immutable datetime tuple"
            )
        _validate_timestamp(self.certified_at, field_name="fast-forward certified_at")
        if not isinstance(self.fingerprint, TraderLabFastForwardFingerprint):
            raise TraderLabValidationError(
                "fingerprint must be TraderLabFastForwardFingerprint"
            )
        expected = compute_trader_lab_fast_forward_fingerprint(
            candidate=self.candidate,
            schedule=self.schedule,
            observations_digest=self.observations_digest,
            certified_at=self.certified_at,
        )
        if self.fingerprint != expected:
            raise TraderLabValidationError(
                "fast-forward fingerprint must match the exact qualification"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.qualification_id.logical_values(),
            self.candidate.fingerprint.logical_values(),
            self.schedule.logical_values(),
            self.observations_digest.logical_values(),
            tuple(
                value.astimezone(UTC).isoformat(timespec="microseconds")
                for value in self.availability_instants
            ),
            self.certified_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.fingerprint.logical_values(),
        )


def qualify_trader_lab_fast_forward(
    *,
    qualification_id: TraderLabFastForwardQualificationId,
    candidate: TraderLabCandidateBinding,
    schedule: TraderLabFastForwardSchedule,
    observations: tuple[RetainedMarketEventObservation, ...],
    certified_at: datetime,
) -> Result[TraderLabFastForwardQualification, TraderLabError]:
    """Certify that one schedule is a valid acceleration of the replay chronology.

    Fails closed (returns insufficient/validation error) whenever the existing
    replay evidence cannot support the property, without reimplementing replay.
    """

    try:
        if not isinstance(qualification_id, TraderLabFastForwardQualificationId):
            raise TraderLabValidationError(
                "qualification_id must be TraderLabFastForwardQualificationId"
            )
        if not isinstance(candidate, TraderLabCandidateBinding):
            raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
        if not isinstance(schedule, TraderLabFastForwardSchedule):
            raise TraderLabValidationError(
                "schedule must be TraderLabFastForwardSchedule"
            )
        _validate_timestamp(certified_at, field_name="fast-forward certified_at")

        ordered = order_market_event_observations(observations)
        base_instants = derive_market_event_availability_instants(observations)
        if len(base_instants) < 2:
            raise TraderLabValidationError(
                "insufficient availability instants to certify fast-forward"
            )
        if tuple(step.simulated_now for step in schedule.steps) != base_instants:
            raise TraderLabValidationError(
                "fast-forward schedule must visit every availability instant "
                "exactly once in exact chronological order"
            )
        base_wall_clock = base_instants[-1] - base_instants[0]
        accelerated_wall_clock = sum(
            (step.wall_clock_advance for step in schedule.steps),
            timedelta(0),
        )
        if base_wall_clock != accelerated_wall_clock * schedule.acceleration_factor:
            raise TraderLabValidationError(
                "accelerated wall clock must compress the base simulated duration "
                "by exactly the acceleration factor"
            )
        _verify_no_lookahead(observations, base_instants)

        observations_digest = TraderLabEvidenceDigest(
            sha256(
                _canonical_bytes(
                    {"events": [list(item.logical_values()) for item in ordered]}
                )
            ).hexdigest()
        )
        fingerprint = compute_trader_lab_fast_forward_fingerprint(
            candidate=candidate,
            schedule=schedule,
            observations_digest=observations_digest,
            certified_at=certified_at,
        )
        return Success(
            TraderLabFastForwardQualification(
                qualification_id=qualification_id,
                candidate=candidate,
                schedule=schedule,
                observations_digest=observations_digest,
                availability_instants=base_instants,
                certified_at=certified_at,
                fingerprint=fingerprint,
            )
        )
    except TraderLabError as error:
        return Failure(error)
