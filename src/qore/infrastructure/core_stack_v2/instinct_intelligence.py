"""Ultra-fast constant-time instinct fusion for Shared Core.

The instinct layer is the hot-path third eye. Heavy perception, causal memory,
cross-market analysis and trajectory/environment models run upstream and keep
resident assessments. This module performs no I/O, no history scan, no PnL
lookup and no trader-specific methodology logic. It fuses already-causal,
already-normalized Shared assessments into one immediate market situation and
one authority-free support methodology.

Complexity contract: O(1) time and O(1) memory per assessment.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.environment_intelligence import (
    MarketEnvironmentAssessment,
    MarketEnvironmentState,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathAssessment,
    PositionPathState,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
)


class InstinctSituation(StrEnum):
    SUPPORTIVE_EXPANSION = "SUPPORTIVE_EXPANSION"
    HEALTHY_CONTINUATION = "HEALTHY_CONTINUATION"
    RECOVERY_BUILDING = "RECOVERY_BUILDING"
    CONTESTED = "CONTESTED"
    FRAGILE = "FRAGILE"
    RAPID_DETERIORATION = "RAPID_DETERIORATION"
    TERMINAL_FAILURE_RISK = "TERMINAL_FAILURE_RISK"
    INSUFFICIENT = "INSUFFICIENT"


class SupportMethodology(StrEnum):
    EXTENSION_SUPPORT = "EXTENSION_SUPPORT"
    HOLD_AND_MONITOR = "HOLD_AND_MONITOR"
    RECOVERY_SUPPORT = "RECOVERY_SUPPORT"
    PROGRESSIVE_DEFENSE = "PROGRESSIVE_DEFENSE"
    IMMEDIATE_DEFENSE = "IMMEDIATE_DEFENSE"
    WINNER_PROTECTION = "WINNER_PROTECTION"
    INSUFFICIENT_FAIL_CLOSED = "INSUFFICIENT_FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class InstinctPolicy:
    minimum_integrity_bps: int = 7_500
    immediate_threat_bps: int = 7_200
    rapid_threat_bps: int = 6_200
    fragile_threat_bps: int = 5_200
    strong_support_bps: int = 6_800
    extension_capacity_bps: int = 7_200
    recovery_bps: int = 6_200
    winner_protection_bps: int = 6_200

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class InstinctAssessment:
    as_of: datetime
    situation: InstinctSituation
    support_methodology: SupportMethodology
    market_support_bps: int
    threat_bps: int
    urgency_bps: int
    confidence_bps: int
    winner_protection_bps: int
    expansion_capacity_bps: int
    reasons: tuple[str, ...]
    complexity: str = "O(1)"
    history_scan_used: bool = False
    io_used: bool = False
    pnl_used: bool = False
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    execution_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "market_support_bps",
            "threat_bps",
            "urgency_bps",
            "confidence_bps",
            "winner_protection_bps",
            "expansion_capacity_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if (
            self.history_scan_used
            or self.io_used
            or self.pnl_used
            or self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.execution_authority
            or self.strategy_mutation_authority
        ):
            raise ValueError(
                "Shared instinct hot path cannot carry authority or hidden data access"
            )


def _mean4(a: int, b: int, c: int, d: int) -> int:
    return (a + b + c + d) // 4


def _clamp(value: int) -> int:
    return max(0, min(10_000, value))


def assess_instinct(
    environment: MarketEnvironmentAssessment,
    trajectory: MarketTrajectoryAssessment,
    *,
    path: PositionPathAssessment | None = None,
    opportunity_quality_bps: int = 5_000,
    expansion_capacity_bps: int = 5_000,
    data_integrity_bps: int = 10_000,
    policy: InstinctPolicy | None = None,
) -> InstinctAssessment:
    """Fuse resident Shared assessments into an immediate support methodology."""
    effective = policy or InstinctPolicy()
    for name, value in (
        ("opportunity_quality_bps", opportunity_quality_bps),
        ("expansion_capacity_bps", expansion_capacity_bps),
        ("data_integrity_bps", data_integrity_bps),
    ):
        if not 0 <= value <= 10_000:
            raise ValueError(f"{name} must be within 0..10000")

    if environment.as_of != trajectory.as_of:
        raise ValueError("resident environment and trajectory assessments must share as_of")
    if path is not None and path.as_of != environment.as_of:
        raise ValueError("resident path assessment must share as_of")

    as_of = environment.as_of.astimezone(UTC)
    path_failure = 0 if path is None else path.terminal_failure_risk_bps
    winner_protection = 0 if path is None else path.winner_protection_bps

    market_support = _mean4(
        environment.market_support_bps,
        trajectory.support_bps,
        opportunity_quality_bps,
        expansion_capacity_bps,
    )
    threat = _mean4(
        environment.adverse_environment_bps,
        trajectory.deterioration_pressure_bps,
        trajectory.adversity_bps,
        path_failure,
    )
    urgency = _clamp(
        _mean4(
            environment.adverse_velocity_bps,
            trajectory.deterioration_velocity_bps,
            environment.adverse_persistence_bps,
            trajectory.deterioration_persistence_bps,
        )
    )
    confidence = _clamp(
        _mean4(
            data_integrity_bps,
            10_000 - abs(environment.adverse_environment_bps - trajectory.adversity_bps),
            max(environment.adverse_persistence_bps, environment.recovery_persistence_bps),
            max(
                trajectory.deterioration_persistence_bps,
                trajectory.recovery_persistence_bps,
            ),
        )
    )

    reasons: list[str] = []
    insufficient = (
        data_integrity_bps < effective.minimum_integrity_bps
        or environment.state is MarketEnvironmentState.INSUFFICIENT
        or trajectory.state is MarketTrajectoryState.INSUFFICIENT
        or (path is not None and path.state is PositionPathState.INSUFFICIENT)
    )
    if insufficient:
        situation = InstinctSituation.INSUFFICIENT
        methodology = SupportMethodology.INSUFFICIENT_FAIL_CLOSED
        reasons.append("INSTINCT_EVIDENCE_INSUFFICIENT")
    elif (
        path is not None
        and path.state in {
            PositionPathState.FAVORABLE_EXPANSION,
            PositionPathState.HEALTHY_PULLBACK,
        }
        and winner_protection >= effective.winner_protection_bps
    ):
        situation = InstinctSituation.HEALTHY_CONTINUATION
        methodology = SupportMethodology.WINNER_PROTECTION
        reasons.extend(("ESTABLISHED_WINNER_PATH", "FALSE_DEFENSE_MUST_BE_AVOIDED"))
    elif (
        path is not None
        and path.state is PositionPathState.FAILURE_RISK
        and threat >= effective.immediate_threat_bps
    ):
        situation = InstinctSituation.TERMINAL_FAILURE_RISK
        methodology = SupportMethodology.IMMEDIATE_DEFENSE
        reasons.extend(("PATH_FAILURE_RISK_HIGH", "MARKET_THREAT_CONVERGED"))
    elif (
        trajectory.state is MarketTrajectoryState.FAILURE
        and environment.state in {
            MarketEnvironmentState.ADVERSE_FORMING,
            MarketEnvironmentState.DEFENSIVE,
        }
        and threat >= effective.immediate_threat_bps
    ):
        situation = InstinctSituation.TERMINAL_FAILURE_RISK
        methodology = SupportMethodology.IMMEDIATE_DEFENSE
        reasons.extend(("TRAJECTORY_FAILURE", "ADVERSE_ENVIRONMENT_CONVERGED"))
    elif (
        trajectory.state in {
            MarketTrajectoryState.DETERIORATING,
            MarketTrajectoryState.FAILURE,
        }
        and environment.state in {
            MarketEnvironmentState.DEGRADING,
            MarketEnvironmentState.ADVERSE_FORMING,
            MarketEnvironmentState.DEFENSIVE,
        }
        and max(threat, urgency) >= effective.rapid_threat_bps
    ):
        situation = InstinctSituation.RAPID_DETERIORATION
        methodology = SupportMethodology.PROGRESSIVE_DEFENSE
        reasons.extend(("DETERIORATION_CONVERGED", "DEFENSE_REQUIRED_WITHOUT_ENTRY_ABSTENTION"))
    elif (
        environment.state in {
            MarketEnvironmentState.FRAGILE,
            MarketEnvironmentState.DEGRADING,
        }
        or trajectory.state in {
            MarketTrajectoryState.WEAKENING,
            MarketTrajectoryState.DIVERGING,
        }
        or threat >= effective.fragile_threat_bps
    ):
        situation = InstinctSituation.FRAGILE
        methodology = SupportMethodology.HOLD_AND_MONITOR
        reasons.append("FRAGILITY_PRESENT_NOT_TERMINAL")
    elif (
        environment.state in {
            MarketEnvironmentState.STABILIZING,
            MarketEnvironmentState.RESTORED,
        }
        or trajectory.state in {
            MarketTrajectoryState.STABILIZING,
            MarketTrajectoryState.RECOVERING,
        }
    ) and (
        max(environment.recovery_velocity_bps, trajectory.recovery_velocity_bps)
        >= effective.recovery_bps
        or market_support >= effective.strong_support_bps
    ):
        situation = InstinctSituation.RECOVERY_BUILDING
        methodology = SupportMethodology.RECOVERY_SUPPORT
        reasons.append("RECOVERY_EVIDENCE_CONVERGED")
    elif (
        market_support >= effective.strong_support_bps
        and expansion_capacity_bps >= effective.extension_capacity_bps
        and trajectory.state in {
            MarketTrajectoryState.HEALTHY,
            MarketTrajectoryState.RECOVERING,
        }
        and environment.state in {
            MarketEnvironmentState.SUPPORTIVE,
            MarketEnvironmentState.RESTORED,
        }
    ):
        situation = InstinctSituation.SUPPORTIVE_EXPANSION
        methodology = SupportMethodology.EXTENSION_SUPPORT
        reasons.extend(("MARKET_SUPPORT_STRONG", "EXPANSION_CAPACITY_HIGH"))
    elif (
        trajectory.state is MarketTrajectoryState.HEALTHY
        and environment.state is MarketEnvironmentState.SUPPORTIVE
    ):
        situation = InstinctSituation.HEALTHY_CONTINUATION
        methodology = SupportMethodology.HOLD_AND_MONITOR
        reasons.append("MARKET_SUPPORT_HEALTHY")
    else:
        situation = InstinctSituation.CONTESTED
        methodology = SupportMethodology.HOLD_AND_MONITOR
        reasons.append("NO_TERMINAL_CONCLUSION")

    return InstinctAssessment(
        as_of=as_of,
        situation=situation,
        support_methodology=methodology,
        market_support_bps=market_support,
        threat_bps=threat,
        urgency_bps=urgency,
        confidence_bps=confidence,
        winner_protection_bps=winner_protection,
        expansion_capacity_bps=expansion_capacity_bps,
        reasons=tuple(dict.fromkeys(reasons)),
    )
