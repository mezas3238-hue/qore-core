"""Relational adversity-challenge intelligence for autonomous Shared Core.

This layer represents *how* local position-path deterioration relates to the
broader market environment through time.  It addresses a failure mode where
local path, geometry and future heads can look terminal while broad market
support is still intact and the path later recovers.

The representation is generic, causal and outcome-blind at runtime.  It
accepts only bounded point-in-time Shared evidence.  It has no trader,
methodology, symbol, calendar, PnL, sizing, risk, order or execution authority.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AdversityChallengeState(StrEnum):
    LOCAL_COLLAPSE_BROAD_SUPPORT_INTACT = "LOCAL_COLLAPSE_BROAD_SUPPORT_INTACT"
    LOCAL_AND_BROAD_DETERIORATION = "LOCAL_AND_BROAD_DETERIORATION"
    RECOVERY_CHALLENGE = "RECOVERY_CHALLENGE"
    RECOVERY_REASSERTING = "RECOVERY_REASSERTING"
    TERMINAL_CONVERGENCE = "TERMINAL_CONVERGENCE"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class AdversityChallengeObservation:
    as_of: datetime
    data_integrity_bps: int
    path_support_bps: int
    path_adverse_bps: int
    path_terminal_bps: int
    winner_protection_bps: int
    trajectory_support_bps: int
    trajectory_adverse_bps: int
    environment_support_bps: int
    environment_adverse_bps: int
    recovery_strength_bps: int
    target_capacity_bps: int
    futures_terminal_bps: int
    futures_recovery_bps: int
    uncertainty_bps: int

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in self.__dataclass_fields__:
            if name == "as_of":
                continue
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class AdversityChallengePolicy:
    minimum_observations: int = 4
    maximum_observations: int = 12
    minimum_integrity_bps: int = 7_500
    local_collapse_bps: int = 5_500
    broad_support_reserve_bps: int = 800
    broad_deterioration_bps: int = 1_000
    terminal_convergence_bps: int = 6_000
    recovery_reassertion_bps: int = 1_200
    maximum_uncertainty_bps: int = 7_500

    def __post_init__(self) -> None:
        if self.minimum_observations < 3:
            raise ValueError("minimum_observations must be at least 3")
        if self.maximum_observations < self.minimum_observations:
            raise ValueError("maximum_observations must cover minimum_observations")
        for name in (
            "minimum_integrity_bps",
            "local_collapse_bps",
            "broad_support_reserve_bps",
            "broad_deterioration_bps",
            "terminal_convergence_bps",
            "recovery_reassertion_bps",
            "maximum_uncertainty_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class AdversityChallengeAssessment:
    as_of: datetime
    state: AdversityChallengeState
    evidence_count: int
    local_adverse_pressure_bps: int
    local_pressure_velocity_bps: int
    broad_support_reserve_bps: int
    broad_support_velocity_bps: int
    recovery_reserve_bps: int
    recovery_velocity_bps: int
    local_broad_decoupling_bps: int
    terminal_convergence_bps: int
    uncertainty_bps: int
    reasons: tuple[str, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False


def _clamp(value: int) -> int:
    return max(0, min(10_000, value))


def _signed_delta(current: int, previous: int) -> int:
    return max(-10_000, min(10_000, current - previous))


def _local_pressure(row: AdversityChallengeObservation) -> int:
    adverse = (
        row.path_adverse_bps
        + row.path_terminal_bps
        + row.trajectory_adverse_bps
        + row.futures_terminal_bps
    ) // 4
    support = (
        row.path_support_bps
        + row.trajectory_support_bps
        + row.winner_protection_bps
    ) // 3
    return _clamp(adverse + (10_000 - support) // 2)


def _broad_reserve(row: AdversityChallengeObservation) -> int:
    return max(-10_000, min(10_000, row.environment_support_bps - row.environment_adverse_bps))


def _recovery_reserve(row: AdversityChallengeObservation) -> int:
    recovery = (
        row.recovery_strength_bps
        + row.target_capacity_bps
        + row.futures_recovery_bps
    ) // 3
    terminal = (
        row.path_terminal_bps
        + row.futures_terminal_bps
        + row.trajectory_adverse_bps
    ) // 3
    return max(-10_000, min(10_000, recovery - terminal))


def assess_adversity_challenge(
    observations: Sequence[AdversityChallengeObservation],
    *,
    policy: AdversityChallengePolicy | None = None,
) -> AdversityChallengeAssessment:
    """Represent bounded local-vs-broad market adversity topology."""

    p = policy or AdversityChallengePolicy()
    if not observations:
        raise ValueError("observations must not be empty")

    window = tuple(observations[-p.maximum_observations :])
    current = window[-1]
    as_of = current.as_of

    if len(window) < p.minimum_observations:
        return AdversityChallengeAssessment(
            as_of=as_of,
            state=AdversityChallengeState.INSUFFICIENT,
            evidence_count=len(window),
            local_adverse_pressure_bps=0,
            local_pressure_velocity_bps=0,
            broad_support_reserve_bps=0,
            broad_support_velocity_bps=0,
            recovery_reserve_bps=0,
            recovery_velocity_bps=0,
            local_broad_decoupling_bps=0,
            terminal_convergence_bps=0,
            uncertainty_bps=current.uncertainty_bps,
            reasons=("OBSERVATIONS_INSUFFICIENT",),
        )

    if min(row.data_integrity_bps for row in window) < p.minimum_integrity_bps:
        return AdversityChallengeAssessment(
            as_of=as_of,
            state=AdversityChallengeState.INSUFFICIENT,
            evidence_count=len(window),
            local_adverse_pressure_bps=0,
            local_pressure_velocity_bps=0,
            broad_support_reserve_bps=0,
            broad_support_velocity_bps=0,
            recovery_reserve_bps=0,
            recovery_velocity_bps=0,
            local_broad_decoupling_bps=0,
            terminal_convergence_bps=0,
            uncertainty_bps=current.uncertainty_bps,
            reasons=("DATA_INTEGRITY_INSUFFICIENT",),
        )

    prior = window[max(0, len(window) - 4)]
    local_now = _local_pressure(current)
    local_prior = _local_pressure(prior)
    broad_now = _broad_reserve(current)
    broad_prior = _broad_reserve(prior)
    recovery_now = _recovery_reserve(current)
    recovery_prior = _recovery_reserve(prior)

    local_velocity = _signed_delta(local_now, local_prior)
    broad_velocity = _signed_delta(broad_now, broad_prior)
    recovery_velocity = _signed_delta(recovery_now, recovery_prior)

    decoupling = _clamp(
        local_now
        + max(0, broad_now)
        + max(0, broad_velocity)
        - 10_000
    )
    terminal_convergence = _clamp(
        (
            local_now
            + max(0, -broad_now)
            + max(0, -broad_velocity)
            + max(0, -recovery_now)
        )
        // 2
    )

    reasons: list[str] = []
    if current.uncertainty_bps > p.maximum_uncertainty_bps:
        state = AdversityChallengeState.CONTESTED
        reasons.append("UNCERTAINTY_HIGH")
    elif (
        recovery_now >= p.recovery_reassertion_bps
        and recovery_velocity > 0
        and local_velocity <= 0
    ):
        state = AdversityChallengeState.RECOVERY_REASSERTING
        reasons.extend(("RECOVERY_RESERVE_POSITIVE", "LOCAL_PRESSURE_NOT_RISING"))
    elif (
        terminal_convergence >= p.terminal_convergence_bps
        and broad_velocity <= -p.broad_deterioration_bps
        and recovery_now < 0
    ):
        state = AdversityChallengeState.TERMINAL_CONVERGENCE
        reasons.extend(("LOCAL_AND_BROAD_FAILURE_CONVERGE", "RECOVERY_RESERVE_NEGATIVE"))
    elif (
        local_now >= p.local_collapse_bps
        and broad_now >= p.broad_support_reserve_bps
        and broad_velocity > -p.broad_deterioration_bps
    ):
        state = AdversityChallengeState.LOCAL_COLLAPSE_BROAD_SUPPORT_INTACT
        reasons.extend(("LOCAL_COLLAPSE", "BROAD_SUPPORT_REMAINS_INTACT"))
    elif (
        local_now >= p.local_collapse_bps
        and (
            broad_now < 0
            or broad_velocity <= -p.broad_deterioration_bps
        )
    ):
        state = AdversityChallengeState.LOCAL_AND_BROAD_DETERIORATION
        reasons.extend(("LOCAL_COLLAPSE", "BROAD_SUPPORT_DEGRADING"))
    elif local_now >= p.local_collapse_bps:
        state = AdversityChallengeState.RECOVERY_CHALLENGE
        reasons.append("LOCAL_ADVERSITY_REQUIRES_RESOLUTION")
    else:
        state = AdversityChallengeState.CONTESTED
        reasons.append("NO_RELATIONAL_STATE_DOMINANT")

    return AdversityChallengeAssessment(
        as_of=as_of,
        state=state,
        evidence_count=len(window),
        local_adverse_pressure_bps=local_now,
        local_pressure_velocity_bps=local_velocity,
        broad_support_reserve_bps=broad_now,
        broad_support_velocity_bps=broad_velocity,
        recovery_reserve_bps=recovery_now,
        recovery_velocity_bps=recovery_velocity,
        local_broad_decoupling_bps=decoupling,
        terminal_convergence_bps=terminal_convergence,
        uncertainty_bps=current.uncertainty_bps,
        reasons=tuple(reasons),
    )
