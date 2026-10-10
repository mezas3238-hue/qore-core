"""Pre-strategy decision sovereignty for QORE Capitalizer V2.

Cognition may only pass a candidate to the frozen source-strategy layer, wait for more causal
evidence, or abstain/kill the current thesis. It cannot emit EXECUTE before source closure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_adversarial_reasoning_v2 import (
    CapitalizerAdversarialAssessment,
    CapitalizerAdversarialVerdict,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerAttentionState,
    CapitalizerCognitivePressure,
    CapitalizerHypothesisStage,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
    CapitalizerMetacognitiveAssessment,
)
from qore.infrastructure.trader_lab.capitalizer_opportunity_competition import (
    CapitalizerOpportunityCompetitionState,
)


class CapitalizerCognitiveGateDecision(StrEnum):
    PASS_TO_STRATEGY = "PASS_TO_STRATEGY"
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveGateFacts:
    symbol: str
    attention: CapitalizerAttentionState
    hypothesis_stage: CapitalizerHypothesisStage
    metacognition: CapitalizerMetacognitiveAssessment
    adversarial: CapitalizerAdversarialAssessment
    cognitive_pressure: CapitalizerCognitivePressure


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveGateAssessment:
    symbol: str
    decision: CapitalizerCognitiveGateDecision
    reasons: tuple[str, ...]
    strategy_may_evaluate: bool
    executes_trade: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.executes_trade:
            raise ValueError("pre-strategy cognitive gate cannot execute trades")
        if self.grants_capital_authority:
            raise ValueError("pre-strategy cognitive gate cannot grant capital authority")
        if self.strategy_may_evaluate != (
            self.decision is CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY
        ):
            raise ValueError("strategy_may_evaluate must match PASS_TO_STRATEGY")


def assess_cognitive_gate(
    *,
    facts: CapitalizerCognitiveGateFacts,
    competition: CapitalizerOpportunityCompetitionState,
) -> CapitalizerCognitiveGateAssessment:
    """Apply fail-closed cognitive sovereignty before strategy-source evaluation."""

    if competition.available_slots <= 0:
        return CapitalizerCognitiveGateAssessment(
            symbol=facts.symbol,
            decision=CapitalizerCognitiveGateDecision.ABSTAIN,
            reasons=("SESSION_EXECUTION_BUDGET_EXHAUSTED",),
            strategy_may_evaluate=False,
        )

    if facts.cognitive_pressure in {
        CapitalizerCognitivePressure.STOP_SESSION,
        CapitalizerCognitivePressure.STOP_DAY,
    }:
        return CapitalizerCognitiveGateAssessment(
            symbol=facts.symbol,
            decision=CapitalizerCognitiveGateDecision.ABSTAIN,
            reasons=(f"COGNITIVE_PRESSURE_{facts.cognitive_pressure.value}",),
            strategy_may_evaluate=False,
        )

    if facts.adversarial.verdict is CapitalizerAdversarialVerdict.FALSIFIED:
        return CapitalizerCognitiveGateAssessment(
            symbol=facts.symbol,
            decision=CapitalizerCognitiveGateDecision.ABSTAIN,
            reasons=("ADVERSARIAL_FALSIFIED", *facts.adversarial.hard_findings),
            strategy_may_evaluate=False,
        )

    if facts.metacognition.readiness is CapitalizerEpistemicReadiness.CONFLICTED:
        return CapitalizerCognitiveGateAssessment(
            symbol=facts.symbol,
            decision=CapitalizerCognitiveGateDecision.ABSTAIN,
            reasons=("METACOGNITION_CONFLICTED",),
            strategy_may_evaluate=False,
        )

    wait_reasons: list[str] = []
    if facts.attention is not CapitalizerAttentionState.DECISION:
        wait_reasons.append("ATTENTION_NOT_DECISION")
    if facts.hypothesis_stage not in {
        CapitalizerHypothesisStage.CONFIRMED,
        CapitalizerHypothesisStage.EXECUTABLE,
    }:
        wait_reasons.append("HYPOTHESIS_NOT_DECISION_READY")
    if facts.metacognition.readiness is not CapitalizerEpistemicReadiness.WELL_SUPPORTED:
        wait_reasons.append("EPISTEMIC_READINESS_NOT_WELL_SUPPORTED")
    if facts.adversarial.verdict is CapitalizerAdversarialVerdict.CHALLENGED:
        wait_reasons.append("ADVERSARIAL_CHALLENGED")
    if facts.cognitive_pressure is CapitalizerCognitivePressure.RECOVERY_OBSERVATION:
        wait_reasons.append("RECOVERY_OBSERVATION_REQUIRES_NEW_EVIDENCE")

    eligible_symbols = {item.symbol for item in competition.eligible_candidates}
    if facts.symbol not in eligible_symbols:
        wait_reasons.append("NOT_ELIGIBLE_FOR_OPPORTUNITY_ARBITRATION")

    if (
        facts.cognitive_pressure is CapitalizerCognitivePressure.HIGH_SELECTIVITY
        and facts.metacognition.readiness is not CapitalizerEpistemicReadiness.WELL_SUPPORTED
    ):
        wait_reasons.append("HIGH_SELECTIVITY_REQUIRES_WELL_SUPPORTED_EVIDENCE")

    if wait_reasons:
        return CapitalizerCognitiveGateAssessment(
            symbol=facts.symbol,
            decision=CapitalizerCognitiveGateDecision.WAIT,
            reasons=tuple(dict.fromkeys(wait_reasons)),
            strategy_may_evaluate=False,
        )

    return CapitalizerCognitiveGateAssessment(
        symbol=facts.symbol,
        decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
        reasons=(
            "COGNITIVE_STATE_PASSED",
            "METACOGNITION_WELL_SUPPORTED",
            "ADVERSARIAL_CHECK_PASSED",
        ),
        strategy_may_evaluate=True,
    )
