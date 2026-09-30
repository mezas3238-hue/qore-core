"""STI-2 V2 causal opportunity discovery by mechanism-specific trajectories.

V2 changes the scientific hypothesis rather than lowering V1 thresholds.
Opportunity emergence is represented by separate source-time mechanism heads
whose temporal level, velocity and persistence are arbitrated only after each
head is evaluated.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
    SharedTraderIntelligenceValidationError,
)


class SharedOpportunityMechanism(StrEnum):
    EXPANSION = "EXPANSION"
    CONTINUATION = "CONTINUATION"
    REVERSAL = "REVERSAL"
    RELATIONSHIP_TRANSITION = "RELATIONSHIP_TRANSITION"


@dataclass(frozen=True, slots=True)
class SharedOpportunityHeadThreshold:
    mechanism: SharedOpportunityMechanism
    early_level_bps: int
    developing_level_bps: int
    mature_level_bps: int
    positive_velocity_bps: int
    persistence_bps: int

    def __post_init__(self) -> None:
        for name in (
            "early_level_bps",
            "developing_level_bps",
            "mature_level_bps",
            "positive_velocity_bps",
            "persistence_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if not (
            self.early_level_bps
            < self.developing_level_bps
            < self.mature_level_bps
        ):
            raise SharedTraderIntelligenceValidationError(
                "trajectory head levels must be strictly ordered"
            )


@dataclass(frozen=True, slots=True)
class SharedOpportunityTrajectoryPolicy:
    policy_id: str
    sequence_window: int
    heads: tuple[SharedOpportunityHeadThreshold, ...]
    minimum_integrity_bps: int
    source_only_calibration: bool
    evidence_refs: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise SharedTraderIntelligenceValidationError(
                "trajectory policy_id must be non-empty"
            )
        if self.sequence_window != 6:
            raise SharedTraderIntelligenceValidationError(
                "STI-2 V2 sequence_window is preregistered at 6"
            )
        expected = tuple(SharedOpportunityMechanism)
        actual = tuple(head.mechanism for head in self.heads)
        if actual != expected:
            raise SharedTraderIntelligenceValidationError(
                "trajectory policy must preserve canonical mechanism order"
            )
        if (
            type(self.minimum_integrity_bps) is not int
            or not 0 <= self.minimum_integrity_bps <= 10_000
        ):
            raise SharedTraderIntelligenceValidationError(
                "minimum_integrity_bps must be int within 0..10000"
            )
        if not self.source_only_calibration:
            raise SharedTraderIntelligenceValidationError(
                "trajectory policy calibration must be source-only"
            )
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "trajectory policy evidence refs must be non-empty and canonical"
            )
        if self.productive_authority:
            raise SharedTraderIntelligenceValidationError(
                "trajectory research policy cannot authorize production"
            )


@dataclass(frozen=True, slots=True)
class SharedOpportunityHeadState:
    mechanism: SharedOpportunityMechanism
    current_level_bps: int
    velocity_bps: int
    persistence_bps: int
    trajectory_score_bps: int
    maturity: SharedOpportunityMaturity


@dataclass(frozen=True, slots=True)
class SharedOpportunityTrajectoryAssessment:
    asset: str
    maturity: SharedOpportunityMaturity
    dominant_mechanism: SharedOpportunityMechanism | None
    head_states: tuple[SharedOpportunityHeadState, ...]
    contradiction_bps: int
    uncertainty_bps: int
    reason_codes: tuple[str, ...]
    creates_trader_setup: bool = False
    execution_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        if not self.asset.strip() or not self.reason_codes:
            raise SharedTraderIntelligenceValidationError(
                "trajectory assessment requires identity and reasons"
            )
        for name in ("contradiction_bps", "uncertainty_bps"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be int within 0..10000"
                )
        if (
            self.creates_trader_setup
            or self.execution_authority
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "opportunity trajectory is attention only"
            )


def opportunity_mechanism_scores(
    observation: SharedOpportunitySourceObservation,
) -> dict[SharedOpportunityMechanism, int]:
    expansion = (
        observation.compression_bps
        + observation.liquidity_accumulation_bps
        + observation.displacement_bps
        + observation.liquidity_vacuum_bps
    ) // 4
    continuation = (
        observation.displacement_bps
        + observation.acceptance_bps
        + observation.leader_confirmation_bps
        + observation.momentum_persistence_bps
    ) // 4
    reversal = (
        observation.failed_auction_bps
        + observation.absorption_bps
        + observation.leader_divergence_bps
        + observation.momentum_decay_bps
        + observation.regime_transition_bps
    ) // 5
    transition = (
        observation.leader_divergence_bps
        + observation.structural_fragility_bps
        + observation.regime_transition_bps
        + observation.anomaly_bps
        + observation.momentum_decay_bps
    ) // 5
    return {
        SharedOpportunityMechanism.EXPANSION: expansion,
        SharedOpportunityMechanism.CONTINUATION: continuation,
        SharedOpportunityMechanism.REVERSAL: reversal,
        SharedOpportunityMechanism.RELATIONSHIP_TRANSITION: transition,
    }


def _maturity(
    *,
    current: int,
    velocity: int,
    persistence: int,
    prior_material: bool,
    threshold: SharedOpportunityHeadThreshold,
) -> SharedOpportunityMaturity:
    if (
        current >= threshold.mature_level_bps
        and persistence >= threshold.persistence_bps
    ):
        return SharedOpportunityMaturity.MATURE
    if current >= threshold.developing_level_bps:
        return SharedOpportunityMaturity.DEVELOPING
    if (
        current >= threshold.early_level_bps
        and velocity >= threshold.positive_velocity_bps
        and persistence >= threshold.persistence_bps
    ):
        return SharedOpportunityMaturity.EARLY
    if (
        prior_material
        and current >= threshold.early_level_bps
        and velocity < 0
    ):
        return SharedOpportunityMaturity.DETERIORATING
    return SharedOpportunityMaturity.NO_OPPORTUNITY


def assess_opportunity_trajectory(
    observations: Sequence[SharedOpportunitySourceObservation],
    *,
    policy: SharedOpportunityTrajectoryPolicy,
) -> SharedOpportunityTrajectoryAssessment:
    if not observations:
        raise SharedTraderIntelligenceValidationError(
            "trajectory engine requires source observations"
        )
    ordered = tuple(observations[-policy.sequence_window :])
    asset = ordered[-1].asset
    for left, right in zip(ordered, ordered[1:], strict=False):
        if left.asset != asset or right.asset != asset:
            raise SharedTraderIntelligenceValidationError(
                "trajectory sequence must use one asset"
            )
        if right.as_of <= left.as_of:
            raise SharedTraderIntelligenceValidationError(
                "trajectory observations must be strictly chronological"
            )

    latest = ordered[-1]
    if latest.data_integrity_bps < policy.minimum_integrity_bps:
        return SharedOpportunityTrajectoryAssessment(
            asset=asset,
            maturity=SharedOpportunityMaturity.INSUFFICIENT,
            dominant_mechanism=None,
            head_states=(),
            contradiction_bps=10_000,
            uncertainty_bps=10_000,
            reason_codes=("DATA_INTEGRITY_INSUFFICIENT",),
        )

    score_rows = [opportunity_mechanism_scores(item) for item in ordered]
    states: list[SharedOpportunityHeadState] = []
    for threshold in policy.heads:
        values = [row[threshold.mechanism] for row in score_rows]
        current = values[-1]
        prior = values[:-1]
        prior_mean = (
            current if not prior else sum(prior) // len(prior)
        )
        velocity = current - prior_mean
        persistence = (
            sum(value >= threshold.early_level_bps for value in values)
            * 10_000
            // len(values)
        )
        prior_material = any(
            value >= threshold.developing_level_bps for value in prior
        )
        maturity = _maturity(
            current=current,
            velocity=velocity,
            persistence=persistence,
            prior_material=prior_material,
            threshold=threshold,
        )
        positive_velocity = max(0, velocity)
        trajectory_score = min(
            10_000,
            (
                current * 5
                + min(10_000, positive_velocity) * 3
                + persistence * 2
            )
            // 10,
        )
        states.append(
            SharedOpportunityHeadState(
                mechanism=threshold.mechanism,
                current_level_bps=current,
                velocity_bps=velocity,
                persistence_bps=persistence,
                trajectory_score_bps=trajectory_score,
                maturity=maturity,
            )
        )

    active = [
        state
        for state in states
        if state.maturity
        not in {
            SharedOpportunityMaturity.NO_OPPORTUNITY,
            SharedOpportunityMaturity.INSUFFICIENT,
        }
    ]
    if active:
        dominant = max(
            active,
            key=lambda item: (
                item.trajectory_score_bps,
                item.current_level_bps,
                item.mechanism.value,
            ),
        )
        dominant_mechanism = dominant.mechanism
        maturity = dominant.maturity
    else:
        dominant_mechanism = None
        maturity = SharedOpportunityMaturity.NO_OPPORTUNITY

    contradiction = (
        latest.leader_divergence_bps
        + latest.structural_fragility_bps
        + latest.anomaly_bps
    ) // 3
    uncertainty = (
        (10_000 - latest.data_integrity_bps)
        + contradiction
        + latest.regime_transition_bps
    ) // 3

    reasons = [
        "MECHANISM_HEADS_BEFORE_ARBITRATION",
        "TEMPORAL_LEVEL_VELOCITY_PERSISTENCE",
    ]
    if dominant_mechanism is not None:
        reasons.append(f"DOMINANT_{dominant_mechanism.value}")
    else:
        reasons.append("NO_MATERIAL_TRAJECTORY")
    if contradiction >= 6_000:
        reasons.append("CONTRADICTION_HIGH")
    if uncertainty >= 6_000:
        reasons.append("UNCERTAINTY_HIGH")

    return SharedOpportunityTrajectoryAssessment(
        asset=asset,
        maturity=maturity,
        dominant_mechanism=dominant_mechanism,
        head_states=tuple(states),
        contradiction_bps=contradiction,
        uncertainty_bps=uncertainty,
        reason_codes=tuple(sorted(reasons)),
    )
