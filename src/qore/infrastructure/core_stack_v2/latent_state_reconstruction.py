"""MC-06 probabilistic latent-state reconstruction from source-time effects."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)


class LatentMarketState(StrEnum):
    HIDDEN_LIQUIDITY_PRESSURE = "HIDDEN_LIQUIDITY_PRESSURE"
    ABSORPTION = "ABSORPTION"
    DIRECTIONAL_PRESSURE = "DIRECTIONAL_PRESSURE"
    INVENTORY_IMBALANCE = "INVENTORY_IMBALANCE"
    LIQUIDITY_VULNERABILITY = "LIQUIDITY_VULNERABILITY"
    MARKET_STRESS = "MARKET_STRESS"
    CROWDING_REFLEXIVITY = "CROWDING_REFLEXIVITY"
    INSTITUTIONAL_PARTICIPATION_LIKE = "INSTITUTIONAL_PARTICIPATION_LIKE"


@dataclass(frozen=True, slots=True)
class LatentStateEstimate:
    state: LatentMarketState
    weight_bps: int
    uncertainty_bps: int
    evidence_refs: tuple[str, ...]
    actor_identity_claimed: bool = False

    def __post_init__(self) -> None:
        for name in ("weight_bps", "uncertainty_bps"):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("latent-state evidence refs must be canonical")
        if self.actor_identity_claimed:
            raise ValueError("latent-state reconstruction cannot claim actor identity")


@dataclass(frozen=True, slots=True)
class LatentStateBelief:
    observation_id: str
    estimates: tuple[LatentStateEstimate, ...]
    source_only: bool = True
    future_market_used: bool = False
    outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("latent belief requires observation identity")
        if self.estimates != tuple(
            sorted(self.estimates, key=lambda item: item.state.value)
        ):
            raise ValueError("latent-state estimates must be canonical")
        if {item.state for item in self.estimates} != set(LatentMarketState):
            raise ValueError("latent belief requires every declared state")
        if sum(item.weight_bps for item in self.estimates) != 10_000:
            raise ValueError("latent-state weights must sum to 10000")
        if (
            not self.source_only
            or self.future_market_used
            or self.outcome_used
            or self.productive_authority
        ):
            raise ValueError("latent-state belief must remain source-only research")

    def fingerprint(self) -> str:
        payload = {
            "observation_id": self.observation_id,
            "estimates": tuple(
                {
                    **asdict(item),
                    "state": item.state.value,
                }
                for item in self.estimates
            ),
            "source_only": self.source_only,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def _mean(*values: int) -> int:
    return sum(values) // len(values)


def _normalize(
    scores: dict[LatentMarketState, int],
) -> dict[LatentMarketState, int]:
    safe = {key: max(1, value) for key, value in scores.items()}
    total = sum(safe.values())
    weights = {
        key: value * 10_000 // total
        for key, value in safe.items()
    }
    remainder = 10_000 - sum(weights.values())
    ordered = sorted(
        weights,
        key=lambda key: (safe[key], key.value),
        reverse=True,
    )
    for index in range(remainder):
        weights[ordered[index % len(ordered)]] += 1
    return weights


def reconstruct_latent_state(
    observation: SharedOpportunitySourceObservation,
) -> LatentStateBelief:
    scores = {
        LatentMarketState.HIDDEN_LIQUIDITY_PRESSURE: _mean(
            observation.liquidity_accumulation_bps,
            observation.absorption_bps,
            observation.compression_bps,
        ),
        LatentMarketState.ABSORPTION: _mean(
            observation.absorption_bps,
            observation.acceptance_bps,
            10_000 - observation.failed_auction_bps,
        ),
        LatentMarketState.DIRECTIONAL_PRESSURE: _mean(
            observation.displacement_bps,
            observation.momentum_persistence_bps,
            observation.leader_confirmation_bps,
        ),
        LatentMarketState.INVENTORY_IMBALANCE: _mean(
            observation.displacement_bps,
            observation.liquidity_accumulation_bps,
            observation.momentum_decay_bps,
        ),
        LatentMarketState.LIQUIDITY_VULNERABILITY: _mean(
            observation.liquidity_vacuum_bps,
            observation.structural_fragility_bps,
            observation.failed_auction_bps,
        ),
        LatentMarketState.MARKET_STRESS: _mean(
            observation.anomaly_bps,
            observation.regime_transition_bps,
            observation.structural_fragility_bps,
            observation.leader_divergence_bps,
        ),
        LatentMarketState.CROWDING_REFLEXIVITY: _mean(
            observation.momentum_persistence_bps,
            observation.leader_confirmation_bps,
            observation.regime_transition_bps,
        ),
        LatentMarketState.INSTITUTIONAL_PARTICIPATION_LIKE: _mean(
            observation.absorption_bps,
            observation.displacement_bps,
            observation.acceptance_bps,
            observation.liquidity_accumulation_bps,
        ),
    }
    weights = _normalize(scores)
    base_uncertainty = _mean(
        10_000 - observation.data_integrity_bps,
        observation.anomaly_bps,
        observation.regime_transition_bps,
        observation.leader_divergence_bps,
    )
    refs = tuple(sorted(observation.provenance_refs))
    estimates = tuple(
        sorted(
            (
                LatentStateEstimate(
                    state=state,
                    weight_bps=weights[state],
                    uncertainty_bps=min(
                        10_000,
                        _mean(base_uncertainty, 10_000 - scores[state]),
                    ),
                    evidence_refs=refs,
                )
                for state in LatentMarketState
            ),
            key=lambda item: item.state.value,
        )
    )
    return LatentStateBelief(
        observation_id=observation.observation_id,
        estimates=estimates,
    )
