"""Real regime-transition intelligence built on causal market trajectories."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedRegimeTransitionState,
    SharedTraderIntelligenceValidationError,
)
from qore.infrastructure.core_stack_v2.transition_intelligence import (
    DynamicTransitionPolicy,
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
    MarketTransitionObservation,
    assess_market_trajectory,
)


class SharedRegimeHypothesis(StrEnum):
    CURRENT_WORLD_CONTINUES = "H1_CURRENT_WORLD_CONTINUES"
    MACRO_TRANSITION = "H2_MACRO_TRANSITION"
    IDIOSYNCRATIC_SHOCK = "H3_IDIOSYNCRATIC_SHOCK"
    RELATIONSHIP_BREAK = "H4_RELATIONSHIP_BREAK"
    LIQUIDITY_TRANSITION = "H5_LIQUIDITY_TRANSITION"
    UNKNOWN_INSUFFICIENT = "H6_UNKNOWN_INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class SharedRegimeHypothesisEvidence:
    hypothesis: SharedRegimeHypothesis
    support_bps: int

    def __post_init__(self) -> None:
        if type(self.support_bps) is not int or not 0 <= self.support_bps <= 10_000:
            raise SharedTraderIntelligenceValidationError(
                "regime hypothesis support_bps must be int within 0..10000"
            )


@dataclass(frozen=True, slots=True)
class SharedRegimeTransitionAssessment:
    state: SharedRegimeTransitionState
    trajectory_state: MarketTrajectoryState
    as_of: datetime
    continuation_support_bps: int
    transition_risk_bps: int
    reversal_evidence_bps: int
    relationship_decay_bps: int
    uncertainty_bps: int
    expected_horizon: str
    competing_hypotheses: tuple[SharedRegimeHypothesisEvidence, ...]
    reason_codes: tuple[str, ...]
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    execution_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "continuation_support_bps",
            "transition_risk_bps",
            "reversal_evidence_bps",
            "relationship_decay_bps",
            "uncertainty_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if not self.expected_horizon.strip():
            raise SharedTraderIntelligenceValidationError(
                "regime expected_horizon must be explicit"
            )
        expected = tuple(
            SharedRegimeHypothesisEvidence(item, 0)
            for item in SharedRegimeHypothesis
        )
        expected_ids = tuple(item.hypothesis for item in expected)
        actual_ids = tuple(item.hypothesis for item in self.competing_hypotheses)
        if actual_ids != expected_ids:
            raise SharedTraderIntelligenceValidationError(
                "regime competing hypotheses must preserve H1-H6 order"
            )
        if not self.reason_codes:
            raise SharedTraderIntelligenceValidationError(
                "regime assessment requires reason codes"
            )
        if (
            self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.execution_authority
            or self.strategy_mutation_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "regime transition intelligence cannot carry trading authority"
            )


def _mean(*values: int) -> int:
    return sum(values) // len(values)


def _map_state(
    trajectory: MarketTrajectoryAssessment,
) -> SharedRegimeTransitionState:
    mapping = {
        MarketTrajectoryState.HEALTHY: SharedRegimeTransitionState.STABLE,
        MarketTrajectoryState.WEAKENING: (
            SharedRegimeTransitionState.EXHAUSTION_RISK
        ),
        MarketTrajectoryState.DIVERGING: (
            SharedRegimeTransitionState.STRUCTURAL_DECOUPLING
        ),
        MarketTrajectoryState.DETERIORATING: (
            SharedRegimeTransitionState.TRANSITION_DEVELOPING
        ),
        MarketTrajectoryState.FAILURE: SharedRegimeTransitionState.REGIME_BREAK,
        MarketTrajectoryState.STABILIZING: (
            SharedRegimeTransitionState.TRANSITION_DEVELOPING
        ),
        MarketTrajectoryState.RECOVERING: (
            SharedRegimeTransitionState.CONTINUATION
        ),
        MarketTrajectoryState.INSUFFICIENT: (
            SharedRegimeTransitionState.INSUFFICIENT
        ),
    }
    return mapping[trajectory.state]


def assess_shared_regime_transition(
    observations: Sequence[MarketTransitionObservation],
    *,
    policy: DynamicTransitionPolicy | None = None,
    expected_horizon: str = "UNSPECIFIED_RESEARCH_HORIZON",
) -> SharedRegimeTransitionAssessment:
    """Assess competing regime-transition explanations from evidence at T."""

    trajectory = assess_market_trajectory(observations, policy=policy)
    latest = observations[-1]

    relationship_break = _mean(
        10_000 - latest.cross_market_confirmation_bps,
        10_000 - latest.correlation_stability_bps,
        latest.contradiction_bps,
    )
    liquidity_transition = _mean(
        10_000 - latest.liquidity_capacity_bps,
        10_000 - latest.volatility_stability_bps,
        latest.anomaly_bps,
    )
    macro_transition = _mean(
        trajectory.deterioration_pressure_bps,
        latest.uncertainty_bps,
        latest.opposite_pressure_bps,
    )
    idiosyncratic_shock = _mean(
        latest.anomaly_bps,
        latest.cross_market_confirmation_bps,
    )
    unknown = _mean(
        latest.uncertainty_bps,
        10_000 - latest.data_integrity_bps,
    )
    transition_risk = max(
        trajectory.deterioration_pressure_bps,
        relationship_break,
        liquidity_transition,
        macro_transition,
    )
    reversal_evidence = _mean(
        trajectory.adversity_bps,
        latest.opposite_pressure_bps,
        latest.contradiction_bps,
    )

    hypotheses = (
        SharedRegimeHypothesisEvidence(
            SharedRegimeHypothesis.CURRENT_WORLD_CONTINUES,
            trajectory.support_bps,
        ),
        SharedRegimeHypothesisEvidence(
            SharedRegimeHypothesis.MACRO_TRANSITION,
            macro_transition,
        ),
        SharedRegimeHypothesisEvidence(
            SharedRegimeHypothesis.IDIOSYNCRATIC_SHOCK,
            idiosyncratic_shock,
        ),
        SharedRegimeHypothesisEvidence(
            SharedRegimeHypothesis.RELATIONSHIP_BREAK,
            relationship_break,
        ),
        SharedRegimeHypothesisEvidence(
            SharedRegimeHypothesis.LIQUIDITY_TRANSITION,
            liquidity_transition,
        ),
        SharedRegimeHypothesisEvidence(
            SharedRegimeHypothesis.UNKNOWN_INSUFFICIENT,
            unknown,
        ),
    )
    reasons = tuple(
        sorted(
            set(
                trajectory.reasons
                + (
                    "COMPETING_WORLDS_PRESERVED",
                    "SOURCE_ONLY_TRAJECTORY",
                )
            )
        )
    )

    return SharedRegimeTransitionAssessment(
        state=_map_state(trajectory),
        trajectory_state=trajectory.state,
        as_of=trajectory.as_of,
        continuation_support_bps=trajectory.support_bps,
        transition_risk_bps=transition_risk,
        reversal_evidence_bps=reversal_evidence,
        relationship_decay_bps=relationship_break,
        uncertainty_bps=latest.uncertainty_bps,
        expected_horizon=expected_horizon,
        competing_hypotheses=hypotheses,
        reason_codes=reasons,
    )
