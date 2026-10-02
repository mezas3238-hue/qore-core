"""Dynamic causal-graph intelligence for Shared Core.

The graph represents *relations between market concepts*, not trade rules.
Edges are beliefs that one concept causally supports or suppresses another.
They are updated only from causal, point-in-time evidence and may be weakened
or falsified by contradictory observations.

This layer is generic, trader-agnostic and authority-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import exp, log


class CausalConcept(StrEnum):
    COMPRESSION = "COMPRESSION"
    LIQUIDITY_ACCUMULATION = "LIQUIDITY_ACCUMULATION"
    FAILED_AUCTION = "FAILED_AUCTION"
    DISPLACEMENT = "DISPLACEMENT"
    ACCEPTANCE = "ACCEPTANCE"
    ABSORPTION = "ABSORPTION"
    LEADER_CONFIRMATION = "LEADER_CONFIRMATION"
    LEADER_DIVERGENCE = "LEADER_DIVERGENCE"
    MOMENTUM_PERSISTENCE = "MOMENTUM_PERSISTENCE"
    MOMENTUM_DECAY = "MOMENTUM_DECAY"
    STRUCTURAL_FRAGILITY = "STRUCTURAL_FRAGILITY"
    STRUCTURAL_FAILURE = "STRUCTURAL_FAILURE"
    LIQUIDITY_VACUUM = "LIQUIDITY_VACUUM"
    EXPANSION_READINESS = "EXPANSION_READINESS"
    CONTINUATION = "CONTINUATION"
    REVERSAL = "REVERSAL"
    REGIME_TRANSITION = "REGIME_TRANSITION"
    ANOMALY = "ANOMALY"


@dataclass(frozen=True, slots=True)
class CausalEdgeEvidence:
    source: CausalConcept
    target: CausalConcept
    as_of: datetime
    support_bps: int
    contradiction_bps: int
    integrity_bps: int
    independence_group: str

    def __post_init__(self) -> None:
        if self.source is self.target:
            raise ValueError("causal edge cannot self-reference")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if not self.independence_group:
            raise ValueError("independence_group must be non-empty")
        for name in ("support_bps", "contradiction_bps", "integrity_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.support_bps == 0 and self.contradiction_bps == 0:
            raise ValueError("edge evidence must contain information")


@dataclass(frozen=True, slots=True)
class CausalEdgeBelief:
    source: CausalConcept
    target: CausalConcept
    probability_bps: int
    confidence_bps: int
    evidence_count: int
    independent_group_count: int
    last_evidence_at: datetime

    def __post_init__(self) -> None:
        for name in ("probability_bps", "confidence_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.evidence_count < 1 or self.independent_group_count < 1:
            raise ValueError("causal edge belief must contain evidence")


@dataclass(frozen=True, slots=True)
class DynamicCausalGraph:
    as_of: datetime
    edges: tuple[CausalEdgeBelief, ...]
    graph_consistency_bps: int
    falsified_edges: tuple[tuple[CausalConcept, CausalConcept], ...]
    evidence_cutoff_at: datetime
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future graph evidence is forbidden")
        if not 0 <= self.graph_consistency_bps <= 10_000:
            raise ValueError("graph consistency must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.stop_authority
            or self.target_authority
            or self.execution_authority
        ):
            raise ValueError("causal graph cannot carry trading authority")

    def edge_probability_bps(
        self,
        source: CausalConcept,
        target: CausalConcept,
    ) -> int:
        for edge in self.edges:
            if edge.source is source and edge.target is target:
                return edge.probability_bps
        return 5_000


@dataclass(frozen=True, slots=True)
class CausalGraphPolicy:
    prior_probability_bps: int = 5_000
    correlation_discount_bps: int = 6_500
    evidence_half_life_seconds: int = 900
    maximum_evidence_age_seconds: int = 3_600
    falsification_probability_bps: int = 2_500
    minimum_falsification_confidence_bps: int = 4_000

    def __post_init__(self) -> None:
        if not 1 <= self.prior_probability_bps <= 9_999:
            raise ValueError("prior probability must be within 1..9999")
        if self.evidence_half_life_seconds <= 0:
            raise ValueError("half life must be positive")
        if self.maximum_evidence_age_seconds <= 0:
            raise ValueError("maximum evidence age must be positive")
        for name in (
            "correlation_discount_bps",
            "falsification_probability_bps",
            "minimum_falsification_confidence_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


def _logit(probability: float) -> float:
    bounded = min(0.9999, max(0.0001, probability))
    return log(bounded / (1.0 - bounded))


def _logistic(value: float) -> float:
    if value >= 0:
        term = exp(-value)
        return 1.0 / (1.0 + term)
    term = exp(value)
    return term / (1.0 + term)


def update_causal_graph(
    *,
    as_of: datetime,
    evidence: tuple[CausalEdgeEvidence, ...],
    policy: CausalGraphPolicy | None = None,
) -> DynamicCausalGraph:
    """Update causal-edge beliefs from point-in-time evidence."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    effective = policy or CausalGraphPolicy()

    grouped: dict[
        tuple[CausalConcept, CausalConcept],
        list[tuple[CausalEdgeEvidence, int]],
    ] = {}
    for item in evidence:
        if item.as_of > as_of:
            raise ValueError("future causal evidence is forbidden")
        age_seconds = int((as_of - item.as_of).total_seconds())
        if age_seconds > effective.maximum_evidence_age_seconds:
            continue
        grouped.setdefault((item.source, item.target), []).append(
            (item, age_seconds)
        )

    beliefs: list[CausalEdgeBelief] = []
    falsified: list[tuple[CausalConcept, CausalConcept]] = []
    consistency_parts: list[int] = []

    for (source, target), items in sorted(
        grouped.items(),
        key=lambda pair: (pair[0][0].value, pair[0][1].value),
    ):
        log_odds = _logit(effective.prior_probability_bps / 10_000.0)
        group_seen: dict[str, int] = {}
        weighted_information = 0.0

        for item, age_seconds in sorted(
            items,
            key=lambda pair: (pair[0].as_of, pair[0].independence_group),
        ):
            repeats = group_seen.get(item.independence_group, 0)
            group_seen[item.independence_group] = repeats + 1
            correlation_weight = (
                effective.correlation_discount_bps / 10_000.0
            ) ** repeats
            decay_weight = 0.5 ** (
                age_seconds / effective.evidence_half_life_seconds
            )
            integrity_weight = item.integrity_bps / 10_000.0
            support = item.support_bps + 250.0
            contradiction = item.contradiction_bps + 250.0
            information = log(support / contradiction)
            weight = correlation_weight * decay_weight * integrity_weight
            log_odds += information * weight
            weighted_information += abs(information) * weight

        probability_bps = int(round(_logistic(log_odds) * 10_000))
        diversity = min(1.0, len(group_seen) / 4.0)
        information_strength = min(1.0, weighted_information / 4.0)
        confidence_bps = int(round(10_000 * diversity * information_strength))
        belief = CausalEdgeBelief(
            source=source,
            target=target,
            probability_bps=probability_bps,
            confidence_bps=confidence_bps,
            evidence_count=len(items),
            independent_group_count=len(group_seen),
            last_evidence_at=max(item.as_of for item, _ in items),
        )
        beliefs.append(belief)
        consistency_parts.append(
            int(
                round(
                    abs(probability_bps - 5_000)
                    * confidence_bps
                    / 5_000
                )
            )
        )
        if (
            probability_bps <= effective.falsification_probability_bps
            and confidence_bps >= effective.minimum_falsification_confidence_bps
        ):
            falsified.append((source, target))

    graph_consistency = (
        0
        if not consistency_parts
        else min(10_000, sum(consistency_parts) // len(consistency_parts))
    )
    cutoff = max((item.as_of for item in evidence), default=as_of)
    return DynamicCausalGraph(
        as_of=as_of,
        edges=tuple(beliefs),
        graph_consistency_bps=graph_consistency,
        falsified_edges=tuple(falsified),
        evidence_cutoff_at=min(cutoff, as_of),
    )
