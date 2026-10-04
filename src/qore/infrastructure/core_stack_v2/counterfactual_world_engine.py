"""MC-18 bounded Counterfactual World Engine.

Generates alternative worlds from source-time evidence only. The worlds are
probabilistic descriptive hypotheses, never deterministic forecasts or trading
instructions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)


class CounterfactualWorldKind(StrEnum):
    LIQUIDITY_HOLDS = "LIQUIDITY_HOLDS"
    LIQUIDITY_FAILS = "LIQUIDITY_FAILS"
    VOLATILITY_RISES = "VOLATILITY_RISES"
    LEADER_REVERSES = "LEADER_REVERSES"
    RELATIONSHIP_BREAKS = "RELATIONSHIP_BREAKS"
    CONTINUATION_PULLBACK = "CONTINUATION_PULLBACK"
    FAILED_AUCTION_REVERSAL = "FAILED_AUCTION_REVERSAL"
    COMPRESSION_PERSISTS = "COMPRESSION_PERSISTS"
    UNKNOWN_SHOCK = "UNKNOWN_SHOCK"


@dataclass(frozen=True, slots=True)
class CounterfactualWorldPath:
    kind: CounterfactualWorldKind
    probability_bps: int
    thesis_robustness_bps: int
    survivability_bps: int
    tail_risk_bps: int
    failure_probability_bps: int
    evidence_refs: tuple[str, ...]
    source_only: bool = True
    future_market_used: bool = False
    outcome_used: bool = False
    deterministic_future_claim: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "probability_bps",
            "thesis_robustness_bps",
            "survivability_bps",
            "tail_risk_bps",
            "failure_probability_bps",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be int within 0..10000")
        if (
            not self.evidence_refs
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("counterfactual evidence refs must be canonical")
        if (
            not self.source_only
            or self.future_market_used
            or self.outcome_used
            or self.deterministic_future_claim
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
        ):
            raise ValueError("counterfactual world violates research governance")


@dataclass(frozen=True, slots=True)
class CounterfactualWorldDistribution:
    observation_id: str
    paths: tuple[CounterfactualWorldPath, ...]
    source_only: bool = True
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("counterfactual distribution needs observation identity")
        if not self.paths:
            raise ValueError("counterfactual distribution requires paths")
        if self.paths != tuple(sorted(self.paths, key=lambda item: item.kind.value)):
            raise ValueError("counterfactual paths must be canonical")
        if sum(item.probability_bps for item in self.paths) != 10_000:
            raise ValueError("counterfactual probabilities must sum to 10000")
        if CounterfactualWorldKind.UNKNOWN_SHOCK not in {
            item.kind for item in self.paths
        }:
            raise ValueError("counterfactual world must preserve unknown shock")
        if not self.source_only or self.productive_authority:
            raise ValueError("counterfactual distribution is research-only")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["paths"] = tuple(
            {
                **asdict(item),
                "kind": item.kind.value,
            }
            for item in self.paths
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def _mean(*values: int) -> int:
    return sum(values) // len(values)


def _normalize(scores: dict[CounterfactualWorldKind, int]) -> dict[CounterfactualWorldKind, int]:
    safe = {key: max(1, value) for key, value in scores.items()}
    total = sum(safe.values())
    provisional = {
        key: value * 10_000 // total for key, value in safe.items()
    }
    remainder = 10_000 - sum(provisional.values())
    if remainder:
        ordered = sorted(
            provisional,
            key=lambda key: (safe[key], key.value),
            reverse=True,
        )
        for index in range(remainder):
            key = ordered[index % len(ordered)]
            provisional[key] += 1
    return provisional


def build_counterfactual_world_distribution(
    observation: SharedOpportunitySourceObservation,
) -> CounterfactualWorldDistribution:
    support = _mean(
        observation.acceptance_bps,
        observation.leader_confirmation_bps,
        observation.momentum_persistence_bps,
    )
    fragility = _mean(
        observation.structural_fragility_bps,
        observation.leader_divergence_bps,
        observation.regime_transition_bps,
    )
    uncertainty = _mean(
        10_000 - observation.data_integrity_bps,
        observation.anomaly_bps,
        observation.regime_transition_bps,
    )

    raw_scores = {
        CounterfactualWorldKind.LIQUIDITY_HOLDS: _mean(
            10_000 - observation.liquidity_vacuum_bps,
            observation.acceptance_bps,
        ),
        CounterfactualWorldKind.LIQUIDITY_FAILS: _mean(
            observation.liquidity_vacuum_bps,
            observation.structural_fragility_bps,
        ),
        CounterfactualWorldKind.VOLATILITY_RISES: _mean(
            observation.anomaly_bps,
            observation.regime_transition_bps,
            observation.displacement_bps,
        ),
        CounterfactualWorldKind.LEADER_REVERSES: _mean(
            observation.leader_divergence_bps,
            observation.momentum_decay_bps,
        ),
        CounterfactualWorldKind.RELATIONSHIP_BREAKS: _mean(
            observation.leader_divergence_bps,
            observation.regime_transition_bps,
        ),
        CounterfactualWorldKind.CONTINUATION_PULLBACK: _mean(
            observation.momentum_persistence_bps,
            observation.acceptance_bps,
            observation.compression_bps,
        ),
        CounterfactualWorldKind.FAILED_AUCTION_REVERSAL: _mean(
            observation.failed_auction_bps,
            observation.momentum_decay_bps,
            observation.structural_fragility_bps,
        ),
        CounterfactualWorldKind.COMPRESSION_PERSISTS: _mean(
            observation.compression_bps,
            observation.liquidity_accumulation_bps,
        ),
        CounterfactualWorldKind.UNKNOWN_SHOCK: max(500, uncertainty),
    }
    probabilities = _normalize(raw_scores)
    refs = tuple(sorted(observation.provenance_refs))

    paths = []
    for kind in CounterfactualWorldKind:
        if kind in {
            CounterfactualWorldKind.LIQUIDITY_FAILS,
            CounterfactualWorldKind.LEADER_REVERSES,
            CounterfactualWorldKind.RELATIONSHIP_BREAKS,
            CounterfactualWorldKind.FAILED_AUCTION_REVERSAL,
            CounterfactualWorldKind.UNKNOWN_SHOCK,
        }:
            failure = min(10_000, _mean(fragility, raw_scores[kind]))
            robustness = max(0, 10_000 - failure)
        else:
            robustness = min(10_000, _mean(support, raw_scores[kind]))
            failure = max(0, 10_000 - robustness)
        tail = min(
            10_000,
            _mean(
                observation.anomaly_bps,
                observation.liquidity_vacuum_bps,
                failure,
            ),
        )
        survivability = max(0, 10_000 - _mean(failure, uncertainty))
        paths.append(
            CounterfactualWorldPath(
                kind=kind,
                probability_bps=probabilities[kind],
                thesis_robustness_bps=robustness,
                survivability_bps=survivability,
                tail_risk_bps=tail,
                failure_probability_bps=failure,
                evidence_refs=refs,
            )
        )

    return CounterfactualWorldDistribution(
        observation_id=observation.observation_id,
        paths=tuple(sorted(paths, key=lambda item: item.kind.value)),
    )
