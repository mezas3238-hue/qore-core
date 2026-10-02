"""Causal position-path intelligence for Shared Core.

This layer answers a specific third-eye question for an already-open position:
is current adversity evidence of terminal path failure, or a recoverable
pullback inside an established favorable journey?

The model is generic and outcome-blind. It consumes normalized causal path
evidence plus Shared market/environment support. It never consumes realized
trade outcome, future bars, PnL labels, capital, sizing, or order state.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class PositionPathState(StrEnum):
    FAVORABLE_EXPANSION = "FAVORABLE_EXPANSION"
    HEALTHY_PULLBACK = "HEALTHY_PULLBACK"
    CONTESTED = "CONTESTED"
    ADVERSE_DOMINANCE = "ADVERSE_DOMINANCE"
    FAILURE_RISK = "FAILURE_RISK"
    RECOVERING = "RECOVERING"
    INSUFFICIENT = "INSUFFICIENT"


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _check_bps(name: str, value: int) -> None:
    if not 0 <= value <= 10_000:
        raise ValueError(f"{name} must be within 0..10000")


def _mean(values: Sequence[int]) -> int:
    if not values:
        raise ValueError("mean requires at least one value")
    return sum(values) // len(values)


def _persistence(values: Sequence[int], *, increasing: bool) -> int:
    if len(values) < 2:
        return 0
    qualifying = 0
    for left, right in zip(values, values[1:], strict=False):
        if (right > left) if increasing else (right < left):
            qualifying += 1
    return qualifying * 10_000 // (len(values) - 1)


@dataclass(frozen=True, slots=True)
class PositionPathObservation:
    as_of: datetime
    data_integrity_bps: int
    journey_progress_bps: int
    close_support_bps: int
    directional_efficiency_bps: int
    favorable_excursion_bps: int
    adverse_excursion_bps: int
    favorable_body_bps: int
    adverse_body_bps: int
    market_support_bps: int
    environment_adverse_bps: int
    recovery_evidence_bps: int

    def __post_init__(self) -> None:
        _iso(self.as_of)
        for name in (
            "data_integrity_bps",
            "journey_progress_bps",
            "close_support_bps",
            "directional_efficiency_bps",
            "favorable_excursion_bps",
            "adverse_excursion_bps",
            "favorable_body_bps",
            "adverse_body_bps",
            "market_support_bps",
            "environment_adverse_bps",
            "recovery_evidence_bps",
        ):
            _check_bps(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class PositionPathPolicy:
    minimum_observations: int = 4
    minimum_integrity_bps: int = 7_500
    established_progress_bps: int = 4_500
    expansion_progress_bps: int = 6_500
    winner_protection_bps: int = 6_200
    adverse_dominance_bps: int = 6_200
    failure_risk_bps: int = 7_200
    persistence_bps: int = 5_500
    recovery_bps: int = 6_200

    def __post_init__(self) -> None:
        if self.minimum_observations < 3:
            raise ValueError("minimum_observations must be at least 3")
        for name in (
            "minimum_integrity_bps",
            "established_progress_bps",
            "expansion_progress_bps",
            "winner_protection_bps",
            "adverse_dominance_bps",
            "failure_risk_bps",
            "persistence_bps",
            "recovery_bps",
        ):
            _check_bps(name, getattr(self, name))


@dataclass(frozen=True, slots=True)
class PositionPathAssessment:
    as_of: datetime
    state: PositionPathState
    evidence_count: int
    path_support_bps: int
    adverse_dominance_bps: int
    adverse_persistence_bps: int
    recovery_persistence_bps: int
    winner_protection_bps: int
    terminal_failure_risk_bps: int
    reasons: tuple[str, ...]
    target_mutation_authority: bool = False
    stop_mutation_authority: bool = False
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _iso(self.as_of)
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        for name in (
            "path_support_bps",
            "adverse_dominance_bps",
            "adverse_persistence_bps",
            "recovery_persistence_bps",
            "winner_protection_bps",
            "terminal_failure_risk_bps",
        ):
            _check_bps(name, getattr(self, name))
        if (
            self.target_mutation_authority
            or self.stop_mutation_authority
            or self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.execution_authority
        ):
            raise ValueError(
                "Shared path intelligence cannot carry trading authority"
            )


def _support(observation: PositionPathObservation) -> int:
    return _mean(
        (
            observation.journey_progress_bps,
            observation.close_support_bps,
            observation.directional_efficiency_bps,
            observation.favorable_excursion_bps,
            observation.favorable_body_bps,
            observation.market_support_bps,
            10_000 - observation.environment_adverse_bps,
        )
    )


def _adversity(observation: PositionPathObservation) -> int:
    return _mean(
        (
            10_000 - observation.close_support_bps,
            10_000 - observation.directional_efficiency_bps,
            observation.adverse_excursion_bps,
            observation.adverse_body_bps,
            observation.environment_adverse_bps,
            10_000 - observation.market_support_bps,
        )
    )


def _winner_protection(observation: PositionPathObservation) -> int:
    established = max(
        observation.journey_progress_bps,
        observation.favorable_excursion_bps,
    )
    resilience = _mean(
        (
            observation.close_support_bps,
            observation.directional_efficiency_bps,
            observation.market_support_bps,
            observation.recovery_evidence_bps,
        )
    )
    return _mean((established, established, resilience))


def assess_position_path(
    observations: Sequence[PositionPathObservation],
    *,
    policy: PositionPathPolicy | None = None,
) -> PositionPathAssessment:
    if not observations:
        raise ValueError("at least one position path observation is required")
    effective = policy or PositionPathPolicy()

    for left, right in zip(observations, observations[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError(
                "position path observations must be strictly increasing and causal"
            )

    latest = observations[-1]
    adversities = [_adversity(item) for item in observations]
    recoveries = [item.recovery_evidence_bps for item in observations]
    support = _support(latest)
    adversity = adversities[-1]
    adverse_persistence = _persistence(adversities, increasing=True)
    recovery_persistence = _persistence(recoveries, increasing=True)
    winner_protection = _winner_protection(latest)
    terminal_failure = _mean(
        (
            adversity,
            adverse_persistence,
            latest.environment_adverse_bps,
            10_000 - winner_protection,
        )
    )

    reasons: list[str] = []
    insufficient = (
        len(observations) < effective.minimum_observations
        or min(item.data_integrity_bps for item in observations)
        < effective.minimum_integrity_bps
    )
    if insufficient:
        state = PositionPathState.INSUFFICIENT
        reasons.append("PATH_EVIDENCE_INSUFFICIENT")
    elif (
        latest.journey_progress_bps >= effective.expansion_progress_bps
        and support >= effective.winner_protection_bps
        and terminal_failure < effective.failure_risk_bps
    ):
        state = PositionPathState.FAVORABLE_EXPANSION
        reasons.extend(
            (
                "FAVORABLE_PATH_ESTABLISHED",
                "CONTINUATION_SUPPORT_REMAINS_STRONG",
            )
        )
    elif (
        latest.journey_progress_bps >= effective.established_progress_bps
        and winner_protection >= effective.winner_protection_bps
        and terminal_failure < effective.failure_risk_bps
    ):
        state = PositionPathState.HEALTHY_PULLBACK
        reasons.extend(
            (
                "PRIOR_FAVORABLE_PROGRESS_ESTABLISHED",
                "PULLBACK_NOT_PROVEN_TERMINAL",
            )
        )
    elif (
        latest.recovery_evidence_bps >= effective.recovery_bps
        and recovery_persistence >= effective.persistence_bps
        and support >= 5_500
    ):
        state = PositionPathState.RECOVERING
        reasons.append("CAUSAL_PATH_RECOVERY_BUILDING")
    elif (
        terminal_failure >= effective.failure_risk_bps
        and adverse_persistence >= effective.persistence_bps
        and winner_protection < effective.winner_protection_bps
    ):
        state = PositionPathState.FAILURE_RISK
        reasons.extend(
            (
                "ADVERSE_PATH_PERSISTENT",
                "WINNER_PROTECTION_EVIDENCE_WEAK",
                "TERMINAL_FAILURE_RISK_HIGH",
            )
        )
    elif (
        adversity >= effective.adverse_dominance_bps
        and adverse_persistence >= effective.persistence_bps
    ):
        state = PositionPathState.ADVERSE_DOMINANCE
        reasons.extend(
            (
                "ADVERSE_PATH_DOMINANT",
                "ADVERSE_PATH_PERSISTENT",
            )
        )
    else:
        state = PositionPathState.CONTESTED
        reasons.append("PATH_CONTESTED_NO_TERMINAL_CONCLUSION")

    if winner_protection >= effective.winner_protection_bps:
        reasons.append("WINNER_PROTECTION_ACTIVE")
    if latest.environment_adverse_bps >= 6_500:
        reasons.append("ADVERSE_ENVIRONMENT_PRESENT")
    if latest.recovery_evidence_bps >= effective.recovery_bps:
        reasons.append("RECOVERY_EVIDENCE_PRESENT")

    return PositionPathAssessment(
        as_of=latest.as_of,
        state=state,
        evidence_count=len(observations),
        path_support_bps=support,
        adverse_dominance_bps=adversity,
        adverse_persistence_bps=adverse_persistence,
        recovery_persistence_bps=recovery_persistence,
        winner_protection_bps=winner_protection,
        terminal_failure_risk_bps=terminal_failure,
        reasons=tuple(dict.fromkeys(reasons)),
    )
