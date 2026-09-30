"""Governed advisory seam from CIBO cognition into QORE Capitalizer.

CIBO is allowed to constrain an already-produced Capitalizer decision, never to manufacture
execution authority. The seam is monotonic toward caution:
EXECUTE may become WAIT/ABSTAIN; WAIT/ABSTAIN can never become EXECUTE because of CIBO.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveDirectiveKind,
    CiboExecutiveSynthesis,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerDecision
from qore.infrastructure.trader_lab.capitalizer_reasoning import (
    CapitalizerReasoningDecision,
)


@dataclass(frozen=True, slots=True)
class CapitalizerCiboAdvisory:
    synthesis_id: UUID
    directive: CiboExecutiveDirectiveKind
    synthesized_at: datetime
    evidence_count: int
    uncertainty_kind: str
    limitations: tuple[str, ...]
    grants_execution_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.evidence_count <= 0:
            raise ValueError("CIBO advisory requires explicit evidence")
        if not self.uncertainty_kind:
            raise ValueError("CIBO advisory requires uncertainty identity")
        if self.grants_execution_authority or self.grants_capital_authority:
            raise ValueError("CIBO advisory cannot grant operational authority")


def adapt_cibo_synthesis(
    synthesis: CiboExecutiveSynthesis,
    *,
    decision_at: datetime,
) -> CapitalizerCiboAdvisory:
    """Convert a governed CIBO synthesis into a causal Capitalizer advisory."""

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise ValueError("decision_at must be timezone-aware")
    synthesis.revalidate()
    if synthesis.synthesized_at > decision_at:
        raise ValueError("future CIBO synthesis cannot enter Capitalizer decision state")
    return CapitalizerCiboAdvisory(
        synthesis_id=synthesis.synthesis_id,
        directive=synthesis.directive,
        synthesized_at=synthesis.synthesized_at,
        evidence_count=len(synthesis.evidence_refs),
        uncertainty_kind=synthesis.uncertainty.kind.value,
        limitations=synthesis.limitations,
    )


def constrain_with_cibo(
    *,
    base: CapitalizerReasoningDecision,
    advisory: CapitalizerCiboAdvisory,
) -> CapitalizerReasoningDecision:
    """Apply CIBO monotonically: preserve or demote, never promote."""

    if base.decision is CapitalizerDecision.ABSTAIN:
        return base

    if advisory.directive is CiboExecutiveDirectiveKind.ABSTAIN:
        return CapitalizerReasoningDecision(
            decision=CapitalizerDecision.ABSTAIN,
            hypothesis_id=base.hypothesis_id,
            source_event_id=base.source_event_id,
            reasons=(*base.reasons, "CIBO_ADVISORY_ABSTAIN"),
            adversarial_findings=base.adversarial_findings,
        )

    if advisory.directive in {
        CiboExecutiveDirectiveKind.DEFER,
        CiboExecutiveDirectiveKind.QUESTION,
        CiboExecutiveDirectiveKind.REQUEST_EVIDENCE,
        CiboExecutiveDirectiveKind.REQUEST_RESEARCH,
    }:
        if base.decision is CapitalizerDecision.EXECUTE:
            return CapitalizerReasoningDecision(
                decision=CapitalizerDecision.WAIT,
                hypothesis_id=base.hypothesis_id,
                source_event_id=base.source_event_id,
                reasons=(*base.reasons, f"CIBO_ADVISORY_{advisory.directive.value.upper()}"),
                adversarial_findings=base.adversarial_findings,
            )
        return base

    # RECOMMEND is still advisory. It may preserve EXECUTE, but can never upgrade WAIT.
    return base
