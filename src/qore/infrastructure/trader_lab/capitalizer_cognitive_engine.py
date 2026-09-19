"""Top-level deterministic cognitive orchestration for QORE Capitalizer V1."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizationPosture,
    CapitalizerDecision,
    EvidenceStrength,
)
from qore.infrastructure.trader_lab.capitalizer_governor import (
    CapitalizerGovernorRecommendation,
    CapitalizerPortfolioState,
    recommend_capitalization_posture,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_reasoning import (
    CapitalizerReasoningDecision,
    reason_capitalizer_opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerSituationModel,
)


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveEvaluation:
    """One complete fast-brain evaluation with immutable ledger output."""

    final_decision: CapitalizerDecision
    reasoning: CapitalizerReasoningDecision
    governor: CapitalizerGovernorRecommendation
    ledger_after: CapitalizerSessionLedger
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_capital_authority:
            raise ValueError("Capitalizer cognition cannot grant capital authority")


def evaluate_capitalizer(
    *,
    situation: CapitalizerSituationModel,
    ledger: CapitalizerSessionLedger,
    loss_memory: CapitalizerLossMemory,
    portfolio_state: CapitalizerPortfolioState,
) -> CapitalizerCognitiveEvaluation:
    """Evaluate a scalp opportunity while preserving QORE RISK sovereignty."""

    governor = recommend_capitalization_posture(portfolio_state)
    reasoning = reason_capitalizer_opportunity(
        situation=situation,
        ledger=ledger,
        loss_memory=loss_memory,
    )

    final = reasoning
    if governor.posture in {
        CapitalizationPosture.STOP_SESSION,
        CapitalizationPosture.STOP_DAY,
    }:
        final = CapitalizerReasoningDecision(
            decision=CapitalizerDecision.ABSTAIN,
            hypothesis_id=situation.hypothesis_id,
            source_event_id=situation.source_event_id,
            reasons=(f"GOVERNOR_{governor.posture.value}",),
            adversarial_findings=reasoning.adversarial_findings,
        )
    elif (
        governor.posture is CapitalizationPosture.HIGH_SELECTIVITY
        and reasoning.decision is CapitalizerDecision.EXECUTE
        and situation.evidence_strength is not EvidenceStrength.HIGH
    ):
        final = CapitalizerReasoningDecision(
            decision=CapitalizerDecision.WAIT,
            hypothesis_id=situation.hypothesis_id,
            source_event_id=situation.source_event_id,
            reasons=("HIGH_SELECTIVITY_REQUIRES_HIGH_EVIDENCE",),
            adversarial_findings=reasoning.adversarial_findings,
        )

    ledger_after = ledger.record_decision(
        decision=final.decision,
        hypothesis_id=final.hypothesis_id,
        source_event_id=final.source_event_id,
    )
    return CapitalizerCognitiveEvaluation(
        final_decision=final.decision,
        reasoning=final,
        governor=governor,
        ledger_after=ledger_after,
    )
