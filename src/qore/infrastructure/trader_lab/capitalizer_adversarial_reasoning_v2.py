"""Counterfactual/adversarial reasoning for QORE Capitalizer V2.

The adversarial brain attempts to falsify a candidate before strategy-source logic may act.
It uses only decision-time cognitive facts and cannot grant execution/capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_cross_market_causality import (
    CapitalizerCrossMarketCausalGraph,
    CapitalizerCrossMarketRelation,
)
from qore.infrastructure.trader_lab.capitalizer_global_world_model import (
    CapitalizerGlobalWorldModel,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
    CapitalizerMetacognitiveAssessment,
)
from qore.infrastructure.trader_lab.capitalizer_perception_integrity import (
    CapitalizerPerceptionStatus,
)
from qore.infrastructure.trader_lab.capitalizer_regime_intelligence import (
    CapitalizerRegimeResolution,
)


class CapitalizerAdversarialVerdict(StrEnum):
    PASSED = "PASSED"
    CHALLENGED = "CHALLENGED"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True, slots=True)
class CapitalizerAdversarialCandidateFacts:
    symbol: str
    hypothesis_id: str
    source_event_id: str
    failure_state_fingerprint: str | None
    metacognition: CapitalizerMetacognitiveAssessment
    perception_status: CapitalizerPerceptionStatus
    regime_resolution: CapitalizerRegimeResolution
    destination_context_known: bool
    destination_available: bool
    event_is_fresh: bool
    genuinely_new_causal_event: bool
    contradictions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapitalizerAdversarialAssessment:
    symbol: str
    verdict: CapitalizerAdversarialVerdict
    hard_findings: tuple[str, ...]
    challenge_findings: tuple[str, ...]
    counterfactual_question_tokens: tuple[str, ...]
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_entry_authority:
            raise ValueError("adversarial reasoning cannot grant entry authority")
        if self.grants_capital_authority:
            raise ValueError("adversarial reasoning cannot grant capital authority")


def assess_adversarial_candidate(
    *,
    facts: CapitalizerAdversarialCandidateFacts,
    world: CapitalizerGlobalWorldModel,
    cross_market_graph: CapitalizerCrossMarketCausalGraph,
) -> CapitalizerAdversarialAssessment:
    """Try to falsify one cognitive candidate before source-strategy reasoning."""

    if facts.symbol not in {item.symbol for item in world.markets}:
        raise ValueError("adversarial candidate symbol absent from Global World Model")
    if cross_market_graph.observed_at > world.observed_at:
        raise ValueError("future cross-market graph cannot enter adversarial reasoning")

    hard: list[str] = []
    challenge: list[str] = []

    if facts.perception_status is CapitalizerPerceptionStatus.BAD:
        hard.append("PERCEPTION_BAD")
    if facts.regime_resolution is CapitalizerRegimeResolution.CONFLICTED:
        hard.append("REGIME_CONFLICTED")
    if facts.metacognition.readiness is CapitalizerEpistemicReadiness.CONFLICTED:
        hard.append("METACOGNITION_CONFLICTED")
    if facts.contradictions:
        hard.extend(f"CONTRADICTION:{item}" for item in facts.contradictions)
    if not facts.event_is_fresh:
        hard.append("EVENT_NOT_FRESH")
    if not facts.destination_available and facts.destination_context_known:
        hard.append("DESTINATION_UNAVAILABLE")
    if (
        facts.failure_state_fingerprint is not None
        and facts.failure_state_fingerprint in world.unresolved_failure_fingerprints
        and not facts.genuinely_new_causal_event
    ):
        hard.append("UNRESOLVED_FAILURE_REPEAT_WITHOUT_NEW_CAUSE")

    if facts.perception_status is CapitalizerPerceptionStatus.DEGRADED:
        challenge.append("PERCEPTION_DEGRADED")
    if facts.regime_resolution is CapitalizerRegimeResolution.UNRESOLVED:
        challenge.append("REGIME_UNRESOLVED")
    if facts.metacognition.readiness in {
        CapitalizerEpistemicReadiness.UNRESOLVED,
        CapitalizerEpistemicReadiness.CONDITIONALLY_SUPPORTED,
    }:
        challenge.append("METACOGNITION_NOT_WELL_SUPPORTED")
    if not facts.destination_context_known:
        challenge.append("DESTINATION_CONTEXT_UNKNOWN")

    for position in world.open_positions:
        if position.symbol == facts.symbol:
            hard.append("SYMBOL_ALREADY_HAS_OPEN_POSITION")
            continue
        edge = cross_market_graph.relation_for(facts.symbol, position.symbol)
        if edge is None:
            continue
        if edge.relation in {
            CapitalizerCrossMarketRelation.MUTUALLY_INVALIDATING,
            CapitalizerCrossMarketRelation.REDUNDANT,
        }:
            hard.append(f"CROSS_MARKET_{edge.relation.value}:{position.symbol}")
        elif edge.relation in {
            CapitalizerCrossMarketRelation.CONTRADICTORY,
            CapitalizerCrossMarketRelation.SHARED_CAUSE,
            CapitalizerCrossMarketRelation.LEADER_FOLLOWER,
        }:
            challenge.append(f"CROSS_MARKET_{edge.relation.value}:{position.symbol}")

    questions = (
        "WHAT_OBSERVATION_WOULD_INVALIDATE_THIS_THESIS",
        "IS_DESTINATION_STILL_AVAILABLE",
        "IS_THIS_A_NEW_CAUSAL_EVENT",
        "IS_ACTIVE_PORTFOLIO_RISK_CAUSALLY_INDEPENDENT",
        "IS_EVIDENCE_COMPLETE_AT_DECISION_TIME",
    )

    if hard:
        verdict = CapitalizerAdversarialVerdict.FALSIFIED
    elif challenge:
        verdict = CapitalizerAdversarialVerdict.CHALLENGED
    else:
        verdict = CapitalizerAdversarialVerdict.PASSED

    return CapitalizerAdversarialAssessment(
        symbol=facts.symbol,
        verdict=verdict,
        hard_findings=tuple(dict.fromkeys(hard)),
        challenge_findings=tuple(dict.fromkeys(challenge)),
        counterfactual_question_tokens=questions,
    )
