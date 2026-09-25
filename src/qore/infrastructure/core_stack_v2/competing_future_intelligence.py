"""Causal competing-futures intelligence for Shared Core.

This module exists to solve a structural failure mode of scalar instinct scores:
terminal adversity and recoverable adversity can both contain high deterioration,
high recovery persistence, fragility and uncertainty at the same time. Averaging
those dimensions destroys the relation between them.

Competing-futures intelligence preserves causal relations across multiple
pre-entry horizons and asks which future has broader structural support:

- TERMINAL_ADVERSE: adversity dominates recovery across horizons.
- RECOVERABLE_ADVERSE: the fast horizon is adverse while broader horizons
  retain recovery/support dominance.
- SUPPORTIVE: recovery/support dominates without a meaningful adverse fast leg.
- CONFLICTED: the evidence does not separate the futures.
- INSUFFICIENT: not enough causal multi-horizon evidence exists.

No outcomes, PnL, sizing, risk, order, stop, target or execution authority are
accepted by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class CompetingFutureState(StrEnum):
    TERMINAL_ADVERSE = "TERMINAL_ADVERSE"
    RECOVERABLE_ADVERSE = "RECOVERABLE_ADVERSE"
    SUPPORTIVE = "SUPPORTIVE"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"


class HorizonFutureState(StrEnum):
    TERMINAL = "TERMINAL"
    RECOVERY = "RECOVERY"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True, slots=True)
class CausalHorizonSnapshot:
    """One causal pre-entry state at one temporal horizon."""

    horizon_minutes: int
    as_of: datetime
    evidence_count: int
    data_integrity_bps: int
    support_bps: int
    adversity_bps: int
    deterioration_velocity_bps: int
    recovery_velocity_bps: int
    deterioration_persistence_bps: int
    recovery_persistence_bps: int
    cross_market_confirmation_bps: int
    cross_market_fragility_bps: int
    structural_fragility_bps: int
    trend_support_bps: int
    uncertainty_bps: int

    def __post_init__(self) -> None:
        if self.horizon_minutes <= 0:
            raise ValueError("horizon_minutes must be positive")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        for name in (
            "data_integrity_bps",
            "support_bps",
            "adversity_bps",
            "deterioration_velocity_bps",
            "recovery_velocity_bps",
            "deterioration_persistence_bps",
            "recovery_persistence_bps",
            "cross_market_confirmation_bps",
            "cross_market_fragility_bps",
            "structural_fragility_bps",
            "trend_support_bps",
            "uncertainty_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class HorizonFutureVote:
    horizon_minutes: int
    state: HorizonFutureState
    terminal_evidence_count: int
    recovery_evidence_count: int
    terminal_channels: tuple[str, ...]
    recovery_channels: tuple[str, ...]

    @property
    def total_evidence_count(self) -> int:
        return self.terminal_evidence_count + self.recovery_evidence_count


@dataclass(frozen=True, slots=True)
class CompetingFutureAssessment:
    as_of: datetime
    state: CompetingFutureState
    horizon_votes: tuple[HorizonFutureVote, ...]
    terminal_horizon_count: int
    recovery_horizon_count: int
    conflicted_horizon_count: int
    terminal_evidence_bps: int
    recovery_evidence_bps: int
    separation_margin_bps: int
    horizon_agreement_bps: int
    confidence_bps: int
    reasons: tuple[str, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "terminal_evidence_bps",
            "recovery_evidence_bps",
            "separation_margin_bps",
            "horizon_agreement_bps",
            "confidence_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
            or self.stop_authority
            or self.target_authority
        ):
            raise ValueError(
                "competing-futures intelligence cannot use outcomes or carry "
                "trading authority"
            )


_RELATIONAL_CHANNELS: tuple[
    tuple[str, str, str],
    ...,
] = (
    ("SUPPORT_VS_ADVERSITY", "support_bps", "adversity_bps"),
    (
        "RECOVERY_VS_DETERIORATION_VELOCITY",
        "recovery_velocity_bps",
        "deterioration_velocity_bps",
    ),
    (
        "RECOVERY_VS_DETERIORATION_PERSISTENCE",
        "recovery_persistence_bps",
        "deterioration_persistence_bps",
    ),
    (
        "CROSS_CONFIRMATION_VS_FRAGILITY",
        "cross_market_confirmation_bps",
        "cross_market_fragility_bps",
    ),
    (
        "TREND_SUPPORT_VS_STRUCTURAL_FRAGILITY",
        "trend_support_bps",
        "structural_fragility_bps",
    ),
)


def _vote(snapshot: CausalHorizonSnapshot) -> HorizonFutureVote:
    terminal: list[str] = []
    recovery: list[str] = []

    for label, recovery_field, terminal_field in _RELATIONAL_CHANNELS:
        recovery_value = int(getattr(snapshot, recovery_field))
        terminal_value = int(getattr(snapshot, terminal_field))
        if recovery_value > terminal_value:
            recovery.append(label)
        elif terminal_value > recovery_value:
            terminal.append(label)

    # Uncertainty is not allowed to manufacture either future. It can only
    # reduce confidence later; this avoids treating uncertainty itself as
    # terminal evidence.
    if len(terminal) > len(recovery):
        state = HorizonFutureState.TERMINAL
    elif len(recovery) > len(terminal):
        state = HorizonFutureState.RECOVERY
    else:
        state = HorizonFutureState.CONFLICTED

    return HorizonFutureVote(
        horizon_minutes=snapshot.horizon_minutes,
        state=state,
        terminal_evidence_count=len(terminal),
        recovery_evidence_count=len(recovery),
        terminal_channels=tuple(terminal),
        recovery_channels=tuple(recovery),
    )


def _bps(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return min(10_000, max(0, numerator * 10_000 // denominator))


def assess_competing_futures(
    snapshots: tuple[CausalHorizonSnapshot, ...],
) -> CompetingFutureAssessment:
    """Assess terminal vs recoverable adversity without outcome labels.

    At least two horizons are required. All snapshots must describe the same
    decision timestamp. The widest horizon acts as structural confirmation;
    the shortest horizon describes the immediate condition.
    """

    if len(snapshots) < 2:
        if not snapshots:
            raise ValueError("at least one snapshot is required")
        as_of = snapshots[0].as_of.astimezone(UTC)
        return CompetingFutureAssessment(
            as_of=as_of,
            state=CompetingFutureState.INSUFFICIENT,
            horizon_votes=tuple(_vote(item) for item in snapshots),
            terminal_horizon_count=0,
            recovery_horizon_count=0,
            conflicted_horizon_count=len(snapshots),
            terminal_evidence_bps=0,
            recovery_evidence_bps=0,
            separation_margin_bps=0,
            horizon_agreement_bps=0,
            confidence_bps=0,
            reasons=("MULTI_HORIZON_EVIDENCE_INSUFFICIENT",),
        )

    normalized = tuple(sorted(snapshots, key=lambda item: item.horizon_minutes))
    as_of = normalized[0].as_of.astimezone(UTC)
    if any(item.as_of.astimezone(UTC) != as_of for item in normalized):
        raise ValueError("all causal horizons must share the same as_of")
    horizons = [item.horizon_minutes for item in normalized]
    if len(horizons) != len(set(horizons)):
        raise ValueError("horizon_minutes must be unique")

    votes = tuple(_vote(item) for item in normalized)
    terminal_horizons = sum(
        item.state is HorizonFutureState.TERMINAL for item in votes
    )
    recovery_horizons = sum(
        item.state is HorizonFutureState.RECOVERY for item in votes
    )
    conflicted_horizons = len(votes) - terminal_horizons - recovery_horizons

    terminal_evidence = sum(item.terminal_evidence_count for item in votes)
    recovery_evidence = sum(item.recovery_evidence_count for item in votes)
    total_evidence = terminal_evidence + recovery_evidence
    terminal_bps = _bps(terminal_evidence, total_evidence)
    recovery_bps = _bps(recovery_evidence, total_evidence)
    separation = abs(terminal_bps - recovery_bps)

    dominant_horizons = max(terminal_horizons, recovery_horizons)
    agreement = _bps(dominant_horizons, len(votes))
    integrity = min(item.data_integrity_bps for item in normalized)
    uncertainty_penalty = max(item.uncertainty_bps for item in normalized)
    clarity = 10_000 - uncertainty_penalty
    confidence = min(integrity, separation, agreement, clarity)

    fast = votes[0]
    broad = votes[-1]
    reasons: list[str] = []

    if (
        broad.state is HorizonFutureState.TERMINAL
        and terminal_horizons > recovery_horizons
    ):
        state = CompetingFutureState.TERMINAL_ADVERSE
        reasons.extend(
            (
                "BROAD_HORIZON_TERMINAL_CONFIRMATION",
                "TERMINAL_HORIZON_MAJORITY",
            )
        )
    elif (
        fast.state is HorizonFutureState.TERMINAL
        and broad.state is HorizonFutureState.RECOVERY
    ):
        state = CompetingFutureState.RECOVERABLE_ADVERSE
        reasons.extend(
            (
                "FAST_ADVERSITY_PRESENT",
                "BROAD_HORIZON_RECOVERY_DOMINANT",
            )
        )
    elif (
        broad.state is HorizonFutureState.RECOVERY
        and recovery_horizons > terminal_horizons
    ):
        if terminal_horizons > 0:
            state = CompetingFutureState.RECOVERABLE_ADVERSE
            reasons.extend(
                (
                    "ADVERSITY_PRESENT_BUT_NOT_STRUCTURALLY_DOMINANT",
                    "RECOVERY_HORIZON_MAJORITY",
                )
            )
        else:
            state = CompetingFutureState.SUPPORTIVE
            reasons.extend(
                (
                    "RECOVERY_HORIZON_MAJORITY",
                    "NO_TERMINAL_HORIZON",
                )
            )
    else:
        state = CompetingFutureState.CONFLICTED
        reasons.append("FUTURE_PATHS_NOT_SEPARATED")

    if conflicted_horizons:
        reasons.append("CONFLICTED_HORIZON_PRESENT")
    if clarity < 5_000:
        reasons.append("HIGH_UNCERTAINTY_REDUCES_CONFIDENCE")

    return CompetingFutureAssessment(
        as_of=as_of,
        state=state,
        horizon_votes=votes,
        terminal_horizon_count=terminal_horizons,
        recovery_horizon_count=recovery_horizons,
        conflicted_horizon_count=conflicted_horizons,
        terminal_evidence_bps=terminal_bps,
        recovery_evidence_bps=recovery_bps,
        separation_margin_bps=separation,
        horizon_agreement_bps=agreement,
        confidence_bps=confidence,
        reasons=tuple(dict.fromkeys(reasons)),
    )
