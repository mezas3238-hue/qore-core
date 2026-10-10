"""Deterministic reasoning sovereignty for the QORE Capitalizer fast brain."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerDecision,
    EvidenceStrength,
    ExecutionQuality,
    MarketState,
    market_is_allowed,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerSituationModel,
)


@dataclass(frozen=True, slots=True)
class CapitalizerReasoningDecision:
    """Auditable fast-brain decision with no capital or broker authority."""

    decision: CapitalizerDecision
    hypothesis_id: str
    source_event_id: str
    reasons: tuple[str, ...]
    adversarial_findings: tuple[str, ...]


def _adversarial_findings(
    *,
    situation: CapitalizerSituationModel,
    loss_memory: CapitalizerLossMemory,
) -> tuple[str, ...]:
    findings: list[str] = []
    if situation.late_entry:
        findings.append("LATE_ENTRY")
    if not situation.destination_available:
        findings.append("DESTINATION_UNAVAILABLE")
    if situation.correlated_exposure_blocked:
        findings.append("CORRELATED_EXPOSURE_BLOCKED")
    if loss_memory.repeats_unresolved_failure(situation.failure_state_fingerprint):
        findings.append("UNRESOLVED_FAILURE_STATE_REPEAT")
    if situation.market_state is MarketState.CHAOS:
        findings.append("MARKET_STATE_CHAOS")
    findings.extend(f"CONTRADICTION:{item}" for item in situation.contradictions)
    return tuple(findings)


def reason_capitalizer_opportunity(
    *,
    situation: CapitalizerSituationModel,
    ledger: CapitalizerSessionLedger,
    loss_memory: CapitalizerLossMemory,
) -> CapitalizerReasoningDecision:
    """Return EXECUTE/WAIT/ABSTAIN using only causal decision-time state.

    ABSTAIN is sovereign: killed hypothesis/source identities cannot be resurrected.
    WAIT is reserved for states that may improve without inventing a new hypothesis.
    """

    if ledger.session is not situation.session:
        raise ValueError("session ledger must match situation session")

    reasons: list[str] = []
    adversarial = _adversarial_findings(situation=situation, loss_memory=loss_memory)

    if not market_is_allowed(session=situation.session, symbol=situation.symbol):
        reasons.append("MARKET_OUTSIDE_SESSION_UNIVERSE")
    if situation.hypothesis_id in ledger.killed_hypotheses:
        reasons.append("HYPOTHESIS_ALREADY_KILLED")
    if situation.source_event_id in ledger.killed_source_events:
        reasons.append("SOURCE_EVENT_ALREADY_KILLED")
    if ledger.execution_budget_remaining <= 0:
        reasons.append("SESSION_EXECUTION_BUDGET_EXHAUSTED")

    hard_adversarial = {
        "LATE_ENTRY",
        "DESTINATION_UNAVAILABLE",
        "UNRESOLVED_FAILURE_STATE_REPEAT",
        "MARKET_STATE_CHAOS",
    }
    if any(item in hard_adversarial or item.startswith("CONTRADICTION:") for item in adversarial):
        reasons.extend(adversarial)

    if reasons:
        return CapitalizerReasoningDecision(
            decision=CapitalizerDecision.ABSTAIN,
            hypothesis_id=situation.hypothesis_id,
            source_event_id=situation.source_event_id,
            reasons=tuple(dict.fromkeys(reasons)),
            adversarial_findings=adversarial,
        )

    if situation.execution.quality is ExecutionQuality.BAD:
        return CapitalizerReasoningDecision(
            decision=CapitalizerDecision.ABSTAIN,
            hypothesis_id=situation.hypothesis_id,
            source_event_id=situation.source_event_id,
            reasons=("EXECUTION_QUALITY_BAD",),
            adversarial_findings=adversarial,
        )

    wait_reasons: list[str] = []
    if situation.correlated_exposure_blocked:
        wait_reasons.append("CORRELATED_EXPOSURE_BLOCKED")
    if situation.execution.quality is ExecutionQuality.DEGRADED:
        wait_reasons.append("EXECUTION_QUALITY_DEGRADED")
    if situation.evidence_strength in {EvidenceStrength.UNKNOWN, EvidenceStrength.LOW}:
        wait_reasons.append("EVIDENCE_INSUFFICIENT")
    if not situation.strategy_trigger_ready:
        wait_reasons.append("STRATEGY_TRIGGER_NOT_READY")
    if not situation.displacement_confirmed:
        wait_reasons.append("DISPLACEMENT_NOT_CONFIRMED")

    if wait_reasons:
        return CapitalizerReasoningDecision(
            decision=CapitalizerDecision.WAIT,
            hypothesis_id=situation.hypothesis_id,
            source_event_id=situation.source_event_id,
            reasons=tuple(wait_reasons),
            adversarial_findings=adversarial,
        )

    return CapitalizerReasoningDecision(
        decision=CapitalizerDecision.EXECUTE,
        hypothesis_id=situation.hypothesis_id,
        source_event_id=situation.source_event_id,
        reasons=("CAUSAL_STATE_PASSED", "ADVERSARIAL_CHECK_PASSED"),
        adversarial_findings=adversarial,
    )
