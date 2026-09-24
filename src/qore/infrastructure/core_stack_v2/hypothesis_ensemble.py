"""Current-market hypothesis ensemble for Shared Core.

Perception describes facts. Hypotheses interpret those facts without using any
historical or future outcome. Memory may later score the hypotheses, but cannot
create present-market evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.perception import (
    PerceptionState,
    PerceptionVector,
)


class MarketHypothesis(StrEnum):
    REVERSAL = "REVERSAL"
    CONTINUATION_AGAINST = "CONTINUATION_AGAINST"
    RANGE_NOISE = "RANGE_NOISE"
    ANOMALY = "ANOMALY"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class HypothesisEnsemble:
    primary: MarketHypothesis
    reversal_score: int
    continuation_against_score: int
    range_noise_score: int
    anomaly_score: int
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (
            self.reversal_score,
            self.continuation_against_score,
            self.range_noise_score,
            self.anomaly_score,
        ):
            if value < 0:
                raise ValueError("hypothesis score cannot be negative")


def _primary(
    reversal: int,
    continuation: int,
    range_noise: int,
    anomaly: int,
) -> MarketHypothesis:
    scores = {
        MarketHypothesis.REVERSAL: reversal,
        MarketHypothesis.CONTINUATION_AGAINST: continuation,
        MarketHypothesis.RANGE_NOISE: range_noise,
        MarketHypothesis.ANOMALY: anomaly,
    }
    ordered = sorted(
        scores.items(),
        key=lambda item: (-item[1], item[0].value),
    )
    if not ordered or ordered[0][1] == 0:
        return MarketHypothesis.UNRESOLVED
    if len(ordered) > 1 and ordered[0][1] == ordered[1][1]:
        return MarketHypothesis.UNRESOLVED
    return ordered[0][0]


def evaluate_reversal_hypotheses(
    perception: PerceptionVector,
) -> HypothesisEnsemble:
    """Interpret current perception for a reversal-style opportunity."""
    reversal = continuation = range_noise = anomaly = 0
    evidence: list[str] = []

    # A strong reclaim/recovery after a liquidity raid is direct current-market
    # evidence for a reversal hypothesis.
    if perception.sweep_recovery_ref >= 0.20:
        reversal += 2
        evidence.append("REVERSAL:STRONG_SWEEP_RECOVERY")
    elif perception.sweep_recovery_ref < 0.08:
        continuation += 2
        evidence.append("CONTINUATION:FAILED_SWEEP_RECOVERY")

    # Acceleration in the opportunity direction after a weaker/negative
    # 10-minute path is a transition, not a contradiction.
    improvement = (
        perception.signed_efficiency_5
        - perception.signed_efficiency_10
    )
    if improvement >= 0.20 and perception.signed_efficiency_5 > 0:
        reversal += 2
        evidence.append("REVERSAL:SHORT_HORIZON_INFLECTION")
    elif (
        perception.signed_efficiency_5 < -0.15
        and perception.signed_efficiency_10 < -0.15
    ):
        continuation += 2
        evidence.append("CONTINUATION:ALIGNED_ADVERSE_EFFICIENCY")

    if perception.signed_body_bias_5 >= 0.10:
        reversal += 1
        evidence.append("REVERSAL:CURRENT_DISPLACEMENT_SUPPORTIVE")
    elif perception.signed_body_bias_5 <= -0.10:
        continuation += 1
        evidence.append("CONTINUATION:CURRENT_DISPLACEMENT_ADVERSE")

    # Cross-market divergence may be useful reversal information. Uniform
    # adverse peer continuation is different from divergence.
    if perception.peer_divergence >= 0.80:
        reversal += 1
        anomaly += 1
        evidence.append("REVERSAL:CROSS_MARKET_DIVERGENCE")
    elif perception.peer_consensus < -0.05:
        continuation += 1
        evidence.append("CONTINUATION:PEERS_CONFIRM_ADVERSE_DIRECTION")
    elif perception.peer_consensus > 0.05:
        reversal += 1
        evidence.append("REVERSAL:PEERS_CONFIRM_OPPORTUNITY_DIRECTION")

    if (
        perception.overlap_5 >= 0.90
        and abs(perception.signed_efficiency_5) < 0.15
    ):
        range_noise += 2
        evidence.append("RANGE:HIGH_OVERLAP_LOW_EFFICIENCY")
    elif (
        perception.overlap_5 <= 0.70
        and perception.signed_efficiency_5 > 0.10
    ):
        reversal += 1
        evidence.append("REVERSAL:CLEAN_EXPANSION")

    if perception.volatility_acceleration >= 2.25:
        anomaly += 2
        evidence.append("ANOMALY:VOLATILITY_SPIKE")
    elif 0.90 <= perception.volatility_acceleration <= 1.75:
        reversal += 1
        evidence.append("REVERSAL:ORDERLY_VOLATILITY")

    if perception.anomaly_state is PerceptionState.ANOMALOUS:
        anomaly += 1
        evidence.append("ANOMALY:PERCEPTION_FLAG")

    primary = _primary(reversal, continuation, range_noise, anomaly)
    return HypothesisEnsemble(
        primary=primary,
        reversal_score=reversal,
        continuation_against_score=continuation,
        range_noise_score=range_noise,
        anomaly_score=anomaly,
        evidence=tuple(evidence),
    )
