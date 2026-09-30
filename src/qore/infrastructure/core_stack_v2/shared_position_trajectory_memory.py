"""X-05 Position Journey and X-06 Trajectory Memory.

Builds immutable source-time journey trajectories for already-open positions.
The memory describes how evidence evolves; it never commands HOLD/EXIT/PROTECT.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
    continuation_source_scores,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)


class SharedPositionJourneyState(StrEnum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DETERIORATING = "DETERIORATING"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedPositionJourneyPoint:
    observation_id: str
    position_id: str
    asset: str
    as_of_iso: str
    minutes_since_fill: int
    continuation_bps: int
    positive_tail_bps: int
    failure_hazard_bps: int
    coherence_bps: int
    uncertainty_bps: int
    continuation_velocity_bps: int
    failure_velocity_bps: int
    journey_state: SharedPositionJourneyState
    provenance_refs: tuple[str, ...]
    position_management_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("observation_id", "position_id", "asset", "as_of_iso"):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        for name in (
            "continuation_bps",
            "positive_tail_bps",
            "failure_hazard_bps",
            "coherence_bps",
            "uncertainty_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        for name in ("continuation_velocity_bps", "failure_velocity_bps"):
            value = getattr(self, name)
            if type(value) is not int or not -10_000 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within -10000..10000"
                )
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "journey point provenance must be non-empty and canonical"
            )
        if (
            self.position_management_authority
            or self.execution_authority
            or self.risk_authority
            or self.capital_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "position journey cognition cannot manage the position"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["journey_state"] = self.journey_state.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SharedPositionTrajectoryMemory:
    position_id: str
    asset: str
    points: tuple[SharedPositionJourneyPoint, ...]
    trajectory_fingerprint: str
    future_market_used: bool = False
    future_outcome_used: bool = False
    pnl_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.position_id.strip() or not self.asset.strip():
            raise SharedTraderIntelligenceValidationError(
                "trajectory memory identity must be non-empty"
            )
        if not self.points:
            raise SharedTraderIntelligenceValidationError(
                "trajectory memory requires at least one point"
            )
        if any(point.position_id != self.position_id for point in self.points):
            raise SharedTraderIntelligenceValidationError(
                "trajectory memory cannot mix positions"
            )
        if any(point.asset != self.asset for point in self.points):
            raise SharedTraderIntelligenceValidationError(
                "trajectory memory cannot mix assets"
            )
        if tuple(point.as_of_iso for point in self.points) != tuple(
            sorted(point.as_of_iso for point in self.points)
        ):
            raise SharedTraderIntelligenceValidationError(
                "trajectory memory points must be chronological"
            )
        expected = hashlib.sha256(
            json.dumps(
                [point.fingerprint() for point in self.points],
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        if self.trajectory_fingerprint != expected:
            raise SharedTraderIntelligenceValidationError(
                "trajectory memory fingerprint mismatch"
            )
        if (
            self.future_market_used
            or self.future_outcome_used
            or self.pnl_used
            or self.productive_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "trajectory memory must remain source-time research"
            )


def build_position_trajectory_memory(
    observations: Sequence[SharedPositionCausalObservation],
    *,
    minimum_integrity_bps: int = 9_500,
) -> SharedPositionTrajectoryMemory:
    if not observations:
        raise SharedTraderIntelligenceValidationError(
            "trajectory memory requires observations"
        )
    ordered = tuple(observations)
    first = ordered[0]
    previous_time = None
    previous_continuation = None
    previous_failure = None
    points: list[SharedPositionJourneyPoint] = []

    for observation in ordered:
        if observation.position_id != first.position_id or observation.asset != first.asset:
            raise SharedTraderIntelligenceValidationError(
                "trajectory sequence must use one position and asset"
            )
        if previous_time is not None and observation.as_of <= previous_time:
            raise SharedTraderIntelligenceValidationError(
                "trajectory observations must be strictly chronological"
            )
        continuation, tail, failure, coherence, uncertainty = (
            continuation_source_scores(observation)
        )
        continuation_velocity = (
            0
            if previous_continuation is None
            else continuation - previous_continuation
        )
        failure_velocity = (
            0 if previous_failure is None else failure - previous_failure
        )

        if observation.data_integrity_bps < minimum_integrity_bps:
            state = SharedPositionJourneyState.INSUFFICIENT
        elif continuation >= failure + 1_500 and continuation_velocity >= 0:
            state = SharedPositionJourneyState.IMPROVING
        elif failure >= continuation + 1_500 and failure_velocity >= 0:
            state = SharedPositionJourneyState.DETERIORATING
        elif abs(continuation - failure) < 1_500:
            state = SharedPositionJourneyState.CONFLICTED
        else:
            state = SharedPositionJourneyState.STABLE

        points.append(
            SharedPositionJourneyPoint(
                observation_id=observation.observation_id,
                position_id=observation.position_id,
                asset=observation.asset,
                as_of_iso=observation.as_of.isoformat(),
                minutes_since_fill=observation.minutes_since_fill,
                continuation_bps=continuation,
                positive_tail_bps=tail,
                failure_hazard_bps=failure,
                coherence_bps=coherence,
                uncertainty_bps=uncertainty,
                continuation_velocity_bps=continuation_velocity,
                failure_velocity_bps=failure_velocity,
                journey_state=state,
                provenance_refs=tuple(
                    sorted(
                        set(
                            observation.provenance_refs
                            + ("x05-x06-position-trajectory-memory",)
                        )
                    )
                ),
            )
        )
        previous_time = observation.as_of
        previous_continuation = continuation
        previous_failure = failure

    point_tuple = tuple(points)
    fingerprint = hashlib.sha256(
        json.dumps(
            [point.fingerprint() for point in point_tuple],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return SharedPositionTrajectoryMemory(
        position_id=first.position_id,
        asset=first.asset,
        points=point_tuple,
        trajectory_fingerprint=fingerprint,
    )
