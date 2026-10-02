"""Metacognitive self-assessment for Shared Core.

The brain must represent not only what it believes, but how trustworthy its own
understanding is. This module combines data quality, disagreement, novelty,
causal consistency, analog familiarity and calibration into an explicit
understanding state.

It is deliberately conservative and authority-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class UnderstandingState(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class MetacognitiveEvidence:
    as_of: datetime
    data_quality_bps: int
    hypothesis_entropy_bps: int
    model_disagreement_bps: int
    novelty_bps: int
    causal_consistency_bps: int
    historical_similarity_bps: int
    calibration_bps: int
    regime_familiarity_bps: int

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "data_quality_bps",
            "hypothesis_entropy_bps",
            "model_disagreement_bps",
            "novelty_bps",
            "causal_consistency_bps",
            "historical_similarity_bps",
            "calibration_bps",
            "regime_familiarity_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


@dataclass(frozen=True, slots=True)
class MetacognitiveAssessment:
    as_of: datetime
    state: UnderstandingState
    confidence_bps: int
    epistemic_uncertainty_bps: int
    out_of_distribution_bps: int
    causal_consistency_bps: int
    model_disagreement_bps: int
    reasons: tuple[str, ...]
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "confidence_bps",
            "epistemic_uncertainty_bps",
            "out_of_distribution_bps",
            "causal_consistency_bps",
            "model_disagreement_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError("metacognition cannot carry trading authority")


def assess_metacognition(
    evidence: MetacognitiveEvidence,
) -> MetacognitiveAssessment:
    """Estimate how well Shared understands the present state."""

    reliability = (
        evidence.data_quality_bps
        + (10_000 - evidence.hypothesis_entropy_bps)
        + (10_000 - evidence.model_disagreement_bps)
        + (10_000 - evidence.novelty_bps)
        + evidence.causal_consistency_bps
        + evidence.historical_similarity_bps
        + evidence.calibration_bps
        + evidence.regime_familiarity_bps
    ) // 8

    epistemic = (
        evidence.hypothesis_entropy_bps
        + evidence.model_disagreement_bps
        + evidence.novelty_bps
        + (10_000 - evidence.historical_similarity_bps)
        + (10_000 - evidence.regime_familiarity_bps)
    ) // 5

    reasons: list[str] = []
    if evidence.data_quality_bps < 6_000:
        reasons.append("DATA_QUALITY_WEAK")
    if evidence.model_disagreement_bps >= 6_000:
        reasons.append("MODEL_DISAGREEMENT_HIGH")
    if evidence.novelty_bps >= 6_000:
        reasons.append("STATE_NOVEL_OR_OUT_OF_DISTRIBUTION")
    if evidence.causal_consistency_bps < 4_000:
        reasons.append("CAUSAL_GRAPH_INCONSISTENT")
    if evidence.historical_similarity_bps < 3_500:
        reasons.append("WEAK_HISTORICAL_ANALOGUES")
    if evidence.calibration_bps < 5_000:
        reasons.append("PREDICTION_CALIBRATION_WEAK")
    if evidence.regime_familiarity_bps < 4_000:
        reasons.append("REGIME_UNFAMILIAR")

    if evidence.data_quality_bps < 3_000:
        state = UnderstandingState.UNKNOWN
        reasons.append("INSUFFICIENT_OBSERVABILITY")
    elif reliability >= 7_500 and epistemic <= 3_500:
        state = UnderstandingState.HIGH
        reasons.append("STATE_UNDERSTANDING_HIGH")
    elif reliability >= 5_500 and epistemic <= 5_500:
        state = UnderstandingState.MEDIUM
        reasons.append("STATE_UNDERSTANDING_PARTIAL")
    else:
        state = UnderstandingState.LOW
        reasons.append("STATE_UNDERSTANDING_LOW")

    return MetacognitiveAssessment(
        as_of=evidence.as_of,
        state=state,
        confidence_bps=max(0, min(10_000, reliability)),
        epistemic_uncertainty_bps=max(0, min(10_000, epistemic)),
        out_of_distribution_bps=evidence.novelty_bps,
        causal_consistency_bps=evidence.causal_consistency_bps,
        model_disagreement_bps=evidence.model_disagreement_bps,
        reasons=tuple(dict.fromkeys(reasons)),
    )
