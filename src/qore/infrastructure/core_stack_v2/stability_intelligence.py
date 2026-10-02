"""Universal Shared drawdown-stability intelligence.

Shared reasons from current market evidence plus CLOSED trader-performance
telemetry that is already known before the next opportunity. It emits only
cognitive context. It never owns order, sizing, capital, Risk, execution or
strategy-mutation authority.

The controller targets a preferred 4R-6R drawdown band. This is a cognitive
stability objective, not a mathematical guarantee against gaps or slippage.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.core_stack_v2.contracts import CognitiveState

ZERO = Decimal("0")
ONE = Decimal("1")
TEN_THOUSAND = Decimal("10000")


class StabilityMode(StrEnum):
    STABLE = "STABLE"
    WATCH = "WATCH"
    DEFENSIVE = "DEFENSIVE"
    RECOVERY = "RECOVERY"


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()


def _bps_ratio(numerator: Decimal, denominator: Decimal) -> int:
    if denominator <= 0:
        raise ValueError("ratio denominator must be positive")
    ratio = max(ZERO, min(ONE, numerator / denominator))
    return int(ratio * TEN_THOUSAND)


def _clamp_bps(value: int) -> int:
    return max(0, min(10_000, value))


@dataclass(frozen=True, slots=True)
class TraderStabilityTelemetry:
    trader_id: str
    as_of: datetime
    last_closed_trade_at: datetime | None
    current_drawdown_r: Decimal
    drawdown_velocity_r: Decimal
    recovery_from_trough_r: Decimal
    recent_trade_count: int
    recent_loss_count: int
    recent_net_r: Decimal
    max_single_trade_risk_r: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.trader_id:
            raise ValueError("trader_id must be non-empty")
        _iso(self.as_of)
        if self.last_closed_trade_at is not None:
            _iso(self.last_closed_trade_at)
            if self.last_closed_trade_at > self.as_of:
                raise ValueError("future closed-trade evidence forbidden")
        if self.current_drawdown_r < 0:
            raise ValueError("current_drawdown_r cannot be negative")
        if self.recovery_from_trough_r < 0:
            raise ValueError("recovery_from_trough_r cannot be negative")
        if self.recent_trade_count < 0 or self.recent_loss_count < 0:
            raise ValueError("recent trade counts cannot be negative")
        if self.recent_loss_count > self.recent_trade_count:
            raise ValueError("recent losses cannot exceed recent trades")
        if self.max_single_trade_risk_r is not None and self.max_single_trade_risk_r <= 0:
            raise ValueError("max_single_trade_risk_r must be positive")


@dataclass(frozen=True, slots=True)
class MarketStabilityEvidence:
    as_of: datetime
    regime: str
    transition: str
    uncertainty_bps: int
    contradiction_bps: int
    cross_market_confirmation_bps: int
    failure_hypothesis_bps: int
    continuation_support_bps: int
    anomaly_bps: int

    def __post_init__(self) -> None:
        _iso(self.as_of)
        if not self.regime or not self.transition:
            raise ValueError("regime and transition must be non-empty")
        for value in (
            self.uncertainty_bps,
            self.contradiction_bps,
            self.cross_market_confirmation_bps,
            self.failure_hypothesis_bps,
            self.continuation_support_bps,
            self.anomaly_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("market evidence basis points must be within 0..10000")


@dataclass(frozen=True, slots=True)
class StabilityPolicy:
    preferred_drawdown_floor_r: Decimal = Decimal("4")
    hard_drawdown_ceiling_r: Decimal = Decimal("6")
    watch_pressure_bps: int = 4_500
    defensive_pressure_bps: int = 6_250
    recovery_confidence_bps: int = 6_000

    def __post_init__(self) -> None:
        if self.preferred_drawdown_floor_r <= 0:
            raise ValueError("preferred_drawdown_floor_r must be positive")
        if self.hard_drawdown_ceiling_r <= self.preferred_drawdown_floor_r:
            raise ValueError("hard drawdown ceiling must exceed preferred floor")
        for value in (
            self.watch_pressure_bps,
            self.defensive_pressure_bps,
            self.recovery_confidence_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("policy basis points must be within 0..10000")


@dataclass(frozen=True, slots=True)
class DrawdownStabilityAssessment:
    trader_id: str
    as_of: datetime
    mode: StabilityMode
    cognitive_state: CognitiveState
    drawdown_pressure_bps: int
    loss_cluster_pressure_bps: int
    market_adversity_bps: int
    deterioration_pressure_bps: int
    recovery_confidence_bps: int
    headroom_to_hard_ceiling_r: Decimal
    reasons: tuple[str, ...]
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    execution_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        _iso(self.as_of)
        for value in (
            self.drawdown_pressure_bps,
            self.loss_cluster_pressure_bps,
            self.market_adversity_bps,
            self.deterioration_pressure_bps,
            self.recovery_confidence_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("assessment basis points must be within 0..10000")
        if (
            self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.execution_authority
            or self.strategy_mutation_authority
        ):
            raise ValueError("Shared stability intelligence cannot carry trading authority")


def assess_drawdown_stability(
    telemetry: TraderStabilityTelemetry,
    market: MarketStabilityEvidence,
    *,
    policy: StabilityPolicy | None = None,
) -> DrawdownStabilityAssessment:
    effective = policy or StabilityPolicy()
    if market.as_of > telemetry.as_of:
        raise ValueError("future market evidence forbidden")

    drawdown_pressure = _bps_ratio(
        telemetry.current_drawdown_r,
        effective.hard_drawdown_ceiling_r,
    )
    loss_cluster_pressure = (
        0
        if telemetry.recent_trade_count == 0
        else int(
            Decimal(telemetry.recent_loss_count)
            / Decimal(telemetry.recent_trade_count)
            * TEN_THOUSAND
        )
    )

    cross_market_adverse = 10_000 - market.cross_market_confirmation_bps
    continuation_failure_gap = max(
        0,
        market.failure_hypothesis_bps - market.continuation_support_bps,
    )
    market_adversity = _clamp_bps(
        (
            market.uncertainty_bps
            + market.contradiction_bps
            + cross_market_adverse
            + market.failure_hypothesis_bps
            + continuation_failure_gap
            + market.anomaly_bps
        )
        // 6
    )

    worsening_velocity_bps = _bps_ratio(
        max(ZERO, telemetry.drawdown_velocity_r),
        max(Decimal("1"), effective.preferred_drawdown_floor_r),
    )
    negative_recent_r_bps = _bps_ratio(
        max(ZERO, -telemetry.recent_net_r),
        max(Decimal("1"), effective.preferred_drawdown_floor_r),
    )

    deterioration = _clamp_bps(
        int(
            Decimal(drawdown_pressure) * Decimal("0.35")
            + Decimal(loss_cluster_pressure) * Decimal("0.20")
            + Decimal(market_adversity) * Decimal("0.25")
            + Decimal(worsening_velocity_bps) * Decimal("0.10")
            + Decimal(negative_recent_r_bps) * Decimal("0.10")
        )
    )

    recovery_market_support = _clamp_bps(
        (
            market.cross_market_confirmation_bps
            + market.continuation_support_bps
            + (10_000 - market.uncertainty_bps)
            + (10_000 - market.contradiction_bps)
        )
        // 4
    )
    recovery_progress_bps = _bps_ratio(
        telemetry.recovery_from_trough_r,
        max(Decimal("1"), effective.preferred_drawdown_floor_r),
    )
    recovery_confidence = _clamp_bps(
        int(
            Decimal(recovery_market_support) * Decimal("0.60")
            + Decimal(recovery_progress_bps) * Decimal("0.25")
            + Decimal(max(0, 10_000 - loss_cluster_pressure)) * Decimal("0.15")
        )
    )

    headroom = effective.hard_drawdown_ceiling_r - telemetry.current_drawdown_r
    reasons: list[str] = []

    if telemetry.current_drawdown_r >= effective.hard_drawdown_ceiling_r:
        mode = StabilityMode.DEFENSIVE
        state = CognitiveState.ABSTAIN
        reasons.append("HARD_DRAWDOWN_CEILING_REACHED")
    elif (
        telemetry.current_drawdown_r >= effective.preferred_drawdown_floor_r
        and deterioration >= effective.defensive_pressure_bps
    ):
        mode = StabilityMode.DEFENSIVE
        state = CognitiveState.ABSTAIN
        reasons.extend(("PREFERRED_DRAWDOWN_BAND_ENTERED", "CAUSAL_DETERIORATION_HIGH"))
    elif drawdown_pressure >= 5_000 and deterioration >= effective.watch_pressure_bps:
        mode = StabilityMode.WATCH
        state = CognitiveState.WAIT
        reasons.append("DRAWDOWN_PRESSURE_AND_MARKET_DETERIORATION")
    elif (
        telemetry.current_drawdown_r >= Decimal("1")
        and telemetry.drawdown_velocity_r < 0
        and telemetry.recovery_from_trough_r > 0
        and recovery_confidence >= effective.recovery_confidence_bps
    ):
        mode = StabilityMode.RECOVERY
        state = CognitiveState.PASS
        reasons.append("CAUSAL_RECOVERY_CONFIRMED")
    elif deterioration >= effective.watch_pressure_bps:
        mode = StabilityMode.WATCH
        state = CognitiveState.WAIT
        reasons.append("EARLY_DETERIORATION_DETECTED")
    else:
        mode = StabilityMode.STABLE
        state = CognitiveState.PASS
        reasons.append("STABILITY_PRESSURE_ACCEPTABLE")

    if market.failure_hypothesis_bps >= 7_500:
        reasons.append("FAILURE_HYPOTHESIS_DOMINANT")
    if market.cross_market_confirmation_bps <= 2_500:
        reasons.append("CROSS_MARKET_CONFIRMATION_WEAK")
    if loss_cluster_pressure >= 7_000:
        reasons.append("RECENT_LOSS_CLUSTER_HIGH")
    if (
        telemetry.max_single_trade_risk_r is not None
        and headroom < telemetry.max_single_trade_risk_r
    ):
        reasons.append("HARD_DD_HEADROOM_BELOW_DECLARED_SINGLE_TRADE_RISK")

    return DrawdownStabilityAssessment(
        trader_id=telemetry.trader_id,
        as_of=telemetry.as_of,
        mode=mode,
        cognitive_state=state,
        drawdown_pressure_bps=drawdown_pressure,
        loss_cluster_pressure_bps=loss_cluster_pressure,
        market_adversity_bps=market_adversity,
        deterioration_pressure_bps=deterioration,
        recovery_confidence_bps=recovery_confidence,
        headroom_to_hard_ceiling_r=headroom,
        reasons=tuple(reasons),
    )
