"""Deterministic cognitive explanations for QORE Capitalizer V2.

The explanation layer converts one Master Cognitive Frame candidate evaluation into an immutable
audit record. It does not generate free-form rationale, mutate rules, select trades or grant
capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_cognitive_audit import (
    CapitalizerCognitiveAuditRecord,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame import (
    CapitalizerCandidateCognitiveEvaluation,
    CapitalizerMasterCognitiveFrame,
)


@dataclass(frozen=True, slots=True)
class CapitalizerCognitiveExplanation:
    symbol: str
    why_tokens: tuple[str, ...]
    uncertainty_tokens: tuple[str, ...]
    audit_record: CapitalizerCognitiveAuditRecord
    free_form_reasoning_used: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.free_form_reasoning_used:
            raise ValueError("cognitive explanation must remain deterministic/auditable")
        if self.grants_capital_authority:
            raise ValueError("cognitive explanation cannot grant capital authority")
        if not self.why_tokens:
            raise ValueError("cognitive explanation requires explicit WHY tokens")


def _candidate(
    frame: CapitalizerMasterCognitiveFrame,
    symbol: str,
) -> CapitalizerCandidateCognitiveEvaluation:
    matches = tuple(
        item for item in frame.candidate_evaluations if item.symbol == symbol.upper()
    )
    if len(matches) != 1:
        raise KeyError(f"candidate evaluation not uniquely available: {symbol.upper()}")
    return matches[0]


def explain_candidate(
    *,
    frame: CapitalizerMasterCognitiveFrame,
    symbol: str,
    audit_namespace: str = "CAPITALIZER_COGNITIVE_V2",
) -> CapitalizerCognitiveExplanation:
    """Explain one pre-strategy candidate using only state already inside the frame."""

    evaluation = _candidate(frame, symbol)
    market = next(item for item in frame.world.markets if item.symbol == evaluation.symbol)

    hypothesis_id = market.hypothesis_id
    source_event_id = market.source_event_id
    hypothesis_stage = market.hypothesis_stage
    if hypothesis_id is None or source_event_id is None or hypothesis_stage is None:
        raise ValueError("candidate explanation requires complete hypothesis identity")
    if not audit_namespace:
        raise ValueError("audit_namespace must be non-empty")

    why = tuple(
        dict.fromkeys(
            (
                f"ATTENTION:{market.attention.value}",
                f"KNOWLEDGE:{market.knowledge.value}",
                f"EPISTEMIC:{evaluation.metacognition.readiness.value}",
                f"ADVERSARIAL:{evaluation.adversarial.verdict.value}",
                f"COGNITIVE_GATE:{evaluation.gate.decision.value}",
                *evaluation.gate.reasons,
                *evaluation.metacognition.reasons,
            )
        )
    )
    uncertainty = tuple(
        dict.fromkeys(
            (
                *evaluation.metacognition.reasons,
                *evaluation.adversarial.challenge_findings,
                *(f"CONTRADICTION:{item}" for item in market.contradictions),
            )
        )
    )
    adversarial_findings = tuple(
        dict.fromkeys(
            (
                *evaluation.adversarial.hard_findings,
                *evaluation.adversarial.challenge_findings,
            )
        )
    )
    observations = tuple(
        dict.fromkeys(
            (
                *evaluation.observation_tokens,
                f"SESSION:{frame.world.current_session.value}",
                f"ATTENTION:{market.attention.value}",
                f"KNOWLEDGE:{market.knowledge.value}",
                (
                    f"REGIME:{evaluation.regime_family_id}"
                    if evaluation.regime_family_id is not None
                    else "REGIME:UNRESOLVED"
                ),
            )
        )
    )

    audit_id = (
        f"{audit_namespace}:{evaluation.observed_at.isoformat()}:"
        f"{evaluation.symbol}:{hypothesis_id}"
    )
    record = CapitalizerCognitiveAuditRecord(
        audit_id=audit_id,
        observed_at=evaluation.observed_at,
        session=frame.world.current_session,
        symbol=evaluation.symbol,
        attention=market.attention,
        knowledge=market.knowledge,
        hypothesis_stage=hypothesis_stage,
        hypothesis_id=hypothesis_id,
        source_event_id=source_event_id,
        regime_family_id=evaluation.regime_family_id,
        observations=observations,
        contradictions=market.contradictions,
        adversarial_findings=adversarial_findings,
        decision=None,
        reasons=evaluation.gate.reasons,
        cognitive_gate_decision=evaluation.gate.decision,
        selected_for_slot=False,
    )

    return CapitalizerCognitiveExplanation(
        symbol=evaluation.symbol,
        why_tokens=why,
        uncertainty_tokens=uncertainty,
        audit_record=record,
    )


def explain_all_candidates(
    frame: CapitalizerMasterCognitiveFrame,
) -> tuple[CapitalizerCognitiveExplanation, ...]:
    return tuple(
        explain_candidate(frame=frame, symbol=item.symbol)
        for item in frame.candidate_evaluations
    )
