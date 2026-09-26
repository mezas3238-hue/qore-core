"""Evidence-bound regime intelligence interface for QORE Capitalizer.

The final nine market families are deliberately not hard-coded here. Dedicated market-family
laboratories must earn those definitions later. This module gives cognition a causal container
for regime hypotheses without fabricating certainty or economic rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)


class CapitalizerRegimeResolution(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    SUPPORTED = "SUPPORTED"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True, slots=True)
class CapitalizerRegimeHypothesis:
    symbol: str
    observed_at: datetime
    family_id: str | None
    causal_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    knowledge: CapitalizerKnowledgeState

    def __post_init__(self) -> None:
        if self.symbol not in NINE_MARKET_UNIVERSE:
            raise ValueError("regime symbol outside Capitalizer universe")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("regime timestamp must be timezone-aware")
        if self.family_id == "":
            raise ValueError("regime family_id cannot be empty")
        if self.family_id is not None and not self.causal_evidence:
            raise ValueError("named regime hypothesis requires causal evidence")


@dataclass(frozen=True, slots=True)
class CapitalizerRegimeAssessment:
    symbol: str
    family_id: str | None
    resolution: CapitalizerRegimeResolution
    reasons: tuple[str, ...]
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.grants_entry_authority:
            raise ValueError("regime intelligence cannot grant entry authority")
        if self.grants_capital_authority:
            raise ValueError("regime intelligence cannot grant capital authority")


def assess_regime(
    hypothesis: CapitalizerRegimeHypothesis,
) -> CapitalizerRegimeAssessment:
    if hypothesis.contradictions:
        return CapitalizerRegimeAssessment(
            symbol=hypothesis.symbol,
            family_id=hypothesis.family_id,
            resolution=CapitalizerRegimeResolution.CONFLICTED,
            reasons=tuple(
                f"CONTRADICTION:{token}" for token in hypothesis.contradictions
            ),
        )
    if (
        hypothesis.family_id is None
        or not hypothesis.causal_evidence
        or hypothesis.knowledge
        in {
            CapitalizerKnowledgeState.UNKNOWN,
            CapitalizerKnowledgeState.CONFLICTED,
        }
    ):
        return CapitalizerRegimeAssessment(
            symbol=hypothesis.symbol,
            family_id=hypothesis.family_id,
            resolution=CapitalizerRegimeResolution.UNRESOLVED,
            reasons=("REGIME_NOT_CAUSALLY_RESOLVED",),
        )
    return CapitalizerRegimeAssessment(
        symbol=hypothesis.symbol,
        family_id=hypothesis.family_id,
        resolution=CapitalizerRegimeResolution.SUPPORTED,
        reasons=("REGIME_CAUSAL_EVIDENCE_PRESENT",),
    )
