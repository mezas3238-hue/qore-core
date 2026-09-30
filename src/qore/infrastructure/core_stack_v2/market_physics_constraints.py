"""MC-10 Market Physics / Constraint Engine research foundation.

"Market physics" here means governed structural consistency, not literal
physical law. The engine rejects internally incompatible source-time
explanations and keeps learned transition support distinct from hard rules.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)


class MarketPhysicsState(StrEnum):
    COMPRESSION = "COMPRESSION"
    ACCEPTANCE = "ACCEPTANCE"
    EXPANSION = "EXPANSION"
    STRUCTURAL_FAILURE = "STRUCTURAL_FAILURE"
    RELATIONSHIP_BREAK = "RELATIONSHIP_BREAK"
    MIXED = "MIXED"


class MarketPhysicsViolation(StrEnum):
    ACCEPTANCE_AND_FAILED_AUCTION = "ACCEPTANCE_AND_FAILED_AUCTION"
    MOMENTUM_PERSISTENCE_AND_DECAY = "MOMENTUM_PERSISTENCE_AND_DECAY"
    LEADER_CONFIRMATION_AND_DIVERGENCE = "LEADER_CONFIRMATION_AND_DIVERGENCE"
    COMPRESSION_AND_DISPLACEMENT = "COMPRESSION_AND_DISPLACEMENT"
    LOW_DATA_INTEGRITY = "LOW_DATA_INTEGRITY"


@dataclass(frozen=True, slots=True)
class LearnedTransitionConstraint:
    previous_state: MarketPhysicsState
    next_state: MarketPhysicsState
    source_count: int
    source_only: bool = True

    def __post_init__(self) -> None:
        if self.source_count <= 0:
            raise ValueError("learned transition source_count must be positive")
        if not self.source_only:
            raise ValueError("learned transition constraints must be source-only")


@dataclass(frozen=True, slots=True)
class MarketPhysicsAssessment:
    state: MarketPhysicsState
    violations: tuple[MarketPhysicsViolation, ...]
    hard_constraints_pass: bool
    learned_transition_seen: bool | None
    learned_transition_source_count: int
    explanation_admissible: bool
    source_only: bool = True
    future_market_used: bool = False
    outcome_used: bool = False
    trader_methodology_used: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.violations != tuple(sorted(set(self.violations), key=lambda x: x.value)):
            raise ValueError("market physics violations must be canonical")
        if self.learned_transition_source_count < 0:
            raise ValueError("learned transition source count cannot be negative")
        if self.explanation_admissible != self.hard_constraints_pass:
            raise ValueError(
                "unseen learned transition cannot be treated as hard impossibility"
            )
        if (
            not self.source_only
            or self.future_market_used
            or self.outcome_used
            or self.trader_methodology_used
            or self.execution_authority
            or self.risk_authority
            or self.capital_authority
        ):
            raise ValueError("market physics research cannot consume forbidden authority")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["state"] = self.state.value
        payload["violations"] = tuple(item.value for item in self.violations)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def classify_market_physics_state(
    observation: SharedOpportunitySourceObservation,
) -> MarketPhysicsState:
    scores = {
        MarketPhysicsState.COMPRESSION: observation.compression_bps,
        MarketPhysicsState.ACCEPTANCE: observation.acceptance_bps,
        MarketPhysicsState.EXPANSION: (
            observation.displacement_bps + observation.momentum_persistence_bps
        )
        // 2,
        MarketPhysicsState.STRUCTURAL_FAILURE: (
            observation.structural_fragility_bps
            + observation.failed_auction_bps
            + observation.liquidity_vacuum_bps
        )
        // 3,
        MarketPhysicsState.RELATIONSHIP_BREAK: (
            observation.leader_divergence_bps
            + observation.regime_transition_bps
            + observation.anomaly_bps
        )
        // 3,
    }
    ordered = sorted(
        scores.items(),
        key=lambda item: (item[1], item[0].value),
        reverse=True,
    )
    if len(ordered) >= 2 and ordered[0][1] - ordered[1][1] < 500:
        return MarketPhysicsState.MIXED
    return ordered[0][0]


def learn_transition_constraints(
    states: tuple[MarketPhysicsState, ...],
) -> tuple[LearnedTransitionConstraint, ...]:
    counts: dict[tuple[MarketPhysicsState, MarketPhysicsState], int] = {}
    for left, right in zip(states, states[1:], strict=False):
        key = (left, right)
        counts[key] = counts.get(key, 0) + 1
    return tuple(
        LearnedTransitionConstraint(
            previous_state=left,
            next_state=right,
            source_count=count,
        )
        for (left, right), count in sorted(
            counts.items(),
            key=lambda item: (item[0][0].value, item[0][1].value),
        )
    )


def _transition_map(
    constraints: tuple[LearnedTransitionConstraint, ...],
) -> Mapping[tuple[MarketPhysicsState, MarketPhysicsState], int]:
    return {
        (item.previous_state, item.next_state): item.source_count
        for item in constraints
    }


def assess_market_physics(
    observation: SharedOpportunitySourceObservation,
    *,
    previous_state: MarketPhysicsState | None = None,
    learned_constraints: tuple[LearnedTransitionConstraint, ...] = (),
    hard_conflict_floor_bps: int = 7_500,
    minimum_integrity_bps: int = 9_500,
) -> MarketPhysicsAssessment:
    if not 0 <= hard_conflict_floor_bps <= 10_000:
        raise ValueError("hard_conflict_floor_bps must be within 0..10000")
    if not 0 <= minimum_integrity_bps <= 10_000:
        raise ValueError("minimum_integrity_bps must be within 0..10000")

    violations: list[MarketPhysicsViolation] = []
    if observation.data_integrity_bps < minimum_integrity_bps:
        violations.append(MarketPhysicsViolation.LOW_DATA_INTEGRITY)
    if (
        observation.acceptance_bps >= hard_conflict_floor_bps
        and observation.failed_auction_bps >= hard_conflict_floor_bps
    ):
        violations.append(MarketPhysicsViolation.ACCEPTANCE_AND_FAILED_AUCTION)
    if (
        observation.momentum_persistence_bps >= hard_conflict_floor_bps
        and observation.momentum_decay_bps >= hard_conflict_floor_bps
    ):
        violations.append(MarketPhysicsViolation.MOMENTUM_PERSISTENCE_AND_DECAY)
    if (
        observation.leader_confirmation_bps >= hard_conflict_floor_bps
        and observation.leader_divergence_bps >= hard_conflict_floor_bps
    ):
        violations.append(MarketPhysicsViolation.LEADER_CONFIRMATION_AND_DIVERGENCE)
    if (
        observation.compression_bps >= hard_conflict_floor_bps
        and observation.displacement_bps >= hard_conflict_floor_bps
    ):
        violations.append(MarketPhysicsViolation.COMPRESSION_AND_DISPLACEMENT)

    state = classify_market_physics_state(observation)
    transition_seen: bool | None = None
    transition_count = 0
    if previous_state is not None:
        transition_count = _transition_map(learned_constraints).get(
            (previous_state, state),
            0,
        )
        transition_seen = transition_count > 0

    canonical = tuple(sorted(set(violations), key=lambda item: item.value))
    hard_pass = not canonical
    return MarketPhysicsAssessment(
        state=state,
        violations=canonical,
        hard_constraints_pass=hard_pass,
        learned_transition_seen=transition_seen,
        learned_transition_source_count=transition_count,
        explanation_admissible=hard_pass,
    )
