"""Real-time authority-free trade management for Shared Core.

Shared's third eye must not stop at classification. Once a methodology-valid
trade exists, Shared may continuously issue a cognitive management directive
that the trader/runtime adapter can translate into a broker-side stop/target
update.

This layer is deliberately sizing-blind. It cannot change position size,
capital, order quantity, or risk budget. Economic experiments must therefore
measure the true effect of Shared intelligence through path management only.

The hot path consumes already-resident causal assessments and is O(1). It does
no I/O, no historical scan, no future lookup, and no terminal-outcome lookup.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.core_stack_v2.instinct_intelligence import (
    InstinctAssessment,
    InstinctSituation,
    SupportMethodology,
)
from qore.infrastructure.core_stack_v2.journey_intelligence import (
    JourneyAssessment,
    JourneyDisposition,
)
from qore.infrastructure.core_stack_v2.path_intelligence import (
    PositionPathAssessment,
    PositionPathState,
)

ZERO = Decimal("0")
ONE = Decimal("1")


class RealtimeTradeAction(StrEnum):
    HOLD = "HOLD"
    DEFEND = "DEFEND"
    TRAIL = "TRAIL"
    EXTEND = "EXTEND"
    TRAIL_AND_EXTEND = "TRAIL_AND_EXTEND"
    EXIT_RISK = "EXIT_RISK"
    INSUFFICIENT = "INSUFFICIENT"


class StopManagementMode(StrEnum):
    KEEP = "KEEP"
    CAP_HALF_RISK = "CAP_HALF_RISK"
    CAP_QUARTER_RISK = "CAP_QUARTER_RISK"
    BREAKEVEN = "BREAKEVEN"
    TRAIL_WIDE = "TRAIL_WIDE"
    TRAIL_TIGHT = "TRAIL_TIGHT"


class TargetManagementMode(StrEnum):
    KEEP = "KEEP"
    EXTEND_125 = "EXTEND_125"
    EXTEND_150 = "EXTEND_150"
    EXTEND_200 = "EXTEND_200"


@dataclass(frozen=True, slots=True)
class RealtimeManagementPolicy:
    minimum_integrity_bps: int = 7_500
    early_progress_bps: int = 2_500
    established_progress_bps: int = 4_500
    extension_progress_bps: int = 6_000
    strong_extension_capacity_bps: int = 8_200
    medium_extension_capacity_bps: int = 7_000
    terminal_threat_bps: int = 7_200
    rapid_threat_bps: int = 6_200
    winner_protection_bps: int = 6_200

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class RealtimeTradeManagementDirective:
    as_of: datetime
    action: RealtimeTradeAction
    stop_mode: StopManagementMode
    target_mode: TargetManagementMode
    maximum_remaining_loss_r: Decimal | None
    trail_distance_r: Decimal | None
    target_multiplier: Decimal
    market_support_bps: int
    threat_bps: int
    urgency_bps: int
    winner_protection_bps: int
    extension_capacity_bps: int
    reasons: tuple[str, ...]
    management_directive_authority: bool = True
    sizing_change_allowed: bool = False
    stop_widening_allowed: bool = False
    history_scan_used: bool = False
    io_used: bool = False
    terminal_outcome_used: bool = False
    future_market_used: bool = False
    risk_budget_authority: bool = False
    order_quantity_authority: bool = False
    broker_execution_authority: bool = False
    complexity: str = "O(1)"

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "market_support_bps",
            "threat_bps",
            "urgency_bps",
            "winner_protection_bps",
            "extension_capacity_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.maximum_remaining_loss_r is not None:
            if not ZERO <= self.maximum_remaining_loss_r <= ONE:
                raise ValueError("maximum_remaining_loss_r must be within 0..1R")
        if self.trail_distance_r is not None:
            if self.trail_distance_r <= ZERO:
                raise ValueError("trail_distance_r must be positive")
        if self.target_multiplier < ONE:
            raise ValueError("target multiplier cannot shrink the original target")
        if (
            self.sizing_change_allowed
            or self.stop_widening_allowed
            or self.history_scan_used
            or self.io_used
            or self.terminal_outcome_used
            or self.future_market_used
            or self.risk_budget_authority
            or self.order_quantity_authority
            or self.broker_execution_authority
        ):
            raise ValueError(
                "Shared real-time management cannot change sizing, widen stops, "
                "use hidden future/outcome data, or own broker execution"
            )


def _target_mode(capacity_bps: int, policy: RealtimeManagementPolicy) -> tuple[
    TargetManagementMode,
    Decimal,
]:
    if capacity_bps >= policy.strong_extension_capacity_bps:
        return TargetManagementMode.EXTEND_200, Decimal("2.00")
    if capacity_bps >= policy.medium_extension_capacity_bps:
        return TargetManagementMode.EXTEND_150, Decimal("1.50")
    return TargetManagementMode.EXTEND_125, Decimal("1.25")


def assess_realtime_trade_management(
    instinct: InstinctAssessment,
    journey: JourneyAssessment,
    path: PositionPathAssessment,
    *,
    progress_bps: int,
    data_integrity_bps: int = 10_000,
    policy: RealtimeManagementPolicy | None = None,
) -> RealtimeTradeManagementDirective:
    """Select immediate stop/target management from resident causal state."""
    effective = policy or RealtimeManagementPolicy()
    if not 0 <= progress_bps <= 10_000:
        raise ValueError("progress_bps must be within 0..10000")
    if not 0 <= data_integrity_bps <= 10_000:
        raise ValueError("data_integrity_bps must be within 0..10000")
    if instinct.as_of != journey.as_of or instinct.as_of != path.as_of:
        raise ValueError("resident management assessments must share as_of")

    reasons: list[str] = []
    stop_mode = StopManagementMode.KEEP
    target_mode = TargetManagementMode.KEEP
    maximum_remaining_loss_r: Decimal | None = None
    trail_distance_r: Decimal | None = None
    target_multiplier = ONE

    insufficient = (
        data_integrity_bps < effective.minimum_integrity_bps
        or instinct.situation is InstinctSituation.INSUFFICIENT
        or journey.disposition is JourneyDisposition.INSUFFICIENT
        or path.state is PositionPathState.INSUFFICIENT
    )
    if insufficient:
        action = RealtimeTradeAction.INSUFFICIENT
        reasons.append("REALTIME_MANAGEMENT_EVIDENCE_INSUFFICIENT")
    elif (
        journey.disposition is JourneyDisposition.EXIT_RISK_WARNING
        or (
            instinct.situation is InstinctSituation.TERMINAL_FAILURE_RISK
            and path.state is PositionPathState.FAILURE_RISK
        )
    ):
        action = RealtimeTradeAction.EXIT_RISK
        stop_mode = StopManagementMode.CAP_QUARTER_RISK
        maximum_remaining_loss_r = Decimal("0.25")
        reasons.extend(
            (
                "TERMINAL_FAILURE_RISK_CONVERGED",
                "LOSS_MUST_BE_COMPRESSED_IMMEDIATELY",
            )
        )
    elif (
        instinct.support_methodology is SupportMethodology.IMMEDIATE_DEFENSE
        or instinct.threat_bps >= effective.terminal_threat_bps
    ) and progress_bps < effective.established_progress_bps:
        action = RealtimeTradeAction.DEFEND
        stop_mode = StopManagementMode.CAP_QUARTER_RISK
        maximum_remaining_loss_r = Decimal("0.25")
        reasons.append("EARLY_TRADE_TERMINAL_THREAT")
    elif (
        instinct.support_methodology is SupportMethodology.PROGRESSIVE_DEFENSE
        or (
            instinct.situation is InstinctSituation.RAPID_DETERIORATION
            and instinct.threat_bps >= effective.rapid_threat_bps
        )
    ) and progress_bps < effective.established_progress_bps:
        action = RealtimeTradeAction.DEFEND
        stop_mode = StopManagementMode.CAP_HALF_RISK
        maximum_remaining_loss_r = Decimal("0.50")
        reasons.append("EARLY_TRADE_RAPID_DETERIORATION")
    elif (
        progress_bps >= effective.established_progress_bps
        and (
            path.winner_protection_bps >= effective.winner_protection_bps
            or path.state
            in {
                PositionPathState.FAVORABLE_EXPANSION,
                PositionPathState.HEALTHY_PULLBACK,
            }
        )
    ):
        extension_supported = (
            journey.disposition is JourneyDisposition.EXTEND
            or instinct.support_methodology is SupportMethodology.EXTENSION_SUPPORT
        )
        if (
            extension_supported
            and progress_bps >= effective.extension_progress_bps
            and instinct.extension_capacity_bps >= effective.medium_extension_capacity_bps
        ):
            action = RealtimeTradeAction.TRAIL_AND_EXTEND
            stop_mode = StopManagementMode.TRAIL_WIDE
            trail_distance_r = Decimal("0.75")
            target_mode, target_multiplier = _target_mode(
                instinct.extension_capacity_bps,
                effective,
            )
            reasons.extend(
                (
                    "WINNER_PATH_ESTABLISHED",
                    "EXTENSION_CAPACITY_SUPPORTED",
                    "PROTECT_AND_ALLOW_EXPANSION",
                )
            )
        else:
            action = RealtimeTradeAction.TRAIL
            stop_mode = StopManagementMode.TRAIL_WIDE
            trail_distance_r = Decimal("0.75")
            reasons.extend(
                (
                    "WINNER_PATH_ESTABLISHED",
                    "TRAIL_WITHOUT_CHOKING_NORMAL_PULLBACK",
                )
            )
    elif (
        progress_bps >= effective.early_progress_bps
        and (
            path.state is PositionPathState.ADVERSE_DOMINANCE
            or instinct.situation is InstinctSituation.RAPID_DETERIORATION
        )
    ):
        action = RealtimeTradeAction.TRAIL
        stop_mode = StopManagementMode.TRAIL_TIGHT
        trail_distance_r = Decimal("0.50")
        reasons.append("PROGRESS_PRESENT_BUT_ADVERSITY_RISING")
    elif (
        journey.disposition is JourneyDisposition.EXTEND
        and instinct.support_methodology is SupportMethodology.EXTENSION_SUPPORT
        and progress_bps >= effective.extension_progress_bps
    ):
        action = RealtimeTradeAction.EXTEND
        target_mode, target_multiplier = _target_mode(
            instinct.extension_capacity_bps,
            effective,
        )
        reasons.append("EXTENSION_SUPPORTED_WITHOUT_STOP_CHANGE")
    else:
        action = RealtimeTradeAction.HOLD
        reasons.append("ORIGINAL_TRADE_GEOMETRY_REMAINS_VALID")

    return RealtimeTradeManagementDirective(
        as_of=instinct.as_of.astimezone(UTC),
        action=action,
        stop_mode=stop_mode,
        target_mode=target_mode,
        maximum_remaining_loss_r=maximum_remaining_loss_r,
        trail_distance_r=trail_distance_r,
        target_multiplier=target_multiplier,
        market_support_bps=instinct.market_support_bps,
        threat_bps=instinct.threat_bps,
        urgency_bps=instinct.urgency_bps,
        winner_protection_bps=path.winner_protection_bps,
        extension_capacity_bps=instinct.extension_capacity_bps,
        reasons=tuple(dict.fromkeys(reasons)),
    )
